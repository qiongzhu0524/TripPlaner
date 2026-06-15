"""Agent 领域模型：ToolCall、ToolResult、AgentContext。"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """表示 Agent 的单个工具调用。"""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """工具执行的结果。"""

    success: bool
    data: Any = None
    error: str | None = None


@dataclass
class AgentContext:
    """每次 Agent 调用时组装的上下文。"""

    user_id: str
    user_profile: dict | None = None
    conversation_history: list[dict] = field(default_factory=list)
    session_id: str | None = None
