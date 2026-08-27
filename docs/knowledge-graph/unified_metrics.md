# Unified knowledge graph -- Metrics

- Total nodes: 1151, edges: 2192

## Node types

| ntype | count |
|---|---|
| endpoint | 602 |
| page | 165 |
| endpoint_group | 132 |
| feature | 73 |
| operation | 57 |
| component | 43 |
| capability | 22 |
| entity | 14 |
| repo | 11 |
| webui | 11 |
| category | 10 |
| protocol | 7 |
| api | 4 |

## Edge types

| etype | count |
|---|---|
| has_endpoint | 602 |
| calls | 555 |
| implements | 327 |
| in_repo | 165 |
| provides | 154 |
| has_group | 132 |
| exposes | 93 |
| contains | 73 |
| has_op | 57 |
| uses | 19 |
| located_in | 15 |

## Capability coverage across ALL 11 repos (normalized user operations)

| repo | capabilities provided |
|---|---|
| deepseek-harness | 21 |
| CodePilot | 21 |
| hermes-agent | 20 |
| OpenGUI | 15 |
| agents-chat | 14 |
| opencode-chatui | 12 |
| assistant-ui | 12 |
| acp-ui | 11 |
| acp-components | 11 |
| CopilotKit | 9 |
| acp-web-gateway | 8 |

## Per-repo backend/frontend footprint (source-verified deep cluster)

| repo | features | endpoints | endpoint groups | pages |
|---|---|---|---|---|
| CodePilot | 60 | 250 | 31 | 155 |
| deepseek-harness | 71 | 53 | 10 | 4 |
| hermes-agent | 61 | 299 | 91 | 6 |

This single graph joins the UI-feature view and the full backend/frontend view on shared repo nodes: you can traverse feature -> repo -> endpoint_group -> endpoint <- page without leaving the graph. UI-layer nodes carry layer='ui', backend/page nodes carry layer='api'; repo nodes are shared.
