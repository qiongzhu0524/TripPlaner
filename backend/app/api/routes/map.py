"""地图/POI/天气 API 端点 — 不通过 Agent 直接访问。"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    POISearchResponse,
    POIItem,
    WeatherResponse,
    WeatherForecastItem,
    RouteRequest,
    RouteResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/poi/search", response_model=POISearchResponse)
async def search_poi(
    keywords: str = Query(..., description="搜索关键词"),
    city: str = Query(..., description="城市名称"),
    limit: int = Query(default=10, ge=1, le=50),
) -> POISearchResponse:
    """通过高德 API 搜索 POI（兴趣点）。

    直接调用工具函数 — 不经过 Agent。
    """
    from app.tools.local.amap_direct import search_poi as _search_poi

    result = await _search_poi(keywords=keywords, city=city, limit=limit)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    pois = [
        POIItem(
            name=p.get("name", ""),
            address=p.get("address", ""),
            lat=float(p.get("location", "0,0").split(",")[0] or 0),
            lng=float(p.get("location", "0,0").split(",")[1] or 0),
            category=p.get("category", ""),
            rating=p.get("rating", ""),
        )
        for p in result.get("results", [])
    ]

    return POISearchResponse(results=pois, total=result.get("total", 0))


@router.get("/weather", response_model=WeatherResponse)
async def get_weather(
    city: str = Query(..., description="城市名称"),
) -> WeatherResponse:
    """通过高德 API 查询天气预报。"""
    from app.tools.local.amap_direct import query_weather as _query_weather

    result = await _query_weather(city=city)

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    forecasts = [
        WeatherForecastItem(
            date=f.get("date", ""),
            temperature_high=float(f.get("day_temp", 0)),
            temperature_low=float(f.get("night_temp", 0)),
            weather=f"{f.get('day_weather', '')}/{f.get('night_weather', '')}",
            wind=f.get("day_wind", ""),
            humidity=0,
        )
        for f in result.get("forecasts", [])
    ]

    return WeatherResponse(city=city, forecasts=forecasts)


@router.post("/route", response_model=RouteResponse)
async def plan_route(req: RouteRequest) -> RouteResponse:
    """规划两个地点之间的路线。"""
    from app.tools.local.amap_direct import (
        get_driving_route,
        get_transit_route,
        get_walking_route,
    )

    if req.mode == "driving":
        result = await get_driving_route(
            origin=req.origin, destination=req.destination, city=req.city
        )
    elif req.mode == "transit":
        result = await get_transit_route(
            origin=req.origin, destination=req.destination, city=req.city
        )
    elif req.mode == "walking":
        result = await get_walking_route(origin=req.origin, destination=req.destination)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {req.mode}")

    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return RouteResponse(
        distance=result.get("distance", ""),
        duration=result.get("duration", ""),
        steps=[s.get("instruction", "") for s in result.get("steps", [])],
    )
