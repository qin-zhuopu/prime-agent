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
    "CP": {"label": "CodePilot", "stack": "Electron+Next.js", "license": "BUSL-1.1"},
    "DH": {"label": "deepseek-harness", "stack": "Cordis+React", "license": "open"},
    "HM": {"label": "hermes-agent", "stack": "Vite+React+xterm", "license": "open"},
}

PROTOCOLS = {
    "SSE": "Server-Sent Events",
    "WS-JSONRPC": "WebSocket JSON-RPC (tui_gateway)",
    "structured-render": "Structured React components",
    "node-render": "Node-ized registrable components",
    "pty-terminal": "PTY -> xterm terminal mirror",
}

REPO_PROTOCOL = [
    ("CP", "SSE"), ("CP", "structured-render"),
    ("DH", "SSE"), ("DH", "node-render"), ("DH", "structured-render"),
    ("HM", "WS-JSONRPC"), ("HM", "pty-terminal"),
]

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
                g.add_edge(rid, fid, etype="implements", kind=KIND_MAP[k])
    return g


def analyze(g: nx.DiGraph) -> str:
    features = [n for n, d in g.nodes(data=True) if d["ntype"] == "feature"]
    lines: list[str] = []
    lines.append("# Chat/Agent UI Knowledge Graph — Metrics\n")
    lines.append(f"- Nodes: {g.number_of_nodes()}  (repos={len(REPOS)}, protocols={len(PROTOCOLS)}, categories={len(CATEGORIES)}, features={len(features)})")
    lines.append(f"- Edges: {g.number_of_edges()}\n")

    # coverage per repo
    lines.append("## Per-repo feature coverage\n")
    lines.append("| repo | structured | terminal | total impl | absent |")
    lines.append("|---|---|---|---|---|")
    for rid in REPOS:
        impl = [(v, g.edges[rid, v]["kind"]) for v in g.successors(rid)
                if g.nodes[v]["ntype"] == "feature"]
        s = sum(1 for _, k in impl if k == "structured")
        t = sum(1 for _, k in impl if k == "terminal")
        absent = len(features) - len(impl)
        lines.append(f"| {REPOS[rid]['label']} | {s} | {t} | {len(impl)} | {absent} |")
    lines.append("")

    # universal features (implemented, any kind, by all 3)
    universal, dh_only, cp_only, hm_only, structured_all = [], [], [], [], []
    for f in features:
        impls = {r: g.edges[r, f]["kind"] for r in REPOS if g.has_edge(r, f)}
        present = set(impls)
        if present == {"CP", "DH", "HM"}:
            universal.append(f)
            if all(v == "structured" for v in impls.values()):
                structured_all.append(f)
        if present == {"DH"}:
            dh_only.append(f)
        if present == {"CP"}:
            cp_only.append(f)
        if present == {"HM"}:
            hm_only.append(f)

    def names(fs):
        return ", ".join(sorted(g.nodes[x]["label"] for x in fs)) or "(none)"

    lines.append("## Cross-repo signals\n")
    lines.append(f"- Universal (all 3 implement, any form): {len(universal)}")
    lines.append(f"  - Structured in all 3 (safest to build first): {names(structured_all)}")
    lines.append(f"- DH-only (unique to deepseek-harness): {names(dh_only)}")
    lines.append(f"- CP-only (unique to CodePilot): {names(cp_only)}")
    lines.append(f"- HM-only (unique to hermes-agent): {names(hm_only)}")
    lines.append("")

    # degree centrality on features (how many repos implement -> maturity signal)
    lines.append("## Feature maturity (by #repos implementing)\n")
    counts: dict[int, list[str]] = {3: [], 2: [], 1: []}
    for f in features:
        c = sum(1 for r in REPOS if g.has_edge(r, f))
        counts.setdefault(c, []).append(g.nodes[f]["label"])
    for c in (3, 2, 1):
        lines.append(f"- {c} repo(s): {len(counts[c])} features")
    lines.append("")
    lines.append("Interpretation: 3-repo features are proven table-stakes; 1-repo features are differentiators to adopt selectively.")
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
