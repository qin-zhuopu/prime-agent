# 同类 AI Agent Web UI 调研（GitHub）

在 GitHub 上搜到的、与我们目标（用户↔AI Agent 交互 Web UI）相关的开源项目。按类别归类，供参考架构选型与功能对标。

内容依据各项目 GitHub 页面公开描述整理并转述（Content was rephrased for compliance with licensing restrictions）。

---

## 一、ACP (Agent Client Protocol) 生态 —— 最值得关注

ACP 是一套 JSON-RPC 2.0 over stdio 的开放协议，已有 33+ 编码 agent 支持（Kiro、Claude Code、Codex CLI、Cursor、Gemini CLI、GitHub Copilot、OpenCode、Cline 等）。围绕它出现了一批"通用 agent 前端"，与我们"后端轻量代理 + 前端组件"的思路高度契合。

| 项目 | 说明 | 参考价值 |
|---|---|---|
| [zvzuola/acp-components](https://github.com/zvzuola/acp-components) | **ACP 的 UI 组件库**：多 agent/多会话编排、streaming、工具调用、权限、plan、文件浏览、diff、skills、settings、桌面传输。定位是"agent 工作台组件"而非又一个聊天框。 | ⭐ 与 DH 的组件库定位最像，功能清单几乎和我们的矩阵重合，重点参考 |
| [formulahendry/acp-ui](https://github.com/formulahendry/acp-ui) | 跨平台 ACP 客户端（桌面/移动/Web）。Web 版支持 chat、sessions、permissions、traffic-monitor，仅缺本地 stdio agent 和宿主文件系统访问（浏览器限制）。 | ⭐ 印证了"浏览器里跑 agent UI"的边界：本地 stdio/FS 需要子进程 |
| [huanyingtianhe/agents-chat](https://github.com/huanyingtianhe/agents-chat) | 独立的多 agent 聊天 UI，直连 ACP CLI 工具（Copilot CLI、Claude Code 等）。 | 多 agent 编排参考 |
| [jamesward/acp-web-gateway](https://github.com/jamesward/acp-web-gateway) | 通过 ACP 连接 AI agent 的 Web 网关。 | ⭐ 与我们"后端 SSE 代理"角色对应，参考网关层 |
| [namanrajpal/acp-to-agui](https://github.com/namanrajpal/acp-to-agui) | 协议桥：把任何支持 ACP 的编码 agent 桥接到任何 Web 前端（ACP stdio ↔ AG-UI）。 | 协议转换层参考 |
| [ElleNajt/acp-mobile](https://github.com/ElleNajt/acp-mobile) | ACP 会话的移动端 Web UI，发现本机 acp-multiplex sockets 并按项目分组，手机上和任意会话聊天。 | 移动端 + 多路复用参考 |
| [aws-samples/sample-kiro-acp-ui](https://github.com/aws-samples/sample-kiro-acp-ui) | 基于 ACP 的桌面聊天示例，用 Kiro CLI 作 AI 后端，零外部依赖（仅 stdlib），易读易改。 | ⭐ 最小可读实现，适合当 ACP 上手样例 |

> 注意：另有一个 [agent-control-protocol/acp](https://github.com/agent-control-protocol/acp)（"Agent **Control** Protocol"）是 WebSocket 协议、让 agent 操控现有应用 UI，与上面的 "Agent **Client** Protocol" 同缩写但不同物，勿混淆。

---

## 二、通用 AI Chat / Generative UI 组件库

| 项目 | 说明 | 参考价值 |
|---|---|---|
| [assistant-ui/assistant-ui](https://github.com/assistant-ui/assistant-ui) | TypeScript/React 的 AI 聊天库，主打生产级聊天体验快速搭建。 | ⭐ 成熟组件库，消息/流式/工具调用抽象值得参考 |
| [CopilotKit/CopilotKit](https://github.com/copilotkit/copilotkit) | Agents & Generative UI 前端栈（React/Angular/Mobile/Slack），**AG-UI 协议**作者。 | ⭐ AG-UI 协议 = agent↔前端事件标准，和我们的 SSE 事件契约同类，重点参考协议 |
| [tambo-ai/tambo](https://github.com/tambo-ai/tambo) | React 的生成式 UI SDK，处理 streaming、状态管理、MCP。 | 生成式 UI + MCP 集成参考 |
| [mallahyari/agentic-chat-ui](https://github.com/mallahyari/agentic-chat-ui) | 基于 AG-UI 协议的生产级聊天应用，实时流式 + 响应式界面。 | AG-UI 落地样例 |
| [huggingface/chat-ui](https://github.com/huggingface/chat-ui) | HuggingChat 的开源代码库，支持 OpenAI 兼容 API。 | 通用聊天，非 agent 工具调用向，参考基础聊天 |

---

## 三、Coding Agent + 自带 Web/Desktop UI（与三 repo 同类）

| 项目 | 说明 | 参考价值 |
|---|---|---|
| [akemmanuel/OpenGUI](https://github.com/akemmanuel/OpenGUI) | 开源桌面/Web 编码 agent，自带 host + harness、持久会话、模型连接、流式聊天、工作区工具。 | ⭐ 与 CP/DH/HM 同类，harness + 会话 + 流式的完整实现 |
| [redentordev/opencode-chatui](https://github.com/redentordev/opencode-chatui) | OpenCode 的 Web 界面，富渲染 AI 响应：工具调用、文件 diff、搜索结果等。 | ⭐ 工具/ diff/ 搜索渲染，直接对标我们的"工具调用"分类 |
| [MaxGfeller/open-harness](https://github.com/MaxGfeller/open-harness) | 代码优先、可组合的 agent SDK，基于 Vercel AI SDK，灵感来自 Claude Code / Codex。 | harness 抽象参考（偏后端/SDK） |
| [emanueleielo/deepagents-open-lovable](https://github.com/emanueleielo/deepagents-open-lovable) | 基于 DeepAgents + LangGraph 的前端开发平台，自然语言生成 React 应用。 | LangGraph agent + 前端参考 |
| [frontman-ai/frontman](https://github.com/frontman-ai/frontman) | 活在浏览器里的编码 agent，作为 dev server 中间件，能看实时 DOM / 组件树 / CSS / 路由 / 日志。 | 浏览器内 agent 的另一种形态 |

---

## 对我们自研的启示

1. **协议层向 ACP / AG-UI 看齐**：这两个是当前 agent↔前端交互的事实标准。
   - **ACP**（JSON-RPC over stdio，33+ agent 支持）适合"接入现有 CLI agent"。
   - **AG-UI**（CopilotKit 主推的事件协议）适合"自研后端 + 前端事件流"，与我们已定的 SSE 事件契约同类，可对齐事件命名。
   - 我们的 runtime 层若在 SSE 之上兼容 ACP/AG-UI 事件形状，未来能直接接入生态里的通用前端。
2. **组件库定位标杆**：[acp-components](https://github.com/zvzuola/acp-components) 和 [assistant-ui](https://github.com/assistant-ui/assistant-ui) 的功能边界几乎覆盖我们的功能矩阵，可作为组件粒度和 API 设计参考。
3. **浏览器边界已被验证**：acp-ui 明确指出 Web 版无法跑本地 stdio agent / 访问宿主 FS——印证我们"后端代理 + 前端组件"的必要性。
4. **富渲染对标**：opencode-chatui 的工具调用/diff/搜索渲染，是我们 P1「工具调用展示」的现成对标物。
