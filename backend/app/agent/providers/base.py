"""所有 LLM 提供者的抽象基类。

所有提供者必须实现：
- generate(messages, tools) -> LLMResponse
- generate_stream(messages, tools) -> AsyncIterator[StreamEvent]
- count_tokens(messages) -> int
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenUsage:
    """LLM 调用的令牌使用统计。"""

    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMResponse:
    """来自任何 LLM 提供者的标准化响应。"""

    content: str
    tool_calls: list[dict] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    finish_reason: str = "stop"


@dataclass
class StreamEvent:
    """流式响应中的单个事件。

    type 取值：
        "content"    — 文本增量（data 为 str）
        "tool_call"  — 增量工具调用（data 为包含 index 和 function 部分的 dict）
        "finish"     — 流结束（data 为包含最终 tool_calls 和 usage 的 dict）
    """

    type: str
    data: Any


class LLMProvider(ABC):
    """所有 LLM 提供者的抽象基类。

    每个提供者将其原生响应格式标准化为 LLMResponse/StreamEvent，
    使得 ReAct 智能体无需修改即可与任何后端协同工作。
    """

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """生成补全（非流式）。

        参数：
            messages: OpenAI 格式的消息字典列表。
            tools: 可选的 OpenAI 工具格式的工具定义列表。
            **kwargs: 提供者特定的覆盖参数（temperature, max_tokens 等）。

        返回：
            标准化的 LLMResponse。
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        """生成补全（流式）。

        为每个内容增量、工具调用片段或完成信号生成 StreamEvent。
        """
        ...

    def count_tokens(self, messages: list[dict]) -> int:
        """计算消息中的近似令牌数。

        默认是基于字符的粗略估计（约每令牌 4 个字符）。
        拥有精确分词器的提供者应重写此方法。
        """
        total = sum(len(str(m.get("content", ""))) for m in messages)
        return max(1, total // 4)

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """返回提供者标识字符串。"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """返回正在使用的模型名称。"""
        ...
