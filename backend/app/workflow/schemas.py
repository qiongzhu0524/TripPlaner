"""工作流schemas：工作流DAG定义、Step、StepResult。"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepType(str, Enum):
    """工作流步骤类型。"""

    MEMORY = "memory"  # 加载/保存记忆
    AGENT = "agent"  # 调用ReAct代理
    TOOL = "tool"  # 直接工具执行（无代理推理）
    PARALLEL = "parallel"  # 并行执行多个子步骤


class StepStatus(str, Enum):
    """步骤的执行状态。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Step:
    """工作流DAG中的单个步骤。

    属性：
        name: 唯一的步骤名称。
        type: 步骤类型（memory, agent, tool, parallel）。
        config: 步骤特定的配置字典。
        depends_on: 在此步骤运行前必须完成的步骤名称列表。
        allow_failure: 如果为True，即使此步骤失败，工作流也会继续。
    """

    name: str
    type: StepType
    config: dict = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    allow_failure: bool = False


@dataclass
class StepResult:
    """单个工作流步骤执行的结果。"""

    step_name: str
    status: StepStatus
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class Workflow:
    """步骤的有向无环图（DAG）。

    步骤按拓扑顺序执行。满足依赖关系的步骤
    可以并行运行（Phase 6处理调度）。
    """

    name: str
    description: str = ""
    steps: list[Step] = field(default_factory=list)

    def get_step(self, name: str) -> Step:
        """按名称查找步骤。如果找不到则抛出KeyError。"""
        for s in self.steps:
            if s.name == name:
                return s
        raise KeyError(f"Step '{name}' not found in workflow '{self.name}'")

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """返回邻接表：step_name → [依赖的步骤]。"""
        graph: dict[str, list[str]] = {s.name: [] for s in self.steps}
        for s in self.steps:
            for dep in s.depends_on:
                if dep in graph:
                    graph[dep].append(s.name)
        return graph
