"""用于国际旅行规划的货币转换工具。

使用exchangerate-api.com（免费层）或备用的静态汇率表。
"""

import logging
from typing import Any

import httpx

from app.tools.base import ToolProtocol, ToolResult

logger = logging.getLogger(__name__)

# 备用静态汇率（以人民币为基准，近似值）
FALLBACK_RATES = {
    "CNY": 1.0,
    "USD": 0.14,
    "EUR": 0.13,
    "JPY": 20.5,
    "KRW": 185.0,
    "THB": 4.9,
    "SGD": 0.19,
    "HKD": 1.09,
    "TWD": 4.4,
    "GBP": 0.11,
    "AUD": 0.21,
    "CAD": 0.19,
}


class CurrencyConvertTool(ToolProtocol):
    """在国际旅行预算估算中进行货币转换。"""

    name = "currency_convert"
    description = (
        "货币转换工具。将金额从一种货币转换为另一种货币。"
        "支持CNY/USD/EUR/JPY/KRW/THB/SGD/HKD/GBP等。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "amount": {"type": "number", "description": "要转换的金额"},
            "from_currency": {"type": "string", "description": "源货币代码，如CNY、USD"},
            "to_currency": {"type": "string", "description": "目标货币代码，如JPY、EUR"},
        },
        "required": ["amount", "from_currency", "to_currency"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        amount = float(kwargs.get("amount", 0))
        from_curr = kwargs.get("from_currency", "CNY").upper()
        to_curr = kwargs.get("to_currency", "USD").upper()

        # 先尝试在线API
        rate = None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://open.er-api.com/v6/latest/{from_curr}"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    rate = data.get("rates", {}).get(to_curr)
        except Exception as e:
            logger.debug(f"Live currency API failed: {e}")

        # 回退到静态汇率
        if rate is None:
            logger.debug(f"Using fallback rates for {from_curr}→{to_curr}")
            from_rate = FALLBACK_RATES.get(from_curr)
            to_rate = FALLBACK_RATES.get(to_curr)
            if from_rate is None or to_rate is None:
                return ToolResult(
                    success=False,
                    error=f"Currency not supported: {from_curr} or {to_curr}. Supported: {list(FALLBACK_RATES.keys())}",
                )
            rate = to_rate / from_rate

        converted = round(amount * rate, 2)

        return ToolResult(
            success=True,
            data={
                "from": {"amount": amount, "currency": from_curr},
                "to": {"amount": converted, "currency": to_curr},
                "rate": round(rate, 6),
            },
        )
