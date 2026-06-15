"""路线优化工具。

使用简单的最近邻TSP启发式算法对POI进行排序，以获得最佳的日间路线。
生产环境中应替换为OR-Tools或合适的TSP求解器。
"""

import logging
import math
from typing import Any

from app.tools.base import ToolProtocol, ToolResult

logger = logging.getLogger(__name__)


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两个坐标之间的千米距离（Haversine公式）。"""
    R = 6371.0  # 地球半径（千米）
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RouteOptimizerTool(ToolProtocol):
    """优化多个POI的访问顺序以最小化行程距离。

    使用最近邻启发式算法（贪心TSP）。接受包含名称和坐标的POI列表，
    以最优访问顺序返回。
    """

    name = "route_optimizer"
    description = (
        "优化多个POI的访问顺序以最小化总行程距离。"
        "输入一组POI（每个包含name、lat、lng），返回最优访问顺序和估算总距离。"
        "使用最近邻启发式算法。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "pois": {
                "type": "array",
                "description": "待优化的POI列表",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "lat": {"type": "number"},
                        "lng": {"type": "number"},
                    },
                    "required": ["name", "lat", "lng"],
                },
            },
            "start_point": {
                "type": "object",
                "description": "起点（通常是酒店），可选",
                "properties": {
                    "name": {"type": "string"},
                    "lat": {"type": "number"},
                    "lng": {"type": "number"},
                },
            },
        },
        "required": ["pois"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        pois = kwargs.get("pois", [])
        start_point = kwargs.get("start_point")

        if len(pois) < 2:
            return ToolResult(
                success=True,
                data={
                    "ordered_pois": pois,
                    "total_distance_km": 0.0,
                    "message": "Less than 2 POIs, no optimization needed.",
                },
            )

        # 构建距离矩阵
        all_points = pois[:]
        start_idx = None
        if start_point:
            all_points = [start_point] + all_points
            start_idx = 0

        n = len(all_points)
        distances = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    distances[i][j] = _haversine_distance(
                        all_points[i]["lat"], all_points[i]["lng"],
                        all_points[j]["lat"], all_points[j]["lng"],
                    )

        # 最近邻贪心TSP算法
        visited = [False] * n
        order = []

        current = start_idx if start_idx is not None else 0
        visited[current] = True
        order.append(current)
        total_distance = 0.0

        for _ in range(n - 1):
            # 查找最近的未访问邻接点
            nearest = None
            min_dist = float("inf")
            for j in range(n):
                if not visited[j] and distances[current][j] < min_dist:
                    min_dist = distances[current][j]
                    nearest = j
            if nearest is not None:
                visited[nearest] = True
                order.append(nearest)
                total_distance += min_dist
                current = nearest

        # 如果指定了起点，添加返回起点的距离
        if start_idx is not None:
            total_distance += distances[current][start_idx]

        # 构建排序后的结果
        ordered_pois = []
        for idx in order:
            if start_idx is not None and idx == start_idx:
                continue  # 在输出中跳过起点
            ordered_pois.append({
                "name": all_points[idx]["name"],
                "lat": all_points[idx]["lat"],
                "lng": all_points[idx]["lng"],
            })

        return ToolResult(
            success=True,
            data={
                "ordered_pois": ordered_pois,
                "total_distance_km": round(total_distance, 2),
                "message": f"Optimized route: {len(ordered_pois)} POIs, ~{total_distance:.1f}km",
            },
        )
