"""DeepSeek 提供者——与 OpenAI 兼容，使用不同的默认值。"""

import os

from openai import AsyncOpenAI

from app.agent.providers.openai import OpenAIProvider
from app.config import settings


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek 提供者。继承自 OpenAIProvider，因为 DeepSeek 与 OpenAI 兼容。"""

    def __init__(self) -> None:
        cfg = settings.llm_deepseek
        self._client = AsyncOpenAI(
            api_key=cfg.api_key or os.getenv("DEEPSEEK_API_KEY"),
            base_url=cfg.base_url or "https://api.deepseek.com",
        )
        self._model = cfg.model
        self._default_max_tokens = cfg.max_tokens
        self._default_temperature = cfg.temperature

    @property
    def provider_name(self) -> str:
        return "deepseek"
