"""LangChain BaseChatModel 工厂函数。

从项目 settings 创建 ChatOpenAI / ChatAnthropic / ChatDeepSeek 实例。
DeepSeek 兼容 OpenAI API，使用 ChatOpenAI + 自定义 base_url。
"""

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from app.config import settings


def create_llm_model(provider: str | None = None) -> BaseChatModel:
    """从 settings 创建 LangChain BaseChatModel 实例。

    参数：
        provider: 'openai', 'anthropic', 'deepseek' 之一。
            如果为 None，则使用 settings.default_llm_provider。

    返回：
        已配置的 BaseChatModel 实例。

    抛出：
        ValueError: 如果 provider 名称未知。
    """
    name = provider or settings.default_llm_provider

    if name == "openai":
        cfg = settings.llm_openai
        return ChatOpenAI(
            model=cfg.model,
            api_key=cfg.api_key or None,
            base_url=cfg.base_url or None,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

    elif name == "anthropic":
        cfg = settings.llm_anthropic
        return ChatAnthropic(
            model=cfg.model,
            api_key=cfg.api_key or None,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

    elif name == "deepseek":
        cfg = settings.llm_deepseek
        # DeepSeek 兼容 OpenAI API
        return ChatOpenAI(
            model=cfg.model,
            api_key=cfg.api_key or None,
            base_url=cfg.base_url or None,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )

    raise ValueError(
        f"Unknown LLM provider: {name}. Valid options: openai, anthropic, deepseek"
    )


def get_default_model() -> BaseChatModel:
    """使用默认 provider 创建模型（便捷方法）。"""
    return create_llm_model()
