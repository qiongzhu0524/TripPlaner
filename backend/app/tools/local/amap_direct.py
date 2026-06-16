"""高德地图直接 API 工具函数。

提供通过 httpx 直接调用高德 Web API 的工具函数。
这是"本地"（非 MCP）路径。

工具函数：
- search_poi: 按关键词和城市搜索 POI
- query_weather: 查询城市天气预报
- get_driving_route: 两地之间的驾车路线
- get_transit_route: 公共交通路线
- get_walking_route: 步行路线
"""

import logging
import os

import httpx
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

AMAP_BASE_URL = "https://restapi.amap.com/v3"


# ---- Pydantic 参数模型 ----

class TextSearchInput(BaseModel):
    """POI 文本搜索参数。"""

    keywords: str = Field(description="搜索关键词，如'景点'、'川菜'、'五星级酒店'")
    city: str = Field(description="城市名称，如'北京'、'上海'")
    limit: int = Field(default=10, description="返回结果数量，默认10，最大50")


class WeatherInput(BaseModel):
    """天气查询参数。"""

    city: str = Field(description="城市名称，如'北京'、'上海'")


class DrivingRouteInput(BaseModel):
    """驾车路线参数。"""

    origin: str = Field(description="起点地址或坐标")
    destination: str = Field(description="终点地址或坐标")
    city: str = Field(default="", description="城市名称（可选）")


class TransitRouteInput(BaseModel):
    """公共交通路线参数。"""

    origin: str = Field(description="起点地址或坐标")
    destination: str = Field(description="终点地址或坐标")
    city: str = Field(description="城市名称")


class WalkingRouteInput(BaseModel):
    """步行路线参数。"""

    origin: str = Field(description="起点地址或坐标")
    destination: str = Field(description="终点地址或坐标")


# ---- 工具函数 ----

async def _get_api_key() -> str:
    """获取高德 API key。"""
    key = settings.amap.api_key or os.getenv("AMAP_API_KEY", "")
    if not key:
        raise ValueError("Amap API key not configured")
    return key


async def search_poi(keywords: str, city: str, limit: int = 10) -> dict:
    """使用高德地图文本搜索 API 搜索 POI（景点/餐厅/酒店）。

    返回名称、地址、坐标和评分。
    """
    api_key = await _get_api_key()
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
            return {"error": str(e)}

    if data.get("status") != "1":
        return {"error": data.get("info", "Unknown Amap error")}

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
    return {"results": results, "total": int(data.get("count", 0))}


async def query_weather(city: str) -> dict:
    """通过高德地图天气 API 查询天气预报。

    返回未来几天的天气、温度、风力、湿度等信息。
    """
    api_key = await _get_api_key()

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 第一步：获取城市 adcode
        try:
            resp = await client.get(
                "https://restapi.amap.com/v3/config/district",
                params={"key": api_key, "keywords": city, "subdistrict": 0},
            )
            resp.raise_for_status()
            district_data = resp.json()
        except httpx.HTTPError as e:
            return {"error": str(e)}

    if district_data.get("status") != "1" or not district_data.get("districts"):
        return {"error": f"City '{city}' not found in Amap"}

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
            return {"error": str(e)}

    if weather_data.get("status") != "1":
        return {"error": weather_data.get("info", "Weather query failed")}

    forecasts = weather_data.get("forecasts", [])
    if not forecasts:
        return {"error": "No forecast data returned"}

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
    return {"city": city, "forecasts": results}


async def get_driving_route(origin: str, destination: str, city: str = "") -> dict:
    """规划两点之间的驾车路线。返回距离、预计时间和导航步骤。"""
    api_key = await _get_api_key()
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
            return {"error": str(e)}

    if data.get("status") != "1":
        return {"error": data.get("info", "Route planning failed")}

    route = data.get("route", {})
    paths = route.get("paths", [])
    if not paths:
        return {"error": "No route found"}

    path = paths[0]
    steps = path.get("steps", [])
    return {
        "distance": path.get("distance", "N/A"),
        "duration": path.get("duration", "N/A"),
        "toll_distance": path.get("toll_distance", "0"),
        "steps": [
            {"instruction": s.get("instruction", ""), "road": s.get("road", "")}
            for s in steps
        ],
    }


async def get_transit_route(origin: str, destination: str, city: str) -> dict:
    """规划两点之间的公共交通路线（公交、地铁）。"""
    api_key = await _get_api_key()
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
            return {"error": str(e)}

    if data.get("status") != "1":
        return {"error": data.get("info", "Route planning failed")}

    route = data.get("route", {})
    if not route.get("transits"):
        return {"error": "No transit route found"}

    transit = route["transits"][0]
    return {
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
    }


async def get_walking_route(origin: str, destination: str) -> dict:
    """规划两点之间的步行路线。返回距离和预计步行时间。"""
    api_key = await _get_api_key()
    params = {"key": api_key, "origin": origin, "destination": destination}

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{AMAP_BASE_URL}/direction/walking", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            return {"error": str(e)}

    if data.get("status") != "1":
        return {"error": data.get("info", "Route planning failed")}

    route = data.get("route", {})
    paths = route.get("paths", [])
    if not paths:
        return {"error": "No walking route found"}

    path = paths[0]
    steps = path.get("steps", [])
    return {
        "distance": path.get("distance", "N/A"),
        "duration": path.get("duration", "N/A"),
        "steps": [
            {"instruction": s.get("instruction", ""), "road": s.get("road", "")}
            for s in steps
        ],
    }
