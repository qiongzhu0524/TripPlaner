"""旅行规划的预定义工作流。

TRIP_PLANNING_WORKFLOW:
    生成完整旅行计划的主工作流。
    步骤：
    1. load_user_profile — 从长期记忆中加载用户偏好
    2. analyze_destination — 代理分析目的地和旅行上下文
    3. search_pois — 并行搜索景点、餐厅、酒店
    4. check_weather — 查询旅行日期的天气预报
    5. generate_itinerary — 代理将所有信息综合为逐日计划
    6. save_memory — 将交互持久化到记忆
"""

from app.workflow.schemas import Step, StepType, Workflow

TRIP_PLANNING_WORKFLOW = Workflow(
    name="trip_planning",
    description="Generate a complete, personalized multi-day travel itinerary",
    steps=[
        Step(
            name="load_user_profile",
            type=StepType.MEMORY,
            config={"action": "load"},
        ),
        Step(
            name="analyze_destination",
            type=StepType.AGENT,
            config={
                "system_prompt": (
                    "You are a travel planning assistant. Analyze the destination "
                    "and suggest an overall trip structure.\n\n"
                    "Destination: {destination}\n"
                    "Dates: {start_date} to {end_date} ({days} days)\n"
                    "Travel style: {travel_style}\n"
                    "Budget: {budget_level}\n"
                    "Interests: {interests}\n"
                    "User profile: {user_profile_summary}\n\n"
                    "Provide a brief analysis of:\n"
                    "1. The best neighborhood/area to stay\n"
                    "2. Key attractions that match the user's interests\n"
                    "3. Recommended daily structure (morning/afternoon/evening)\n"
                    "4. Transportation recommendations\n"
                    "5. Any seasonal considerations"
                ),
                "user_input": (
                    "Analyze the trip to {destination} for {days} days starting {start_date}. "
                    "User preferences: {travel_style} style, {budget_level} budget, "
                    "interests in {interests}."
                ),
            },
            depends_on=["load_user_profile"],
        ),
        Step(
            name="search_pois",
            type=StepType.PARALLEL,
            config={
                "sub_steps": [
                    {
                        "name": "attractions",
                        "type": "tool",
                        "config": {
                            "tool_name": "maps_text_search",
                            "arguments": {
                                "keywords": "景点",
                                "city": "{destination}",
                                "limit": 15,
                            },
                        },
                    },
                    {
                        "name": "restaurants",
                        "type": "tool",
                        "config": {
                            "tool_name": "maps_text_search",
                            "arguments": {
                                "keywords": "美食",
                                "city": "{destination}",
                                "limit": 15,
                            },
                        },
                    },
                    {
                        "name": "hotels",
                        "type": "tool",
                        "config": {
                            "tool_name": "maps_text_search",
                            "arguments": {
                                "keywords": "酒店",
                                "city": "{destination}",
                                "limit": 10,
                            },
                        },
                    },
                ],
            },
            depends_on=["analyze_destination"],
        ),
        Step(
            name="check_weather",
            type=StepType.TOOL,
            config={
                "tool_name": "maps_weather",
                "arguments": {"city": "{destination}"},
            },
        ),
        Step(
            name="generate_itinerary",
            type=StepType.AGENT,
            config={
                "system_prompt": (
                    "You are an expert travel planner. Generate a detailed, "
                    "day-by-day itinerary based on the research results provided.\n\n"
                    "## Research Results\n"
                    "Destination Analysis: {analyze_destination}\n"
                    "POI Search Results: {search_pois}\n"
                    "Weather Forecast: {check_weather}\n\n"
                    "## Trip Parameters\n"
                    "Destination: {destination}\n"
                    "Dates: {start_date} to {end_date} ({days} days)\n"
                    "Travel style: {travel_style}\n"
                    "Budget: {budget_level}\n"
                    "Interests: {interests}\n\n"
                    "## Requirements\n"
                    "1. Create a complete day-by-day itinerary\n"
                    "2. For each day, provide:\n"
                    "   - Morning activity (with specific POI names)\n"
                    "   - Lunch recommendation\n"
                    "   - Afternoon activity\n"
                    "   - Dinner recommendation\n"
                    "   - Evening activity (optional)\n"
                    "   - Estimated costs\n"
                    "3. Consider weather for outdoor vs indoor activities\n"
                    "4. Route between locations should be realistic\n"
                    "5. Include practical tips (what to wear, what to bring, local customs)\n"
                    "6. Mark the total estimated cost for the trip"
                ),
                "user_input": (
                    "Generate a {days}-day itinerary for {destination} "
                    "from {start_date} to {end_date}.\n"
                    "Style: {travel_style}, Budget: {budget_level}, Interests: {interests}"
                ),
            },
            depends_on=["search_pois", "check_weather"],
        ),
        Step(
            name="save_memory",
            type=StepType.MEMORY,
            config={"action": "save"},
            depends_on=["generate_itinerary"],
        ),
    ],
)
