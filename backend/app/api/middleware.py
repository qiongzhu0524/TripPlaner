"""FastAPI 中间件：CORS、请求日志、错误处理。"""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录传入请求及其处理时间。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} "
            f"({duration_ms:.0f}ms)"
        )
        return response
