"""Anthropic 提供者——将 Anthropic 的原生格式适配到我们的公共接口。

与 OpenAI 的关键区别：
- 系统提示是独立参数，而非 role="system" 的消息
- 工具格式使用 "input_schema" 而非 "parameters"
- 响应内容是块列表（文本、工具使用），而非单个字符串
- 流式使用 content_block_start/delta/stop 事件
"""

import json
import os
from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import (
    MessageStreamEvent,
    ContentBlockStartEvent,
    ContentBlockDeltaEvent,
    MessageStopEvent,
)

from app.agent.providers.base import LLMProvider, LLMResponse, StreamEvent, TokenUsage
from app.config import settings


class AnthropicProvider(LLMProvider):
    """Anthropic Claude 模型的 LLM 提供者。"""

    def __init__(self) -> None:
        cfg = settings.llm_anthropic
        self._client = AsyncAnthropic(api_key=cfg.api_key or os.getenv("ANTHROPIC_API_KEY"))
        self._model = cfg.model
        self._default_max_tokens = cfg.max_tokens
        self._default_temperature = cfg.temperature

    # ------------------------------------------------------------------
    # 格式转换辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_system(messages: list[dict]) -> tuple[str | None, list[dict]]:
        """从消息列表中提取系统消息。

        返回 (system_text, remaining_messages)。
        """
        system_text = None
        remaining = []
        for m in messages:
            if m["role"] == "system":
                # 合并多条系统消息
                if system_text is None:
                    system_text = m.get("content", "")
                else:
                    system_text += "\n" + m.get("content", "")
            else:
                remaining.append(m)
        return system_text, remaining

    @staticmethod
    def _convert_tools_to_anthropic(tools: list[dict] | None) -> list[dict] | None:
        """将 OpenAI 工具格式转换为 Anthropic 工具格式。

        OpenAI: {"type": "function", "function": {"name": "...", "parameters": {...}}}
        Anthropic: {"name": "...", "description": "...", "input_schema": {...}}
        """
        if not tools:
            return None

        anthropic_tools = []
        for t in tools:
            func = t.get("function", t)
            anthropic_tools.append(
                {
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", func.get("input_schema", {})),
                }
            )
        return anthropic_tools

    @staticmethod
    def _convert_history_to_anthropic(messages: list[dict]) -> list[dict]:
        """将 OpenAI 格式的消息转换为 Anthropic 格式。

        处理：
        - 工具调用消息（带有 tool_calls 的 assistant）
        - 工具结果消息（role="tool"）
        """
        converted = []
        pending_tool_results: list[dict] = []

        for m in messages:
            role = m.get("role", "")

            if role == "assistant":
                # 首先刷新任何待处理的工具结果
                if pending_tool_results:
                    converted.append({
                        "role": "user",
                        "content": pending_tool_results,
                    })
                    pending_tool_results = []

                content: list[dict] = []
                if m.get("content"):
                    content.append({"type": "text", "text": m["content"]})

                # 添加 tool_use 块
                for tc in m.get("tool_calls", []):
                    func = tc.get("function", tc)
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                    content.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": func.get("name", ""),
                        "input": args,
                    })

                converted.append({"role": "assistant", "content": content})

            elif role == "tool":
                pending_tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": m.get("tool_call_id", ""),
                    "content": m.get("content", ""),
                })

            elif role == "user":
                if pending_tool_results:
                    converted.append({
                        "role": "user",
                        "content": list(pending_tool_results),
                    })
                    pending_tool_results = []
                converted.append({"role": "user", "content": m.get("content", "")})

        # 刷新剩余的
        if pending_tool_results:
            converted.append({"role": "user", "content": pending_tool_results})

        return converted

    # ------------------------------------------------------------------
    # 核心 API
    # ------------------------------------------------------------------

    async def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """通过 Anthropic Messages API 生成补全。"""
        system_text, remaining = self._extract_system(messages)
        anthropic_messages = self._convert_history_to_anthropic(remaining)
        anthropic_tools = self._convert_tools_to_anthropic(tools)

        params: dict[str, Any] = {
            "model": self._model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", self._default_max_tokens),
            "temperature": kwargs.get("temperature", self._default_temperature),
        }
        if system_text:
            params["system"] = system_text
        if anthropic_tools:
            params["tools"] = anthropic_tools

        response = await self._client.messages.create(**params)

        # 提取文本内容和工具调用
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input, ensure_ascii=False),
                    },
                })

        return LLMResponse(
            content="\n".join(text_parts),
            tool_calls=tool_calls,
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            finish_reason=response.stop_reason or "stop",
        )

    async def generate_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        """通过 Anthropic Messages API 生成流式补全。"""
        system_text, remaining = self._extract_system(messages)
        anthropic_messages = self._convert_history_to_anthropic(remaining)
        anthropic_tools = self._convert_tools_to_anthropic(tools)

        params: dict[str, Any] = {
            "model": self._model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", self._default_max_tokens),
            "temperature": kwargs.get("temperature", self._default_temperature),
            "stream": True,
        }
        if system_text:
            params["system"] = system_text
        if anthropic_tools:
            params["tools"] = anthropic_tools

        tool_use_acc: dict[int, dict] = {}
        tool_name_acc: dict[int, str] = {}

        async with self._client.messages.stream(**params) as stream:
            async for event in stream:
                if isinstance(event, ContentBlockStartEvent):
                    block = event.content_block
                    if block.type == "tool_use":
                        idx = event.index
                        tool_use_acc[idx] = {"id": block.id, "name": block.name, "input": {}}

                elif isinstance(event, ContentBlockDeltaEvent):
                    delta = event.delta
                    if delta.type == "text_delta":
                        yield StreamEvent(type="content", data=delta.text)
                    elif delta.type == "input_json_delta":
                        # 累积工具调用参数的 JSON
                        idx = event.index
                        if idx not in tool_name_acc:
                            tool_name_acc[idx] = ""
                        tool_name_acc[idx] += delta.partial_json

                elif isinstance(event, MessageStopEvent):
                    # 构建最终的工具调用
                    final_tool_calls = []
                    for idx, acc in tool_use_acc.items():
                        accumulated_json = tool_name_acc.get(idx, "")
                        try:
                            arguments = json.loads(accumulated_json)
                        except (json.JSONDecodeError, TypeError):
                            arguments = {}
                        final_tool_calls.append({
                            "id": acc["id"],
                            "type": "function",
                            "function": {
                                "name": acc["name"],
                                "arguments": json.dumps(arguments, ensure_ascii=False),
                            },
                        })

                    usage = TokenUsage(
                        input_tokens=event.message.usage.input_tokens,
                        output_tokens=event.message.usage.output_tokens,
                    )

                    yield StreamEvent(
                        type="finish",
                        data={
                            "tool_calls": final_tool_calls,
                            "usage": {
                                "input_tokens": usage.input_tokens,
                                "output_tokens": usage.output_tokens,
                            },
                        },
                    )

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model
