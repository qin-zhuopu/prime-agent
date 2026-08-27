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

Post-migration actuals (after the repo/webui/api split and the unified-consistency fix
that merges the canonical api layer, so all four `api` nodes and the `webui --calls--> api`
edges reach the unified graph):

| Command | Result (verbatim) |
| --- | --- |
| `python3 validate.py` | `OK: 199 YAML nodes valid (schema + referential + semantic).` |
| `python3 build_from_yaml.py` | `UI graph: 112 nodes/430 edges; API graph: 125 nodes/221 edges` |
| `python3 build_full_graph.py` | `Full API graph: 905 nodes, 1390 edges` |
| `python3 build_unified_graph.py` | `Unified graph: 1151 nodes, 2192 edges` |

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

### SDK repo audit (confirmed, FEAT-002)

This audit decides, per repo, whether it warrants a `webui` node and/or a network `api`
node. It does NOT presume "SDK => no api"; every repo is decided from its own evidence.

Method and its limitation (stated up front so this is not mistaken for a full source
audit): the 11 source repos are NOT present in this sandbox and their source trees cannot
be read or re-scanned. The conclusions below are therefore derived from the ALREADY
MATERIALIZED surface evidence, not from a fresh source-tree read. The evidence used is:

1. `map_capabilities.py` dict `M` - the `surface_kind` values each repo actually uses
   across the 22 user capabilities. This is the primary discriminator. Classification rule
   (from section 6): `surface_kind` in `{endpoint, rpc, ws-rpc}` is a NETWORK surface, so
   the repo earns an `api` node; `surface_kind` in `{sdk-hook, component, protocol}` is
   in-process / rendering only and backs NO `api` node.
2. `data/repos/<repo>.yaml` `integration` (`REST+SSE` / `WebSocket` / `stdio-rpc` /
   `in-process-sdk`), `transport`, `protocols`, and `browser_native`.
3. `data/full/endpoints_<repo>.json` (only CP / DH / HM have materialized endpoints).
4. `README.md` and existing docs (`DATA-PROVENANCE.md`, `EXTRACTION-METHOD.md`) notes.

The `surface_kind` sets below are computed directly from `map_capabilities.py` `M`:

- CP: `{endpoint, component}`; DH: `{rpc, component}`; HM: `{ws-rpc, sdk-hook, component}`
- ACPWG: `{ws-rpc, component}`
- ACPC: `{sdk-hook}`; ACPUI: `{component}`; ASTUI: `{sdk-hook, component}`;
  OCUI: `{component}`; OGUI: `{sdk-hook, component}`; CKIT: `{protocol, sdk-hook}`;
  ACHAT: `{sdk-hook, component}`

Every one of the 11 is a browser-facing chat / agent UI (each `data/repos/*.yaml` carries
a frontend `stack` and every repo implements user-facing capabilities through
components/hooks), so web-ui is `yes` for all 11. A network `api` node is earned by exactly
the four repos whose evidence shows a network `surface_kind`: CP, DH, HM, ACPWG.

| repo | web ui? (yes/no + evidence) | network api? (yes/no + style + evidence) | notes |
| --- | --- | --- | --- |
| CP | yes - `stack: Electron+Next.js`, `browser_native: true` (repos/CP.yaml); implements 22 capabilities via components (map_capabilities `M`) | yes, style=rest - `surface_kind=endpoint` across many caps (e.g. `POST /chat/sessions`) in `M`; `integration: REST+SSE` (repos/CP.yaml); materialized `data/full/endpoints_CP.json` | Full REST backend; api path derivable from `endpoints_CP.json` `src`. Evidence is materialized surface data, not a fresh source read. |
| DH | yes - `stack: Cordis+React`, `browser_native: true` (repos/DH.yaml); component surfaces in `M` | yes, style=rpc - `surface_kind=rpc` across caps (e.g. `session.prompt`) in `M`; `integration: REST+SSE` (repos/DH.yaml); `data/full/endpoints_DH.json` | RPC-style methods over HTTP. Materialized surface data only. |
| HM | yes - `stack: Vite+React+xterm`, `browser_native: true` (repos/HM.yaml); component/sdk-hook surfaces in `M` | yes, style=ws-rpc - `surface_kind=ws-rpc` across caps (e.g. `prompt.submit`) in `M`; `integration: WebSocket`, `protocols: [WS-JSONRPC]` (repos/HM.yaml); `data/full/endpoints_HM.json` | WebSocket JSON-RPC backend. Materialized surface data only. |
| ACPWG | yes - `stack: Kotlin server + web` (repos/ACPWG.yaml); `StatusBar` component surface in `M` | yes, style=ws-rpc - `surface_kind=ws-rpc` across caps (e.g. `session.new`, `session.prompt`) in `M`; `integration: [WebSocket, stdio-rpc]`, `transport: WebSocket` (repos/ACPWG.yaml) | Wraps upstream ACP (stdio-rpc) behind a WebSocket gateway, so it DOES expose a network api even though the underlying ACP protocol is stdio. This is the key "SDK != no api" case. Materialized surface data only. |
| ACPC | yes - `stack: React (core+react pkgs)` (repos/ACPC.yaml); sdk-hook surfaces (e.g. `useSession`, `useToolCalls`) in `M` | no - only `surface_kind=sdk-hook` in `M`; `integration: [stdio-rpc, in-process-sdk]`, `browser_native: false` (repos/ACPC.yaml) | React component/hook workbench library; ACP is spoken by the host over stdio, not exposed as a network endpoint by this repo. Materialized surface data only; no source tree read. |
| ACPUI | yes - `stack: Vue3+Tauri` (repos/ACPUI.yaml); component surfaces (e.g. `SessionList`, `ChatView`) in `M` | no - only `surface_kind=component` in `M`; `integration: stdio-rpc`, `browser_native: false` (repos/ACPUI.yaml) | Tauri desktop UI talking ACP over stdio; no network api exposed by this repo. Materialized surface data only. |
| ASTUI | yes - `stack: React (TS lib)`, `browser_native: true` (repos/ASTUI.yaml); sdk-hook + component surfaces (e.g. `useThreadRuntime`, `Reasoning`) in `M` | no - only `surface_kind` in `{sdk-hook, component}` in `M`; `integration: in-process-sdk` (repos/ASTUI.yaml) | React chat UI library consumed in-process; no network surface. Materialized surface data only. |
| OCUI | yes - `stack: React+Vite+tRPC`, `browser_native: true` (repos/OCUI.yaml); component surfaces (e.g. `MessageDisplay`, `DiffViewer`) in `M` | no - only `surface_kind=component` in `M`; no materialized endpoints (`data/full/endpoints_OCUI.json` absent) | `integration: REST+SSE` in repos/OCUI.yaml describes the client transport it consumes, but this repo contributes only component surfaces in the materialized evidence, so no api node from this repo. Materialized surface data only; if a future source scan reveals its own backend, an api node can be added. |
| OGUI | yes - `stack: React+Vite+Electron`, `browser_native: true` (repos/OGUI.yaml); sdk-hook + component surfaces (e.g. `use-agent-state`, `diff-view`) in `M` | no - `surface_kind` in `{sdk-hook, component}` only in `M`; no materialized endpoints (`data/full/endpoints_OGUI.json` absent) | `integration: [REST+SSE, in-process-sdk]` describes consumed transport; no network surface contributed by this repo in the evidence. Materialized surface data only; api node addable later if a source scan shows one. |
| CKIT | yes - `stack: React+Next.js`, `browser_native: true` (repos/CKIT.yaml); sdk-hook surfaces (e.g. `use-agent`, `use-mcp`) in `M` | no - `surface_kind` in `{sdk-hook, protocol}` only in `M`; `integration: in-process-sdk`, `protocols: [AG-UI]` (repos/CKIT.yaml) | AG-UI is a PROTOCOL the host implements, not an endpoint this repo exposes; `stream-response` uses `surface_kind=protocol` (`AG-UI events`), which is in-process, not a network api. Materialized surface data only. |
| ACHAT | yes - `stack: Next.js+React` (repos/ACHAT.yaml); sdk-hook + component surfaces (e.g. `useChatRuntime`, `PermissionPrompt`) in `M` | no - `surface_kind` in `{sdk-hook, component}` only in `M`; `integration: stdio-rpc`, `browser_native: false` (repos/ACHAT.yaml) | Speaks ACP over stdio via SDK hooks; no network api exposed by this repo. Materialized surface data only. |

### Resulting node inventory (for FEAT-003 to implement)

From the audit, every repo yields a `webui` node; exactly CP, DH, HM, ACPWG additionally
yield an `api` node with the style shown. No other repo yields an `api` node under the
current materialized evidence.

| current repo id | repo node | webui node | api node(s) |
| --- | --- | --- | --- |
| CP | `CP` | `W:CP/<caller path>` | `A:CP/<src path>` style=rest |
| DH | `DH` | `W:DH/<caller path>` | `A:DH/<src path>` style=rpc |
| HM | `HM` | `W:HM/<caller path>` | `A:HM/<src path>` style=ws-rpc |
| ACPWG | `ACPWG` | `W:ACPWG/.` | `A:ACPWG/.` style=ws-rpc |
| ACPC | `ACPC` | `W:ACPC/.` | none (sdk-hook only) |
| ACPUI | `ACPUI` | `W:ACPUI/.` | none (component only) |
| ASTUI | `ASTUI` | `W:ASTUI/.` | none (sdk-hook / component) |
| OCUI | `OCUI` | `W:OCUI/.` | none (component only) |
| OGUI | `OGUI` | `W:OGUI/.` | none (sdk-hook / component) |
| CKIT | `CKIT` | `W:CKIT/.` | none (sdk-hook / protocol) |
| ACHAT | `ACHAT` | `W:ACHAT/.` | none (sdk-hook / component) |

Net: 11 `webui` nodes + 4 `api` nodes (CP rest, DH rpc, HM ws-rpc, ACPWG ws-rpc). The
CP/DH/HM concrete paths come from the section 8 evidence sources; the other eight repos
use the section 3.1 `.` fallback because their source trees are absent.

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
| OCUI | `OCUI` | `W:OCUI/.` | none (component-only, confirmed FEAT-002 audit) |
| OGUI | `OGUI` | `W:OGUI/.` | none (sdk-hook/component-only, confirmed FEAT-002 audit) |
| CKIT | `CKIT` | `W:CKIT/.` | none (SDK / protocol only) |
| ACHAT | `ACHAT` | `W:ACHAT/.` | none (SDK-only) |
| ACPWG | `ACPWG` | `W:ACPWG/.` | `A:ACPWG/.` style=ws-rpc |

Notes:
- For CP/DH/HM the exact `<path>` per surface is chosen in FEAT-003 from the evidence
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
  (`endpoint` / `rpc` / `ws-rpc`). Under the current evidence that is ACPWG (ws-rpc); the
  FEAT-002 audit in section 6 confirms the other seven earn no api node.

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
