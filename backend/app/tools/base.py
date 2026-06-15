"""抽象工具协议和基础实现。

所有工具（基于MCP和本地）都实现ToolProtocol接口，
为ReAct代理提供统一的方式来发现和调用工具。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """任何工具执行的标准结果。"""

    success: bool
    data: Any = None
    error: str | None = None


class ToolProtocol(ABC):
    """每个工具必须实现的协议。

    每个工具有：
    - 元数据：名称、描述、参数（JSON Schema）
    - 执行：execute(**kwargs) → ToolResult
    - 序列化：to_openai_format() → 提供给LLM的字典
    """

    name: str
    description: str
    parameters: dict  # 工具输入的JSON Schema

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """使用给定的关键字参数执行工具。

        参数：
            **kwargs: 匹配工具参数JSON Schema的参数。

        返回：
            ToolResult，包含成功/数据或失败/错误。
        """
        ...

    def to_openai_format(self) -> dict:
        """以OpenAI函数调用格式导出工具定义。

        返回：
            包含"type": "function"和"function": {name, description, parameters}的字典。
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __repr__(self) -> str:
        return f"Tool({self.name})"
