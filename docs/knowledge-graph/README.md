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


---

## 数据即 YAML + Schema 校验（可复现管线）

图数据已从"硬编码 Python 字典"重构为**每个节点一个 YAML 文件**，可审查、可 diff、可增量、可校验。

### 目录

```
data/
  repos/       *.yaml   (11)   每个 repo 一份
  protocols/   *.yaml   (7)
  features/    *.yaml   (73)   文件名 = category__name
  entities/    *.yaml   (14)
  operations/  *.yaml   (49)   文件名 = Entity__op
schemas/
  {repo,protocol,feature,entity,operation}.schema.yaml   (每种节点类型一个 JSON Schema)
```

### 脚本

| 脚本 | 作用 |
|---|---|
| `scan_api.py` | **纯脚本**抓后端 API（正则，无 LLM）→ `data/api_raw/<repo>.json`（CP 250 / DH 53 / HM 299） |
| `map_api.py` | **规则映射**（显式表，无 LLM）：raw 端点 → canonical 实体/操作 → 重写 `data/entities`、`data/operations`；未匹配的记入 `data/api_raw/unmapped.json` |
| `export_to_yaml.py` | 一次性种子：把当前内存图导出成 `data/` 下的 per-node YAML（UI 部分用） |
| `validate.py` | **全量质量检查**：schema + 引用完整性 + 语义规则；exit 1 表示有问题 |
| `build_from_yaml.py` | **规范构建路径**：先跑 validate（fail-closed），通过才从 YAML 构图并出图 |
| `build_graph.py` / `build_api_graph.py` | 原始种子来源 + 复用其 `analyze()` 写度量 |

### validate.py 的三层检查

1. **schema**：每个 YAML 对应 `schemas/<ntype>.schema.yaml`（枚举、pattern、必填字段、`additionalProperties:false`）。
2. **referential**：引用必须解析——operation.entity → entity 节点；feature 的实现 repo / entity.names 的 repo / repo.protocols → 对应节点存在。
3. **semantic**：质量规则——id 唯一；operation id 必须等于 `O:{entity}.{label}`；REST 端点必须带 http verb，RPC/WS-RPC 不能带；无孤儿操作；feature.category 必须与 id 前缀一致；每个 entity 至少被一个 operation 引用；repo 必须声明合法 transport。

已实测：故意注入坏枚举/悬空引用/REST 缺 verb，三类都被抓出；`build_from_yaml.py` 在坏数据时拒绝出图。

### 用法

```bash
python3 validate.py          # 只校验
python3 build_from_yaml.py   # 校验通过后重建全部图与度量
```

改数据 = 直接编辑 `data/**/*.yaml`，跑 `build_from_yaml.py` 即可（自带校验闸门）。

---

## 后端传输：SSE vs WebSocket（已纳入图谱）

三 repo 的关键架构分歧就是传输层，已建模为一等维度：

- **CP / DH → SSE**：REST/RPC 请求发起 + SSE 单向流回推。
- **HM → WebSocket**：全双工 JSON-RPC（`tui_gateway`），请求与事件同一条连接。
- **survey 集**：assistant-ui / opencode-chatui / OpenGUI / CopilotKit 偏 SSE；acp-components / acp-ui / agents-chat 走 ACP（原生 stdio，浏览器侧经 gateway）；acp-web-gateway 用 WebSocket 承载 ACP。

建模位置：
- `repo.yaml` 的 `transport` 字段（`[SSE] / [WebSocket] / [stdio]`）——该 repo 实际用的传输，权威值。
- `protocol.yaml` 的 `transport` + `kind`（transport / protocol / rendering）——协议的原生传输。
- 二者刻意解耦：同一协议在不同 repo 可走不同传输（如 ACP 原生 stdio，但 acp-web-gateway 用 WebSocket 承载），所以 `validate.py` 不强制 repo.transport 等于其 protocol 的 transport，只校验 transport 合法且非空。

**对自研的意义**：我们已定 SSE（对齐 CP/DH）。若未来要支持 WebSocket（如 HM 式全双工、或双向 steering），传输是可替换的一层——operation 节点不变，只换 `endpoints[*].transport` 与承载协议。
