"""聊天 API 端点 — 基于 SSE 流式传输的对话式 Agent 交互。"""

import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def chat_message(req: ChatRequest) -> ChatResponse:
    """向旅行助手 Agent 发送消息。

    非流式端点。如需流式响应，请使用 GET /api/chat/message/stream。
    """
    from app.agent.react import ReActAgent
    from app.agent.context import ContextBuilder
    from app.agent.providers import create_llm_model
    from app.memory.manager import MemoryManager
    from app.database import async_session_factory
    from app.tools.langchain_tools import create_all_tools

    session_id = req.session_id or f"chat_{uuid.uuid4().hex[:12]}"

    # 初始化
    llm = create_llm_model()
    tools = create_all_tools()
    agent = ReActAgent(model=llm, tools=tools)

    # 加载上下文并执行
    async with async_session_factory() as db:
        memory = MemoryManager(db)
        ctx = await memory.build_context(req.user_id, session_id)

        # 构建系统提示词
        tools_desc = "\n".join(f"- {t.name}: {t.description}" for t in tools)
        profile_summary = ctx.user_profile.get("summary", "") if ctx.user_profile else ""

        system_prompt = (
            f"You are an expert travel planning assistant.\n\n"
            f"Available tools:\n{tools_desc}\n\n"
            f"User profile: {profile_summary}\n"
            f"Be helpful, conversational, and use tools when you need real data."
        )

        # 执行 Agent
        result = await agent.execute(
            user_input=req.message,
            system_prompt=system_prompt,
            conversation_history=ctx.conversation_history,
        )

        # 保存交互记录
        await memory.save_interaction(
            user_id=req.user_id,
            session_id=session_id,
            user_message=req.message,
            assistant_message=result.content,
            tool_calls=result.tool_calls,
            llm=llm,
        )
        await db.commit()

    return ChatResponse(
        session_id=session_id,
        response=result.content,
        tool_calls=[
            {"tool": tc["tool"], "args": tc.get("arguments", {})}
            for tc in result.tool_calls
        ],
    )


@router.get("/message/stream")
async def chat_message_stream(
    user_id: str,
    message: str,
    session_id: str | None = None,
) -> StreamingResponse:
    """通过 Server-Sent Events 流式传输 Agent 响应。

    事件类型：
        data: {"type": "start"}
        data: {"type": "llm_response", "data": {...}}
        data: {"type": "tool_result", "data": {...}}
        data: {"type": "done", "data": {...}}
    """
    from app.agent.streaming import sse_event_generator
    from app.agent.react import ReActAgent
    from app.agent.providers import create_llm_model
    from app.tools.langchain_tools import create_all_tools

    sid = session_id or f"chat_{uuid.uuid4().hex[:12]}"

    llm = create_llm_model()
    tools = create_all_tools()
    agent = ReActAgent(model=llm, tools=tools)

    tools_desc = "\n".join(f"- {t.name}: {t.description}" for t in tools)

    system_prompt = (
        f"You are an expert travel planning assistant.\n\n"
        f"Available tools:\n{tools_desc}\n\n"
        f"Be helpful and conversational."
    )

    return StreamingResponse(
        sse_event_generator(
            agent=agent,
            user_input=message,
            system_prompt=system_prompt,
            conversation_history=None,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
