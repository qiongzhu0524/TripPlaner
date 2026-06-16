# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI 驱动的旅行规划助手，采用 **FastAPI + Vue 3** 前后端分离架构。Agent 系统基于 **LangGraph**（`create_react_agent` + 自定义 StateGraph），集成高德地图工具、记忆系统和 RAG 管道。所有注释已中文化。

## 常用命令

### 后端 (Python 3.12, FastAPI)

```bash
cd backend

# 安装依赖
uv sync --group dev          # 含dev/rag依赖

# 启动开发服务器 (端口 8000)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 运行测试
uv run pytest                           # 全部测试
uv run pytest -k test_something         # 单个测试
uv run pytest --cov=app --cov-report=html

# 代码检查
uv run ruff check .                     # Lint
uv run ruff check . --fix               # Lint + 自动修复
uv run mypy app/                        # 类型检查
```

### 前端 (Vue 3, TypeScript)

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器 (端口 5173, API代理 -> localhost:8000)
npm run dev

# 构建
npm run build

# 类型检查
npx vue-tsc --noEmit
```

### Docker

```bash
# 启动全部服务 (app + PostgreSQL pgvector)
docker compose up -d

# 仅数据库
docker compose up -d db
```

## 架构概览

```
请求 → FastAPI Router → TripService → LangGraph StateGraph
                              ↓
              load_profile → prepare_prompt → execute_agent* → extract_output → save_memory
                                                   ↓
                              * execute_agent = create_react_agent 子图 (LLM ↔ Tools 循环)
                                                   ↓
                              MemoryManager (短期对话 + 长期用户画像)
```

### 核心分层

| 层 | 路径 | 职责 |
|---|---|---|
| API 路由 | `app/api/routes/` | HTTP 端点：`/api/chat`、`/api/trip`、`/api/map`、`/health` |
| 业务服务 | `app/services/trip_service.py` | 编排层：构建 LangGraph 初始状态，调用图执行，翻译流事件 |
| Agent | `app/agent/` | `ReActAgent` 封装 `langgraph.prebuilt.create_react_agent`；`ContextBuilder` 构建 system prompt；`streaming.py` 提供 SSE 流式传输 |
| 工作流图 | `app/workflow/` | LangGraph StateGraph：5 节点流水线（加载画像→构建提示→执行Agent→提取输出→保存记忆） |
| 工具系统 | `app/tools/` | `langchain_tools.py` 将所有本地工具包装为 LangChain `StructuredTool`；MCP 适配器为桩代码 |
| 记忆系统 | `app/memory/` | `MemoryManager` 协调短期记忆 (对话) + 长期记忆 (用户画像)；`chat_history.py` 适配 LangChain `BaseChatMessageHistory` 接口 |
| RAG | `app/rag/` | 知识库嵌入 + pgvector 向量检索 |
| LLM Provider | `app/agent/providers/models.py` | 工厂函数 `create_llm_model()` 返回 LangChain `ChatOpenAI` / `ChatAnthropic` 实例 |

### Agent 系统（LangGraph 驱动）

`app/agent/react.py` — `ReActAgent` 类封装 `langgraph.prebuilt.create_react_agent`：
1. 初始化时绑定工具到模型（`model.bind_tools(tools)`），编译 create_react_agent 子图
2. `execute()` 构建消息列表（SystemMessage + 历史 + HumanMessage），调用 `graph.ainvoke()` 或 `graph.astream_events()`
3. 工具重试：`_wrap_tools_with_retry()` 给每个工具包装失败重试逻辑（默认 2 次）
4. 最大迭代次数通过 `recursion_limit` 控制（`max_iterations * 2 + 5`）

`app/agent/providers/models.py` — `create_llm_model(provider)` 工厂：
- `"openai"` → `ChatOpenAI`
- `"anthropic"` → `ChatAnthropic`
- `"deepseek"` → `ChatOpenAI` + `base_url="https://api.deepseek.com"`（API 兼容）

`app/agent/context.py` — `ContextBuilder` 构建 system prompt，注入工具描述、用户画像、对话摘要、旅行参数。

### 工作流图（LangGraph StateGraph）

`app/workflow/graph.py` — `build_trip_planning_graph()` 构建 5 节点流水线：

```
START → load_profile → prepare_prompt → execute_agent → extract_output → save_memory → END
```

- `load_profile`：从 MemoryManager 加载用户画像和对话历史
- `prepare_prompt`：用 ContextBuilder 构建 System Prompt + HumanMessage
- `execute_agent`：`create_react_agent` 子图（LLM ↔ Tools 自动循环）
- `extract_output`：从消息列表提取最终回复、工具调用、token 用量
- `save_memory`：将交互持久化到记忆系统

状态定义在 `app/workflow/state.py`（`TripPlanState` TypedDict）。图由 `TripService` 实例化并调用，不是 API 层直接操作。

### 工具系统

- **本地工具** (`app/tools/local/`): 高德地图（文本搜索、天气、驾车/公交/步行路线）、路线优化（最近邻TSP）、日期工具、货币转换 — 每个工具有 Pydantic `args_schema`
- **工具包装** (`app/tools/langchain_tools.py`): `create_all_tools()` 将所有本地函数包装为 LangChain `StructuredTool` 列表
- **MCP 工具** (`app/tools/mcp/`): `MCPToolAdapter` 和 `MCPSessionManager` — **当前为桩代码**，真实 MCP 连接尚未实现

### 记忆系统

- **短期记忆** (`short_term.py`): 按 session_id 管理对话，token 预算内检索。超预算时用 LLM 摘要压缩（保留约 40% 最近消息，其余总结）
- **长期记忆** (`long_term.py`): 用户画像 CRUD，用 LLM 从对话提取偏好。`generate_embedding()` 和 `search_similar_users()` 是占位
- **LangChain 适配** (`chat_history.py`): `ConversationMessageHistory` 将现有 `conversation_messages` 表适配为 LangChain `BaseChatMessageHistory` 接口
- **统一入口** (`manager.py`): `MemoryManager` 协调短/长期记忆，提供 `build_context()` 和 `save_interaction()` 两个核心方法

### 数据库

PostgreSQL + pgvector。ORM 模型在 `app/memory/models.py`（`ConversationMessage`, `UserProfileRecord`）。`app/database.py` 提供 `async_session_factory` 和 FastAPI 依赖 `get_db()`。**无 Alembic 迁移**，表结构需手动创建。连接 DSN 通过环境变量 `DATABASE__DSN` 配置。

### 前端路由

- `/` — `HomeView`: 旅行参数表单
- `/result/:id` — `ResultView`: 展示行程结果（Markdown 渲染、地图占位、统计）

`vite.config.ts` 将 `/api` 代理到 `http://localhost:8000`。

### 流式传输

`app/agent/streaming.py` — `sse_event_generator()` 使用 `asyncio.Queue` 桥接 Agent 回调与 SSE 输出。
`app/services/trip_service.py` — `TripService._translate_event()` 将 LangGraph `astream_events` 事件翻译为前端可消费的 SSE 格式。
事件类型：`start` → `llm_response`（文本增量）/ `tool_result`（工具执行） → `done`。

## 关键设计决策

1. **LangGraph 而非自研 Agent** — ReAct 循环使用 `langgraph.prebuilt.create_react_agent`，行程规划使用自定义 StateGraph 流水线
2. **LangChain 工具包装** — 所有本地工具通过 `StructuredTool.from_function()` 包装，MCP 工具待接入
3. **全异步** — 使用 `asyncpg`、`httpx.AsyncClient`、LangChain 异步 API（`ainvoke`、`astream_events`）
4. **TripService 驱动 LangGraph 图** — `POST /api/trip/plan` 通过 TripService 构建初始状态并调用图；图单例可通过 `set_trip_planning_graph()` 在 lifespan 中预编译
5. **配置通过 pydantic-settings** — 所有环境变量在 `app/config.py` 中定义，使用 `__` 嵌套分隔符（如 `LLM_OPENAI__API_KEY`）
6. **无 Alembic 迁移** — 数据库表通过应用代码或手动 SQL 创建；pgvector 扩展需手动启用
