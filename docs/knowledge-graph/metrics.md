# Chat/Agent UI Knowledge Graph — Metrics

- Nodes: 91  (repos=3, protocols=5, categories=10, features=73)
- Edges: 272

## Per-repo feature coverage

| repo | structured | terminal | total impl | absent |
|---|---|---|---|---|
| CodePilot | 60 | 0 | 60 | 13 |
| deepseek-harness | 71 | 0 | 71 | 2 |
| hermes-agent | 41 | 20 | 61 | 12 |

## Cross-repo signals

- Universal (all 3 implement, any form): 50
  - Structured in all 3 (safest to build first): assistant-markdown, attachments, background-jobs, context-usage, conversation-view, details-panel, dir-picker, effort-setting, empty-welcome, error-boundary, file-read-view, i18n, mcp-config, media-preview, message-actions, message-input, model-picker, primitives, reconnect-resume, rewind-retry, risk-confirm, run-status, runtime-switch, session-connect, sidebar-session-list, skills, slash-commands, stop-interrupt, stream-subscribe, submission-policy, terminal-output, theme, thinking-anim, toast-modal
- DH-only (unique to deepseek-harness): goal, message-feedback
- CP-only (unique to CodePilot): image-gen, rate-limit-banner
- HM-only (unique to hermes-agent): (none)

## Feature maturity (by #repos implementing)

- 3 repo(s): 50 features
- 2 repo(s): 19 features
- 1 repo(s): 4 features

Interpretation: 3-repo features are proven table-stakes; 1-repo features are differentiators to adopt selectively.
