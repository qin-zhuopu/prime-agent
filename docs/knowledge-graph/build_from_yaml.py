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


def build_ui_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    for d in _load("repos"):
        g.add_node(d["id"], ntype="repo", label=d["label"], stack=d.get("stack", ""),
                   license=d.get("license", ""), tier=d["tier"],
                   integration=",".join(d.get("integration", [])),
                   browser_native=bool(d.get("browser_native", False)),
                   transport=",".join(d.get("transport", [])))
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
        for rid, impl in d.get("implementations", {}).items():
            g.add_edge(rid, d["id"], etype="implements", kind=impl["kind"], source=impl["source"])
    return g


def build_api_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    # repos (reuse styles from api module)
    for rid, m in api.REPOS.items():
        g.add_node(rid, ntype="repo", label=m["label"], style=m["style"])
    for d in _load("entities"):
        names = d.get("names", {})
        g.add_node(d["id"], ntype="entity", label=d["label"],
                   **{f"name_{r}": names.get(r, "") for r in api.REPOS})
    for d in _load("operations"):
        oid = d["id"]
        g.add_node(oid, ntype="operation", label=d["label"], entity=d["entity"])
        g.add_edge(f"E:{d['entity']}", oid, etype="has_op")
        for rid, ep in d.get("endpoints", {}).items():
            g.add_edge(rid, oid, etype="exposes", repo=rid, name=ep["name"],
                       http=ep.get("http", ""), style=ep["style"])

    # frontend component/page -> operation call references (built from code scan)
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
    return g


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
    (HERE / "metrics.md").write_text(ui.analyze(g))

    ag = build_api_graph()
    nx.write_graphml(ag, HERE / "api_graph.graphml")
    (HERE / "api_graph.json").write_text(json.dumps(nx.node_link_data(ag), indent=2, ensure_ascii=False))
    (HERE / "api_metrics.md").write_text(api.analyze(ag))

    print(f"OK (validated). UI graph: {g.number_of_nodes()} nodes/{g.number_of_edges()} edges; "
          f"API graph: {ag.number_of_nodes()} nodes/{ag.number_of_edges()} edges")
    return 0


if __name__ == "__main__":
    sys.exit(main())
