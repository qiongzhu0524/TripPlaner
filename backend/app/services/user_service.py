"""用户服务：用户档案的 CRUD 操作。"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.long_term import LongTermMemory

logger = logging.getLogger(__name__)


class UserService:
    """用户档案管理的业务逻辑。"""

    def __init__(self, session: AsyncSession) -> None:
        self._ltm = LongTermMemory(session)

    async def get_profile(self, user_id: str) -> dict | None:
        """获取用户档案。"""
        return await self._ltm.get_profile(user_id)

    async def update_profile(self, user_id: str, updates: dict[str, Any]) -> dict:
        """更新用户档案字段。"""
        record = await self._ltm.update_profile(user_id, updates)
        return record.to_profile_dict()

    async def get_or_create_profile(self, user_id: str) -> dict:
        """获取或创建用户档案。"""
        record = await self._ltm.get_or_create_profile(user_id)
        return record.to_profile_dict()

    def format_summary(self, profile: dict | None) -> str:
        """将档案格式化为人类可读的字符串。"""
        return LongTermMemory.profile_to_summary(profile)
