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

> **repo 已拆成三类核心节点**：原来那个"什么都往上挂"的 `repo` 节点，被拆成 git 身份（`repo`）、前端（`webui`）、后端网络接口（`api`）三类。原来挂在 repo 上的运行时属性（stack/transport/integration/browser_native/protocols）迁到 `webui`；后端子类型 `style` 落在 `api`；所有功能边（uses/implements/provides）改从 `webui` 出发，`exposes` 改从 `api` 出发。详见下面各节及 `MIGRATION-DESIGN.md`。

节点类型（`ntype`）：
- `repo` — **纯 git 身份**：只保留 `id`（大写缩写，如 CP/DH/HM/ACPC）、`ntype`、`label`、可选 `license`。**11 个** repo：CP / DH / HM / acp-components / acp-ui / assistant-ui / opencode-chatui / OpenGUI / CopilotKit / agents-chat / acp-web-gateway。app 层属性已全部迁出（见 `webui`/`api`）。
- `webui` — **位于某 repo 某路径的前端**（`repo + path`）。id 形如 `W:<repoId>/<path>`，携带 `stack` / `transport` / `integration` / `browser_native` / `protocols`（均从旧 `repo` 迁来）。**11 个**（每个 repo 都是给人用的 web UI，各有一个 webui 节点）。
- `api` — **位于某 repo 某路径的后端网络接口**（`repo + path`），按风格分子类型 `style ∈ {rest, rpc, ws-rpc, stdio-rpc}`。id 形如 `A:<repoId>/<path>`，可带后端 `transport`。仅**网络可达**的表面才建 `api` 节点（见"SDK 建模"一节）：CP(rest) / DH(rpc) / HM(ws-rpc) / ACPWG(ws-rpc)。
- `protocol` — 7 种传输/渲染范式（SSE、WS-JSONRPC、ACP、AG-UI、structured-render、node-render、pty-terminal）
- `category` — 10 个功能分类，带 priority（P0..P4）
- `feature` — 73 个具体功能项（**功能点是独立节点类型**）

边类型（`etype`）：
- `webui --located_in--> repo`（边属性 `path`）
- `api --located_in--> repo`（边属性 `path`）
- `webui --calls--> api`（前端调用某个后端接口表面）
- `webui --uses--> protocol`
- `category --contains--> feature`
- `webui --implements--> feature`，边属性：
  - `kind ∈ {structured, terminal}`（结构化组件 vs HM 的终端语义）
  - `source ∈ {verified, declared}`（边级：该功能是读源码确认的 `verified`，还是看 README/结构声明的 `declared`）
- `api --exposes--> operation`（原来从 repo 出发，现改从 api 出发）
- `webui --provides--> capability`（原来从 repo 出发，现改从 webui 出发）
- 未变：`category --contains--> feature`、`entity --has_op--> operation`、全量层的 `has_group` / `has_endpoint`、`page --in_repo--> repo`、`page --calls--> endpoint`。

### 按 path 命名的 id 约定（W: / A:）与 `.` 兜底

`webui` / `api` 的 id **按源码路径命名**，让 id 在重新扫描时也稳定唯一：

- `webui` id = `W:<repoId>/<path>`
- `api` id = `A:<repoId>/<path>`

其中 `<path>` 是该表面所在的 repo 相对源码目录/文件。

**`.` 兜底**：本沙箱里 11 个源码仓库都不在场、无法重新扫描。只有 CP/DH/HM 的扫描路径已物化在 `data/**`（后端来自 `data/full/endpoints_<repo>.json` 的 `src`，前端来自 `data/frontend_calls/<repo>.json` / `data/full/calls_<repo>.json` 的 `caller_file`），可以给出具体 `<path>`。其余 8 个 repo（ACPC / ACPUI / ASTUI / OCUI / OGUI / CKIT / ACHAT，加上仅有网关证据的 ACPWG）源码树缺席、无具体路径，一律用 `path = "."`（repo 根），得到 `W:<repoId>/.`、`A:<repoId>/.`，仍然每 repo 唯一稳定。将来源码到位后可收紧 path，repo id 不受影响。

> **两个正交概念，别混**：
> - `source`（verified/declared）是**边级的核对深度**，人工标注，反映"这条实现关系是怎么确认的"。保留。
> - **深度分层（deep/broad）已改为涌现**：由 `derive_tier.py` 按每个 repo 的特征覆盖数做一维最大间隔聚类（k=2）自动算出，不再有手写的 primary/survey 字段。新增/删除 repo 会自动重新聚类。
> - 二者高度相关（核对得深→覆盖数高），但前者是输入标注、后者是数据派生。当前涌现结果：deep=CP/DH/HM（覆盖 60–71），broad=其余 8（10–31），自然断层 gap=29。

## 两张图

### A. UI 功能图（`build_graph.py`）
节点：`repo` / `webui` / `protocol` / `category` / `feature`。功能边（uses/implements/provides）从 `webui` 出发，`webui --located_in--> repo`。见上方图模型。

### B. 后端 API 实体-操作图（`build_api_graph.py`）
新增两类节点，粒度下探到"实体上的操作"：
- `entity` — 后端业务实体（Session / Message / Permission / Goal / Subagent / Model / Skill / AgentPreset / Workspace / File / Attachment / Settings / Credential / Job，共 14）
- `operation` — 实体上的 canonical 操作（create / list / get / update / delete / send / interrupt / fork / select / respond / pause / resume / complete / clear / history / stream / search，以及聊天紧密相关的 **steer（实时干预）/ compress（上下文压缩）/ undo（撤销）/ reset / usage / rename**）

边：
- `entity --has_op--> operation`（如 Session 的 create/list/get/update/delete/fork/interrupt/search 各是一个操作节点）
- `api --exposes--> operation`，边属性 `name`（该 api 的真实 URL 或 RPC 方法）、`http`（REST 才有）、`style`（REST / RPC / WS-RPC / stdio-rpc）。**该边从 `api` 节点出发**（原来从 `repo` 出发）；每个 `api` 节点 `api --located_in--> repo`。

即：同一个 canonical 操作（如 `Session.create`）下挂三条 `exposes` 边，分别从 CP 的 rest api、DH 的 rpc api、HM 的 ws-rpc api 出发：CP=`POST /chat/sessions`、DH=`session.create`、HM=`session.create`。实体在各 repo 的名字见 `api_metrics.md` 的映射表。

**新增 `component` 节点 + `calls` 边（从代码构建）**：`scan_frontend_calls.py` 扫描前端源码里对端点的调用（CP 的 `fetch("/api/...")`、DH/HM 的 RPC 方法字符串），建立"页面/组件 → 操作"的引用边：
- `component --calls--> operation`，边属性 `endpoint`（被调的真实 URL/方法）、`kind`（REST/RPC）
- 排除测试/fixture 文件，只保留生产代码引用
- 能反查"谁调用了某端点"（如 `Session.create` 的调用方是哪些组件），也揭示架构差异（CP 组件散调 vs DH 收敛到连接层 vs HM 走终端少 RPC）

### 接入面 integration surface（现落在 webui / api，不再在 repo）

拆分后，接入面属性从 `repo` 迁到了 `webui`（前端）与 `api`（后端）：
- `webui.integration`：前端接入方式数组，取值 `REST+SSE` / `WebSocket` / `stdio-rpc` / `in-process-sdk`
- `webui.browser_native`：能否纯浏览器直连（无需 Node/Tauri/Electron 宿主 spawn 子进程）
- `webui.transport` / `webui.stack` / `webui.protocols`：也都从 repo 迁到 webui
- `api.style`（rest/rpc/ws-rpc/stdio-rpc）与 `api.transport`：后端表面的子类型与传输

`repo` 节点本身只剩 git 身份（id/ntype/label/license），不再承载任何运行时/接入信息。

关键：**很多 agent 只给 SDK 或 RPC，不给 HTTP API**。ACP 生态的 CLI agent（Claude Code/Codex 等）只说 stdio JSON-RPC → `webui.browser_native=false`，需网关 spawn 子进程再桥接成 WS/SSE（这就是 acp-web-gateway / agents-chat 存在的原因）。SDK 型（assistant-ui/CopilotKit/acp-components）是前端库，没有自己的网络端点，因此**只建 `webui` 节点、不建 `api` 节点**（见下）。

### SDK 建模：只有网络端点才建 api 节点（逐 repo 核过，见 MIGRATION-DESIGN.md 第 6 节）

`api` 节点**只**为网络可达（TCP/网络端点）的表面而建，即 `rest | rpc | ws-rpc | stdio-rpc-over-gateway`。纯进程内 SDK 表面（`sdk-hook` / `component` / `protocol`）**不建** `api` 节点，只贡献一个 `webui` 节点。

审计不预设"SDK 就一定没有 api"，而是逐 repo 看 `map_capabilities.py` 里各 repo 实际用到的 `surface_kind` 以及 `data/repos/<repo>.yaml` 的 integration/transport 证据来判定：

- **11 个 repo 都是给人用的 web UI**（各有 `stack`、都通过组件/hook 实现用户能力），所以 `webui` 全部为 yes（11 个 webui 节点）。
- **网络 api 节点只归给证据里出现网络 surface 的 4 个 repo**：CP（rest）、DH（rpc）、HM（ws-rpc）、ACPWG（ws-rpc）。
- 其余 7 个（ACPC / ACPUI / ASTUI / OCUI / OGUI / CKIT / ACHAT）只有 `sdk-hook` / `component` / `protocol` 表面，是 webui-only、不建 api 节点。
- **ACPWG 是关键的"SDK != 无 api"案例**：它把上游 ACP（stdio-rpc）包成 WebSocket 网关对外暴露，所以尽管底层协议是 stdio，它仍然拥有一个 ws-rpc 的网络 `api` 节点。

> 现有 4 个 `api` 数据节点（`data/api/{CP,DH,HM,ACPWG}.yaml`）。核心"实体-操作图"里当前接线 3 个（CP/DH/HM 有 canonical operation 暴露）；ACPWG 的 api 节点存在并通过校验，其 `exposes` 归一待后续证据补齐。

## 产物

| 文件 | 用途 |
|---|---|
| `chat_ui_graph.{graphml,json,dot}` | UI 功能图（Gephi/yEd/Cytoscape / D3 / Graphviz） |
| `metrics.md` | UI 图度量（覆盖率 / 通用功能 / 独有功能 / 成熟度） |
| `api_graph.{graphml,json,dot}` | 后端 API 实体-操作图 |
| `api_metrics.md` | 实体命名对照表 + 每实体操作的三 repo 端点映射 |
| `EXTRACTION-METHOD.md` | **数据是怎么提取的**（人工语义 vs 脚本）+ 自动化建议 |
| `DATA-PROVENANCE.md` | **每类节点/属性/边由谁维护**：🔧 代码机械抓取 vs 🧠 大模型语义维护 vs ⚙️ 派生 |

## 关键结论（见 metrics.md）

- **规模**：UI 功能图 112 节点 / 430 边（含 11 webui 节点），11 repos，73 个功能项。
- **协议格局**：`structured-render` 9/11 repo（主流）；`ACP` 4 repo（acp-components / acp-ui / acp-web-gateway / agents-chat，生态标准）；`AG-UI` 1（CopilotKit）；`SSE` 2；HM 的 `pty-terminal` 与 DH 的 `node-render` 各 1（独特）。
- **跨全部 11 repo 的 table-stakes**（demand 信号最强，7–11 repo 实现）：会话视图、消息列表、流式打字、助手 Markdown、工具卡片、输入框、流订阅（均 11/11）；主题、会话侧栏、基础原语、停止中断、代码高亮、diff、权限面板、模型选择（7–10）。**这批是 P0/P1 必做**。
- **deep 三 repo 独有**（broad 集里没人做的差异化/高成本项）：goal、trajectory-replay、plan-review、agent-asks-user、message-queue、rewind-retry、compaction-view、image-gen、rate-limit-banner、message-feedback 等——选择性采纳。
- **分层是涌现的**：deep/broad 由特征覆盖度自动聚类（`derive_tier.py`），非人工指定。

## 数据来源与准确性

功能矩阵与 `kind` 标注来自对三个仓库前端源码的实际浏览（见 `chat-ui-features.md` 的代码路径列）。`kind=terminal` 特指 hermes-agent 把该交互放在 PTY→xterm 终端流里，而非结构化 React 组件。


---

## 数据即 YAML + Schema 校验（可复现管线）

图数据已从"硬编码 Python 字典"重构为**每个节点一个 YAML 文件**，可审查、可 diff、可增量、可校验。

### 目录

```
data/
  repos/       *.yaml   (11)   每个 repo 一份（纯 git 身份）
  webui/       *.yaml   (11)   每个 repo 的前端节点（W:<repoId>/<path>）
  api/         *.yaml   (4)    网络后端节点（A:<repoId>/<path>）：CP/DH/HM/ACPWG
  protocols/   *.yaml   (7)
  features/    *.yaml   (73)   文件名 = category__name
  entities/    *.yaml   (14)
  operations/  *.yaml   (57)   文件名 = Entity__op
  capabilities/*.yaml   (22)
schemas/
  {repo,webui,api,protocol,feature,entity,operation,capability,category,component,full_endpoint,full_call}.schema.yaml
  (12 个 JSON Schema：新增 webui.schema.yaml + api.schema.yaml；repo.schema.yaml 已精简为 git 身份)
```

### 脚本

| 脚本 | 作用 |
|---|---|
| `scan_api.py` | **纯脚本**抓后端 API（正则，无 LLM）→ `data/api_raw/<repo>.json`（CP 250 / DH 53 / HM 299） |
| `map_api.py` | **规则映射**（显式表，无 LLM）：raw 端点 → canonical 实体/操作 → 重写 `data/entities`、`data/operations`；未匹配的记入 `data/api_raw/unmapped.json` |
| `scan_frontend_calls.py` | **纯脚本**扫前端源码里对端点的调用 → `data/frontend_calls/<repo>.json`；构建时连成 `component --calls--> operation` 引用边（排除测试） |
| `export_to_yaml.py` | 一次性种子：把当前内存图导出成 `data/` 下的 per-node YAML（UI 部分用） |
| `validate.py` | **正确性校验**（pass/fail）：schema + 引用完整性 + 语义规则（含 frontend_calls）；exit 1 表示有问题 |
| `quality_check.py` | **完整性/缺口报告**（分级 ERROR/WARN/INFO）：schema 覆盖、repo 覆盖、实体操作薄弱、孤儿节点、字段缺失；输出存档为 `quality-report.md` |
| `derive_tier.py` | **涌现分层**：按特征覆盖度一维最大间隔聚类（k=2）算出 deep/broad，替代已删除的人工 `tier` 字段；纯计算不写回 YAML |
| `build_from_yaml.py` | **规范构建路径**：先跑 validate（fail-closed），通过才从 YAML 构图并出图 |
| `build_graph.py` / `build_api_graph.py` | 原始种子来源 + 复用其 `analyze()` 写度量 |

### validate.py 的三层检查

1. **schema**：每个 YAML 对应 `schemas/<ntype>.schema.yaml`（枚举、pattern、必填字段、`additionalProperties:false`）。校验的 8 类节点：`repo` / `webui` / `api` / `protocol` / `feature` / `entity` / `operation` / `capability`（W:/A: id 的 pattern、api.style 枚举等都在这层）。
2. **referential**：引用必须解析——`webui.repo` / `api.repo` → repo 节点；`webui.protocols` → protocol 节点（协议引用现在挂在 webui 上，不在 repo）；operation.entity → entity 节点；feature/capability 的实现 repo、entity.names 的 repo → 对应节点存在。
3. **semantic**：质量规则——id 唯一；operation id 必须等于 `O:{entity}.{label}`；REST 端点必须带 http verb，RPC/WS-RPC 不能带；无孤儿操作；feature.category 必须与 id 前缀一致；每个 entity 至少被一个 operation 引用；**每个 `webui` 必须声明合法且非空的 transport**；**每个 `api` 的 style 必须是 `rest|rpc|ws-rpc|stdio-rpc` 之一**。

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
- `webui.yaml` 的 `transport` 字段（`[SSE] / [WebSocket] / [stdio]`）：该前端实际用的传输，权威值（从旧 `repo` 迁来）；后端表面的传输可另记在 `api.transport`。
- `protocol.yaml` 的 `transport` + `kind`（transport / protocol / rendering）——协议的原生传输。
- 二者刻意解耦：同一协议在不同 repo 可走不同传输（如 ACP 原生 stdio，但 acp-web-gateway 用 WebSocket 承载），所以 `validate.py` 不强制 `webui.transport` 等于其 protocol 的 transport，只校验 transport 合法且非空。

**对自研的意义**：我们已定 SSE（对齐 CP/DH）。若未来要支持 WebSocket（如 HM 式全双工、或双向 steering），传输是可替换的一层——operation 节点不变，只换 `endpoints[*].transport` 与承载协议。


---

## 全量层 + 统一图（不裁剪，覆盖三个源码核对的 repo）

前面的 API 图是"聊天核心"精选子集（14 实体/57 操作）。全量层则**不重不漏抓取三个源码核对 repo（CP/DH/HM，即 deep 簇）的所有后端接口和所有调用接口的前端页面**，再归一成一张总图。

> 范围说明：全量抓取只覆盖 CP/DH/HM——因为只有它们在本地克隆且被完整读过源码。其余 8 个 broad 簇 repo 多数只看了 README，且不少是 SDK 型（无网络端点），做不了全量接口抓取。（已无人工 primary/survey 标签，deep/broad 由 `derive_tier.py` 涌现。）

### 脚本（全量层）

| 脚本 | 作用 |
|---|---|
| `scan_full.py` | 全量抓后端接口（无裁剪）→ `data/full/endpoints_<repo>.json`。CP 250(187路由×动词)/DH 53/HM 299，按命名空间/路径首段自动分组 |
| `scan_full_calls.py` | 全量抓前端文件对所有接口的调用 → `data/full/calls_<repo>.json`，含 server-internal 统计 |
| `build_full_graph.py` | 全量 API 图：`repo / endpoint_group / endpoint / page` + `has_group/has_endpoint/calls/in_repo`。905 节点/1390 边 |
| `build_unified_graph.py` | **归一化**：在共享 repo 节点上合并 UI 功能图 + 全量 API 图 + 规范 API 层(entity/operation/exposes) → **统一图 1151 节点/2192 边**。含 validate 闸门 |

### 统一图节点/边

节点(13 类)：`endpoint`(602) / `page`(165) / `endpoint_group`(132) / `feature`(73) / `operation`(57) / `component`(43) / `capability`(22) / `entity`(14) / `repo`(11) / `webui`(11) / `category`(10) / `protocol`(7) / `api`(4)。
UI 层节点带 `layer=ui`，后端/页面节点带 `layer=api`，repo 节点共享(带 `has_api_layer`)。统一图纳入全部 4 个 `api` 节点（含 ACPWG，即“SDK 经网络端点封装后才成为 api”的样例），与 api 图保持一致。

边(11 类)：`has_endpoint`(602) / `calls`(555) / `implements`(327) / `in_repo`(165) / `provides`(154) / `has_group`(132) / `exposes`(93) / `contains`(73) / `has_op`(57) / `uses`(19) / `located_in`(15)。`implements` / `provides` / `uses` 现从 `webui` 出发，`exposes` 从 `api` 出发，`located_in` 是 `webui`/`api` → repo 的归属边；聚合的 `webui --calls--> api` 边把前端与后端两层在统一图中连通。

**归一化的价值**：一张图里可跨层遍历 `feature → repo → endpoint_group → endpoint ← page`，把"某 repo 实现哪些功能""这些功能对应哪些后端接口""哪些前端页面调用它们"打通。

### 每 repo 全景（unified_metrics.md）

| repo | features | endpoints | groups | pages calling API | server-internal |
|---|---|---|---|---|---|
| CodePilot | 60 | 250 | 31 | 155 | 39 |
| deepseek-harness | 71 | 53 | 10 | 4 | 36 |
| hermes-agent | 61 | 299 | 91 | 6 | 289 |

三行数字直接揭示架构差异：CP 组件直接 fetch(155 页面散调 REST)；DH 把 RPC 方法名收敛在 connection 层(仅 4 文件，Cordis 契约驱动，业务组件走 typed service)；HM 端点最多(299)但绝大多数无前端 RPC 调用(289 server-internal)，因为交互走 PTY 终端。

### 完整 pipeline

```
# 聊天核心层
scan_api → map_api → scan_frontend_calls → validate → build_from_yaml
# 全量层
scan_full → scan_full_calls → build_full_graph
# 归一
build_unified_graph   (validate 闸门 → unified_graph.* + unified_metrics.md)
# 质量
validate.py / quality_check.py (含 full 层 schema 与覆盖统计)
```
全程纯脚本，无 LLM。


---

## Capability 层：所有 11 个 web UI 的统一对比

前面的全量后端接口只能覆盖有自己后端的 repo（CP/DH/HM）。但**所有 11 个都是给人用的 web UI，用户能做的操作是一样的**——不管底层是 REST / RPC / WebSocket / SDK-hook / 协议。所以归一到一个 **capability（用户可执行操作）** 层，让全部 11 个 repo 在同一维度对比。

### 为什么 capability 能归一而 endpoint 不能

- SDK/库型（assistant-ui、acp-components、CopilotKit）没有自己的后端 endpoint，但**有用户操作**（发消息、看工具调用），通过 hook/component 提供。
- capability 比 endpoint 抽象一级：`capability`（用户视角）→ 各 repo 用不同 `surface`（endpoint / rpc / ws-rpc / sdk-hook / component / protocol）实现。
- 证据来自源码：CP/DH/HM 用真实 endpoint，其余 8 个用真实 hook 名（`usePrompt`/`use-ask-copilot`…）或组件名（`ChatView`/`PermissionDialog`…）。

### 脚本与数据

| 脚本 | 作用 |
|---|---|
| `map_capabilities.py` | 定义 22 个 canonical user capability，映射 11 repo 各自的实现 surface → `data/capabilities/*.yaml` |

一个 capability YAML 示例（send-message）下挂 11 个 repo 的实现：CP=`POST /chat/messages`、DH=`session.prompt`、HM=`prompt.submit`、acp-components=`usePrompt`、assistant-ui=`useComposerRuntime`、CopilotKit=`use-ask-copilot`…（同一操作，不同 surface）。

### 22 个 capability

start-session, list-sessions, send-message, stream-response, stop-generation, view-reasoning, view-tool-call, approve-permission, pick-model, set-mode-effort, attach-file, mention-ref, slash-command, view-diff, browse-files, manage-todos, manage-subagents, edit-message, message-feedback, manage-skills, manage-mcp, connect-status

### 11 repo 能力覆盖对比（unified_metrics.md）

| repo | 能力覆盖 (/22) | 实现风格 |
|---|---|---|
| CodePilot | 21 | REST endpoint |
| deepseek-harness | 21 | RPC + component |
| hermes-agent | 20 | WS-RPC + terminal |
| OpenGUI | 15 | sdk-hook + endpoint |
| agents-chat | 14 | sdk-hook (spawn ACP) |
| assistant-ui | 12 | sdk-hook (runtime adapters) |
| opencode-chatui | 12 | component (external server) |
| acp-components | 11 | sdk-hook (ACP protocol) |
| acp-ui | 11 | component (Tauri + ACP) |
| CopilotKit | 9 | sdk-hook (AG-UI) |
| acp-web-gateway | 8 | ws-rpc (ACP gateway) |

统一图节点含 `capability`(22)，边 `provides`（**现从 `webui` 出发** → capability，带 surface_kind/surface_name）。统一图现 **1151 节点 / 2192 边**，所有 11 repo 通过 capability 层可比。
