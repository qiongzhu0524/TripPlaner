"""ToolRegistry：所有代理工具的中央注册表。

支持：
- 运行时注册/注销工具
- 按名称执行工具
- 以OpenAI函数调用格式导出工具schema
- 列出可用工具以供内省
"""

import logging
from typing import Any

from app.tools.base import ToolProtocol, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """代理可用所有工具的中央注册表和执行中心。

    用法：
        registry = ToolRegistry()
        registry.register(AmapTextSearchTool())
        registry.register(WeatherTool())
        tools_schema = registry.to_openai_tools_format()
        result = await registry.execute("maps_text_search", keywords="故宫", city="北京")
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolProtocol] = {}

    def register(self, tool: ToolProtocol) -> None:
        """注册一个工具实例。

        参数：
            tool: 一个ToolProtocol实现。

        抛出：
            ValueError: 如果同名的工具已经注册。
        """
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> None:
        """按名称移除工具。

        参数：
            name: 要移除的工具名称。

        抛出：
            KeyError: 如果工具未注册。
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        del self._tools[name]
        logger.info(f"Unregistered tool: {name}")

    def get(self, name: str) -> ToolProtocol:
        """按名称获取工具。

        抛出：
            KeyError: 如果未找到。
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry. Available: {self.list_names()}")
        return self._tools[name]

    async def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """按名称使用关键字参数执行工具。

        参数：
            name: 工具名称。
            **kwargs: 匹配工具输入schema的参数。

        返回：
            ToolResult，包含成功/数据或失败/错误。
        """
        tool = self.get(name)
        logger.debug(f"Executing tool '{name}' with args: {kwargs}")
        try:
            result = await tool.execute(**kwargs)
            if result.success:
                logger.debug(f"Tool '{name}' succeeded")
            else:
                logger.warning(f"Tool '{name}' returned error: {result.error}")
            return result
        except Exception as e:
            logger.error(f"Tool '{name}' raised exception: {e}")
            return ToolResult(success=False, error=str(e), data=None)

    def to_openai_tools_format(self) -> list[dict]:
        """以OpenAI函数调用格式导出所有已注册的工具。

        返回：
            工具定义字典列表。
        """
        return [tool.to_openai_format() for tool in self._tools.values()]

    def list_names(self) -> list[str]:
        """返回已注册工具名称列表。"""
        return list(self._tools.keys())

    def list_tools(self) -> list[dict]:
        """返回用于内省/调试的工具元数据。

        返回：
            包含名称、描述、参数的字典列表。
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
