"""行程规划服务：编排完整的行程规划工作流。

注入：WorkflowEngine + MemoryManager + ToolRegistry + ReActAgent。
是 POST /api/trip/plan 端点的唯一入口。
"""

import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class TripService:
    """行程规划的业务编排。

    用法：
        async with async_session_factory() as db:
            service = TripService(db, agent, tool_registry)
            plan = await service.plan_trip(request)
    """

    def __init__(
        self,
        session: AsyncSession,
        agent,  # ReActAgent 实例
        tool_registry,  # ToolRegistry 实例
    ) -> None:
        """使用所需服务进行初始化。

        Args:
            session: 数据库会话。
            agent: 已配置的 ReActAgent。
            tool_registry: 已配置的 ToolRegistry。
        """
        self._session = session
        self.agent = agent
        self.tool_registry = tool_registry
        self.memory = MemoryManager(session)

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

        流水线：
        1. 从记忆系统加载用户上下文
        2. 构建注入所有上下文的系统提示词
        3. 执行 ReAct Agent（带工具访问权限）
        4. 将交互记录保存到记忆系统
        5. 返回结构化的行程规划

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
        end_date = start_date.replace(day=start_date.day + days - 1) if days > 0 else start_date
        session_id = f"trip_{uuid.uuid4().hex[:12]}"

        logger.info(
            f"Planning trip: user={user_id}, dest={destination}, "
            f"{days} days from {start_date}, style={travel_style}, budget={budget_level}"
        )

        # 步骤 1：加载用户上下文
        context = await self.memory.build_context(user_id, session_id)
        profile_summary = context.user_profile.get("summary", "") if context.user_profile else ""

        # 步骤 2：构建系统提示词
        from app.agent.context import ContextBuilder

        tools_description = self._format_tools_description()

        system_prompt = ContextBuilder.build_system_prompt(
            tools_description=tools_description,
            destination=destination,
            start_date=start_date.isoformat(),
            end_date=(end_date.isoformat() if isinstance(end_date, date) else str(end_date)),
            days=days,
            travel_style=travel_style,
            budget_level=budget_level,
            interests=interests,
            user_profile_summary=profile_summary,
            conversation_summary="First planning session for this trip.",
        )

        # 步骤 3：构建用户输入
        user_input = (
            f"Plan a {days}-day trip to {destination} starting {start_date.isoformat()}. "
            f"Travel style: {travel_style}. Budget: {budget_level}. "
            f"Interests: {', '.join(interests) if interests else 'general sightseeing'}. "
            f"Dietary preferences: {', '.join(dietary_preferences) if dietary_preferences else 'none'}. "
            f"Please search for real POIs using the available tools, check the weather, "
            f"and create a detailed day-by-day itinerary with estimated costs."
        )

        # 步骤 4：执行 Agent
        from app.agent.react import AgentResult

        result: AgentResult = await self.agent.execute(
            user_input=user_input,
            system_prompt=system_prompt,
            conversation_history=context.conversation_history,
            stream_handler=stream_handler,
        )

        # 步骤 5：保存到记忆系统
        await self.memory.save_interaction(
            user_id=user_id,
            session_id=session_id,
            user_message=user_input,
            assistant_message=result.content,
            tool_calls=result.tool_calls,
            llm=self.agent.llm,
        )

        # 步骤 6：构建响应
        return {
            "trip_id": session_id,
            "destination": destination,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat() if isinstance(end_date, date) else end_date,
            "days": days,
            "content": result.content,
            "tool_calls_made": [
                {"tool": tc["tool"], "args_summary": str(tc.get("arguments", {}))[:100]}
                for tc in result.tool_calls
            ],
            "iterations": result.iterations,
            "usage": {
                "input_tokens": result.usage.input_tokens if result.usage else 0,
                "output_tokens": result.usage.output_tokens if result.usage else 0,
            } if result.usage else None,
        }

    def _format_tools_description(self) -> str:
        """构建格式化的可用工具列表，用于系统提示词。"""
        tools = self.tool_registry.list_tools()
        if not tools:
            return "No tools available."

        lines = []
        for t in tools:
            params = t.get("parameters", {})
            props = params.get("properties", {})
            required = params.get("required", [])
            param_desc = ", ".join(
                f"{k}{'*' if k in required else ''}" for k in props.keys()
            )
            lines.append(f"- **{t['name']}**: {t['description']}")
            if param_desc:
                lines.append(f"  Parameters: {param_desc}")
        return "\n".join(lines)
