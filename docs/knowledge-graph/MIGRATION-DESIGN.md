# Knowledge Graph Migration Design: split `repo` into `repo` / `webui` / `api`

Authoritative spec for the `task-kg-repo-split` refactor. FEAT-002 through FEAT-005
implement this document. This file changes no graph data itself; it records the target
model, the by-path id rules, the edge re-homing, the attribute relocation, the
SDK-vs-api constraint, and the per-repo node mapping, plus the evidence sources that
justify each derived path.

Scope reminder: strictly `docs/knowledge-graph/`. No prime-agent business code. Never
hardcode the GitHub repo name or URL anywhere. Do not use em dashes in this repo's docs.

## 0. Baseline (captured before any change)

All commands run from `docs/knowledge-graph/` with the sandbox default `python3`
(3.9.25; networkx 3.2.1). Dependency check `python3 -c "import networkx,yaml,jsonschema"`
exits 0.

| Command | Result (verbatim) |
| --- | --- |
| `python3 validate.py` | `OK: 184 YAML nodes valid (schema + referential + semantic).` |
| `python3 build_from_yaml.py` | `UI graph: 101 nodes/419 edges; API graph: 117 nodes/214 edges` |
| `python3 build_full_graph.py` | `Full API graph: 902 nodes, 1387 edges` |
| `python3 build_unified_graph.py` | `Unified graph: 1022 nodes, 1960 edges` |

These four graphs must stay green (build succeeds, validate fail-closed passes) at every
step of the migration. Node/edge totals will legitimately change once the split lands;
the numbers above are the pre-migration reference point, not a post-migration target.

## 1. Motivation

The current `repo` node is app-heavy: it carries git identity (id, label, license) but
also frontend runtime facts (stack, transport, integration, browser_native, protocols)
and is the origin of every functional edge (uses/implements/provides/exposes). This
conflates three distinct concepts. Now that we distinguish frontend from backend, we
split the single `repo` node into three core node types.

## 2. Target node model (three core types)

### 2.1 `repo` (pure git identity)

The `repo` node keeps only what identifies the git repository.

```
repo {
  id: string        # uppercase abbreviation, e.g. CP, DH, HM, ACPC (pattern ^[A-Z][A-Z0-9]*$)
  ntype: "repo"
  label: string     # human name, e.g. CodePilot
  license?: string  # optional, unchanged
}
```

All app-level attributes (`stack`, `transport`, `integration`, `browser_native`,
`protocols`) LEAVE the repo node (see section 5, attribute relocation).

### 2.2 `webui` (a frontend located at repo + path)

A `webui` node represents a browser-facing frontend that lives at a specific
repo-relative path.

```
webui {
  id: string            # "W:<repoId>/<path>"  (see section 3, id rules)
  ntype: "webui"
  label: string         # human name for the surface, defaults to repo label
  repo: string          # owning repo id (must reference a repo node)
  path: string          # repo-relative source dir/file the frontend lives at ("." fallback)
  stack?: string        # relocated from repo
  transport?: [enum]    # relocated from repo (SSE|WebSocket|stdio|"none/unknown")
  integration?: [enum]  # relocated from repo (REST+SSE|WebSocket|stdio-rpc|in-process-sdk)
  browser_native?: bool # relocated from repo
  protocols?: [string]  # relocated from repo (protocol node ids)
}
```

### 2.3 `api` (a backend surface located at repo + path, subtyped by style)

An `api` node represents a network-reachable backend surface. It is subtyped by `style`.

```
api {
  id: string       # "A:<repoId>/<path>"  (see section 3, id rules)
  ntype: "api"
  label: string    # human name for the surface, defaults to repo label
  repo: string     # owning repo id (must reference a repo node)
  path: string     # repo-relative source dir/file the backend surface lives at ("." fallback)
  style: enum      # one of: rest | rpc | ws-rpc | stdio-rpc
  transport?: [enum] # SSE|WebSocket|stdio|"none/unknown", relocated where applicable
}
```

`style` values map to the existing operation-endpoint styles as follows:

| operation endpoint `style` (existing) | api node `style` |
| --- | --- |
| `REST` | `rest` |
| `RPC` | `rpc` |
| `WS-RPC` | `ws-rpc` |
| `stdio-rpc` | `stdio-rpc` |
| `sdk-call` | (no api node; see section 6) |

## 3. ID naming BY PATH (user decision A)

IDs are derived from the source path the surface lives at, so ids stay unique and stable
across rescans.

- `webui` id = `W:<repoId>/<path>`
- `api`   id = `A:<repoId>/<path>`

where `<path>` is the repo-relative source directory or file where the surface lives.

### 3.1 The `.` fallback (mandatory, documented explicitly)

The 11 source repos are NOT present in this sandbox and cannot be re-scanned. For the
three repos whose scanned source paths ARE materialized under `data/**` (CP, DH, HM), we
can derive concrete `<path>` values from that evidence. For the other 8 repos
(ACPC, ACPUI, ASTUI, OCUI, OGUI, CKIT, ACHAT, ACPWG) the concrete source path is unknown
because their source tree is absent and only per-repo surface evidence exists.

For any repo whose concrete source path is unknown, use `path = "."` (repo root). This
keeps ids `W:<repoId>/.` and `A:<repoId>/.` unique and stable per repo. When the source
becomes available later, the path can be tightened without changing the repo id.

Examples: `W:ASTUI/.`, `A:ACPWG/.`, `W:CP/src/components`, `A:CP/src/app/api`.

## 4. Edge re-homing (user decision B)

New structural edges introduced by the split:

- `webui --located_in--> repo`  (edge attr `path`)
- `api   --located_in--> repo`  (edge attr `path`)
- `webui --calls--> api`        (frontend calls a backend surface)

Existing functional edges are re-homed off `repo`:

| current edge | after migration originates from |
| --- | --- |
| `repo --uses--> protocol` | `webui --uses--> protocol` |
| `repo --implements--> feature` (attrs kind/source) | `webui --implements--> feature` |
| `repo --provides--> capability` (attrs surface_kind/surface_name) | `webui --provides--> capability` |
| `repo --exposes--> operation` (attrs name/http/style) | `api --exposes--> operation` |

Rationale: uses/implements/provides describe the user-facing frontend, so they move to
`webui`. `exposes` describes a backend surface, so it moves to `api`.

## 5. Attribute relocation

The following attributes move OFF `repo`:

| attribute | moves to |
| --- | --- |
| `stack` | `webui` |
| `transport` | `webui` (and `api` where a backend transport applies) |
| `integration` | `webui` |
| `browser_native` | `webui` |
| `protocols` | `webui` |
| `style` (new) | `api` |

`repo` retains only `id`, `ntype`, `label`, and optional `license`.

## 6. SDK modeling constraint (user decision E)

An `api` node exists ONLY for a surface reachable as a TCP / network endpoint, i.e. one of
`rest | rpc | ws-rpc | stdio-rpc-over-gateway`. Pure in-process SDK surfaces do NOT get an
`api` node; they are modeled as webui-only.

Concretely, in `map_capabilities.py` the per-repo evidence carries a `surface_kind`:

- Network kinds -> may back an `api` node: `endpoint` (REST), `rpc`, `ws-rpc`.
- In-process kinds -> NEVER back an `api` node: `sdk-hook`, `component`, `protocol`.

A pure-SDK repo (its surfaces are only `sdk-hook` / `component` / `protocol`) contributes
a `webui` node but NO `api` node. SDKs are modeled as api only once wrapped behind a
network endpoint (for example the acp-web-gateway exposes ACP over WebSocket).

### SDK repo audit (placeholder, to be filled from FEAT-005 findings)

FEAT-005 will audit the pure-SDK / broad repos (ACPC / ASTUI / CKIT and the other
survey repos) against their materialized surface evidence to decide, per repo, whether a
web ui and/or a network api node is warranted. The confirmed SDK-vs-api decision table
goes here once FEAT-005 produces it. Do NOT presume these repos lack a UI or api; decide
from the evidence in `map_capabilities.py` surface_kind and any `data/full` endpoint data.

Provisional expectation (subject to FEAT-005 confirmation), from current
`map_capabilities.py` evidence:

| repo | label | integration | network surfaces in evidence | provisional nodes |
| --- | --- | --- | --- | --- |
| CP | CodePilot | REST+SSE | REST endpoints (endpoints_CP.json) | repo + webui + api(rest) |
| DH | deepseek-harness | REST+SSE | rpc methods | repo + webui + api(rpc) |
| HM | hermes-agent | WebSocket | ws-rpc methods | repo + webui + api(ws-rpc) |
| ACPWG | acp-web-gateway | WebSocket, stdio-rpc | ws-rpc methods | repo + webui + api(ws-rpc) |
| ACPC | acp-components | stdio-rpc, in-process-sdk | sdk-hook only | repo + webui (no api) |
| ACPUI | acp-ui | stdio-rpc | component only | repo + webui (no api) |
| ASTUI | assistant-ui | in-process-sdk | sdk-hook / component | repo + webui (no api) |
| OCUI | opencode-chatui | REST+SSE | component only in caps; check data/full | repo + webui (api TBD by FEAT-005) |
| OGUI | OpenGUI | REST+SSE, in-process-sdk | sdk-hook / component; check data/full | repo + webui (api TBD by FEAT-005) |
| CKIT | CopilotKit | in-process-sdk | sdk-hook / protocol | repo + webui (no api) |
| ACHAT | agents-chat | stdio-rpc | sdk-hook / component | repo + webui (no api) |

## 7. Per-repo node mapping (all 11 current repo ids)

Each current `repo` id maps to a `repo` node plus a `webui` node, and an `api` node only
where a network surface exists (section 6). Paths follow section 3: concrete for CP/DH/HM
where scanned `src` / `caller_file` evidence exists; `.` fallback for the other 8.

| current repo id | repo node | webui node | api node(s) |
| --- | --- | --- | --- |
| CP | `CP` | `W:CP/<caller path>` | `A:CP/<src path>` style=rest |
| DH | `DH` | `W:DH/<caller path>` | `A:DH/<src path>` style=rpc |
| HM | `HM` | `W:HM/<caller path>` | `A:HM/<src path>` style=ws-rpc |
| ACPC | `ACPC` | `W:ACPC/.` | none (SDK-only) |
| ACPUI | `ACPUI` | `W:ACPUI/.` | none (component-only) |
| ASTUI | `ASTUI` | `W:ASTUI/.` | none (SDK-only) |
| OCUI | `OCUI` | `W:OCUI/.` | TBD by FEAT-005 |
| OGUI | `OGUI` | `W:OGUI/.` | TBD by FEAT-005 |
| CKIT | `CKIT` | `W:CKIT/.` | none (SDK / protocol only) |
| ACHAT | `ACHAT` | `W:ACHAT/.` | none (SDK-only) |
| ACPWG | `ACPWG` | `W:ACPWG/.` | `A:ACPWG/.` style=ws-rpc |

Notes:
- For CP/DH/HM the exact `<path>` per surface is chosen in FEAT-002/003 from the evidence
  sources in section 8. Where a single repo has many endpoint files, the api node path is
  the common backend source root (for example `src/app/api` for CP) unless the design in a
  later feature justifies finer-grained api nodes per group.
- ACPWG wraps ACP (stdio-rpc) behind a WebSocket gateway, so it earns a network `api` node
  even though its underlying protocol is stdio-rpc.

## 8. Known evidence sources for path derivation

Because the source repos are absent, all paths are derived from already-materialized
artifacts. These are authoritative migration input and must not be deleted or re-scanned.

- API (backend) paths for CP/DH/HM: `data/full/endpoints_<repo>.json`, field `src`
  (repo-relative source file of each endpoint, e.g.
  `CodePilot/src/app/api/app/updates/route.ts`).
- WEBUI (frontend) paths for CP/DH/HM: `data/frontend_calls/<repo>.json` and
  `data/full/calls_<repo>.json`, field `caller_file` (the frontend/source file that issues
  the call, e.g. `CodePilot/src/components/bridge/BridgeSection.tsx`).
- The other 8 repos have only per-repo surface evidence in `map_capabilities.py`
  (`surface_kind` + `surface_name`) and no source tree. Their `webui` path is therefore `.`
  and they receive an `api` node ONLY where `surface_kind` is a network kind
  (`endpoint` / `rpc` / `ws-rpc`). Under the current evidence that is ACPWG (ws-rpc);
  FEAT-005 confirms the rest.

Path normalization guidance for later features: the `src` / `caller_file` values are
prefixed with the source repo folder name (e.g. `CodePilot/...`, `DeepSeekHarness/...`).
Strip that leading source-folder segment so the stored `path` is repo-relative
(e.g. `src/app/api/...`), keeping ids stable regardless of where the repo is cloned.

## 9. Downstream artifacts to update (later features, for reference)

Schemas (`schemas/*.schema.yaml`): add `webui.schema.yaml` and `api.schema.yaml`; trim
`repo.schema.yaml` to git-identity-only. Data YAML under `data/` (repos + operations +
capabilities + protocols/features references). `validate.py` fail-closed gate (schema +
referential + semantic layers for the new node/edge types and id patterns). All four graph
builders (`build_from_yaml.py`, `build_api_graph.py` / `build_graph.py`,
`build_full_graph.py`, `build_unified_graph.py`) so chat_ui / api / full_api / unified stay
consistent, and the regenerated exports (`*_graph.{json,graphml,dot}`) plus metrics md
files. Docs: `README.md`, `DATA-PROVENANCE.md`, `EXTRACTION-METHOD.md`. This design file
governs all of them.
