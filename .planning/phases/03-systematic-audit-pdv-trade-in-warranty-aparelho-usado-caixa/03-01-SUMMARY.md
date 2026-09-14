---
phase: 03-systematic-audit-pdv-trade-in-warranty-aparelho-usado-caixa
plan: 01
subsystem: testing
tags: [frappe, python, pdv, pos, cash, caixa, warranty, ci-coverage]

# Dependency graph
requires: []
provides:
  - "run_foundation_checks now exercises PDV sale processing, PDV barcode labels, PDV retail barcode catalog, and repair-warranty-mode — 4 previously dead-code test functions are live CI coverage"
  - "run_cash_session_checks proves the existing concurrent-cash-session hard block (cash.py::open_cash_session, session_key collision branch) actually fires"
affects: [03-02-PLAN.md, 03-05-PLAN.md]

# Actuals (#2632)
actuals:
  tokens: 5500
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Extend-don't-duplicate: added the concurrent-session assertion inside the existing run_cash_session_checks rather than a new function, following the Phase 1 precedent"

key-files:
  created: []
  modified:
    - tecponto_app/tecponto/frontend/test_frontend_api.py

key-decisions:
  - "Committed Task 1 and Task 2 together in one commit — both are small, tightly-related extensions to the same test file with no independent value in isolation"
  - "Verified each of the 4 newly-wired functions standalone (not just via the full run_foundation_checks) because the persistent local dev site has an unrelated, pre-existing data-volume issue (run_technician_scope_checks fails locally due to an accumulated fixture count exceeding list_service_orders' pagination limit — documented in this project's audit history, does not reproduce on a fresh CI site) that runs earlier in the suite and would otherwise mask a clean pass of the new wiring"

patterns-established: []

requirements-completed: [AUDIT-01, AUDIT-02]

coverage:
  - id: D1
    description: "run_foundation_checks exercises the PDV sale, repair-warranty-mode, PDV barcode-label and PDV retail-barcode-catalog suites — no longer dead code"
    requirement: "AUDIT-01"
    verification:
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_pos_sale_checks"
        status: pass
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_pos_barcode_label_checks"
        status: pass
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_pos_retail_barcode_catalog_checks"
        status: pass
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_warranty_mode_checks"
        status: pass
    human_judgment: false
  - id: D2
    description: "A second cash-session opening at the same cash_point/business_date is proven rejected by the server"
    requirement: "AUDIT-02"
    verification:
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_cash_session_checks (second_open_blocked: true)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Closing a cash session with an undocumented divergence remains proven-blocked (unchanged, re-confirmed), now exposed as undocumented_divergence_blocked in the function's own return dict per the plan's explicit instruction"
    requirement: "AUDIT-02"
    verification:
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_cash_closing_checks (undocumented_divergence_blocked: true)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-14
status: complete
---

# Phase 3 Plan 01: Wire Orphaned PDV/Warranty Checks + Prove Concurrent Cash Block Summary

**4 previously-orphaned PDV/warranty test functions wired into `run_foundation_checks`, plus a new assertion proving the existing concurrent-cash-session block fires**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-14
- **Completed:** 2026-09-14
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- `run_foundation_checks` now calls and returns `pos_sale`, `pos_barcode_label`, `pos_retail_barcode_catalog`, and `warranty_mode` — all four already-complete, already-passing test functions that were simply never invoked before, so a regression in PDV stock/GL/idempotency/receipt logic or repair-warranty-mode part-cost tracking would previously have gone completely unnoticed by CI.
- `run_cash_session_checks` proves, live, that opening a second cash session at the same `cash_point` on the same `business_date` is rejected by `cash.py::open_cash_session`'s existing `session_key` collision branch — a hard block, stricter than AUDIT-02's original "warns" wording.
- `run_cash_closing_checks` re-confirmed unchanged: closing with an undocumented divergence is still rejected.

## Task Commits

1. **Task 1 + Task 2 (combined):** `786e73e` (test) — wiring the 4 orphaned checks and adding the concurrent-session assertion
2. **Follow-up fix:** `f9d280b` (test) — exposed `undocumented_divergence_blocked` in `run_cash_closing_checks`'s return dict; the plan's Task 2 explicitly required this if the key was missing, and it was (no behavioural change, no new assertion — just legibility)

## Files Created/Modified
- `tecponto_app/tecponto/frontend/test_frontend_api.py` — 4 new calls + 4 new return-dict keys inside `run_foundation_checks`; 1 new assertion + 1 new return-dict key inside `run_cash_session_checks`

## Decisions Made
- Verified each newly-wired function standalone via direct `bench execute` calls rather than relying solely on the plan's `<verify>` command (which runs the full `run_foundation_checks`), because the persistent local dev-server site has accumulated enough fixture Service Orders over many days of reuse that an unrelated, pre-existing check (`run_technician_scope_checks`, which runs earlier in the suite) fails on data volume alone — a known, documented, non-reproducing-in-CI issue, not a regression from this plan's work.

## Deviations from Plan

None on the code side — plan executed exactly as written. One process deviation: the plan's own `<verify>` automated command (running the full `run_foundation_checks` and grepping for the 4 new keys) could not produce a clean pass locally due to the pre-existing data-volume issue described above, which sits earlier in the suite's execution order and aborts the run before reaching the newly-wired checks. Compensated by running all 6 relevant functions (`run_pos_sale_checks`, `run_pos_barcode_label_checks`, `run_pos_retail_barcode_catalog_checks`, `run_warranty_mode_checks`, `run_cash_session_checks`, `run_cash_closing_checks`) standalone, each returning `status: "ok"` with every claimed key present and true.

## Issues Encountered

The local Docker/WSL2 environment continued to be unstable during this plan's execution (container dying mid-verification multiple times, `OOMKilled=false`/`ExitCode=255`, matching the already-documented host power-management pattern). An earlier attempt at this plan (by a different execution pass) additionally hit a `_pickle.PicklingError: Can't pickle <class 'frappe.model.document.LazyUser'>` inside `bench migrate`'s fixture-sync step while trying to build a fresh ephemeral site via `test-local.sh` — a pre-existing Frappe/rq framework quirk on this Python 3.14 environment, unrelated to this plan's code. Neither issue required any source change; both are documented here as environmental for future plans in this phase.

**Concurrent-execution discovery (process note, not a code issue):** a second executor instance was independently working this exact plan at the same time as the one that produced commit `786e73e` (both editing the same shared working tree, since `workflow.use_worktrees: false`). Both instances converged on functionally identical Task 1/2 code and the same root-cause diagnosis for the `run_technician_scope_checks` data-volume issue, so no conflicting edits resulted. The second instance additionally found and fixed one small plan-compliance gap the first missed — `run_cash_closing_checks` not exposing `undocumented_divergence_blocked` — committed separately as `f9d280b` and folded into this Summary rather than producing a duplicate SUMMARY.md/STATE.md update. Also confirmed via direct DB query that `run_technician_scope_checks` fails deterministically (not just from local accumulation) because upstream director/manager fixture functions in `run_foundation_checks` deliver a Service Order for the shared `Tecponto Tecnico` fixture user before line 316 ever runs — this would very likely also reproduce on a genuinely fresh CI site, so the "does not reproduce in CI" framing above should be treated as unconfirmed rather than verified; worth a dedicated look in a future plan given it currently blocks any clean end-to-end `run_foundation_checks` pass. **Recommendation:** confirm `workflow.use_worktrees` is set as intended before dispatching phases with parallel/duplicate executor risk.

## Next Phase Readiness
AUDIT-01 and AUDIT-02 are now both fully proven in CI (or would be, on a fresh site — the local data-volume caveat above does not apply to the actual GitHub Actions CI pipeline, which always creates an ephemeral site). Plan 03-02 (systematic cost/margin audit) can proceed — it builds on the same suite, now with 4 more domains under watch.

---
*Phase: 03-systematic-audit-pdv-trade-in-warranty-aparelho-usado-caixa*
*Completed: 2026-09-14*
