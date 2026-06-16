"""LangGraph StateGraph 状态定义。

TripPlanState TypedDict 定义了行程规划图的所有状态字段。
LangGraph 通过 add_messages reducer 自动合并消息列表。
"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class TripPlanState(TypedDict, total=False):
    """行程规划 LangGraph 图的状态。

    字段分为：
    - 输入：由路由处理器设置
    - 中间结果：由各节点计算
    - 最终输出：由最后一个节点设置
    """

    # ---- 输入 ----
    user_id: str
    session_id: str
    destination: str
    start_date: str
    end_date: str
    days: int
    travel_style: str
    budget_level: str
    interests: list[str]
    dietary_preferences: list[str]

    # ---- 中间结果 ----
    user_profile: dict
    user_profile_summary: str
    conversation_history: list[dict]
    system_prompt: str
    tools_description: str

    # ---- ReAct Agent 消息流（add_messages 自动追加，不覆盖） ----
    messages: Annotated[list[BaseMessage], add_messages]

    # ---- 最终输出 ----
    final_response: str
    tool_calls_made: list[dict]
    iterations: int
    usage: dict
