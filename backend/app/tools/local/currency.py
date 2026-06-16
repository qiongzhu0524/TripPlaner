"""用于国际旅行规划的货币转换工具。

使用 exchangerate-api.com（免费层）或备用的静态汇率表。
"""

import logging
from pydantic import BaseModel, Field
import httpx

logger = logging.getLogger(__name__)

# 备用静态汇率（以人民币为基准，近似值）
FALLBACK_RATES = {
    "CNY": 1.0, "USD": 0.14, "EUR": 0.13, "JPY": 20.5, "KRW": 185.0,
    "THB": 4.9, "SGD": 0.19, "HKD": 1.09, "TWD": 4.4, "GBP": 0.11,
    "AUD": 0.21, "CAD": 0.19,
}


class CurrencyConvertInput(BaseModel):
    """货币转换参数。"""

    amount: float = Field(description="要转换的金额")
    from_currency: str = Field(description="源货币代码，如CNY、USD")
    to_currency: str = Field(description="目标货币代码，如JPY、EUR")


async def currency_convert(amount: float, from_currency: str, to_currency: str) -> dict:
    """在国际旅行预算估算中进行货币转换。

    支持 CNY/USD/EUR/JPY/KRW/THB/SGD/HKD/GBP 等。
    """
    from_curr = from_currency.upper()
    to_curr = to_currency.upper()

    # 先尝试在线 API
    rate = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://open.er-api.com/v6/latest/{from_curr}")
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
            supported = list(FALLBACK_RATES.keys())
            return {"error": f"Currency not supported: {from_curr} or {to_curr}. Supported: {supported}"}
        rate = to_rate / from_rate

    converted = round(amount * rate, 2)
    return {
        "from": {"amount": amount, "currency": from_curr},
        "to": {"amount": converted, "currency": to_curr},
        "rate": round(rate, 6),
    }
