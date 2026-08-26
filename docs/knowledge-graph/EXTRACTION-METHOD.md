# 提取方法说明（功能点 & API 实体/操作是怎么来的）

明确记录知识图谱的数据是**怎么提取的**、可信度如何、以及要自动化该怎么做。

## 1. UI 功能点：目前是人工语义分析，非自动脚本

- **提取方式**：由模型（本次会话）用 `ls` / `grep` / 读源码，看组件目录、组件名、hook 名、SSE 回调，然后**人工语义归纳**成 73 个功能点，并判断每个 repo 是 `structured`（结构化组件）还是 `terminal`（HM 的终端语义）。
- **primary 三 repo**（CP/DH/HM）：读了源码，标 `source=verified`。
- **survey 八 repo**：只看 README + 目录/组件/hook 名，标 `source=declared`（较粗）。
- **`build_graph.py` 不做提取**：它只是把人工结论（`FEATURES`、`SURVEY_IMPLEMENTS` 字典）组装成 NetworkX 图。
- **没有固定的提取 prompt 写进项目**——当前不存在 LLM 提取管线。

## 2. 后端 API 实体/操作：脚本抓取 + 人工归一化（更可靠）

API 表面是结构化的，可以脚本 grep，不靠语义猜：

- **CP**（RESTful Next.js）：`find src/app/api -name route.ts` 得到 URL，`grep "export function GET|POST|..."` 得到 HTTP 方法。共 187 路由。
- **DH**（RPC）：`grep` `packages/host/apiproxy/src/api/rpc-map.ts` 里的 `entity.action` 方法名。共 53 方法。
- **HM**（WS JSON-RPC）：`grep` `tui_gateway/` 里的 `"entity.action"` 方法名。共 299 方法。

三种 API 表面（REST path+verb / RPC / WS-RPC）**由人工归一化**到统一的 canonical `(entity, operation)`，写在 `build_api_graph.py` 的 `MAP` 里。归一化是人工的（判断"CP 的 `POST /chat/messages`"= "DH 的 `session.prompt`" = "HM 的 `prompt.submit`" 都是 Message.send），但**端点名/URL/方法本身是脚本抓的真实值**，不是编造。

## 3. 可信度分层（图里都有标注）

| 数据 | 提取方式 | 边属性 |
|---|---|---|
| primary UI 功能点 | 人工读源码 | `source=verified` |
| survey UI 功能点 | 人工看 README/结构 | `source=declared` |
| API 端点名/URL/方法 | 脚本 grep | 真实值 |
| API 实体归一化 | 人工判断 | canonical `(entity, operation)` |

## 4. 要做成可复现自动提取管线的话（推荐方向）

对齐你 `llm` 项目里 `scripts/extract_yaml.py` 的思路，把 prompt **固化到脚本**，而非一次性人工判断：

1. **API（先做，最容易）**：把上面的 grep 规则写成 `scan_api.py`，每个 repo 输出结构化 JSON（endpoint 列表）。这部分完全不需要 LLM。
2. **API 实体归一化**：用**模板化 prompt**（动态注入 canonical 实体表 + 操作词汇表），让 LLM 把每个 repo 的 raw endpoint 映射到 `(entity, operation)`，输出 JSON。prompt 固定在脚本里，可回归。
3. **UI 功能点**：同样用模板化 prompt（注入 73 功能点定义 + structured/terminal 判定标准），对每个 repo 的组件清单做分类，输出 JSON。
4. **validate + quality_check**：schema 校验 + 人工抽检。
5. `build_graph.py` / `build_api_graph.py` 读这些 JSON 而非硬编码字典。

> 结论：**API 提取应优先脚本化**（结构化、无需 LLM）；**语义归一化/UI 分类可用固化 prompt 的 LLM 管线**。现状是人工产出的一版基线，可作为自动管线的 ground-truth 对照。
