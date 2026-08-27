# 数据来源与维护责任（代码维护 vs 大模型语义维护）

这份文档逐一说明知识图谱里**每类节点、每个属性、每种边**是**谁维护的**：

- 🔧 **CODE（脚本机械维护）**：纯正则/遍历从源码抓取或从其他数据派生，可复现、换机器结果一致、无主观判断。改源码重跑即更新。
- 🧠 **LLM（大模型语义维护）**：需要人工/模型的语义判断——命名归一、跨 repo 对齐、功能分类、能力映射。这些写在脚本的**规则表**或 **YAML 数据**里，是"固化下来的判断"，改动需要重新做语义判断。
- ⚙️ **DERIVED（计算派生）**：由其他数据算出，无独立判断（如涌现分层）。

一句话原则：**"某个东西是什么"（名字、URL、方法、文件）由 CODE 抓；"两个东西是不是一回事 / 属于哪类"（归一、分类、能力对齐）由 LLM 判断。**

---

## 一、节点类型（node types）

| 节点类型 | 数量 | 维护方 | 说明 |
|---|---|---|---|
| `repo` | 11 | 🧠 LLM | 手动选定纳入哪些 repo；现在只承载 git 身份（`id/label/license`），app 层属性已迁到 `webui`/`api` |
| `webui` | 11 | 🧠+🔧 混合 | 每个 repo 的前端节点（`W:<repoId>/<path>`）；`stack/transport/integration/browser_native/protocols` 从旧 repo 迁来（🧠 判断）；`path` 由 🔧 从 `caller_file` 派生（缺席源码则 `.` 兜底） |
| `api` | 4 | 🧠+🔧 混合 | 网络后端节点（`A:<repoId>/<path>`）：CP/DH/HM/ACPWG；`style`（rest/rpc/ws-rpc）是 🔧 从来源判定、🧠 定子类型；`path` 由 🔧 从 endpoint 的 `src` 派生（缺席源码则 `.` 兜底） |
| `protocol` | 7 | 🧠 LLM | 传输/渲染范式的抽象分类，人工定义 |
| `category` | 10 | 🧠 LLM | 功能分类（messaging/tool-use…），人工定义的分类体系 |
| `feature` | 73 | 🧠 LLM | 功能点由读源码后**语义归纳**，非脚本抽取 |
| `entity` | 14 | 🧠 LLM | 后端业务实体的归一命名（Session/Message…），跨 repo 语义对齐 |
| `operation` | 57 | 🧠+🔧 混合 | 操作**名字/URL/方法**是 🔧 脚本抓的真值；归到哪个 `(entity, op)` 是 🧠 规则映射 |
| `endpoint` | 602 | 🔧 CODE | `scan_full.py` 正则全量抓取，零判断 |
| `endpoint_group` | 132 | 🔧 CODE | 按命名空间/路径首段自动分组，机械 |
| `page` | 165 | 🔧 CODE | `scan_full_calls.py` 抓取有 API 调用的前端文件 |
| `capability` | 22 | 🧠 LLM | 用户可执行操作的归一词汇表，人工定义 + 跨 11 repo 映射 |

---

## 二、节点属性（node attributes）

### `repo`（拆分后只剩 git 身份）
| 属性 | 维护方 | 说明 |
|---|---|---|
| `id` / `label` | 🧠 LLM | 人工命名 |
| `license` | 🔧 CODE 可查，🧠 填 | 从 LICENSE 可读，当前人工填 |
| tier (deep/broad) | ⚙️ DERIVED | **不存储**；`derive_tier.py` 按特征覆盖度涌现算出 |

> 拆分前挂在 `repo` 上的 `stack/transport/integration/browser_native/protocols` 已全部迁到 `webui`（见下）。

### `webui`（前端节点，app 层属性从旧 repo 迁来）
| 属性 | 维护方 | 说明 |
|---|---|---|
| `id` (`W:<repoId>/<path>`) | 🔧+🧠 | id 由 repoId + path 组合而成，path 是 🔧 派生（见下） |
| `repo` | 🔧 CODE | 指向所属 repo，机械 |
| `path` | 🔧 CODE | 从 `data/frontend_calls/<repo>.json` / `data/full/calls_<repo>.json` 的 `caller_file` 派生（去掉源码目录前缀）；源码缺席则 `.` 兜底 |
| `stack` | 🔧 CODE 可查，🧠 填 | 从 package.json 可读，当前人工填 |
| `transport` (SSE/WebSocket/stdio) | 🧠 LLM | 人工核对源码判断的传输方式 |
| `integration` (REST+SSE/stdio-rpc/in-process-sdk) | 🧠 LLM | 人工判断的接入形态 |
| `browser_native` | 🧠 LLM | 人工判断能否纯浏览器直连 |
| `protocols` | 🧠 LLM | 人工指定该前端用哪些协议 |

### `api`（网络后端节点）
| 属性 | 维护方 | 说明 |
|---|---|---|
| `id` (`A:<repoId>/<path>`) | 🔧+🧠 | id 由 repoId + path 组合而成，path 是 🔧 派生（见下） |
| `repo` | 🔧 CODE | 指向所属 repo，机械 |
| `path` | 🔧 CODE | 从 `data/full/endpoints_<repo>.json` 的 `src` 派生（去掉源码目录前缀）；源码缺席则 `.` 兜底 |
| `style` (rest/rpc/ws-rpc/stdio-rpc) | 🔧+🧠 | 由来源接口形态判定（REST URL vs entity.action RPC vs WS-RPC）；ACPWG 是"stdio SDK 包成网络网关"的语义判断 |
| `transport` | 🧠 LLM | 后端表面的传输，人工核对 |

### `feature`
| 属性 | 维护方 | 说明 |
|---|---|---|
| `id` / `label` / `category` / `priority` | 🧠 LLM | 全部人工语义归纳 |
| `implementations[repo].kind` (structured/terminal) | 🧠 LLM | 人工判断该 repo 是结构化组件还是终端语义 |
| `implementations[repo].source` (verified/declared) | 🧠 LLM | 人工标注核对深度（读了源码 vs 只看 README） |

### `operation`
| 属性 | 维护方 | 说明 |
|---|---|---|
| `endpoints[repo].name` (URL/方法名) | 🔧 CODE | `scan_api.py` 从源码抓的真值 |
| `endpoints[repo].http` (GET/POST…) | 🔧 CODE | 脚本抓取 |
| `endpoints[repo].style` (REST/RPC/WS-RPC) | 🔧 CODE | 脚本按来源判定 |
| `id` = `O:{entity}.{op}` / `entity` / `label` | 🧠 LLM | 归一到哪个实体+操作，是 `map_api.py` 规则表的语义判断 |
| `names`（实体在各 repo 的名字） | 🧠 LLM | 跨 repo 命名对齐 |

### `endpoint`（全量层）
| 属性 | 维护方 | 说明 |
|---|---|---|
| `name` / `http` / `kind` / `src` | 🔧 CODE | 全部脚本正则抓取 |
| `group` | 🔧 CODE | 按命名空间/路径段机械分组 |

### `capability`
| 属性 | 维护方 | 说明 |
|---|---|---|
| `id` / `label` / `description` | 🧠 LLM | 人工定义的能力词汇 |
| `implementations[repo].surface_kind` | 🧠 LLM | 人工判断该 repo 用 endpoint/hook/component… 提供 |
| `implementations[repo].surface_name` | 🧠+🔧 | 具体 hook/组件/端点名是 🔧 从源码抓到的真值；**选哪个**对应此能力是 🧠 判断 |

---

## 三、边（edges）

| 边 | 连接 | 维护方 | 说明 |
|---|---|---|---|
| `located_in` | webui → repo / api → repo | 🔧 CODE | webui/api 归属到 repo，边属性 `path`，由节点的 repo/path 机械派生 |
| `calls` (跨层) | webui → api | 🔧 CODE | 前端调用某后端接口表面，由调用证据派生 |
| `uses` | webui → protocol | 🧠 LLM | 人工指定（原来从 repo 出发，现从 webui 出发） |
| `contains` | category → feature | 🔧 CODE | 由 feature.category 机械派生 |
| `implements` | webui → feature | 🧠 LLM | 人工判断该前端是否实现该功能 + kind/source（原来从 repo 出发） |
| `has_op` | entity → operation | 🔧 CODE | 由 operation.entity 机械派生 |
| `exposes` | api → operation | 🧠+🔧 | 边存在性=🔧脚本抓到该端点；归到哪个 canonical op=🧠 映射（原来从 repo 出发，现从 api 出发） |
| `has_group` | repo → endpoint_group | 🔧 CODE | 机械（全量层） |
| `has_endpoint` | endpoint_group → endpoint | 🔧 CODE | 机械 |
| `calls` (全量层) | page → endpoint/operation | 🔧 CODE | `scan_*_calls.py` 正则匹配前端调用，机械 |
| `in_repo` | page → repo | 🔧 CODE | 机械 |
| `provides` | webui → capability | 🧠 LLM | 人工判断该前端是否提供该能力 + surface（原来从 repo 出发） |

---

## 四、按脚本归类维护责任

### 🔧 CODE（纯机械，改源码重跑即更新，无需重新判断）
| 脚本 | 产出 |
|---|---|
| `scan_api.py` | 聊天核心层的 raw 端点（正则抓） |
| `scan_frontend_calls.py` | 聊天核心层前端调用（正则抓） |
| `scan_full.py` | 全量后端端点（正则抓） |
| `scan_full_calls.py` | 全量前端调用（正则抓） |
| `derive_tier.py` | deep/broad 分层（覆盖度涌现，派生） |
| `build_*.py` | 组图（纯组装 YAML/JSON，无判断） |
| `validate.py` / `quality_check.py` | 校验/质量（规则检查，无判断） |

### 🧠 LLM（语义判断固化在这里，改动需重新做判断）
| 位置 | 承载的判断 |
|---|---|
| `data/features/*.yaml` | 73 功能点的定义、分类、每 repo 的 kind/source |
| `data/webui/*.yaml` | 每个前端的 transport/integration/browser_native/protocols（从旧 `data/repos/*.yaml` 迁来） |
| `data/api/*.yaml` | 4 个网络后端节点的 style（rest/rpc/ws-rpc），含 ACPWG 的"stdio 网关暴露成 WebSocket"判断 |
| `data/entities/*.yaml` + `data/protocols/*.yaml` | 实体/协议的归一命名与分类 |
| `map_api.py` 的规则表 | `NS_TO_ENTITY` / `ACTION_ALIAS` / `ENTITY_OPS` / `CP_REST_RULES` / `EXACT_OVERRIDE`——把 raw 端点归一到 canonical 实体+操作 |
| `map_capabilities.py` 的 `M` 表 | 22 能力 × 11 repo 的实现 surface 映射 |

> 注：`map_*.py` 虽然是"脚本"，但其**规则表内容是语义判断**（判断 `session.prompt` = `Message.send`）。脚本本身（遍历+套表）是 CODE，表里的映射关系是 LLM。这是最容易混淆的一层，特此说明。

---

## 五、更新时的操作指引

- **源码变了**（新增 API/组件）→ 重跑 🔧 scan/build，端点/页面/调用自动更新；但新出现的语义归一（新端点归哪个实体、新功能属哪类）需 🧠 补规则表/YAML。
- **新增 repo** → 🧠 补 `data/repos/*.yaml`（git 身份）+ `data/webui/*.yaml`（前端属性）+（若有网络端点）`data/api/*.yaml` + 各 map 表里该 repo 的列；🔧 scan 自动抓它的端点/页面；⚙️ tier 自动重算。
- **改分类/能力体系** → 纯 🧠，改 category/capability 定义与映射。
- **验证** → 🔧 `validate.py`（对错）+ `quality_check.py`（缺口），随时可跑。
