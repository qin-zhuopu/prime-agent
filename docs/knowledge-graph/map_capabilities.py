#!/usr/bin/env python3
"""Normalize all 11 web UIs onto a shared USER-CAPABILITY layer. NO LLM.

Key idea (per user): every one of these is a web UI *for humans*, so regardless of the
backend shape (REST / RPC / WS / SDK-hook / protocol), the user-facing operations are
the same and CAN be normalized. A `capability` is one thing a user can do (start a
session, send a message, approve a permission, pick a model, view a tool call, ...).

Each repo IMPLEMENTS a capability via some surface, recorded as evidence:
  surface_kind: endpoint | rpc | ws-rpc | sdk-hook | component | protocol
  surface_name: the concrete route/method/hook/component that provides it

Evidence sources (all mechanical / from scanned data, no judgement beyond the mapping table):
  - CP/DH/HM: reuse data/operations/*.yaml endpoints (already scanned)
  - survey repos: hook names (data/full/signals_<repo>.txt) + known component names

Output: data/capabilities/*.yaml (one per capability), each listing per-repo evidence.
This lets the unified graph compare ALL 11 repos on the same axis.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

HERE = Path(__file__).parent
DATA = HERE / "data"
CAP_DIR = DATA / "capabilities"

REPOS = ["CP", "DH", "HM", "ACPC", "ACPUI", "ASTUI", "OCUI", "OGUI", "CKIT", "ACHAT", "ACPWG"]

# canonical user capabilities (what a user can DO in the chat/agent UI)
CAPABILITIES = {
    "start-session":   "Create / start a conversation session",
    "list-sessions":   "Browse and switch between sessions",
    "send-message":    "Send a prompt / message to the agent",
    "stream-response": "Receive streaming assistant output",
    "stop-generation": "Interrupt / cancel a running turn",
    "view-reasoning":  "See the agent's thinking / reasoning",
    "view-tool-call":  "See tool calls, args and results",
    "approve-permission": "Approve / deny a permission request",
    "pick-model":      "Choose the model",
    "set-mode-effort": "Set mode / reasoning effort",
    "attach-file":     "Attach files / images / paste",
    "mention-ref":     "@-mention files or references",
    "slash-command":   "Run slash commands",
    "view-diff":       "View file diffs produced by tools",
    "browse-files":    "Browse workspace / file tree",
    "manage-todos":    "See task / todo list",
    "manage-subagents":"See / navigate subagents",
    "edit-message":    "Edit / copy / retry a message",
    "message-feedback":"Thumbs up/down feedback",
    "manage-skills":   "Manage skills",
    "manage-mcp":      "Manage MCP servers / toolsets",
    "connect-status":  "See connection / runtime status",
}

# Per-repo evidence: capability -> repo -> (surface_kind, surface_name) or None if absent.
# For CP/DH/HM the surface_name references the real endpoint (from earlier scans).
# For survey repos it references the real hook or component found in the source.
# None = capability not present in that repo.
M: dict[str, dict[str, tuple[str, str] | None]] = {
    "start-session": {
        "CP": ("endpoint", "POST /chat/sessions"), "DH": ("rpc", "session.create"),
        "HM": ("ws-rpc", "session.create"), "ACPC": ("sdk-hook", "useSession"),
        "ACPUI": ("component", "SessionList"), "ASTUI": ("sdk-hook", "useThreadRuntime"),
        "OCUI": ("component", "SessionList"), "OGUI": ("sdk-hook", "useChatSessionSurface"),
        "CKIT": ("sdk-hook", "use-agent"), "ACHAT": ("sdk-hook", "useChatRuntime"),
        "ACPWG": ("ws-rpc", "session.new"),
    },
    "list-sessions": {
        "CP": ("endpoint", "GET /chat/sessions"), "DH": ("rpc", "session.list"),
        "HM": ("ws-rpc", "sessions.list"), "ACPC": ("sdk-hook", "useSessions"),
        "ACPUI": ("component", "SessionList"), "ASTUI": ("sdk-hook", "useThreadListRuntime"),
        "OCUI": ("component", "SessionList"), "OGUI": ("sdk-hook", "useActiveSessionQueue"),
        "CKIT": None, "ACHAT": ("sdk-hook", "useAgentRegistry"),
        "ACPWG": ("ws-rpc", "session.list"),
    },
    "send-message": {
        "CP": ("endpoint", "POST /chat/messages"), "DH": ("rpc", "session.prompt"),
        "HM": ("ws-rpc", "prompt.submit"), "ACPC": ("sdk-hook", "usePrompt"),
        "ACPUI": ("component", "ChatView"), "ASTUI": ("sdk-hook", "useComposerRuntime"),
        "OCUI": ("component", "MessageDisplay"), "OGUI": ("sdk-hook", "use-prompt-draft"),
        "CKIT": ("sdk-hook", "use-ask-copilot"), "ACHAT": ("sdk-hook", "useComposerState"),
        "ACPWG": ("ws-rpc", "session.prompt"),
    },
    "stream-response": {
        "CP": ("endpoint", "POST /chat/structured"), "DH": ("rpc", "session.prompt(stream)"),
        "HM": ("ws-rpc", "message.delta"), "ACPC": ("sdk-hook", "useToolCalls"),
        "ACPUI": ("component", "ChatView"), "ASTUI": ("sdk-hook", "useMessageRuntime"),
        "OCUI": ("component", "MessageDisplay"), "OGUI": ("sdk-hook", "use-agent-state"),
        "CKIT": ("protocol", "AG-UI events"), "ACHAT": ("sdk-hook", "useChatRuntime"),
        "ACPWG": ("ws-rpc", "session.update"),
    },
    "stop-generation": {
        "CP": ("endpoint", "POST /chat/interrupt"), "DH": ("rpc", "session.cancel"),
        "HM": ("ws-rpc", "session.interrupt"), "ACPC": ("sdk-hook", "useSession"),
        "ACPUI": ("component", "ChatView"), "ASTUI": ("sdk-hook", "useActionBarStop"),
        "OCUI": None, "OGUI": ("sdk-hook", "use-agent-state"),
        "CKIT": ("sdk-hook", "use-agent"), "ACHAT": ("sdk-hook", "useChatRuntime"),
        "ACPWG": ("ws-rpc", "session.cancel"),
    },
    "view-reasoning": {
        "CP": ("component", "reasoning.tsx"), "DH": ("component", "ReasoningRow"),
        "HM": ("component", "terminal"), "ACPC": None, "ACPUI": None,
        "ASTUI": ("component", "Reasoning"), "OCUI": ("component", "MessageDisplay"),
        "OGUI": ("component", "MessageList"), "CKIT": None, "ACHAT": None, "ACPWG": None,
    },
    "view-tool-call": {
        "CP": ("component", "tool.tsx"), "DH": ("component", "ToolRow"),
        "HM": ("component", "terminal"), "ACPC": ("sdk-hook", "useToolCalls"),
        "ACPUI": ("component", "ToolCallCard"), "ASTUI": ("component", "ToolFallback"),
        "OCUI": ("component", "ToolCall"), "OGUI": ("component", "tool-view"),
        "CKIT": ("sdk-hook", "use-render-tool-call"), "ACHAT": ("component", "ToolCall"),
        "ACPWG": ("ws-rpc", "tool.call"),
    },
    "approve-permission": {
        "CP": ("endpoint", "POST /chat/permission"), "DH": ("rpc", "approvals.respond"),
        "HM": ("ws-rpc", "approval.respond"), "ACPC": ("sdk-hook", "usePermission"),
        "ACPUI": ("component", "PermissionDialog"), "ASTUI": None,
        "OCUI": ("component", "PermissionModal"), "OGUI": ("component", "permission"),
        "CKIT": None, "ACHAT": ("component", "PermissionPrompt"),
        "ACPWG": ("ws-rpc", "session.request_permission"),
    },
    "pick-model": {
        "CP": ("endpoint", "POST /chat/model"), "DH": ("rpc", "session.selectModel"),
        "HM": ("ws-rpc", "model.select"), "ACPC": None,
        "ACPUI": ("component", "ModelPicker"), "ASTUI": ("sdk-hook", "useModelConfig"),
        "OCUI": ("component", "ModelSelector"), "OGUI": ("sdk-hook", "use-agent-variant-core"),
        "CKIT": None, "ACHAT": ("component", "AgentSelector"),
        "ACPWG": None,
    },
    "set-mode-effort": {
        "CP": ("endpoint", "POST /chat/mode"), "DH": ("component", "submission-settings"),
        "HM": ("ws-rpc", "agent.reasoning_effort"), "ACPC": None,
        "ACPUI": ("component", "ModePicker"), "ASTUI": None, "OCUI": None,
        "OGUI": ("sdk-hook", "use-agent-variant-core"), "CKIT": None,
        "ACHAT": None, "ACPWG": None,
    },
    "attach-file": {
        "CP": ("endpoint", "POST /assets/html-bundles"), "DH": ("rpc", "session.attachment"),
        "HM": ("ws-rpc", "clipboard.paste"), "ACPC": None,
        "ACPUI": None, "ASTUI": ("sdk-hook", "use-attachments"),
        "OCUI": None, "OGUI": ("sdk-hook", "use-prompt-files"),
        "CKIT": ("sdk-hook", "use-attachments"), "ACHAT": None, "ACPWG": None,
    },
    "mention-ref": {
        "CP": ("component", "MessageInputParts"), "DH": ("component", "ReferenceIcon"),
        "HM": None, "ACPC": None, "ACPUI": None, "ASTUI": None, "OCUI": None,
        "OGUI": ("sdk-hook", "use-file-mention"), "CKIT": None,
        "ACHAT": None, "ACPWG": None,
    },
    "slash-command": {
        "CP": ("component", "SlashCommandPopover"), "DH": ("rpc", "commands.catalog"),
        "HM": ("component", "SlashPopover"), "ACPC": None, "ACPUI": ("component", "CommandPalette"),
        "ASTUI": None, "OCUI": None, "OGUI": None, "CKIT": None,
        "ACHAT": ("sdk-hook", "useSlashCommands"), "ACPWG": None,
    },
    "view-diff": {
        "CP": ("component", "DiffSummary"), "DH": ("component", "DiffBlock"),
        "HM": ("component", "terminal"), "ACPC": None, "ACPUI": None, "ASTUI": None,
        "OCUI": ("component", "DiffViewer"), "OGUI": ("component", "diff-view"),
        "CKIT": None, "ACHAT": ("sdk-hook", "useLiveEditorSelection"), "ACPWG": None,
    },
    "browse-files": {
        "CP": ("endpoint", "GET /files/browse"), "DH": ("rpc", "host.listDirectory"),
        "HM": ("ws-rpc", "files.list"), "ACPC": ("sdk-hook", "useFileTree"),
        "ACPUI": None, "ASTUI": None, "OCUI": ("component", "DirectoryTree"),
        "OGUI": ("sdk-hook", "use-file-mention"), "CKIT": None,
        "ACHAT": ("sdk-hook", "useFileWorkspaceState"), "ACPWG": None,
    },
    "manage-todos": {
        "CP": ("component", "TaskRunMarker"), "DH": ("component", "TodoPanel"),
        "HM": ("component", "terminal"), "ACPC": None, "ACPUI": None, "ASTUI": None,
        "OCUI": ("component", "TodoList"), "OGUI": None, "CKIT": None,
        "ACHAT": ("sdk-hook", "useSchedules"), "ACPWG": None,
    },
    "manage-subagents": {
        "CP": ("component", "SubagentCard"), "DH": ("rpc", "subagent.list"),
        "HM": ("ws-rpc", "agents.list"), "ACPC": None, "ACPUI": None, "ASTUI": None,
        "OCUI": None, "OGUI": None, "CKIT": ("sdk-hook", "use-coagent"),
        "ACHAT": ("sdk-hook", "useAgentRegistry"), "ACPWG": None,
    },
    "edit-message": {
        "CP": ("component", "MessageIconActions"), "DH": ("component", "MessageIconActions"),
        "HM": ("component", "clipboard"), "ACPC": ("sdk-hook", "useCopy"),
        "ACPUI": None, "ASTUI": ("sdk-hook", "useActionBarEdit"),
        "OCUI": None, "OGUI": None, "CKIT": None, "ACHAT": None, "ACPWG": None,
    },
    "message-feedback": {
        "CP": None, "DH": ("component", "ui-message-feedback"), "HM": None,
        "ACPC": None, "ACPUI": None, "ASTUI": ("sdk-hook", "useActionBarFeedback"),
        "OCUI": None, "OGUI": None, "CKIT": None, "ACHAT": None, "ACPWG": None,
    },
    "manage-skills": {
        "CP": ("endpoint", "GET /skills"), "DH": ("rpc", "skill.list"),
        "HM": ("ws-rpc", "skills.list"), "ACPC": ("sdk-hook", "useSkills"),
        "ACPUI": None, "ASTUI": None, "OCUI": None, "OGUI": None, "CKIT": None,
        "ACHAT": None, "ACPWG": None,
    },
    "manage-mcp": {
        "CP": ("endpoint", "GET /codex/mcp/[server]"), "DH": None,
        "HM": ("ws-rpc", "mcp.manage"), "ACPC": None, "ACPUI": None, "ASTUI": None,
        "OCUI": None, "OGUI": None, "CKIT": ("sdk-hook", "use-mcp"),
        "ACHAT": None, "ACPWG": None,
    },
    "connect-status": {
        "CP": ("component", "ConnectionBanner"), "DH": ("component", "ConnectionBanner"),
        "HM": ("sdk-hook", "useSidebarStatus"), "ACPC": ("sdk-hook", "useConnectionStatus"),
        "ACPUI": ("component", "StartupProgress"), "ASTUI": ("sdk-hook", "useThreadRuntime"),
        "OCUI": ("component", "ConnectionStatus"), "OGUI": ("sdk-hook", "use-agent-backend"),
        "CKIT": ("sdk-hook", "use-copilot-runtime"), "ACHAT": ("sdk-hook", "useChatRuntime"),
        "ACPWG": ("component", "StatusBar"),
    },
}


def main() -> None:
    CAP_DIR.mkdir(parents=True, exist_ok=True)
    for f in CAP_DIR.glob("*.yaml"):
        f.unlink()
    for cap, desc in CAPABILITIES.items():
        impls = {}
        for rid in REPOS:
            ev = M.get(cap, {}).get(rid)
            if ev:
                impls[rid] = {"surface_kind": ev[0], "surface_name": ev[1]}
        (CAP_DIR / f"{cap}.yaml").write_text(yaml.safe_dump(
            {"id": f"CAP:{cap}", "ntype": "capability", "label": cap,
             "description": desc, "implementations": dict(sorted(impls.items()))},
            sort_keys=False, allow_unicode=True))
    # coverage summary
    cov = {rid: sum(1 for cap in CAPABILITIES if M.get(cap, {}).get(rid)) for rid in REPOS}
    print(f"Capabilities: {len(CAPABILITIES)}, repos: {len(REPOS)}")
    print("Per-repo capability coverage:", dict(sorted(cov.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
