---
phase: 01-os-6-closure-warranty-verification-deadline-wiring
plan: 02
subsystem: service-order
tags: [frappe, python, warranty, boundary-test, integration-test]

# Dependency graph
requires:
  - phase: 01-os-6-closure-warranty-verification-deadline-wiring
    provides: "01-01's estimated_deadline write path was unrelated but ran first in the same phase; no functional dependency"
provides:
  - "Live create-deliver-claim proof that the 90-day repair warranty boundary is inclusive: day 89 and day 90 after delivery still allow a same-defect warranty rework, day 91 is rejected by the engine"
  - "boundary_day_89_allowed / boundary_day_90_allowed / boundary_day_91_blocked keys inside run_warranty_delivery_checks, wired into run_foundation_checks and CI"
affects: []

# Actuals (#2632)
actuals:
  tokens: 1100
  tasks: 2
  commits: 1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Boundary-day fixtures back-date pickup_date via add_days(nowdate(), -N) and derive warranty_expiry from that same pickup_date (add_days(boundary_pickup, 90)), never a literal date, so the assertion proves the 90-day window rather than restating it"

key-files:
  created: []
  modified:
    - tecponto_app/tecponto/frontend/test_frontend_api.py

key-decisions:
  - "Followed D-01 exactly: extended the existing run_warranty_delivery_checks in place, reusing its fixtures/users/finally cleanup, instead of writing a new standalone warranty test function."
  - "Used a for-loop over (days_ago, result_key, expect_blocked, failure_message) tuples instead of three copy-pasted try/except blocks — keeps the blocked=False/try/except frappe.ValidationError idiom from the existing expired-warranty case while avoiding duplicating the checkin-payload boilerplate three times. Each case still produces its own distinct Portuguese AssertionError message."
  - "Reset the persistent local dev-server site to a documented environmental baseline (bench_migrate lock timeout, then two more pre-existing/unrelated failures) before getting a clean ./scripts/test-local.sh run on attempt 4 — no source code was touched to work around any of these; see Deviations."

patterns-established:
  - "When adding a day-N boundary case to a delivery-date-driven test, derive the dependent date (warranty_expiry) from the same back-dated anchor (pickup_date) via add_days, never hardcode the expected value, so the fixture cannot silently drift from the rule under test."

requirements-completed: [WARR-01]

coverage:
  - id: D1
    description: "An OS delivered 91 days ago cannot receive a same-defect warranty rework — the Python engine rejects the check-in with frappe.ValidationError"
    requirement: "WARR-01"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_warranty_delivery_checks (boundary_day_91_blocked)"
        status: pass
    human_judgment: false
  - id: D2
    description: "An OS delivered 89 days ago can still receive a same-defect warranty rework — the check-in succeeds"
    requirement: "WARR-01"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_warranty_delivery_checks (boundary_day_89_allowed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "An OS delivered exactly 90 days ago, whose warranty expires today, can still receive a warranty rework — the boundary is inclusive of the expiry date"
    requirement: "WARR-01"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_warranty_delivery_checks (boundary_day_90_allowed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The boundary is proven against real dates on a live site through create-deliver-claim (not by reading the comparison in policies.py), and the whole foundation suite still passes with the three new fixtures in place"
    requirement: "WARR-01"
    verification:
      - kind: integration
        ref: "./scripts/test-local.sh (full run_foundation_checks, warranty_delivery section)"
        status: pass
    human_judgment: false

# Metrics
duration: 45min
completed: 2026-09-03
status: complete
---

# Phase 1 Plan 2: Warranty Boundary Proof (Day 89/90/91) Summary

**Live create→deliver→claim proof that `_validate_warranty`'s 90-day comparison is inclusive of the expiry date — days 89 and 90 pass, day 91 is rejected by the Python engine — added inside the existing `run_warranty_delivery_checks`.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-09-03T13:11:00Z
- **Completed:** 2026-09-03T13:56:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added a day-89 / day-90 / day-91 boundary block inside `run_warranty_delivery_checks`, positioned after the existing expired-warranty block (which stays untouched) and before the `default_warranty_days` switch to 30, so it runs while the 90-day setting is still the active one.
- Each boundary case creates an isolated OS via `_create_action_request_service_order`, back-dates `pickup_date` to `add_days(nowdate(), -N)`, and derives `warranty_expiry` as `add_days(boundary_pickup, 90)` — never a literal date — then attempts a same-defect warranty check-in as the attendant and asserts the outcome against the inclusive comparison in `_validate_warranty` (`getdate(warranty_expiry) < getdate(nowdate())`).
- Confirmed live: day 89 (expiry tomorrow) and day 90 (expiry today) both succeed; day 91 (expiry yesterday) is rejected with `frappe.ValidationError`.
- Extended the function's returned dict with `boundary_day_89_allowed`, `boundary_day_90_allowed`, `boundary_day_91_blocked` — all confirmed `True` in both the standalone function run and the full foundation suite.
- The existing `finally` cleanup (restores `default_warranty_days`, deletes the temporary catalog service, restores the session user) remains the function's last statement, unmodified and still reached.
- Full local foundation suite (`./scripts/test-local.sh`) passes end-to-end with `warranty_delivery: {"status": "ok", ..., "boundary_day_89_allowed": true, "boundary_day_90_allowed": true, "boundary_day_91_blocked": true}` and the overall run reports `status: "ok"`.

## Task Commits

1. **Task 1 + Task 2: Add day-89/90/91 boundary assertions and run the full foundation suite** - `b8d30c1` (test) — per the plan's own Task 2 instruction ("commit as one atomic change"), Task 1's code addition and Task 2's full-suite verification are covered by this single commit (Task 1 had no independent commit instruction; the file touched by both tasks is the same).

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified
- `tecponto_app/tecponto/frontend/test_frontend_api.py` — new day-89/90/91 boundary block inside `run_warranty_delivery_checks`, plus three new keys (`boundary_day_89_allowed`, `boundary_day_90_allowed`, `boundary_day_91_blocked`) in its returned dict.

## Decisions Made
- Extended the existing `run_warranty_delivery_checks` in place rather than writing a new function, per D-01 — reuses the fixtures, users, temp catalog service, and `finally` cleanup this function already sets up.
- Used a small loop over the three boundary cases (rather than three literal copy-pasted blocks) to avoid duplicating the check-in payload three times, while keeping the exact `blocked = False / try / except frappe.ValidationError: blocked = True` idiom the existing expired-warranty case uses, with a distinct Portuguese `AssertionError` message per case.
- Derived `warranty_expiry` from each case's own back-dated `pickup_date` via `add_days`, never a literal date, so the proof is a real 90-day-window test and not a date-arithmetic tautology (matches the plan's explicit instruction).

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written. No source-code deviations from the plan's specified action.

### Environment Note (not a deviation — informational only)

`./scripts/test-local.sh` needed 4 logged attempts (plus 2 earlier unlogged attempts) to reach a clean pass, none caused by this plan's changes:

1. First two attempts hit `filelock._error.Timeout` acquiring `bench_migrate.lock` and then (on the persistent dev site, pre-reset) an unrelated `run_technician_scope_checks` assertion (`Contador de OS do técnico ignorou o escopo da atribuição`) — traced to the persistent `local-ci.local` test site having accumulated 128+ `Service Order` records across many prior sessions, exceeding `list_service_orders`'s `limit=100` while `frappe.db.count` does not truncate. Not caused by this plan: the new boundary fixtures never set a `technician` field.
2. Reset the persistent test site (`TECPONTO_LOCAL_RESET=1`) for a clean baseline. The fresh-site run failed inside `run_technician_part_request_checks` with `frappe.exceptions.PermissionError: Usuário sem papel operacional` — the exact same failure signature already documented as pre-existing/unrelated in `01-01-SUMMARY.md`.
3. Retry failed **inside `bench migrate` itself** with `_pickle.PicklingError: Can't pickle <class 'frappe.model.document.LazyUser'>` while enqueueing a background search-index job — again the exact same Frappe/rq background-job pickling error already documented in `01-01-SUMMARY.md`, before the foundation-check suite even starts.
4. Fourth attempt passed cleanly end-to-end, including `warranty_delivery: {"status": "ok", ..., "boundary_day_89_allowed": true, "boundary_day_90_allowed": true, "boundary_day_91_blocked": true}`.

No `tecponto_app` source file was touched to work around any of these; all four failure modes are either infrastructure-level (Docker/WSL2 lock contention, Frappe/rq pickling) or accumulated persistent-site state unrelated to warranty logic — consistent with `CLAUDE.md`'s own documented note that the local Docker/WSL2 environment is unstable.

---

**Total deviations:** 0 auto-fixed. Plan executed exactly as written.
**Impact on plan:** None — all four failed attempts were environmental/pre-existing, verified by cross-referencing the exact same failure signatures already logged in `01-01-SUMMARY.md`. The fifth attempt (fourth logged) passed cleanly with the plan's changes intact.

## Issues Encountered
See "Environment Note" above — resolved by retrying `./scripts/test-local.sh` until a clean run was obtained; no code changes were needed to reach a passing run.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- WARR-01 is closed: the 90-day repair warranty boundary is proven live at days 89, 90, and 91 through a real create-deliver-claim cycle, inside the existing, CI-wired `run_warranty_delivery_checks`.
- No blockers for the remaining phase plans (01-03, 01-04) — this plan touched only `test_frontend_api.py` and did not modify `policies.py`, `aceites.py`, `api.py`, or any frontend file.
- Plan 01-01's pending human UAT item (coverage D5, técnico deadline UI round-trip) remains open and deferred to end-of-phase UAT per `workflow.human_verify_mode: end-of-phase` — unaffected by this plan.

## Self-Check: PASSED

`tecponto_app/tecponto/frontend/test_frontend_api.py` confirmed modified on disk; commit `b8d30c1` confirmed present in `git log --oneline --all`; `./scripts/test-local.sh` confirmed exit 0 with `warranty_delivery.status == "ok"` and all three boundary keys `true` on the fourth logged attempt.

---
*Phase: 01-os-6-closure-warranty-verification-deadline-wiring*
*Completed: 2026-09-03*
