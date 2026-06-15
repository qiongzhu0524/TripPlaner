"""工作流引擎：逐步执行工作流DAG。

处理：
- 基于依赖关系的步骤拓扑排序
- 顺序执行：每个步骤仅在其依赖完成后运行
- 错误处理：步骤可以标记为 allow_failure=True
- 并行子步骤：PARALLEL类型的步骤并发运行其子步骤
"""

import asyncio
import logging
import time
from typing import Any

from app.workflow.schemas import Step, StepResult, StepStatus, StepType, Workflow

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """执行工作流DAG。

    用法：
        engine = WorkflowEngine(agent=agent, tool_registry=registry, memory=memory)
        workflow = TRIP_PLANNING_WORKFLOW
        results = await engine.execute(workflow, context={"destination": "北京", ...})
    """

    def __init__(
        self,
        agent=None,  # ReActAgent实例
        tool_registry=None,  # ToolRegistry实例
        memory_manager=None,  # MemoryManager实例
    ) -> None:
        """使用所需的服务进行初始化。

        参数：
            agent: 用于agent类型步骤的ReActAgent。
            tool_registry: 用于tool类型步骤的ToolRegistry。
            memory_manager: 用于memory类型步骤的MemoryManager。
        """
        self.agent = agent
        self.tool_registry = tool_registry
        self.memory = memory_manager

    async def execute(
        self,
        workflow: Workflow,
        context: dict[str, Any],
    ) -> list[StepResult]:
        """按拓扑顺序执行所有步骤。

        参数：
            workflow: 要执行的工作流DAG。
            context: 传递给每个步骤的共享上下文字典。

        返回：
            StepResult列表，每个步骤一个。
        """
        if not workflow.steps:
            logger.warning(f"Workflow '{workflow.name}' has no steps")
            return []

        logger.info(f"Executing workflow '{workflow.name}' with {len(workflow.steps)} steps")

        results: dict[str, StepResult] = {}
        completed: set[str] = set()

        # 简单的顺序执行（Phase 6 MVP）。
        # 完整的实现会进行拓扑排序 + 并行分发。
        for step in workflow.steps:
            # 检查依赖
            deps_met = all(dep in completed for dep in step.depends_on)
            if not deps_met:
                missing = [d for d in step.depends_on if d not in completed]
                logger.warning(f"Step '{step.name}': dependencies not met: {missing}")
                result = StepResult(
                    step_name=step.name,
                    status=StepStatus.FAILED,
                    error=f"Dependencies not met: {missing}",
                )
                results[step.name] = result
                if not step.allow_failure:
                    break
                continue

            # 执行步骤
            result = await self._execute_step(step, context)
            results[step.name] = result

            # 将输出存入上下文以供下游步骤使用
            if result.status == StepStatus.COMPLETED and result.output is not None:
                context[step.name] = result.output

            if result.status == StepStatus.COMPLETED:
                completed.add(step.name)
            elif result.status == StepStatus.FAILED and not step.allow_failure:
                logger.error(
                    f"Workflow '{workflow.name}' aborted: step '{step.name}' failed"
                )
                break

        logger.info(
            f"Workflow '{workflow.name}' completed: "
            f"{len(completed)}/{len(workflow.steps)} steps succeeded"
        )
        return list(results.values())

    async def _execute_step(
        self,
        step: Step,
        context: dict[str, Any],
    ) -> StepResult:
        """根据步骤类型执行单个步骤。

        参数：
            step: 要执行的步骤。
            context: 共享的执行上下文。

        返回：
            包含状态和输出的StepResult。
        """
        start_time = time.monotonic()
        logger.info(f"  → Step '{step.name}' [{step.type.value}]")

        try:
            if step.type == StepType.MEMORY:
                output = await self._execute_memory_step(step, context)
            elif step.type == StepType.AGENT:
                output = await self._execute_agent_step(step, context)
            elif step.type == StepType.TOOL:
                output = await self._execute_tool_step(step, context)
            elif step.type == StepType.PARALLEL:
                output = await self._execute_parallel_step(step, context)
            else:
                return StepResult(
                    step_name=step.name,
                    status=StepStatus.FAILED,
                    error=f"Unknown step type: {step.type}",
                )

            duration = (time.monotonic() - start_time) * 1000
            return StepResult(
                step_name=step.name,
                status=StepStatus.COMPLETED,
                output=output,
                duration_ms=round(duration, 1),
            )

        except Exception as e:
            duration = (time.monotonic() - start_time) * 1000
            logger.error(f"Step '{step.name}' failed: {e}")
            return StepResult(
                step_name=step.name,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=round(duration, 1),
            )

    async def _execute_memory_step(
        self,
        step: Step,
        context: dict[str, Any],
    ) -> Any:
        """执行memory类型的步骤。

        配置键：
        - action: "load" | "save"
        - user_id, session_id: 标识符
        """
        action = step.config.get("action", "load")
        user_id = context.get("user_id", step.config.get("user_id", "default"))
        session_id = context.get("session_id", step.config.get("session_id", "default"))

        if action == "load":
            if self.memory:
                agent_ctx = await self.memory.build_context(user_id, session_id)
                return {
                    "user_profile": agent_ctx.user_profile,
                    "history": agent_ctx.conversation_history,
                }
            return {"user_profile": None, "history": []}

        elif action == "save":
            if self.memory:
                await self.memory.save_interaction(
                    user_id=user_id,
                    session_id=session_id,
                    user_message=context.get("user_message", ""),
                    assistant_message=context.get("assistant_message", ""),
                    tool_calls=context.get("tool_calls"),
                )
            return {"saved": True}

        return {}

    async def _execute_agent_step(
        self,
        step: Step,
        context: dict[str, Any],
    ) -> Any:
        """执行agent类型的步骤。

        配置键：
        - system_prompt: str（可以使用{key}引用上下文值）
        - user_input: str（给代理的提示）
        """
        if not self.agent:
            return {"error": "Agent not configured"}

        system_prompt = step.config.get("system_prompt", "").format(**context)
        user_input = step.config.get("user_input", "").format(**context)
        history = context.get("history", [])

        result = await self.agent.execute(
            user_input=user_input,
            system_prompt=system_prompt,
            conversation_history=history,
        )

        return {
            "content": result.content,
            "tool_calls": result.tool_calls,
            "iterations": result.iterations,
            "success": result.success,
        }

    async def _execute_tool_step(
        self,
        step: Step,
        context: dict[str, Any],
    ) -> Any:
        """执行tool类型的步骤。

        配置键：
        - tool_name: str — 注册表中的工具名称
        - arguments: dict — 工具的关键字参数
        """
        if not self.tool_registry:
            return {"error": "Tool registry not configured"}

        tool_name = step.config.get("tool_name", "")
        args = step.config.get("arguments", {})

        # 解析参数中的上下文引用（例如 {"city": "{destination}"}）
        resolved_args = {}
        for k, v in args.items():
            if isinstance(v, str) and v.startswith("{") and v.endswith("}"):
                key = v[1:-1]
                resolved_args[k] = context.get(key, v)
            else:
                resolved_args[k] = v

        result = await self.tool_registry.execute(tool_name, **resolved_args)
        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
        }

    async def _execute_parallel_step(
        self,
        step: Step,
        context: dict[str, Any],
    ) -> Any:
        """并行执行多个子步骤。

        配置键：
        - sub_steps: 步骤字典列表（与工作流步骤格式相同）
        """
        sub_steps_config = step.config.get("sub_steps", [])
        if not sub_steps_config:
            return []

        # 将子步骤配置转换为Step对象
        sub_steps = [
            Step(
                name=f"{step.name}.{s.get('name', i)}",
                type=StepType(s.get("type", "tool")),
                config=s.get("config", {}),
                allow_failure=s.get("allow_failure", True),
            )
            for i, s in enumerate(sub_steps_config)
        ]

        # 并发执行所有子步骤
        tasks = [self._execute_step(s, context.copy()) for s in sub_steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            {
                "step": sub_steps[i].name,
                "status": r.status.value if isinstance(r, StepResult) else "failed",
                "output": r.output if isinstance(r, StepResult) else None,
                "error": r.error if isinstance(r, StepResult) else str(r),
            }
            for i, r in enumerate(results)
        ]
