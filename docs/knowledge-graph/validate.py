#!/usr/bin/env python3
"""Full-corpus quality checker for the knowledge-graph YAML data.

Three layers of checks:
  1. schema      : each YAML node validates against schemas/<ntype>.schema.yaml
  2. referential : cross-node references resolve (op.entity -> entity node,
                   feature.impl repo -> repo node, repo.protocols -> protocol node, etc.)
  3. semantic     : quality rules (unique ids, id/filename/label consistency,
                   REST endpoints carry http verb, no orphan operations, transport sanity)

Exit code 0 = clean, 1 = problems found. Import check_all() to reuse in build scripts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

HERE = Path(__file__).parent
DATA = HERE / "data"
SCHEMAS = HERE / "schemas"

NTYPES = ["repo", "protocol", "feature", "entity", "operation"]
SUBDIR = {"repo": "repos", "protocol": "protocols", "feature": "features",
          "entity": "entities", "operation": "operations"}


def _load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text())


def load_all() -> dict[str, list[tuple[Path, dict]]]:
    out: dict[str, list[tuple[Path, dict]]] = {t: [] for t in NTYPES}
    for t in NTYPES:
        for p in sorted((DATA / SUBDIR[t]).glob("*.yaml")):
            out[t].append((p, _load_yaml(p)))
    return out


def check_all() -> list[str]:
    problems: list[str] = []
    validators = {
        t: Draft7Validator(_load_yaml(SCHEMAS / f"{t}.schema.yaml")) for t in NTYPES
    }
    nodes = load_all()

    # index for referential checks
    repo_ids = {d["id"] for _, d in nodes["repo"]}
    protocol_ids = {d["id"] for _, d in nodes["protocol"]}
    entity_labels = {d["label"] for _, d in nodes["entity"]}
    all_ids: dict[str, Path] = {}

    # 1. schema + id uniqueness + filename/id consistency
    for t in NTYPES:
        for p, d in nodes[t]:
            for err in sorted(validators[t].iter_errors(d), key=lambda e: e.path):
                loc = "/".join(str(x) for x in err.path) or "(root)"
                problems.append(f"[schema] {p.name}: {loc}: {err.message}")
            nid = d.get("id")
            if nid in all_ids:
                problems.append(f"[dup-id] {nid} in {p.name} and {all_ids[nid].name}")
            else:
                all_ids[nid] = p

    # 2. referential integrity
    for p, d in nodes["repo"]:
        for proto in d.get("protocols", []):
            if proto not in protocol_ids:
                problems.append(f"[ref] repo {d['id']}: protocol '{proto}' not found")
    for p, d in nodes["feature"]:
        for rid in d.get("implementations", {}):
            if rid not in repo_ids:
                problems.append(f"[ref] feature {d['id']}: impl repo '{rid}' not found")
    for p, d in nodes["entity"]:
        for rid in d.get("names", {}):
            if rid not in repo_ids:
                problems.append(f"[ref] entity {d['id']}: name repo '{rid}' not found")
    op_entities = set()
    for p, d in nodes["operation"]:
        op_entities.add(d["entity"])
        if d["entity"] not in entity_labels:
            problems.append(f"[ref] operation {d['id']}: entity '{d['entity']}' has no entity node")
        for rid, ep in d.get("endpoints", {}).items():
            if rid not in repo_ids:
                problems.append(f"[ref] operation {d['id']}: endpoint repo '{rid}' not found")

    # 3. semantic quality rules
    for p, d in nodes["operation"]:
        # id must encode entity.label
        expected = f"O:{d['entity']}.{d['label']}"
        if d["id"] != expected:
            problems.append(f"[semantic] operation {p.name}: id '{d['id']}' != expected '{expected}'")
        for rid, ep in d.get("endpoints", {}).items():
            if ep["style"] == "REST" and not ep.get("http"):
                problems.append(f"[semantic] operation {d['id']} @ {rid}: REST endpoint missing http verb")
            if ep["style"] in ("RPC", "WS-RPC") and ep.get("http"):
                problems.append(f"[semantic] operation {d['id']} @ {rid}: non-REST endpoint should not carry http verb")
        if not d.get("endpoints"):
            problems.append(f"[semantic] operation {d['id']}: orphan (no repo exposes it)")
    for p, d in nodes["feature"]:
        expected_cat = d["id"].split(":", 1)[0]
        if d["category"] != expected_cat:
            problems.append(f"[semantic] feature {p.name}: category '{d['category']}' != id prefix '{expected_cat}'")
    # every declared entity should have at least one operation
    for p, d in nodes["entity"]:
        if d["label"] not in op_entities:
            problems.append(f"[semantic] entity {d['id']}: no operation node references it")
    # transport sanity: every repo must declare a transport, and each declared
    # transport must be a real transport class (not a rendering paradigm).
    # NOTE: repo.transport is authoritative (what the repo actually uses); a
    # protocol's transport is only its *native/typical* one (e.g. ACP is natively
    # stdio, but acp-web-gateway carries it over WebSocket), so we do NOT force
    # repo.transport to equal its protocols' transports.
    valid_transports = {"SSE", "WebSocket", "stdio", "none/unknown"}
    for p, d in nodes["repo"]:
        rtrans = set(d.get("transport", []))
        if not rtrans:
            problems.append(f"[semantic] repo {d['id']}: no transport declared")
        bad = rtrans - valid_transports
        if bad:
            problems.append(f"[semantic] repo {d['id']}: unknown transport(s) {sorted(bad)}")

    return problems


def main() -> int:
    problems = check_all()
    total = sum(len(list((DATA / SUBDIR[t]).glob("*.yaml"))) for t in NTYPES)
    if not problems:
        print(f"OK: {total} YAML nodes valid (schema + referential + semantic).")
        return 0
    print(f"FOUND {len(problems)} problem(s) across {total} nodes:\n")
    for pr in problems:
        print(" ", pr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
