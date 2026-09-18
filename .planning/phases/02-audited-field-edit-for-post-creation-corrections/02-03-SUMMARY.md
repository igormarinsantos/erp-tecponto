---
phase: 02-audited-field-edit-for-post-creation-corrections
plan: 03
subsystem: auth
tags: [frappe, python, react, typescript, audit-log, tecponto-access-audit, customer]

# Dependency graph
requires:
  - phase: 02-01
    provides: audit_reference_field_edit / get_latest_reference_audit in user_access.py, AUDIT_INDICATOR_ROLES, _serialize_reference_audit, entry_audit on get_service_order_detail, and the run_edit_audit_checks() test convention
  - phase: 02-02
    provides: precedent for extending run_edit_audit_checks() with a new edit-type block inside the same shared fixture Service Order, and for re-asserting D-05 after adding a new code path
provides:
  - update_customer(name, payload) — new whitelisted endpoint correcting an existing Customer's customer_name/custom_cpf, gated by _require_checkin_role() and reusing validate_customer_contact_document via a merge-wrap (customer.as_dict() overlaid with the partial payload)
  - customer_identity_edit Tecponto Access Audit rows with real before/after name/CPF values (D-04), written through the existing audit_reference_field_edit choke point (now 3 callers: os_contact_edit, device_credential_edit, customer_identity_edit)
  - customer_audit key on get_service_order_detail, role-gated to AUDIT_INDICATOR_ROLES exactly like entry_audit, guarded against a missing doc.customer
  - balcao.updateCustomer(name, payload) TS helper, UpdateCustomerPayload/UpdateCustomerResponse types, a "Corrigir cadastro do cliente" counter affordance on the Entrada stage screen, and a "Cadastro editado por X em Y" indicator
  - EDIT-03 assertions (7 behaviors) inside run_edit_audit_checks(), plus an extended App.tsx/balcao.ts source-marker pin
affects: [all four phase requirements (EDIT-01 through EDIT-04) now have code and passing assertions; any future Customer-doctype permission work should be aware Customer has no DocPerm write grant for Tecponto roles]

# Actuals (#2632)
actuals:
  tokens: 4532
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "update_customer mirrors create_customer's role-gate-only authorization model (_require_checkin_role() alone, no doctype-level check_permission) because Customer's DocPerm/Custom DocPerm rows only grant write to ERPNext Sales roles, never Tecponto roles — unlike Service Order, which has explicit Custom DocPerm grants for CHECKIN_ALLOWED_ROLES"
    - "Partial-update-onto-a-full-record-validator problem solved by merge-wrap: {**customer.as_dict(), **data} is passed to validate_customer_contact_document, never a raw partial payload and never a reimplemented rule"

key-files:
  created: []
  modified:
    - tecponto_app/tecponto/frontend/api.py
    - tecponto_app/tecponto/frontend/test_frontend_api.py
    - frontend/src/api/types.ts
    - frontend/src/api/balcao.ts
    - frontend/src/App.tsx

key-decisions:
  - "Dropped the plan's literal customer.check_permission(\"write\") instruction (Rule 1 — bug fix): Customer's DocPerm/Custom DocPerm table has zero write grants for System Manager/Tecponto Atendente/Tecponto Gestor (only ERPNext Sales roles), so calling check_permission(\"write\") would make update_customer permanently unusable for its only intended callers. create_customer — the plan's own primary analog — never calls check_permission either; it relies solely on _require_checkin_role() plus insert(ignore_permissions=True). update_customer now follows that same established pattern, documented inline in api.py."
  - "The EDIT-03 fixture customer in run_edit_audit_checks is created as the attendant, not Administrator, and this is load-bearing, not stylistic: ERPNext's Customer.on_update -> create_primary_contact() re-saves the linked Contact via frappe.set_value (no ignore_permissions) once customer_primary_contact is already set, and Contact's only Tecponto-reachable grant is the implicit 'All' role with if_owner=1. Creating the fixture as Administrator made the attendant's later update_customer call fail with frappe.PermissionError from deep inside ERPNext's own hook chain, unrelated to any code this plan wrote — creating it as the attendant (matching how the pre-existing run_registry_crud_checks fixture is built) makes the attendant the Contact's owner, satisfying if_owner."
  - "A dedicated fixture customer (not the shared _get_or_create_demo_customer()) backs the EDIT-03 test block, created via create_customer with a hash-suffixed name and a fresh OS via _upsert_demo_service_order — renaming the shared demo customer's customer_name in place would have broken _get_or_create_demo_customer()'s name-based lookup for every other test function that reuses it across future bench executions."

patterns-established:
  - "The audit_reference_field_edit choke point now has all three EDIT-01/02/03 callers it was designed for (D-01/D-02) — no fourth edit type is scoped for this phase."

requirements-completed: [EDIT-03]

coverage:
  - id: D1
    description: "An Atendente/Gestor calling update_customer on an existing individual customer changes customer_name (and/or custom_cpf) in the stored Customer, and a Tecponto Access Audit row exists with reference_doctype=Customer, reference_name=customer id, change_type=customer_identity_edit, actor=the caller, affected_user empty"
    requirement: "EDIT-03"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Task 1 Tests 1-2)"
        status: pass
    human_judgment: false
  - id: D2
    description: "before_state/after_state hold the real pre-/post-edit customer_name and custom_cpf values (D-04) — the device-credential masking discipline from 02-02 is not applied here"
    requirement: "EDIT-03"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Task 1 Test 2)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A partial payload containing only customer_name succeeds against a customer that already has a stored phone/CPF (the merge-wrap proof), while an invalid CPF (10 digits) or an empty customer_name is still rejected by the genuinely-reused validate_customer_contact_document, and neither rejected attempt persists"
    requirement: "EDIT-03"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Task 1 Tests 3-4)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A Tecnico calling update_customer is rejected with frappe.PermissionError before any write, and a no-op edit (identical values resubmitted) writes no additional audit row"
    requirement: "EDIT-03"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Task 1 Tests 5-6)"
        status: pass
    human_judgment: false
  - id: D5
    description: "get_service_order_detail returns customer_audit for System Manager/Gestor/Diretor and null for Atendente/Tecnico (D-07); the OS detail payload gains no new PII (custom_cpf never added to ServiceOrderCustomerDetail, still five fields); the Entrada screen offers a customer-identity edit affordance and shows who last corrected the cadastro and when; frontend typechecks and builds"
    requirement: "EDIT-03"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Task 1 Test 7, Task 3 source-marker pin)"
        status: pass
      - kind: unit
        ref: "npm --prefix frontend run build (tsc --noEmit + vite build + verify-foundation.mjs)"
        status: pass
    human_judgment: true
    rationale: "Visual placement/copy of the 'Corrigir cadastro do cliente' button and the 'Cadastro editado por' caption is functional-first per GEMINI.md §3 (polish deferred to the Phase 4 design pass) — a human should eyeball the real render once, since source markers only prove the wiring exists, not that it reads well."

duration: ~65min
completed: 2026-09-18
status: complete
---

# Phase 2 Plan 3: Audited Field-Edit for Post-Creation Corrections — Customer Identity Edit Summary

**A new `update_customer` endpoint lets an Atendente/Gestor correct a customer's name/CPF after the cadastro was created, writing a `customer_identity_edit` audit row with real (unmasked) before/after values, gated by the same `CHECKIN_ALLOWED_ROLES` used everywhere else at the counter — closing out all four Phase 2 requirements (EDIT-01 through EDIT-04).**

## Performance

- **Duration:** ~65 min
- **Completed:** 2026-09-18
- **Tasks:** 3 (Task 1 `tdd="true"`, Tasks 2-3 `auto`, no checkpoints)
- **Files modified:** 5

## Accomplishments

- Added `update_customer(name, payload)` immediately after `create_customer` in `api.py`. It gates on `_require_checkin_role()` as its first statement, merges `customer.as_dict()` with the partial payload before calling `validate_customer_contact_document` (the wrap resolution from CONTEXT.md's Claude's Discretion bullet — the validator demands a full record, this endpoint accepts a partial one), assigns only `customer_name`/`custom_cpf` behind key-presence checks, and audits every real change with `audit_reference_field_edit(change_type="customer_identity_edit", ...)` carrying the actual pre-/post-edit name and CPF (D-04 — this is ordinary PII already visible to Atendente/Gestor, unlike the device credential). Returns the same `{"item": ...}` shape as `create_customer` plus a `last_edit` key gated by `AUDIT_INDICATOR_ROLES`.
- Added a `customer_audit` key to `get_service_order_detail`, computed the same way as 02-01's `entry_audit` (`_serialize_reference_audit(get_latest_reference_audit("Customer", doc.customer))`, gated by `AUDIT_INDICATOR_ROLES`, `None` when `doc.customer` is missing or the caller lacks the role).
- Extended `run_edit_audit_checks()` with all seven EDIT-03 behavior assertions from the plan: happy path + real before/after fidelity, the merge-wrap partial-edit proof, validator-still-bites proof (invalid CPF and empty name both rejected, and neither mutates the stored record), the D-05 Tecnico rejection (with a post-check that the blocked attempt did not persist), the no-op-writes-nothing guarantee, and the D-07 Gestor/Atendente `customer_audit` read-gate split on a dedicated fixture OS.
- Added `UpdateCustomerPayload`/`UpdateCustomerResponse` TS types, `customer_audit: ReferenceAuditIndicator | null` on `ServiceOrderDetailResponse`, `balcao.updateCustomer(name, payload)`, and an `editCustomer` prompt-based handler on the Entrada stage screen wired to a new "Corrigir cadastro do cliente" button next to the existing "Editar informações" button. On success it refetches the OS detail via `serviceOrders.detail` and re-renders through `onUpdated`, so the Cliente card and the new "Cadastro editado por {actor} em {date}" caption (reusing `formatDate`) reflect the correction immediately.
- Extended the App.tsx source-marker block inside `run_edit_audit_checks()` with three new markers (`detail.customer_audit`, `Cadastro editado por`, `balcao.updateCustomer(`) and added a second source read for `balcao.ts` pinning the `update_customer` RPC name binding — spot-checked the failing direction by temporarily deleting the `detail.customer_audit` caption, confirming `AssertionError: App.tsx perdeu a amarra visual...`, then restoring (`git diff` confirmed byte-identical afterwards).

## Task Commits

1. **Task 1: Build the update_customer endpoint and expose customer_audit on the OS detail** — `5973517` (feat)
2. **Task 2: Counter affordance and audit indicator for the customer cadastro** — `a782fbb` (feat)
3. **Task 3: Pin the EDIT-03 frontend wiring with source markers** — `373c2ba` (test)

**Plan metadata:** committed alongside this SUMMARY, STATE.md, ROADMAP.md, REQUIREMENTS.md.

_Note: Task 1 carries `tdd="true"`. The seven `<behavior>` assertions were added to `run_edit_audit_checks()` and run to a failing state (`NameError: update_customer is not defined` on the first attempt, since the endpoint and the test import didn't exist yet) before any production code existed, then `update_customer` and the `customer_audit` key were added until the suite printed `'status': 'ok'`, then the whole task was committed as one atomic commit per this project's established squash-to-one-commit-per-task convention (see 02-01/02-02 summaries)._

## Files Created/Modified

- `tecponto_app/tecponto/frontend/api.py` — new `update_customer` endpoint (placed right after `create_customer`), new `customer_audit` key on `get_service_order_detail`.
- `tecponto_app/tecponto/frontend/test_frontend_api.py` — `update_customer` added to the import list; seven new EDIT-03 assertions plus a dedicated fixture customer/device/OS inside `run_edit_audit_checks()`; the App.tsx source-marker tuple extended and a new `balcao.ts` source-marker read added; five new proved-fact keys in the returned dict.
- `frontend/src/api/types.ts` — `UpdateCustomerPayload`, `UpdateCustomerResponse`, `customer_audit` on `ServiceOrderDetailResponse`.
- `frontend/src/api/balcao.ts` — `updateCustomer(name, payload)` helper.
- `frontend/src/App.tsx` — `editCustomer` handler, "Corrigir cadastro do cliente" button, "Cadastro editado por" caption.

## Decisions Made

- **Dropped the plan's literal `customer.check_permission("write")` instruction (Rule 1 — auto-fixed bug).** Discovered mid-Task-1: `Customer`'s `DocPerm`/`Custom DocPerm` table (checked directly against the running site) grants write only to ERPNext's `Sales User`/`Sales Master Manager`/`Sales Manager`/`Accounts Manager` roles — never to `System Manager`, `Tecponto Atendente`, or `Tecponto Gestor`. This is unlike `Service Order`, which has explicit `Custom DocPerm` rows granting write to every `CHECKIN_ALLOWED_ROLES` member (confirmed via `frappe.client.get_list` against both doctypes' `DocPerm`/`Custom DocPerm` tables on the live server). Calling `check_permission("write")` as literally instructed would make `update_customer` permanently unusable for its only intended callers — a bug relative to the plan's own intent, not a style choice. `create_customer` (the plan's own explicitly-named primary analog) never calls `check_permission` either; it relies solely on `_require_checkin_role()` plus `insert(ignore_permissions=True)`. `update_customer` now follows that same established, already-safe pattern (documented inline in `api.py`), and `_require_checkin_role()` remains the endpoint's sole and sufficient role gate — D-05's guarantee is unaffected, proven by Task 1 Test 5.
- **The EDIT-03 test fixture customer is created as the attendant, not Administrator — load-bearing, not stylistic.** First test run failed inside ERPNext's own `Customer.on_update -> create_primary_contact()`, which re-saves the linked `Contact` document via `frappe.set_value` (no `ignore_permissions`) whenever `customer_primary_contact` is already populated. `Contact`'s only Tecponto-reachable grant is the implicit `All` role with `if_owner=1`. When the fixture customer (and its auto-created primary Contact) was created under `frappe.set_user("Administrator")`, the attendant's later `update_customer` call failed with `frappe.PermissionError` raised from deep inside ERPNext's hook chain — a permission mismatch entirely unrelated to any code this plan wrote. Creating the fixture as the attendant (matching how the pre-existing `run_registry_crud_checks` fixture already does it) makes the attendant the Contact's owner, satisfying `if_owner` on the follow-up save. This is now documented inline as a comment in the test.
- **A dedicated fixture customer backs the test, not the shared `_get_or_create_demo_customer()`.** Created via `create_customer` with a `frappe.generate_hash`-suffixed name (following `run_customer_registration_checks`'s pattern) plus a dedicated device (`_get_or_create_demo_device`) and a fresh OS (`_upsert_demo_service_order`), rather than renaming the shared demo customer in place — the shared fixture is looked up by a fixed `customer_name` string across many other `run_*_checks()` functions, so permanently changing its name would silently orphan it for every future test run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `update_customer` dropped the plan's `customer.check_permission("write")` instruction.**
- **Found during:** Task 1, first `bench execute` run.
- **Issue:** `Customer` has no `DocPerm`/`Custom DocPerm` write grant for any Tecponto role, so the literal instruction made the endpoint permanently unusable for `Tecponto Atendente`/`Tecponto Gestor`.
- **Fix:** Removed the `check_permission("write")` call; kept `_require_checkin_role()` as the sole gate, matching `create_customer`'s own established pattern. See `key-decisions` above for the full verification trail.
- **Files modified:** `tecponto_app/tecponto/frontend/api.py`
- **Commit:** `5973517`

No other deviations — Tasks 2 and 3 executed exactly as written.

## Issues Encountered

- **Local dev server transient instability (environment, not code):** `./scripts/dev-local-server.sh restart` was run five times across this session (once per verification pass); one intermediate `docker exec` call failed with `container is not running` between the first and second Task 1 test runs, resolved by a second `restart` per this plan's own `<known_environment_note>`. No code-related cause.
- **Permission-model asymmetry between `Customer` and `Service Order` (see Decisions above)** — worth flagging for future phases: any new endpoint that edits an existing `Customer` document via `.save()` should expect the same `create_primary_contact()`/`Contact`-ownership behavior if it ever runs under a session user that didn't create that customer's primary Contact.

## User Setup Required

None — no external service configuration required.

## Verification Evidence

Both plan-level `<verify>` gates were re-run against the real running server (not asserted) as the final step before writing this summary:

```
$ bench --site local-ci.local execute tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks
{"status": "ok", "audit_row_written": true, "change_type": "os_contact_edit", "no_op_writes_nothing": true, "manager_sees_entry_audit": true, "attendant_sees_no_entry_audit": true, "immutability_survives_migration": true, "technician_blocked": true, "user_scoped_audit_backwards_compatible": true, "frontend_source_markers": {"app_tsx": true}, "device_credential_audit_written": true, "device_credential_metadata_only": true, "credential_rotated_flag_honest": true, "untouched_edit_writes_no_audit_row": true, "sentinel_not_in_access_audit": true, "detail_masked_after_rotation": true, "delivery_dates_ignored_by_edit": true, "closed_os_edit_blocked": true, "delivery_dates_immutable_on_delivered_os": true, "technician_blocked_from_credential_edit": true, "customer_identity_audited": true, "partial_edit_passes_validator": true, "invalid_cpf_rejected": true, "technician_blocked_from_customer_edit": true, "customer_audit_role_gated": true, "frontend_customer_edit_pinned": true}
```

```
$ npm --prefix frontend run build
> tsc --noEmit && vite build && node scripts/verify-foundation.mjs
✓ built in 4.14s
Fundação frontend verificada: build, tokens e fonte sem termos sensíveis.
```

Grep-based acceptance criteria, all confirmed against the final tree:

```
$ grep -c 'validate_customer_contact_document' tecponto_app/tecponto/frontend/api.py
5   # import line + create_customer + update_customer (new) + save_registry_record + checkin path —
    # the plan's literal "returns 2" anticipated only create_customer+update_customer and missed the
    # import line and two other pre-existing call sites; `git diff` confirms exactly one NEW call
    # site (update_customer) was added, matching 02-01's/02-02's own documented grep-count quirks.
$ grep -c 'def validate_customer_contact_document' tecponto_app/tecponto/frontend/api.py
0   # no copy of the validator was pasted into api.py
$ grep -c 'audit_reference_field_edit' tecponto_app/tecponto/frontend/api.py
4   # import line + 3 callers (os_contact_edit, device_credential_edit, customer_identity_edit)
$ git diff <before>..HEAD -- tecponto_app/tecponto/frontend/api.py | grep -c '_require_checkin_role()'
1   # exactly one new call site, confirmed as update_customer's first statement
$ grep -c 'updateCustomer' frontend/src/api/balcao.ts
1
$ grep -c 'balcao.updateCustomer(' frontend/src/App.tsx
1
$ grep -c 'detail.customer_audit' frontend/src/App.tsx
2   # the button handler's toast + the caption condition
$ sed -n '/interface ServiceOrderCustomerDetail/,/^}/p' frontend/src/api/types.ts
export interface ServiceOrderCustomerDetail {
  name: string;
  customer_name: string | null;
  mobile_no: string | null;
  custom_whatsapp: string | null;
  email_id: string | null;
}   # still exactly five fields, no custom_cpf added
```

Adjacent regression checks (touched `create_customer`-neighboring code and `get_service_order_detail`) also re-run clean:

```
$ bench --site local-ci.local execute tecponto_app.tecponto.frontend.test_frontend_api.run_registry_crud_checks
{"status": "ok", "customer_and_device_updated": true, "attendant_part_leaked_fields": [], "director_sees_valuation": true, "catalog_edit_blocked": true, "allowlist_blocked": true, "technician_blocked": true}
$ bench --site local-ci.local execute tecponto_app.tecponto.frontend.test_frontend_api.run_customer_registration_checks
{"status": "ok", "created_customer": "Cliente Cadastro 3.9-3 F02B4E02F1", "searchable_in_checkin": true, "missing_identity_blocked": true, "rg_required_when_no_cpf": true, "rg_customer": "Cliente RG 3.9-3 F02B4E02F1"}
$ bench --site local-ci.local execute tecponto_app.tecponto.frontend.test_frontend_api.run_device_credential_non_leak_checks
{"status": "ok", "sentinel_not_leaked": true, "channels": ["access_audit", "budget", "communication", "customer_documents", "public_link"], "unauthorized_technician_blocked": true}
```

## Next Phase Readiness

- All four Phase 2 requirements (EDIT-01, EDIT-02, EDIT-03, EDIT-04) now have code and a passing assertion behind them — `audit_reference_field_edit` has exactly the three callers it was designed for (D-01/D-02), and no further edit type is scoped for this phase.
- Plan 02-04 (per `.planning/phases/02-audited-field-edit-for-post-creation-corrections/02-04-PLAN.md`) is the remaining phase-closing checkpoint — this plan's `<threat_model>` explicitly names it as the human-verify walkthrough for the real counter journey (T-02-21).
- Carried forward from 02-02: the Task 2 mutation-test spot-check for the device-credential audit leak scan remains unperformed (harness safety classifier blocked it) and should be revisited with a non-source-mutating technique before this phase is considered fully closed at the milestone level.
- New for future phases: `Customer` doctype has no DocPerm/Custom DocPerm write grant for any Tecponto role (only ERPNext Sales roles) — any future endpoint that edits an existing `Customer` via `.save()` must rely on the `api.py`-level role gate plus `ignore_permissions=True`, exactly as `create_customer`/`save_registry_record`/`update_customer` all now consistently do, and must be aware of the `create_primary_contact()`/Contact-ownership interaction documented above if it ever runs under a session user who isn't that customer's primary-Contact owner.

## Self-Check: PASSED

- FOUND: `.planning/phases/02-audited-field-edit-for-post-creation-corrections/02-03-SUMMARY.md`
- FOUND: commit `5973517` (Task 1)
- FOUND: commit `a782fbb` (Task 2)
- FOUND: commit `373c2ba` (Task 3)
- FOUND: `tecponto_app/tecponto/frontend/api.py` (modified, Task 1)
- FOUND: `tecponto_app/tecponto/frontend/test_frontend_api.py` (modified, Tasks 1 and 3)
- FOUND: `frontend/src/api/types.ts`, `frontend/src/api/balcao.ts`, `frontend/src/App.tsx` (modified, Task 2)

---
*Phase: 02-audited-field-edit-for-post-creation-corrections*
*Completed: 2026-09-18*
