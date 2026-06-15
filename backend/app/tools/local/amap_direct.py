"""高德地图直接API工具。

提供通过httpx直接调用高德Web API的工具。
这是"本地"（非MCP）路径——适用于对性能敏感
或MCP服务器不可用的场景。

工具：
- maps_text_search: 按关键词和城市搜索POI
- maps_weather: 查询城市天气预报
- maps_direction_driving: 两地之间的驾车路线
- maps_direction_transit: 公共交通路线
- maps_direction_walking: 步行路线
"""

import logging
import os
from typing import Any

import httpx

from app.config import settings
from app.tools.base import ToolProtocol, ToolResult

logger = logging.getLogger(__name__)

AMAP_BASE_URL = "https://restapi.amap.com/v3"


class AmapTextSearchTool(ToolProtocol):
    """使用高德地图文本搜索API搜索POI（景点/餐厅/酒店）。"""

    name = "maps_text_search"
    description = (
        "搜索指定城市的POI（景点、餐厅、酒店等）。"
        "使用高德地图API进行文本搜索，返回名称、地址、坐标和评分。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "string",
                "description": "搜索关键词，如'景点'、'川菜'、'五星级酒店'",
            },
            "city": {
                "type": "string",
                "description": "城市名称，如'北京'、'上海'",
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量，默认10，最大50",
                "default": 10,
            },
        },
        "required": ["keywords", "city"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        keywords = kwargs.get("keywords", "")
        city = kwargs.get("city", "")
        limit = kwargs.get("limit", 10)

        api_key = settings.amap.api_key or os.getenv("AMAP_API_KEY", "")
        if not api_key:
            return ToolResult(success=False, error="Amap API key not configured")

        params = {
            "key": api_key,
            "keywords": keywords,
            "city": city,
            "offset": min(limit, 50),
            "extensions": "all",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(f"{AMAP_BASE_URL}/place/text", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                logger.error(f"Amap text search failed: {e}")
                return ToolResult(success=False, error=str(e))

        if data.get("status") != "1":
            return ToolResult(success=False, error=data.get("info", "Unknown Amap error"))

        pois = data.get("pois", [])
        results = [
            {
                "name": p.get("name"),
                "address": p.get("address"),
                "location": p.get("location"),
                "category": p.get("type", ""),
                "rating": p.get("biz_ext", {}).get("rating", "N/A"),
                "cost": p.get("biz_ext", {}).get("cost", "N/A"),
            }
            for p in pois
        ]

        return ToolResult(
            success=True,
            data={"results": results, "total": int(data.get("count", 0))},
        )


class AmapWeatherTool(ToolProtocol):
    """通过高德地图天气API查询天气预报。"""

    name = "maps_weather"
    description = (
        "查询指定城市的天气预报。返回未来几天的天气、温度、风力、湿度等信息。"
        "使用高德地图气象API。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称，如'北京'、'上海'",
            },
        },
        "required": ["city"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        city = kwargs.get("city", "")

        api_key = settings.amap.api_key or os.getenv("AMAP_API_KEY", "")
        if not api_key:
            return ToolResult(success=False, error="Amap API key not configured")

        # 第一步：获取城市adcode
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                # 获取城市编码
                resp = await client.get(
                    "https://restapi.amap.com/v3/config/district",
                    params={"key": api_key, "keywords": city, "subdistrict": 0},
                )
                resp.raise_for_status()
                district_data = resp.json()
            except httpx.HTTPError as e:
                return ToolResult(success=False, error=str(e))

        if district_data.get("status") != "1" or not district_data.get("districts"):
            return ToolResult(success=False, error=f"City '{city}' not found in Amap")

        adcode = district_data["districts"][0]["adcode"]

        # 第二步：获取天气
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{AMAP_BASE_URL}/weather/weatherInfo",
                    params={"key": api_key, "city": adcode, "extensions": "all"},
                )
                resp.raise_for_status()
                weather_data = resp.json()
            except httpx.HTTPError as e:
                return ToolResult(success=False, error=str(e))

        if weather_data.get("status") != "1":
            return ToolResult(success=False, error=weather_data.get("info", "Weather query failed"))

        forecasts = weather_data.get("forecasts", [])
        if not forecasts:
            return ToolResult(success=False, error="No forecast data returned")

        casts = forecasts[0].get("casts", [])
        results = [
            {
                "date": c.get("date"),
                "day_weather": c.get("dayweather"),
                "night_weather": c.get("nightweather"),
                "day_temp": c.get("daytemp"),
                "night_temp": c.get("nighttemp"),
                "day_wind": c.get("daywind"),
                "night_wind": c.get("nightwind"),
            }
            for c in casts
        ]

        return ToolResult(
            success=True,
            data={"city": city, "forecasts": results},
        )


class AmapDirectionDrivingTool(ToolProtocol):
    """两地之间的驾车路线。"""

    name = "maps_direction_driving"
    description = (
        "规划两点之间的驾车路线。返回距离、预计时间和导航步骤。"
        "起点和终点可以是地址或坐标（如'116.481028,39.989643'）。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "origin": {"type": "string", "description": "起点地址或坐标"},
            "destination": {"type": "string", "description": "终点地址或坐标"},
            "city": {"type": "string", "description": "城市名称（可选）"},
        },
        "required": ["origin", "destination"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        origin = kwargs.get("origin", "")
        destination = kwargs.get("destination", "")

        api_key = settings.amap.api_key or os.getenv("AMAP_API_KEY", "")
        if not api_key:
            return ToolResult(success=False, error="Amap API key not configured")

        params = {
            "key": api_key,
            "origin": origin,
            "destination": destination,
            "extensions": "all",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(f"{AMAP_BASE_URL}/direction/driving", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                return ToolResult(success=False, error=str(e))

        if data.get("status") != "1":
            return ToolResult(success=False, error=data.get("info", "Route planning failed"))

        route = data.get("route", {})
        paths = route.get("paths", [])
        if not paths:
            return ToolResult(success=False, error="No route found")

        path = paths[0]
        steps = path.get("steps", [])

        return ToolResult(
            success=True,
            data={
                "distance": path.get("distance", "N/A"),
                "duration": path.get("duration", "N/A"),
                "toll_distance": path.get("toll_distance", "0"),
                "steps": [
                    {"instruction": s.get("instruction", ""), "road": s.get("road", "")}
                    for s in steps
                ],
            },
        )


class AmapDirectionTransitTool(ToolProtocol):
    """两地之间的公共交通路线。"""

    name = "maps_direction_transit"
    description = (
        "规划两点之间的公共交通路线（公交、地铁）。返回总距离、预计时间和换乘方案。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "origin": {"type": "string", "description": "起点地址或坐标"},
            "destination": {"type": "string", "description": "终点地址或坐标"},
            "city": {"type": "string", "description": "城市名称"},
        },
        "required": ["origin", "destination", "city"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        origin = kwargs.get("origin", "")
        destination = kwargs.get("destination", "")
        city = kwargs.get("city", "")

        api_key = settings.amap.api_key or os.getenv("AMAP_API_KEY", "")
        if not api_key:
            return ToolResult(success=False, error="Amap API key not configured")

        params = {
            "key": api_key,
            "origin": origin,
            "destination": destination,
            "city": city,
            "extensions": "all",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{AMAP_BASE_URL}/direction/transit/integrated", params=params
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                return ToolResult(success=False, error=str(e))

        if data.get("status") != "1":
            return ToolResult(success=False, error=data.get("info", "Route planning failed"))

        route = data.get("route", {})
        if not route.get("transits"):
            return ToolResult(success=False, error="No transit route found")

        transit = route["transits"][0]
        return ToolResult(
            success=True,
            data={
                "distance": transit.get("distance", "N/A"),
                "duration": transit.get("duration", "N/A"),
                "cost": transit.get("cost", "N/A"),
                "walking_distance": transit.get("walking_distance", "N/A"),
                "segments": [
                    {
                        "type": s.get("bus", {}).get("type", "walking"),
                        "name": s.get("bus", {}).get("buslines", [{}])[0].get("name", ""),
                        "stops": s.get("bus", {}).get("buslines", [{}])[0].get("via_stops", 0),
                    }
                    for s in transit.get("segments", [])
                ],
            },
        )


class AmapDirectionWalkingTool(ToolProtocol):
    """两地之间的步行路线。"""

    name = "maps_direction_walking"
    description = "规划两点之间的步行路线。返回距离和预计步行时间。"
    parameters = {
        "type": "object",
        "properties": {
            "origin": {"type": "string", "description": "起点地址或坐标"},
            "destination": {"type": "string", "description": "终点地址或坐标"},
        },
        "required": ["origin", "destination"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        origin = kwargs.get("origin", "")
        destination = kwargs.get("destination", "")

        api_key = settings.amap.api_key or os.getenv("AMAP_API_KEY", "")
        if not api_key:
            return ToolResult(success=False, error="Amap API key not configured")

        params = {"key": api_key, "origin": origin, "destination": destination}

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(f"{AMAP_BASE_URL}/direction/walking", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                return ToolResult(success=False, error=str(e))

        if data.get("status") != "1":
            return ToolResult(success=False, error=data.get("info", "Route planning failed"))

        route = data.get("route", {})
        paths = route.get("paths", [])
        if not paths:
            return ToolResult(success=False, error="No walking route found")

        path = paths[0]
        steps = path.get("steps", [])

        return ToolResult(
            success=True,
            data={
                "distance": path.get("distance", "N/A"),
                "duration": path.get("duration", "N/A"),
                "steps": [
                    {"instruction": s.get("instruction", ""), "road": s.get("road", "")}
                    for s in steps
                ],
            },
        )
