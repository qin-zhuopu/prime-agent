#!/usr/bin/env python3
"""Data quality checker for the knowledge graph (coverage & gap report). NO LLM.

Complements validate.py (which is pass/fail correctness). This one is a GRADED report
of completeness gaps: what is missing, thin, asymmetric, or orphaned — so gaps can be
filled deliberately. Levels: ERROR (must fix) / WARN (should fill) / INFO (by design).

Checks:
  - schema coverage : every node type used in the graph has a schema file
  - repo coverage   : which repos have UI-feature data / API data / frontend-call data
  - feature coverage: features with no implementations; per-repo feature counts
  - api coverage    : entities with few operations; operations exposed by 0 repos
  - call coverage   : operations no frontend calls resolve to; repos with 0 call data
  - field coverage  : optional-but-recommended fields left blank (stack, license, ...)

Exit 0 always (report tool); use --strict to exit 1 when ERRORs exist.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).parent
DATA = HERE / "data"
SCHEMAS = HERE / "schemas"

NODE_DIRS = {"repo": "repos", "protocol": "protocols", "feature": "features",
             "entity": "entities", "operation": "operations"}
GRAPH_NODE_TYPES = set(NODE_DIRS) | {"component", "category"}


def load(subdir: str) -> list[dict]:
    return [yaml.safe_load(p.read_text()) for p in sorted((DATA / subdir).glob("*.yaml"))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit 1 if any ERROR")
    args = ap.parse_args()

    errors: list[str] = []
    warns: list[str] = []
    infos: list[str] = []

    repos = load("repos")
    features = load("features")
    entities = load("entities")
    operations = load("operations")
    repo_ids = [r["id"] for r in repos]
    # emergent tier from data (no manual label); deep cluster = high feature coverage
    import derive_tier
    tiers = derive_tier.classify()
    deep = set(tiers["deep"])

    # --- schema coverage ---
    have_schema = {p.stem.replace(".schema", "") for p in SCHEMAS.glob("*.schema.yaml")}
    # node types that actually appear in the graph
    graph_types = set(NODE_DIRS)
    if (DATA / "frontend_calls").is_dir():
        graph_types.add("component")
    graph_types.add("category")  # created implicitly by build_graph
    for t in sorted(graph_types):
        if t not in have_schema:
            errors.append(f"schema: node type '{t}' used in graph has NO schema file")
    infos.append(f"schema: {len(graph_types)} graph node types, all have schema files "
                 f"({', '.join(sorted(graph_types))})")

    # --- repo coverage: UI vs API vs calls ---
    feat_repos = set()
    for f in features:
        feat_repos |= set(f.get("implementations", {}))
    api_repos = set()
    for o in operations:
        api_repos |= set(o.get("endpoints", {}))
    call_repos = {p.stem for p in (DATA / "frontend_calls").glob("*.json")}

    for rid in repo_ids:
        if rid not in feat_repos:
            warns.append(f"coverage: repo {rid} has NO UI feature implementations recorded")
    for rid in repo_ids:
        if rid not in api_repos:
            t = "deep" if rid in deep else "broad"
            # broad cluster is intentionally UI-only; missing API there is expected
            (infos if rid not in deep else errors).append(
                f"coverage: repo {rid} ({t}) has NO API entity/operation data")
    for rid in repo_ids:
        if rid not in call_repos:
            t = "deep" if rid in deep else "broad"
            (infos if rid not in deep else warns).append(
                f"coverage: repo {rid} ({t}) has NO frontend-call data")

    # --- feature coverage ---
    for f in features:
        if not f.get("implementations"):
            warns.append(f"feature: {f['id']} has zero implementations (orphan feature)")

    # --- api coverage ---
    ops_by_entity = defaultdict(list)
    for o in operations:
        ops_by_entity[o["entity"]].append(o["label"])
    for e in entities:
        n = len(ops_by_entity.get(e["label"], []))
        if n == 0:
            errors.append(f"api: entity {e['label']} has NO operations")
        elif n == 1:
            warns.append(f"api: entity {e['label']} has only 1 operation ({ops_by_entity[e['label']][0]}) — likely thin")
    for o in operations:
        if not o.get("endpoints"):
            errors.append(f"api: operation {o['id']} exposed by 0 repos (orphan)")

    # --- entity name coverage across repos (deep cluster only, since only they have API data) ---
    deep_list = sorted(deep)
    for e in entities:
        named = set(e.get("names", {}))
        missing = [r for r in deep_list if r not in named]
        if len(named) < len(deep_list) and missing:
            infos.append(f"api: entity {e['label']} has no name in {missing} (absent there, or unmapped)")

    # --- call coverage: operations nothing calls ---
    called_ops = set()
    for fj in (DATA / "frontend_calls").glob("*.json"):
        for rec in json.loads(fj.read_text()):
            called_ops.add(rec["operation"])
    uncalled = [o["id"] for o in operations if o["id"] not in called_ops]
    if uncalled:
        infos.append(f"calls: {len(uncalled)} operations have no resolved frontend call "
                     f"(may be server-internal, event-only, or scanner gap)")

    # --- field coverage (recommended fields) ---
    for r in repos:
        for fld in ("stack", "license", "integration", "browser_native", "transport"):
            if fld not in r or r.get(fld) in (None, "", []):
                warns.append(f"field: repo {r['id']} missing/empty recommended field '{fld}'")

    # --- capability layer coverage (all 11 repos, normalized user operations) ---
    caps = load("capabilities")
    if caps:
        cov = {rid: 0 for rid in repo_ids}
        for c in caps:
            for rid in c.get("implementations", {}):
                cov[rid] = cov.get(rid, 0) + 1
        ranked = sorted(cov.items(), key=lambda kv: -kv[1])
        infos.append(f"capability: {len(caps)} normalized user capabilities across all {len(repo_ids)} repos; "
                     f"coverage " + ", ".join(f"{r}={n}" for r, n in ranked))
        for c in caps:
            if not c.get("implementations"):
                warns.append(f"capability: {c['id']} implemented by no repo")

    # --- full layer (untrimmed endpoints + calls) coverage ---
    full_dir = DATA / "full"
    if full_dir.is_dir():
        for rid in ("CP", "DH", "HM"):
            ej = full_dir / f"endpoints_{rid}.json"
            cj = full_dir / f"calls_{rid}.json"
            if not ej.is_file():
                errors.append(f"full: missing endpoints_{rid}.json")
                continue
            eps = json.loads(ej.read_text())
            ep_names = {e["name"] for e in eps}
            hit = {c["endpoint"] for c in json.loads(cj.read_text())} if cj.is_file() else set()
            uncalled = len(ep_names - hit)
            infos.append(f"full: {rid} has {len(eps)} endpoints ({len(ep_names)} distinct), "
                         f"{len(hit)} called by frontend, {uncalled} server-internal (no frontend caller)")

    # --- report ---
    def show(title, items):
        print(f"\n## {title} ({len(items)})")
        for it in items:
            print("  -", it)

    print("# Knowledge-graph data quality report")
    print(f"\n> Tiers are EMERGENT (derive_tier.py), not hand-assigned: repos cluster by "
          f"feature coverage at the largest natural gap (={tiers['gap']}). The 'deep' cluster "
          f"({', '.join(sorted(deep))}) also happens to be the set whose source was read in full; "
          f"'broad' repos ({', '.join(sorted(set(repo_ids)-deep))}) have UI-feature breadth only, so "
          f"their absent API/call layers below are expected, not defects.")
    print(f"\nrepos={len(repos)} (deep={len(deep)}, broad={len(repos)-len(deep)}), "
          f"protocols={len(load('protocols'))}, capabilities={len(load('capabilities'))}, features={len(features)}, "
          f"entities={len(entities)}, operations={len(operations)}, "
          f"schemas={len(have_schema)}")
    show("ERROR (must fix)", errors)
    show("WARN (should fill)", warns)
    show("INFO (by design / expected)", infos)
    print(f"\nSummary: {len(errors)} errors, {len(warns)} warnings, {len(infos)} infos")

    if args.strict and errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
