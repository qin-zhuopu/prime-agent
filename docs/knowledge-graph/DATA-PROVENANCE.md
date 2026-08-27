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
| `repo` | 11 | 🧠 LLM | 手动选定纳入哪些 repo；`label/stack/license/integration/browser_native` 是人工核对填的 |
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

### `repo`
| 属性 | 维护方 | 说明 |
|---|---|---|
| `id` / `label` | 🧠 LLM | 人工命名 |
| `stack` / `license` | 🔧 CODE 可查，🧠 填 | 从 package.json/LICENSE 可读，但当前是人工填 |
| `transport` (SSE/WebSocket/stdio) | 🧠 LLM | 人工核对源码判断的传输方式 |
| `integration` (REST+SSE/stdio-rpc/in-process-sdk) | 🧠 LLM | 人工判断的接入形态 |
| `browser_native` | 🧠 LLM | 人工判断能否纯浏览器直连 |
| `protocols` | 🧠 LLM | 人工指定该 repo 用哪些协议 |
| tier (deep/broad) | ⚙️ DERIVED | **不存储**；`derive_tier.py` 按特征覆盖度涌现算出 |

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
| `uses` | repo → protocol | 🧠 LLM | 人工指定 |
| `contains` | category → feature | 🔧 CODE | 由 feature.category 机械派生 |
| `implements` | repo → feature | 🧠 LLM | 人工判断该 repo 是否实现该功能 + kind/source |
| `has_op` | entity → operation | 🔧 CODE | 由 operation.entity 机械派生 |
| `exposes` | repo → operation | 🧠+🔧 | 边存在性=🔧脚本抓到该端点；归到哪个 canonical op=🧠 映射 |
| `has_group` | repo → endpoint_group | 🔧 CODE | 机械 |
| `has_endpoint` | endpoint_group → endpoint | 🔧 CODE | 机械 |
| `calls` | page → endpoint/operation | 🔧 CODE | `scan_*_calls.py` 正则匹配前端调用，机械 |
| `in_repo` | page → repo | 🔧 CODE | 机械 |
| `provides` | repo → capability | 🧠 LLM | 人工判断该 repo 是否提供该能力 + surface |

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
| `data/repos/*.yaml` | 每 repo 的 transport/integration/browser_native/protocols |
| `data/entities/*.yaml` + `data/protocols/*.yaml` | 实体/协议的归一命名与分类 |
| `map_api.py` 的规则表 | `NS_TO_ENTITY` / `ACTION_ALIAS` / `ENTITY_OPS` / `CP_REST_RULES` / `EXACT_OVERRIDE`——把 raw 端点归一到 canonical 实体+操作 |
| `map_capabilities.py` 的 `M` 表 | 22 能力 × 11 repo 的实现 surface 映射 |

> 注：`map_*.py` 虽然是"脚本"，但其**规则表内容是语义判断**（判断 `session.prompt` = `Message.send`）。脚本本身（遍历+套表）是 CODE，表里的映射关系是 LLM。这是最容易混淆的一层，特此说明。

---

## 五、更新时的操作指引

- **源码变了**（新增 API/组件）→ 重跑 🔧 scan/build，端点/页面/调用自动更新；但新出现的语义归一（新端点归哪个实体、新功能属哪类）需 🧠 补规则表/YAML。
- **新增 repo** → 🧠 补 `data/repos/*.yaml` + 各 map 表里该 repo 的列；🔧 scan 自动抓它的端点/页面；⚙️ tier 自动重算。
- **改分类/能力体系** → 纯 🧠，改 category/capability 定义与映射。
- **验证** → 🔧 `validate.py`（对错）+ `quality_check.py`（缺口），随时可跑。
