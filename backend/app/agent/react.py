"""ReAct（推理+行动）智能体 — 基于 LangGraph create_react_agent。

模式：
    create_react_agent 编译一个 StateGraph：
    - 调用 LLM（带工具绑定）
    - 如果有工具调用 → 执行工具 → 反馈结果 → 回到 LLM
    - 如果无工具调用 → 最终答案 → END
"""

import json
import logging
from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    AIMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

logger = logging.getLogger(__name__)

# 流回调的类型别名：async def handler(event_type: str, data: dict) -> None
StreamHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass
class AgentResult:
    """ReAct 智能体执行结果。"""

    success: bool
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    iterations: int = 0
    usage: dict | None = None  # {"input_tokens": int, "output_tokens": int}


class ReActAgent:
    """ReAct 智能体：使用 LangGraph create_react_agent。

    智能体：
    1. 将消息（系统提示 + 历史记录 + 用户输入）发送给 LLM
    2. LLM 返回以下之一：
       a. 纯文本（最终答案）→ 返回给调用者
       b. 工具调用 → create_react_agent 自动执行工具并循环

    用法：
        agent = ReActAgent(model=model, tools=tools)
        result = await agent.execute(
            user_input="计划一个为期3天的北京之旅",
            system_prompt="你是一个旅行规划师...",
            conversation_history=[...],
        )
    """

    def __init__(
        self,
        model: BaseChatModel,
        tools: list[BaseTool],
        max_iterations: int = 10,
        max_tool_retries: int = 2,
    ) -> None:
        """初始化 ReAct 智能体。

        参数：
            model: LangChain BaseChatModel 实例。
            tools: LangChain BaseTool 列表。
            max_iterations: ReAct 循环的最大迭代次数。
            max_tool_retries: 每个工具执行失败时的最大重试次数。
        """
        self.model = model
        self.tools = tools
        self.max_iterations = max_iterations
        self.max_tool_retries = max_tool_retries

        # 绑定工具到模型
        self._model_with_tools = model.bind_tools(tools)

        # 编译 create_react_agent 图（一次性）
        self._graph = create_react_agent(
            model=self._model_with_tools,
            tools=self._wrap_tools_with_retry(tools, max_tool_retries),
        )

    def _wrap_tools_with_retry(
        self, tools: list[BaseTool], max_retries: int
    ) -> list[BaseTool]:
        """给工具包装重试逻辑。

        对于每个工具，创建一个包装器，在失败时自动重试最多 max_retries 次。
        如果 max_retries <= 0，直接返回原工具列表。
        """
        if max_retries <= 0:
            return tools

        from langchain_core.tools import StructuredTool

        wrapped = []
        for tool in tools:
            # 获取原始协程函数
            original_func = tool.func or tool.coroutine
            if original_func is None:
                wrapped.append(tool)
                continue

            # 使用工厂函数捕获循环变量
            def make_wrapper(func, retries, tool_name):
                async def wrapper(**kwargs):
                    last_error = None
                    for attempt in range(retries + 1):
                        try:
                            result = await func(**kwargs)
                            if isinstance(result, dict) and "error" in result:
                                last_error = result["error"]
                                if attempt < retries:
                                    logger.warning(
                                        f"Tool {tool_name} returned error "
                                        f"(attempt {attempt+1}), retrying: {last_error}"
                                    )
                                    continue
                            return result
                        except Exception as e:
                            last_error = str(e)
                            if attempt < retries:
                                logger.warning(
                                    f"Tool {tool_name} failed (attempt {attempt+1}), retrying: {e}"
                                )
                            else:
                                return {"error": f"Error after {retries+1} attempts: {last_error}"}
                    return {"error": str(last_error)}
                return wrapper

            wrapped_tool = StructuredTool.from_function(
                name=tool.name,
                description=tool.description,
                args_schema=tool.args_schema,
                coroutine=make_wrapper(original_func, max_retries, tool.name),
            )
            wrapped.append(wrapped_tool)

        return wrapped

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
            stream_handler: 可选的异步实时进度回调。
                async def handler(event_type: str, data: dict) -> None
                event_type 取值："llm_response", "tool_result", "final"

        返回：
            包含最终答案或错误状态的 AgentResult。
        """
        # 构建初始消息
        messages: list[BaseMessage] = [SystemMessage(content=system_prompt)]

        # 转换对话历史为 LangChain 消息格式
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
                elif role == "tool":
                    messages.append(ToolMessage(
                        content=content,
                        tool_call_id=msg.get("tool_call_id", ""),
                    ))
                elif role == "system":
                    messages.append(SystemMessage(content=content))

        # 添加用户输入
        messages.append(HumanMessage(content=user_input))

        # 配置 recursion limit
        config = {"recursion_limit": self.max_iterations * 2 + 5}

        if stream_handler:
            return await self._execute_streaming(messages, config, stream_handler)
        else:
            return await self._execute_non_streaming(messages, config)

    async def _execute_non_streaming(
        self, messages: list[BaseMessage], config: dict
    ) -> AgentResult:
        """非流式执行。"""
        try:
            result = await self._graph.ainvoke(
                {"messages": messages},
                config=config,
            )
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return AgentResult(
                success=False,
                content=f"Agent execution failed: {e}",
            )

        return self._extract_result(result)

    async def _execute_streaming(
        self,
        messages: list[BaseMessage],
        config: dict,
        stream_handler: StreamHandler,
    ) -> AgentResult:
        """流式执行，实时推送事件。"""
        all_tool_calls: list[dict] = []

        try:
            async for event in self._graph.astream_events(
                {"messages": messages},
                config=config,
                version="v2",
            ):
                event_type = event.get("event", "")

                # LLM 流式输出
                if event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        await stream_handler("llm_response", {
                            "content": chunk.content,
                            "tool_calls": [],
                            "iteration": 0,
                        })

                # 工具调用开始
                elif event_type == "on_tool_start":
                    tool_name = event.get("name", "unknown")
                    tool_input = event.get("data", {}).get("input", {})
                    await stream_handler("tool_result", {
                        "tool": tool_name,
                        "arguments": tool_input,
                        "result": "Executing...",
                    })

                # 工具调用结束
                elif event_type == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    tool_output = event.get("data", {}).get("output")
                    # 格式化工具输出
                    result_str = str(tool_output) if tool_output else ""
                    tc_record = {
                        "tool": tool_name,
                        "arguments": {},
                        "result": result_str,
                    }
                    all_tool_calls.append(tc_record)
                    await stream_handler("tool_result", tc_record)

        except Exception as e:
            logger.error(f"Streaming agent execution failed: {e}")
            await stream_handler("final", {"content": f"Error: {e}"})
            return AgentResult(
                success=False,
                content=f"Agent execution failed: {e}",
                tool_calls=all_tool_calls,
            )

        # 发送最终事件
        final_content = "Agent completed streaming."
        await stream_handler("final", {"content": final_content})

        return AgentResult(
            success=True,
            content=final_content,
            tool_calls=all_tool_calls,
        )

    def _extract_result(self, result: dict) -> AgentResult:
        """从 LangGraph 结果中提取 AgentResult。"""
        messages: list[BaseMessage] = result.get("messages", [])

        # 提取最终 AI 回复
        final_content = ""
        tool_calls_made: list[dict] = []

        for msg in messages:
            if isinstance(msg, AIMessage):
                if msg.content:
                    final_content = msg.content
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls_made.append({
                            "tool": tc.get("name", ""),
                            "arguments": tc.get("args", {}),
                            "result": "",  # 工具结果在后续的 ToolMessage 中
                        })
            elif isinstance(msg, ToolMessage):
                # 将工具结果关联到最近的工具调用
                tc_id = getattr(msg, "tool_call_id", "")
                for tc in tool_calls_made:
                    if tc.get("id") == tc_id:
                        tc["result"] = msg.content
                        break

        # 统计迭代次数（每对 AIMessage+ToolMessage = 1 次迭代）
        ai_count = sum(1 for m in messages if isinstance(m, AIMessage) and getattr(m, "tool_calls", None))
        iterations = ai_count + 1  # +1 因为最终回复也是一次 LLM 调用

        # 提取 token 用量
        usage = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and hasattr(msg, "usage_metadata"):
                um = msg.usage_metadata
                usage = {
                    "input_tokens": um.get("input_tokens", 0),
                    "output_tokens": um.get("output_tokens", 0),
                }
                break

        return AgentResult(
            success=True,
            content=final_content,
            tool_calls=tool_calls_made,
            iterations=iterations,
            usage=usage,
        )
