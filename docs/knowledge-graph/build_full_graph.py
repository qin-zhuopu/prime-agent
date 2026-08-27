#!/usr/bin/env python3
"""Build the FULL backend-endpoint + frontend-page graph (all endpoints, no trimming).

Reads scan_full.py + scan_full_calls.py outputs (data/full/*.json) and builds:

Node types:
  - repo      : CP / DH / HM (source-verified 'deep' cluster)
  - endpoint_group : namespace / first path segment (e.g. chat, files, session, goal)
  - endpoint  : one backend endpoint (REST url+verb, or RPC/WS-RPC method)
  - page      : a frontend file that calls >=1 endpoint (component/page granularity)

Edges:
  - repo  --has_group-->    endpoint_group
  - endpoint_group --has_endpoint--> endpoint
  - page  --calls-->        endpoint   (attrs: kind, endpoint name)
  - page  --in_repo-->      repo

Outputs: full_api_graph.{graphml,json}, full_api_metrics.md
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import networkx as nx

HERE = Path(__file__).parent
FULL = HERE / "data" / "full"
REPOS = {"CP": "CodePilot", "DH": "deepseek-harness", "HM": "hermes-agent"}


def build_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    for rid, label in REPOS.items():
        g.add_node(f"R:{rid}", ntype="repo", label=label, rid=rid)

    # endpoints + groups
    for rid in REPOS:
        eps = json.loads((FULL / f"endpoints_{rid}.json").read_text())
        for e in eps:
            gid = f"G:{rid}:{e['group']}"
            if gid not in g:
                g.add_node(gid, ntype="endpoint_group", label=e["group"], repo=rid)
                g.add_edge(f"R:{rid}", gid, etype="has_group")
            eid = f"EP:{rid}:{e['id']}"
            g.add_node(eid, ntype="endpoint", label=e["name"], repo=rid,
                       kind=e["kind"], http=e.get("http", ""), group=e["group"],
                       src=e.get("src", ""))
            g.add_edge(gid, eid, etype="has_endpoint")

    # frontend pages + calls
    for rid in REPOS:
        f = FULL / f"calls_{rid}.json"
        if not f.is_file():
            continue
        for c in json.loads(f.read_text()):
            pid = f"P:{rid}:{c['caller_file']}"
            if pid not in g:
                g.add_node(pid, ntype="page", label=c["caller_file"].split("/")[-1],
                           file=c["caller_file"], repo=rid)
                g.add_edge(pid, f"R:{rid}", etype="in_repo")
            # resolve endpoint node id
            eid = f"EP:{rid}:{c['endpoint_id']}" if rid != "CP" else None
            if rid == "CP":
                # CP endpoint id is "VERB url"; a page->url call may hit multiple verbs.
                # link to every verb endpoint on that url.
                targets = [n for n in g.nodes
                           if n.startswith(f"EP:CP:") and g.nodes[n]["label"] == c["endpoint"]]
            else:
                targets = [eid] if eid in g else []
            for t in targets:
                g.add_edge(pid, t, etype="calls", kind=c["kind"], endpoint=c["endpoint"])
    return g


def analyze(g: nx.DiGraph) -> str:
    def nodes_of(t):
        return [n for n, d in g.nodes(data=True) if d["ntype"] == t]
    L: list[str] = []
    L.append("# Full backend-endpoint + frontend-page graph -- Metrics\n")
    L.append(f"- Nodes: {g.number_of_nodes()} "
             f"(repos={len(nodes_of('repo'))}, groups={len(nodes_of('endpoint_group'))}, "
             f"endpoints={len(nodes_of('endpoint'))}, pages={len(nodes_of('page'))})")
    L.append(f"- Edges: {g.number_of_edges()}\n")

    L.append("## Per-repo endpoint & page coverage\n")
    L.append("| repo | endpoints | groups | pages calling API | endpoints hit | server-internal (0 callers) |")
    L.append("|---|---|---|---|---|---|")
    for rid in REPOS:
        eps = [n for n in nodes_of("endpoint") if g.nodes[n]["repo"] == rid]
        grps = [n for n in nodes_of("endpoint_group") if g.nodes[n]["repo"] == rid]
        pages = [n for n in nodes_of("page") if g.nodes[n]["repo"] == rid]
        hit = {v for _, v, d in g.edges(data=True)
               if d.get("etype") == "calls" and g.nodes[v]["repo"] == rid}
        internal = len(eps) - len(hit)
        L.append(f"| {REPOS[rid]} | {len(eps)} | {len(grps)} | {len(pages)} | {len(hit)} | {internal} |")
    L.append("")

    L.append("## Endpoint groups per repo (top by endpoint count)\n")
    for rid in REPOS:
        cnt = Counter(g.nodes[n]["group"] for n in nodes_of("endpoint") if g.nodes[n]["repo"] == rid)
        top = ", ".join(f"{k}({v})" for k, v in cnt.most_common(12))
        L.append(f"- **{REPOS[rid]}** ({len(cnt)} groups): {top}")
    L.append("")

    L.append("## Most-called endpoints (by #calling pages)\n")
    call_targets = Counter()
    for u, v, d in g.edges(data=True):
        if d.get("etype") == "calls":
            call_targets[v] += 1
    L.append("| endpoint | repo | #pages |")
    L.append("|---|---|---|")
    for eid, n in call_targets.most_common(12):
        d = g.nodes[eid]
        name = f"{d.get('http','')} {d['label']}".strip()
        L.append(f"| {name} | {d['repo']} | {n} |")
    L.append("")
    L.append("Architectural signal: CP fans endpoint calls across many component files "
             "(REST, direct fetch); DH concentrates method-name literals in its connection "
             "layer (typed service contract, Cordis); HM exposes many endpoints but routes "
             "most interaction through the PTY terminal, so few have structured frontend callers.")
    return "\n".join(L) + "\n"


def main() -> None:
    g = build_graph()
    nx.write_graphml(g, HERE / "full_api_graph.graphml")
    (HERE / "full_api_graph.json").write_text(
        json.dumps(nx.node_link_data(g), indent=2, ensure_ascii=False))
    (HERE / "full_api_metrics.md").write_text(analyze(g))
    print(f"Full API graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
    print("Wrote full_api_graph.graphml/.json, full_api_metrics.md")


if __name__ == "__main__":
    main()
