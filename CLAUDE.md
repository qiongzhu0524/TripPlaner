# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI 驱动的旅行规划助手，采用 **FastAPI + Vue 3** 前后端分离架构。项目按`重构建议.md`中的 7 阶段重建，包含自研 ReAct Agent、MCP 工具集成、记忆系统和 RAG 管道。所有注释已中文化。

## 常用命令

### 后端 (Python 3.12, FastAPI)

```bash
cd backend

# 安装依赖
uv sync --group dev          # 含dev/rag依赖
pip install -e ".[dev,rag]"  # pip方式

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
请求 → FastAPI Router → Service → ReActAgent → LLM Provider (OpenAI/Anthropic/DeepSeek)
                              ↓
                    ToolRegistry (本地工具 + MCP工具)
                              ↓
                    MemoryManager (短期对话 + 长期用户画像)
                              ↓
                    RAG Pipeline (知识库检索)
```

### 核心分层

| 层 | 路径 | 职责 |
|---|---|---|
| API 路由 | `app/api/routes/` | HTTP 端点：`/api/chat`、`/api/trip`、`/api/map`、`/health` |
| 业务服务 | `app/services/` | 编排层，协调 agent、工具、记忆 |
| Agent | `app/agent/` | ReAct 循环 (`react.py`) + 三个 LLM Provider |
| 工具系统 | `app/tools/` | `ToolRegistry` 管理本地工具 (高德地图) 和 MCP 工具 |
| 记忆系统 | `app/memory/` | `MemoryManager` 协调短期记忆 (对话) + 长期记忆 (用户画像) |
| RAG | `app/rag/` | 知识库嵌入 + pgvector 向量检索 |
| 工作流 | `app/workflow/` | DAG 引擎 (已实现但 API 尚未接入) |

### Agent 系统（项目灵魂）

`app/agent/react.py` 是自研的 ReAct Agent，约 200 行。流程：
1. 构建消息列表 (system prompt + 历史 + 用户输入)
2. 调用 LLM，LLM 返回文本或 tool_calls
3. 如有 tool_calls → 执行工具 → 追加结果 → 回到步骤 2
4. 最大迭代 10 次，工具重试 2 次

`app/agent/context.py` 的 `ContextBuilder` 负责构建 system prompt，注入工具描述、用户画像、对话摘要、旅行参数。

三个 LLM Provider 通过 `create_llm_provider(name)` 工厂创建。DeepSeekProvider 继承自 OpenAIProvider (API 兼容)。

### 工具系统

- **本地工具** (`app/tools/local/`): 高德地图 (文本搜索、天气、驾车/公交/步行路线)、路线优化 (最近邻TSP)、日期工具、货币转换
- **MCP 工具** (`app/tools/mcp/`): `MCPToolAdapter` 和 `MCPSessionManager` — **当前为桩代码**，真正的 MCP 服务器连接尚未实现

### 记忆系统

- **短期记忆** (`short_term.py`): 按 session_id 管理对话，token 预算内检索。超预算时用轻量 LLM 摘要压缩
- **长期记忆** (`long_term.py`): 用户画像 CRUD，用 LLM 从对话提取偏好。`generate_embedding()` 和 `search_similar_users()` 是占位

### 数据库

PostgreSQL + pgvector。ORM 模型在 `app/memory/models.py` 和 `app/rag/store.py`。**无 Alembic 迁移**，表结构需通过应用代码或手动创建。连接 DSN 通过环境变量 `DATABASE__DSN` 配置。

### 前端路由

- `/` — `HomeView`: 旅行参数表单
- `/result/:id` — `ResultView`: 展示行程结果（Markdown 渲染、地图占位、统计）

`vite.config.ts` 将 `/api` 代理到 `http://localhost:8000`。

## 关键设计决策

1. **自研 Agent 而非 LangChain/LangGraph** — ReAct 循环完全自研，避免框架耦合
2. **全异步** — 使用 `asyncpg`、`httpx.AsyncClient`、`AsyncOpenAI`
3. **MCP 协议** — 工具接口遵循 Model Context Protocol 标准，但适配器尚未完成真实连接
4. **TripService 未使用 WorkflowEngine** — 当前 `POST /api/trip/plan` 手动编排流程；工作流引擎已定义在 `app/workflow/` 但未接入 API
5. **配置通过 pydantic-settings** — 所有环境变量在 `app/config.py` 中定义，支持嵌套模型 (LLM、API、Database、Memory)
