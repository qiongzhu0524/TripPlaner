"""LangGraph 图节点函数。

每个节点是一个 async 函数，接收 state 并返回状态更新（部分 dict）。
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import ContextBuilder
from app.database import async_session_factory
from app.memory.manager import MemoryManager
from app.workflow.state import TripPlanState

logger = logging.getLogger(__name__)


async def load_profile_node(
    state: TripPlanState, config: RunnableConfig
) -> dict[str, Any]:
    """节点1: 从 MemoryManager 加载用户画像和对话历史。

    输入: user_id, session_id
    输出: user_profile, user_profile_summary, conversation_history
    """
    user_id = state["user_id"]
    session_id = state.get("session_id", f"trip_{uuid.uuid4().hex[:12]}")

    async with async_session_factory() as db:
        memory = MemoryManager(db)
        ctx = await memory.build_context(user_id, session_id)

    profile = ctx.user_profile or {}
    return {
        "session_id": session_id,
        "user_profile": profile,
        "user_profile_summary": profile.get("summary", ""),
        "conversation_history": ctx.conversation_history,
    }


async def prepare_prompt_node(
    state: TripPlanState, config: RunnableConfig
) -> dict[str, Any]:
    """节点2: 构建 System Prompt 和 User Input。

    输入: destination, days, start_date, end_date, travel_style, budget_level,
          interests, dietary_preferences, user_profile_summary, tools_description
    输出: system_prompt, messages (初始用户消息)
    """
    tools_desc = state.get("tools_description", "Various travel planning tools available.")

    system_prompt = ContextBuilder.build_system_prompt(
        tools_description=tools_desc,
        destination=state["destination"],
        start_date=state["start_date"],
        end_date=state.get("end_date", state["start_date"]),
        days=state.get("days", 3),
        travel_style=state.get("travel_style", "balanced"),
        budget_level=state.get("budget_level", "midrange"),
        interests=state.get("interests"),
        user_profile_summary=state.get("user_profile_summary", "No profile data yet."),
        conversation_summary="First planning session for this trip.",
    )

    interests = state.get("interests", [])
    dietary = state.get("dietary_preferences", [])

    user_input = (
        f"Plan a {state.get('days', 3)}-day trip to {state['destination']} "
        f"starting {state['start_date']}. "
        f"Travel style: {state.get('travel_style', 'balanced')}. "
        f"Budget: {state.get('budget_level', 'midrange')}. "
        f"Interests: {', '.join(interests) if interests else 'general sightseeing'}. "
        f"Dietary preferences: {', '.join(dietary) if dietary else 'none'}. "
        f"Please search for real POIs using the available tools, check the weather, "
        f"and create a detailed day-by-day itinerary with estimated costs."
    )

    return {
        "system_prompt": system_prompt,
        "messages": [HumanMessage(content=user_input)],
    }


async def save_memory_node(
    state: TripPlanState, config: RunnableConfig
) -> dict[str, Any]:
    """节点4: 保存交互到记忆系统。

    输入: user_id, session_id, messages, final_response
    输出: (无，副作用)
    """
    user_id = state["user_id"]
    session_id = state["session_id"]

    # 提取用户输入（第一条 HumanMessage）
    messages: list[BaseMessage] = state.get("messages", [])
    user_input = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            user_input = str(msg.content)
            break

    final_response = state.get("final_response", "")
    tool_calls = state.get("tool_calls_made", [])

    # 从 config 获取 LLM（由调用者注入）
    llm = config.get("configurable", {}).get("llm") if config else None

    async with async_session_factory() as db:
        memory = MemoryManager(db)
        await memory.save_interaction(
            user_id=user_id,
            session_id=session_id,
            user_message=user_input,
            assistant_message=final_response,
            tool_calls=tool_calls,
            llm=llm,
        )
        await db.commit()

    logger.info(f"Saved memory for session {session_id[:8]}")
    return {}


def extract_final_output_node(
    state: TripPlanState, config: RunnableConfig
) -> dict[str, Any]:
    """节点3（后处理）: 从 Agent 消息中提取最终输出。

    在 execute_agent 之后运行，解析消息列表提取：
    - final_response: 最后一条 AI 消息的文本内容
    - tool_calls_made: 所有工具调用记录
    - iterations: LLM 调用次数
    - usage: token 用量
    """
    messages: list[BaseMessage] = state.get("messages", [])
    tool_calls_made: list[dict] = []

    final_content = ""
    ai_message_count = 0

    for msg in messages:
        if isinstance(msg, AIMessage):
            ai_message_count += 1
            if msg.content:
                final_content = msg.content
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_made.append({
                        "tool": tc.get("name", ""),
                        "arguments": tc.get("args", {}),
                        "result": "",  # 由后续 ToolMessage 填充
                    })
        elif isinstance(msg, ToolMessage):
            # 将工具结果关联到最近的无结果工具调用
            for tc in reversed(tool_calls_made):
                if not tc.get("result"):
                    tc["result"] = str(msg.content) if msg.content else ""
                    break

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

    return {
        "final_response": final_content,
        "tool_calls_made": tool_calls_made,
        "iterations": ai_message_count,
        "usage": usage,
    }
