"""TripPlaner AI - FastAPI 应用工厂。"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动和关闭逻辑。"""
    setup_logging(settings.log_level)
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Starting TripPlaner AI v0.1.0")
    # TODO: 初始化工具注册表单例、MCP 服务器等
    yield
    # TODO: 关闭：关闭 MCP 会话、数据库连接
    logger.info("Shutting down TripPlaner AI")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    app = FastAPI(
        title="TripPlaner AI",
        version="0.1.0",
        description="AI-powered trip planning assistant with ReAct agent, MCP tools, memory, and RAG",
        lifespan=lifespan,
    )

    # CORS — 允许前端开发服务器
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件
    from app.api.middleware import RequestLoggingMiddleware

    app.add_middleware(RequestLoggingMiddleware)

    # 注册路由
    from app.api.routes import health, trip, map, chat

    app.include_router(health.router, tags=["health"])
    app.include_router(trip.router, prefix="/api/trip", tags=["trip"])
    app.include_router(map.router, prefix="/api/map", tags=["map"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

    return app


app = create_app()
