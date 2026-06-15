"""行程规划领域模型：POI、WeatherForecast。"""

from dataclasses import dataclass


@dataclass
class POI:
    """兴趣点（景点/餐厅/酒店）。"""

    name: str
    address: str
    location: tuple[float, float]
    category: str = ""
    rating: float = 0.0
    cost_level: str = ""
    opening_hours: str = ""
    description: str = ""


@dataclass
class WeatherForecast:
    """单日天气预报。"""

    date: str
    temperature_high: float
    temperature_low: float
    weather: str
    wind: str
    humidity: int
