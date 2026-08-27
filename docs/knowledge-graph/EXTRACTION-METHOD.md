# 提取方法说明（功能点 & API 实体/操作是怎么来的）

明确记录知识图谱的数据是**怎么提取的**、可信度如何、以及要自动化该怎么做。

## 1. UI 功能点：目前是人工语义分析，非自动脚本

- **提取方式**：由模型（本次会话）用 `ls` / `grep` / 读源码，看组件目录、组件名、hook 名、SSE 回调，然后**人工语义归纳**成 73 个功能点，并判断每个 repo 是 `structured`（结构化组件）还是 `terminal`（HM 的终端语义）。
- **CP/DH/HM**：读了源码，标 `source=verified`。
- **其余 8 repo**：只看 README + 目录/组件/hook 名，标 `source=declared`（较粗）。
- 注：不再有人工 primary/survey 标签；深度分层由 `derive_tier.py` 从特征覆盖度自动涌现（deep/broad）。`source` 是独立的、边级的核对深度标注。
- **`build_graph.py` 不做提取**：它只是把人工结论（`FEATURES`、`SURVEY_IMPLEMENTS` 字典）组装成 NetworkX 图。
- **没有固定的提取 prompt 写进项目**——当前不存在 LLM 提取管线。

## 2. 后端 API 实体/操作：已改为纯脚本抓取 + 规则映射（无 LLM）

API 表面是结构化的，两步纯脚本流程，无任何 LLM：

### 2.1 `scan_api.py` — 机械抓取（零判断）

只用正则从源码抓 raw 端点，输出 `data/api_raw/<repo>.json`：

- **CP**（RESTful Next.js）：`rglob("route.ts")` 得 URL，正则 `export [async] function GET|POST|...` 得 HTTP 方法。抓到 250 条（含多 verb 展开）。
- **DH**（RPC）：解析 `packages/host/apiproxy/src/api/rpc-map.ts` 的 `RpcMethodMap` interface 键（`'entity.action'`）。53 方法。
- **HM**（WS JSON-RPC）：正则抓 `tui_gateway/*.py` 里所有点分字符串字面量 `"a.b[.c]"`（JSON-RPC 命名约定）。299 方法。

这一步完全可复现，换机器/换时间结果一致。

### 2.2 `map_api.py` — 规则映射（显式规则，非 LLM）

把 raw 端点映射到 canonical `(entity, operation)`，重写 `data/entities/*.yaml` + `data/operations/*.yaml`。映射靠三张显式表：

- `NS_TO_ENTITY`：命名空间 → 实体（如 `session`→Session、`approval`→Permission）。
- `ACTION_ALIAS` + `CANON_OPS`：动作别名归一（如 `remove`→delete、`edit`→update）。
- `ENTITY_OPS` 白名单 + `EXACT_OVERRIDE`：per-entity 合法操作过滤 + 跨命名空间修正（如 `session.prompt` 实为 `Message.send`，`session.selectModel` 实为 `Model.select`）。
- `CP_REST_RULES`：CP 的 (url, verb) → (entity, op)，因 REST 无 `entity.action` 结构。

不匹配核心交互实体的端点归入 `data/api_raw/unmapped.json`（可据此扩展规则表）。**端点名/URL/方法是脚本抓的真实值**；映射规则是人工可维护的代码，不是一次性 LLM 判断。当前：14 实体 / 50 操作，unmapped 明确记录。

## 3. 可信度分层（图里都有标注）

| 数据 | 提取方式 | 边属性 |
|---|---|---|
| primary UI 功能点 | 人工读源码 | `source=verified` |
| survey UI 功能点 | 人工看 README/结构 | `source=declared` |
| API 端点名/URL/方法 | 脚本正则抓取（`scan_api.py`） | 真实值 |
| API 实体归一化 | 脚本规则映射（`map_api.py`，显式表） | canonical `(entity, operation)` |

## 4. 现状与后续

### 已实现：API 纯脚本管线

```
scan_api.py   ->  data/api_raw/<repo>.json   (regex only, no LLM)
map_api.py    ->  data/entities/*.yaml + data/operations/*.yaml  (explicit rule tables)
validate.py   ->  schema + referential + semantic checks
build_from_yaml.py -> api_graph.* + api_metrics.md  (fail-closed on validation)
```

跑法：`python3 scan_api.py && python3 map_api.py && python3 build_from_yaml.py`。
改 API 覆盖 = 编辑 `map_api.py` 的规则表（`NS_TO_ENTITY` / `ACTION_ALIAS` / `ENTITY_OPS` / `CP_REST_RULES`），重跑即可，无需 LLM。

### 未做：UI 功能点仍是人工语义

UI 功能点（73 个）目前仍是人工归纳（见第 1 节）。若要同样自动化，可对齐 `llm` 项目 `extract_yaml.py`：用**固化在脚本里的模板化 prompt**（注入功能点定义 + structured/terminal 判定标准）让 LLM 对每个 repo 的组件清单分类输出 JSON，再走 validate。当前人工版可作为该 LLM 管线的 ground-truth 对照。

> 结论：**API 已做到纯脚本、可复现、无 LLM**；UI 分类因涉及语义判断，暂留人工基线，未来可用固化 prompt 的 LLM 管线补齐。
