"""记忆系统的数据库模型。

使用 SQLAlchemy 2.0 ORM（支持异步）。
需要 pgvector 扩展用于向量嵌入（长期记忆）。

数据表：
- conversation_messages：每个会话的短期对话历史
- user_profiles：带有向量嵌入的长期用户偏好存储
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConversationMessage(Base):
    """存储对话会话中的单条消息。

    由 ShortTermMemory 用于对话历史和上下文窗口管理。
    """

    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # 角色：user/assistant/tool/system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # 复合索引，用于高效的会话检索
    __table_args__ = (
        Index("ix_session_created", "session_id", "created_at"),
    )

    def to_message_dict(self) -> dict:
        """转换为兼容 LLM 的消息字典。"""
        return {"role": self.role, "content": self.content}

    def __repr__(self) -> str:
        return f"<Message {self.role} [{self.session_id[:8]}]: {self.content[:50]}...>"


class UserProfileRecord(Base):
    """持久化的用户档案，带有用于语义检索的向量嵌入。

    由 LongTermMemory 用于存储用户偏好、历史行程和兴趣。
    嵌入列支持语义搜索（例如："用户偏好户外活动"）。
    """

    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    profile_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    # 嵌入向量通过建表后的原生 SQL 创建（pgvector）
    # CREATE EXTENSION IF NOT EXISTS vector;
    # ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS embedding vector(1536);
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_profile_dict(self) -> dict:
        """转换为适用于 UserProfile Pydantic 模型的普通字典。"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            **self.profile_json,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }

    def __repr__(self) -> str:
        return f"<UserProfile {self.user_id}>"
