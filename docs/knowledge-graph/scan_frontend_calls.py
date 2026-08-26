#!/usr/bin/env python3
"""Scan frontend source for API endpoint CALLS and tie them to operations. NO LLM.

Builds the "component/page -> operation" reference layer: which frontend files call
which backend endpoint. Pure regex over source; matched against the endpoint names
already captured in data/operations/*.yaml.

  - CP: fetch("/api/<path>") / "/api/<path>" string literals -> strip /api -> match REST url
  - DH: RPC method string literals 'entity.action' in packages/client -> match RPC name
  - HM: RPC method string literals "entity.action" in web/src -> match WS-RPC name

Output: data/frontend_calls/<repo>.json  = list of {caller_file, endpoint, kind}
where caller_file is repo-relative and endpoint is the raw called name/url.

Only calls that resolve to a known operation endpoint are kept (others reported as
"unresolved" count). caller_file is the granularity of the reference node.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

HERE = Path(__file__).parent
OPS_DIR = HERE / "data" / "operations"
OUT = HERE / "data" / "frontend_calls"

# frontend roots per repo (relative to repos-root)
FE_ROOTS = {
    "CP": ["CodePilot/src/components", "CodePilot/src/hooks", "CodePilot/src/lib", "CodePilot/src/app"],
    "DH": ["deepseek-harness/packages/client"],
    "HM": ["hermes-agent/web/src"],
}
EXTS = {".ts", ".tsx", ".js", ".jsx", ".vue"}

CP_URL_RE = re.compile(r"""['"`]/api(/[a-zA-Z0-9/_.\-\[\]]+)""")
RPC_STR_RE = re.compile(r"""['"]([a-zA-Z]+\.[a-zA-Z][a-zA-Z.]*)['"]""")


def load_operation_endpoints() -> dict[str, dict[str, str]]:
    """repo -> {endpoint_name -> operation_id}. For CP endpoint_name is the URL."""
    idx: dict[str, dict[str, str]] = {"CP": {}, "DH": {}, "HM": {}}
    for p in OPS_DIR.glob("*.yaml"):
        d = yaml.safe_load(p.read_text())
        for repo, ep in d.get("endpoints", {}).items():
            idx.setdefault(repo, {})[ep["name"]] = d["id"]
    return idx


_SKIP = (".d.ts", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx",
         ".client.spec.ts", ".client.spec.tsx", ".client.ts")


def _is_test(p: Path) -> bool:
    n = p.name
    if any(n.endswith(s) for s in _SKIP):
        return True
    if "fixture" in n or "fake-api" in n or "mock" in n.lower():
        return True
    parts = set(p.parts)
    return "tests" in parts or "test" in parts or "__tests__" in parts


def iter_files(root: Path):
    for p in root.rglob("*"):
        if p.suffix in EXTS and "node_modules" not in p.parts and not _is_test(p):
            yield p


def scan_repo(repo: str, repos_root: Path, ep_index: dict[str, str]) -> tuple[list[dict], int]:
    calls: list[dict] = []
    unresolved = 0
    seen: set[tuple[str, str]] = set()
    # normalize CP dynamic segments in endpoint index: /chat/sessions/[id] etc.
    for rel in FE_ROOTS[repo]:
        root = repos_root / rel
        if not root.is_dir():
            continue
        for f in iter_files(root):
            text = f.read_text(encoding="utf-8", errors="ignore")
            caller = str(f.relative_to(repos_root))
            if repo == "CP":
                for m in CP_URL_RE.findall(text):
                    url = _cp_normalize(m)
                    opid = ep_index.get(url)
                    if opid:
                        key = (caller, opid)
                        if key not in seen:
                            seen.add(key)
                            calls.append({"caller_file": caller, "endpoint": url,
                                          "operation": opid, "kind": "REST"})
            else:
                for name in RPC_STR_RE.findall(text):
                    opid = ep_index.get(name)
                    if opid:
                        key = (caller, opid)
                        if key not in seen:
                            seen.add(key)
                            calls.append({"caller_file": caller, "endpoint": name,
                                          "operation": opid, "kind": "RPC"})
    return calls, unresolved


def _cp_normalize(raw: str) -> str:
    """Map a called URL to the canonical route form used in operations.
    Frontend calls use concrete ids/templates; collapse them to [id] segments and
    trim query/trailing to best-effort match the route table."""
    url = raw.split("?")[0].rstrip("/")
    # collapse ${...} or `${id}` template segments and numeric/uuid-ish concrete ids
    parts = []
    for seg in url.split("/"):
        if not seg:
            continue
        if seg.startswith("$") or seg.startswith("{") or "${" in seg:
            parts.append("[id]")
        else:
            parts.append(seg)
    out = "/" + "/".join(parts)
    return out


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos-root", default=os.environ.get("REPOS_ROOT", "/projects/sandbox"))
    args = ap.parse_args()
    root = Path(args.repos_root)

    OUT.mkdir(parents=True, exist_ok=True)
    idx = load_operation_endpoints()
    summary = {}
    for repo in ("CP", "DH", "HM"):
        calls, _ = scan_repo(repo, root, idx.get(repo, {}))
        (OUT / f"{repo}.json").write_text(json.dumps(calls, indent=2, ensure_ascii=False))
        files = len({c["caller_file"] for c in calls})
        summary[repo] = {"call_edges": len(calls), "caller_files": files}
    print("Frontend endpoint-call references:", summary)
    print(f"Written to {OUT.relative_to(HERE)}/<repo>.json")


if __name__ == "__main__":
    main()
