"""健康检查端点。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """返回服务健康状态。"""
    return {"status": "ok", "version": "0.1.0"}
