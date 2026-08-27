#!/usr/bin/env python3
"""FULL backend-endpoint scanner for the three source-verified repos. NO LLM, no trimming.

Unlike scan_api.py (which trims to a chat-core canonical subset), this captures EVERY
backend endpoint, then auto-groups by namespace / path segment. Output:
  data/full/endpoints_<repo>.json  = [{repo, id, kind, name, http, group, src}]

Repos covered = the source-verified set (CP/DH/HM), i.e. the 'deep' cluster from
derive_tier.py. Survey repos are README-declared / partly SDK-only (no wire endpoints),
so full endpoint extraction does not apply to them.

  - CP  REST : rglob route.ts; url=path; verbs=export [async] function GET|POST|PUT|DELETE|PATCH
  - DH  RPC  : keys of RpcMethodMap interface in rpc-map.ts ('ns.action')
  - HM  WS-RPC: dotted method string literals "ns.action[.sub]" across tui_gateway/*.py

group = first path segment (CP, minus dynamic [id]) or namespace before first dot (DH/HM).
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "data" / "full"

HTTP_RE = re.compile(r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)\b")
DH_METHOD_RE = re.compile(r"^\s*'([a-zA-Z]+\.[a-zA-Z.]+)'\s*:")
DOTTED_RE = re.compile(r'"([a-z_]+(?:\.[a-z_]+)+)"')


def scan_cp(root: Path) -> list[dict]:
    api = root / "CodePilot" / "src" / "app" / "api"
    out: list[dict] = []
    if not api.is_dir():
        return out
    for route in sorted(api.rglob("route.ts")):
        url = "/" + str(route.parent.relative_to(api)).replace(os.sep, "/")
        if url == "/.":
            url = "/"
        seg = [s for s in url.split("/") if s and not s.startswith("[")]
        group = seg[0] if seg else "root"
        for v in sorted(set(HTTP_RE.findall(route.read_text(encoding="utf-8", errors="ignore")))) or ["<none>"]:
            out.append({"repo": "CP", "kind": "REST", "name": url, "http": v,
                        "id": f"{v} {url}", "group": group,
                        "src": str(route.relative_to(root))})
    return out


def scan_dh(root: Path) -> list[dict]:
    f = root / "deepseek-harness" / "packages" / "host" / "apiproxy" / "src" / "api" / "rpc-map.ts"
    out: list[dict] = []
    if not f.is_file():
        return out
    in_map = False
    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "interface RpcMethodMap" in line:
            in_map = True
            continue
        if in_map:
            if line.strip() == "}":
                break
            m = DH_METHOD_RE.match(line)
            if m:
                name = m.group(1)
                out.append({"repo": "DH", "kind": "RPC", "name": name, "http": "",
                            "id": name, "group": name.split(".")[0],
                            "src": str(f.relative_to(root))})
    return out


def scan_hm(root: Path) -> list[dict]:
    d = root / "hermes-agent" / "tui_gateway"
    seen: dict[str, str] = {}
    if not d.is_dir():
        return []
    for py in sorted(d.glob("*.py")):
        rel = str(py.relative_to(root))
        for m in DOTTED_RE.findall(py.read_text(encoding="utf-8", errors="ignore")):
            if len(m) <= 60 and not m.endswith(".py") and " " not in m:
                seen.setdefault(m, rel)  # first file that mentions it
    return [{"repo": "HM", "kind": "WS-RPC", "name": m, "http": "",
             "id": m, "group": m.split(".")[0], "src": src}
            for m, src in sorted(seen.items())]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos-root", default=os.environ.get("REPOS_ROOT", "/projects/sandbox"))
    args = ap.parse_args()
    root = Path(args.repos_root)
    OUT.mkdir(parents=True, exist_ok=True)

    res = {"CP": scan_cp(root), "DH": scan_dh(root), "HM": scan_hm(root)}
    for repo, eps in res.items():
        (OUT / f"endpoints_{repo}.json").write_text(json.dumps(eps, indent=2, ensure_ascii=False))
    summary = {}
    for repo, eps in res.items():
        groups = sorted({e["group"] for e in eps})
        summary[repo] = {"endpoints": len(eps), "groups": len(groups)}
    print("Full backend endpoints:", summary)
    print(f"Written to {OUT.relative_to(HERE)}/endpoints_<repo>.json")


if __name__ == "__main__":
    main()
