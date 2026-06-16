"""将现有 conversation_messages 表适配为 LangChain BaseChatMessageHistory 接口。

这样 LangGraph/LangChain 组件可以直接读写我们现有的数据库表，
不需要引入第二套消息存储。
"""

import logging
from collections.abc import Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.models import ConversationMessage

logger = logging.getLogger(__name__)

# 角色映射：数据库角色 <-> LangChain 消息类型
_ROLE_TO_MESSAGE_TYPE: dict[str, type] = {
    "user": HumanMessage,
    "assistant": AIMessage,
    "tool": ToolMessage,
    "system": SystemMessage,
}


class ConversationMessageHistory(BaseChatMessageHistory):
    """适配现有 conversation_messages 表到 LangChain BaseChatMessageHistory。

    直接使用我们已有的 SQLAlchemy ORM 模型，保持数据库 schema 不变。

    用法：
        history = ConversationMessageHistory(db_session, session_id="abc")
        await history.aadd_messages([HumanMessage(content="hello")])
        messages = history.messages  # 同步读取缓存
    """

    def __init__(self, session: AsyncSession, session_id: str) -> None:
        self._session = session
        self._session_id = session_id
        self._cached_messages: list[BaseMessage] | None = None

    @property
    def messages(self) -> list[BaseMessage]:
        """同步返回缓存的消息列表。

        注意：必须先调用 await history.aload() 加载消息。
        """
        if self._cached_messages is None:
            logger.warning("Messages not loaded; returning empty list. Call aload() first.")
            return []
        return list(self._cached_messages)

    async def aload(self) -> list[BaseMessage]:
        """从数据库加载消息并缓存。"""
        query = (
            select(ConversationMessage)
            .where(ConversationMessage.session_id == self._session_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(200)
        )
        result = await self._session.execute(query)
        records = result.scalars().all()

        messages: list[BaseMessage] = []
        for record in records:
            msg_cls = _ROLE_TO_MESSAGE_TYPE.get(record.role, HumanMessage)
            if record.role == "tool":
                # ToolMessage 需要 tool_call_id，存回 content 中
                msg = ToolMessage(content=record.content, tool_call_id="")
            else:
                msg = msg_cls(content=record.content)
            messages.append(msg)

        self._cached_messages = messages
        return messages

    async def aadd_messages(self, messages: Sequence[BaseMessage]) -> None:
        """将 LangChain 消息持久化到 conversation_messages 表。"""
        from datetime import timezone

        for msg in messages:
            role = _message_to_role(msg)
            content = _message_to_content(msg)

            record = ConversationMessage(
                session_id=self._session_id,
                user_id="",  # 由调用方在 add_message 时设置，这里不感知 user_id
                role=role,
                content=content,
                token_count=len(content) // 4,
            )
            self._session.add(record)

        await self._session.flush()

        # 刷新缓存
        if self._cached_messages is not None:
            self._cached_messages.extend(messages)

    async def aclear(self) -> None:
        """删除会话的所有消息。"""
        query = select(ConversationMessage).where(
            ConversationMessage.session_id == self._session_id
        )
        result = await self._session.execute(query)
        records = result.scalars().all()
        for record in records:
            await self._session.delete(record)
        await self._session.flush()
        self._cached_messages = []
        logger.info(f"Cleared messages for session {self._session_id[:8]}")


def _message_to_role(msg: BaseMessage) -> str:
    """LangChain BaseMessage → 数据库 role 字符串。"""
    if isinstance(msg, HumanMessage):
        return "user"
    elif isinstance(msg, AIMessage):
        return "assistant"
    elif isinstance(msg, ToolMessage):
        return "tool"
    elif isinstance(msg, SystemMessage):
        return "system"
    return "user"


def _message_to_content(msg: BaseMessage) -> str:
    """LangChain BaseMessage → 内容字符串。"""
    if isinstance(msg, AIMessage) and msg.tool_calls:
        # 如果有 tool_calls，将 content + tool_calls 序列化
        import json
        parts = []
        if msg.content:
            parts.append(msg.content)
        for tc in msg.tool_calls:
            parts.append(json.dumps(tc, ensure_ascii=False))
        return "\n".join(parts)
    return str(msg.content) if msg.content else ""
