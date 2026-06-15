"""API 请求/响应的 Pydantic 模型。"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TripPlanRequest(BaseModel):
    """生成行程规划的请求。"""

    user_id: str = Field(..., description="用于记忆/个性化的用户标识符")
    destination: str = Field(..., description="目的地城市或地区")
    start_date: date = Field(..., description="行程开始日期")
    days: int = Field(default=3, ge=1, le=30, description="旅行天数")
    travel_style: Optional[Literal["relaxed", "balanced", "intensive"]] = "balanced"
    budget_level: Optional[Literal["budget", "midrange", "luxury"]] = "midrange"
    dietary_preferences: Optional[list[str]] = None
    interests: Optional[list[str]] = None


class Activity(BaseModel):
    """一天行程中的单个活动。"""

    name: str
    location: str
    lat: float
    lng: float
    time_slot: str
    duration_hours: float
    estimated_cost: float
    description: str


class MealSuggestion(BaseModel):
    """餐饮推荐。"""

    type: Literal["breakfast", "lunch", "dinner"]
    restaurant_name: str
    cuisine: str
    estimated_cost: float
    address: str = ""


class DayPlan(BaseModel):
    """单日行程安排。"""

    day: int
    date: str
    activities: list[Activity] = Field(default_factory=list)
    meals: list[MealSuggestion] = Field(default_factory=list)
    accommodation: Optional[str] = None
    weather: Optional[str] = None


class TripPlanResponse(BaseModel):
    """完整的行程规划响应。"""

    trip_id: str
    destination: str
    days: list[DayPlan] = Field(default_factory=list)
    total_estimated_cost: float = 0.0
    tips: list[str] = Field(default_factory=list)


class POISearchRequest(BaseModel):
    """POI 搜索请求。"""

    keywords: str = Field(..., description="搜索关键词（例如：'景点'、'餐厅'）")
    city: str = Field(..., description="城市名称")
    limit: int = Field(default=10, ge=1, le=50)


class POISearchResponse(BaseModel):
    """POI 搜索响应。"""

    results: list["POIItem"] = Field(default_factory=list)
    total: int = 0


class POIItem(BaseModel):
    """单个兴趣点（POI）。"""

    name: str
    address: str
    lat: float
    lng: float
    category: str = ""
    rating: str = ""


class WeatherRequest(BaseModel):
    """天气查询请求。"""

    city: str


class WeatherResponse(BaseModel):
    """天气查询响应。"""

    city: str
    forecasts: list["WeatherForecastItem"] = Field(default_factory=list)


class WeatherForecastItem(BaseModel):
    """单日天气预报。"""

    date: str
    temperature_high: float
    temperature_low: float
    weather: str
    wind: str
    humidity: int


class RouteRequest(BaseModel):
    """路线规划请求。"""

    origin: str
    destination: str
    city: str = ""
    mode: Literal["driving", "walking", "transit"] = "driving"


class RouteResponse(BaseModel):
    """路线规划响应。"""

    distance: str
    duration: str
    steps: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """向 Agent 发送的聊天请求。"""

    user_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    """Agent 的聊天响应。"""

    session_id: str
    response: str
    tool_calls: list[dict] = Field(default_factory=list)
