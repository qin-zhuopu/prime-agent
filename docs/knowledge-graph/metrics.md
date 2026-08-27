# Chat/Agent UI Knowledge Graph -- Metrics

- Nodes: 101  (repos=11, protocols=7, categories=10, features=73)
- Edges: 419
- Emergent tiers (by feature coverage, natural break gap=29): 3 deep + 8 broad (NOT hand-assigned; see derive_tier.py)

## Per-repo feature coverage

| repo | tier (emergent) | structured | terminal | total impl |
|---|---|---|---|---|
| CodePilot | deep | 60 | 0 | 60 |
| deepseek-harness | deep | 71 | 0 | 71 |
| hermes-agent | deep | 41 | 20 | 61 |
| acp-components | broad | 31 | 0 | 31 |
| acp-ui | broad | 19 | 0 | 19 |
| assistant-ui | broad | 17 | 0 | 17 |
| opencode-chatui | broad | 16 | 0 | 16 |
| OpenGUI | broad | 18 | 0 | 18 |
| CopilotKit | broad | 10 | 0 | 10 |
| agents-chat | broad | 14 | 0 | 14 |
| acp-web-gateway | broad | 10 | 0 | 10 |

## Protocol adoption (repos per protocol)

| protocol | #repos | repos |
|---|---|---|
| SSE | 2 | CodePilot, deepseek-harness |
| WS-JSONRPC | 1 | hermes-agent |
| ACP | 4 | acp-components, acp-ui, acp-web-gateway, agents-chat |
| AG-UI | 1 | CopilotKit |
| structured-render | 9 | CodePilot, CopilotKit, OpenGUI, acp-components, acp-ui, agents-chat, assistant-ui, deepseek-harness, opencode-chatui |
| node-render | 1 | deepseek-harness |
| pty-terminal | 1 | hermes-agent |

## Cross-repo signals (primary 3, source-verified)

- Universal (all 3 implement, any form): 50
  - Structured in all 3 (safest to build first): assistant-markdown, attachments, background-jobs, context-usage, conversation-view, details-panel, dir-picker, effort-setting, empty-welcome, error-boundary, file-read-view, i18n, mcp-config, media-preview, message-actions, message-input, model-picker, primitives, reconnect-resume, rewind-retry, risk-confirm, run-status, runtime-switch, session-connect, sidebar-session-list, skills, slash-commands, stop-interrupt, stream-subscribe, submission-policy, terminal-output, theme, thinking-anim, toast-modal
- DH-only: goal, message-feedback
- CP-only: image-gen, rate-limit-banner
- HM-only: (none)

## Feature maturity across ALL repos (primary + survey)

Top features by #repos implementing (demand / table-stakes signal):

| feature | category | #repos |
|---|---|---|
| message-input | composer | 11 |
| assistant-markdown | messaging | 11 |
| conversation-view | messaging | 11 |
| message-list | messaging | 11 |
| streaming-typing | messaging | 11 |
| stream-subscribe | stream-control | 11 |
| tool-card | tool-use | 11 |
| theme | aux | 10 |
| primitives | aux | 9 |
| sidebar-session-list | aux | 9 |
| session-connect | stream-control | 9 |
| stop-interrupt | stream-control | 8 |
| code-highlight | messaging | 7 |
| model-picker | model-config | 7 |
| permission-panel | permission | 7 |
| diff-view | tool-use | 7 |
| empty-welcome | aux | 6 |
| attachments | composer | 5 |
| submission-policy | composer | 5 |
| message-actions | messaging | 5 |

## Features absent from ALL survey repos

(present only in the primary trio; either niche or high-effort differentiators)

agent-asks-user, agent-preset, auth-pairing, auto-review-notice, background-jobs, batch-image-gen, chain-of-thought, compaction-view, context-injection, deliverables, effort-setting, error-boundary, goal, image-gen, image-thumb-lightbox, math-katex, media-preview, mentions, message-feedback, message-queue, permission-presets, plan-review, rate-limit-banner, rewind-retry, risk-confirm, run-status, terminal-output, terminal-reason, thinking-anim, toast-modal, todo-list, trajectory-replay, virtual-scroll, web-card, workflow-run

Interpretation: features implemented by many repos are proven table-stakes; features absent from the whole survey set are differentiators to adopt selectively. Survey-repo edges are `source=declared` (README/structure scan), primary edges are `source=verified` (source read).
