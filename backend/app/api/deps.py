"""FastAPI 依赖注入辅助工具。

提供异步依赖：
- 数据库会话
- 工具注册表（单例，在启动时初始化）
- Agent 实例（注入工具和记忆）
- 记忆管理器
"""

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


def get_settings():
    """返回应用配置（用于非 DI 上下文，直接导入）。"""
    from app.config import settings

    return settings
