# TripPlaner AI — 基于 LangGraph 的智能旅行规划助手

<div align="center">

**AI 驱动 · ReAct Agent · 多 LLM 切换 · 记忆系统 · RAG 检索 · 流式响应**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-4FC08D?style=flat&logo=vue.js)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-1C3C3C?style=flat)](https://github.com/langchain-ai/langgraph)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://opensource.org/licenses/MIT)

</div>

---

## 目录

- [一、这是什么项目？](#一这是什么项目)
- [二、有什么特点？](#二有什么特点)
- [三、快速上手](#三快速上手)
- [四、架构概览](#四架构概览)
- [五、从 HelloAgents 到这里的思考](#五从-helloagents-到这里的思考)
- [六、关键模块详解](#六关键模块详解)
- [七、API 与使用指南](#七api-与使用指南)
- [八、进一步参与](#八进一步参与)
- [九、路线图](#九路线图)
- [附录](#附录)

---

## 一、这是什么项目？

### 1.1 一句话描述

**TripPlaner AI** 是一个基于 LangGraph 的 AI 旅行规划应用。用户告诉它目的地、日期和偏好，它就会自动调用高德地图搜索景点、查询天气、规划路线，生成一份包含吃住行和费用估算的个性化多日行程。

### 1.2 它解决什么问题？

你打开 ChatGPT 说"帮我规划一个北京三日游"，它会给你一段看起来不错的文字。但你细看会发现——推荐的餐厅可能已经关门、景区路线不顺路、天气信息靠猜、而且每次对话它都不记得你上次说过"我吃不了辣"。

**LLM 只负责"说"，真正的旅行规划需要"做"：**

- 🔍 **搜索真实的 POI**（景点、餐厅、酒店）——不是 LLM 训练数据里的幻觉
- 🌦️ **查询真实天气**——不是靠训练截止日期的记忆
- 🗺️ **规划真实路线**——不是"大概"而是"具体怎么走"
- 💾 **记住你的偏好**——不是每次都从头问
- 📚 **参考本地攻略**——把北京人写的北京攻略喂给 AI，而不是让它凭空编

TripPlaner AI 做的就是把一个能"说"的 LLM 变成一个能"行动"的 Agent——给它工具、给它记忆、给它知识库，让它真正能干这件事。

### 1.3 适用场景和读者

| 你是谁 | 你能得到什么 |
|--------|-------------|
| 🧑‍💻 **Agent 开发者** | 一个 LangGraph ReAct Agent 的完整实践参考——工具绑定、记忆注入、StateGraph 编排、流式输出 |
| 🏗️ **架构学习者** | Agent 系统如何分层（API → Service → Graph → Nodes），LangChain + LangGraph 如何配合使用 |
| 🔄 **HelloAgents 迁移者** | 从 HelloAgents 到 LangGraph 的迁移路径、遇到的问题和最终方案——为什么选了 LangGraph 而不是自研 |
| 🚀 **创业者/产品经理** | 可运行的旅行规划 MVP，Docker 一键启动，快速验证想法 |
| 📖 **RAG 实践者** | pgvector 向量检索 + Markdown 知识库分块 + LLM 上下文注入的完整 RAG 管道 |

---

## 二、有什么特点？

### 2.1 核心功能一览

```mermaid
graph LR
    A[👤 用户填写表单] --> B[⚙️ LangGraph StateGraph 编排]
    B --> C[🧠 load_profile: 加载记忆]
    C --> D[✍️ prepare_prompt: 构建提示词]
    D --> E[🤖 execute_agent: ReAct Agent 循环]
    E --> F[🔧 工具调用: 搜索/天气/路线]
    E --> G[📚 RAG: 知识库检索]
    F --> H[📤 extract_output: 提取结果]
    H --> I[💾 save_memory: 持久化]
    I --> J[🌊 SSE 流式返回前端]
```

### 2.2 能力矩阵

| 能力 | 实现方式 | 一句话说明 |
|------|---------|-----------|
| 🤖 **ReAct Agent** | LangGraph `create_react_agent` | LLM 与工具自动交替的多轮对话循环，不是黑盒 |
| 🔌 **三 LLM 支持** | LangChain `ChatOpenAI` / `ChatAnthropic` | OpenAI / Anthropic Claude / DeepSeek，环境变量一行切换 |
| 🛠️ **8 个内置工具** | LangChain `StructuredTool` 包装 | 高德 POI 搜索、天气、驾车/公交/步行路线、TSP 路线优化、货币转换、日期工具 |
| 💾 **双系统记忆** | 自研 `MemoryManager` | 短期对话（滑动窗口 + 摘要压缩）+ 长期用户画像（LLM 驱动偏好提取） |
| 📚 **RAG 知识库** | OpenAI Embedding + pgvector | Markdown 攻略分块 → 向量检索 → 自动注入 Agent 上下文 |
| 🔀 **工作流编排** | LangGraph `StateGraph` | 5 节点流水线：加载画像 → 构建提示 → 执行Agent → 提取输出 → 保存记忆 |
| 🌊 **流式响应** | LangGraph `astream_events` + SSE | 用户实时观察 Agent 的每一步思考和工具调用 |
| 🖥️ **Vue 3 前端** | Vue 3 + TypeScript | 旅行参数表单 → 实时进度 → Markdown 行程渲染 |
| 🐳 **一键部署** | Docker Compose | 含 PostgreSQL + pgvector，一条命令启动 |
| 📝 **全中文注释** | — | 所有代码注释、变量名、文档均为中文 |

### 2.3 与其他方案的对比

| 维度 | HelloAgents | 纯 LangChain 封装 | **TripPlaner (本项目)** |
|------|------------|-------------------|------------------------|
| Agent 内核 | 黑盒 SimpleAgent | 自己写 while 循环 | **LangGraph create_react_agent** |
| 可观测性 | ❌ 看不到内部 | ✅ 自己控制 | ✅ StateGraph 节点级可观测 + 流式事件 |
| LLM 切换 | ❌ 仅 OpenAI | ✅ 手动适配 | ✅ LangChain 抽象，一行切换 |
| 记忆系统 | ❌ 无 | 需自己实现 | ✅ 双系统记忆，开箱即用 |
| 工作流 | ❌ 无 | 需自己实现 | ✅ StateGraph 编排，可扩展 |
| 代码量 | ~100 行 | ~500 行 | **~2000 行（含完整功能）** |
| 基础设施 | ❌ 无 | 需自己搭 | ✅ Docker、配置中心、日志、中间件 |
| 前端 | 无 | 无 | ✅ Vue 3 完整前端 |

> **一句话：** HelloAgents 太简陋，纯手写太累，LangGraph 给了我们刚好够用的抽象——看得清内部、改得动代码、但不用从零造轮子。

---

## 三、快速上手

### 3.1 你需要准备

- [Docker + Docker Compose](https://docs.docker.com/compose/)（推荐，含数据库）
- **高德地图 API Key** → [免费申请](https://lbs.amap.com/)
- **至少一个 LLM API Key**（OpenAI / Anthropic / DeepSeek 任选其一）

### 3.2 Docker Compose 一键启动

```bash
# 1. 克隆
git clone <repo-url> && cd TripPlaner_2

# 2. 配置 API Key
cp backend/.env.example backend/.env
# 编辑 backend/.env，至少填：
#   AMAP__API_KEY=你的高德key
#   LLM_OPENAI__API_KEY=sk-xxx    （三选一即可）

# 3. 启动后端 + 数据库
docker compose up -d

# 4. 验证
curl http://localhost:8000/health
# → {"status": "ok", "version": "0.1.0"}
```

### 3.3 启动前端

```bash
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173
```

### 3.4 手动启动（无 Docker）

后端：

```bash
cd backend
cp .env.example .env   # 编辑 API Key

# 使用 uv（推荐，更快）
uv sync --group dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 或 pip
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,rag]"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

前端同上。

### 3.5 环境变量参考

```bash
# ===== 必填 =====
AMAP__API_KEY=your_amap_web_api_key          # 高德地图

# 三选一
LLM_OPENAI__API_KEY=sk-xxx
LLM_ANTHROPIC__API_KEY=sk-ant-xxx
LLM_DEEPSEEK__API_KEY=sk-xxx

# ===== 可选 =====
DEFAULT_LLM_PROVIDER=openai                  # openai / anthropic / deepseek
DATABASE__DSN=postgresql+asyncpg://tripuser:tripsecret@localhost:5432/tripplaner
MEMORY__SHORT_TERM_MAX_TOKENS=4000           # 短期记忆 token 预算
LOG_LEVEL=INFO                                # DEBUG / INFO / WARNING
```

> 完整配置见 [`backend/.env.example`](backend/.env.example)。使用 `__`（双下划线）映射嵌套配置，如 `LLM_OPENAI__API_KEY` → `settings.llm_openai.api_key`。

### 3.6 最简示例：通过 API 生成行程

```bash
curl -X POST http://localhost:8000/api/trip/plan \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "destination": "北京",
    "start_date": "2026-07-01",
    "days": 3,
    "travel_style": "balanced",
    "budget_level": "midrange",
    "interests": ["历史古迹", "美食"]
  }'
```

返回结果包含完整的逐日行程、工具调用记录、token 用量统计。

流式观察 Agent 思考过程：

```bash
curl -N "http://localhost:8000/api/chat/message/stream?user_id=demo&message=推荐北京故宫周边的餐厅"
```

> 浏览器访问 `http://localhost:8000/docs` 查看完整的 Swagger API 文档。

---

## 四、架构概览

### 4.1 请求全链路

```mermaid
graph TB
    subgraph 前端["前端 (Vue 3)"]
        HV[HomeView: 旅行表单] --> API[API Service: Axios + SSE]
        API --> RV[ResultView: 行程展示]
    end

    前端 -->|HTTP / SSE| FastAPI

    subgraph 后端["FastAPI (端口 8000)"]
        subgraph Routes["API 路由层"]
            R1[POST /api/trip/plan]
            R2[GET /api/chat/message/stream]
            R3[GET /api/map/poi/*]
        end

        Routes --> TripService[TripService: 服务编排层]

        TripService --> Graph[LangGraph StateGraph: 5 节点流水线]

        subgraph Nodes["StateGraph 结点"]
            N1[load_profile] --> N2[prepare_prompt]
            N2 --> N3[execute_agent]
            N3 --> N4[extract_output]
            N4 --> N5[save_memory]
        end

        N1 --> MM[MemoryManager: 短期 + 长期]
        N2 --> CB[ContextBuilder: System Prompt 工厂]
        N3 --> ReactAgent[create_react_agent: LLM ↔ Tools]
        N5 --> MM

        ReactAgent --> Model[LangChain BaseChatModel]
        ReactAgent --> Tools[LangChain StructuredTool x8]
    end

    Model --> External[OpenAI / Claude / DeepSeek]
    Tools --> Amap[高德地图 Web API]
```

### 4.2 目录结构

```
TripPlaner_2/
├── backend/
│   ├── app/
│   │   ├── agent/                          # Agent 系统
│   │   │   ├── react.py                    #   ReActAgent: 封装 create_react_agent + 流式
│   │   │   ├── context.py                  #   ContextBuilder: System Prompt 工厂
│   │   │   ├── streaming.py               #   SSE 事件生成器
│   │   │   └── providers/
│   │   │       ├── __init__.py             #     工厂函数入口
│   │   │       └── models.py               #     create_llm_model(): ChatOpenAI/ChatAnthropic
│   │   ├── tools/                          # 工具系统
│   │   │   ├── langchain_tools.py          #   create_all_tools(): 包装为 LangChain StructuredTool
│   │   │   ├── local/                      #   本地工具（httpx 直连高德 API）
│   │   │   │   ├── amap_direct.py          #     5 个高德地图工具（搜索/天气/驾驶/公交/步行）
│   │   │   │   ├── route_optimizer.py      #     TSP 路线优化（最近邻贪心）
│   │   │   │   ├── currency.py             #     货币转换
│   │   │   │   └── date_utils.py           #     日期工具
│   │   │   └── mcp/                        #   MCP 协议适配器（桩代码，预留扩展）
│   │   │       ├── adapter.py
│   │   │       └── manager.py
│   │   ├── memory/                         # 记忆系统
│   │   │   ├── manager.py                  #   MemoryManager: 统一入口
│   │   │   ├── short_term.py              #   短期记忆：滑动窗口 + Token 预算 + 摘要压缩
│   │   │   ├── long_term.py               #   长期记忆：用户画像 CRUD + LLM 偏好提取
│   │   │   ├── chat_history.py            #   LangChain BaseChatMessageHistory 适配器
│   │   │   └── models.py                  #   ORM 模型（ConversationMessage, UserProfileRecord）
│   │   ├── rag/                            # RAG 知识检索
│   │   │   ├── embedder.py                #   OpenAI text-embedding-3-small，带 LRU 缓存
│   │   │   ├── loader.py                  #   Markdown 加载 + 按标题层级分块
│   │   │   ├── retriever.py               #   嵌入 → 检索 → 格式化上下文
│   │   │   └── store.py                   #   pgvector CRUD + 余弦相似度搜索
│   │   ├── workflow/                       # LangGraph 工作流
│   │   │   ├── state.py                   #   TripPlanState TypedDict（所有状态字段）
│   │   │   ├── nodes.py                   #   5 个结点函数（load/prepare/execute/extract/save）
│   │   │   └── graph.py                   #   build_trip_planning_graph() + 单例管理
│   │   ├── api/                            # API 层
│   │   │   ├── middleware.py              #   请求日志中间件
│   │   │   └── routes/
│   │   │       ├── trip.py                #     POST /api/trip/plan
│   │   │       ├── chat.py                #     GET /api/chat/message/stream
│   │   │       ├── map.py                 #     直连地图工具（绕过 Agent）
│   │   │       └── health.py              #     GET /health
│   │   ├── services/
│   │   │   └── trip_service.py            #   TripService: 编排入口（初始化图 + 调用执行）
│   │   ├── models/                         # 领域模型
│   │   │   ├── agent.py                   #   AgentContext, ToolCall
│   │   │   ├── schemas.py                 #   Pydantic API 模型
│   │   │   └── trip.py                    #   POI, WeatherForecast 等
│   │   ├── config.py                      # pydantic-settings 配置中心
│   │   ├── database.py                    # SQLAlchemy 异步引擎 + 会话工厂
│   │   └── main.py                        # FastAPI 应用工厂（lifespan 管理）
│   ├── data/knowledge/                    # 知识库（Markdown 旅行攻略）
│   │   ├── beijing.md
│   │   └── shanghai.md
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── views/                         # HomeView.vue + ResultView.vue
│   │   ├── components/                    # TripForm.vue + DayPlanCard.vue + MapView.vue
│   │   ├── services/api.ts               # API 客户端 + SSE EventSource 消费
│   │   └── types/trip.ts                 # TypeScript 类型定义
│   └── vite.config.ts                    # 开发服务器 + API 代理
├── docker-compose.yml                     # App + PostgreSQL pgvector
├── CLAUDE.md                              # Claude Code 项目指南
└── README.md                              # 本文
```

### 4.3 核心设计决策

| 决策 | 选择 | 为什么 |
|------|------|--------|
| Agent 框架 | **LangGraph** `create_react_agent` | 不是黑盒——StateGraph 可见每个节点和边；不是从零造轮子——200 行代码完成 Agent 和流式处理 |
| LLM 抽象 | **LangChain** `BaseChatModel` | OpenAI/Anthropic/DeepSeek 统一接口，`bind_tools()` 自动处理工具绑定格式差异 |
| 工具包装 | **LangChain** `StructuredTool` | Pydantic args_schema 自动校验参数；`from_function()` 一行包装现有函数 |
| 工作流编排 | **LangGraph** `StateGraph` | 5 节点流水线天然可见；`add_messages` reducer 自动合并消息；支持嵌套子图 |
| 记忆存储 | **自研** + LangChain 适配器 | 短期/长期记忆逻辑自研（业务强相关）；通过 `ConversationMessageHistory` 适配 LangChain 接口 |
| 数据库 | **PostgreSQL + pgvector** | 一库多用：对话 + 用户画像 + 向量检索 |
| IO 模型 | **全异步** `async/await` | Agent 等待 LLM 响应是 IO 密集场景，异步大幅提升吞吐 |
| 配置管理 | **pydantic-settings** | 类型安全、嵌套模型、`__` 分隔符支持 |
| 代码注释 | **全部中文** | 降低中文开发者阅读门槛 |

---

## 五、从 HelloAgents 到这里的思考

> 这一章是我写这个项目最想表达的东西——不是"用什么框架"，而是"为什么这么选"。

### 5.1 起点：HelloAgents 的简洁之美

这个项目的前身基于 Datawhale 社区的 [HelloAgents](https://github.com/jjyaoao/HelloAgents) 框架。HelloAgents 有一个很大的优点——**极简**：

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

amap_tool = MCPTool(name="amap", server_command=["uvx", "amap-mcp-server"], auto_expand=True)
agent = SimpleAgent(name="旅行规划助手", llm=HelloAgentsLLM())
agent.add_tool(amap_tool)
result = agent.run("帮我规划北京三日游")
```

不到 10 行代码就能运行一个 Agent。对于教学和快速验证来说，这非常优雅。

### 5.2 转折：做产品时遇到的问题

但当我想把它做成一个真正的旅行规划产品时，问题一个接一个暴露：

| # | 问题 | 直接后果 |
|---|------|---------|
| 1 | `SimpleAgent` 是**完全黑盒**，看不到 LLM 推理过程 | 工具调用失败时不知道是 prompt 问题还是参数问题，调试全靠猜 |
| 2 | `HelloAgentsLLM` **只封装 OpenAI** | 想用 Claude 或 DeepSeek 降低推理成本？改框架源码 |
| 3 | **没有记忆** | 用户每次都要重复"我喜欢历史、吃辣、预算中等" |
| 4 | **没有知识检索** | LLM 不知道北京的樱花什么时候开、故宫周一闭馆——这些实时信息无法注入 |
| 5 | MCP 工具**依赖外部子进程** | amap-mcp-server 崩溃 → 整个 Agent 不可用；调试 MCP 通信异常困难 |
| 6 | **阻塞式 API**，前端干等 30-60 秒 | 用户不知道 Agent 在干嘛——"是死了还是在思考？" |
| 7 | **所有逻辑塞进一次调用** | 搜索 POI + 查天气 + 生成行程——LLM 容易遗漏步骤，没有结构化保障 |

### 5.3 两条路径的选择

面对这些问题，我面前有两条路：

**路径 A：自己从零写一个 Agent 框架**

这就是旧版 README 描述的方向——200 行自研 ReAct 循环、自定义 DAG 工作流引擎、自定义 ToolRegistry。这条路有教育意义——你确实会彻底搞懂 Agent 的每个细节。

但实际开发中，我遇到了新问题：自己写的 Provider 层要处理 OpenAI 和 Anthropic 的工具调用格式差异、流式事件格式差异、消息角色差异——这些不是 Agent 逻辑，而是**接入工程的苦力活**。而且自己写的 DAG 引擎在拓扑排序、错误传递、子图嵌套等方面有大量边界 case 需要处理。

**路径 B：基于 LangGraph + LangChain，自己只写业务逻辑**

LangGraph 的 `create_react_agent` 已经解决了 ReAct 循环——而且不是黑盒，它编译成一个 StateGraph，你可以看到每个节点。LangChain 的 `BaseChatModel` 已经处理了多 Provider 的工具绑定、消息格式、流式事件差异。`StructuredTool` 已经提供了 Pydantic 参数校验。

> **关键洞察：LangGraph 不是又一个"黑盒框架"。它是给你一个可见的图结构——你能看到节点、边、状态流转——然后用你自己的函数填充这些节点。这和"自研"的区别只是：LangGraph 写了执行引擎（拓扑排序、重试、流式事件），你写了业务逻辑（加载记忆、构建 prompt、保存结果）。**

我最终选了 **B**，原因是：

1. **LangGraph 的抽象层次刚好** —— 它管理消息流、工具循环、状态传递，但不隐藏任何业务决策
2. **LangChain 解决了枯燥的接入工程** —— 我不想花两周调试 Anthropic 的 tool_use 格式
3. **不重复造轮子，但保持控制权** —— 图的结构是我的、节点的逻辑是我的、记忆系统是我的、RAG 管道是我的
4. **代码量合理** —— 约 2000 行业务代码 + 成熟的依赖，而不是 5000 行自研框架 + 1000 行业务代码

### 5.4 对比总结

```mermaid
graph TB
    subgraph HelloAgents["阶段1: HelloAgents"]
        H1[黑盒 Agent] --> H2[单 LLM]
        H1 --> H3[无记忆]
        H1 --> H4[无 RAG]
        H1 --> H5[阻塞 API]
    end

    subgraph SelfBuilt["❌ 阶段2: 纯自研（放弃）"]
        S1["200行 ReAct + 自定义DAG + 手工Provider适配"]
        S2["问题: OpenAI/Anthropic格式差异是体力活<br/>DAG引擎边界case多<br/>维护成本高"]
    end

    subgraph Current["✅ 阶段2: LangGraph（当前）"]
        C1[LangGraph StateGraph 编排] --> C2[create_react_agent 子图]
        C1 --> C3[自研 MemoryManager]
        C1 --> C4[自研 RAG Pipeline]
        C2 --> C5[LangChain 多 Provider]
        C5 --> C6[OpenAI / Claude / DeepSeek]
    end

    HelloAgents -->|"黑盒→可见<br/>简陋→完整"| SelfBuilt
    SelfBuilt -->|"不重复造轮子<br/>LangGraph足够透明"| Current
```

| 维度 | HelloAgents | 纯自研 | **本项目 (LangGraph)** |
|------|------------|--------|----------------------|
| 代码可见性 | ❌ 黑盒 | ✅ 完全透明 | ✅ 图结构完全可见 |
| 开发效率 | ✅ 很快 | ❌ 慢（体力活多） | ✅ 快（只写业务逻辑） |
| LLM 切换 | ❌ 仅 OpenAI | ⚠️ 需手工适配 | ✅ LangChain 抽象 |
| 基础设施 | ❌ 无 | ⚠️ 需自己搭 | ✅ 成熟可靠 |
| 可维护性 | ❌ 依赖第三方 | ⚠️ 全是自己维护 | ✅ 合理分工 |
| **适合什么** | 教学/原型 | 学习 Agent 原理 | **生产级应用** |

> **这个项目的工程哲学：** 选对抽象层——底层交给成熟的框架（LangChain/LangGraph），上层保留完全控制（记忆、RAG、工具、编排逻辑）。不因为框架有过教训就走向另一个极端（拒绝一切框架），也不因为有成熟框架就用它替代所有思考和设计。

---

## 六、关键模块详解

### 6.1 ReAct Agent（Agent 的心脏）

代码见 [`backend/app/agent/react.py`](backend/app/agent/react.py)。

核心不是"自己写循环"——而是**理解 LangGraph 的 create_react_agent 到底做了什么**，并在它之上构建流式、重试、结果提取：

```python
class ReActAgent:
    def __init__(self, model, tools, max_iterations=10, max_tool_retries=2):
        self._model_with_tools = model.bind_tools(tools)     # 1. 绑定工具
        self._graph = create_react_agent(                     # 2. 编译子图
            model=self._model_with_tools,
            tools=self._wrap_tools_with_retry(tools),        # 3. 包装重试逻辑
        )

    async def execute(self, user_input, system_prompt, history, stream_handler):
        messages = [SystemMessage(system_prompt)] + history + [HumanMessage(user_input)]
        if stream_handler:
            return await self._execute_streaming(messages, ...)
        else:
            return await self._execute_non_streaming(messages, ...)
```

**create_react_agent 编译后的图实际执行：**

```mermaid
graph LR
    START --> Agent[agent: LLM 推理]
    Agent -->|有 tool_calls| Tools[tools: 执行工具]
    Agent -->|无 tool_calls| END
    Tools --> Agent
```

这就是 ReAct 循环的本质：`Agent → Tools → Agent → ... → END`。LangGraph 帮你管理这个循环的图结构，你注入的是工具包装（重试逻辑）和结果提取。

**流式事件处理**（`_execute_streaming`）监听 LangGraph 的 `astream_events` v2 API：
- `on_chat_model_stream` → 推送给前端（LLM 正在生成文字）
- `on_tool_start` → 推送给前端（开始执行某个工具）
- `on_tool_end` → 推送给前端（工具执行完毕）

### 6.2 LLM Provider 工厂

代码见 [`backend/app/agent/providers/models.py`](backend/app/agent/providers/models.py)。

```python
def create_llm_model(provider=None) -> BaseChatModel:
    name = provider or settings.default_llm_provider
    if name == "openai":     return ChatOpenAI(model=..., api_key=...)
    if name == "anthropic":  return ChatAnthropic(model=..., api_key=...)
    if name == "deepseek":   return ChatOpenAI(model=..., base_url="https://api.deepseek.com")
```

**为什么不用自研 Provider？** LangChain 已经处理好了：
- 工具定义格式转换（OpenAI 的 `function` 格式 vs Anthropic 的 `tool_use` 格式）
- 流式事件归一化
- 消息角色映射

这些是纯体力活——知道 DeepSeek 兼容 OpenAI API 后，切换只需改 `base_url`，一行代码。**把精力花在业务逻辑上，而不是 API 格式适配。**

### 6.3 工具系统

代码见 [`backend/app/tools/langchain_tools.py`](backend/app/tools/langchain_tools.py)。

每个工具是：
1. 一个 **async Python 函数**（调用高德 HTTP API）→ 写在 `local/` 下
2. 一个 **Pydantic args_schema**（定义参数类型和校验）→ 写在函数旁
3. 通过 `StructuredTool.from_function()` **包装为 LangChain 工具**

```python
# 高德 POI 搜索
class TextSearchInput(BaseModel):
    keywords: str = Field(description="搜索关键词，如'故宫'、'川菜'")
    city: str = Field(description="城市名称，如'北京'")

async def search_poi(keywords, city):  # 调用高德 API
    ...

# 一行包装
StructuredTool.from_function(
    name="maps_text_search",
    description="搜索指定城市的 POI（景点、餐厅等）",
    args_schema=TextSearchInput,
    coroutine=search_poi,
)
```

**MCP 适配器** （`tools/mcp/`）当前为预留桩代码。未来接入真正的 MCP 服务器时，只需实现 `MCPToolAdapter`，无需改动 Agent 核心。这样设计的原因是：本地直连工具已经稳定可用，MCP 的标准化接入可以后续渐进式完成。

### 6.4 记忆系统

代码见 [`backend/app/memory/`](backend/app/memory/)。

```mermaid
sequenceDiagram
    participant S as TripService
    participant MM as MemoryManager
    participant STM as ShortTermMemory
    participant LTM as LongTermMemory
    participant DB as PostgreSQL

    Note over S,DB: === Agent 执行前 ===
    S->>MM: build_context(user_id, session_id)
    MM->>LTM: get_profile(user_id)
    DB-->>LTM: 用户画像 (JSON)
    MM->>STM: get_history(session_id)
    DB-->>STM: 最近 N 条消息
    LTM-->>MM: profile_summary
    STM-->>MM: conversation_history
    MM-->>S: AgentContext (注入 System Prompt)

    Note over S,DB: === Agent 执行后 ===
    S->>MM: save_interaction(user_id, session_id, messages)
    MM->>STM: add_message(user) → add_message(tool*) → add_message(assistant)
    MM->>STM: summarize_and_compress()  (超 token 预算时)
    MM->>LTM: extract_preferences()  (LLM 从对话提取偏好)
```

**短期记忆** （`short_term.py`）：
- 按 `session_id` 管理对话
- 滑动窗口：在 token 预算内保留最近消息
- 超预算时：用轻量 LLM 将旧消息总结压缩（保留约 40% 最近消息）

**长期记忆** （`long_term.py`）：
- 用户画像 CRUD：`travel_style`、`budget_level`、`interests`、`dietary_preferences` 等
- LLM 驱动的偏好自动提取——用户说"我喜欢吃辣，预算不要太贵"→ 自动更新画像
- `generate_embedding()` 和 `search_similar_users()` 预留 pgvector 用户协作推荐

**LangChain 适配** （`chat_history.py`）：`ConversationMessageHistory` 将现有数据库表适配为 LangChain `BaseChatMessageHistory`——这样 LangGraph/LangChain 可以直接读写我们的数据，不需要第二套存储。

### 6.5 RAG 知识检索

代码见 [`backend/app/rag/`](backend/app/rag/)。

```mermaid
graph LR
    A["知识库: data/knowledge/beijing.md"] --> B["loader.py: 按 ### 标题分块<br/>保留层级路径 → 北京 > 美食 > 烤鸭"]
    B --> C["embedder.py: OpenAI text-embedding-3-small<br/>1536维向量 + LRU缓存"]
    C --> D["store.py: pgvector 存储"]
    E["用户查询: 故宫周边有什么好吃的"] --> C
    C --> F["store.py: 余弦相似度检索 Top-K"]
    F --> G["retriever.py: 合并、去重、格式化"]
    G --> H["注入 Agent System Prompt"]
```

**分块策略**：按 Markdown 的 `###` 标题层级分块，每个块携带完整的层级路径（如 `北京 > 美食 > 烤鸭`），最小块 50 字符。这确保检索到的片段有清晰的上下文标签。

**嵌入模型**：OpenAI `text-embedding-3-small`（1536 维），带 LRU 缓存避免重复调用。

### 6.6 LangGraph StateGraph 编排

代码见 [`backend/app/workflow/graph.py`](backend/app/workflow/graph.py) 和 [`backend/app/workflow/nodes.py`](backend/app/workflow/nodes.py)。

```mermaid
graph TB
    START --> N1[load_profile: 从 MemoryManager 加载用户画像和对话历史]
    N1 --> N2[prepare_prompt: 用 ContextBuilder 构建 System Prompt + HumanMessage]
    N2 --> N3[execute_agent: create_react_agent 子图<br/>LLM ↔ Tools 自动循环]
    N3 --> N4[extract_output: 从消息列表提取最终回复、工具调用、token 用量]
    N4 --> N5[save_memory: 交互持久化 + 摘要压缩 + 偏好提取]
    N5 --> END
```

状态定义（`state.py`）使用 `TypedDict`，`messages` 字段有 `add_messages` reducer——LangGraph 自动追加消息而不是覆盖。

`TripService`（`services/trip_service.py`）是编排入口：
1. 构建初始状态
2. 调用 `graph.ainvoke()` 或 `graph.astream_events()`
3. 翻译流事件为前端 SSE 格式

---

## 七、API 与使用指南

### 7.1 API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/trip/plan` | 🎯 生成旅行计划（核心接口） |
| `GET` | `/api/chat/message/stream` | 🌊 SSE 流式聊天 |
| `GET` | `/api/map/poi/search` | POI 搜索（绕过 Agent 直连） |
| `POST` | `/api/map/route` | 路线规划 |
| `GET` | `/api/map/weather` | 天气查询 |

完整文档：`http://localhost:8000/docs`

### 7.2 切换 LLM

```bash
# 环境变量方式
echo "DEFAULT_LLM_PROVIDER=anthropic" >> backend/.env

# Docker Compose
DEFAULT_LLM_PROVIDER=deepseek docker compose up -d
```

### 7.3 加载自定义知识库

将 Markdown 攻略放入 `backend/data/knowledge/`，然后索引：

```python
from app.rag.loader import MarkdownKnowledgeLoader
from app.rag.store import KnowledgeVectorStore
from app.rag.embedder import Embedder

loader = MarkdownKnowledgeLoader("backend/data/knowledge/")
chunks = loader.load_all()

embedder = Embedder()
store = KnowledgeVectorStore(session)
for chunk in chunks:
    embedding = await embedder.embed(chunk.content)
    await store.add_chunk(chunk, embedding)
```

### 7.4 SSE 事件格式

Agent 流式执行时，前端通过 EventSource 收到的 SSE 事件：

```
event: llm_response
data: {"content": "我来搜索故宫周边的餐厅...", "tool_calls": []}

event: tool_result
data: {"tool": "maps_text_search", "arguments": {"keywords":"餐厅","city":"北京"}, "result": "找到15个POI..."}

event: tool_result
data: {"tool": "maps_weather", "arguments": {"city":"北京"}, "result": "北京今日晴，22-30°C..."}

event: llm_response
data: {"content": "根据搜索结果，为您推荐...", "tool_calls": []}
```

用户在前端看到的是 Agent **正在思考的实时过程**，而不是等待 30 秒后的一个结果。

---

## 八、进一步参与

### 8.1 开发环境搭建

```bash
# 后端
cd backend
uv sync --group dev
cp .env.example .env

# 前端
cd frontend
npm install
```

### 8.2 代码规范

提交前执行：

```bash
cd backend
uv run ruff check .          # Lint
uv run mypy app/             # 类型检查
uv run pytest                # 测试
```

### 8.3 项目依赖

| 依赖 | 用途 |
|------|------|
| `langgraph` | ReAct Agent 子图 + StateGraph 编排 |
| `langchain` + `langchain-core` | BaseChatModel 抽象 + BaseTool 接口 + 消息类型 |
| `langchain-openai` | ChatOpenAI (OpenAI + DeepSeek) |
| `langchain-anthropic` | ChatAnthropic |
| `fastapi[standard]` | Web 框架 + API 自动文档 |
| `sqlalchemy[asyncio]` | 异步 ORM |
| `asyncpg` | PostgreSQL 异步驱动 |
| `pgvector` | 向量存储扩展 |
| `httpx` | 异步 HTTP（高德 API 调用） |
| `pydantic-settings` | 配置管理 |
| `mcp` | MCP 协议 SDK（预留） |

### 8.4 如何贡献

欢迎提交 Issue 和 PR。以下是几个适合入手的贡献方向：

- 🗺️ **扩展知识库**：为更多城市撰写 Markdown 攻略（参考现有 `beijing.md` 格式）
- 🔧 **完善 MCP 连接**：实现 `MCPToolAdapter.connect()` 连接真正的 amap-mcp-server
- 🧪 **补充测试**：为核心模块编写更多单元测试和集成测试
- 🌐 **前端增强**：`MapView.vue` 接入高德 JS API 展示地图；优化移动端适配
- 🔐 **认证系统**：用户注册/登录、session 管理
- 📦 **Docker 优化**：多阶段构建、生产环境配置

---

## 九、路线图

### 已完成 ✅

- [x] **ReAct Agent** — LangGraph `create_react_agent` + 流式事件 + 工具重试
- [x] **三 LLM Provider** — OpenAI / Anthropic / DeepSeek，LangChain 统一接口
- [x] **8 个本地工具** — 高德地图 x5 + 路线优化 + 货币 + 日期
- [x] **双系统记忆** — 短期滑动窗口 + 长期用户画像 + LLM 偏好提取
- [x] **RAG 知识库** — OpenAI Embedding + pgvector + Markdown 分块
- [x] **LangGraph 工作流** — 5 节点 StateGraph 编排
- [x] **SSE 流式响应** — LangGraph astream_events → SSE → 前端实时展示
- [x] **Vue 3 前端** — 旅行表单 + 行程渲染 + 实时流式消费
- [x] **Docker Compose** — 一键启动（App + PostgreSQL + pgvector）

### 待完成 🔲

- [ ] **MCP 工具真实连接** — `MCPToolAdapter` 完整实现，通过标准协议接入第三方工具
- [ ] **用户协作推荐** — 用户画像向量化 + pgvector 相似用户推荐
- [ ] **Alembic 迁移** — 替代当前的自动建表
- [ ] **更多城市知识库** — 扩充 `data/knowledge/` 覆盖更多目的地
- [ ] **前端地图集成** — `MapView.vue` 接入高德 JS API
- [ ] **用户认证系统** — 注册/登录/session 管理
- [ ] **集成测试 + E2E 测试** — 完善测试覆盖
- [ ] **前端移动端适配** — 响应式优化

---

## 附录

### A. 致谢

- [HelloAgents](https://github.com/jjyaoao/HelloAgents) — 这个项目的起点，启发了第一版架构
- [LangGraph](https://github.com/langchain-ai/langgraph) — 提供了 Agent 和 StateGraph 的坚实基础
- [LangChain](https://github.com/langchain-ai/langchain) — LLM 抽象和工具集成
- [高德地图开放平台](https://lbs.amap.com/) — 地图、POI、天气、路线数据
- [amap-mcp-server](https://github.com/sugarforever/amap-mcp-server) — 高德 MCP 工具参考实现

### B. 参考文档

- [CLAUDE.md](CLAUDE.md) — Claude Code 开发指南（含完整架构分层和常用命令）
- [参考.md](参考.md) — HelloAgents 旧版项目文档
- [重构建议.md](重构建议.md) — 7 阶段重构规划

---

<div align="center">

**TripPlaner AI** — 用 LangGraph 把 LLM 变成一个真正能"干活"的旅行规划 Agent 🚀

*选对抽象，比什么都自己写更重要*

</div>
