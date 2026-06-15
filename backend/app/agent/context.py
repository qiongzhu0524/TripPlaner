"""ContextBuilder: 为每次 agent 调用组装系统提示词和消息列表。

注入内容：
- 工具描述（来自注册表）
- 用户画像摘要（来自长期记忆）
- 对话摘要（来自短期记忆）
- 旅行参数（目的地、日期等）
"""

from datetime import datetime, timezone

SYSTEM_PROMPT_TEMPLATE = """你是一位专业的旅行规划助手，帮助用户创建详细且个性化的旅行行程。

## 可用工具
{tools_description}

## 用户画像
{user_profile_summary}

## 对话上下文
{conversation_summary}

## 当前规划参数
- 当前日期：{current_date}
- 目的地：{destination}
- 旅行日期：{start_date} 至 {end_date}
- 行程时长：{days} 天
- 旅行风格：{travel_style}
- 预算水平：{budget_level}
- 兴趣爱好：{interests}

## 指导原则
1. 在推荐具体地点之前，务必使用 maps_text_search 搜索真实的兴趣点(POI)。
2. 务必使用 maps_weather 查询旅行日期的天气情况，以便提供合适的建议。
3. 考虑地点之间的距离和交通时间，规划切实可行的路线。
4. 充分考虑用户的偏好及饮食要求。
5. 尽可能为每项活动和餐食提供预估费用。
6. 将最终行程以清晰的天数结构呈现，并包含具体时间段安排。
7. 提供关于交通、当地习俗和必尝美食的实用提示。
8. 如果用户的预算水平为“经济型”，优先推荐免费或低成本的景点。
"""


class ContextBuilder:
    """构建完整的上下文(system prompt + user prompt)给agent"""

    @staticmethod
    def build_system_prompt(
        tools_description: str,
        destination: str,
        start_date: str,
        end_date: str,
        days: int = 3,
        travel_style: str = "balanced",
        budget_level: str = "midrange",
        interests: list[str] | None = None,
        user_profile_summary: str = "No profile data yet.",
        conversation_summary: str = "No prior conversation.",
    ) -> str:
        """构建系统提示词，注入所有上下文信息。

        Args:
            tools_description: 来自 ToolRegistry 的可用工具格式化列表。
            destination: 旅行目的地。
            start_date: 旅行开始日期字符串。
            end_date: 旅行结束日期字符串。
            days: 旅行天数。
            travel_style: relaxed / balanced / intensive（休闲 / 均衡 / 紧凑）。
            budget_level: budget / midrange / luxury（经济 / 中档 / 奢华）。
            interests: 用户兴趣列表（例如：['历史', '美食']）。
            user_profile_summary: 来自长期记忆的用户摘要。
            conversation_summary: 来自短期记忆的对话摘要。

        Returns:
            完整的系统提示词字符串。
        """
        interests_str = ", ".join(interests) if interests else "Not specified"

        return SYSTEM_PROMPT_TEMPLATE.format(
            tools_description=tools_description,
            user_profile_summary=user_profile_summary,
            conversation_summary=conversation_summary,
            current_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            days=days,
            travel_style=travel_style,
            budget_level=budget_level,
            interests=interests_str,
        )

    @staticmethod
    def build_messages(
        system_prompt: str,
        user_input: str,
        conversation_history: list[dict] | None = None,
    ) -> list[dict]:
        """构建发送给 LLM 的完整消息列表。

        Args:
            system_prompt: 系统提示词字符串。
            user_input: 当前用户消息。
            conversation_history: 之前的消息轮次。

        Returns:
            可直接供 LLM 消费的消息字典列表。
        """
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_input})
        return messages
