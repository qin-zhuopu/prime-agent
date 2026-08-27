#!/usr/bin/env python3
"""Unify all layers into ONE graph, joined on shared repo nodes. NO LLM.

Merges three previously separate graphs on a single canonical repo node per repo:

  UI layer   (build_from_yaml.build_ui_graph):
      repo, protocol, category, feature   + uses/contains/implements
  Full API layer (build_full_graph.build_graph):
      repo, endpoint_group, endpoint, page + has_group/has_endpoint/calls/in_repo

Repo identity is normalized: UI uses "CP", full-API uses "R:CP" -> both map to "CP".
The result is a single heterogeneous graph where a repo node connects to BOTH its
UI features AND its backend endpoints + frontend pages, so you can traverse
feature -> repo -> endpoint_group -> endpoint <- page in one graph.

Validation gate: refuses to build if validate.check_all() reports problems.

Outputs: unified_graph.{graphml,json}, unified_metrics.md
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import networkx as nx
import yaml

import build_from_yaml as ui
import build_full_graph as full
import validate

HERE = Path(__file__).parent


def build() -> nx.DiGraph:
    g = nx.DiGraph()

    # --- UI layer (repo ids like "CP") ---
    uig = ui.build_ui_graph()
    for n, d in uig.nodes(data=True):
        g.add_node(n, layer="ui", **d)
    for u, v, d in uig.edges(data=True):
        g.add_edge(u, v, **d)

    # --- Full API layer (repo ids like "R:CP", entities R:/G:/EP:/P:) ---
    fg = full.build_graph()
    repo_remap = {f"R:{r}": r for r in full.REPOS}  # unify repo node identity
    for n, d in fg.nodes(data=True):
        if n in repo_remap:
            # merge into the existing UI repo node; add API-layer marker
            g.nodes[repo_remap[n]]["has_api_layer"] = True
            continue
        g.add_node(n, layer="api", **d)
    for u, v, d in fg.edges(data=True):
        uu = repo_remap.get(u, u)
        vv = repo_remap.get(v, v)
        g.add_edge(uu, vv, **d)

    # --- capability layer (normalizes ALL 11 repos on user-facing operations) ---
    cap_dir = HERE / "data" / "capabilities"
    for cf in sorted(cap_dir.glob("*.yaml")):
        c = yaml.safe_load(cf.read_text())
        cid = c["id"]
        g.add_node(cid, layer="capability", ntype="capability",
                   label=c["label"], description=c["description"])
        for rid, ev in c.get("implementations", {}).items():
            if rid in g:  # repo node exists (all 11 do)
                g.add_edge(rid, cid, etype="provides",
                           surface_kind=ev["surface_kind"], surface_name=ev["surface_name"])
    return g


def analyze(g: nx.DiGraph) -> str:
    types = Counter(d.get("ntype", "?") for _, d in g.nodes(data=True))
    etypes = Counter(d.get("etype", "?") for _, _, d in g.edges(data=True))
    L: list[str] = []
    L.append("# Unified knowledge graph -- Metrics\n")
    L.append(f"- Total nodes: {g.number_of_nodes()}, edges: {g.number_of_edges()}\n")
    L.append("## Node types\n")
    L.append("| ntype | count |")
    L.append("|---|---|")
    for t, c in types.most_common():
        L.append(f"| {t} | {c} |")
    L.append("\n## Edge types\n")
    L.append("| etype | count |")
    L.append("|---|---|")
    for t, c in etypes.most_common():
        L.append(f"| {t} | {c} |")

    # capability coverage across ALL 11 repos (the true normalization layer)
    all_repos = [n for n, d in g.nodes(data=True) if d.get("ntype") == "repo"]
    L.append("\n## Capability coverage across ALL 11 repos (normalized user operations)\n")
    L.append("| repo | capabilities provided |")
    L.append("|---|---|")
    cap_cov = []
    for rid in all_repos:
        c = sum(1 for _, v, d in g.out_edges(rid, data=True) if d.get("etype") == "provides")
        cap_cov.append((c, g.nodes[rid]["label"]))
    for c, label in sorted(cap_cov, reverse=True):
        L.append(f"| {label} | {c} |")
    L.append("")

    # per-repo: how many of each thing hangs off it (the join payoff), deep cluster only
    L.append("## Per-repo backend/frontend footprint (source-verified deep cluster)\n")
    L.append("| repo | features | endpoints | endpoint groups | pages |")
    L.append("|---|---|---|---|---|")
    for rid, label in full.REPOS.items():
        feat = sum(1 for _, v, d in g.out_edges(rid, data=True)
                   if d.get("etype") == "implements")
        eps = sum(1 for n, d in g.nodes(data=True)
                  if d.get("ntype") == "endpoint" and d.get("repo") == rid)
        grps = sum(1 for n, d in g.nodes(data=True)
                   if d.get("ntype") == "endpoint_group" and d.get("repo") == rid)
        pages = sum(1 for n, d in g.nodes(data=True)
                    if d.get("ntype") == "page" and d.get("repo") == rid)
        L.append(f"| {label} | {feat} | {eps} | {grps} | {pages} |")
    L.append("")
    L.append("This single graph joins the UI-feature view and the full backend/frontend view "
             "on shared repo nodes: you can traverse feature -> repo -> endpoint_group -> "
             "endpoint <- page without leaving the graph. UI-layer nodes carry layer='ui', "
             "backend/page nodes carry layer='api'; repo nodes are shared.")
    return "\n".join(L) + "\n"


def main() -> int:
    problems = validate.check_all()
    if problems:
        print(f"BUILD ABORTED: {len(problems)} validation problems.", file=sys.stderr)
        for p in problems[:20]:
            print("  ", p, file=sys.stderr)
        return 1
    g = build()
    nx.write_graphml(g, HERE / "unified_graph.graphml")
    (HERE / "unified_graph.json").write_text(
        json.dumps(nx.node_link_data(g), indent=2, ensure_ascii=False))
    (HERE / "unified_metrics.md").write_text(analyze(g))
    print(f"Unified graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
    print("Wrote unified_graph.graphml/.json, unified_metrics.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
