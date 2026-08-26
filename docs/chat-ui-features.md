# 聊天 / AI Agent 交互 UI 功能表（三 repo 综合参考）

> 目的：盘点「用户 ↔ AI Agent」交互所需的前端组件与功能，作为我们自研的需求参考。
> 综合三套开源实现的功能与代码定位，仅作**功能对照参考**，不复制代码。
>
> 参考来源：
> - **CodePilot**（记作 `CP`）：Electron + Next.js 16 + React 19 + `ai` SDK + streamdown + Shiki。命令式组件树。传输 **SSE**。许可 BUSL-1.1（商业/大组织内部用途受限）。代码路径相对其仓库 `src/`。
> - **deepseek-harness**（记作 `DH`）：Cordis 插件架构 + React 渲染绑定 + 契约驱动 slot 注册。前端在 `packages/client/`，每个交互功能≈一个 `ui-*` 包。传输 **SSE（sessions 服务）**。代码路径相对其仓库 `packages/client/`。
> - **hermes-agent**（记作 `HM`）：Vite + React 19 + React Router + xterm.js + `@nous-research/ui`。组件平铺在 `web/src/`。传输 **WebSocket JSON-RPC（tui_gateway）**，聊天主体是 **PTY→xterm 终端镜像**，旁挂结构化事件侧栏。代码路径相对其仓库 `web/src/`。
>
> 定位差异：CP = 应用内聊天页；DH = 可插拔 Cordis 组件库；HM = 多页 Dashboard，聊天页把 Agent 的 Ink TUI 通过 PTY 转发进浏览器终端。
> DH 的架构最贴近我们自研目标（契约驱动、包拆分、静态注册、SSE）。**HM 的 PTY-终端路线与我们方向不同**，其结构化组件仅覆盖会话管理/配置，富交互（工具/权限/reasoning）都在终端流里——因此下表 HM 列很多格为"PTY 终端语义"。

---

## 优先级速览

| 阶段 | 范围 |
|---|---|
| **P0 最小闭环** | 消息列表 + 流式文本 + Markdown/代码高亮 + 输入框 + 停止/中断 + 本轮结束态 |
| **P1 Agent 核心** | 工具调用卡片（use/output/result）+ 思考展示 + 权限确认 + 终止原因 |
| **P2 长会话体验** | 虚拟滚动 + 上下文用量 + 断线重连 snapshot + 消息排队 + rewind/分支 |
| **P3 高级** | 任务清单/子代理 + 模型/运行时/effort 切换 + @提及/斜杠命令 + Plan 模式 + 技能 |
| **P4 可选** | 多媒体/图片生成、交付物、反馈点赞、轨迹回放、i18n |

---

## 一、消息与流式渲染（核心，P0）

| 功能 | CP (`src/`) | DH (`packages/client/`) | HM (`web/src/`) |
|---|---|---|---|
| 会话主视图 | `components/chat/ChatView.tsx` | `ui-conversation/src/client/chat/ChatView.tsx` | `pages/ChatPage.tsx` |
| 会话骨架/根容器 | `components/chat/ChatView.tsx`（一体） | `ui-conversation/src/client/skeleton/ConversationRoot.tsx`、`ConversationSession.tsx` | `pages/ChatPage.tsx` + `components/ChatSidebar.tsx` |
| 消息列表 | `components/chat/MessageList.tsx` | `ui-conversation/src/client/chat/ChatView.tsx` + `ChatNodeSeat.tsx`（node 化） | PTY 终端语义（xterm 渲染，`lib/pty-scroll.ts`） |
| 虚拟滚动 | `components/chat/message-list-virtual.ts` | `ui-trajectory/src/client/trajectory-virtual-rows.ts` | xterm 自带 viewport（无 DOM 虚拟列表） |
| 单条消息 | `ai-elements/message.tsx`、`chat/MessageItem.tsx` | `ui-conversation/src/client/chat/MessageItem.tsx` | PTY 终端语义 |
| 流式打字/节流刷新 | `components/chat/StreamingMessage.tsx` | `ui-conversation/.../use-throttled-visual-update.ts`、`AssistantNodeView.tsx` | `message.delta` 事件 → 写入 xterm；`lib/pty-resume-loading.ts` |
| 助手 Markdown | `components/chat/markdown-components.tsx` | `ui-conversation/src/client/chat/AssistantMarkdown.tsx` | `components/Markdown.tsx`（轻量渲染，用于结构化侧栏） |
| Markdown 原语 | 依赖 `streamdown` | `ui-primitives/src/markdown/*` | `components/Markdown.tsx`（自研轻量） |
| 代码块高亮 | `ai-elements/code-block.tsx` + `shiki.worker.ts` | `ui-primitives/src/markdown/CodeBlock.tsx`、`highlight.ts` | 终端 ANSI（无独立高亮器） |
| 数学公式 | `@streamdown/math` | `ui-primitives/src/markdown/katex.tsx` | （无） |
| 消息操作（复制等） | `ai-elements/message.tsx` | `ui-conversation/.../MessageIconActions.tsx` | `lib/clipboard.ts` + ChatPage 复制按钮 |
| 消息分支切换 | `ai-elements/message.tsx` | `conversation-nodes/turn-tail.ts` | （无，终端线性流） |

## 二、思考 / 推理展示（Agent 特有，P1）

| 功能 | CP | DH | HM |
|---|---|---|---|
| Reasoning 展示 | `ai-elements/reasoning.tsx` | `ui-conversation/.../ReasoningRow.tsx` | PTY 终端语义（终端内展示） |
| 思维链步骤 | `ai-elements/chain-of-thought.tsx` | （并入 ReasoningRow / trajectory turn） | PTY 终端语义 |
| 思考中动效 | `ai-elements/shimmer.tsx` | `ui-primitives/src/StateDot.tsx` | 终端 spinner；`components/SidebarStatusStrip.tsx` |
| Reasoning 强度设置 | `chat/EffortSelectorDropdown.tsx` | `ui-conversation/.../submission-settings.ts` | `components/ReasoningPicker.tsx`（侧栏设置 effort） |

## 三、工具调用（Tool Use，Agent 交互重点，P1）

| 功能 | CP | DH | HM |
|---|---|---|---|
| 工具调用卡片/行 | `ai-elements/tool.tsx` | `ui-tool/.../components/ToolRow.tsx` | PTY 终端语义（工具输出在终端流） |
| 工具调用树（嵌套） | （无独立组件） | `ui-tool/.../ToolCallTree.tsx`、`ToolDetails.tsx` | PTY 终端语义 |
| 工具动作组 | `ai-elements/tool-actions-group.tsx` | `ui-tool/.../models/tool-call-model.ts` | PTY 终端语义 |
| 终端输出（ANSI） | `ai-elements/terminal.tsx` | `ui-primitives/src/TerminalBlock.tsx`、`toolviews/bash-sample.tsx` | **原生**：整个聊天即 xterm 终端（`pages/ChatPage.tsx`） |
| 文件差异 diff | `chat/DiffSummary.tsx`、`ai-elements/artifact.tsx` | `ui-primitives/src/DiffBlock.tsx`、`toolviews/file-mutation-row.tsx` | PTY 终端语义 |
| 文件读取展示 | `ai-elements/file-tree.tsx` | `ui-primitives/src/ReadBlock.tsx`、`toolviews/read-row.tsx` | `pages/FilesPage.tsx`（独立文件页，非聊天内联） |
| 搜索/来源 | `ai-elements/sources.tsx`、`chat/SearchSources.tsx` | `ui-primitives/src/SearchBlock.tsx`、`toolviews/search-row.tsx` | PTY 终端语义 |
| 网页/Web 卡片 | （并入 sources） | `ui-primitives/src/WebBlock.tsx`、`toolviews/web-row.tsx` | PTY 终端语义 |
| 通用工具卡片 | `ai-elements/tool.tsx` | `ui-tool/.../toolviews/GenericToolCard.tsx` | PTY 终端语义 |
| 危险操作确认 | `ai-elements/confirmation.tsx` | `ui-primitives/src/RiskConfirmation.tsx` | PTY 终端内确认；`components/ConfirmDialog.tsx`（通用弹窗） |

## 四、权限确认 / 人在环（同步交互，P1）

| 功能 | CP | DH | HM |
|---|---|---|---|
| 权限请求面板 | `chat/PermissionPrompt.tsx` | `ui-conversation/.../skeleton/ApprovalPanel.tsx` | PTY 终端内交互 |
| 权限模式选择 | `chat/ChatPermissionSelector.tsx` | `skeleton/PermissionSelect.tsx`、`ui-permission-presets/.../PermissionRow.tsx` | PTY 终端语义 |
| 权限预设管理 | （无） | `ui-permission-presets/.../settings-store.ts` | `pages/ConfigPage.tsx`（配置侧） |
| 自动审查通知 | `chat/PermissionReviewNotices.tsx` | （并入 ApprovalPanel 状态） | PTY 终端语义 |
| 等待权限的任务面板 | `chat/TaskWaitingForPermissionPanel.tsx` | `skeleton/ApprovalPanel.tsx` | PTY 终端语义 |

## 五、输入区 Composer（P0 / P3）

| 功能 | CP | DH | HM |
|---|---|---|---|
| 消息输入框 | `chat/MessageInput.tsx`、`ai-elements/prompt-input.tsx` | `skeleton/InputBar.tsx`、`input/machine.ts` | xterm 输入 + `lib/pty-mobile-input.ts`、`pty-keyboard-shortcuts.ts` |
| 输入状态机/提交策略 | （分散在 hooks） | `input/machine.ts`、`submission-policy.ts` | `lib/pty-composition.ts`（IME 合成转发） |
| 输入区动作栏 | `chat/ChatComposerActionBar.tsx` | `skeleton/InputBar.tsx`（一体） | ChatPage 顶部操作（复制/重置/侧栏） |
| 触发菜单（/ 与 @） | 分别实现 | `ui-input-trigger/.../MenuView.tsx`、`core/detect.ts` | `components/SlashPopover.tsx` + `lib/slashExec.ts` |
| 斜杠命令 | `chat/SlashCommandPopover.tsx`、`hooks/useSlashCommands.ts` | `ui-commands/.../PopupSelectView.tsx`、`service.ts` | `components/SlashPopover.tsx`、`lib/slashExec.ts` |
| @ 提及 / 引用 | `chat/MessageInputParts.tsx`、`hooks/useMentionTokenEstimate.ts` | `ui-reference/`、`chat/reference/ReferenceIcon.tsx` | （无独立，终端语义） |
| 文件附件 / 粘贴图片 | `ai-elements/attachments.tsx`、`chat/FileCard.tsx` | `ui-attachment/` | `lib/chatImagePaste.ts`（终端粘贴图片） |
| Enter 行为设置 | （settings） | `settings/EnterBehaviorRow.tsx` | `lib/pty-keyboard-shortcuts.ts` |
| 目录/工作区选择 | `chat/FolderPicker.tsx`、`hooks/useNativeFolderPicker.ts` | `ui-directory-picker-*`、`ui-workspace/` | `pages/FilesPage.tsx` |

## 六、流控制与运行状态（异步生命周期，P2）

| 功能 | CP | DH | HM |
|---|---|---|---|
| 流订阅 / 事件解析 | `hooks/useSSEStream.ts`、`useStreamSubscription.ts` | `ui-conversation/.../service.ts` + `runtime/`（SSE） | `lib/gatewayClient.ts`（WS JSON-RPC）、`lib/events-reconnect.ts` |
| 会话服务/连接 | `lib/stream-session-manager.ts` | `connection/`、`runtime/` | `lib/gatewayClient.ts`、`@hermes/shared`（JsonRpcGatewayClient） |
| 停止 / 中断 | `stream-session-manager`（stopStream） | `runtime/`（interrupt） | 终端 Ctrl-C 转发（`lib/pty-keyboard-shortcuts.ts`） |
| 消息排队 | `stream-session-manager`（enqueueMessage） | `queue/QueueDock.tsx`、`queue/store.ts` | （无，终端串行） |
| 回退点 / rewind / 重试 | `stream-session-manager`（getRewindPoints） | `conversation-nodes/retry.ts`、`turn-tail.ts` | ChatPage 重置按钮（RotateCcw），无逐轮 rewind |
| 断线重连 / resume | `hooks/events-reconnect`（无独立文件，内联） | `connection/` | `lib/pty-reconnect.ts`、`pty-resume-loading.ts`、`pty-resume-sanitizer.ts`、`events-reconnect.ts` |
| 运行状态总览 | `chat/RunCockpit.tsx`、`RunStatusPanel.tsx` | `chat/StatsLine.tsx`、`turn-metrics.ts` | `components/SidebarStatusStrip.tsx`、`hooks/useSidebarStatus.ts` |
| 运行/任务检查点 | `chat/RunCheckpoint.tsx`、`TaskCheckpoint.tsx` | `conversation-nodes/*` | （无） |
| 终止原因提示 | `chat/TerminalReasonChip.tsx` | `conversation-nodes/turn-error.ts`、`turn-max-tokens.ts` | PTY 终端语义 |
| 连接状态横幅 | （无独立） | `ui-primitives/src/ConnectionBanner.tsx` | `components/MemoryPressureBanner.tsx`（资源告警） |

## 七、任务 / 子代理 / Plan（Multi-agent，P3）

| 功能 | CP | DH | HM |
|---|---|---|---|
| 任务清单 (Todo) | `ai-elements/task.tsx`、`chat/TaskRunMarker.tsx` | `skeleton/TodoPanel.tsx`、`toolviews/todo-row.tsx` | PTY 终端语义 |
| 子代理卡片 | `chat/SubagentCard.tsx`、`SubagentModelIcon.tsx` | `ui-subagent/.../SubagentHeaderLineage.tsx` | PTY 终端语义 |
| Plan 模式控制 | （无） | `ui-plan/.../PlanModeControl.tsx` | PTY 终端语义 |
| Plan 审查面板 | （无） | `ui-user-questions/.../PlanReviewPanel.tsx` | PTY 终端语义 |
| Agent 向用户提问 | （无独立） | `ui-user-questions/.../QuestionComposer.tsx`、`toolviews/ask-question-row.tsx` | PTY 终端语义 |
| 目标 (Goal) | （无） | `ui-goal/` | （无） |
| 后台任务 (Jobs) | `hooks/useBatchImageGen.ts`（仅图片） | `ui-jobs/`（通用） | `pages/CronPage.tsx`、`components/ScheduleBuilder.tsx`（定时任务） |
| 工作流运行 | （无） | `ui-workflow-run/` | `components/AutomationBlueprints.tsx` |
| 轨迹回放/表格 | （无） | `ui-trajectory/.../TrajectoryView.tsx` 等 | `pages/SessionsPage.tsx`（会话历史，非逐 turn 轨迹） |

## 八、模型 / 运行时 / 上下文配置（P3）

| 功能 | CP | DH | HM |
|---|---|---|---|
| 模型选择器 | `chat/ModelSelectorDropdown.tsx`、`ai-elements/model-selector.tsx` | `ui-model-selection/`、`ui-settings-models/` | `components/ModelPickerDialog.tsx`、`pages/ModelsPage.tsx`、`lib/model-picker-filter.ts` |
| 模型信息卡 | `hooks/useProviderModels.ts` | `ui-settings-models/` | `components/ModelInfoCard.tsx`、`ModelReloadConfirm.tsx` |
| 运行时选择/切换 | `chat/RuntimeSelector.tsx`、`RuntimeSwitchMarker.tsx` | `runtime/` | `pages/ProfilesPage.tsx`、`components/ProfileSwitcher.tsx`（profile 即运行配置） |
| 思考强度选择 | `chat/EffortSelectorDropdown.tsx` | `submission-settings.ts`、`ui-agent-preset/` | `components/ReasoningPicker.tsx`、`lib/reasoning-effort.ts` |
| 模式指示 | `chat/ModeIndicator.tsx` | `ui-plan/` + `submission-settings.ts` | `components/ProfileScopeBanner.tsx` |
| 上下文用量指示 | `chat/ContextUsageIndicator.tsx`、`ai-elements/context.tsx` | `skeleton/ContextMeter.tsx` | `components/MemoryPressureBanner.tsx`（资源侧，非 token 环） |
| 上下文注入/明细 | `chat/context-breakdown/` | `chat/ContextBody.tsx`、`ContextInjectionRow.tsx` | （无） |
| 上下文压缩展示 | `useSSEStream`（onContextCompressed） | `chat/CompactionItem.tsx`、`conversation-nodes/compaction.ts` | PTY 终端语义（compressor 在后端 `trajectory_compressor.py`） |
| 速率限制横幅 | `chat/RateLimitBanner.tsx` | （无独立组件） | （无） |
| Agent 预设 / Profile | （无） | `ui-agent-preset/` | `pages/ProfilesPage.tsx`、`ProfileBuilderPage.tsx`、`components/ProfileSwitcher.tsx` |
| 技能 | `hooks`（skill_nudge 回调） | `ui-skill/` | `pages/SkillsPage.tsx`、`components/SkillEditorDialog.tsx` |
| MCP / 工具集配置 | `.mcp.json` | （host 侧） | `pages/McpPage.tsx`、`components/ToolsetConfigDrawer.tsx` |

## 九、多媒体 / 交付物（P4，可选）

| 功能 | CP | DH | HM |
|---|---|---|---|
| 图片缩略图 / 灯箱 | `chat/ImageThumbnail.tsx`、`ImageLightbox.tsx` | `ui-attachment/` | （无独立，终端粘贴见 `lib/chatImagePaste.ts`） |
| 图片生成卡片 | `chat/ImageGenCard.tsx`、`ImageGenConfirmation.tsx` | （无） | （无） |
| 媒体预览 | `chat/MediaPreview.tsx` | `ui-attachment/` | `pages/FilesPage.tsx` |
| 批量图片生成 | `chat/batch-image-gen/`、`hooks/useBatchImageGen.ts` | `ui-jobs/` | `batch_runner.py`（后端，无前端卡片） |
| 交付物 (deliverables) | （无） | `ui-deliverables/` | `pages/FilesPage.tsx`（产物文件） |

## 十、辅助 / 布局 / 健壮性（贯穿各阶段）

| 功能 | CP | DH | HM |
|---|---|---|---|
| 空状态 / 欢迎页 | `chat/ChatEmptyState.tsx`、`NewChatWelcome.tsx` | `skeleton/EmptyHero.tsx`、`ui-primitives/.../OnboardingSurface.tsx` | `pages/PairingPage.tsx`（二维码配对引导） |
| 侧栏 / 会话列表 | （app 布局） | `ui-sidebar/`、`ui-layout/` | `components/ChatSessionList.tsx`、`ChatSidebar.tsx`、`SidebarFooter.tsx` |
| 详情面板 | `chat/RunCockpitPopoverContent.tsx` | `skeleton/DetailsPanel.tsx` | `components/ChatSidebar.tsx` |
| 组件错误边界 | `chat/WidgetErrorBoundary.tsx`、`WidgetRenderer.tsx` | `ui-renderer/`（统一兜底） | （React Router 层） |
| 消息反馈（点赞/踩） | （无） | `ui-message-feedback/` | （无） |
| 主题 | `hooks/useAppTheme.ts` | `ui-theme/`、`ui-brand-official/` | `components/ThemeSwitcher.tsx`、`src/themes/` |
| Toast / 弹窗 | `hooks/useToast.ts` | `ui-primitives/src/Toast.tsx` | `components/ConfirmDialog.tsx`、`DeleteConfirmDialog.tsx`、`hooks/useModalBehavior.ts` |
| 基础原语 | `components/ui/*` | `ui-primitives/src/*` | `@nous-research/ui`（外部组件库）+ `components/AutoField.tsx` |
| 国际化 | `hooks/useTranslation.ts`、`i18n/{en,zh}.ts` | 各包 `locales.ts` + `locale/` | `src/i18n/`、`components/LanguageSwitcher.tsx`（en/es/zh/ur-pk） |
| 认证 / 配对 | （无） | `credentials`（host 侧） | `components/AuthWidget.tsx`、`OAuthLoginModal.tsx`、`pages/PairingPage.tsx`（QR 码远程配对） |
| 插件/渲染注册 | （无，命令式） | `ui-slots/`、`ui-renderer/`、各包 `apply.ts` + `contract/slots.ts` | `src/plugins/`（页面级插件） |

---

## 附录 A：事件交互协议（后端需对齐）

### A.1 CP 的 SSE 回调（最完整，作为契约检查清单）

从 CP 的 `hooks/useSSEStream.ts` 回调集合反推。DH 侧由 `runtime/` sessions 服务 + `ui-conversation/service.ts` 消费。

| 事件 | 含义 |
|---|---|
| `onText` | 助手文本增量 |
| `onThinking` | 思考内容增量 |
| `onToolUse` | 工具开始调用（名字 + 入参） |
| `onToolOutput` | 工具实时输出（如 shell stdout） |
| `onToolProgress` | 工具执行耗时进度 |
| `onToolResult` | 工具结果（含 media / sources / 是否 error） |
| `onToolTimeout` | 工具超时 |
| `onStatus` | 状态文字 |
| `onPermissionRequest` / `onPermissionResolved` / `onPermissionReview` | 权限请求 / 自动解决(超时) / 自动审查拒绝 |
| `onTaskUpdate` | 任务清单更新 |
| `onRewindPoint` | 可回退点 |
| `onFileChanged` | 文件变更（触发预览刷新） |
| `onModeChanged` | 模式切换 |
| `onContextUsage` / `onContextCompressed` | 上下文用量快照 / 压缩完成 |
| `onRateLimit` | 速率限制信息 |
| `onSkillNudge` | 技能提示 |
| `onInitMeta` | 会话初始化元信息（可用 tools / slash_commands / skills / mcp_servers） |
| `onResult` | 本轮结束（token 用量 + 终止原因） |
| `onKeepAlive` / `onError` | 保活 / 错误 |

### A.2 DH 后端 API 形态（SSE，沿用其 sessions 服务契约）

`POST /sessions` 创建、`POST /sessions/:id/messages` 发送、`GET /sessions/:id/stream` 流、`POST /sessions/:id/interrupt` 中断、`DELETE /sessions/:id` 关闭。

### A.3 HM 的 WS JSON-RPC 方言（tui_gateway，`lib/gatewayClient.ts`）

浏览器 WebSocket 说与 Ink TUI 完全相同的换行分隔 JSON-RPC；服务端把同一 dispatcher 的输出路由到 stdout 或 WebSocket。结构化事件极少（富交互都在 PTY 流里）：

| 方法 / 事件 | 类型 | 含义 |
|---|---|---|
| `session.create` | request | 建会话，返回 `session_id` |
| `session.info` | request | 查会话信息 |
| `prompt.submit` | request | 提交用户输入 |
| `message.delta` | event | 助手文本增量（`payload.text`） |
| （其余工具/权限/reasoning） | — | 走 PTY 终端流，不在结构化事件层 |

## 附录 B：三种交互模型对比（对自研的核心指导）

| 维度 | CP | DH | HM |
|---|---|---|---|
| 传输 | SSE | SSE（sessions 服务） | WebSocket JSON-RPC |
| 渲染范式 | 结构化 React 组件 | node 化结构化组件（可注册） | **PTF→xterm 终端镜像** + 轻结构化侧栏 |
| 组织 | 命令式组件树 | 契约驱动 39 个 `ui-*` 包 | 组件平铺 `web/src/components` |
| 富交互（工具/权限/reasoning） | 结构化卡片 | 结构化卡片/node | 终端语义（复用 TUI） |
| 会话历史/切换 | app 布局 | `ui-sidebar` | `ChatSessionList` / `SessionsPage` |
| 独有亮点 | 图片生成全链路、速率限制横幅 | Plan/轨迹/目标/交付物/反馈、契约插件化 | 二维码远程配对、多渠道(Slack)、Cron、移动端终端输入 |

## 附录 C：取舍建议（对自研的落地结论）

- **架构基座取 DH**：Cordis + slot 契约 + 包拆分正是我们已定方向（`ui-slots` → `ui-renderer` → 业务 `ui-*` 包，`apply.ts` + `contract/slots.ts` 声明式注册）。自研包结构直接对齐 DH。
- **消息 node 化取 DH**：`conversation-nodes/*`（assistant / tool / command / compaction / turn-tail…）把每种消息类型建模成可注册 node，比 CP 命令式组件树更利于扩展。
- **工具卡片分层取 DH**：`models/*`（数据模型）+ `toolviews/*`（视图）+ `ToolRow`/`ToolCallTree`（容器），原生支持嵌套子调用树。
- **交互协议取 CP**：SSE 回调粒度最细最完整（附录 A.1），作为后端事件契约检查清单。
- **不取 HM 的 PTY-终端路线**：HM 把 TUI 转发进 xterm，改动最小但交互是终端语义（无结构化工具卡片/权限面板），与我们"结构化 Web UI + SSE"的目标不符。**但可借鉴 HM 的**：
  - 断线重连/resume 的工程化拆分（`pty-reconnect` / `pty-resume-loading` / `pty-resume-sanitizer` / `events-reconnect` 各自单测），我们的 SSE 重连可参考这种可测试的状态拆分。
  - 移动端输入/IME 合成处理（`pty-mobile-input`、`pty-composition`），Web 端输入框要注意。
  - 二维码远程配对（`PairingPage`）、资源告警横幅（`MemoryPressureBanner`），按需纳入。
- **DH 独有、值得纳入**：Plan 模式（`ui-plan`）、Agent 提问（`ui-user-questions`）、目标（`ui-goal`）、通用后台任务（`ui-jobs`）、轨迹回放（`ui-trajectory`）、交付物（`ui-deliverables`）、消息反馈（`ui-message-feedback`）。
- **CP 独有、按需纳入**：图片生成全链路（`batch-image-gen`）、速率限制横幅（`RateLimitBanner`）、runtime 切换标记（`RuntimeSwitchMarker`）。
