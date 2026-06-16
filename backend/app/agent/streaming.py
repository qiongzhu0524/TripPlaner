"""SSE（服务器发送事件）流式传输辅助工具。

使用 LangGraph 的 astream_events 将 Agent 执行进度流式传输到前端。
"""

import json
import logging
from collections.abc import AsyncIterator

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


async def sse_event_generator(
    agent,  # ReActAgent 实例
    user_input: str,
    system_prompt: str,
    conversation_history: list[dict] | None = None,
) -> AsyncIterator[str]:
    """生成 ReAct 智能体执行的 SSE 事件。

    用法（在 FastAPI 路由中）：
        return StreamingResponse(
            sse_event_generator(agent, user_input, prompt, history),
            media_type="text/event-stream",
        )

    生成：
        SSE 格式的字符串："data: {json}\\n\\n"

    事件类型：
        - start: 流开始
        - llm_response: LLM 文本增量
        - tool_result: 工具执行完成
        - done: 流结束
    """
    # 发送开始事件
    yield f"data: {json.dumps({'type': 'start', 'data': {}})}\n\n"

    async def stream_handler(event_type: str, data: dict) -> None:
        """异步回调：将事件放入队列。"""
        queue.put_nowait({"type": event_type, "data": data})

    import asyncio
    queue: asyncio.Queue[dict] = asyncio.Queue()

    # 后台执行 Agent
    task = asyncio.create_task(
        agent.execute(
            user_input=user_input,
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            stream_handler=stream_handler,
        )
    )

    # 流式传输到达的事件
    while not task.done() or not queue.empty():
        try:
            event = await asyncio.wait_for(queue.get(), timeout=0.1)
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except asyncio.TimeoutError:
            continue

    # 获取最终结果
    result = await task
    yield f"data: {json.dumps({'type': 'done', 'data': {'success': result.success, 'content': result.content, 'iterations': result.iterations}}, ensure_ascii=False)}\n\n"
