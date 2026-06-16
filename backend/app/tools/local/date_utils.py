"""旅行规划的日期工具。

提供日期范围生成和星期查询功能。
"""

from datetime import date, timedelta
from pydantic import BaseModel, Field


class DateRangeInput(BaseModel):
    """日期范围参数。"""

    start_date: str = Field(description="起始日期 YYYY-MM-DD")
    days: int = Field(description="天数")


async def date_range(start_date: str, days: int) -> dict:
    """生成旅行日期范围内的日期列表，每个日期带有星期几。"""
    try:
        start = date.fromisoformat(start_date)
    except (ValueError, TypeError):
        return {"error": f"Invalid date format: {start_date}. Use YYYY-MM-DD."}

    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    dates = []
    for i in range(days):
        d = start + timedelta(days=i)
        dates.append({
            "date": d.isoformat(),
            "weekday": weekday_names[d.weekday()],
            "day_number": i + 1,
        })

    return {"dates": dates, "total_days": len(dates)}
