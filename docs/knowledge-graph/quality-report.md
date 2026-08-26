# Knowledge-graph data quality report

> Scope by design: primary repos (CP/DH/HM) get full depth (UI features + API entities/operations + frontend call refs, source-verified). Survey repos get UI-feature breadth only (README/structure-declared); their API/call layers are intentionally not mined. INFO items below are expected consequences of that scope, not defects.

repos=11 (primary=3, survey=8), protocols=7, features=73, entities=14, operations=51, schemas=7

## ERROR (must fix) (0)

## WARN (should fill) (0)

## INFO (by design / expected) (21)
  - schema: 7 graph node types, all have schema files (category, component, entity, feature, operation, protocol, repo)
  - coverage: repo ACHAT (survey) has NO API entity/operation data
  - coverage: repo ACPC (survey) has NO API entity/operation data
  - coverage: repo ACPUI (survey) has NO API entity/operation data
  - coverage: repo ACPWG (survey) has NO API entity/operation data
  - coverage: repo ASTUI (survey) has NO API entity/operation data
  - coverage: repo CKIT (survey) has NO API entity/operation data
  - coverage: repo OCUI (survey) has NO API entity/operation data
  - coverage: repo OGUI (survey) has NO API entity/operation data
  - coverage: repo ACHAT (survey) has NO frontend-call data
  - coverage: repo ACPC (survey) has NO frontend-call data
  - coverage: repo ACPUI (survey) has NO frontend-call data
  - coverage: repo ACPWG (survey) has NO frontend-call data
  - coverage: repo ASTUI (survey) has NO frontend-call data
  - coverage: repo CKIT (survey) has NO frontend-call data
  - coverage: repo OCUI (survey) has NO frontend-call data
  - coverage: repo OGUI (survey) has NO frontend-call data
  - api: entity AgentPreset has no name in ['CP'] (absent there, or unmapped)
  - api: entity Goal has no name in ['CP'] (absent there, or unmapped)
  - api: entity Skill has no name in ['CP'] (absent there, or unmapped)
  - calls: 24 operations have no resolved frontend call (may be server-internal, event-only, or scanner gap)

Summary: 0 errors, 0 warnings, 21 infos
