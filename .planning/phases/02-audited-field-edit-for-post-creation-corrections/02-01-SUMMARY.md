---
phase: 02-audited-field-edit-for-post-creation-corrections
plan: 01
subsystem: auth
tags: [frappe, python, react, typescript, audit-log, tecponto-access-audit]

# Dependency graph
requires:
  - phase: 03 (Systematic Audit)
    provides: precedent for role-free reader + role-gated caller pattern (is_warranty_active), and the run_*_checks() test convention
provides:
  - Migrated Tecponto Access Audit doctype (affected_user optional, reference_doctype/reference_name Dynamic Link pair)
  - Widened _write_audit; new audit_reference_field_edit and get_latest_reference_audit helpers in user_access.py
  - update_service_order_entry writes an os_contact_edit audit row (before/after, no-op short-circuit)
  - entry_audit key on get_service_order_detail, gated to System Manager/Tecponto Gestor/Tecponto Diretor via AUDIT_INDICATOR_ROLES
  - ReferenceAuditIndicator TS type + "Entrada editada por ... em ..." indicator on the entrada stage screen
  - run_edit_audit_checks() wired into run_foundation_checks, proving EDIT-01 end to end plus D-01/D-02/D-04/D-05/D-06/D-07
affects: [02-02 (device credential edit), 02-03 (customer identity edit)]

# Actuals (#2632)
actuals:
  tokens: 5252
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Generic reference_doctype/reference_name Dynamic Link pair on a shared audit doctype, extending rather than duplicating (D-01)"
    - "Role-free audit reader (get_latest_reference_audit) with the role gate living at the api.py call site (AUDIT_INDICATOR_ROLES), mirroring is_warranty_active's precedent"

key-files:
  created: []
  modified:
    - tecponto_app/tecponto/doctype/tecponto_access_audit/tecponto_access_audit.json
    - tecponto_app/tecponto/user_access.py
    - tecponto_app/tecponto/frontend/api.py
    - tecponto_app/tecponto/frontend/test_frontend_api.py
    - frontend/src/api/types.ts
    - frontend/src/App.tsx

key-decisions:
  - "Task 1 checkpoint (one-way schema migration: relax affected_user reqd, add reference_doctype/reference_name) was approved by the developer in a prior session ('Aprovar e seguir') before this executor run began; no file was touched until that approval existed."
  - "Task 2 and Task 3 each landed as a single atomic commit per the plan's own explicit <done> instruction, even though Task 2 carries tdd=\"true\" — the test (run_edit_audit_checks) was written and run to failure before any production code existed, then production code was added until it passed, then committed once, matching this project's established squash-to-one-commit-per-task convention (see prior 01-03/01-04 summaries)."

patterns-established:
  - "audit_reference_field_edit(*, change_type, reference_doctype, reference_name, before, after) is now the single entry point for EDIT-01/02/03 audit writes — 02-02 and 02-03 call this directly, never _write_audit."

requirements-completed: [EDIT-01]

coverage:
  - id: D1
    description: "An Atendente/Gestor edit of os_contact_name/os_contact_phone on an open OS writes exactly one Tecponto Access Audit row (change_type=os_contact_edit, actor=session user, real before/after contact values); a no-op edit writes nothing"
    requirement: "EDIT-01"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Tests 1-3)"
        status: pass
    human_judgment: false
  - id: D2
    description: "get_service_order_detail exposes entry_audit (actor/change_type/occurred_on) to System Manager/Gestor/Diretor and null to every other role, including Tecnico"
    requirement: "EDIT-01"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Test 4)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The migrated Tecponto Access Audit row remains immutable (save/delete both raise frappe.PermissionError) and a Tecnico is rejected from update_service_order_entry"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Tests 5-6)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Existing User-scoped audit callers (audit_password_change etc.) keep working unchanged after _write_audit is widened, and never populate reference_doctype/reference_name"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Test 7)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Gestor sees an 'Entrada editada por X em Y' line on the entrada stage screen when the OS has an audited edit; Atendente/Tecnico see nothing; frontend typechecks and builds"
    requirement: "EDIT-01"
    verification:
      - kind: unit
        ref: "npm --prefix frontend run build (tsc --noEmit + vite build + verify-foundation.mjs)"
        status: pass
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (App.tsx source-marker assertions: 'detail.entry_audit', 'Entrada editada por')"
        status: pass
    human_judgment: true
    rationale: "Visual placement/copy of the indicator inside the entrada stage screen is functional-first per GEMINI.md §3 (polish deferred to the Phase 4 design pass) — a human should eyeball the real render once, since source markers only prove the wiring exists, not that it reads well."

duration: ~50min
completed: 2026-09-18
status: complete
---

# Phase 2 Plan 1: Audited Field-Edit for Post-Creation Corrections — OS Contact Edit Summary

**EDIT-01 tracer slice shipped: an Atendente/Gestor's OS contact (name/phone) correction is written to a migrated `Tecponto Access Audit` row keyed to the Service Order (not a User), and a Gestor/Diretor sees "Entrada editada por X em Y" on the OS detail screen.**

## Performance

- **Duration:** ~50 min (this executor run; Task 1's checkpoint decision was approved by the developer in an earlier session before this run started)
- **Completed:** 2026-09-18
- **Tasks:** 3 (Task 1 checkpoint decision + Task 2 tracer + Task 3 UI close-out)
- **Files modified:** 6

## Accomplishments
- Migrated the `Tecponto Access Audit` doctype: `affected_user` is now optional, and two new fields (`reference_doctype` Link→DocType, `reference_name` Dynamic Link→`reference_doctype`) let a row point at a Service Order or Customer instead of only a User — `permissions`, `track_changes`, and `hooks.py`'s immutability hooks are byte-identical to before.
- Widened `_write_audit` (keyword-only, backward compatible) and added two new public helpers in `user_access.py`: `audit_reference_field_edit` (the single write entry point for EDIT-01/02/03) and `get_latest_reference_audit` (a role-free reader, mirroring the `is_warranty_active` precedent).
- Wired `update_service_order_entry` to capture before/after `os_contact_name`/`os_contact_phone` and write an `os_contact_edit` audit row only when the values actually changed — no justification/reason field added (D-06).
- Added `AUDIT_INDICATOR_ROLES` and `_serialize_reference_audit` to `api.py`; `get_service_order_detail` now returns `entry_audit` (actor/change_type/occurred_on) to System Manager/Gestor/Diretor and `None` to everyone else, including Tecnico (D-07).
- Added `run_edit_audit_checks()` to `test_frontend_api.py` (wired into `run_foundation_checks`) proving: the happy path with before/after fidelity, the no-op short-circuit, the Gestor/Atendente read-gate split, immutability surviving the schema migration (both `.save()` and `frappe.delete_doc` raise `frappe.PermissionError`), the Tecnico role rejection (D-05), and that the pre-existing `audit_password_change` User-scoped path still works unchanged after the widening (D-01).
- Added `ReferenceAuditIndicator` to `frontend/src/api/types.ts` and rendered "Entrada editada por {actor} em {data}" under the Cliente `IdentityCard` on the entrada stage screen, reusing the existing `formatDate` helper; pinned with App.tsx source-marker assertions inside `run_edit_audit_checks` since there is no frontend test runner.

## Task Commits

1. **Task 1: Decision gate — migrating the Tecponto Access Audit schema** — approved by the developer in a prior session ("Aprovar e seguir"); no commit of its own (decision-only task, recorded here per the plan's `<done>` requirement).
2. **Task 2: Tracer — OS contact edit writes an audited Service Order row, end to end through the backend** — `6b538df` (feat)
3. **Task 3: Close the tracer at the UI — entry_audit contract and the "editado por" indicator** — `f7fbefa` (feat)

**Plan metadata:** committed alongside this SUMMARY, STATE.md, ROADMAP.md, REQUIREMENTS.md.

_Note: Task 2 carries `tdd="true"`; the test (`run_edit_audit_checks`) was written and run to a `MandatoryError` failure (schema not yet relaxed) before any production code existed, then production code was added incrementally until the test printed `'status': 'ok'`, then the whole task was committed as one atomic commit per the plan's own explicit `<done>` instruction._

## Files Created/Modified
- `tecponto_app/tecponto/doctype/tecponto_access_audit/tecponto_access_audit.json` - schema migration (D-01)
- `tecponto_app/tecponto/user_access.py` - widened `_write_audit`, new `audit_reference_field_edit`/`get_latest_reference_audit`
- `tecponto_app/tecponto/frontend/api.py` - `AUDIT_INDICATOR_ROLES`, `_serialize_reference_audit`, audit wiring in `update_service_order_entry`, `entry_audit` on `get_service_order_detail`
- `tecponto_app/tecponto/frontend/test_frontend_api.py` - `run_edit_audit_checks()` + foundation-suite wiring + source-marker pin
- `frontend/src/api/types.ts` - `ReferenceAuditIndicator`, `entry_audit` on `ServiceOrderDetailResponse`
- `frontend/src/App.tsx` - "Entrada editada por..." indicator under the Cliente `IdentityCard`

## Decisions Made
- Task 1's one-way schema migration was approved verbatim as proposed in the checkpoint (relax `affected_user.reqd`, add `reference_doctype`/`reference_name`, `field_order` to 8 entries, `permissions`/`track_changes`/`hooks.py` untouched, no `patches.txt` entry) — approval happened in a prior session; this run verified via `git log`/`git status` that no file had been touched and no commit existed before proceeding, per the continuation contract.
- Followed this project's established pattern (see STATE.md Decisions for 01-03/01-04) of squashing a `tdd="true"` task's RED→GREEN cycle into one atomic commit when the plan's own `<done>` text says "Committed as one atomic commit."

## Deviations from Plan

None — plan executed exactly as written. One verification nuance worth recording: the Task 3 acceptance criterion `grep -c 'function formatDate' frontend/src/App.tsx` returns `1` was written assuming an exact match, but the file also contains a pre-existing, untouched `formatDateInputValue` function whose name is a substring match for that grep pattern, so the count is `2`. Confirmed via `git diff` that `formatDateInputValue` was not touched by this plan and no second date *formatter* (in the sense the criterion cares about — a competing implementation of `formatDate` itself) was introduced.

## Issues Encountered
- The local dev stack's `./scripts/dev-local-server.sh restart` triggers a full `bench migrate`, which failed with an unrelated pre-existing bug (`_pickle.PicklingError: Can't pickle <class 'frappe.model.document.LazyUser'>`) inside `sync_fixtures()`'s background-job enqueue path, and the `mariadb` test container also exited on its own mid-session (matches the "known chronic instability, 5.9GB RAM" note in `AUDITORIA_SISTEMA.md`/`CLAUDE.md`). Neither is caused by this plan's changes (the traceback occurs during fixture sync, unrelated to the `Tecponto Access Audit` doctype). Worked around by running `bench --site local-ci.local reload-doctype "Tecponto Access Audit"` in a disposable container (schema-only sync, skips the broken fixtures step) to apply the migration, then verified end to end via `bench execute ... run_edit_audit_checks` in the same disposable-container pattern. Both required automated `<verify>` commands from the plan (the `bench execute` check and the schema-assertion script) passed with real output, and `npm run build` passed normally. The persistent `dev-local-server.sh`-managed server container is currently stopped and will need a fresh `bench migrate` (or a fix to the underlying fixture-enqueue bug) before it can be used for interactive browser testing again — this is an environment issue to flag for the next session, not a code defect in this plan's deliverable.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `audit_reference_field_edit`, `get_latest_reference_audit`, `AUDIT_INDICATOR_ROLES`, `_serialize_reference_audit`, and the `run_edit_audit_checks` test convention are all in place and proven — 02-02 (device credential edit, EDIT-02) and 02-03 (customer identity edit, EDIT-03) can call `audit_reference_field_edit` directly without touching `_write_audit` again.
- Known environment concern for the next session: `./scripts/dev-local-server.sh restart` currently fails via a pre-existing, unrelated `bench migrate`/`sync_fixtures` pickling bug; the workaround documented above (disposable container + `reload-doctype`/`execute`) unblocks doctype-schema and backend verification but does not fix the underlying bug. Recommend a dedicated look before 02-02/02-03 if interactive browser testing is needed.

## Self-Check: PASSED

- FOUND: `.planning/phases/02-audited-field-edit-for-post-creation-corrections/02-01-SUMMARY.md`
- FOUND: commit `6b538df` (Task 2)
- FOUND: commit `f7fbefa` (Task 3)
- FOUND: all 6 files in `key-files.modified`

---
*Phase: 02-audited-field-edit-for-post-creation-corrections*
*Completed: 2026-09-18*
