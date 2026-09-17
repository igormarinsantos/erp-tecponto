---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 1
total_count: 2
last_updated: 2026-09-17T20:15:53.676Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 3 | unrun-verify | tecponto_app/tecponto/frontend/test_frontend_api.py |  | run_foundation_checks cannot currently complete end-to-end locally: run_technician_scope_checks (pre-existing, unrelated to 03-01) fails deterministically because upstream director/manager fixture functions deliver a Service Order for the shared Tecponto Tecnico user before line 316 runs, likely reproducible on fresh CI too. D-01/D-02 verified via standalone bench execute of each function instead. | fixed |  | 2026-09-14T22:59:34.249Z | 2026-09-17T20:14:51.884Z |
| 2 | 3 | unrun-verify | tecponto_app/tecponto/frontend/api.py | 1683 | complete_technical_diagnosis raises frappe.model.workflow.WorkflowTransitionError (Not a valid Workflow Action) when apply_workflow is called with the action name _get_allowed_kanban_action derives for Em diagnostico -> Diagnosticado - aguardando orcamento. Reproduced deterministically via standalone bench execute of run_diagnosis_handoff_checks, unrelated to any Phase 3 change (pre-existing code in workflow.py/api.py, not touched by AUDIT-01 through AUDIT-05). Hypothesis (not yet confirmed by a live DB query, container kept crashing before I could run one): the real Frappe Workflow doctype record for Service Order has drifted from the SERVICE_ORDER_TRANSITIONS python constant in tecponto_app/tecponto/workflow.py - whatever sync step is meant to keep them in lockstep during migrate/install may not be running or may have a bug. Needs a dedicated investigation with a stable container: compare the live Workflow doctype transitions child table against SERVICE_ORDER_TRANSITIONS for this exact from/to state pair. | open |  | 2026-09-17T20:15:53.676Z |  |

````json
[
  {
    "id": 1,
    "kind": "unrun-verify",
    "phase": "3",
    "file": "tecponto_app/tecponto/frontend/test_frontend_api.py",
    "line": null,
    "description": "run_foundation_checks cannot currently complete end-to-end locally: run_technician_scope_checks (pre-existing, unrelated to 03-01) fails deterministically because upstream director/manager fixture functions deliver a Service Order for the shared Tecponto Tecnico user before line 316 runs, likely reproducible on fresh CI too. D-01/D-02 verified via standalone bench execute of each function instead.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-09-14T22:59:34.249Z",
    "resolved_at": "2026-09-17T20:14:51.884Z"
  },
  {
    "id": 2,
    "kind": "unrun-verify",
    "phase": "3",
    "file": "tecponto_app/tecponto/frontend/api.py",
    "line": 1683,
    "description": "complete_technical_diagnosis raises frappe.model.workflow.WorkflowTransitionError (Not a valid Workflow Action) when apply_workflow is called with the action name _get_allowed_kanban_action derives for Em diagnostico -> Diagnosticado - aguardando orcamento. Reproduced deterministically via standalone bench execute of run_diagnosis_handoff_checks, unrelated to any Phase 3 change (pre-existing code in workflow.py/api.py, not touched by AUDIT-01 through AUDIT-05). Hypothesis (not yet confirmed by a live DB query, container kept crashing before I could run one): the real Frappe Workflow doctype record for Service Order has drifted from the SERVICE_ORDER_TRANSITIONS python constant in tecponto_app/tecponto/workflow.py - whatever sync step is meant to keep them in lockstep during migrate/install may not be running or may have a bug. Needs a dedicated investigation with a stable container: compare the live Workflow doctype transitions child table against SERVICE_ORDER_TRANSITIONS for this exact from/to state pair.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-17T20:15:53.676Z",
    "resolved_at": null
  }
]
````
