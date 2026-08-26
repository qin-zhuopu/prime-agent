# Chat/Agent UI 知识图谱

用 **NetworkX** 把 `docs/chat-ui-features.md` 的三 repo 功能矩阵（CodePilot / deepseek-harness / hermes-agent）编码成知识图谱，用于分析功能成熟度、跨 repo 覆盖、独有差异点。

## 关于 graphify vs NetworkX

- **graphify** 不是一个单一权威库——GitHub 上有多个同名项目（JS 的可视化、Neo4j ETL 等），没有稳定的 Python 图分析标准实现。
- **NetworkX** 是 Python 图分析的事实标准，纯本地、无外部服务依赖，能导出所有主流图格式。因此这里用 NetworkX 建图，并导出通用格式，可再喂给任何可视化工具（含各种 "graphify" 类前端）。

## 运行

```bash
cd docs/knowledge-graph
pip install networkx        # 已在沙箱验证 networkx 3.2.1
python3 build_graph.py
```

## 图模型

节点类型（`ntype`）：
- `repo` — **11 个** agent web UI 实现：3 个 primary（源码核对：CP / DH / HM）+ 8 个 survey（README/结构扫描：acp-components / acp-ui / assistant-ui / opencode-chatui / OpenGUI / CopilotKit / agents-chat / acp-web-gateway）
- `protocol` — 7 种传输/渲染范式（SSE、WS-JSONRPC、ACP、AG-UI、structured-render、node-render、pty-terminal）
- `category` — 10 个功能分类，带 priority（P0..P4）
- `feature` — 73 个具体功能项（**功能点是独立节点类型**）

边类型（`etype`）：
- `repo --uses--> protocol`
- `category --contains--> feature`
- `repo --implements--> feature`，边属性：
  - `kind ∈ {structured, terminal}`（结构化组件 vs HM 的终端语义）
  - `source ∈ {verified, declared}`（primary 源码核对 vs survey README/结构声明）

> 数据可信度分层：primary 三 repo 的边来自实际读源码（`verified`）；survey 八 repo 的边来自 README 声明 + 目录/组件/hook 名扫描（`declared`，较粗）。跨 repo 核心结论只用 primary 集，survey 集用于"需求/成熟度"信号。

## 两张图

### A. UI 功能图（`build_graph.py`）
节点：`repo` / `protocol` / `category` / `feature`。见上方图模型。

### B. 后端 API 实体-操作图（`build_api_graph.py`）
新增两类节点，粒度下探到"实体上的操作"：
- `entity` — 后端业务实体（Session / Message / Permission / Goal / Subagent / Model / Skill / AgentPreset / Workspace / File / Attachment / Settings / Credential / Job，共 14）
- `operation` — 实体上的 canonical 操作（create / list / get / update / delete / send / interrupt / fork / select / respond / pause / resume / complete / clear / history / stream / search）

边：
- `entity --has_op--> operation`（如 Session 的 create/list/get/update/delete/fork/interrupt/search 各是一个操作节点）
- `repo --exposes--> operation`，边属性 `name`（该 repo 的真实 URL 或 RPC 方法）、`http`（REST 才有）、`style`（REST / RPC / WS-RPC）

即：同一个 canonical 操作（如 `Session.create`）下挂三条 `exposes` 边——CP=`POST /chat/sessions`、DH=`session.create`、HM=`session.create`。实体在各 repo 的名字见 `api_metrics.md` 的映射表。

## 产物

| 文件 | 用途 |
|---|---|
| `chat_ui_graph.{graphml,json,dot}` | UI 功能图（Gephi/yEd/Cytoscape / D3 / Graphviz） |
| `metrics.md` | UI 图度量（覆盖率 / 通用功能 / 独有功能 / 成熟度） |
| `api_graph.{graphml,json,dot}` | 后端 API 实体-操作图 |
| `api_metrics.md` | 实体命名对照表 + 每实体操作的三 repo 端点映射 |
| `EXTRACTION-METHOD.md` | **数据是怎么提取的**（人工语义 vs 脚本）+ 自动化建议 |

## 关键结论（见 metrics.md）

- **规模**：101 节点，419 边，11 repos，73 个功能项。
- **协议格局**：`structured-render` 9/11 repo（主流）；`ACP` 4 repo（acp-components / acp-ui / acp-web-gateway / agents-chat，生态标准）；`AG-UI` 1（CopilotKit）；`SSE` 2；HM 的 `pty-terminal` 与 DH 的 `node-render` 各 1（独特）。
- **跨全部 11 repo 的 table-stakes**（demand 信号最强，7–11 repo 实现）：会话视图、消息列表、流式打字、助手 Markdown、工具卡片、输入框、流订阅（均 11/11）；主题、会话侧栏、基础原语、停止中断、代码高亮、diff、权限面板、模型选择（7–10）。**这批是 P0/P1 必做**。
- **primary 三 repo 独有**（survey 集里没人做的差异化/高成本项）：goal、trajectory-replay、plan-review、agent-asks-user、message-queue、rewind-retry、compaction-view、image-gen、rate-limit-banner、message-feedback 等——选择性采纳。
- **可信度分层**：primary 结论 `verified`，survey 覆盖 `declared`。

## 数据来源与准确性

功能矩阵与 `kind` 标注来自对三个仓库前端源码的实际浏览（见 `chat-ui-features.md` 的代码路径列）。`kind=terminal` 特指 hermes-agent 把该交互放在 PTY→xterm 终端流里，而非结构化 React 组件。
