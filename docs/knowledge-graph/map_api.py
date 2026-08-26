#!/usr/bin/env python3
"""Map raw scanned endpoints -> canonical (entity, operation) YAML nodes. NO LLM.

Reads data/api_raw/<repo>.json (from scan_api.py) and, using an explicit rule table
(namespace -> canonical entity; action-alias -> canonical operation), regenerates:
  - data/entities/*.yaml
  - data/operations/*.yaml

The rule table is the ONE place with human judgement; the scan itself is pure regex.
Only chat/agent-interaction core entities are modeled; everything else is ignored
(reported under "unmapped" so the table can be extended deliberately).

Design: DH and HM name endpoints as `entity.action` natively, so their namespace and
action are parsed directly. CP is REST, so URL+verb is mapped via CP_REST_RULES.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).parent
RAW = HERE / "data" / "api_raw"
ENT_DIR = HERE / "data" / "entities"
OP_DIR = HERE / "data" / "operations"

# canonical operation vocabulary (must match operation.schema.yaml enum)
CANON_OPS = {"create", "list", "get", "update", "delete", "send", "interrupt",
             "stream", "fork", "rename", "search", "select", "respond",
             "pause", "resume", "complete", "clear", "history"}

# namespace (DH/HM) -> canonical Entity label. Only core interaction entities.
NS_TO_ENTITY = {
    "session": "Session",
    "message": "Message", "prompt": "Message", "turn": "Message",
    "approval": "Permission", "approvals": "Permission",
    "model": "Model", "llm": "Model",
    "subagent": "Subagent", "subagents": "Subagent", "agents": "Subagent",
    "goal": "Goal",
    "skill": "Skill", "skills": "Skill",
    "agentPreset": "AgentPreset", "profile": "AgentPreset", "profiles": "AgentPreset",
    "workspace": "Workspace",
    "host": "File", "file": "File", "files": "File",
    "credentials": "Credential", "auth": "Credential",
    "settings": "Settings", "config": "Settings",
    "jobs": "Job", "background": "Job",
    "clipboard": "Attachment", "paste": "Attachment", "uploaded": "Attachment",
}

# action alias -> canonical operation. Anything not here falls back to the raw
# action if it is already a canonical op, else it is skipped (reported).
ACTION_ALIAS = {
    "create": "create", "new": "create", "set": "create", "start": "create",
    "list": "list", "active_list": "list", "all": "list",
    "get": "get", "read": "get", "info": "get", "history": "history", "describe": "get",
    "update": "update", "edit": "update", "mutate": "update", "replace": "update",
    "updateQueue": "update", "rename": "rename",
    "delete": "delete", "remove": "delete", "unset": "delete", "close": "delete",
    "archiveSession": "delete",
    "send": "send", "prompt": "send", "submit": "send", "deliver": "send",
    "interrupt": "interrupt", "cancel": "interrupt", "stop": "interrupt",
    "fork": "fork", "branch": "fork",
    "search": "search",
    "select": "select", "selectModel": "select", "selectmodel": "select",
    "models": "list", "discoverModels": "list", "providers": "list",
    "respond": "respond", "received": "respond",
    "pause": "pause", "resume": "resume", "complete": "complete", "clear": "clear",
    "listDirectory": "list", "openPath": "get", "attachment": "create",
    "createDirectory": "create",
    "manage": "update", "reload": "update", "save": "update",
}

# CP REST (url, verb) -> (Entity, operation). Explicit because REST has no entity.action.
CP_REST_RULES: dict[tuple[str, str], tuple[str, str]] = {
    ("/chat/sessions", "POST"): ("Session", "create"),
    ("/chat/sessions", "GET"): ("Session", "list"),
    ("/chat/sessions/[id]", "GET"): ("Session", "get"),
    ("/chat/sessions/[id]", "PATCH"): ("Session", "update"),
    ("/chat/sessions/[id]", "DELETE"): ("Session", "delete"),
    ("/chat/sessions/by-cwd", "GET"): ("Session", "search"),
    ("/chat/rewind", "POST"): ("Session", "fork"),
    ("/chat/interrupt", "POST"): ("Session", "interrupt"),
    ("/chat/messages", "POST"): ("Message", "send"),
    ("/chat/messages", "PUT"): ("Message", "update"),
    ("/chat/sessions/[id]/messages", "GET"): ("Message", "list"),
    ("/chat/structured", "POST"): ("Message", "stream"),
    ("/chat/permission", "POST"): ("Permission", "respond"),
    ("/chat/permission-capability", "GET"): ("Permission", "get"),
    ("/chat/model", "POST"): ("Model", "select"),
    ("/codex/models", "GET"): ("Model", "list"),
    ("/chat/sessions/[id]/subagent-runs", "GET"): ("Subagent", "list"),
    ("/files/browse", "GET"): ("Workspace", "list"),
    ("/files/mkdir", "POST"): ("Workspace", "create"),
    ("/files/delete", "POST"): ("File", "delete"),
    ("/files/raw", "GET"): ("File", "get"),
    ("/files/write", "POST"): ("File", "create"),
    ("/files/rename", "POST"): ("File", "update"),
    ("/assets/html-bundles", "POST"): ("Attachment", "create"),
    ("/assets/[id]", "GET"): ("Attachment", "get"),
    ("/assets/[id]", "DELETE"): ("Attachment", "delete"),
    ("/settings", "GET"): ("Settings", "get"),
    ("/settings", "PUT"): ("Settings", "update"),
    ("/claude-auth", "GET"): ("Credential", "get"),
    ("/claude-auth", "POST"): ("Credential", "update"),
    ("/media/jobs", "GET"): ("Job", "list"),
    ("/media/jobs", "POST"): ("Job", "create"),
}

# entity label -> per-repo display name (namespace as it appears in that repo).
ENTITY_DISPLAY = {
    "Session": {"CP": "chat/sessions", "DH": "session", "HM": "session"},
    "Message": {"CP": "chat/messages", "DH": "session.prompt", "HM": "prompt"},
    "Permission": {"CP": "chat/permission", "DH": "approvals", "HM": "approval"},
    "Model": {"CP": "codex/models", "DH": "llm/session.models", "HM": "model"},
    "Subagent": {"CP": "chat/sessions/[id]/subagent-runs", "DH": "subagent", "HM": "agents"},
    "Goal": {"DH": "goal", "HM": "goal"},
    "Skill": {"DH": "skill", "HM": "skills"},
    "AgentPreset": {"DH": "agentPreset", "HM": "profile"},
    "Workspace": {"CP": "files/browse", "DH": "workspace", "HM": "workspace"},
    "File": {"CP": "files", "DH": "host(fs)", "HM": "files"},
    "Attachment": {"CP": "assets", "DH": "session.attachment", "HM": "clipboard.paste"},
    "Settings": {"CP": "settings", "DH": "settings", "HM": "config"},
    "Credential": {"CP": "claude-auth", "DH": "credentials", "HM": "auth"},
    "Job": {"CP": "media/jobs", "DH": "jobs", "HM": "background"},
}


# per-entity whitelist of semantically valid operations. Filters out combinations
# like Session.send (that is really Message.send). An (entity, op) not listed here
# is dropped to unmapped, keeping the canonical model clean.
ENTITY_OPS = {
    "Session": {"create", "list", "get", "update", "delete", "fork", "interrupt", "search", "history"},
    "Message": {"send", "list", "update", "stream"},
    "Permission": {"respond", "get"},
    "Model": {"list", "select"},
    "Subagent": {"list", "send", "interrupt", "history"},
    "Goal": {"create", "update", "pause", "resume", "complete", "clear"},
    "Skill": {"list", "update"},
    "AgentPreset": {"list", "get", "select", "delete", "create"},
    "Workspace": {"create", "list", "delete", "rename"},
    "File": {"get", "list", "create", "update", "delete"},
    "Attachment": {"create", "get", "delete"},
    "Settings": {"get", "update"},
    "Credential": {"get", "update", "delete"},
    "Job": {"list", "create"},
}

# exact overrides where the wire namespace does not equal the semantic entity, or the
# action needs a specific canonical op. Key = raw method name, value = (Entity, op).
EXACT_OVERRIDE: dict[str, tuple[str, str]] = {
    "session.prompt": ("Message", "send"),
    "session.selectModel": ("Model", "select"),
    "session.models": ("Model", "list"),
    "session.attachment": ("Attachment", "create"),
    "session.updateQueue": ("Message", "update"),
    "session.history": ("Session", "history"),
    "workspace.archiveSession": ("Session", "delete"),
    "prompt.submit": ("Message", "send"),
    "message.start": ("Message", "stream"),
    "message.delta": ("Message", "stream"),
}


def norm_action(raw_action: str) -> str | None:
    a = ACTION_ALIAS.get(raw_action)
    if a:
        return a
    if raw_action in CANON_OPS:
        return raw_action
    return None


def map_rpc(name: str) -> tuple[str, str] | None:
    if name in EXACT_OVERRIDE:
        entity, op = EXACT_OVERRIDE[name]
    else:
        parts = name.split(".")
        ns, action = parts[0], parts[1] if len(parts) > 1 else ""
        entity = NS_TO_ENTITY.get(ns)
        if not entity:
            return None
        op = norm_action(action)
        if not op:
            return None
    # enforce per-entity operation whitelist
    if op not in ENTITY_OPS.get(entity, set()):
        return None
    return entity, op


def main() -> None:
    raw = {r: json.loads((RAW / f"{r}.json").read_text()) for r in ("CP", "DH", "HM")}

    # canonical (entity, op) -> {repo: endpoint dict}
    ops: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    unmapped: dict[str, list[str]] = {"CP": [], "DH": [], "HM": []}

    for ep in raw["CP"]:
        key = (ep["url"], ep["http"])
        rule = CP_REST_RULES.get(key)
        if not rule:
            unmapped["CP"].append(f"{ep['http']} {ep['url']}")
            continue
        entity, op = rule
        ops[(entity, op)]["CP"] = {"name": ep["url"], "http": ep["http"], "style": "REST"}

    for r in ("DH", "HM"):
        for ep in raw[r]:
            mapped = map_rpc(ep["name"])
            if not mapped:
                unmapped[r].append(ep["name"])
                continue
            entity, op = mapped
            # keep first mapping per (entity,op,repo); prefer exact action names
            ops[(entity, op)].setdefault(r, {"name": ep["name"], "style": ep["style"]})

    # entities referenced by at least one operation
    used_entities = {e for (e, _), m in ops.items() if m}

    # rewrite entity YAML
    ENT_DIR.mkdir(parents=True, exist_ok=True)
    for f in ENT_DIR.glob("*.yaml"):
        f.unlink()
    for entity in sorted(used_entities):
        names = {r: n for r, n in ENTITY_DISPLAY.get(entity, {}).items()}
        (ENT_DIR / f"{entity}.yaml").write_text(yaml.safe_dump(
            {"id": f"E:{entity}", "ntype": "entity", "label": entity, "names": names},
            sort_keys=False, allow_unicode=True))

    # rewrite operation YAML
    OP_DIR.mkdir(parents=True, exist_ok=True)
    for f in OP_DIR.glob("*.yaml"):
        f.unlink()
    for (entity, op), repo_eps in sorted(ops.items()):
        if not repo_eps:
            continue
        (OP_DIR / f"{entity}__{op}.yaml").write_text(yaml.safe_dump(
            {"id": f"O:{entity}.{op}", "ntype": "operation", "label": op,
             "entity": entity, "endpoints": dict(sorted(repo_eps.items()))},
            sort_keys=False, allow_unicode=True))

    print("Mapped canonical nodes:",
          {"entities": len(used_entities), "operations": len(ops)})
    print("Unmapped (not core interaction entities), counts:",
          {r: len(v) for r, v in unmapped.items()})
    (RAW / "unmapped.json").write_text(json.dumps(unmapped, indent=2, ensure_ascii=False))
    print(f"Unmapped detail -> {(RAW / 'unmapped.json').relative_to(HERE)}")


if __name__ == "__main__":
    main()
