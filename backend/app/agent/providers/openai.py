"""OpenAI 提供者——也适用于任何与 OpenAI 兼容的 API（DeepSeek 等）。"""

import json
import os
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.agent.providers.base import LLMProvider, LLMResponse, StreamEvent, TokenUsage
from app.config import settings


class OpenAIProvider(LLMProvider):
    """OpenAI 及与 OpenAI 兼容的 API 的 LLM 提供者。"""

    def __init__(self) -> None:
        cfg = settings.llm_openai
        self._client = AsyncOpenAI(
            api_key=cfg.api_key or os.getenv("OPENAI_API_KEY"),
            base_url=cfg.base_url or None,
        )
        self._model = cfg.model
        self._default_max_tokens = cfg.max_tokens
        self._default_temperature = cfg.temperature

    async def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """通过 OpenAI 聊天 API 生成补全。"""
        params: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self._default_max_tokens),
            "temperature": kwargs.get("temperature", self._default_temperature),
        }
        if tools:
            params["tools"] = tools

        response = await self._client.chat.completions.create(**params)
        choice = response.choices[0]

        tool_calls = []
        if choice.message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]

        return LLMResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            usage=TokenUsage(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
            ),
            finish_reason=choice.finish_reason or "stop",
        )

    async def generate_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        """通过 OpenAI 聊天 API 生成流式补全。"""
        params: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self._default_max_tokens),
            "temperature": kwargs.get("temperature", self._default_temperature),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            params["tools"] = tools

        stream = await self._client.chat.completions.create(**params)

        tool_calls_acc: dict[int, dict] = {}
        final_usage = TokenUsage()

        async for chunk in stream:
            if not chunk.choices:
                # 用量块（当 stream_options.include_usage=True 时）
                if chunk.usage:
                    final_usage = TokenUsage(
                        input_tokens=chunk.usage.prompt_tokens or 0,
                        output_tokens=chunk.usage.completion_tokens or 0,
                    )
                continue

            delta = chunk.choices[0].delta
            if delta is None:
                continue

            # 文本内容增量
            if delta.content:
                yield StreamEvent(type="content", data=delta.content)

            # 工具调用增量
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    acc = tool_calls_acc[idx]
                    if tc_delta.id:
                        acc["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            acc["function"]["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            acc["function"]["arguments"] += tc_delta.function.arguments

        # 包含完整工具调用和用量的最终事件
        yield StreamEvent(
            type="finish",
            data={
                "tool_calls": list(tool_calls_acc.values()),
                "usage": {
                    "input_tokens": final_usage.input_tokens,
                    "output_tokens": final_usage.output_tokens,
                },
            },
        )

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model
