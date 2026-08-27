#!/usr/bin/env python3
"""Build a knowledge graph of chat/agent UI features across three reference repos.

Data source: docs/chat-ui-features.md (CP = CodePilot, DH = deepseek-harness, HM = hermes-agent).

Node types:
  - repo       : the three reference implementations
  - protocol   : transport / rendering paradigm
  - category   : the 10 feature groups (P0..P4)
  - feature    : an individual capability

Edges:
  - repo    --uses-->      protocol
  - category --contains--> feature
  - repo    --implements--> feature   (data.kind: structured | terminal | none)

Outputs (written next to this script):
  - chat_ui_graph.graphml   (open in Gephi / yEd / Cytoscape)
  - chat_ui_graph.json      (node-link JSON for D3 / web)
  - chat_ui_graph.dot       (Graphviz)
  - metrics.md              (centrality + coverage analysis)
"""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

HERE = Path(__file__).parent

# --- repos + protocols -------------------------------------------------------
REPOS = {
    # --- primary set: verified by reading the source ---
    "CP": {"label": "CodePilot", "stack": "Electron+Next.js", "license": "BUSL-1.1"},
    "DH": {"label": "deepseek-harness", "stack": "Cordis+React", "license": "open"},
    "HM": {"label": "hermes-agent", "stack": "Vite+React+xterm", "license": "open"},
    # --- survey set: capabilities from README/structure scan (source=declared) ---
    "ACPC": {"label": "acp-components", "stack": "React (core+react pkgs)", "license": "open"},
    "ACPUI": {"label": "acp-ui", "stack": "Vue3+Tauri", "license": "open"},
    "ASTUI": {"label": "assistant-ui", "stack": "React (TS lib)", "license": "open"},
    "OCUI": {"label": "opencode-chatui", "stack": "React+Vite+tRPC", "license": "open"},
    "OGUI": {"label": "OpenGUI", "stack": "React+Vite+Electron", "license": "open"},
    "CKIT": {"label": "CopilotKit", "stack": "React+Next.js", "license": "open"},
    "ACHAT": {"label": "agents-chat", "stack": "Next.js+React", "license": "open"},
    "ACPWG": {"label": "acp-web-gateway", "stack": "Kotlin server + web", "license": "open"},
}

PROTOCOLS = {
    "SSE": "Server-Sent Events",
    "WS-JSONRPC": "WebSocket JSON-RPC (tui_gateway)",
    "ACP": "Agent Client Protocol (JSON-RPC/stdio)",
    "AG-UI": "AG-UI agent<->frontend event protocol",
    "structured-render": "Structured React components",
    "node-render": "Node-ized registrable components",
    "pty-terminal": "PTY -> xterm terminal mirror",
}

REPO_PROTOCOL = [
    ("CP", "SSE"), ("CP", "structured-render"),
    ("DH", "SSE"), ("DH", "node-render"), ("DH", "structured-render"),
    ("HM", "WS-JSONRPC"), ("HM", "pty-terminal"),
    # survey set
    ("ACPC", "ACP"), ("ACPC", "structured-render"),
    ("ACPUI", "ACP"), ("ACPUI", "structured-render"),
    ("ASTUI", "structured-render"),
    ("OCUI", "structured-render"),
    ("OGUI", "structured-render"),
    ("CKIT", "AG-UI"), ("CKIT", "structured-render"),
    ("ACHAT", "ACP"), ("ACHAT", "structured-render"),
    ("ACPWG", "ACP"),
]

# Survey repos: coarse capability tags from README + structure scan (source="declared").
# Only capabilities we could confirm from the repo (deps, dir/component/hook names, README claims).
# feature ids must match "{category}:{name}" used in FEATURES below.
SURVEY_IMPLEMENTS: dict[str, list[str]] = {
    # acp-components: full ACP workbench; react pkg exposes hooks for prompt/permission/toolcalls/skills/session/filetree
    "ACPC": [
        "messaging:conversation-view", "messaging:message-list", "messaging:streaming-typing",
        "messaging:assistant-markdown", "messaging:message-actions",
        "reasoning:reasoning-display",
        "tool-use:tool-card", "tool-use:tool-call-tree", "tool-use:diff-view",
        "tool-use:file-read-view", "tool-use:search-sources",
        "permission:permission-panel", "permission:permission-mode",
        "composer:message-input", "composer:submission-policy",
        "stream-control:stream-subscribe", "stream-control:session-connect",
        "stream-control:stop-interrupt", "stream-control:reconnect-resume",
        "multi-agent:plan-mode", "multi-agent:subagent-card",
        "model-config:model-picker", "model-config:skills", "model-config:context-usage",
        "aux:sidebar-session-list", "aux:details-panel", "aux:theme", "aux:i18n",
        "aux:primitives", "aux:plugin-registry", "aux:empty-welcome",
    ],
    # acp-ui: cross-platform ACP client; chat/sessions/permissions/traffic-monitor
    "ACPUI": [
        "messaging:conversation-view", "messaging:message-list", "messaging:streaming-typing",
        "messaging:assistant-markdown", "messaging:code-highlight",
        "tool-use:tool-card", "tool-use:diff-view",
        "permission:permission-panel", "permission:permission-mode",
        "composer:message-input", "composer:attachments",
        "stream-control:stream-subscribe", "stream-control:session-connect", "stream-control:stop-interrupt",
        "model-config:model-picker",
        "aux:sidebar-session-list", "aux:theme", "aux:empty-welcome", "aux:primitives",
    ],
    # assistant-ui: production React chat lib; streaming, tool calls, markdown, attachments, branching
    "ASTUI": [
        "messaging:conversation-view", "messaging:message-list", "messaging:streaming-typing",
        "messaging:assistant-markdown", "messaging:code-highlight",
        "messaging:message-actions", "messaging:message-branching",
        "reasoning:reasoning-display",
        "tool-use:tool-card",
        "composer:message-input", "composer:submission-policy", "composer:attachments",
        "stream-control:stream-subscribe", "stream-control:stop-interrupt",
        "aux:primitives", "aux:theme", "aux:empty-welcome",
    ],
    # opencode-chatui: rich rendering of tool calls, file diffs, search results
    "OCUI": [
        "messaging:conversation-view", "messaging:message-list", "messaging:streaming-typing",
        "messaging:assistant-markdown", "messaging:code-highlight",
        "tool-use:tool-card", "tool-use:diff-view", "tool-use:file-read-view", "tool-use:search-sources",
        "composer:message-input",
        "stream-control:stream-subscribe", "stream-control:session-connect",
        "model-config:model-picker",
        "aux:sidebar-session-list", "aux:theme", "aux:primitives",
    ],
    # OpenGUI: host+harness, durable sessions, model connections, streaming chat, workspace tools
    "OGUI": [
        "messaging:conversation-view", "messaging:message-list", "messaging:streaming-typing",
        "messaging:assistant-markdown", "messaging:code-highlight",
        "tool-use:tool-card", "tool-use:diff-view",
        "composer:message-input", "composer:dir-picker",
        "stream-control:stream-subscribe", "stream-control:session-connect",
        "stream-control:stop-interrupt", "stream-control:reconnect-resume",
        "model-config:model-picker", "model-config:runtime-switch",
        "aux:sidebar-session-list", "aux:theme", "aux:primitives",
    ],
    # CopilotKit: generative UI stack, AG-UI author; streaming, generative UI, MCP
    "CKIT": [
        "messaging:conversation-view", "messaging:message-list", "messaging:streaming-typing",
        "messaging:assistant-markdown",
        "tool-use:tool-card",
        "composer:message-input",
        "stream-control:stream-subscribe",
        "model-config:mcp-config",
        "aux:primitives", "aux:theme",
    ],
    # agents-chat: multi-agent ACP chat UI
    "ACHAT": [
        "messaging:conversation-view", "messaging:message-list", "messaging:streaming-typing",
        "messaging:assistant-markdown",
        "tool-use:tool-card",
        "permission:permission-panel",
        "composer:message-input", "composer:slash-commands",
        "stream-control:stream-subscribe", "stream-control:session-connect", "stream-control:stop-interrupt",
        "multi-agent:subagent-card",
        "aux:sidebar-session-list", "aux:theme",
    ],
    # acp-web-gateway: web interface to ACP agents (Kotlin server + web front)
    "ACPWG": [
        "messaging:conversation-view", "messaging:message-list", "messaging:streaming-typing",
        "messaging:assistant-markdown",
        "tool-use:tool-card",
        "permission:permission-panel",
        "composer:message-input",
        "stream-control:stream-subscribe", "stream-control:session-connect",
        "aux:sidebar-session-list",
    ],
}

# --- feature matrix ----------------------------------------------------------
# category -> priority -> [ (feature, {repo: kind}) ]
# kind: "structured" (real component), "terminal" (PTY semantics), "none" (absent)
CATEGORIES = {
    "messaging": ("P0", "Messaging & streaming render"),
    "reasoning": ("P1", "Thinking / reasoning display"),
    "tool-use": ("P1", "Tool call display"),
    "permission": ("P1", "Permission / human-in-loop"),
    "composer": ("P0", "Input composer"),
    "stream-control": ("P2", "Stream control & run state"),
    "multi-agent": ("P3", "Task / subagent / plan"),
    "model-config": ("P3", "Model / runtime / context config"),
    "media": ("P4", "Media / deliverables"),
    "aux": ("P0", "Layout / robustness / aux"),
}

# S=structured, T=terminal, N=none
FEATURES = {
    "messaging": [
        ("conversation-view", {"CP": "S", "DH": "S", "HM": "S"}),
        ("message-list", {"CP": "S", "DH": "S", "HM": "T"}),
        ("virtual-scroll", {"CP": "S", "DH": "S", "HM": "N"}),
        ("streaming-typing", {"CP": "S", "DH": "S", "HM": "T"}),
        ("assistant-markdown", {"CP": "S", "DH": "S", "HM": "S"}),
        ("code-highlight", {"CP": "S", "DH": "S", "HM": "T"}),
        ("math-katex", {"CP": "S", "DH": "S", "HM": "N"}),
        ("message-actions", {"CP": "S", "DH": "S", "HM": "S"}),
        ("message-branching", {"CP": "S", "DH": "S", "HM": "N"}),
    ],
    "reasoning": [
        ("reasoning-display", {"CP": "S", "DH": "S", "HM": "T"}),
        ("chain-of-thought", {"CP": "S", "DH": "S", "HM": "T"}),
        ("thinking-anim", {"CP": "S", "DH": "S", "HM": "S"}),
        ("effort-setting", {"CP": "S", "DH": "S", "HM": "S"}),
    ],
    "tool-use": [
        ("tool-card", {"CP": "S", "DH": "S", "HM": "T"}),
        ("tool-call-tree", {"CP": "N", "DH": "S", "HM": "T"}),
        ("terminal-output", {"CP": "S", "DH": "S", "HM": "S"}),
        ("diff-view", {"CP": "S", "DH": "S", "HM": "T"}),
        ("file-read-view", {"CP": "S", "DH": "S", "HM": "S"}),
        ("search-sources", {"CP": "S", "DH": "S", "HM": "T"}),
        ("web-card", {"CP": "S", "DH": "S", "HM": "T"}),
        ("risk-confirm", {"CP": "S", "DH": "S", "HM": "S"}),
    ],
    "permission": [
        ("permission-panel", {"CP": "S", "DH": "S", "HM": "T"}),
        ("permission-mode", {"CP": "S", "DH": "S", "HM": "T"}),
        ("permission-presets", {"CP": "N", "DH": "S", "HM": "S"}),
        ("auto-review-notice", {"CP": "S", "DH": "S", "HM": "T"}),
    ],
    "composer": [
        ("message-input", {"CP": "S", "DH": "S", "HM": "S"}),
        ("submission-policy", {"CP": "S", "DH": "S", "HM": "S"}),
        ("slash-commands", {"CP": "S", "DH": "S", "HM": "S"}),
        ("mentions", {"CP": "S", "DH": "S", "HM": "N"}),
        ("attachments", {"CP": "S", "DH": "S", "HM": "S"}),
        ("dir-picker", {"CP": "S", "DH": "S", "HM": "S"}),
    ],
    "stream-control": [
        ("stream-subscribe", {"CP": "S", "DH": "S", "HM": "S"}),
        ("session-connect", {"CP": "S", "DH": "S", "HM": "S"}),
        ("stop-interrupt", {"CP": "S", "DH": "S", "HM": "S"}),
        ("message-queue", {"CP": "S", "DH": "S", "HM": "N"}),
        ("rewind-retry", {"CP": "S", "DH": "S", "HM": "S"}),
        ("reconnect-resume", {"CP": "S", "DH": "S", "HM": "S"}),
        ("run-status", {"CP": "S", "DH": "S", "HM": "S"}),
        ("terminal-reason", {"CP": "S", "DH": "S", "HM": "T"}),
    ],
    "multi-agent": [
        ("todo-list", {"CP": "S", "DH": "S", "HM": "T"}),
        ("subagent-card", {"CP": "S", "DH": "S", "HM": "T"}),
        ("plan-mode", {"CP": "N", "DH": "S", "HM": "T"}),
        ("plan-review", {"CP": "N", "DH": "S", "HM": "T"}),
        ("agent-asks-user", {"CP": "N", "DH": "S", "HM": "T"}),
        ("goal", {"CP": "N", "DH": "S", "HM": "N"}),
        ("background-jobs", {"CP": "S", "DH": "S", "HM": "S"}),
        ("workflow-run", {"CP": "N", "DH": "S", "HM": "S"}),
        ("trajectory-replay", {"CP": "N", "DH": "S", "HM": "S"}),
    ],
    "model-config": [
        ("model-picker", {"CP": "S", "DH": "S", "HM": "S"}),
        ("runtime-switch", {"CP": "S", "DH": "S", "HM": "S"}),
        ("context-usage", {"CP": "S", "DH": "S", "HM": "S"}),
        ("context-injection", {"CP": "S", "DH": "S", "HM": "N"}),
        ("compaction-view", {"CP": "S", "DH": "S", "HM": "T"}),
        ("rate-limit-banner", {"CP": "S", "DH": "N", "HM": "N"}),
        ("agent-preset", {"CP": "N", "DH": "S", "HM": "S"}),
        ("skills", {"CP": "S", "DH": "S", "HM": "S"}),
        ("mcp-config", {"CP": "S", "DH": "S", "HM": "S"}),
    ],
    "media": [
        ("image-thumb-lightbox", {"CP": "S", "DH": "S", "HM": "N"}),
        ("image-gen", {"CP": "S", "DH": "N", "HM": "N"}),
        ("media-preview", {"CP": "S", "DH": "S", "HM": "S"}),
        ("batch-image-gen", {"CP": "S", "DH": "S", "HM": "N"}),
        ("deliverables", {"CP": "N", "DH": "S", "HM": "S"}),
    ],
    "aux": [
        ("empty-welcome", {"CP": "S", "DH": "S", "HM": "S"}),
        ("sidebar-session-list", {"CP": "S", "DH": "S", "HM": "S"}),
        ("details-panel", {"CP": "S", "DH": "S", "HM": "S"}),
        ("error-boundary", {"CP": "S", "DH": "S", "HM": "S"}),
        ("message-feedback", {"CP": "N", "DH": "S", "HM": "N"}),
        ("theme", {"CP": "S", "DH": "S", "HM": "S"}),
        ("toast-modal", {"CP": "S", "DH": "S", "HM": "S"}),
        ("primitives", {"CP": "S", "DH": "S", "HM": "S"}),
        ("i18n", {"CP": "S", "DH": "S", "HM": "S"}),
        ("auth-pairing", {"CP": "N", "DH": "S", "HM": "S"}),
        ("plugin-registry", {"CP": "N", "DH": "S", "HM": "S"}),
    ],
}

KIND_MAP = {"S": "structured", "T": "terminal", "N": "none"}


def build_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    for rid, meta in REPOS.items():
        g.add_node(rid, ntype="repo", label=meta["label"], stack=meta["stack"], license=meta["license"])
    for pid, desc in PROTOCOLS.items():
        g.add_node(pid, ntype="protocol", label=desc)
    for r, p in REPO_PROTOCOL:
        g.add_edge(r, p, etype="uses")

    for cid, (prio, clabel) in CATEGORIES.items():
        g.add_node(cid, ntype="category", label=clabel, priority=prio)

    for cid, feats in FEATURES.items():
        for fname, repo_kinds in feats:
            fid = f"{cid}:{fname}"
            g.add_node(fid, ntype="feature", label=fname, category=cid, priority=CATEGORIES[cid][0])
            g.add_edge(cid, fid, etype="contains")
            for rid, k in repo_kinds.items():
                if k == "N":
                    continue  # absent: no implements edge
                # primary repos: verified from source
                g.add_edge(rid, fid, etype="implements", kind=KIND_MAP[k], source="verified")

    # survey repos: declared capabilities (coarse, from README + structure scan)
    known_features = {f"{cid}:{name}" for cid, feats in FEATURES.items() for name, _ in feats}
    for rid, fids in SURVEY_IMPLEMENTS.items():
        for fid in fids:
            if fid not in known_features:
                raise ValueError(f"survey feature id not in matrix: {fid}")
            g.add_edge(rid, fid, etype="implements", kind="structured", source="declared")
    return g


def analyze(g: nx.DiGraph) -> str:
    import derive_tier
    features = [n for n, d in g.nodes(data=True) if d["ntype"] == "feature"]
    tiers = derive_tier.classify()
    # 'deep' cluster emerges from feature-coverage (no manual label). This replaces
    # the former hand-assigned primary/survey. Cross-repo conclusions still focus on
    # the deep cluster because it is the source-verified, high-coverage set.
    primary = [r for r in tiers["deep"] if r in REPOS]
    survey = [r for r in tiers["broad"] if r in REPOS]
    lines: list[str] = []
    lines.append("# Chat/Agent UI Knowledge Graph -- Metrics\n")
    lines.append(f"- Nodes: {g.number_of_nodes()}  (repos={len(REPOS)}, protocols={len(PROTOCOLS)}, categories={len(CATEGORIES)}, features={len(features)})")
    lines.append(f"- Edges: {g.number_of_edges()}")
    lines.append(f"- Emergent tiers (by feature coverage, natural break gap={tiers['gap']}): "
                 f"{len(primary)} deep + {len(survey)} broad (NOT hand-assigned; see derive_tier.py)\n")

    def names(fs):
        return ", ".join(sorted(g.nodes[x]["label"] for x in fs)) or "(none)"

    # coverage per repo
    deep_set = set(primary)
    lines.append("## Per-repo feature coverage\n")
    lines.append("| repo | tier (emergent) | structured | terminal | total impl |")
    lines.append("|---|---|---|---|---|")
    for rid in REPOS:
        impl = [(v, g.edges[rid, v]) for v in g.successors(rid)
                if g.nodes[v]["ntype"] == "feature"]
        s = sum(1 for _, e in impl if e["kind"] == "structured")
        t = sum(1 for _, e in impl if e["kind"] == "terminal")
        tier = "deep" if rid in deep_set else "broad"
        lines.append(f"| {REPOS[rid]['label']} | {tier} | {s} | {t} | {len(impl)} |")
    lines.append("")

    # protocol adoption
    lines.append("## Protocol adoption (repos per protocol)\n")
    lines.append("| protocol | #repos | repos |")
    lines.append("|---|---|---|")
    for pid in PROTOCOLS:
        users = [REPOS[u]["label"] for u, _ in g.in_edges(pid) if g.nodes[u]["ntype"] == "repo"]
        if users:
            lines.append(f"| {pid} | {len(users)} | {', '.join(sorted(users))} |")
    lines.append("")

    # cross-repo signals -- PRIMARY set only (verified), to keep conclusions clean
    universal, dh_only, cp_only, hm_only, structured_all = [], [], [], [], []
    for f in features:
        impls = {r: g.edges[r, f]["kind"] for r in primary if g.has_edge(r, f)}
        present = set(impls)
        if present == set(primary):
            universal.append(f)
            if all(v == "structured" for v in impls.values()):
                structured_all.append(f)
        if present == {"DH"}:
            dh_only.append(f)
        if present == {"CP"}:
            cp_only.append(f)
        if present == {"HM"}:
            hm_only.append(f)

    lines.append("## Cross-repo signals (primary 3, source-verified)\n")
    lines.append(f"- Universal (all 3 implement, any form): {len(universal)}")
    lines.append(f"  - Structured in all 3 (safest to build first): {names(structured_all)}")
    lines.append(f"- DH-only: {names(dh_only)}")
    lines.append(f"- CP-only: {names(cp_only)}")
    lines.append(f"- HM-only: {names(hm_only)}")
    lines.append("")

    # feature maturity across ALL repos (primary + survey) -> demand signal
    lines.append("## Feature maturity across ALL repos (primary + survey)\n")
    ranked = sorted(
        features,
        key=lambda f: sum(1 for r in REPOS if g.has_edge(r, f)),
        reverse=True,
    )
    lines.append("Top features by #repos implementing (demand / table-stakes signal):\n")
    lines.append("| feature | category | #repos |")
    lines.append("|---|---|---|")
    for f in ranked[:20]:
        c = sum(1 for r in REPOS if g.has_edge(r, f))
        lines.append(f"| {g.nodes[f]['label']} | {g.nodes[f]['category']} | {c} |")
    lines.append("")

    # features NOT implemented by any survey repo (either niche or hard)
    survey_covered = {f for f in features if any(g.has_edge(r, f) for r in survey)}
    survey_gap = [f for f in features if f not in survey_covered]
    lines.append("## Features absent from ALL survey repos\n")
    lines.append("(present only in the primary trio; either niche or high-effort differentiators)\n")
    lines.append(names(survey_gap))
    lines.append("")
    lines.append("Interpretation: features implemented by many repos are proven table-stakes; "
                 "features absent from the whole survey set are differentiators to adopt selectively. "
                 "Survey-repo edges are `source=declared` (README/structure scan), primary edges are `source=verified` (source read).")
    return "\n".join(lines) + "\n"


def main() -> None:
    g = build_graph()

    nx.write_graphml(g, HERE / "chat_ui_graph.graphml")

    data = nx.node_link_data(g)
    (HERE / "chat_ui_graph.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))

    try:
        nx.nx_pydot.write_dot(g, HERE / "chat_ui_graph.dot")
    except Exception:
        # pydot not installed; write a minimal DOT by hand
        with open(HERE / "chat_ui_graph.dot", "w") as fh:
            fh.write("digraph chat_ui {\n")
            for u, v, d in g.edges(data=True):
                fh.write(f'  "{u}" -> "{v}" [label="{d.get("etype","")}"];\n')
            fh.write("}\n")

    (HERE / "metrics.md").write_text(analyze(g))
    print("Wrote: chat_ui_graph.graphml, chat_ui_graph.json, chat_ui_graph.dot, metrics.md")
    print(f"Graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")


if __name__ == "__main__":
    main()
