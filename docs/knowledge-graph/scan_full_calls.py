#!/usr/bin/env python3
"""FULL frontend-call scanner: which frontend files call which backend endpoint. NO LLM.

Matches every frontend file's endpoint calls against the FULL endpoint inventory
(data/full/endpoints_<repo>.json from scan_full.py) — not the trimmed chat subset.

Output: data/full/calls_<repo>.json = [{caller_file, endpoint_id, endpoint, kind}]
Also reports, per repo: files scanned, resolved call edges, distinct caller files,
distinct endpoints hit, and endpoints with zero frontend caller (server-internal).

  - CP: string literals "/api/<path>"  -> strip /api, collapse ${}/[id] -> match REST url
  - DH: RPC method string literals 'ns.action' -> match RPC name
  - HM: RPC method string literals "ns.action" -> match WS-RPC name

Tests/fixtures excluded (see _is_test). caller_file granularity = one frontend file.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
FULL = HERE / "data" / "full"

FE_ROOTS = {
    "CP": ["CodePilot/src"],
    "DH": ["deepseek-harness/packages/client"],
    "HM": ["hermes-agent/web/src"],
}
EXTS = {".ts", ".tsx", ".js", ".jsx", ".vue"}
CP_URL_RE = re.compile(r"""['"`]/api(/[a-zA-Z0-9/_.\-\[\]${}]*)""")
RPC_STR_RE = re.compile(r"""['"]([a-zA-Z]+\.[a-zA-Z][a-zA-Z._]*)['"]""")
_SKIP_SUFFIX = (".d.ts", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx",
                ".client.spec.ts", ".client.spec.tsx")


def _is_test(p: Path) -> bool:
    n = p.name
    if any(n.endswith(s) for s in _SKIP_SUFFIX):
        return True
    if "fixture" in n or "fake-api" in n or "mock" in n.lower():
        return True
    parts = set(p.parts)
    return bool({"tests", "test", "__tests__"} & parts)


def iter_files(root: Path):
    for p in root.rglob("*"):
        if p.suffix in EXTS and "node_modules" not in p.parts and not _is_test(p):
            yield p


def _cp_norm(raw: str) -> str:
    url = raw.split("?")[0].rstrip("/")
    parts = []
    for seg in url.split("/"):
        if not seg:
            continue
        if seg.startswith("$") or seg.startswith("{") or "${" in seg or seg.startswith("["):
            parts.append("[id]")
        else:
            parts.append(seg)
    return "/" + "/".join(parts)


def load_endpoints(repo: str) -> dict[str, str]:
    """endpoint name (url for CP, method for DH/HM) -> a representative endpoint id."""
    idx: dict[str, str] = {}
    f = FULL / f"endpoints_{repo}.json"
    if not f.is_file():
        return idx
    for e in json.loads(f.read_text()):
        # for CP many verbs share one url; map url->url (verb resolved later if needed)
        idx.setdefault(e["name"], e["name"] if repo == "CP" else e["id"])
    return idx


def scan_repo(repo: str, root: Path) -> tuple[list[dict], dict]:
    ep_index = load_endpoints(repo)
    calls: list[dict] = []
    seen: set[tuple[str, str]] = set()
    files_scanned = 0
    for rel in FE_ROOTS[repo]:
        base = root / rel
        if not base.is_dir():
            continue
        for f in iter_files(base):
            files_scanned += 1
            text = f.read_text(encoding="utf-8", errors="ignore")
            caller = str(f.relative_to(root))
            if repo == "CP":
                for m in CP_URL_RE.findall(text):
                    url = _cp_norm(m)
                    if url in ep_index:
                        key = (caller, url)
                        if key not in seen:
                            seen.add(key)
                            calls.append({"caller_file": caller, "endpoint": url,
                                          "endpoint_id": url, "kind": "REST"})
            else:
                for name in RPC_STR_RE.findall(text):
                    if name in ep_index:
                        key = (caller, name)
                        if key not in seen:
                            seen.add(key)
                            calls.append({"caller_file": caller, "endpoint": name,
                                          "endpoint_id": ep_index[name], "kind": "RPC"})
    stats = {
        "files_scanned": files_scanned,
        "call_edges": len(calls),
        "caller_files": len({c["caller_file"] for c in calls}),
        "endpoints_hit": len({c["endpoint"] for c in calls}),
        "endpoints_total": len(ep_index),
    }
    return calls, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos-root", default=os.environ.get("REPOS_ROOT", "/projects/sandbox"))
    args = ap.parse_args()
    root = Path(args.repos_root)
    FULL.mkdir(parents=True, exist_ok=True)

    summary = {}
    for repo in ("CP", "DH", "HM"):
        calls, stats = scan_repo(repo, root)
        (FULL / f"calls_{repo}.json").write_text(json.dumps(calls, indent=2, ensure_ascii=False))
        stats["endpoints_uncalled"] = stats["endpoints_total"] - stats["endpoints_hit"]
        summary[repo] = stats
    print("Full frontend calls:")
    for r, s in summary.items():
        print(f"  {r}: {s}")
    print(f"Written to {FULL.relative_to(HERE)}/calls_<repo>.json")


if __name__ == "__main__":
    main()
