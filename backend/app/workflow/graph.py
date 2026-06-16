"""LangGraph StateGraph 构建器 — 行程规划 DAG。

图结构：
    load_profile → prepare_prompt → execute_agent → extract_output → save_memory → END

其中 execute_agent 是 create_react_agent 子图（内部有 LLM ↔ Tools 循环）。
"""

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from app.workflow.state import TripPlanState
from app.workflow.nodes import (
    load_profile_node,
    prepare_prompt_node,
    save_memory_node,
    extract_final_output_node,
)

logger = logging.getLogger(__name__)

# 模块级单例（在 lifespan 中设置）
_trip_planning_graph: CompiledStateGraph | None = None


def build_trip_planning_graph(
    model: BaseChatModel,
    tools: list[BaseTool],
    max_iterations: int = 10,
) -> CompiledStateGraph:
    """构建并编译行程规划 LangGraph StateGraph。

    参数：
        model: LangChain BaseChatModel 实例。
        tools: LangChain BaseTool 列表。
        max_iterations: ReAct Agent 最大迭代次数。

    返回：
        编译后的 CompiledStateGraph，可调用 .ainvoke() / .astream_events()。
    """
    # ---- 创建 ReAct Agent 子图（替代 execute_agent 节点） ----
    model_with_tools = model.bind_tools(tools)
    react_agent = create_react_agent(
        model=model_with_tools,
        tools=tools,
    )

    # ---- 构建主图 ----
    workflow = StateGraph(TripPlanState)

    # 添加节点
    workflow.add_node("load_profile", load_profile_node)
    workflow.add_node("prepare_prompt", prepare_prompt_node)
    workflow.add_node("execute_agent", react_agent)  # 嵌套子图
    workflow.add_node("extract_output", extract_final_output_node)
    workflow.add_node("save_memory", save_memory_node)

    # 连接边
    workflow.add_edge(START, "load_profile")
    workflow.add_edge("load_profile", "prepare_prompt")
    workflow.add_edge("prepare_prompt", "execute_agent")
    workflow.add_edge("execute_agent", "extract_output")
    workflow.add_edge("extract_output", "save_memory")
    workflow.add_edge("save_memory", END)

    # 编译（recursion_limit 控制 Agent 最大迭代次数）
    compiled = workflow.compile()

    logger.info(
        f"Trip planning graph compiled: 5 nodes, "
        f"recursion_limit={max_iterations * 2 + 5}"
    )
    return compiled


def get_trip_planning_graph() -> CompiledStateGraph | None:
    """获取编译后的图单例。"""
    global _trip_planning_graph
    return _trip_planning_graph


def set_trip_planning_graph(graph: CompiledStateGraph) -> None:
    """设置编译后的图单例（在 lifespan 中调用）。"""
    global _trip_planning_graph
    _trip_planning_graph = graph
