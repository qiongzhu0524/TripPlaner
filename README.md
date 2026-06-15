# TripPlaner AI — 从 HelloAgents 到自研 Agent 框架的工程实践

<div align="center">

**AI 驱动的智能旅行规划助手 | 自研 ReAct Agent | 多 LLM 支持 | 记忆系统 | RAG 知识库 | DAG 工作流引擎**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.x-4FC08D?style=flat&logo=vue.js)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://opensource.org/licenses/MIT)

</div>

---

## 目录

- [一、项目介绍](#一项目介绍)
- [二、HelloAgents 起源与遇到的问题](#二helloagents-起源与遇到的问题)
- [三、重构之路——七大问题的解决方案](#三重构之路七大问题的解决方案)
- [四、架构全景](#四架构全景)
- [五、快速开始](#五快速开始)
- [六、使用指南](#六使用指南)
- [七、深入理解关键模块](#七深入理解关键模块)
- [八、工程实践](#八工程实践)
- [九、路线图](#九路线图)
- [十、贡献指南](#十贡献指南)
- [附录](#附录)

---

## 一、项目介绍

### 1.1 这是什么？

TripPlaner AI 是一个**完全自研 AI Agent 框架**的旅行规划助手。用户只需输入目的地、日期和偏好，系统便会自动调用高德地图工具搜索景点、查询天气、优化路线，生成一份包含餐饮、住宿、交通和费用估算的个性化多日行程。

但它的定位不止于此——它更是一个 **AI 工程能力的展示平台**，完整呈现了从依赖第三方框架到自研核心的工程迁移全过程。如果你正在学习 AI Agent 开发，或者正考虑从 LangChain/HelloAgents 等框架迁移到自研方案，这个项目将为你提供一个真实的参考。

### 1.2 核心能力一览

```mermaid
graph LR
    A[用户填写表单] --> B[后端接收请求]
    B --> C[MemoryManager 加载用户画像]
    C --> D[ContextBuilder 构建系统提示词]
    D --> E[ReAct Agent 循环调用工具]
    E --> F[搜索景点 / 查询天气 / 规划路线]
    F --> G[生成行程]
    G --> H[保存到记忆系统]
    H --> I[前端展示结果]
```

- 🧠 **自研 ReAct Agent**：200 行核心循环，从框架黑盒变为完全可控
- 🔌 **三 LLM Provider 切换**：OpenAI / Anthropic Claude / DeepSeek，一行代码切换
- 🛠️ **8 个内置工具**：高德地图 POI 搜索、天气、驾车/公交/步行路线、TSP 路线优化、货币转换、日期工具
- 🧩 **双路径工具系统**：本地直连高德 API（生产可用）+ MCP 协议适配器（扩展预留）
- 💾 **双系统记忆**：短期记忆（滑动窗口 + 自动摘要压缩）+ 长期记忆（用户画像 + LLM 驱动偏好提取）
- 📚 **RAG 知识库检索**：OpenAI Embedding + pgvector 向量检索，自动注入本地旅行攻略
- ⚙️ **DAG 工作流引擎**：拓扑排序执行，支持并行子步骤和依赖解析
- 🌊 **SSE 流式响应**：实时观察 Agent 的每一个思考和工具调用
- 🖥️ **Vue 3 前端**：响应式表单 + Markdown 行程渲染 + 实时流式聊天

### 1.3 适用读者

- 对 **AI Agent 工程实践** 感兴趣的开发者
- 正考虑从 LangChain / HelloAgents 迁移到自研方案的团队
- 想深入理解 ReAct 模式、RAG、记忆系统、工作流引擎的研究者
- 希望快速搭建旅行规划应用的创业者

---

## 二、HelloAgents 起源与遇到的问题

### 2.1 最初的架构

这个项目的前身叫 **"HelloAgents 智能旅行助手"**（详见 [参考.md](./参考.md)），基于 Datawhale 社区的 [HelloAgents](https://github.com/jjyaoao/HelloAgents) 框架构建。

```python
# 旧架构：HelloAgents 时代的核心代码
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

# 创建高德地图 MCP 工具（依赖外部子进程 amap-mcp-server）
amap_tool = MCPTool(
    name="amap",
    server_command=["uvx", "amap-mcp-server"],
    env={"AMAP_MAPS_API_KEY": "your_api_key"},
    auto_expand=True
)

# 创建 Agent —— SimpleAgent 是一个黑盒，你无法看到内部如何推理
agent = SimpleAgent(
    name="旅行规划助手",
    llm=HelloAgentsLLM(),          # 只能使用 OpenAI
    system_prompt="你是一个专业的旅行规划助手..."
)
agent.add_tool(amap_tool)

# 调用后阻塞等待，无法观察中间过程
result = agent.run("帮我规划北京三日游")
```

那时的架构非常简单：

```mermaid
graph TB
    A[API 路由] --> B[HelloAgents SimpleAgent 黑盒]
    B --> C[MCP 工具 依赖子进程]
    B --> D[HelloAgentsLLM 只封装了 OpenAI]
```

项目结构也只有寥寥几个模块：

```
helloagents-trip-planner/
├── backend/
│   ├── agents/          # Agent 实现（调用 hello_agents 库）
│   ├── api/             # FastAPI 路由
│   ├── services/        # 薄服务层
│   └── models/          # 数据模型
└── frontend/            # Vue 前端
```

### 2.2 实际开发中遇到的七个核心问题

随着开发深入，HelloAgents 框架的限制越来越突出。以下是我们踩过的所有坑：

| # | 问题 | 具体场景 | 痛点 |
|---|------|---------|------|
| 1 | **框架黑盒** | `SimpleAgent` 的核心循环完全不可定制 | 工具调用失败时无法定位原因；无法控制迭代次数；无法观察中间推理状态；调试全靠猜 |
| 2 | **LLM 锁定** | `HelloAgentsLLM` 只封装了 OpenAI | 想切换到 Claude 或 DeepSeek？你需要去改框架源码。每个 LLM 有不同的消息格式和工具调用协议，框架帮你"屏蔽"了差异，也屏蔽了切换的可能 |
| 3 | **无记忆系统** | 每次对话都是全新的 | 用户每次都要重复"我喜欢历史景点、吃辣、预算中等"；无法积累用户画像；重复交互体验极差 |
| 4 | **无知识检索** | Agent 只能靠模型训练数据 | 北京的季节性攻略、最新的门票价格、当地的特色餐厅——这些实时信息 LLM 不知道，也无法获取 |
| 5 | **MCP 工具脆弱** | 依赖 `amap-mcp-server` 作为独立子进程运行 | 子进程崩溃 → 整个 Agent 不可用；调试 MCP 通信异常困难；无法直接控制请求参数 |
| 6 | **无工作流编排** | 一次 Agent 调用做完所有事 | 搜索 POI、查天气、生成行程全塞进一次调用——复杂场景下 LLM 容易遗漏步骤，没有结构化流程保证 |
| 7 | **无流式响应** | 阻塞式 API，前端干等 30-60 秒 | 用户看不到任何进度反馈，体验极差 — "是死了还是在思考？" |

### 2.3 迁移决策

面对这些问题，我们有两个选择：

**方案 A：换一个更大的框架（如 LangChain/LangGraph）**

❌ 引入几百 MB 的依赖，学习成本高，框架锁定更严重  
❌ 200 行能搞定的 ReAct 循环，为什么要引入一个庞大的框架？

**方案 B：完全自研**（✅ 我们选了这个）

✅ 核心代码不到 200 行，完全透明  
✅ 每个组件都可根据需求自定义  
✅ 深入理解 Agent 运行机制的每一个细节  
✅ "先搞懂再动手"——这正是 [重构建议.md](./重构建议.md) 的核心思想

重构按 7 个 Phase 推进——先搭骨架，再做灵魂（Agent），然后陆续补齐工具、记忆、RAG、工作流，最后完整交付。接下来，让我们看看每个问题是如何被解决的。

---

## 三、重构之路——七大问题的解决方案

> 从"黑盒"到"白盒"的工程进化。以下每个章节对应上面一个核心问题。

### 3.1 问题一：框架黑盒 → 自研 ReAct Agent

**核心思路：200 行代码，完全掌控 Thought → Action → Observation 循环。**

代码位于 [`backend/app/agent/react.py`](backend/app/agent/react.py)：

```python
class ReActAgent:
    """ReAct 智能体：使用 LLM + 工具迭代地推理和行动。"""

    def __init__(self, llm, tool_registry, max_iterations=10, max_tool_retries=2):
        self.llm = llm
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.max_tool_retries = max_tool_retries

    async def execute(self, user_input, system_prompt, conversation_history=None, stream_handler=None):
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_input})

        tools_schema = self.tool_registry.to_openai_tools_format()
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1

            # 步骤 1：LLM 生成响应 (Thought + Action)
            response = await self.llm.generate(messages=messages, tools=tools_schema)

            # 步骤 2：无工具调用 = 最终答案
            if not response.tool_calls:
                return AgentResult(success=True, content=response.content, ...)

            # 步骤 3：执行工具调用 (Observation)，将结果反馈给 LLM
            for tc in response.tool_calls:
                result = await self.tool_registry.execute(tc.name, **tc.args)
                messages.append({"role": "tool", "content": result.data})  # 反馈
```

**收益对比：**

| 维度 | HelloAgents SimpleAgent | 自研 ReActAgent |
|------|------------------------|-----------------|
| 可观测性 | 看不到内部状态 | `stream_handler` 回调实时观察每一步 |
| 可控性 | 固定参数，不可调 | `max_iterations`、`max_tool_retries` 完全可配置 |
| 可调试性 | 黑盒，日志极少 | 每次迭代都有完整日志 |
| 代码量 | 依赖框架（数万行） | 核心循环 **226 行** |

---

### 3.2 问题二：LLM 锁定 → 多 Provider 抽象层

**核心思路：定义统一接口，为每个 LLM 实现格式适配。**

代码位于 [`backend/app/agent/providers/`](backend/app/agent/providers/)：

```python
# base.py — 统一接口
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages, tools) -> LLMResponse: ...
    @abstractmethod
    async def generate_stream(self, messages, tools) -> AsyncIterator[StreamEvent]: ...

# __init__.py — 工厂函数
def create_llm_provider(provider_name: str | None = None) -> LLMProvider:
    name = provider_name or settings.default_llm_provider
    if name == "openai":   return OpenAIProvider()
    if name == "anthropic": return AnthropicProvider()
    if name == "deepseek":  return DeepSeekProvider()
    raise ValueError(f"Unknown provider: {name}")
```

**关键挑战：Anthropic 格式转换**

OpenAI 和 Anthropic 的消息格式、工具定义、流式事件完全不同。`AnthropicProvider`（[`anthropic.py`](backend/app/agent/providers/anthropic.py)）处理了全部格式差异：

| 维度 | OpenAI | Anthropic |
|------|--------|-----------|
| System Prompt | `role: "system"` 消息 | 独立的 `system` 参数 |
| 工具定义 | `{"type":"function", "function":{"parameters":...}}` | `{"name":"...", "input_schema":...}` |
| 工具调用 | `tool_calls: [{function: {name, arguments}}]` | `content: [{type:"tool_use", id, name, input}]` |
| 工具结果 | `role: "tool", tool_call_id: "..."` | `role: "user", content: [{type:"tool_result", tool_use_id, content}]` |
| 流式事件 | `chunk.choices[0].delta` | `content_block_start/delta/stop` |

DeepSeek 因 API 兼容 OpenAI，直接继承 `OpenAIProvider` 仅修改 base_url 和 model 名称，**仅 13 行代码**。

**收益：一行切换，零业务代码改动。**

```bash
# 环境变量切换
DEFAULT_LLM_PROVIDER=anthropic docker compose up -d
```

---

### 3.3 问题三：无记忆 → 双系统记忆架构

**核心思路：短期记忆负责对话上下文，长期记忆负责用户画像积累。**

代码位于 [`backend/app/memory/`](backend/app/memory/)：

```mermaid
graph TB
    MM[MemoryManager - manager.py]
    MM --> STM[ShortTermMemory - short_term.py]
    MM --> LTM[LongTermMemory - long_term.py]
    STM --> SW[滑动窗口: 在 token 预算内保留最近消息]
    STM --> AS[自动摘要: 超预算时用轻量 LLM 压缩旧消息]
    STM --> SI[基于 session_id 隔离不同对话]
    LTM --> UP[用户画像 CRUD: 旅行风格/预算等级/兴趣偏好/饮食要求]
    LTM --> PE[LLM 驱动的偏好自动提取]
    LTM --> VS[pgvector 语义搜索: 用户协作推荐预留]
```

**一次完整 Agent 交互的记忆流：**

```mermaid
sequenceDiagram
    participant DB as Database
    participant STM as ShortTermMemory
    participant LTM as LongTermMemory
    participant AC as AgentContext
    participant SP as System Prompt

    Note over DB,SP: Agent 执行前
    DB->>STM: get_history()
    DB->>LTM: get_profile()
    STM->>AC: 对话历史
    LTM->>AC: 用户画像
    AC->>SP: 注入 System Prompt

    Note over DB,SP: Agent 执行后
    AC->>STM: add_message(UserMessage)
    AC->>STM: add_message(ToolCalls)
    AC->>STM: add_message(AssistantMessage)
    STM->>STM: summarize_and_compress() 超预算时
    STM->>LTM: extract_preferences() LLM提取偏好
```

**关键示例：偏好自动提取**

用户说"我喜欢吃辣，预算不要太贵，对历史文化特别感兴趣"→ 系统自动提取：

```json
{
  "travel_style": "cultural",
  "budget_level": "budget",
  "interests": ["历史古迹", "博物馆"],
  "dietary_preferences": ["辣味", "中式"],
  "preferred_activities": ["逛博物馆", "历史街区漫步"]
}
```

下次用户再来，Agent **自动知道**这些偏好，无需重复询问。

---

### 3.4 问题四：无知识检索 → RAG 管道

**核心思路：将本地旅行攻略（Markdown）转为向量，在 Agent 执行时自动检索相关段落注入上下文。**

代码位于 [`backend/app/rag/`](backend/app/rag/)：

```mermaid
graph LR
    A[用户查询: 北京故宫周边有什么好吃的] --> B[Embedder.embed]
    B --> C[1536 维向量]
    C --> D[pgvector 余弦距离检索]
    D --> E[按相似度阈值筛选]
    E --> F[TravelKnowledgeRetriever.format_for_context]
    F --> G[注入 Agent System Prompt]
```

**分块策略（[`loader.py`](backend/app/rag/loader.py)）**：按 `###` 标题层级分块，保留层级路径。例如 `北京 > 美食 > 烤鸭`，确保每个块都带有清晰的上下文标签。最小块大小 50 字符，过滤无效内容。

**嵌入模型**：OpenAI `text-embedding-3-small`（1536 维），带 LRU 缓存减少重复调用开销。

**知识库示例**：[`backend/data/knowledge/beijing.md`](backend/data/knowledge/beijing.md) 和 [`shanghai.md`](backend/data/knowledge/shanghai.md) 包含景点、美食、交通、住宿、季节建议等结构化旅行攻略。

---

### 3.5 问题五：MCP 工具脆弱 → 双路径工具系统

**核心思路：本地直连高德 API 作为主路径（稳定、快速），MCP 协议适配器作为扩展路径（标准化、可扩展）。**

```mermaid
graph LR
    A[Agent 调用] --> B[本地工具 主路径]
    A --> C[MCP 工具 扩展]
    B --> D[httpx → 高德 Web API]
    D --> E[稳定/快速/生产可用]
    C --> F[stdio/SSE → amap-mcp-server]
    F --> G[标准化/待完成]
```

所有工具通过 [`ToolRegistry`](backend/app/tools/registry.py) 统一管理：

```python
registry = ToolRegistry()
# 本地工具 — 直接 HTTP 调用高德 API
registry.register(AmapTextSearchTool())       # maps_text_search
registry.register(AmapWeatherTool())          # maps_weather
registry.register(AmapDirectionDrivingTool()) # maps_direction_driving
registry.register(AmapDirectionTransitTool()) # maps_direction_transit
registry.register(AmapDirectionWalkingTool()) # maps_direction_walking
# 辅助工具
registry.register(RouteOptimizerTool())       # 最近邻 TSP 路线优化
registry.register(CurrencyConvertTool())      # 货币汇率转换
registry.register(DateRangeTool())            # 日期范围生成

# 一键导出为 OpenAI 兼容的工具格式
tools_schema = registry.to_openai_tools_format()
```

**本地工具的优势：**

- ✅ 无子进程依赖，不会因 MCP 服务器崩溃导致整个 Agent 不可用
- ✅ 精细的错误处理和重试逻辑
- ✅ 请求参数完全可控
- ✅ 响应速度快（直连 vs 通过子进程 stdio 中转）

**MCP 适配器（[`adapter.py`](backend/app/tools/mcp/adapter.py)）**：当前为桩代码，定义了 `MCPToolAdapter` 和 `MCPSessionManager` 的标准接口。未来完成 MCP 连接后，可以通过标准 MCP 协议接入任何符合规范的第三方工具服务器。

---

### 3.6 问题六：无工作流编排 → DAG 工作流引擎

**核心思路：将旅行规划拆解为结构化的 DAG 步骤，引擎按拓扑顺序执行，支持并行和依赖解析。**

代码位于 [`backend/app/workflow/`](backend/app/workflow/)：

```mermaid
graph TB
    LP[load_user_profile<br/>MEMORY: 加载用户画像] --> AD[analyze_destination<br/>AGENT: 分析目的地]
    AD --> AT[attractions<br/>PARALLEL: 并发搜索]
    AD --> RT[restaurants<br/>PARALLEL: 并发搜索]
    AD --> HT[hotels<br/>PARALLEL: 并发搜索]
    AT --> GI[generate_itinerary<br/>AGENT: 综合生成行程]
    RT --> GI
    HT --> GI
    CW[check_weather<br/>TOOL: 天气查询] --> GI
    GI --> SM[save_memory<br/>MEMORY: 持久化到记忆]
```

工作流定义示例（[`trip_planning.py`](backend/app/workflow/trip_planning.py)）：

```python
TRIP_PLANNING_WORKFLOW = Workflow(
    name="trip_planning",
    steps=[
        Step(name="load_user_profile",   type=StepType.MEMORY,   ...),
        Step(name="analyze_destination",  type=StepType.AGENT,    depends_on=["load_user_profile"]),
        Step(name="search_pois",         type=StepType.PARALLEL, depends_on=["analyze_destination"],
             config={"sub_steps": [
                 {"name": "attractions",  "config": {"tool_name": "maps_text_search", ...}},
                 {"name": "restaurants", "config": {"tool_name": "maps_text_search", ...}},
                 {"name": "hotels",      "config": {"tool_name": "maps_text_search", ...}},
             ]}),
        Step(name="generate_itinerary",  type=StepType.AGENT,    depends_on=["search_pois", "check_weather"]),
        Step(name="save_memory",         type=StepType.MEMORY,   depends_on=["generate_itinerary"]),
    ]
)
```

**当前状态**：工作流引擎已完全实现，但 API 层的 [`TripService`](backend/app/services/trip_service.py) 当前使用手动编排（6 步顺序调用）。这是有意为之——先确保每一步正确，再切换到 DAG 引擎驱动。

---

### 3.7 问题七：无流式响应 → SSE 流式传输

**核心思路：将 Agent 内部回调桥接到 FastAPI SSE，前端通过 EventSource 实时消费。**

代码位于 [`backend/app/agent/streaming.py`](backend/app/agent/streaming.py) 和 [`backend/app/api/routes/chat.py`](backend/app/api/routes/chat.py)：

```mermaid
graph TB
    A[ReActAgent.stream_handler<br/>同步回调] --> B[asyncio.Queue<br/>桥接为异步]
    B --> C[SSE StreamingResponse<br/>FastAPI]
    C --> D[EventSource API<br/>前端 Vue 3 消费]
```

SSE 事件类型：
- `start` — Agent 开始执行
- `llm_response` — LLM 返回推理结果或工具调用决策
- `tool_result` — 工具执行完毕，展示调用参数和返回数据
- `done` — 完成（含最终答案和 token 用量统计）

**最终效果**：用户可以在前端**实时看到** Agent 的每一步思考——"正在搜索北京的景点... 找到 15 个 POI... 正在查询天气... 正在规划第一天行程..."——不再是面对一个加载转圈干等 30 秒。

---

## 四、架构全景

### 4.1 整体架构图

```mermaid
graph TB
    subgraph 前端["前端 Vue 3 + TypeScript + Ant Design Vue"]
        HV[HomeView 旅行表单<br/>TripForm.vue] --> API[API Service Axios<br/>api.ts] --> RV[ResultView 行程展示<br/>DayPlanCard.vue]
    end

    前端 -->|HTTP / SSE| FastAPI

    subgraph FastAPI["FastAPI 端口 8000"]
        subgraph Routes["API 路由层"]
            R1[POST /api/trip/plan]
            R2[GET /api/chat/message/stream]
            R3[GET /api/map/poi/*]
            R4[GET /api/map/weather]
            R5[GET /health]
        end

        Routes --> Service[服务编排层<br/>TripService.plan_trip<br/>加载记忆 → 构建提示词 → Agent → 保存]

        Service --> Core

        subgraph Core["核心引擎层"]
            RA[ReActAgent<br/>react.py<br/>while tool: call LLM, exec tool, feedback]
            CB[ContextBuilder<br/>context.py<br/>注入: 工具/画像/偏好/知识/参数]
            MM[MemoryManager<br/>manager.py<br/>ShortTermMemory + LongTermMemory]
            RA --> LP[LLMProvider 3个实现]
            RA --> TR[ToolRegistry 8+工具]
            CB --> RP[RAG Pipeline<br/>embed+search]
            LP --> LLM[OpenAI / Claude / DeepSeek]
            RP --> DB[(PostgreSQL + pgvector)]
        end
    end
```

### 4.2 目录结构全览

```
TripPlaner_2/
├── backend/                            # 后端 (Python 3.12 + FastAPI)
│   ├── app/
│   │   ├── agent/                      # Agent 系统（项目灵魂）
│   │   │   ├── react.py                #   ReAct 核心循环 (~226行)
│   │   │   ├── context.py              #   System Prompt 构造器
│   │   │   ├── streaming.py            #   SSE 流式事件生成器
│   │   │   └── providers/              #   LLM 提供者层
│   │   │       ├── base.py             #     抽象基类 (统一接口)
│   │   │       ├── openai.py           #     OpenAI 实现
│   │   │       ├── anthropic.py        #     Anthropic 实现 (+格式转换)
│   │   │       └── deepseek.py         #     DeepSeek 实现 (复用OpenAI, 13行)
│   │   ├── tools/                      # 工具系统
│   │   │   ├── base.py                 #   ToolProtocol 抽象接口
│   │   │   ├── registry.py             #   工具注册表 (注册/执行/导出)
│   │   │   ├── local/                  #   本地工具 (httpx 直连高德 API)
│   │   │   │   ├── amap_direct.py      #     5个高德地图工具
│   │   │   │   ├── route_optimizer.py  #     TSP 路线优化 (最近邻贪心)
│   │   │   │   ├── currency.py         #     货币转换 (实时+静态兜底)
│   │   │   │   └── date_utils.py       #     日期范围生成
│   │   │   └── mcp/                    #   MCP 协议适配器 (桩代码)
│   │   │       ├── adapter.py          #     MCP 工具包装器
│   │   │       └── manager.py          #     MCP 会话生命周期管理
│   │   ├── memory/                     # 记忆系统
│   │   │   ├── manager.py              #   统一协调器 (build + save)
│   │   │   ├── short_term.py           #   短期记忆 (滑动窗口 + 摘要压缩)
│   │   │   ├── long_term.py            #   长期记忆 (用户画像 + 偏好提取)
│   │   │   └── models.py               #   ORM 模型 (对话 + 画像)
│   │   ├── rag/                        # RAG 管道
│   │   │   ├── embedder.py             #   嵌入模型 (OpenAI, 带缓存)
│   │   │   ├── loader.py               #   Markdown 知识库加载 + 分块
│   │   │   ├── retriever.py            #   检索器 (嵌入+搜索+格式化)
│   │   │   └── store.py                #   pgvector 向量存储 (CRUD+相似搜索)
│   │   ├── workflow/                   # DAG 工作流引擎
│   │   │   ├── engine.py               #   执行引擎 (拓扑排序+并行)
│   │   │   ├── schemas.py              #   Step/Workflow/Result 定义
│   │   │   └── trip_planning.py        #   旅行规划工作流 (6步DAG)
│   │   ├── api/                        # API 层
│   │   │   ├── middleware.py           #   请求日志中间件
│   │   │   ├── deps.py                 #   依赖注入
│   │   │   └── routes/
│   │   │       ├── trip.py             #     POST /api/trip/plan
│   │   │       ├── chat.py             #     POST/GET /api/chat (含SSE流)
│   │   │       ├── map.py              #     GET /api/map (直连工具)
│   │   │       └── health.py           #     GET /health
│   │   ├── services/                   # 业务服务层
│   │   │   ├── trip_service.py         #   行程规划编排
│   │   │   └── user_service.py         #   用户画像 CRUD
│   │   ├── models/                     # 领域模型
│   │   │   ├── agent.py                #   AgentContext, ToolCall
│   │   │   ├── schemas.py              #   Pydantic API 模型
│   │   │   ├── trip.py                 #   POI, WeatherForecast
│   │   │   └── user.py                 #   UserProfile
│   │   ├── config.py                   # pydantic-settings 配置中心
│   │   ├── database.py                 # SQLAlchemy 异步引擎
│   │   ├── logging_config.py           # 结构化日志配置
│   │   └── main.py                     # FastAPI 应用工厂
│   ├── data/knowledge/                 # 旅行攻略知识库 (Markdown)
│   │   ├── beijing.md                  #   北京旅行攻略
│   │   └── shanghai.md                 #   上海旅行攻略
│   ├── tests/                          # 测试
│   ├── pyproject.toml                  # Python 依赖管理
│   ├── Dockerfile                      # Docker 构建
│   └── .env.example                    # 环境变量模板
├── frontend/                           # 前端 (Vue 3 + TypeScript)
│   ├── src/
│   │   ├── views/
│   │   │   ├── HomeView.vue            #   主页：旅行参数表单
│   │   │   └── ResultView.vue          #   结果页：行程展示 + 统计
│   │   ├── components/
│   │   │   ├── TripForm.vue            #   表单组件（目的地/日期/风格/预算）
│   │   │   ├── DayPlanCard.vue         #   逐日行程卡片
│   │   │   └── MapView.vue             #   高德地图组件（需 API Key）
│   │   ├── services/api.ts             #   API 客户端 + SSE 流消费
│   │   ├── types/trip.ts               #   TypeScript 类型定义
│   │   ├── router/index.ts             #   路由配置
│   │   └── main.ts                     #   应用入口
│   └── vite.config.ts                  #   开发服务器 + API 代理
├── docker-compose.yml                  # App + PostgreSQL pgvector 编排
├── .gitignore
├── CLAUDE.md                           # Claude Code 项目指南
├── 参考.md                             # 旧版 HelloAgents 项目文档
└── 重构建议.md                         # 7 阶段重构规划
```

### 4.3 核心设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 框架 | **自研**，不选 LangChain/LangGraph | 200 行能搞定的核心循环，不应引入几百 MB 依赖 |
| 数据库 | **PostgreSQL + pgvector** | 一库多用：对话存储 + 用户画像 + 向量检索 |
| IO 模型 | **全异步 async/await** | Agent 调用 LLM 是典型的 IO 密集场景 |
| 配置管理 | **pydantic-settings** | 类型安全、嵌套模型、支持 `__` 环境变量分隔符 |
| 工具执行 | **本地直连优先**，MCP 为扩展 | 降低依赖风险，生产可用 |
| 工作流编排 | **DAG 引擎已实现**，TripService 手动 | 先确保每步正确，再迁移到引擎驱动 |
| 代码注释 | **全部中文** | 降低阅读门槛，面向中文开发者 |

---

## 五、快速开始

### 5.1 前置依赖

- **Python 3.12+** 和 **Node.js 18+**
- **Docker + Docker Compose**（推荐，否则需要本地 PostgreSQL + pgvector）
- **高德地图 Web 服务 API Key** → [高德开放平台](https://lbs.amap.com/) 免费申请
- **至少一个 LLM API Key**：OpenAI / Anthropic / DeepSeek

### 5.2 Docker Compose 一键启动（推荐）

```bash
# 1. 克隆项目并进入目录
git clone <repo-url> && cd TripPlaner_2

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入你的 API Key

# 3. 一键启动（含 PostgreSQL pgvector + FastAPI）
docker compose up -d

# 4. 验证
curl http://localhost:8000/health
# → {"status": "ok", "version": "0.1.0"}

# 5. 启动前端（另一个终端）
cd frontend
npm install
npm run dev

# 6. 打开 http://localhost:5173 开始使用
```

### 5.3 手动启动

**后端：**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate

# 安装依赖（含 RAG）
pip install -e ".[dev,rag]"
# 或使用 uv（更快）
uv sync --group dev

# 配置环境变量
cp .env.example .env
# 编辑 .env：至少填入 AMAP__API_KEY 和一个 LLM API Key

# 启动（端口 8000）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端：**

```bash
cd frontend
npm install
npm run dev    # 端口 5173, API 自动代理到 localhost:8000
```

### 5.4 环境变量配置

项目使用 `pydantic-settings`，通过 `__`（双下划线）支持嵌套配置：

```bash
# ========== 必填 ==========
# 高德地图
AMAP__API_KEY=your_amap_web_api_key

# 至少选一个 LLM Provider
LLM_OPENAI__API_KEY=sk-xxx
# LLM_ANTHROPIC__API_KEY=sk-ant-xxx
# LLM_DEEPSEEK__API_KEY=sk-xxx

# ========== 可选 ==========
# 默认 LLM Provider (openai / anthropic / deepseek)
DEFAULT_LLM_PROVIDER=openai

# 数据库 (Docker Compose 无需修改)
DATABASE__DSN=postgresql+asyncpg://tripuser:tripsecret@localhost:5432/tripplaner

# 记忆系统
MEMORY__MAX_SHORT_TERM_TOKENS=4000
MEMORY__SUMMARY_MODEL=gpt-4o-mini
```

完整配置项参见 [`backend/.env.example`](backend/.env.example)。

### 5.5 数据库初始化

首次启动时，表结构会通过 SQLAlchemy 自动创建。如果使用 Docker Compose，PostgreSQL + pgvector 已预配置。

如需手动初始化，连接 PostgreSQL 后执行：

```sql
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector 扩展
```

---

## 六、使用指南

### 6.1 通过前端使用

1. 访问 `http://localhost:5173`
2. 填写旅行信息：
   - **目的地**：如"北京"、"上海"
   - **出发日期 + 天数**：选择开始日期和旅行天数（1-30 天）
   - **旅行风格**：轻松 / 平衡 / 紧凑
   - **预算等级**：经济 / 中等 / 奢华
   - **兴趣爱好**：历史古迹 / 自然风光 / 美食 / 购物 / 博物馆 / 户外运动 / 亲子 / 夜生活 / 摄影
3. 点击 **"生成旅行计划"**
4. 观察 Agent 逐步调用工具的过程（实时流式展示）
5. 查看结果：
   - 📊 **统计信息**：工具调用次数、Agent 迭代轮数、Token 消耗
   - 🔧 **工具调用记录**：每个工具的调用参数和返回摘要
   - 📝 **完整行程**：Markdown 渲染的逐日行程，含景点推荐、餐饮、交通、天气

### 6.2 通过 API 使用

**生成旅行计划：**

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
    "interests": ["历史古迹", "美食"],
    "dietary_preferences": ["中式"]
  }'
```

**SSE 流式聊天（观察 Agent 的每一步思考）：**

```bash
curl -N "http://localhost:8000/api/chat/message/stream?user_id=demo&message=推荐北京故宫周边的餐厅"
```

事件流示例：

```
event: start
data: {"message": "Agent started"}

event: llm_response
data: {"content": "我来搜索故宫周边的餐厅...", "tool_calls": [{"function":{"name":"maps_text_search","arguments":"{\"keywords\":\"餐厅\",\"city\":\"北京\"}"}}]}

event: tool_result
data: {"tool": "maps_text_search", "result": "找到 15 个餐厅 POI..."}

event: done
data: {"content": "故宫周边有以下推荐餐厅：1. ...", "usage": {"input_tokens": 1200, "output_tokens": 350}}
```

**直连地图工具（绕过 Agent）：**

```bash
# POI 搜索
curl "http://localhost:8000/api/map/poi/search?keywords=故宫&city=北京&limit=5"

# 天气查询
curl "http://localhost:8000/api/map/weather?city=北京"

# 驾车路线
curl -X POST http://localhost:8000/api/map/route \
  -H "Content-Type: application/json" \
  -d '{"origin": "天安门", "destination": "颐和园", "type": "driving"}'
```

浏览器访问 `http://localhost:8000/docs` 查看完整的 Swagger API 文档。

### 6.3 切换 LLM Provider

```bash
# 方式一：环境变量（Docker Compose）
DEFAULT_LLM_PROVIDER=anthropic docker compose up -d

# 方式二：.env 文件
echo "DEFAULT_LLM_PROVIDER=deepseek" >> backend/.env

# 方式三：代码中（测试/开发时）
from app.agent.providers import create_llm_provider
llm = create_llm_provider("anthropic")  # 或 "openai" / "deepseek"
```

### 6.4 加载自定义知识库

将 Markdown 格式的旅行攻略文件放入 `backend/data/knowledge/`：

```markdown
## 目的地名

### 景点
#### 景点名称
详细描述...

### 美食
#### 推荐餐厅
详细描述...

### 交通
...
```

然后通过代码索引：

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

---

## 七、深入理解关键模块

### 7.1 ReAct Agent 执行流程

```mermaid
graph TB
    A[用户输入 + System Prompt] --> B[构建消息列表<br/>system + history + user]
    B --> C{ReAct 循环}
    C --> D[LLM.generate<br/>返回 content + tools]
    D --> E{有 tool_calls?}
    E -->|否| F[返回最终答案]
    E -->|是| G[执行工具<br/>重试最多2次]
    G --> H[结果追加到消息列表]
    H --> C
```

### 7.2 记忆系统时序

```mermaid
sequenceDiagram
    participant U as 用户请求
    participant MM as MemoryManager
    participant DB as PostgreSQL

    U->>MM: plan_trip(user_id, req)
    MM->>DB: get_profile(user_id)
    DB-->>MM: profile JSON
    MM->>DB: get_history(session_id)
    DB-->>MM: messages[]
    MM-->>U: AgentContext

    Note over U,DB: ~~~ Agent 执行中 ~~~

    U->>MM: save_interaction()
    MM->>DB: add_message(user_msg)
    MM->>DB: add_message(tool_msgs)
    MM->>DB: add_message(asst_msg)
    MM->>DB: summarize_and_compress() 如超预算
    MM->>DB: extract_preferences() LLM驱动
    MM-->>U: 完成
```

### 7.3 工具注册与执行

```python
# 注册阶段（启动时一次）
registry = ToolRegistry()
registry.register(AmapTextSearchTool())   # tool.name = "maps_text_search"
registry.register(AmapWeatherTool())      # tool.name = "maps_weather"
registry.register(RouteOptimizerTool())   # tool.name = "route_optimizer"

# LLM 调用时 — 导出 tool schema
tools_schema = registry.to_openai_tools_format()
# → [{"type":"function","function":{"name":"maps_text_search","description":"...","parameters":{...}}}, ...]

# LLM 返回 tool_calls 时 — 执行工具
result = await registry.execute("maps_text_search", keywords="故宫", city="北京")
# → ToolResult(success=True, data={"pois": [...]})

# 调试自省
print(registry.list_names())   # ['maps_text_search', 'maps_weather', ...]
print(len(registry))           # 8
print("maps_text_search" in registry)  # True
```

---

## 八、工程实践

### 8.1 全异步架构

项目中的所有 IO 操作全部使用 `async/await`：

| 层 | 异步依赖 |
|---|---------|
| 数据库 | `asyncpg` + SQLAlchemy 2.0 async ORM |
| HTTP 客户端 | `httpx.AsyncClient` |
| LLM 调用 | `AsyncOpenAI` / `AsyncAnthropic` |
| SSE 流式 | `asyncio.Queue` 桥接回调 → 异步迭代器 |

Agent 调用 LLM 是典型的 IO 密集场景——等待网络响应的时间远大于计算时间。全异步架构确保在等待一个 LLM 响应时，可以并发处理其他请求，大幅提升吞吐量。

### 8.2 配置管理

所有配置集中在 [`backend/app/config.py`](backend/app/config.py)，使用 `pydantic-settings` 实现类型安全和环境变量自动绑定：

```python
class LLMProviderConfig(BaseModel):
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.7

class Settings(BaseSettings):
    default_llm_provider: str = "openai"
    llm_openai: LLMProviderConfig = Field(default_factory=LLMProviderConfig, alias="LLM_OPENAI")
    amap: AmapConfig = Field(default_factory=AmapConfig, alias="AMAP")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, alias="DATABASE")
```

环境变量通过 `__` 映射到嵌套模型：`LLM_OPENAI__API_KEY` → `settings.llm_openai.api_key`。

### 8.3 错误处理策略

| 场景 | 策略 |
|------|------|
| LLM 调用失败 | 立即返回 `AgentResult(success=False)` + 错误信息 |
| 工具执行失败 | 最多 **2 次重试**，失败后返回 `ToolResult(error=...)` 反馈给 LLM |
| 记忆系统异常 | **非致命错误**，`save_interaction()` 中 try-except，不影响主流程 |
| Agent 达到最大迭代 | 返回 `AgentResult(success=False)` + 提示任务可能过于复杂 |
| 工作流步骤失败 | `allow_failure` 字段控制是否中断整个工作流 |

### 8.4 代码质量工具

```bash
# Lint 检查
uv run ruff check .

# 自动修复
uv run ruff check . --fix

# 类型检查
uv run mypy app/

# 运行测试
uv run pytest
uv run pytest --cov=app --cov-report=html
```

---

## 九、路线图

### 已完成 ✅

- [x] **Phase 1** — 项目骨架（分层目录、配置、Docker、日志、测试框架）
- [x] **Phase 2** — ReAct Agent + 3 LLM Provider（项目灵魂）
- [x] **Phase 3** — 本地工具（8 个）+ MCP 适配器桩代码
- [x] **Phase 4** — 双系统记忆（短期滑动窗口 + 长期用户画像）
- [x] **Phase 5** — RAG 管道（嵌入 + pgvector 检索 + Markdown 知识库）
- [x] **Phase 6** — DAG 工作流引擎（拓扑执行 + 并行子步骤）
- [x] **Phase 7** — 业务 API + Vue 3 前端交付

### 待完成 🔲

- [ ] **MCP 工具真实连接** — `MCPToolAdapter.connect()` 完整实现，连接真正的 amap-mcp-server
- [ ] **TripService 接入 WorkflowEngine** — 将当前手动编排迁移为 DAG 引擎驱动
- [ ] **用户协作推荐** — `pgvector` 用户画像向量化 + 相似用户推荐
- [ ] **Alembic 数据库迁移** — 替代当前的自动建表方案
- [ ] **用户注册/登录** — 完善用户体系
- [ ] **更多知识库城市** — 扩展 `data/knowledge/` 覆盖更多目的地
- [ ] **集成测试与端到端测试** — 完善测试覆盖
- [ ] **高德地图前端集成** — `MapView.vue` 接入高德 JS API（需配置 Key）

---

## 十、贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境

```bash
# Fork 并克隆
git clone <your-fork-url> && cd TripPlaner_2

# 后端
cd backend
uv sync --group dev
cp .env.example .env  # 填入你的 API Key

# 前端
cd frontend
npm install
```

### 代码规范

提交前请确保：

```bash
cd backend
uv run ruff check .        # 无 lint 错误
uv run mypy app/           # 类型检查通过
uv run pytest              # 测试通过
```

建议配置 pre-commit 钩子自动检查。

---

## 附录

### A. 依赖清单

| 依赖 | 用途 |
|------|------|
| `fastapi[standard]` | Web 框架 + 自动文档 |
| `openai>=1.0` | OpenAI / DeepSeek SDK |
| `anthropic>=0.40` | Anthropic Claude SDK |
| `sqlalchemy[asyncio]>=2.0` | 异步 ORM |
| `asyncpg>=0.30` | PostgreSQL 异步驱动 |
| `pgvector>=0.3` | 向量存储扩展 |
| `httpx>=0.27` | 异步 HTTP 客户端 |
| `pydantic-settings>=2.0` | 配置管理 |
| `alembic>=1.13` | 数据库迁移（待启用） |
| `mcp>=1.0` | MCP 协议 SDK（待启用） |

### B. API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/trip/plan` | 生成旅行计划 |
| `POST` | `/api/chat/message` | 同步聊天 |
| `GET` | `/api/chat/message/stream` | SSE 流式聊天 |
| `GET` | `/api/map/poi/search` | POI 搜索（直连工具） |
| `GET` | `/api/map/weather` | 天气查询（直连工具） |
| `POST` | `/api/map/route` | 路线规划（直连工具） |

完整 Swagger 文档：`http://localhost:8000/docs`

### C. 致谢

- [HelloAgents](https://github.com/datawhalechina/Hello-Agents) 和 [HelloAgents 框架](https://github.com/jjyaoao/HelloAgents) — 启发了我们对 Agent 框架的理解，也是这个项目重构的起点
- [高德地图开放平台](https://lbs.amap.com/) — 提供地图、POI、天气、路线数据服务
- [amap-mcp-server](https://github.com/sugarforever/amap-mcp-server) — 高德地图 MCP 工具参考实现
- Vue 3 / FastAPI / SQLAlchemy / pgvector 等开源项目

### D. 参考文档

- [参考.md](./参考.md) — 旧版 HelloAgents 智能旅行助手文档
- [重构建议.md](./重构建议.md) — 7 阶段重构规划
- [CLAUDE.md](./CLAUDE.md) — Claude Code 项目指南

---

<div align="center">

**TripPlaner AI** — 从 200 行 ReAct 循环开始的 Agent 工程实践 🚀

</div>
