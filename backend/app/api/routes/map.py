"""地图/POI/天气 API 端点 — 不通过 Agent 直接访问。"""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    POISearchRequest,
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

    直接调用工具 — 不经过 Agent。
    """
    from app.tools.local.amap_direct import AmapTextSearchTool

    tool = AmapTextSearchTool()
    result = await tool.execute(keywords=keywords, city=city, limit=limit)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    data = result.data or {}
    pois = [
        POIItem(
            name=p.get("name", ""),
            address=p.get("address", ""),
            lat=float(p.get("location", "0,0").split(",")[0] or 0),
            lng=float(p.get("location", "0,0").split(",")[1] or 0),
            category=p.get("category", ""),
            rating=p.get("rating", ""),
        )
        for p in data.get("results", [])
    ]

    return POISearchResponse(results=pois, total=data.get("total", 0))


@router.get("/weather", response_model=WeatherResponse)
async def get_weather(
    city: str = Query(..., description="城市名称"),
) -> WeatherResponse:
    """通过高德 API 查询天气预报。"""
    from app.tools.local.amap_direct import AmapWeatherTool

    tool = AmapWeatherTool()
    result = await tool.execute(city=city)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    data = result.data or {}
    forecasts = [
        WeatherForecastItem(
            date=f.get("date", ""),
            temperature_high=float(f.get("day_temp", 0)),
            temperature_low=float(f.get("night_temp", 0)),
            weather=f"{f.get('day_weather', '')}/{f.get('night_weather', '')}",
            wind=f.get("day_wind", ""),
            humidity=0,
        )
        for f in data.get("forecasts", [])
    ]

    return WeatherResponse(city=city, forecasts=forecasts)


@router.post("/route", response_model=RouteResponse)
async def plan_route(req: RouteRequest) -> RouteResponse:
    """规划两个地点之间的路线。"""
    from app.tools.local.amap_direct import (
        AmapDirectionDrivingTool,
        AmapDirectionTransitTool,
        AmapDirectionWalkingTool,
    )

    tool_map = {
        "driving": AmapDirectionDrivingTool(),
        "transit": AmapDirectionTransitTool(),
        "walking": AmapDirectionWalkingTool(),
    }

    tool = tool_map.get(req.mode)
    if not tool:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {req.mode}")

    kwargs = {"origin": req.origin, "destination": req.destination}
    if req.mode == "transit":
        kwargs["city"] = req.city

    result = await tool.execute(**kwargs)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    data = result.data or {}
    return RouteResponse(
        distance=data.get("distance", ""),
        duration=data.get("duration", ""),
        steps=[s.get("instruction", "") for s in data.get("steps", [])],
    )
