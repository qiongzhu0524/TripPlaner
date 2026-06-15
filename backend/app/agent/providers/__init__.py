"""LLM 提供者工厂。

用法：
    from app.agent.providers import create_llm_provider
    llm = create_llm_provider("openai")
    response = await llm.generate(messages=[...], tools=[...])
"""

from app.agent.providers.base import LLMProvider, LLMResponse, StreamEvent, TokenUsage
from app.agent.providers.openai import OpenAIProvider
from app.agent.providers.anthropic import AnthropicProvider
from app.agent.providers.deepseek import DeepSeekProvider


def create_llm_provider(provider_name: str | None = None) -> LLMProvider:
    """工厂函数：返回已配置的 LLM 提供者实例。

    参数：
        provider_name: 'openai', 'anthropic', 'deepseek' 之一。
            如果为 None，则使用 settings.default_llm_provider。

    返回：
        一个可直接使用的 LLMProvider 实例。

    抛出：
        ValueError: 如果 provider_name 未知。
    """
    from app.config import settings

    name = provider_name or settings.default_llm_provider

    if name == "openai":
        return OpenAIProvider()
    elif name == "anthropic":
        return AnthropicProvider()
    elif name == "deepseek":
        return DeepSeekProvider()

    raise ValueError(f"Unknown LLM provider: {name}. Valid options: openai, anthropic, deepseek")


__all__ = [
    "LLMProvider",
    "LLMResponse",
    "StreamEvent",
    "TokenUsage",
    "OpenAIProvider",
    "AnthropicProvider",
    "DeepSeekProvider",
    "create_llm_provider",
]
