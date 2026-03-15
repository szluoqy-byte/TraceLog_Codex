# Agent Trace Observability Prototype (TraceLog)

一个最小可运行的 AI Agent 轨迹可观测原型系统：采集 Agent 执行轨迹日志，解析为统一 Trace/Span/Event 模型，存储到 SQLite，并在 Web UI 中以「Span 树 + Waterfall 时间轴 + 详情面板」方式可视化，辅助调试与理解 Agent 执行过程。

## Step 1: 系统架构设计

**数据流**

1. Agent/SDK/脚本将执行轨迹以 JSON 形式发送到后端 `POST /api/v1/ingest`
2. 后端解析并标准化为内部模型（受 OpenTelemetry GenAI 语义约定启发）
3. 写入 SQLite（Trace/Span/Event 规范化表 + JSON 扩展字段）
4. 前端通过 REST API 拉取 Trace 列表与详情并渲染

**组件**

- `backend/`: FastAPI + SQLite（SQLModel），提供日志解析与 REST API
- `frontend/`: Vite + React + TypeScript，提供 Trace 列表与可视化详情页
- `samples/`: 示例 Agent Trace 日志（可直接 ingest）

## Step 2: Trace 数据模型设计

系统内部的统一概念：

- `Trace`: 一次 Agent 运行的全链路，包含多个 `Span`
- `Span`: 一个步骤/调用的时间片，支持层级（parent/child），核心类型：
  - `agent`: Agent 的高层步骤（plan/act/reflect 等）
  - `llm`: LLM invocation（模型、prompt、tokens、latency）
  - `tool`: Tool call（工具名、入参、出参、错误）
- `Event`: 附着在 span 上的离散事件（例如异常、重试、流式增量、日志）
- `TokenUsage`: prompt/completion/total
- `Error`: 统一错误结构（message/type/stack）

存储采用规范化表：

- `traces`: trace 元信息与聚合指标（span_count、error_count、duration_ms 等）
- `spans`: span 结构化字段（kind、timing、model、tool、tokens）+ `attributes/input/output` JSON
- `events`: span 事件（timestamp + attributes JSON）

## Step 3: API 设计（REST）

- `POST /api/v1/ingest`
  - Body: Trace bundle JSON（见 `samples/trace_sample.json`）
  - 返回：ingested trace_ids 与统计
- `POST /api/v1/ingest/span`
  - 分布式节点单点上报：一次请求上报一个 span（可包含 events），后端按 `(trace_id, span_id)` upsert 并聚合成调用链
- `POST /api/v1/ingest/event`
  - 分布式节点单点上报：一次请求上报一个 event（span 不存在会创建占位 span，保证乱序可接收）
- `GET /api/v1/traces?limit=50&offset=0&q=...`
  - 返回：Trace 列表（摘要）
- `GET /api/v1/traces/{trace_id}`
  - 返回：Trace 详情（trace + spans + events）
- `GET /api/v1/healthz`

## Step 4: 后端实现

见 `backend/`，包含：

- 统一解析器：将输入日志标准化为 Trace/Span/Event
- SQLite 持久化：启动时自动建表
- 查询 API：Trace 列表与详情

## Step 5: 前端实现

见 `frontend/`，页面：

- Trace 列表：可搜索、显示耗时/错误/服务名/开始时间
- Trace 详情：Span 树（层级）+ Waterfall（耗时）+ 详情面板（prompt/tool/tokens/error）

## Step 6: 示例 Agent 日志

`samples/trace_sample.json` 提供一条包含 `agent -> llm -> tool -> llm` 的完整 trace。

## Step 7: 本地运行说明

### 后端（Windows PowerShell）

```powershell
Set-Location F:\Code\TraceLog_Codex
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python backend\main.py
```

后端默认监听：`http://127.0.0.1:8000`，Swagger：`http://127.0.0.1:8000/docs`

### 前端

```powershell
Set-Location F:\Code\TraceLog_Codex\frontend
npm install
npm run dev
```

前端默认：`http://127.0.0.1:5173`（已配置代理到后端 `/api`）

### 导入示例日志

```powershell
Set-Location F:\Code\TraceLog_Codex
curl.exe -X POST http://127.0.0.1:8000/api/v1/ingest `
  -H "Content-Type: application/json" `
  -d @samples/trace_sample.json
```

或直接运行脚本：

```powershell
Set-Location F:\Code\TraceLog_Codex
.\scripts\ingest_sample.ps1 -Sample samples\trace_sample.json
.\scripts\ingest_sample.ps1 -Sample samples\trace_error.json
```

然后打开前端即可浏览与可视化。

### 分布式单点上报示例

该示例模拟 `node-a` / `node-b` 乱序上报 span，后端会在同一个 `trace_id` 下聚合成完整调用链：

```powershell
Set-Location F:\Code\TraceLog_Codex
.\scripts\ingest_distributed.ps1
```

### 扇出调用链示例（A 并发调 B/C/D；C 再调 E/D）

```powershell
Set-Location F:\Code\TraceLog_Codex
.\scripts\ingest_graph_fanout.ps1
```

### 复杂 Agent 调研全流程示例（plan -> collect -> analyze -> write）

```powershell
Set-Location F:\Code\TraceLog_Codex
.\scripts\ingest_research_case.ps1
```

### 配置（可选）

- `TRACELOG_DB_PATH`: SQLite 文件路径（默认 `backend/data/tracelog.db`）
- `TRACELOG_HOST` / `TRACELOG_PORT`: 后端监听地址与端口
