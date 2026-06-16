"""路线优化工具。

使用简单的最近邻 TSP 启发式算法对 POI 进行排序，以获得最佳的日间路线。
"""

import logging
import math
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两个坐标之间的千米距离（Haversine 公式）。"""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class POIItem(BaseModel):
    """单个 POI。"""

    name: str
    lat: float
    lng: float


class StartPoint(BaseModel):
    """起点。"""

    name: str
    lat: float
    lng: float


class RouteOptimizerInput(BaseModel):
    """路线优化参数。"""

    pois: list[POIItem] = Field(description="待优化的 POI 列表")
    start_point: StartPoint | None = Field(
        default=None, description="起点（通常是酒店），可选"
    )


async def route_optimizer(pois: list[dict], start_point: dict | None = None) -> dict:
    """优化多个 POI 的访问顺序以最小化总行程距离。

    使用最近邻启发式算法（贪心 TSP）。
    """
    if len(pois) < 2:
        return {
            "ordered_pois": pois,
            "total_distance_km": 0.0,
            "message": "Less than 2 POIs, no optimization needed.",
        }

    # 构建距离矩阵
    all_points = list(pois)
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

    # 最近邻贪心 TSP 算法
    visited = [False] * n
    order = []

    current = start_idx if start_idx is not None else 0
    visited[current] = True
    order.append(current)
    total_distance = 0.0

    for _ in range(n - 1):
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

    if start_idx is not None:
        total_distance += distances[current][start_idx]

    ordered_pois = []
    for idx in order:
        if start_idx is not None and idx == start_idx:
            continue
        ordered_pois.append({
            "name": all_points[idx]["name"],
            "lat": all_points[idx]["lat"],
            "lng": all_points[idx]["lng"],
        })

    return {
        "ordered_pois": ordered_pois,
        "total_distance_km": round(total_distance, 2),
        "message": f"Optimized route: {len(ordered_pois)} POIs, ~{total_distance:.1f}km",
    }
