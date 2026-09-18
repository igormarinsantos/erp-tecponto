---
phase: 02-audited-field-edit-for-post-creation-corrections
plan: 02
subsystem: auth
tags: [frappe, python, audit-log, tecponto-access-audit, device-credential, security]

# Dependency graph
requires:
  - phase: 02-01
    provides: audit_reference_field_edit / get_latest_reference_audit in user_access.py, the migrated Tecponto Access Audit reference_doctype/reference_name schema, and the run_edit_audit_checks() test convention
provides:
  - update_service_order_entry writes a device_credential_edit audit row (metadata-only: device_access_type/had_credential/credential_rotated) whenever a device credential is touched, using the existing audit_reference_field_edit choke point
  - A site-wide sentinel scan (no reference filter) across the whole Tecponto Access Audit table, proving a rotated credential never leaks into any row
  - An access_audit entry in the channels dict of the canonical run_device_credential_non_leak_checks (OS.2), so the audit trail is scanned by the same sentinel test as print formats/tracking links/WhatsApp going forward
  - An explicit two-layer EDIT-04 regression proof (allowlist-by-omission at the endpoint + _validate_delivery_dates_are_immutable at the document-write level) inside run_edit_audit_checks
affects: [02-03 (customer identity edit, same audit choke point), any future refactor of the device-credential path]

# Actuals (#2632)
actuals:
  tokens: 4360
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Credential audit rows always write on touch (guard is credential_touched and before != after, and after always carries an extra credential_rotated key), with honesty coming from the credential_rotated flag rather than from suppressing the write — 'touched but preserved' and 'never touched' stay distinguishable in the log"
    - "had_credential is derived from Customer Device.device_access_type presence via frappe.db.get_value, read both before and after _save_device_access_credential runs, never by decrypting device_access_credential"

key-files:
  created: []
  modified:
    - tecponto_app/tecponto/frontend/api.py
    - tecponto_app/tecponto/frontend/test_frontend_api.py

key-decisions:
  - "Every credential-touching call to update_service_order_entry writes an audit row, even a type-only edit with a blank (preserve-existing) credential — the before/after metadata dicts are structurally always different (after always carries the extra credential_rotated key), so credential_rotated is the signal that distinguishes a real rotation from a touched-but-preserved edit, matching the plan's Test 5 and the T-02-13 repudiation mitigation in the threat register."
  - "The mandatory mutation-test spot-check in Task 2's acceptance criteria ('temporarily revert Task 1's metadata dict to include the raw credential, confirm the test fails, then restore') was not performed as literally specified — the harness's auto-mode safety classifier blocked the Edit tool call that would have written a raw-credential-leaking line into api.py, citing 'Credential Leakage' / 'Code That Leaks When Run'. This is treated as a correctly-functioning guardrail, not a bug to route around: GEMINI.md itself forbids disabling a security protection 'nem mesmo para fazer testes passarem'. No equivalent proof was substituted in this run; see Deviations."

patterns-established:
  - "The device-credential audit path reuses audit_reference_field_edit exactly as 02-01 established — no second audit-writing mechanism was introduced for this phase's most sensitive field."

requirements-completed: [EDIT-02, EDIT-04]

coverage:
  - id: D1
    description: "Correcting a device credential on an open OS writes a device_credential_edit Tecponto Access Audit row whose before_state/after_state contain only device_access_type/had_credential/credential_rotated — never the raw credential, a fragment >=4 chars, or its length"
    requirement: "EDIT-02"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Task 1 block, Tests 1-6)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A unique sentinel rotated in as a device credential through the real endpoint appears in zero Tecponto Access Audit rows site-wide, get_service_order_detail stays masked (device_access_type visible, secret absent) after the rotation, and the canonical OS.2 sentinel test (run_device_credential_non_leak_checks) now scans access_audit as a first-class channel"
    requirement: "EDIT-02"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Task 2 block) and run_device_credential_non_leak_checks (Step B, access_audit channel)"
        status: pass
    human_judgment: false
  - id: D3
    description: "pickup_date/warranty_expiry/estimated_deadline are structurally unreachable through update_service_order_entry (a payload including all three alongside a legitimate contact change leaves the dates byte-identical and lands the contact change), a delivered/cancelled OS refuses any edit outright, and a direct document write to those fields on a delivered OS is rejected by _validate_delivery_dates_are_immutable even bypassing the endpoint entirely"
    requirement: "EDIT-04"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Task 3 block, Tests 1-4)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A Tecnico calling update_service_order_entry with a device_access_type/credential payload is rejected with frappe.PermissionError before any write happens, even after Task 1 added a new branch into the function (D-05)"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks (Task 3 Test 5)"
        status: pass
    human_judgment: false

duration: ~70min
completed: 2026-09-18
status: complete
---

# Phase 2 Plan 2: Audited Field-Edit for Post-Creation Corrections — Device-Credential Edit & EDIT-04 Regression Proof Summary

**A device-credential correction on an open OS now writes a `device_credential_edit` audit row carrying only `device_access_type`/`had_credential`/`credential_rotated` metadata — never the secret, a fragment of it, or its length — and the access-audit log is proven, by a site-wide sentinel scan and by enumeration in the canonical OS.2 test, to never leak a rotated credential; delivery/warranty date immutability (EDIT-04) is now pinned by an explicit two-layer regression test instead of holding only by accident.**

## Performance

- **Duration:** ~70 min
- **Completed:** 2026-09-18
- **Tasks:** 3 (all `type="auto" tdd="true"`, no checkpoints)
- **Files modified:** 2

## Accomplishments

- `update_service_order_entry` now computes `before_credential_meta`/`after_credential_meta` around the existing `_save_device_access_credential` call — `device_access_type`/`had_credential` are read via `frappe.db.get_value("Customer Device", ...)` before and after the rotation (never decrypting the secret), and `credential_rotated` is a boolean computed once from the stripped payload value and never referenced again. When the metadata actually changed, it calls `audit_reference_field_edit(change_type="device_credential_edit", ...)` — the same choke point 02-01 established for `os_contact_edit`, with no second audit-writing mechanism introduced.
- Extended `run_edit_audit_checks()` with the six device-credential behavior assertions from the plan: happy path + row existence, the D-03 key whitelist (`before_state`/`after_state` key sets are subsets of `{device_access_type, had_credential, credential_rotated}`), a substring/length non-leak scan (raw value, every 4+-char fragment, and the credential's character count as a value), before-state fidelity (fresh device has `had_credential=False`), the honest `credential_rotated=False` on a type-only/blank-credential edit that preserves the existing secret, and a no-new-row guarantee when neither contact nor credential is touched.
- Added a site-wide (no `reference_name` filter) sentinel scan to `run_edit_audit_checks()`: a credential sentinel rotated in through the real endpoint is proven absent from every `Tecponto Access Audit` row in the table, and `get_service_order_detail` called immediately after the rotation is proven to still expose `device_access_type` (the label) while `frappe.as_json` of the whole payload never contains the sentinel.
- Added an `access_audit` entry to the `channels` dict of the canonical `run_device_credential_non_leak_checks` (OS.2), reading every `Tecponto Access Audit` row referencing that test's Service Order or Customer Device under the Administrator session — the existing per-channel substring scan now covers the audit log automatically, alongside `customer_documents`, `communication`, `budget`, and `public_link`.
- Extended `run_edit_audit_checks()` with the EDIT-04 regression proof at both layers: (1) a payload carrying `pickup_date`/`warranty_expiry`/`estimated_deadline` alongside a legitimate contact change leaves the three dates byte-identical (compared via `getdate()` to normalize the DB's `datetime` round-trip against `nowdate()`'s date string) while the contact change lands, and no audit row ever mentions those field names; (2) a delivered or cancelled OS refuses the edit outright at the endpoint's existing `workflow_state` guard, and a direct `frappe.get_doc(...).save()` write to `pickup_date`/`warranty_expiry` on a delivered OS is independently rejected by `_validate_delivery_dates_are_immutable`, with the stored value confirmed unchanged after the failed save. Also re-asserted the Técnico role gate (D-05) on the credential branch Task 1 added.
- `api.py`/`policies.py` are untouched by Task 3's commit — `git diff --stat` confirms EDIT-04 was proved, not implemented, matching the plan's explicit constraint.

## Task Commits

1. **Task 1: Audit the device-credential correction with metadata only** — `b7ca345` (feat)
2. **Task 2: Sentinel-prove the audit log is not a credential leak channel** — `eee2ab6` (test)
3. **Task 3: Regression-prove the delivery and warranty dates stay untouchable (EDIT-04)** — `27c8f5a` (test)

**Plan metadata:** committed alongside this SUMMARY, STATE.md, ROADMAP.md, REQUIREMENTS.md.

_Note: all three tasks carry `tdd="true"`. For each, the new assertions were added to `run_edit_audit_checks()` and run to a failing/erroring state before any production or fixture code existed to satisfy them (Task 1: `AssertionError: ... achou 0`; Tasks 2 and 3 are pure test-file additions exercising already-correct production behavior, so their "RED" was the assertions not yet existing rather than a failing run), then the corresponding code was added/fixed until the suite printed `'status': 'ok'`, then each task was committed as a single atomic commit per this project's established convention (see 02-01's summary)._

## Files Created/Modified

- `tecponto_app/tecponto/frontend/api.py` — `update_service_order_entry`: computes `before_credential_meta`/`after_credential_meta` around `_save_device_access_credential`, writes a `device_credential_edit` audit row via `audit_reference_field_edit` guarded by `credential_touched and before != after`. `_save_device_access_credential` and the `text_fields` allowlist are byte-identical to before this plan.
- `tecponto_app/tecponto/frontend/test_frontend_api.py` — three new blocks inside `run_edit_audit_checks()` (device-credential audit, sentinel non-leak scan, EDIT-04 regression proof), a new `access_audit` channel entry in `run_device_credential_non_leak_checks`, and `getdate` added to the existing `frappe.utils` import line.

## Decisions Made

- Every credential-touching call always writes an audit row (see `key-decisions` in frontmatter) — the metadata dicts are structurally distinct before vs. after (the `after` dict always carries the extra `credential_rotated` key), so the write guard `before_credential_meta != after_credential_meta` fires on every touch, and `credential_rotated` (not row absence) is what makes a real rotation distinguishable from a preserve-only edit in the log. This matches the plan's Test 5 wording and the threat register's T-02-13 repudiation mitigation ("a genuine rotation always writes a row").
- Reset the shared demo `Customer Device`'s `device_access_type` to blank at the start of the Task 1 test block (`frappe.db.set_value(..., update_modified=False)`) rather than assuming a clean starting state — this device is reused by `_get_or_create_demo_device` across many `run_*_checks()` functions in the same foundation suite (including `run_device_credential_non_leak_checks`, which sets `device_access_type = "Alfanumérica"` on it), so the before-state-fidelity assertion (Test 4: `had_credential` false → true) would be order-dependent and flaky without this reset.
- Fixed a real (test-only) bug caught by the plan's own Test 4/backstop assertions during GREEN: `frappe.db.get_value("Service Order", ..., "pickup_date")` returns a `datetime.datetime` object from this DB round-trip, not a bare `date`, so `str(...)` comparison against `nowdate()`'s `'YYYY-MM-DD'` string false-failed. Fixed by comparing via `getdate(...)` on both sides (added `getdate` to the existing `frappe.utils` import), which normalizes the type mismatch without weakening what the assertion actually proves (Rule 1 — bug in the test I was writing, not in production code; `git diff --stat` for `api.py`/`policies.py` stayed empty as the plan requires).

## Deviations from Plan

### Not performed as specified

**1. [Task 2 acceptance criterion] The "temporarily revert Task 1's metadata dict to include the raw credential" mutation-test spot-check was not performed as literally written.**
- **What the plan asked:** "Temporarily reverting Task 1's metadata dict to include the raw credential makes `run_edit_audit_checks` fail (spot-check the failing direction once, then restore)."
- **What happened:** The `Edit` tool call that would have added a line like `"raw_credential_TEMP_LEAK_SPOTCHECK": data.get("device_access_credential")` to `after_credential_meta` in `api.py` was blocked by this harness's auto-mode safety classifier, with reason `Credential Leakage`. A follow-up attempt to even inspect `git diff` in the same turn was also blocked (`Code That Leaks When Run`), then a subsequent identical `git status` call succeeded normally, suggesting the block was a session-level heightened-suspicion response to the specific edit rather than a permanent tool lockout.
- **Why not routed around:** The instructions accompanying the block explicitly direct against working around it via other tools "in malicious ways," and against continuing to retry. Writing a real, if temporary, raw-credential-leaking line into tracked source directly contradicts GEMINI.md §1.3 ("Nenhuma proteção de segurança pode ser ignorada ou desativada, nem mesmo para fazer testes passarem") in spirit, even though the plan's own intent was a fully-reverted mutation test, not a genuine weakening. Given the explicit block plus that principle, the safer choice was to skip the literal mutation test rather than find an indirect path to the same edit.
- **What was NOT substituted:** No equivalent "inject a synthetic leaked row via an ephemeral, non-source-file mechanism" proof was completed in this run before time/attempts were redirected to finishing the rest of the plan — this is a real gap relative to the plan's acceptance criterion, not a false negative. The actual `<verify>` gates for both Task 1 and Task 2 (the two `bench execute` commands) passed with real output quoted below, and Task 2's other three acceptance criteria (channel enumeration, site-wide filter-less scan, `access_audit` in the returned `channels` list) were all verified directly. The mutation-test direction specifically (proving the test *would* catch a real leak) is the one piece left unverified by this run.
- **Impact:** Low-to-moderate. The forward-direction proof (current code does not leak, verified three independent ways: key whitelist, substring/length scan, site-wide sentinel scan) is solid. What's unverified is a meta-property (would the test itself catch a regression) rather than the production guarantee itself.
- **Recommendation:** A future session should perform this mutation-test check via a mechanism this harness's safety classifier does not flag — e.g., a throwaway unit test that calls `audit_reference_field_edit` directly with a synthetic leaking dict and asserts the *existing* Test 2/Test 3 assertions (copy-pasted as a standalone check, not modifying `api.py`) would raise — rather than mutating `update_service_order_entry` itself.

No other deviations — Tasks 1 and 3 executed exactly as written, including the explicit "do not modify `api.py`/`policies.py`" constraint in Task 3.

## Issues Encountered

- **Local dev server transient crash (environment, not code):** After the Task 1 test-file edit, `./scripts/dev-local-server.sh restart` brought the container up but it crashed seconds later with `MySQLdb.OperationalError: (2006, 'Server has gone away')` inside an unrelated Frappe notification-subscription code path during its own startup request — matching the documented chronic Docker/WSL2 instability. A second `restart` (per this plan's `<known_environment_note>`) succeeded and the container stayed up for the remainder of the session; no further retries were needed.
- **Test-only date-type bug (caught by TDD, not shipped):** the first run of Task 3's immutability backstop assertions failed with `pickup_date de OS entregue mudou mesmo após o save ter lançado exceção` even though the `save()` correctly raised `frappe.ValidationError` — the assertion itself was comparing a `datetime.datetime` (from `frappe.db.get_value`) against a `'YYYY-MM-DD'` string (from `nowdate()`) via `str(...)`. Debugged with a temporary `print()` (removed before commit), fixed by normalizing both sides through `getdate()`. This was a bug in the test being written this session, not in `_validate_delivery_dates_are_immutable`, and is documented here rather than under "Deviations" since it never touched `api.py`/`policies.py`.

## User Setup Required

None — no external service configuration required.

## Verification Evidence

Both plan-level `<verify>` gates were re-run against the real running server (not asserted) as the final step before writing this summary:

```
$ bench --site local-ci.local execute tecponto_app.tecponto.frontend.test_frontend_api.run_edit_audit_checks
{"status": "ok", "audit_row_written": true, "change_type": "os_contact_edit", "no_op_writes_nothing": true, "manager_sees_entry_audit": true, "attendant_sees_no_entry_audit": true, "immutability_survives_migration": true, "technician_blocked": true, "user_scoped_audit_backwards_compatible": true, "frontend_source_markers": {"app_tsx": true}, "device_credential_audit_written": true, "device_credential_metadata_only": true, "credential_rotated_flag_honest": true, "untouched_edit_writes_no_audit_row": true, "sentinel_not_in_access_audit": true, "detail_masked_after_rotation": true, "delivery_dates_ignored_by_edit": true, "closed_os_edit_blocked": true, "delivery_dates_immutable_on_delivered_os": true, "technician_blocked_from_credential_edit": true}
```

```
$ bench --site local-ci.local execute tecponto_app.tecponto.frontend.test_frontend_api.run_device_credential_non_leak_checks
{"status": "ok", "sentinel_not_leaked": true, "channels": ["access_audit", "budget", "communication", "customer_documents", "public_link"], "unauthorized_technician_blocked": true}
```

```
$ grep -c 'get_password\|get_decrypted_password' tecponto_app/tecponto/frontend/api.py
0
```

`npm run build` (frontend, unmodified by this plan) also re-verified clean: `Fundação frontend verificada: build, tokens e fonte sem termos sensíveis.`

## Acceptance-criteria note

The plan's Task 1 acceptance criterion `grep -c 'audit_reference_field_edit' tecponto_app/tecponto/frontend/api.py returns 2` literally returns `3` after this task, not `2` — the plan's count anticipated only the two call sites (contact from 02-01, credential from this task) but the file also has one `from ... import audit_reference_field_edit, get_latest_reference_audit` line at the top, which the same grep pattern matches. Confirmed via `git diff` that exactly one new call site (`device_credential_edit`) was added and no second audit-writing mechanism exists — this is a plan-authoring counting quirk (same class as 02-01's `formatDate`/`formatDateInputValue` grep note), not a functional gap.

## Next Phase Readiness

- `audit_reference_field_edit` remains the single audit-writing choke point after this plan added its second caller — 02-03 (customer identity edit, EDIT-03) can call it directly for `customer_identity_edit` without touching `user_access.py` again.
- The `access_audit` channel is now permanently wired into `run_device_credential_non_leak_checks`, so any future change to the credential path (including 02-03's unrelated work, if it ever touches device fields) is automatically scanned for leaks by the existing OS.2 sentinel test.
- Outstanding from this run: the Task 2 mutation-test spot-check (see Deviations) should be revisited with a non-source-mutating technique before this phase is considered fully closed out at the milestone level.
- Environment note carried forward from 02-01 remains true: the persistent dev server container is subject to occasional transient MySQL connection drops on startup; a second `restart` resolves it, matching this plan's own `<known_environment_note>`.

## Self-Check: PASSED

- FOUND: `.planning/phases/02-audited-field-edit-for-post-creation-corrections/02-02-SUMMARY.md`
- FOUND: commit `b7ca345` (Task 1)
- FOUND: commit `eee2ab6` (Task 2)
- FOUND: commit `27c8f5a` (Task 3)
- FOUND: `tecponto_app/tecponto/frontend/api.py` (modified, Task 1 only)
- FOUND: `tecponto_app/tecponto/frontend/test_frontend_api.py` (modified, all three tasks)

---
*Phase: 02-audited-field-edit-for-post-creation-corrections*
*Completed: 2026-09-18*
