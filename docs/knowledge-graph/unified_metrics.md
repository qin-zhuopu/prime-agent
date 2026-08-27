# Unified knowledge graph -- Metrics

- Total nodes: 1000, edges: 1806

## Node types

| ntype | count |
|---|---|
| endpoint | 602 |
| page | 165 |
| endpoint_group | 132 |
| feature | 73 |
| repo | 11 |
| category | 10 |
| protocol | 7 |

## Edge types

| etype | count |
|---|---|
| has_endpoint | 602 |
| calls | 488 |
| implements | 327 |
| in_repo | 165 |
| has_group | 132 |
| contains | 73 |
| uses | 19 |

## Per-repo unified footprint

| repo | features | endpoints | endpoint groups | pages |
|---|---|---|---|---|
| CodePilot | 60 | 250 | 31 | 155 |
| deepseek-harness | 71 | 53 | 10 | 4 |
| hermes-agent | 61 | 299 | 91 | 6 |

This single graph joins the UI-feature view and the full backend/frontend view on shared repo nodes: you can traverse feature -> repo -> endpoint_group -> endpoint <- page without leaving the graph. UI-layer nodes carry layer='ui', backend/page nodes carry layer='api'; repo nodes are shared.
