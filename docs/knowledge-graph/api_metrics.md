# Backend API Knowledge Graph -- Metrics

- Nodes: 66 (repos=3, entities=14, operations=49)
- Edges: 153

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
| delete | - | agentPreset.remove | - |
| get | - | agentPreset.read | - |
| list | - | agentPreset.list | profiles.list |
| select | - | agentPreset.select | profile.select |

### Attachment

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| create | /assets/html-bundles [POST] | session.attachment | clipboard.paste |
| delete | /assets/[id] [DELETE] | - | - |
| get | /assets/[id] [GET] | - | - |

### Credential

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| delete | - | credentials.unset | - |
| get | /claude-auth [GET] | credentials.describe | auth.json |
| update | /claude-auth [POST] | credentials.set | - |

### File

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| create | /files/write [POST] | - | - |
| delete | /files/delete [POST] | - | - |
| get | /files/raw [GET] | host.openPath | files.read |
| list | /files/browse [GET] | host.listDirectory | files.list |
| update | /files/rename [POST] | - | - |

### Goal

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| clear | - | goal.clear | goal.clear |
| complete | - | goal.complete | - |
| create | - | goal.create | goal.set |
| pause | - | goal.pause | - |
| resume | - | goal.resume | - |
| update | - | goal.edit | - |

### Job

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| create | /media/jobs [POST] | jobs.create | - |
| list | /media/jobs [GET] | jobs.list | background.list |

### Message

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| list | /chat/sessions/[id]/messages [GET] | session.history | - |
| send | /chat/messages [POST] | session.prompt | prompt.submit |
| stream | /chat/structured [POST] | session.prompt(stream) | message.delta |
| update | /chat/messages [PUT] | session.updateQueue | - |

### Model

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| list | /codex/models [GET] | llm.models | models.list |
| select | /chat/model [POST] | session.selectModel | agent.reasoning_effort |

### Permission

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| get | /chat/permission-capability [GET] | approvals.describe | approval.pending |
| respond | /chat/permission [POST] | approvals.respond | approval.respond |

### Session

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| create | /chat/sessions [POST] | session.create | session.create |
| delete | /chat/sessions/[id] [DELETE] | workspace.archiveSession | session.delete |
| fork | /chat/rewind [POST] | session.fork | - |
| get | /chat/sessions/[id] [GET] | session.history | session.info |
| interrupt | /chat/interrupt [POST] | session.cancel | session.interrupt |
| list | /chat/sessions [GET] | session.list | sessions.list |
| search | /chat/sessions/by-cwd [GET] | session.search | - |
| update | /chat/sessions/[id] [PATCH] | session.rename | session.rename |

### Settings

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| get | /settings [GET] | settings.describe | config.get |
| update | /settings [PUT] | settings.update | config.set |

### Skill

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| list | - | skill.list | skills.list |

### Subagent

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| history | - | subagent.history | - |
| interrupt | - | subagent.interrupt | - |
| list | /chat/sessions/[id]/subagent-runs [GET] | subagent.list | agents.list |
| send | - | subagent.prompt | - |

### Workspace

| operation | CP (url [method]) | DH (rpc) | HM (rpc) |
|---|---|---|---|
| create | /files/mkdir [POST] | workspace.create | - |
| delete | /files/delete [POST] | workspace.delete | - |
| list | /files/browse [GET] | host.listDirectory | complete.path |

## Per-repo API operation coverage

| repo | style | #operations exposed |
|---|---|---|
| CodePilot | REST | 34 |
| deepseek-harness | RPC | 44 |
| hermes-agent | WS-RPC | 26 |

Note: CP uses RESTful URL+HTTP-method; DH and HM use `entity.action` RPC naming (no URL/HTTP verb). All are normalized to canonical (entity, operation) nodes so the three shapes become comparable. Entity/op absence in a repo = no `exposes` edge.
