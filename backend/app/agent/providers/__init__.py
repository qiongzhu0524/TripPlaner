"""LLM Provider 工厂 — 基于 LangChain 实现。

用法：
    from app.agent.providers import create_llm_model
    model = create_llm_model("openai")
    response = await model.ainvoke(messages)
"""

from app.agent.providers.models import create_llm_model, get_default_model

__all__ = ["create_llm_model", "get_default_model"]
