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
- `repo` — 三个参考实现（CP / DH / HM），带 stack / license 属性
- `protocol` — 传输/渲染范式（SSE、WS-JSONRPC、structured-render、node-render、pty-terminal）
- `category` — 10 个功能分类，带 priority（P0..P4）
- `feature` — 73 个具体功能项

边类型（`etype`）：
- `repo --uses--> protocol`
- `category --contains--> feature`
- `repo --implements--> feature`，边属性 `kind ∈ {structured, terminal}`（缺失则无边）

## 产物

| 文件 | 用途 |
|---|---|
| `chat_ui_graph.graphml` | 通用图格式，用 Gephi / yEd / Cytoscape 打开可视化 |
| `chat_ui_graph.json` | node-link JSON，喂给 D3 / 前端可视化 |
| `chat_ui_graph.dot` | Graphviz，`dot -Tsvg chat_ui_graph.dot -o graph.svg` |
| `metrics.md` | 度量分析（覆盖率 / 通用功能 / 独有功能 / 成熟度） |

## 关键结论（见 metrics.md）

- **规模**：91 节点，272 边，73 个功能项。
- **覆盖率**：DH 最全（71 结构化实现，仅缺 2），CP 60，HM 61（其中 20 项是终端语义 `terminal` 而非结构化组件）。
- **50 个功能三 repo 都实现**（table-stakes），其中 34 项在三家都是结构化组件——**这批最该先做**（会话视图、Markdown、代码高亮、输入框、斜杠命令、模型选择、上下文用量、停止/中断、断线重连、风险确认等）。
- **DH 独有**：`goal`、`message-feedback`。
- **CP 独有**：`image-gen`、`rate-limit-banner`。
- **HM 独有**：无（HM 的差异化在"实现形式"= 终端语义，而非独有功能）。
- **成熟度**：50 功能三家都有 / 19 功能两家有 / 4 功能仅一家有（差异化候选）。

## 数据来源与准确性

功能矩阵与 `kind` 标注来自对三个仓库前端源码的实际浏览（见 `chat-ui-features.md` 的代码路径列）。`kind=terminal` 特指 hermes-agent 把该交互放在 PTY→xterm 终端流里，而非结构化 React 组件。
