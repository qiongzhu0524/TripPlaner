"""ReAct（推理+行动）智能体——核心循环。

模式：
    while 未完成 and 迭代次数 < 最大迭代次数:
        response = LLM.generate(messages, tools)
        if 无工具调用:
            done → 返回最终答案
        for 每个工具调用:
            result = execute_tool(name, args)
            将工具结果追加到 messages
        repeat
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.agent.providers.base import LLMProvider, TokenUsage

logger = logging.getLogger(__name__)

# 流回调的类型别名
StreamHandler = Callable[[str, dict[str, Any]], Any | None]


@dataclass
class AgentResult:
    """ReAct 智能体执行结果。"""

    success: bool
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    iterations: int = 0
    usage: TokenUsage | None = None


class ReActAgent:
    """ReAct 智能体：使用 LLM + 工具迭代地推理和行动。

    智能体：
    1. 将消息（系统提示 + 历史记录 + 用户输入）发送给 LLM
    2. LLM 返回以下之一：
       a. 纯文本（最终答案）→ 返回给调用者
       b. 工具调用 → 执行工具，将结果反馈，重复

    用法：
        agent = ReActAgent(llm=llm, tool_registry=registry)
        result = await agent.execute(
            user_input="计划一个为期3天的北京之旅",
            system_prompt="你是一个旅行规划师...",
            conversation_history=[...],
        )
    """

    def __init__(
        self,
        llm: LLMProvider,
        tool_registry: "ToolRegistry",
        max_iterations: int = 10,
        max_tool_retries: int = 2,
    ) -> None:
        """初始化 ReAct 智能体。

        参数：
            llm: LLM 提供者实例。
            tool_registry: 用于执行工具调用的工具注册表。
            max_iterations: ReAct 循环的最大迭代次数，超过后强制停止。
            max_tool_retries: 每个工具执行失败时的最大重试次数。
        """
        self.llm = llm
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.max_tool_retries = max_tool_retries

    async def execute(
        self,
        user_input: str,
        system_prompt: str,
        conversation_history: list[dict] | None = None,
        stream_handler: StreamHandler | None = None,
    ) -> AgentResult:
        """执行 ReAct 循环。

        参数：
            user_input: 用户的当前消息。
            system_prompt: 包含工具描述和上下文的系统提示。
            conversation_history: 之前的对话轮次（用户/助手/工具消息）。
            stream_handler: 可选的实时进度回调。
                签名：async def handler(event_type: str, data: dict) -> None
                event_type 取值："llm_response", "tool_result", "final"

        返回：
            包含最终答案或错误状态的 AgentResult。
        """
        # 构建初始消息
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_input})

        tools_schema = self.tool_registry.to_openai_tools_format()
        iteration = 0
        all_tool_calls: list[dict] = []
        total_usage = TokenUsage()

        while iteration < self.max_iterations:
            iteration += 1
            logger.debug(
                f"ReAct iteration {iteration}/{self.max_iterations}, "
                f"messages: {len(messages)}, tools: {len(tools_schema)}"
            )

            # ---- 步骤 1：LLM 生成响应 ----
            try:
                response = await self.llm.generate(
                    messages=messages,
                    tools=tools_schema if tools_schema else None,
                )
            except Exception as e:
                logger.error(f"LLM call failed at iteration {iteration}: {e}")
                return AgentResult(
                    success=False,
                    content=f"LLM call failed: {e}",
                    tool_calls=all_tool_calls,
                    iterations=iteration,
                )

            total_usage.input_tokens += response.usage.input_tokens
            total_usage.output_tokens += response.usage.output_tokens

            if stream_handler:
                stream_handler("llm_response", {
                    "content": response.content,
                    "tool_calls": response.tool_calls,
                    "iteration": iteration,
                })

            # ---- 步骤 2：检查是否为最终答案 ----
            if not response.tool_calls:
                logger.info(f"Agent finished at iteration {iteration}")
                if stream_handler:
                    stream_handler("final", {"content": response.content})
                return AgentResult(
                    success=True,
                    content=response.content,
                    tool_calls=all_tool_calls,
                    iterations=iteration,
                    usage=total_usage,
                )

            # ---- 步骤 3：执行工具调用 ----
            # 追加助手消息及工具调用
            assistant_msg: dict = {
                "role": "assistant",
                "content": response.content or "",
            }
            if response.tool_calls:
                assistant_msg["tool_calls"] = response.tool_calls
            messages.append(assistant_msg)

            for tc in response.tool_calls:
                func_info = tc.get("function", tc)
                func_name = func_info.get("name", "")
                raw_args = func_info.get("arguments", "{}")

                # 解析参数
                try:
                    if isinstance(raw_args, str):
                        func_args = json.loads(raw_args)
                    else:
                        func_args = raw_args
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Failed to parse arguments for {func_name}: {raw_args}")
                    func_args = {}

                # 执行工具（带重试）
                tool_result_content = ""
                last_error = None

                for attempt in range(self.max_tool_retries + 1):
                    try:
                        result = await self.tool_registry.execute(func_name, **func_args)
                        if result.success:
                            tool_result_content = json.dumps(result.data, ensure_ascii=False)
                        else:
                            tool_result_content = f"Error: {result.error}"
                            last_error = result.error
                        break
                    except Exception as e:
                        last_error = str(e)
                        if attempt < self.max_tool_retries:
                            logger.warning(
                                f"Tool {func_name} failed (attempt {attempt+1}), retrying: {e}"
                            )
                        else:
                            tool_result_content = f"Error after {self.max_tool_retries+1} attempts: {last_error}"

                tool_call_record = {
                    "tool": func_name,
                    "arguments": func_args,
                    "result": tool_result_content,
                }
                all_tool_calls.append(tool_call_record)

                if stream_handler:
                    stream_handler("tool_result", tool_call_record)

                # Append tool result message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": tool_result_content,
                })

        # ---- 达到最大迭代次数 ----
        logger.warning(f"Agent reached max iterations ({self.max_iterations}) without final answer")
        return AgentResult(
            success=False,
            content="Maximum iterations reached without a final answer. The task may be too complex.",
            tool_calls=all_tool_calls,
            iterations=iteration,
            usage=total_usage,
        )
