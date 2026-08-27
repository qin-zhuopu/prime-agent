#!/usr/bin/env python3
"""Derive repo depth tiers from data (unsupervised), replacing the removed manual 'tier'.

No hand-assigned label. A repo's tier EMERGES from how many UI features it implements:
we sort repos by feature-implementation count and split at the single largest gap
(1-D natural-breaks / maximum-gap clustering, k=2). The high-coverage cluster is
"deep", the rest are "broad".

This is a pure function over the YAML data; call classify() from other scripts.
Nothing is written back to the YAML — tier is a computed view, not stored input.
"""
from __future__ import annotations

from pathlib import Path

import yaml

HERE = Path(__file__).parent
DATA = HERE / "data"


def _feature_impl_counts() -> dict[str, int]:
    """repo id -> number of features it implements (from feature YAML)."""
    counts: dict[str, int] = {}
    for p in (DATA / "repos").glob("*.yaml"):
        counts[yaml.safe_load(p.read_text())["id"]] = 0
    for p in (DATA / "features").glob("*.yaml"):
        for rid in yaml.safe_load(p.read_text()).get("implementations", {}):
            counts[rid] = counts.get(rid, 0) + 1
    return counts


def classify() -> dict:
    """Return the emergent tiering.

    { 'counts': {repo: n}, 'threshold': int, 'gap': int,
      'deep': [repo...], 'broad': [repo...] }
    """
    counts = _feature_impl_counts()
    ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    vals = [n for _, n in ordered]

    if len(vals) < 2:
        return {"counts": counts, "threshold": 0, "gap": 0,
                "deep": [r for r, _ in ordered], "broad": []}

    # largest gap between consecutive sorted values = the natural break
    gaps = [(vals[i] - vals[i + 1], i) for i in range(len(vals) - 1)]
    gap, split_i = max(gaps)
    threshold = vals[split_i]  # last value still in the "deep" cluster
    deep = [r for r, n in ordered if n >= threshold]
    broad = [r for r, n in ordered if n < threshold]
    return {"counts": counts, "threshold": threshold, "gap": gap,
            "deep": deep, "broad": broad}


def main() -> None:
    res = classify()
    print("# Emergent repo tiers (from feature-implementation coverage)\n")
    print(f"{'features':>8}  cluster  repo")
    deep = set(res["deep"])
    for rid, n in sorted(res["counts"].items(), key=lambda kv: kv[1], reverse=True):
        print(f"{n:>8}  {'deep' if rid in deep else 'broad':6}  {rid}")
    print(f"\nnatural break: largest gap = {res['gap']} "
          f"(cluster boundary at >= {res['threshold']} features)")
    print(f"deep  ({len(res['deep'])}): {', '.join(res['deep'])}")
    print(f"broad ({len(res['broad'])}): {', '.join(res['broad'])}")
    print("\nNote: tiers are computed from data, not hand-assigned. Add/remove repos "
          "and they re-cluster automatically.")


if __name__ == "__main__":
    main()
