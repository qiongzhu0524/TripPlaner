"""长期记忆：基于向量嵌入的持久化用户档案。

特性：
- 存储/检索用户偏好（预算、旅行风格、兴趣、饮食等）
- 通过 pgvector 嵌入进行语义搜索（查找具有相似偏好的用户）
- 从对话文本中自动提取偏好
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import UserProfileRecord

logger = logging.getLogger(__name__)


class LongTermMemory:
    """管理基于向量语义检索的持久化用户档案。

    用法：
        ltm = LongTermMemory(db_session)
        profile = await ltm.get_profile("user123")
        await ltm.update_profile("user123", {"interests": ["history", "food"]})
        await ltm.extract_preferences("user123", conversation_text, model)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_profile(self, user_id: str) -> dict | None:
        """获取用户档案。如果未找到则返回 None。"""
        result = await self._session.execute(
            select(UserProfileRecord).where(UserProfileRecord.user_id == user_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return record.to_profile_dict()

    async def get_or_create_profile(self, user_id: str) -> UserProfileRecord:
        """获取现有档案，如果不存在则创建默认档案。"""
        result = await self._session.execute(
            select(UserProfileRecord).where(UserProfileRecord.user_id == user_id)
        )
        record = result.scalar_one_or_none()

        if record is None:
            record = UserProfileRecord(
                user_id=user_id,
                profile_json={
                    "dietary_preferences": [],
                    "budget_level": "midrange",
                    "travel_style": "balanced",
                    "interests": [],
                    "past_destinations": [],
                },
                updated_at=datetime.now(timezone.utc),
            )
            self._session.add(record)
            await self._session.flush()
            logger.info(f"Created new user profile: {user_id}")

        return record

    async def update_profile(self, user_id: str, updates: dict[str, Any]) -> UserProfileRecord:
        """更新用户档案中的特定字段。

        将更新字典合并到现有的 profile_json 中。
        """
        record = await self.get_or_create_profile(user_id)
        profile = dict(record.profile_json)
        profile.update(updates)
        record.profile_json = profile
        record.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        logger.info(f"Updated profile for {user_id}: {list(updates.keys())}")
        return record

    async def extract_preferences(
        self,
        user_id: str,
        conversation_text: str,
        llm: BaseChatModel,
    ) -> dict[str, Any]:
        """从对话文本中提取旅行偏好。

        分析对话并提取结构化偏好：
        - 旅行风格（relaxed/balanced/intensive）
        - 预算等级（budget/midrange/luxury）
        - 兴趣（例如：历史、美食、自然、购物）
        - 饮食偏好（例如：素食、清真、无禁忌）
        - 偏好的活动

        Args:
            user_id: 用户标识符。
            conversation_text: 要分析的对话文本。
            llm: LangChain BaseChatModel 实例。

        Returns:
            提取的偏好字典。
        """
        messages = [
            SystemMessage(content=(
                "You are a preference extraction assistant. "
                "From the conversation below, extract the user's travel preferences. "
                "Return ONLY a valid JSON object with these fields:\n"
                '{\n'
                '  "travel_style": "relaxed" | "balanced" | "intensive",\n'
                '  "budget_level": "budget" | "midrange" | "luxury",\n'
                '  "interests": [string, ...],  // e.g., ["history", "food", "nature"]\n'
                '  "dietary_preferences": [string, ...],  // e.g., ["vegetarian", "halal"]\n'
                '  "preferred_activities": [string, ...]\n'
                "}\n"
                "Only include fields where you have clear evidence from the conversation. "
                "Use null for unknown fields."
            )),
            HumanMessage(content=f"Extract travel preferences from:\n\n{conversation_text}"),
        ]

        try:
            response = await llm.ainvoke(messages)
            extracted = json.loads(str(response.content))
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Preference extraction failed: {e}")
            return {}

        # 合并到档案中
        clean = {k: v for k, v in extracted.items() if v is not None and v != []}
        if clean:
            await self.update_profile(user_id, clean)

        return clean

    async def generate_embedding(self, text: str, llm: Any) -> list[float] | None:
        """为给定文本生成向量嵌入（占位实现）。"""
        logger.debug("Embedding generation not yet implemented (placeholder)")
        return None

    async def search_similar_users(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        """通过向量相似度搜索具有相似偏好的用户（占位实现）。"""
        logger.debug("Vector similarity search not yet implemented (requires pgvector setup)")
        return []

    @staticmethod
    def profile_to_summary(profile: dict | None) -> str:
        """将用户档案字典转换为系统提示词可读的摘要。"""
        if not profile:
            return "No user profile data available."

        parts = []

        style = profile.get("travel_style", "balanced")
        parts.append(f"Travel style: {style}")

        budget = profile.get("budget_level", "midrange")
        parts.append(f"Budget level: {budget}")

        interests = profile.get("interests", [])
        if interests:
            parts.append(f"Interests: {', '.join(interests)}")

        diet = profile.get("dietary_preferences", [])
        if diet:
            parts.append(f"Dietary: {', '.join(diet)}")

        past = profile.get("past_destinations", [])
        if past:
            parts.append(f"Previously visited: {', '.join(past)}")

        return " | ".join(parts)
