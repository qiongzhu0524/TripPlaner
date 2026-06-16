"""行程规划 API 端点。"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.schemas import TripPlanRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/plan", response_model=dict)
async def plan_trip(
    req: TripPlanRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """生成完整的行程规划。

    此端点：
    1. 加载用户个人档案和对话历史
    2. 构建注入所有上下文的系统提示词
    3. 使用 ReAct Agent 执行规划（配备高德地图工具）
    4. 将交互记录持久化到记忆系统
    5. 返回结构化的行程安排
    """
    from app.agent.providers import create_llm_model
    from app.tools.langchain_tools import create_all_tools
    from app.services.trip_service import TripService

    # 初始化依赖
    llm = create_llm_model()
    tools = create_all_tools()

    # 执行规划
    service = TripService(llm=llm, tools=tools, max_iterations=10)

    try:
        result = await service.plan_trip(
            user_id=req.user_id,
            destination=req.destination,
            start_date=req.start_date,
            days=req.days,
            travel_style=req.travel_style or "balanced",
            budget_level=req.budget_level or "midrange",
            interests=req.interests,
            dietary_preferences=req.dietary_preferences,
        )
        return result
    except Exception as e:
        logger.error(f"Trip planning failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Trip planning failed: {str(e)}")
