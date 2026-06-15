"""MemoryManager：短期记忆与长期记忆的统一接口。

协调：
- 在 Agent 执行前加载用户上下文（档案 + 对话历史）
- 在 Agent 执行后保存交互记录（消息 + 提取的偏好）
- 构建 ReAct Agent 使用的 AgentContext 对象
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.long_term import LongTermMemory
from app.memory.short_term import ShortTermMemory
from app.models.agent import AgentContext

logger = logging.getLogger(__name__)


class MemoryManager:
    """Agent 的统一记忆管理。

    用法：
        # 在 Agent 执行前
        async with async_session_factory() as db:
            memory = MemoryManager(db)
            context = await memory.build_context(user_id, session_id)

        # 在 Agent 执行后
        await memory.save_interaction(user_id, session_id, messages, llm)
    """

    def __init__(self, session: AsyncSession) -> None:
        """使用数据库会话初始化。

        Args:
            session: SQLAlchemy AsyncSession。
        """
        self.short_term = ShortTermMemory(session)
        self.long_term = LongTermMemory(session)

    async def build_context(
        self,
        user_id: str,
        session_id: str,
    ) -> AgentContext:
        """在执行前构建完整的 Agent 上下文。

        加载：
        1. 从长期记忆中获取用户档案（或创建默认档案）
        2. 从短期记忆中获取最近的对话历史
        3. 组装为 AgentContext

        Args:
            user_id: 用户标识符。
            session_id: 对话会话标识符。

        Returns:
            准备好注入系统提示词的 AgentContext。
        """
        # 加载用户档案（长期记忆）
        profile = await self.long_term.get_profile(user_id)
        if profile is None:
            profile_record = await self.long_term.get_or_create_profile(user_id)
            profile = profile_record.to_profile_dict()

        # 加载对话历史（短期记忆）
        history = await self.short_term.get_history(session_id)

        # 生成可读的用户档案摘要
        profile_summary = self.long_term.profile_to_summary(profile)

        logger.debug(
            f"Built context for user={user_id} session={session_id[:8]}: "
            f"history messages={len(history)}, profile fields={len(profile)}"
        )

        return AgentContext(
            user_id=user_id,
            user_profile={
                "full": profile,
                "summary": profile_summary,
            },
            conversation_history=history,
            session_id=session_id,
        )

    async def save_interaction(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        assistant_message: str,
        tool_calls: list[dict] | None = None,
        llm: Any = None,
    ) -> None:
        """将完整的交互轮次保存到记忆系统。

        持久化：
        1. 用户消息 → 短期记忆
        2. 工具调用消息（如果有） → 短期记忆
        3. 助手回复 → 短期记忆
        4. 超出 Token 预算时触发总结压缩
        5. 从对话中触发偏好提取

        Args:
            user_id: 用户标识符。
            session_id: 会话标识符。
            user_message: 用户的输入消息。
            assistant_message: Agent 的最终回复。
            tool_calls: 本轮次的工具调用记录。
            llm: 用于总结/偏好提取的 LLMProvider。
        """
        # 保存用户消息
        await self.short_term.add_message(session_id, user_id, "user", user_message)

        # 保存工具调用（如果有）
        if tool_calls:
            for tc in tool_calls:
                tool_msg = f"Tool [{tc.get('tool', 'unknown')}]: {tc.get('result', '')}"
                await self.short_term.add_message(
                    session_id, user_id, "tool", tool_msg
                )

        # 保存助手回复
        await self.short_term.add_message(
            session_id, user_id, "assistant", assistant_message
        )

        # 检查是否需要总结压缩
        if llm:
            try:
                await self.short_term.summarize_and_compress(session_id, llm)
            except Exception as e:
                logger.warning(f"Summarization failed (non-fatal): {e}")

            # 从对话中提取偏好
            try:
                conversation = f"User: {user_message}\nAssistant: {assistant_message}"
                await self.long_term.extract_preferences(user_id, conversation, llm)
            except Exception as e:
                logger.warning(f"Preference extraction failed (non-fatal): {e}")

        logger.info(
            f"Saved interaction for user={user_id} session={session_id[:8]}"
        )

    async def save_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
    ) -> None:
        """保存单条消息（便捷包装方法）。

        Args:
            session_id: 会话标识符。
            user_id: 用户标识符。
            role: 消息角色。
            content: 消息内容。
        """
        await self.short_term.add_message(session_id, user_id, role, content)
