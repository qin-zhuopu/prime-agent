# Backend API Knowledge Graph -- Metrics

- Nodes: 117 (repos=3, entities=14, operations=57)
- Edges: 214

## Entity naming across repos

| entity | CodePilot (REST) | deepseek-harness (RPC) | hermes-agent (WS-RPC) |
|---|---|---|---|
| AgentPreset | - | agentPreset | profile |
| Attachment | assets | session.attachment | clipboard.paste |
| Credential | claude-auth | credentials | auth |
| File | files | host(fs) | files |
| Goal | - | goal | goal |
| Job | media/jobs | jobs | background |
| Message | chat/messages | session.prompt | prompt |
| Model | codex/models | llm/session.models | model |
| Permission | chat/permission | approvals | approval |
| Session | chat/sessions | session | session |
| Settings | settings | settings | config |
| Skill | - | skill | skills |
| Subagent | chat/sessions/[id]/subagent-runs | subagent | agents |
| Workspace | files/browse | workspace | workspace |

## Operations per entity (with per-repo endpoint)

### AgentPreset

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| create | - | - | profiles.create |
| delete | - | agentPreset.remove | - |
| get | - | agentPreset.read | profiles.describe |
| list | - | agentPreset.list | profiles.list |
| select | - | agentPreset.select | - |

### Attachment

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| create | /assets/html-bundles [POST] | session.attachment | - |
| get | /assets/[id] [GET] | - | - |

### Credential

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| delete | - | credentials.unset | - |
| get | /claude-auth [GET] | credentials.describe | - |

### File

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| create | /files/write [POST] | host.createDirectory | - |
| delete | /files/delete [POST] | - | - |
| get | /files/raw [GET] | host.describe | - |
| list | - | host.listDirectory | - |
| update | /files/rename [POST] | - | - |

### Goal

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| clear | - | goal.clear | - |
| complete | - | goal.complete | - |
| create | - | goal.create | - |
| pause | - | goal.pause | - |
| resume | - | goal.resume | - |
| update | - | goal.edit | - |

### Job

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| create | /media/jobs [POST] | - | - |
| list | /media/jobs [GET] | - | - |

### Message

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| list | /chat/sessions/[id]/messages [GET] | - | - |
| send | /chat/messages [POST] | session.prompt | prompt.submit |
| stream | /chat/structured [POST] | - | message.delta |
| update | /chat/messages [PUT] | session.updateQueue | - |

### Model

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| list | /codex/models [GET] | session.models | - |
| select | /chat/model [POST] | session.selectModel | - |

### Permission

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| get | /chat/permission-capability [GET] | - | - |
| respond | /chat/permission [POST] | - | approval.received |

### Session

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| compress | - | - | session.compress |
| create | /chat/sessions [POST] | session.create | session.create |
| delete | /chat/sessions/[id] [DELETE] | workspace.archiveSession | session.close |
| fork | /chat/rewind [POST] | session.fork | session.branch |
| get | /chat/sessions/[id] [GET] | - | session.info |
| history | - | session.history | session.history |
| interrupt | /chat/interrupt [POST] | session.cancel | session.interrupt |
| list | /chat/sessions [GET] | session.list | session.active_list |
| rename | - | session.rename | session.title |
| reset | - | - | session.reset |
| search | /chat/sessions/by-cwd [GET] | session.search | - |
| steer | - | - | session.steer |
| undo | - | - | session.undo |
| update | /chat/sessions/[id] [PATCH] | - | session.save |
| usage | - | - | session.usage |

### Settings

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| get | /settings [GET] | settings.describe | config.get |
| update | /settings [PUT] | settings.update | - |

### Skill

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| list | - | skill.list | - |
| update | - | - | skills.manage |

### Subagent

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| history | - | subagent.history | - |
| interrupt | - | subagent.interrupt | subagent.interrupt |
| list | /chat/sessions/[id]/subagent-runs [GET] | subagent.list | agents.list |
| send | - | subagent.prompt | - |

### Workspace

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| create | /files/mkdir [POST] | workspace.create | - |
| delete | - | workspace.delete | - |
| list | /files/browse [GET] | workspace.list | - |
| rename | - | workspace.rename | - |

## Per-repo API operation coverage

| repo | style | #operations exposed |
|---|---|---|
| CodePilot | REST | 30 |
| deepseek-harness | RPC | 39 |
| hermes-agent | WS-RPC | 24 |

Note: CP uses RESTful URL+HTTP-method; DH and HM use `entity.action` RPC naming (no URL/HTTP verb). All are normalized to canonical (entity, operation) nodes so the three shapes become comparable. Entity/op absence in a repo = no `exposes` edge.

## Frontend call references (component/page -> operation)

Built by scanning frontend source for endpoint calls (scan_frontend_calls.py); tests/fixtures excluded.

| repo | caller files | call edges |
|---|---|---|
| CodePilot | 39 | 52 |
| deepseek-harness | 2 | 7 |
| hermes-agent | 2 | 5 |

Most-referenced operations (by #calling files across repos):

| operation | #call edges |
|---|---|
| Session.list | 17 |
| File.get | 6 |
| Permission.respond | 4 |
| Workspace.list | 3 |
| Message.list | 3 |
| Model.list | 3 |
| Settings.update | 3 |
| Session.interrupt | 3 |

Architectural signal: CP components fetch endpoints directly (calls spread across many component files); DH concentrates RPC in its runtime/connection layer (few files, Cordis contract-driven); HM routes most interaction through the PTY terminal, so few structured RPC call sites appear.
