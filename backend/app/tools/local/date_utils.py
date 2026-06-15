"""旅行规划的日期工具。

提供：
- date_range: 生成起始日期之间的日期列表
- get_weekday: 返回给定日期的星期名称
- is_holiday: 检查日期是否为中国的公共假日（简化版）
"""

from datetime import date, datetime, timedelta
from typing import Any

from app.tools.base import ToolProtocol, ToolResult


class DateRangeTool(ToolProtocol):
    """生成旅行日期列表。"""

    name = "date_range"
    description = "生成旅行日期范围内的日期列表，每个日期带有星期几。"
    parameters = {
        "type": "object",
        "properties": {
            "start_date": {"type": "string", "description": "起始日期 YYYY-MM-DD"},
            "days": {"type": "integer", "description": "天数"},
        },
        "required": ["start_date", "days"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        start_str = kwargs.get("start_date", "")
        days = kwargs.get("days", 1)

        try:
            start_date = date.fromisoformat(start_str)
        except (ValueError, TypeError):
            return ToolResult(success=False, error=f"Invalid date format: {start_str}. Use YYYY-MM-DD.")

        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        dates = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            dates.append({
                "date": d.isoformat(),
                "weekday": weekday_names[d.weekday()],
                "day_number": i + 1,
            })

        return ToolResult(
            success=True,
            data={"dates": dates, "total_days": len(dates)},
        )
