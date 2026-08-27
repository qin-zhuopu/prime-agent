#!/usr/bin/env python3
"""Build both knowledge graphs FROM the per-node YAML data, with validation gate.

This is the canonical build path once data/ is seeded: it reads YAML (not hardcoded
dicts), runs validate.check_all() first, and refuses to build if there are problems
(fail-closed). Reuses the analysis writers from build_graph.py / build_api_graph.py.

Outputs: chat_ui_graph.* + metrics.md, api_graph.* + api_metrics.md (same as before).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import networkx as nx
import yaml

import build_graph as ui
import build_api_graph as api
import validate

HERE = Path(__file__).parent
DATA = HERE / "data"


def _load(subdir: str) -> list[dict]:
    return [yaml.safe_load(p.read_text()) for p in sorted((DATA / subdir).glob("*.yaml"))]


def webui_by_repo() -> dict[str, dict]:
    """repo id -> its webui node dict (one webui per repo in the current model)."""
    return {d["repo"]: d for d in _load("webui")}


def api_by_repo() -> dict[str, dict]:
    """repo id -> its api node dict (only network-surface repos have one)."""
    return {d["repo"]: d for d in _load("api")}


def build_ui_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    # repo nodes are pure git identity now (id/label/license only).
    for d in _load("repos"):
        g.add_node(d["id"], ntype="repo", label=d["label"], license=d.get("license", ""))
    # webui nodes carry the relocated frontend runtime facts and located_in edge.
    webui = webui_by_repo()
    for rid, d in webui.items():
        g.add_node(d["id"], ntype="webui", label=d["label"], repo=rid, path=d.get("path", "."),
                   stack=d.get("stack", ""),
                   integration=",".join(d.get("integration", [])),
                   browser_native=bool(d.get("browser_native", False)),
                   transport=",".join(d.get("transport", [])),
                   protocols=",".join(d.get("protocols", [])))
        g.add_edge(d["id"], rid, etype="located_in", path=d.get("path", "."))
        # uses now originates from the webui node (was repo--uses).
        for proto in d.get("protocols", []):
            g.add_edge(d["id"], proto, etype="uses")
    for d in _load("protocols"):
        g.add_node(d["id"], ntype="protocol", label=d["label"],
                   kind=d.get("kind", ""), transport=d.get("transport", ""))
    for d in _load("features"):
        cid = d["category"]
        if cid not in g:
            g.add_node(cid, ntype="category", label=cid, priority=d["priority"])
        g.add_node(d["id"], ntype="feature", label=d["label"], category=cid, priority=d["priority"])
        g.add_edge(cid, d["id"], etype="contains")
        # implements now originates from the repo's webui node (was repo--implements).
        # No bare-repo fallback: every repo has a webui (enforced by validate.py);
        # fail loud rather than silently re-couple the edge onto the repo node.
        for rid, impl in d.get("implementations", {}).items():
            if rid not in webui:
                raise ValueError(f"feature {d['id']}: repo '{rid}' has no webui node "
                                 f"to home the implements edge on")
            g.add_edge(webui[rid]["id"], d["id"], etype="implements",
                       kind=impl["kind"], source=impl["source"])
    return g


def build_api_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    # bare repo nodes (pure git identity).
    for rid, m in api.REPOS.items():
        g.add_node(rid, ntype="repo", label=m["label"])
    # api nodes: one per network-surface repo, located_in the repo, subtyped by style.
    apis = api_by_repo()
    for rid, d in apis.items():
        if rid not in g:
            g.add_node(rid, ntype="repo", label=d["label"])
        g.add_node(d["id"], ntype="api", label=d["label"], repo=rid, path=d.get("path", "."),
                   style=d.get("style", ""), transport=",".join(d.get("transport", [])))
        g.add_edge(d["id"], rid, etype="located_in", path=d.get("path", "."))
    for d in _load("entities"):
        names = d.get("names", {})
        g.add_node(d["id"], ntype="entity", label=d["label"],
                   **{f"name_{r}": names.get(r, "") for r in api.REPOS})
    for d in _load("operations"):
        oid = d["id"]
        g.add_node(oid, ntype="operation", label=d["label"], entity=d["entity"])
        g.add_edge(f"E:{d['entity']}", oid, etype="has_op")
        # exposes now originates from the repo's api node (was repo--exposes).
        # No bare-repo fallback: a repo exposing an operation must have an api
        # node (enforced by validate.py); fail loud rather than re-couple the
        # exposes edge onto the bare repo node.
        for rid, ep in d.get("endpoints", {}).items():
            if rid not in apis:
                raise ValueError(f"operation {oid}: repo '{rid}' has no api node "
                                 f"to home the exposes edge on")
            g.add_edge(apis[rid]["id"], oid, etype="exposes", repo=rid, name=ep["name"],
                       http=ep.get("http", ""), style=ep["style"])

    # frontend component/page -> operation call references (built from code scan).
    # We keep the fine-grained component--calls-->operation edges AND add an
    # aggregated webui--calls-->api edge per repo (decision C).
    webui = webui_by_repo()
    fc_dir = DATA / "frontend_calls"
    if fc_dir.is_dir():
        for fj in sorted(fc_dir.glob("*.json")):
            repo = fj.stem
            for c in json.loads(fj.read_text()):
                cid = f"C:{repo}:{c['caller_file']}"
                if cid not in g:
                    g.add_node(cid, ntype="component", label=c["caller_file"].split("/")[-1],
                               file=c["caller_file"], repo=repo)
                if c["operation"] in g:
                    g.add_edge(cid, c["operation"], etype="calls",
                               repo=repo, endpoint=c["endpoint"], kind=c["kind"])
            # aggregated webui--calls-->api edge for this repo (decision C).
            if repo in webui and repo in apis:
                wid = webui[repo]["id"]
                aid = apis[repo]["id"]
                if wid not in g:
                    g.add_node(wid, ntype="webui", label=webui[repo]["label"],
                               repo=repo, path=webui[repo].get("path", "."))
                g.add_edge(wid, aid, etype="calls", repo=repo)
    return g


def _write_dot(g: nx.DiGraph, path: Path, name: str) -> None:
    try:
        nx.nx_pydot.write_dot(g, path)
    except Exception:
        with open(path, "w") as fh:
            fh.write(f"digraph {name} {{\n")
            for u, v, d in g.edges(data=True):
                fh.write(f'  "{u}" -> "{v}" [label="{d.get("etype","")}"];\n')
            fh.write("}\n")


def main() -> int:
    problems = validate.check_all()
    if problems:
        print(f"BUILD ABORTED: {len(problems)} validation problem(s). Run validate.py.", file=sys.stderr)
        for p in problems[:20]:
            print("  ", p, file=sys.stderr)
        return 1

    g = build_ui_graph()
    nx.write_graphml(g, HERE / "chat_ui_graph.graphml")
    (HERE / "chat_ui_graph.json").write_text(json.dumps(nx.node_link_data(g), indent=2, ensure_ascii=False))
    _write_dot(g, HERE / "chat_ui_graph.dot", "chat_ui")
    (HERE / "metrics.md").write_text(ui.analyze(g))

    ag = build_api_graph()
    nx.write_graphml(ag, HERE / "api_graph.graphml")
    (HERE / "api_graph.json").write_text(json.dumps(nx.node_link_data(ag), indent=2, ensure_ascii=False))
    _write_dot(ag, HERE / "api_graph.dot", "api")
    (HERE / "api_metrics.md").write_text(api.analyze(ag))

    print(f"OK (validated). UI graph: {g.number_of_nodes()} nodes/{g.number_of_edges()} edges; "
          f"API graph: {ag.number_of_nodes()} nodes/{ag.number_of_edges()} edges")
    return 0


if __name__ == "__main__":
    sys.exit(main())
