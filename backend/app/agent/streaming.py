"""SSE（服务器发送事件）流式传输辅助工具。

封装一个异步生成器，通过 FastAPI 的 StreamingResponse 将 ReAct 智能体的进度事件流式传输到前端。
"""

import json
import logging
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


async def sse_event_generator(
    agent,
    user_input: str,
    system_prompt: str,
    conversation_history: list[dict] | None = None,
    tool_registry=None,
) -> AsyncIterator[str]:
    """生成 ReAct 智能体执行的 SSE 事件。

    用法（在 FastAPI 路由中）：
        return StreamingResponse(
            sse_event_generator(agent, user_input, prompt, history, registry),
            media_type="text/event-stream",
        )

    生成：
        SSE 格式的字符串："data: {json}\\n\\n"
    """
    async def stream_handler(event_type: str, data: dict) -> None:
        """回调：非异步安全，但 SSE 生成器是唯一的消费者。"""
        pass

    # 我们使用队列来桥接基于回调的流处理器与 SSE 生成器
    import asyncio

    queue: asyncio.Queue[dict] = asyncio.Queue()

    def sync_handler(event_type: str, data: dict) -> None:
        """将事件放入异步队列的同步回调。"""
        try:
            queue.put_nowait({"type": event_type, "data": data})
        except asyncio.QueueFull:
            logger.warning("SSE event queue full, dropping event")

    # 将智能体执行为后台任务
    task = asyncio.create_task(
        agent.execute(
            user_input=user_input,
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            stream_handler=sync_handler,
        )
    )

    # 流式传输到达的事件
    yield "data: {}\n\n".format(json.dumps({"type": "start", "data": {}}))

    while not task.done() or not queue.empty():
        try:
            event = await asyncio.wait_for(queue.get(), timeout=0.1)
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except asyncio.TimeoutError:
            continue

    # 获取最终结果
    result = await task
    yield f"data: {json.dumps({'type': 'done', 'data': {'success': result.success, 'content': result.content, 'iterations': result.iterations}}, ensure_ascii=False)}\n\n"
