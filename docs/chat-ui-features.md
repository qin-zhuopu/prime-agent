# 聊天 / AI Agent 交互 UI 功能表（双 repo 综合参考）

> 目的：盘点「用户 ↔ AI Agent」交互所需的前端组件与功能，作为我们自研的需求参考。
> 综合两套开源实现的功能与代码定位，仅作**功能对照参考**，不复制代码。
>
> 参考来源：
> - **CodePilot**（记作 `CP`）：Electron + Next.js 16 + React 19 + `ai` SDK + streamdown + Shiki。命令式组件树。许可 BUSL-1.1（商业/大组织内部用途受限）。代码路径相对其仓库 `src/`。
> - **deepseek-harness**（记作 `DH`）：Cordis 插件架构 + React 渲染绑定 + 契约驱动 slot 注册。前端在 `packages/client/`，每个交互功能≈一个 `ui-*` 包。代码路径相对其仓库 `packages/client/`。
>
> 两者定位差异：CP 是"一个应用里的聊天页"，DH 是"可插拔的聊天 UI 组件库（Cordis 生态）"。DH 的架构更贴近我们自研的目标（契约驱动、包拆分、静态注册）。

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

| 功能 | CodePilot (CP, `src/`) | deepseek-harness (DH, `packages/client/`) |
|---|---|---|
| 会话主视图 | `components/chat/ChatView.tsx` | `ui-conversation/src/client/chat/ChatView.tsx` |
| 会话骨架/根容器 | `components/chat/ChatView.tsx`（一体） | `ui-conversation/src/client/skeleton/ConversationRoot.tsx`、`ConversationSession.tsx` |
| 消息列表 | `components/chat/MessageList.tsx` | `ui-conversation/src/client/chat/ChatView.tsx` + `ChatNodeSeat.tsx`（node 化渲染） |
| 虚拟滚动 | `components/chat/message-list-virtual.ts` | `ui-trajectory/src/client/trajectory-virtual-rows.ts`（轨迹视图虚拟行） |
| 单条消息 | `components/ai-elements/message.tsx`、`components/chat/MessageItem.tsx` | `ui-conversation/src/client/chat/MessageItem.tsx` |
| 流式打字/节流刷新 | `components/chat/StreamingMessage.tsx` | `ui-conversation/src/client/chat/use-throttled-visual-update.ts`、`AssistantNodeView.tsx` |
| 助手 Markdown | `components/chat/markdown-components.tsx` | `ui-conversation/src/client/chat/AssistantMarkdown.tsx` |
| Markdown 原语 | 依赖 `streamdown` | `ui-primitives/src/markdown/MarkdownText.tsx`、`render.tsx`、`incremental.ts`、`parse.ts` |
| 代码块高亮 | `components/ai-elements/code-block.tsx` + `shiki.worker.ts`（Web Worker） | `ui-primitives/src/markdown/CodeBlock.tsx`、`highlight.ts` |
| 数学公式 | `@streamdown/math` | `ui-primitives/src/markdown/katex.tsx`、`mathCompatibility.ts` |
| 消息操作（复制等） | `components/ai-elements/message.tsx` | `ui-conversation/src/client/chat/MessageIconActions.tsx` |
| 消息分支切换 | `components/ai-elements/message.tsx` | `ui-conversation/tests/chat-branch-tails` + `conversation-nodes/turn-tail.ts` |

## 二、思考 / 推理展示（Agent 特有，P1）

| 功能 | CP | DH |
|---|---|---|
| Reasoning 展示 | `components/ai-elements/reasoning.tsx` | `ui-conversation/src/client/chat/ReasoningRow.tsx` |
| 思维链步骤 | `components/ai-elements/chain-of-thought.tsx` | （并入 ReasoningRow / trajectory turn） |
| 思考中动效 | `components/ai-elements/shimmer.tsx` | `ui-primitives/src/StateDot.tsx`（状态点） |

## 三、工具调用（Tool Use，Agent 交互重点，P1）

| 功能 | CP | DH |
|---|---|---|
| 工具调用卡片/行 | `components/ai-elements/tool.tsx` | `ui-tool/src/client/tool/components/ToolRow.tsx` |
| 工具调用树（嵌套/子调用） | （无独立组件） | `ui-tool/src/client/tool/ToolCallTree.tsx`、`ToolDetails.tsx` |
| 工具动作组 | `components/ai-elements/tool-actions-group.tsx` | `ui-tool/src/client/tool/models/tool-call-model.ts` |
| 终端输出（ANSI） | `components/ai-elements/terminal.tsx` | `ui-primitives/src/TerminalBlock.tsx`、`ui-tool/.../toolviews/bash-sample.tsx`、`models/terminal-card-model.ts` |
| 文件差异 diff | `components/chat/DiffSummary.tsx`、`ai-elements/artifact.tsx` | `ui-primitives/src/DiffBlock.tsx`、`ui-tool/.../toolviews/file-mutation-row.tsx`、`models/diff-card-model.ts` |
| 文件读取展示 | `components/ai-elements/file-tree.tsx` | `ui-primitives/src/ReadBlock.tsx`、`ui-tool/.../toolviews/read-row.tsx`、`models/read-card-model.ts` |
| 搜索/来源 | `components/ai-elements/sources.tsx`、`chat/SearchSources.tsx` | `ui-primitives/src/SearchBlock.tsx`、`ui-tool/.../toolviews/search-row.tsx`、`models/search-card-model.ts` |
| 网页/Web 卡片 | （并入 sources） | `ui-primitives/src/WebBlock.tsx`、`ui-tool/.../toolviews/web-row.tsx`、`models/web-card-model.ts` |
| 通用工具卡片 | `components/ai-elements/tool.tsx` | `ui-tool/src/client/tool/toolviews/GenericToolCard.tsx` |
| 危险操作确认 | `components/ai-elements/confirmation.tsx` | `ui-primitives/src/RiskConfirmation.tsx` |

## 四、权限确认 / 人在环（同步交互，P1）

| 功能 | CP | DH |
|---|---|---|
| 权限请求面板 | `components/chat/PermissionPrompt.tsx` | `ui-conversation/src/client/skeleton/ApprovalPanel.tsx` |
| 权限模式选择 | `components/chat/ChatPermissionSelector.tsx` | `ui-conversation/src/client/skeleton/PermissionSelect.tsx`、`ui-permission-presets/src/client/PermissionRow.tsx` |
| 权限预设管理 | （无） | `ui-permission-presets/src/client/settings-store.ts`、`presentation.ts` |
| 自动审查通知 | `components/chat/PermissionReviewNotices.tsx` | （并入 ApprovalPanel 状态） |
| 等待权限的任务面板 | `components/chat/TaskWaitingForPermissionPanel.tsx` | `ui-conversation/src/client/skeleton/ApprovalPanel.tsx` |

## 五、输入区 Composer（P0 / P3）

| 功能 | CP | DH |
|---|---|---|
| 消息输入框 | `components/chat/MessageInput.tsx`、`ai-elements/prompt-input.tsx` | `ui-conversation/src/client/skeleton/InputBar.tsx`、`input/machine.ts`、`input/hub.ts` |
| 输入状态机/提交策略 | （分散在 hooks） | `ui-conversation/src/client/input/machine.ts`、`submission-policy.ts`、`contract/composer-submission.ts` |
| 输入区动作栏 | `components/chat/ChatComposerActionBar.tsx` | `ui-conversation/src/client/skeleton/InputBar.tsx`（一体） |
| 触发菜单（/ 与 @ 通用） | 分别实现 | `ui-input-trigger/src/client/MenuView.tsx`、`core/detect.ts`、`controller.ts` |
| 斜杠命令 | `components/chat/SlashCommandPopover.tsx`、`hooks/useSlashCommands.ts` | `ui-commands/src/client/PopupSelectView.tsx`、`service.ts`、`popup.ts` |
| @ 提及 / 引用 | `components/chat/MessageInputParts.tsx`、`hooks/useMentionTokenEstimate.ts` | `ui-reference/`、`ui-conversation/src/client/reference/ReferenceIcon.tsx` |
| 文件附件 | `ai-elements/attachments.tsx`、`chat/FileAttachmentDisplay.tsx`、`FileCard.tsx` | `ui-attachment/`、`ui-conversation/src/client/image-labels.ts` |
| Enter 行为设置 | （settings） | `ui-conversation/src/client/settings/EnterBehaviorRow.tsx` |
| 目录/工作区选择 | `components/chat/FolderPicker.tsx`、`hooks/useNativeFolderPicker.ts` | `ui-directory-picker-native/`、`ui-directory-picker-browse/`、`ui-workspace/` |

## 六、流控制与运行状态（异步生命周期，P2）

| 功能 | CP | DH |
|---|---|---|
| 流订阅 / SSE 解析 | `hooks/useSSEStream.ts`、`hooks/useStreamSubscription.ts` | `ui-conversation/src/client/service.ts` + `runtime/`（sessions 服务，SSE adapter） |
| 会话服务/连接 | `lib/stream-session-manager.ts` | `connection/`、`runtime/`（sessions.scope / sessions.list） |
| 停止 / 中断 | `lib/stream-session-manager.ts`（stopStream） | `runtime/`（interrupt）+ `ui-conversation/service.ts` |
| 消息排队 | `lib/stream-session-manager.ts`（enqueueMessage） | `ui-conversation/src/client/queue/QueueDock.tsx`、`queue/store.ts`、`contract/queue.ts` |
| 回退点 / rewind / 重试 | `lib/stream-session-manager.ts`（getRewindPoints） | `ui-conversation/src/client/conversation-nodes/retry.ts`、`turn-tail.ts` |
| 运行状态总览 | `components/chat/RunCockpit.tsx`、`RunStatusPanel.tsx` | `ui-conversation/src/client/chat/StatsLine.tsx`、`turn-metrics.ts` |
| 运行/任务检查点 | `components/chat/RunCheckpoint.tsx`、`TaskCheckpoint.tsx` | `ui-conversation/src/client/conversation-nodes/*`（node 化） |
| 终止原因提示 | `components/chat/TerminalReasonChip.tsx` | `ui-conversation/src/client/conversation-nodes/turn-error.ts`、`turn-max-tokens.ts`、`TurnTailNodeView.tsx` |
| 连接状态横幅 | （无独立） | `ui-primitives/src/ConnectionBanner.tsx` |

## 七、任务 / 子代理 / Plan（Multi-agent，P3）

| 功能 | CP | DH |
|---|---|---|
| 任务清单 (Todo) | `components/ai-elements/task.tsx`、`chat/TaskRunMarker.tsx` | `ui-conversation/src/client/skeleton/TodoPanel.tsx`、`ui-tool/.../toolviews/todo-row.tsx` |
| 子代理卡片 | `components/chat/SubagentCard.tsx`、`SubagentModelIcon.tsx` | `ui-subagent/src/client/SubagentHeaderLineage.tsx`、`SubagentReadOnlyComposer.tsx` |
| Plan 模式控制 | （无） | `ui-plan/src/client/PlanModeControl.tsx` |
| Plan 审查面板 | （无） | `ui-user-questions/src/client/PlanReviewPanel.tsx` |
| Agent 向用户提问 | （无独立） | `ui-user-questions/src/client/QuestionComposer.tsx`、`ui-tool/.../toolviews/ask-question-row.tsx` |
| 目标 (Goal) | （无） | `ui-goal/` |
| 后台任务 (Jobs) | `hooks/useBatchImageGen.ts`（仅图片） | `ui-jobs/`（通用后台任务） |
| 工作流运行 | （无） | `ui-workflow-run/` |
| 轨迹回放/表格 | （无） | `ui-trajectory/src/client/TrajectoryView.tsx`、`TrajectoryTimeline.tsx`、`TrajectoryTable.tsx` 等 |

## 八、模型 / 运行时 / 上下文配置（P3）

| 功能 | CP | DH |
|---|---|---|
| 模型选择器 | `components/chat/ModelSelectorDropdown.tsx`、`ai-elements/model-selector.tsx`、`hooks/useProviderModels.ts` | `ui-model-selection/`、`ui-settings-models/` |
| 运行时选择/切换 | `components/chat/RuntimeSelector.tsx`、`RuntimeSwitchMarker.tsx` | `runtime/`（多 runtime 由 sessions 服务承载） |
| 思考强度选择 | `components/chat/EffortSelectorDropdown.tsx` | `ui-conversation/src/client/submission-settings.ts`、`ui-agent-preset/` |
| 模式指示 | `components/chat/ModeIndicator.tsx` | `ui-plan/`（Plan 模式）+ `submission-settings.ts` |
| 上下文用量指示 | `components/chat/ContextUsageIndicator.tsx`、`ai-elements/context.tsx`、`hooks/useContextUsage.ts` | `ui-conversation/src/client/skeleton/ContextMeter.tsx` |
| 上下文注入/明细 | `components/chat/context-breakdown/` | `ui-conversation/src/client/chat/ContextBody.tsx`、`ContextInjectionRow.tsx` |
| 上下文压缩展示 | `useSSEStream`（onContextCompressed 回调） | `ui-conversation/src/client/chat/CompactionItem.tsx`、`CompactionCommandCard.tsx`、`conversation-nodes/compaction.ts` |
| 速率限制横幅 | `components/chat/RateLimitBanner.tsx` | （无独立组件） |
| Agent 预设 | （无） | `ui-agent-preset/` |
| 技能 | `hooks`（skill_nudge 回调） | `ui-skill/` |

## 九、多媒体 / 交付物（P4，可选）

| 功能 | CP | DH |
|---|---|---|
| 图片缩略图 / 灯箱 | `components/chat/ImageThumbnail.tsx`、`ImageLightbox.tsx` | `ui-attachment/` |
| 图片生成卡片 | `components/chat/ImageGenCard.tsx`、`ImageGenConfirmation.tsx` | （无，DH 非图片方向） |
| 媒体预览 | `components/chat/MediaPreview.tsx` | `ui-attachment/` |
| 批量图片生成 | `components/chat/batch-image-gen/`、`hooks/useBatchImageGen.ts` | `ui-jobs/`（通用任务，非图片专用） |
| 交付物 (deliverables) | （无） | `ui-deliverables/` |

## 十、辅助 / 布局 / 健壮性（贯穿各阶段）

| 功能 | CP | DH |
|---|---|---|
| 空状态 / 欢迎页 | `components/chat/ChatEmptyState.tsx`、`NewChatWelcome.tsx` | `ui-conversation/src/client/skeleton/EmptyHero.tsx`、`ui-primitives/src/OnboardingSurface.tsx` |
| 侧栏 / 会话列表 | （app 布局） | `ui-sidebar/`、`ui-layout/` |
| 详情面板 | `components/chat/RunCockpitPopoverContent.tsx` | `ui-conversation/src/client/skeleton/DetailsPanel.tsx` |
| 组件错误边界 | `components/chat/WidgetErrorBoundary.tsx`、`WidgetRenderer.tsx` | `ui-renderer/`（Cordis→React 桥接层统一兜底） |
| 消息反馈（点赞/踩） | （无） | `ui-message-feedback/` |
| 主题 | `hooks/useAppTheme.ts` | `ui-theme/`、`ui-brand-official/` |
| Toast 通知 | `hooks/useToast.ts` | `ui-primitives/src/Toast.tsx` |
| 基础原语 (Button/Modal/Tooltip…) | `components/ui/*` | `ui-primitives/src/*`（Button/Modal/Tooltip/HoverCard/Menu/Pill…） |
| 国际化 | `hooks/useTranslation.ts`、`i18n/{en,zh}.ts` | 各包 `locales.ts` + `locale/`（分布式 i18n） |
| 插件/渲染注册 | （无，命令式） | `ui-slots/`（SlotCore）、`ui-renderer/`、各包 `apply.ts` + `contract/slots.ts` |

---

## 附录 A：SSE / 事件交互协议（后端需对齐）

从 CP 的 `hooks/useSSEStream.ts` 回调集合反推的流式事件协议（DH 侧由 `runtime/` 的 sessions 服务 + `ui-conversation/service.ts` 消费）。这是「用户↔Agent 交互」的骨架，建议后端按此粒度设计：

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

DH 后端 API 形态（沿用其 sessions 服务契约）：`POST /sessions` 创建、`POST /sessions/:id/messages` 发送、`GET /sessions/:id/stream` 流、`POST /sessions/:id/interrupt` 中断、`DELETE /sessions/:id` 关闭。

## 附录 B：两套实现取舍建议（对自研的指导）

- **架构基座取 DH**：DH 的 Cordis + slot 契约 + 包拆分正是我们已定的方向（`ui-slots` → `ui-renderer` → 业务 `ui-*` 包，`apply.ts` + `contract/slots.ts` 声明式注册）。自研包结构直接对齐 DH。
- **消息 node 化取 DH**：DH 用 `conversation-nodes/*`（assistant / tool / command / compaction / turn-tail…）把每种消息类型建模成可注册的 node 定义，比 CP 的命令式组件树更利于扩展新消息类型。
- **工具卡片分层取 DH**：DH 把工具拆成 `models/*`（数据模型）+ `toolviews/*`（视图）+ `ToolRow`/`ToolCallTree`（容器），比 CP 单个 `tool.tsx` 更清晰，且原生支持嵌套子调用树。
- **交互协议取 CP**：CP 的 SSE 回调粒度最细最完整（见附录 A），适合作为后端事件契约的检查清单。
- **DH 独有、CP 缺失、值得纳入**：Plan 模式（`ui-plan`）、Agent 向用户提问（`ui-user-questions`）、目标（`ui-goal`）、通用后台任务（`ui-jobs`）、轨迹回放（`ui-trajectory`）、交付物（`ui-deliverables`）、消息反馈（`ui-message-feedback`）。
- **CP 独有、DH 缺失、按需纳入**：图片生成全链路（`batch-image-gen`）、速率限制横幅（`RateLimitBanner`）、显式 runtime 切换标记（`RuntimeSwitchMarker`）。
