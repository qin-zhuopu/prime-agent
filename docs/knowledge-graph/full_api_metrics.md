# Full backend-endpoint + frontend-page graph -- Metrics

- Nodes: 902 (repos=3, groups=132, endpoints=602, pages=165)
- Edges: 1387

## Per-repo endpoint & page coverage

| repo | endpoints | groups | pages calling API | endpoints hit | server-internal (0 callers) |
|---|---|---|---|---|---|
| CodePilot | 250 | 31 | 155 | 194 | 56 |
| deepseek-harness | 53 | 10 | 4 | 17 | 36 |
| hermes-agent | 299 | 91 | 6 | 10 | 289 |

## Endpoint groups per repo (top by endpoint count)

- **CodePilot** (31 groups): settings(28), providers(24), media(22), chat(18), tasks(18), workspace(18), files(13), harness-home(12), codex(11), cli-tools(10), plugins(10), skills(10)
- **deepseek-harness** (10 groups): session(12), workspace(8), agentPreset(6), goal(6), host(5), settings(5), subagent(4), credentials(3), llm(3), skill(1)
- **hermes-agent** (91 groups): session(32), pet(18), projects(15), display(12), mcp(10), wake(9), browser(7), preview(7), subagent(7), billing(6), model(6), profiles(6)

## Most-called endpoints (by #calling pages)

| endpoint | repo | #pages |
|---|---|---|
| GET /providers/models | CP | 18 |
| DELETE /chat/sessions/[id] | CP | 12 |
| GET /chat/sessions/[id] | CP | 12 |
| PATCH /chat/sessions/[id] | CP | 12 |
| GET /settings/app | CP | 10 |
| PUT /settings/app | CP | 10 |
| GET /setup | CP | 9 |
| PUT /setup | CP | 9 |
| GET /media/serve | CP | 9 |
| GET /providers/options | CP | 8 |
| PUT /providers/options | CP | 8 |
| GET /chat/sessions/[id]/messages | CP | 8 |

Architectural signal: CP fans endpoint calls across many component files (REST, direct fetch); DH concentrates method-name literals in its connection layer (typed service contract, Cordis); HM exposes many endpoints but routes most interaction through the PTY terminal, so few have structured frontend callers.
