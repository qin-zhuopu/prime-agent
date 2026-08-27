#!/usr/bin/env python3
"""Backend API knowledge graph: business entities and per-entity operations.

Adds two node types on top of the UI graph:
  - entity    : a backend business entity (Session, Message, Permission, Goal, ...)
  - operation : a canonical CRUD-ish operation on an entity (create/list/get/update/delete/... )

Edges:
  - entity --has_op-->      operation
  - repo   --exposes-->     operation   (endpoint attrs: repo, name, url_or_method, http, style)

Data source (raw dumps in _raw_api/, produced by scanning the three primary repos):
  - CP  : RESTful Next.js routes   -> style=REST,  name=URL path, http=GET/POST/...
  - DH  : RPC map "entity.action"  -> style=RPC,   name=rpc method
  - HM  : WS JSON-RPC "entity.action" -> style=WS-RPC, name=rpc method

The canonical mapping below is authored by reading the raw API dumps. Each entry ties a
canonical (entity, operation) to the concrete name each repo uses (or None if absent).
This is the layer you asked for: "granularity down to operations on an entity", plus
"what each entity is called in each repo and what URL/method the operation maps to".

Outputs (next to this script):
  - api_graph.graphml / api_graph.json / api_graph.dot
  - api_metrics.md   (entity coverage + per-repo naming table)
"""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

HERE = Path(__file__).parent

REPOS = {
    "CP": {"label": "CodePilot", "style": "REST"},
    "DH": {"label": "deepseek-harness", "style": "RPC"},
    "HM": {"label": "hermes-agent", "style": "WS-RPC"},
}

# Canonical operation vocabulary (the operation-node identities).
OPS = ["create", "list", "get", "update", "delete", "send", "interrupt",
       "stream", "fork", "rename", "search", "select", "respond",
       "pause", "resume", "complete", "clear", "history"]

# entity -> per-repo display name (what the entity is called in that repo's API).
ENTITY_NAMES: dict[str, dict[str, str | None]] = {
    "Session":    {"CP": "chat/sessions", "DH": "session", "HM": "session"},
    "Message":    {"CP": "chat/messages", "DH": "session.prompt", "HM": "prompt"},
    "Permission": {"CP": "chat/permission", "DH": "approvals", "HM": "approval"},
    "Model":      {"CP": "codex/models", "DH": "llm/session.models", "HM": "model"},
    "Subagent":   {"CP": "chat/sessions/[id]/subagent-runs", "DH": "subagent", "HM": "agents"},
    "Goal":       {"CP": None, "DH": "goal", "HM": "goal"},
    "Skill":      {"CP": None, "DH": "skill", "HM": "skills"},
    "AgentPreset":{"CP": None, "DH": "agentPreset", "HM": "profile"},
    "Workspace":  {"CP": "files/browse", "DH": "workspace", "HM": "workspace"},
    "File":       {"CP": "files", "DH": "host(fs)", "HM": "files"},
    "Attachment": {"CP": "assets", "DH": "session.attachment", "HM": "clipboard.paste"},
    "Settings":   {"CP": "settings", "DH": "settings", "HM": "config"},
    "Credential": {"CP": "claude-auth", "DH": "credentials", "HM": "auth"},
    "Job":        {"CP": "media/jobs", "DH": "jobs", "HM": "background"},
}

# (entity, operation) -> per-repo concrete endpoint name (URL / rpc method) or None if absent.
# http is only meaningful for REST (CP).
MAP: dict[tuple[str, str], dict[str, tuple[str | None, str | None]]] = {
    # entity op                repo: (name/url, http)
    ("Session", "create"):    {"CP": ("/chat/sessions", "POST"), "DH": ("session.create", None), "HM": ("session.create", None)},
    ("Session", "list"):      {"CP": ("/chat/sessions", "GET"),  "DH": ("session.list", None),   "HM": ("sessions.list", None)},
    ("Session", "get"):       {"CP": ("/chat/sessions/[id]", "GET"), "DH": ("session.history", None), "HM": ("session.info", None)},
    ("Session", "update"):    {"CP": ("/chat/sessions/[id]", "PATCH"), "DH": ("session.rename", None), "HM": ("session.rename", None)},
    ("Session", "delete"):    {"CP": ("/chat/sessions/[id]", "DELETE"), "DH": ("workspace.archiveSession", None), "HM": ("session.delete", None)},
    ("Session", "fork"):      {"CP": ("/chat/rewind", "POST"), "DH": ("session.fork", None), "HM": (None, None)},
    ("Session", "interrupt"): {"CP": ("/chat/interrupt", "POST"), "DH": ("session.cancel", None), "HM": ("session.interrupt", None)},
    ("Session", "search"):    {"CP": ("/chat/sessions/by-cwd", "GET"), "DH": ("session.search", None), "HM": (None, None)},

    ("Message", "send"):      {"CP": ("/chat/messages", "POST"), "DH": ("session.prompt", None), "HM": ("prompt.submit", None)},
    ("Message", "list"):      {"CP": ("/chat/sessions/[id]/messages", "GET"), "DH": ("session.history", None), "HM": (None, None)},
    ("Message", "update"):    {"CP": ("/chat/messages", "PUT"), "DH": ("session.updateQueue", None), "HM": (None, None)},
    ("Message", "stream"):    {"CP": ("/chat/structured", "POST"), "DH": ("session.prompt(stream)", None), "HM": ("message.delta", None)},

    ("Permission", "respond"):{"CP": ("/chat/permission", "POST"), "DH": ("approvals.respond", None), "HM": ("approval.respond", None)},
    ("Permission", "get"):    {"CP": ("/chat/permission-capability", "GET"), "DH": ("approvals.describe", None), "HM": ("approval.pending", None)},

    ("Model", "list"):        {"CP": ("/codex/models", "GET"), "DH": ("llm.models", None), "HM": ("models.list", None)},
    ("Model", "select"):      {"CP": ("/chat/model", "POST"), "DH": ("session.selectModel", None), "HM": ("agent.reasoning_effort", None)},

    ("Subagent", "list"):     {"CP": ("/chat/sessions/[id]/subagent-runs", "GET"), "DH": ("subagent.list", None), "HM": ("agents.list", None)},
    ("Subagent", "send"):     {"CP": (None, None), "DH": ("subagent.prompt", None), "HM": (None, None)},
    ("Subagent", "interrupt"):{"CP": (None, None), "DH": ("subagent.interrupt", None), "HM": (None, None)},
    ("Subagent", "history"):  {"CP": (None, None), "DH": ("subagent.history", None), "HM": (None, None)},

    ("Goal", "create"):       {"CP": (None, None), "DH": ("goal.create", None), "HM": ("goal.set", None)},
    ("Goal", "update"):       {"CP": (None, None), "DH": ("goal.edit", None), "HM": (None, None)},
    ("Goal", "pause"):        {"CP": (None, None), "DH": ("goal.pause", None), "HM": (None, None)},
    ("Goal", "resume"):       {"CP": (None, None), "DH": ("goal.resume", None), "HM": (None, None)},
    ("Goal", "complete"):     {"CP": (None, None), "DH": ("goal.complete", None), "HM": (None, None)},
    ("Goal", "clear"):        {"CP": (None, None), "DH": ("goal.clear", None), "HM": ("goal.clear", None)},

    ("Skill", "list"):        {"CP": (None, None), "DH": ("skill.list", None), "HM": ("skills.list", None)},

    ("AgentPreset", "list"):  {"CP": (None, None), "DH": ("agentPreset.list", None), "HM": ("profiles.list", None)},
    ("AgentPreset", "get"):   {"CP": (None, None), "DH": ("agentPreset.read", None), "HM": (None, None)},
    ("AgentPreset", "select"):{"CP": (None, None), "DH": ("agentPreset.select", None), "HM": ("profile.select", None)},
    ("AgentPreset", "delete"):{"CP": (None, None), "DH": ("agentPreset.remove", None), "HM": (None, None)},

    ("Workspace", "create"):  {"CP": ("/files/mkdir", "POST"), "DH": ("workspace.create", None), "HM": (None, None)},
    ("Workspace", "list"):    {"CP": ("/files/browse", "GET"), "DH": ("host.listDirectory", None), "HM": ("complete.path", None)},
    ("Workspace", "delete"):  {"CP": ("/files/delete", "POST"), "DH": ("workspace.delete", None), "HM": (None, None)},

    ("File", "get"):          {"CP": ("/files/raw", "GET"), "DH": ("host.openPath", None), "HM": ("files.read", None)},
    ("File", "list"):         {"CP": ("/files/browse", "GET"), "DH": ("host.listDirectory", None), "HM": ("files.list", None)},
    ("File", "create"):       {"CP": ("/files/write", "POST"), "DH": (None, None), "HM": (None, None)},
    ("File", "update"):       {"CP": ("/files/rename", "POST"), "DH": (None, None), "HM": (None, None)},
    ("File", "delete"):       {"CP": ("/files/delete", "POST"), "DH": (None, None), "HM": (None, None)},

    ("Attachment", "create"): {"CP": ("/assets/html-bundles", "POST"), "DH": ("session.attachment", None), "HM": ("clipboard.paste", None)},
    ("Attachment", "get"):    {"CP": ("/assets/[id]", "GET"), "DH": (None, None), "HM": (None, None)},
    ("Attachment", "delete"): {"CP": ("/assets/[id]", "DELETE"), "DH": (None, None), "HM": (None, None)},

    ("Settings", "get"):      {"CP": ("/settings", "GET"), "DH": ("settings.describe", None), "HM": ("config.get", None)},
    ("Settings", "update"):   {"CP": ("/settings", "PUT"), "DH": ("settings.update", None), "HM": ("config.set", None)},

    ("Credential", "get"):    {"CP": ("/claude-auth", "GET"), "DH": ("credentials.describe", None), "HM": ("auth.json", None)},
    ("Credential", "update"): {"CP": ("/claude-auth", "POST"), "DH": ("credentials.set", None), "HM": (None, None)},
    ("Credential", "delete"): {"CP": (None, None), "DH": ("credentials.unset", None), "HM": (None, None)},

    ("Job", "list"):          {"CP": ("/media/jobs", "GET"), "DH": ("jobs.list", None), "HM": ("background.list", None)},
    ("Job", "create"):        {"CP": ("/media/jobs", "POST"), "DH": ("jobs.create", None), "HM": (None, None)},
}


# api-node style (lowercase) for each seed repo; the endpoint edge keeps the
# legacy uppercase `style` for metric rendering.
API_STYLE = {"CP": "rest", "DH": "rpc", "HM": "ws-rpc"}


def api_node_id(rid: str) -> str:
    """Seed-path api node id. Path is unknown in the seed model, so use the
    `.` fallback (see MIGRATION-DESIGN section 3.1)."""
    return f"A:{rid}/."


def build_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    # repo nodes are pure git identity; the api surface is a separate node.
    for rid, m in REPOS.items():
        g.add_node(rid, ntype="repo", label=m["label"])
        aid = api_node_id(rid)
        g.add_node(aid, ntype="api", label=m["label"], repo=rid, path=".",
                   style=API_STYLE[rid])
        g.add_edge(aid, rid, etype="located_in", path=".")
    for ent, names in ENTITY_NAMES.items():
        g.add_node(f"E:{ent}", ntype="entity", label=ent,
                   **{f"name_{r}": (names.get(r) or "") for r in REPOS})
    seen_ops: set[str] = set()
    for (ent, op), repo_map in MAP.items():
        eid = f"E:{ent}"
        oid = f"O:{ent}.{op}"
        if oid not in seen_ops:
            g.add_node(oid, ntype="operation", label=op, entity=ent)
            g.add_edge(eid, oid, etype="has_op")
            seen_ops.add(oid)
        for rid, (name, http) in repo_map.items():
            if not name:
                continue  # entity/op absent in this repo
            # exposes now originates from the api node, not the repo node.
            g.add_edge(api_node_id(rid), oid, etype="exposes",
                       repo=rid, name=name, http=(http or ""),
                       style=REPOS[rid]["style"])
    return g


def analyze(g: nx.DiGraph) -> str:
    entities = [n for n, d in g.nodes(data=True) if d["ntype"] == "entity"]
    ops = [n for n, d in g.nodes(data=True) if d["ntype"] == "operation"]
    lines: list[str] = []
    lines.append("# Backend API Knowledge Graph -- Metrics\n")
    lines.append(f"- Nodes: {g.number_of_nodes()} (repos=3, entities={len(entities)}, operations={len(ops)})")
    lines.append(f"- Edges: {g.number_of_edges()}\n")

    lines.append("## Entity naming across repos\n")
    lines.append("| entity | CodePilot (REST) | deepseek-harness (RPC) | hermes-agent (WS-RPC) |")
    lines.append("|---|---|---|---|")
    for e in sorted(entities, key=lambda x: g.nodes[x]["label"]):
        nm = g.nodes[e]
        lines.append(f"| {nm['label']} | {nm['name_CP'] or '-'} | {nm['name_DH'] or '-'} | {nm['name_HM'] or '-'} |")
    lines.append("")

    lines.append("## Operations per entity (with per-repo endpoint)\n")
    for e in sorted(entities, key=lambda x: g.nodes[x]["label"]):
        ename = g.nodes[e]["label"]
        eops = [o for o in g.successors(e) if g.nodes[o]["ntype"] == "operation"]
        if not eops:
            continue
        lines.append(f"### {ename}\n")
        lines.append("| operation | CP (url [method]) | DH (rpc) | HM (rpc) |")
        lines.append("|---|---|---|---|")
        for o in sorted(eops, key=lambda x: g.nodes[x]["label"]):
            cells = {"CP": "-", "DH": "-", "HM": "-"}
            # `exposes` now originates from an api node; the owning repo is carried
            # on the edge's `repo` attribute.
            for src, _, d in g.in_edges(o, data=True):
                if d.get("etype") != "exposes":
                    continue
                r = d.get("repo")
                if r not in cells:
                    continue
                if d["style"] == "REST":
                    cells[r] = f"{d['name']} [{d['http']}]"
                else:
                    cells[r] = d["name"]
            lines.append(f"| {g.nodes[o]['label']} | {cells['CP']} | {cells['DH']} | {cells['HM']} |")
        lines.append("")

    # coverage
    lines.append("## Per-repo API operation coverage\n")
    lines.append("| repo | style | #operations exposed |")
    lines.append("|---|---|---|")
    # exposes edges originate from api nodes and carry the owning repo id.
    exposed_by_repo: dict[str, set] = {rid: set() for rid in REPOS}
    for u, v, d in g.edges(data=True):
        if d.get("etype") == "exposes" and d.get("repo") in exposed_by_repo:
            exposed_by_repo[d["repo"]].add(v)
    for rid in REPOS:
        c = len(exposed_by_repo[rid])
        lines.append(f"| {REPOS[rid]['label']} | {REPOS[rid]['style']} | {c} |")
    lines.append("")
    lines.append("Note: CP uses RESTful URL+HTTP-method; DH and HM use `entity.action` RPC naming "
                 "(no URL/HTTP verb). All are normalized to canonical (entity, operation) nodes so the "
                 "three shapes become comparable. Entity/op absence in a repo = no `exposes` edge.")

    # frontend component -> operation call references (built from code scan)
    comps = [n for n, d in g.nodes(data=True) if d["ntype"] == "component"]
    calls = [(u, v) for u, v, d in g.edges(data=True) if d["etype"] == "calls"]
    if comps:
        lines.append("\n## Frontend call references (component/page -> operation)\n")
        lines.append("Built by scanning frontend source for endpoint calls (scan_frontend_calls.py); "
                     "tests/fixtures excluded.\n")
        lines.append("| repo | caller files | call edges |")
        lines.append("|---|---|---|")
        for rid in REPOS:
            rc = [c for c in comps if g.nodes[c].get("repo") == rid]
            re_ = [e for e in calls if g.nodes[e[0]].get("repo") == rid]
            lines.append(f"| {REPOS[rid]['label']} | {len(rc)} | {len(re_)} |")
        lines.append("")
        # most-called operations
        from collections import Counter
        called = Counter(g.nodes[v]["label"] and v for _, v in calls)
        top = Counter(v for _, v in calls).most_common(8)
        lines.append("Most-referenced operations (by #calling files across repos):\n")
        lines.append("| operation | #call edges |")
        lines.append("|---|---|")
        for oid, n in top:
            lines.append(f"| {oid.replace('O:','')} | {n} |")
        lines.append("")
        lines.append("Architectural signal: CP components fetch endpoints directly (calls spread across "
                     "many component files); DH concentrates RPC in its runtime/connection layer (few files, "
                     "Cordis contract-driven); HM routes most interaction through the PTY terminal, so few "
                     "structured RPC call sites appear.")
    return "\n".join(lines) + "\n"


def main() -> None:
    g = build_graph()
    nx.write_graphml(g, HERE / "api_graph.graphml")
    (HERE / "api_graph.json").write_text(json.dumps(nx.node_link_data(g), indent=2, ensure_ascii=False))
    with open(HERE / "api_graph.dot", "w") as fh:
        fh.write("digraph api {\n")
        for u, v, d in g.edges(data=True):
            fh.write(f'  "{u}" -> "{v}" [label="{d.get("etype","")}"];\n')
        fh.write("}\n")
    (HERE / "api_metrics.md").write_text(analyze(g))
    print("Wrote: api_graph.graphml, api_graph.json, api_graph.dot, api_metrics.md")
    print(f"API graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")


if __name__ == "__main__":
    main()
