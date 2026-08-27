# Knowledge-graph data quality report

> Tiers are EMERGENT (derive_tier.py), not hand-assigned: repos cluster by feature coverage at the largest natural gap (=29). The 'deep' cluster (CP, DH, HM) also happens to be the set whose source was read in full; 'broad' repos (ACHAT, ACPC, ACPUI, ACPWG, ASTUI, CKIT, OCUI, OGUI) have UI-feature breadth only, so their absent API/call layers below are expected, not defects.

repos=11 (deep=3, broad=8), protocols=7, capabilities=22, features=73, entities=14, operations=57, schemas=12

## ERROR (must fix) (0)

## WARN (should fill) (0)

## INFO (by design / expected) (25)
  - schema: 9 graph node types, all have schema files (api, category, component, entity, feature, operation, protocol, repo, webui)
  - coverage: repo ACHAT (broad) has NO API entity/operation data
  - coverage: repo ACPC (broad) has NO API entity/operation data
  - coverage: repo ACPUI (broad) has NO API entity/operation data
  - coverage: repo ACPWG (broad) has NO API entity/operation data
  - coverage: repo ASTUI (broad) has NO API entity/operation data
  - coverage: repo CKIT (broad) has NO API entity/operation data
  - coverage: repo OCUI (broad) has NO API entity/operation data
  - coverage: repo OGUI (broad) has NO API entity/operation data
  - coverage: repo ACHAT (broad) has NO frontend-call data
  - coverage: repo ACPC (broad) has NO frontend-call data
  - coverage: repo ACPUI (broad) has NO frontend-call data
  - coverage: repo ACPWG (broad) has NO frontend-call data
  - coverage: repo ASTUI (broad) has NO frontend-call data
  - coverage: repo CKIT (broad) has NO frontend-call data
  - coverage: repo OCUI (broad) has NO frontend-call data
  - coverage: repo OGUI (broad) has NO frontend-call data
  - api: entity AgentPreset has no name in ['CP'] (absent there, or unmapped)
  - api: entity Goal has no name in ['CP'] (absent there, or unmapped)
  - api: entity Skill has no name in ['CP'] (absent there, or unmapped)
  - calls: 30 operations have no resolved frontend call (may be server-internal, event-only, or scanner gap)
  - capability: 22 normalized user capabilities across all 11 repos; coverage CP=21, DH=21, HM=20, OGUI=15, ACHAT=14, ASTUI=12, OCUI=12, ACPC=11, ACPUI=11, CKIT=9, ACPWG=8
  - full: CP has 250 endpoints (187 distinct), 148 called by frontend, 39 server-internal (no frontend caller)
  - full: DH has 53 endpoints (53 distinct), 17 called by frontend, 36 server-internal (no frontend caller)
  - full: HM has 299 endpoints (299 distinct), 10 called by frontend, 289 server-internal (no frontend caller)

Summary: 0 errors, 0 warnings, 25 infos
