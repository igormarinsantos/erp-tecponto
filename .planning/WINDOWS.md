---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-09-14T22:59:34.249Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 3 | unrun-verify | tecponto_app/tecponto/frontend/test_frontend_api.py |  | run_foundation_checks cannot currently complete end-to-end locally: run_technician_scope_checks (pre-existing, unrelated to 03-01) fails deterministically because upstream director/manager fixture functions deliver a Service Order for the shared Tecponto Tecnico user before line 316 runs, likely reproducible on fresh CI too. D-01/D-02 verified via standalone bench execute of each function instead. | open |  | 2026-09-14T22:59:34.249Z |  |

````json
[
  {
    "id": 1,
    "kind": "unrun-verify",
    "phase": "3",
    "file": "tecponto_app/tecponto/frontend/test_frontend_api.py",
    "line": null,
    "description": "run_foundation_checks cannot currently complete end-to-end locally: run_technician_scope_checks (pre-existing, unrelated to 03-01) fails deterministically because upstream director/manager fixture functions deliver a Service Order for the shared Tecponto Tecnico user before line 316 runs, likely reproducible on fresh CI too. D-01/D-02 verified via standalone bench execute of each function instead.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-14T22:59:34.249Z",
    "resolved_at": null
  }
]
````
