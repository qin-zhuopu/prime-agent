#!/usr/bin/env python3
"""Pure-script backend API scanner (NO LLM).

Mechanically extracts raw API endpoints from the three primary repos by reading
source files with regex only. Outputs structured JSON per repo under data/api_raw/.

  - CP (CodePilot):     Next.js file routes. URL = path under src/app/api;
                        HTTP verbs = `export [async] function GET|POST|...`.
  - DH (deepseek-harness): RPC map. methods = keys of RpcMethodMap in
                        packages/host/apiproxy/src/api/rpc-map.ts ('entity.action').
  - HM (hermes-agent):  WS JSON-RPC. methods = dotted string literals "a.b[.c]"
                        found across tui_gateway/*.py (JSON-RPC naming convention).

This produces the RAW endpoint inventory. Canonical (entity, operation) mapping is a
separate, explicit step in map_api.py — kept apart so the mechanical scan has zero
judgement in it and is fully reproducible.

Configure repo roots via env or --repos-root (default: /projects/sandbox).
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "data" / "api_raw"

HTTP_RE = re.compile(r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)\b")
DH_METHOD_RE = re.compile(r"^\s*'([a-zA-Z]+\.[a-zA-Z.]+)'\s*:")
DOTTED_RE = re.compile(r'"([a-z_]+(?:\.[a-z_]+)+)"')


def scan_cp(root: Path) -> list[dict]:
    api_dir = root / "CodePilot" / "src" / "app" / "api"
    endpoints: list[dict] = []
    if not api_dir.is_dir():
        return endpoints
    for route in sorted(api_dir.rglob("route.ts")):
        url = "/" + str(route.parent.relative_to(api_dir)).replace(os.sep, "/")
        if url == "/.":
            url = "/"
        verbs = sorted(set(HTTP_RE.findall(route.read_text(encoding="utf-8", errors="ignore"))))
        for v in verbs or ["<none>"]:
            endpoints.append({"repo": "CP", "style": "REST", "url": url, "http": v,
                              "name": url, "src": str(route.relative_to(root))})
    return endpoints


def scan_dh(root: Path) -> list[dict]:
    f = root / "deepseek-harness" / "packages" / "host" / "apiproxy" / "src" / "api" / "rpc-map.ts"
    endpoints: list[dict] = []
    if not f.is_file():
        return endpoints
    in_map = False
    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "RpcMethodMap" in line and "interface" in line:
            in_map = True
            continue
        if in_map:
            if line.strip() == "}":
                break
            m = DH_METHOD_RE.match(line)
            if m:
                endpoints.append({"repo": "DH", "style": "RPC", "name": m.group(1),
                                  "http": "", "src": str(f.relative_to(root))})
    return endpoints


def scan_hm(root: Path) -> list[dict]:
    d = root / "hermes-agent" / "tui_gateway"
    methods: set[str] = set()
    if not d.is_dir():
        return []
    for py in sorted(d.glob("*.py")):
        for m in DOTTED_RE.findall(py.read_text(encoding="utf-8", errors="ignore")):
            # JSON-RPC method convention: namespace.action[.sub]; skip obvious non-methods
            if len(m) <= 60 and not m.endswith(".py") and " " not in m:
                methods.add(m)
    return [{"repo": "HM", "style": "WS-RPC", "name": m, "http": "",
             "src": "tui_gateway/*.py"} for m in sorted(methods)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos-root", default=os.environ.get("REPOS_ROOT", "/projects/sandbox"))
    args = ap.parse_args()
    root = Path(args.repos_root)

    OUT.mkdir(parents=True, exist_ok=True)
    results = {"CP": scan_cp(root), "DH": scan_dh(root), "HM": scan_hm(root)}
    for repo, eps in results.items():
        (OUT / f"{repo}.json").write_text(json.dumps(eps, indent=2, ensure_ascii=False))
    print("Scanned raw API endpoints:",
          {r: len(eps) for r, eps in results.items()})
    print(f"Written to {OUT.relative_to(HERE)}/<repo>.json")


if __name__ == "__main__":
    main()
