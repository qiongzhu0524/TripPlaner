"""行程规划服务：编排完整的行程规划工作流。

基于 LangGraph StateGraph，替代旧的手动编排逻辑。
是 POST /api/trip/plan 端点的唯一入口。
"""

import logging
import uuid
from datetime import date
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from app.workflow.state import TripPlanState
from app.workflow.graph import build_trip_planning_graph

logger = logging.getLogger(__name__)


class TripService:
    """行程规划的业务编排 — 基于 LangGraph。

    用法：
        llm = create_llm_model()
        tools = create_all_tools()
        service = TripService(llm=llm, tools=tools)
        plan = await service.plan_trip(user_id=..., destination=...)
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: list[BaseTool],
        max_iterations: int = 10,
    ) -> None:
        """使用 LLM 和工具初始化。

        Args:
            llm: LangChain BaseChatModel 实例。
            tools: LangChain BaseTool 列表。
            max_iterations: ReAct Agent 最大迭代次数。
        """
        self._llm = llm
        self._tools = tools
        self._max_iterations = max_iterations

        # 编译图（TripService 内部管理，避免路由层感知）
        self._graph = build_trip_planning_graph(
            model=llm,
            tools=tools,
            max_iterations=max_iterations,
        )

    async def plan_trip(
        self,
        user_id: str,
        destination: str,
        start_date: date,
        days: int = 3,
        travel_style: str = "balanced",
        budget_level: str = "midrange",
        interests: list[str] | None = None,
        dietary_preferences: list[str] | None = None,
        stream_handler=None,
    ) -> dict[str, Any]:
        """执行完整的行程规划流水线。

        流水线（由 LangGraph 图驱动）：
        1. load_profile: 从记忆系统加载用户上下文
        2. prepare_prompt: 构建系统提示词
        3. execute_agent: ReAct Agent（带工具访问权限）
        4. extract_output: 解析 Agent 输出
        5. save_memory: 将交互记录保存到记忆系统

        Args:
            user_id: 用户标识符。
            destination: 行程目的地。
            start_date: 行程开始日期。
            days: 旅行天数。
            travel_style: relaxed / balanced / intensive。
            budget_level: budget / midrange / luxury。
            interests: 兴趣标签列表。
            dietary_preferences: 饮食限制列表。
            stream_handler: 可选的异步回调，用于流式进度更新。

        Returns:
            包含行程安排、提示和元数据的行程规划字典。
        """
        if days > 0:
            end_date = start_date.replace(day=start_date.day + days - 1)
        else:
            end_date = start_date

        session_id = f"trip_{uuid.uuid4().hex[:12]}"

        logger.info(
            f"Planning trip: user={user_id}, dest={destination}, "
            f"{days} days from {start_date}, style={travel_style}, budget={budget_level}"
        )

        # 构建工具描述（用于注入 system prompt）
        tools_description = self._format_tools_description()

        # 构建初始状态
        initial_state: TripPlanState = {
            "user_id": user_id,
            "session_id": session_id,
            "destination": destination,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days,
            "travel_style": travel_style,
            "budget_level": budget_level,
            "interests": interests or [],
            "dietary_preferences": dietary_preferences or [],
            "tools_description": tools_description,
            # 消息由 prepare_prompt_node 设置
            "messages": [],
        }

        # 注入 LLM 到 config（供 save_memory_node 使用）
        config = {"configurable": {"llm": self._llm}}

        if stream_handler:
            # 流式路径
            async for event in self._graph.astream_events(
                initial_state, config=config, version="v2"
            ):
                translated = self._translate_event(event)
                if translated:
                    await stream_handler(translated["type"], translated["data"])

            # 对于流式，返回基本响应
            return {
                "trip_id": session_id,
                "destination": destination,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
                "content": "Trip planning completed. See stream for details.",
                "tool_calls_made": [],
                "iterations": 0,
                "usage": None,
            }
        else:
            # 非流式路径
            final_state = await self._graph.ainvoke(initial_state, config=config)

            return {
                "trip_id": session_id,
                "destination": destination,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
                "content": final_state.get("final_response", ""),
                "tool_calls_made": final_state.get("tool_calls_made", []),
                "iterations": final_state.get("iterations", 0),
                "usage": final_state.get("usage"),
            }

    def _format_tools_description(self) -> str:
        """构建格式化的可用工具列表，用于系统提示词。"""
        if not self._tools:
            return "No tools available."

        lines = []
        for tool in self._tools:
            lines.append(f"- **{tool.name}**: {tool.description}")
            if tool.args_schema:
                # 从 Pydantic model 提取参数字段
                try:
                    schema = tool.args_schema.model_json_schema()
                    props = schema.get("properties", {})
                    required = schema.get("required", [])
                    param_desc = ", ".join(
                        f"{k}{'*' if k in required else ''}" for k in props.keys()
                    )
                    if param_desc:
                        lines.append(f"  Parameters: {param_desc}")
                except Exception:
                    pass
        return "\n".join(lines)

    @staticmethod
    def _translate_event(event: dict) -> dict | None:
        """将 LangGraph astream_events 事件翻译为旧 SSE 格式。

        返回 {'type': str, 'data': dict} 或 None（如果事件应被忽略）。
        """
        event_type = event.get("event", "")

        if event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                return {
                    "type": "llm_response",
                    "data": {"content": chunk.content, "tool_calls": [], "iteration": 0},
                }

        elif event_type == "on_tool_start":
            return {
                "type": "tool_result",
                "data": {
                    "tool": event.get("name", "unknown"),
                    "arguments": event.get("data", {}).get("input", {}),
                    "result": "Executing...",
                },
            }

        elif event_type == "on_tool_end":
            output = event.get("data", {}).get("output", "")
            return {
                "type": "tool_result",
                "data": {
                    "tool": event.get("name", "unknown"),
                    "arguments": {},
                    "result": str(output) if output else "",
                },
            }

        return None  # 忽略其他事件
