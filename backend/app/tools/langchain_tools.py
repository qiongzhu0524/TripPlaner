"""将所有本地工具包装为 LangChain StructuredTool，供 LangGraph 使用。

每个工具函数从 app/tools/local/ 导入，用 StructuredTool.from_function() 包装，
附加 Pydantic args_schema 和描述。
"""

from langchain_core.tools import StructuredTool

from app.tools.local.amap_direct import (
    TextSearchInput,
    WeatherInput,
    DrivingRouteInput,
    TransitRouteInput,
    WalkingRouteInput,
    search_poi,
    query_weather,
    get_driving_route,
    get_transit_route,
    get_walking_route,
)
from app.tools.local.currency import CurrencyConvertInput, currency_convert
from app.tools.local.date_utils import DateRangeInput, date_range
from app.tools.local.route_optimizer import RouteOptimizerInput, route_optimizer


def create_all_tools() -> list[StructuredTool]:
    """创建所有本地工具为 LangChain StructuredTool 列表。

    返回：
        准备好用于 LangGraph create_react_agent 的 BaseTool 实例列表。
    """
    tools: list[StructuredTool] = []

    # ---- 高德地图工具 (5) ----
    tools.append(StructuredTool.from_function(
        name="maps_text_search",
        description=(
            "搜索指定城市的 POI（景点、餐厅、酒店等）。"
            "使用高德地图 API 进行文本搜索，返回名称、地址、坐标和评分。"
        ),
        args_schema=TextSearchInput,
        coroutine=search_poi,
    ))

    tools.append(StructuredTool.from_function(
        name="maps_weather",
        description=(
            "查询指定城市的天气预报。返回未来几天的天气、温度、风力、湿度等信息。"
            "使用高德地图气象 API。"
        ),
        args_schema=WeatherInput,
        coroutine=query_weather,
    ))

    tools.append(StructuredTool.from_function(
        name="maps_direction_driving",
        description=(
            "规划两点之间的驾车路线。返回距离、预计时间和导航步骤。"
            "起点和终点可以是地址或坐标（如'116.481028,39.989643'）。"
        ),
        args_schema=DrivingRouteInput,
        coroutine=get_driving_route,
    ))

    tools.append(StructuredTool.from_function(
        name="maps_direction_transit",
        description=(
            "规划两点之间的公共交通路线（公交、地铁）。返回总距离、预计时间和换乘方案。"
        ),
        args_schema=TransitRouteInput,
        coroutine=get_transit_route,
    ))

    tools.append(StructuredTool.from_function(
        name="maps_direction_walking",
        description="规划两点之间的步行路线。返回距离和预计步行时间。",
        args_schema=WalkingRouteInput,
        coroutine=get_walking_route,
    ))

    # ---- 货币转换 ----
    tools.append(StructuredTool.from_function(
        name="currency_convert",
        description=(
            "货币转换工具。将金额从一种货币转换为另一种货币。"
            "支持CNY/USD/EUR/JPY/KRW/THB/SGD/HKD/GBP等。"
        ),
        args_schema=CurrencyConvertInput,
        coroutine=currency_convert,
    ))

    # ---- 日期工具 ----
    tools.append(StructuredTool.from_function(
        name="date_range",
        description="生成旅行日期范围内的日期列表，每个日期带有星期几。",
        args_schema=DateRangeInput,
        coroutine=date_range,
    ))

    # ---- 路线优化 ----
    tools.append(StructuredTool.from_function(
        name="route_optimizer",
        description=(
            "优化多个 POI 的访问顺序以最小化总行程距离。"
            "输入一组 POI（每个包含 name、lat、lng），返回最优访问顺序和估算总距离。"
            "使用最近邻启发式算法。"
        ),
        args_schema=RouteOptimizerInput,
        coroutine=route_optimizer,
    ))

    return tools
