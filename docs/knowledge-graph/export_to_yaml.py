#!/usr/bin/env python3
"""One-shot exporter: dump the current in-memory graphs to per-node YAML files.

Reads the existing build_graph.py (UI) and build_api_graph.py (API) graphs and writes
one YAML file per node under data/, grouped by node type. This makes the graph data
reviewable/diffable and lets validate.py check it against schemas/.

Run once to seed data/; after that, edit YAML files directly and rebuild from them.
"""
from __future__ import annotations

from pathlib import Path

import yaml

import build_graph as ui
import build_api_graph as api

HERE = Path(__file__).parent
DATA = HERE / "data"

# transport class per repo (SSE vs WebSocket vs stdio). Authored from source scan.
REPO_TRANSPORT = {
    "CP": ["SSE"], "DH": ["SSE"], "HM": ["WebSocket"],
    "ACPC": ["stdio"], "ACPUI": ["stdio"], "ASTUI": ["SSE"],
    "OCUI": ["SSE"], "OGUI": ["SSE"], "CKIT": ["SSE"],
    "ACHAT": ["stdio"], "ACPWG": ["WebSocket"],
}

# transport class per protocol node
PROTOCOL_META = {
    "SSE": ("transport", "SSE"),
    "WS-JSONRPC": ("protocol", "WebSocket"),
    "ACP": ("protocol", "stdio"),
    "AG-UI": ("protocol", "SSE"),
    "structured-render": ("rendering", "n/a"),
    "node-render": ("rendering", "n/a"),
    "pty-terminal": ("rendering", "n/a"),
}


def dump(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True))


def main() -> None:
    g = ui.build_graph()
    ag = api.build_graph()

    # --- repos ---
    for rid, d in g.nodes(data=True):
        if d["ntype"] != "repo":
            continue
        protos = sorted(v for _, v in g.out_edges(rid) if g.nodes[v]["ntype"] == "protocol")
        dump(DATA / "repos" / f"{rid}.yaml", {
            "id": rid, "ntype": "repo", "label": d["label"],
            "stack": d.get("stack", ""), "license": d.get("license", ""),
            "transport": REPO_TRANSPORT.get(rid, ["none/unknown"]),
            "protocols": protos,
        })

    # --- protocols ---
    for pid, d in g.nodes(data=True):
        if d["ntype"] != "protocol":
            continue
        kind, transport = PROTOCOL_META.get(pid, ("protocol", "n/a"))
        dump(DATA / "protocols" / f"{pid}.yaml", {
            "id": pid, "ntype": "protocol", "label": d["label"],
            "kind": kind, "transport": transport,
        })

    # --- features ---
    for fid, d in g.nodes(data=True):
        if d["ntype"] != "feature":
            continue
        impls = {}
        for r, _, e in g.in_edges(fid, data=True):
            if g.nodes[r]["ntype"] == "repo":
                impls[r] = {"kind": e["kind"], "source": e["source"]}
        fname = fid.replace(":", "__")
        dump(DATA / "features" / f"{fname}.yaml", {
            "id": fid, "ntype": "feature", "label": d["label"],
            "category": d["category"], "priority": d["priority"],
            "implementations": dict(sorted(impls.items())),
        })

    # --- entities ---
    for eid, d in ag.nodes(data=True):
        if d["ntype"] != "entity":
            continue
        names = {r: d[f"name_{r}"] for r in ("CP", "DH", "HM") if d.get(f"name_{r}")}
        dump(DATA / "entities" / f"{d['label']}.yaml", {
            "id": eid, "ntype": "entity", "label": d["label"], "names": names,
        })

    # --- operations ---
    for oid, d in ag.nodes(data=True):
        if d["ntype"] != "operation":
            continue
        endpoints = {}
        for r, _, e in ag.in_edges(oid, data=True):
            if ag.nodes[r]["ntype"] != "repo":
                continue
            ep = {"name": e["name"], "style": e["style"]}
            if e["style"] == "REST":
                ep["http"] = e.get("http", "")
            endpoints[r] = ep
        fname = oid.replace("O:", "").replace(".", "__")
        dump(DATA / "operations" / f"{fname}.yaml", {
            "id": oid, "ntype": "operation", "label": d["label"],
            "entity": d["entity"], "endpoints": dict(sorted(endpoints.items())),
        })

    counts = {}
    for sub in ("repos", "protocols", "features", "entities", "operations"):
        counts[sub] = len(list((DATA / sub).glob("*.yaml")))
    print("Exported YAML node files:", counts)


if __name__ == "__main__":
    main()
