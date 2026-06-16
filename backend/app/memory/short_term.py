"""短期记忆：对话历史管理。

特性：
- 滑动窗口：在 Token 预算内仅保留最近的消息
- 自动总结：当历史记录超出 Token 预算时，使用轻量级 LLM 总结旧消息并用摘要替代
- 基于会话的隔离：每个 session_id 独立管理
- 底层使用 LangChain BaseChatMessageHistory 接口持久化
"""

import logging
from datetime import datetime, timezone
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.memory.chat_history import ConversationMessageHistory
from app.memory.models import ConversationMessage

logger = logging.getLogger(__name__)

# 粗略估计：4 个字符 ≈ 1 个 token
CHARS_PER_TOKEN = 4


class ShortTermMemory:
    """在 Token 预算内管理对话历史。

    提供：
    - add_message：持久化新消息
    - get_history：在 Token 预算内检索最近消息
    - summarize_and_compress：总结旧消息以释放预算空间
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._max_tokens = settings.memory.short_term_max_tokens

    async def add_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
    ) -> ConversationMessage:
        """添加消息到对话历史。

        Args:
            session_id: 对话会话标识符。
            user_id: 用户标识符。
            role: 消息角色（user, assistant, tool, system）。
            content: 消息文本内容。

        Returns:
            创建的 ConversationMessage。
        """
        msg = ConversationMessage(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            token_count=len(content) // CHARS_PER_TOKEN,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(msg)
        await self._session.flush()
        return msg

    async def get_history(
        self,
        session_id: str,
        max_tokens: int | None = None,
    ) -> list[dict]:
        """获取 Token 预算内的最近对话消息。

        按创建时间倒序检索消息，从最新开始累积直到达到 Token 预算。

        Args:
            session_id: 要检索的会话。
            max_tokens: 覆盖默认的 Token 预算。

        Returns:
            按时间顺序排列的消息字典列表（旧的在前面）。
        """
        budget = max_tokens or self._max_tokens

        query = (
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(100)  # 硬限制，避免无界查询
        )
        result = await self._session.execute(query)
        messages = result.scalars().all()

        # 在预算内累积消息（从最新开始遍历）
        selected: list[ConversationMessage] = []
        total_tokens = 0
        for msg in messages:
            tokens = msg.token_count or len(msg.content) // CHARS_PER_TOKEN
            if total_tokens + tokens <= budget:
                selected.append(msg)
                total_tokens += tokens
            else:
                break

        # 按时间顺序返回
        selected.reverse()
        return [m.to_message_dict() for m in selected]

    async def summarize_and_compress(
        self,
        session_id: str,
        llm: BaseChatModel,
    ) -> str | None:
        """总结旧消息并用摘要替换它们。

        当对话历史超出 Token 预算时，此方法：
        1. 检索会话的所有消息
        2. 将消息分为"旧消息"（待总结）和"最近消息"（保留）
        3. 使用 LLM 生成旧消息的摘要
        4. 删除旧消息并插入一条摘要消息

        Args:
            session_id: 要压缩的会话。
            llm: LangChain BaseChatModel 实例。

        Returns:
            摘要文本，如果不需要压缩则返回 None。
        """
        # 获取所有消息
        query = (
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc())
        )
        result = await self._session.execute(query)
        all_messages = result.scalars().all()

        if not all_messages:
            return None

        # 检查是否需要压缩
        total_tokens = sum(
            m.token_count or len(m.content) // CHARS_PER_TOKEN for m in all_messages
        )
        if total_tokens <= self._max_tokens:
            return None

        # 分割：保留预算的约 40%，总结其余部分
        keep_tokens = int(self._max_tokens * 0.4)
        current_tokens = 0
        split_idx = len(all_messages)

        for i in range(len(all_messages) - 1, -1, -1):
            t = all_messages[i].token_count or len(all_messages[i].content) // CHARS_PER_TOKEN
            if current_tokens + t <= keep_tokens:
                current_tokens += t
                split_idx = i
            else:
                break

        old_messages = all_messages[:split_idx]

        if not old_messages:
            return None

        # 构建总结提示词
        conversation_text = "\n".join(
            f"[{m.role}]: {m.content}" for m in old_messages
        )

        summary_prompt = [
            SystemMessage(content=(
                "Summarize the following conversation. Include key decisions, "
                "user preferences mentioned, and important context. Keep it concise (2-3 paragraphs)."
            )),
            HumanMessage(content=conversation_text),
        ]

        try:
            response = await llm.ainvoke(summary_prompt)
            summary = f"[Conversation Summary]: {response.content}"
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            summary = f"[Truncated conversation — {len(old_messages)} older messages omitted]"

        # 删除旧消息并插入摘要
        for msg in old_messages:
            await self._session.delete(msg)

        summary_msg = ConversationMessage(
            session_id=session_id,
            user_id=all_messages[0].user_id,
            role="system",
            content=summary,
            token_count=len(summary) // CHARS_PER_TOKEN,
            created_at=old_messages[-1].created_at,
        )
        self._session.add(summary_msg)
        await self._session.flush()

        logger.info(
            f"Compressed {len(old_messages)} messages into summary "
            f"({len(summary)} chars) for session {session_id[:8]}"
        )
        return summary

    async def clear_session(self, session_id: str) -> int:
        """删除会话的所有消息。返回删除的消息数量。"""
        query = select(ConversationMessage).where(
            ConversationMessage.session_id == session_id
        )
        result = await self._session.execute(query)
        messages = result.scalars().all()
        for msg in messages:
            await self._session.delete(msg)
        await self._session.flush()
        logger.info(f"Cleared {len(messages)} messages from session {session_id[:8]}")
        return len(messages)
