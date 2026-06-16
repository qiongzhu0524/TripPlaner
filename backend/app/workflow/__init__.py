"""LangGraph 工作流 — 行程规划 DAG。

基于 LangGraph StateGraph，替代旧的 WorkflowEngine + 手动 TripService 编排。

用法：
    from app.workflow.graph import build_trip_planning_graph
    graph = build_trip_planning_graph()
    result = await graph.ainvoke(initial_state)
"""

from app.workflow.graph import build_trip_planning_graph

__all__ = ["build_trip_planning_graph"]
