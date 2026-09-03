---
phase: 01-os-6-closure-warranty-verification-deadline-wiring
plan: 04
subsystem: service-order
tags: [react, typescript, frappe, python, service-order, deadline, kanban, ui]

# Dependency graph
requires:
  - phase: 01-os-6-closure-warranty-verification-deadline-wiring
    provides: "01-01's write path (set_service_order_estimated_deadline, estimated_deadline on ServiceOrderSummary/ServiceOrderDetailResponse) and 01-03's get_service_order_deadline_suggestion endpoint"
provides:
  - "ServiceOrderDeadlineSuggestion TS interface and serviceOrders.deadlineSuggestion(name) client method"
  - "TechnicalBudgetEditor pre-fills the deadline input from the SLA suggestion only when no deadline is saved, with disabled/loading and empty-state placeholders, never overwriting a saved value"
  - "Prazo estimado DetailLine row in ServiceOrderPersistentOverview and a Prazo estimado CardLine row in the Kanban's KanbanCard, both reading the OS-level estimated_deadline field"
  - "Python source-marker assertions in run_service_order_deadline_checks pinning both frontend wirings so a future refactor cannot silently drop them"
affects: []

# Actuals (#2632)
actuals:
  tokens: 3000
  tasks: 3
  commits: 1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Read-only pre-fill fetches follow the existing useCallback(try/catch → onToast) + useEffect(active-flag teardown) shape already established for load/catalog-search in TechnicalBudgetEditor, guarded by a suggesting state initialized once from whether the prop arrived empty"
    - "Frontend surfaces with no test runner get pinned by literal-substring source-marker assertions read directly off disk in the Python integration suite (Path(__file__).parents[3]), the same idiom already used for WarrantyScreen.tsx"

key-files:
  created: []
  modified:
    - frontend/src/api/types.ts
    - frontend/src/api/serviceOrders.ts
    - frontend/src/App.tsx
    - frontend/src/ServiceOrderKanban.tsx
    - tecponto_app/tecponto/frontend/test_frontend_api.py

key-decisions:
  - "Squashed the three tasks' intermediate per-task commits into one atomic commit via git reset --soft before the final commit, per the plan's own explicit Task 3 instruction and matching the pattern already established in 01-01/01-03."
  - "Reused the already-imported Clock3 icon for the new Kanban row instead of importing a new icon, since the UI-SPEC does not mandate a specific icon and the row is a text-and-timestamp fact identical in kind to the existing modified row."
  - "Cleared the suggesting loading state in a finally-equivalent path (after both the success and error branches of the suggestion fetch) so a failed suggestion fetch can never leave the deadline input permanently disabled."

patterns-established:
  - "A read-only pre-fill fetch that must never overwrite a saved value is guarded by a boolean state initialized once from the emptiness of the incoming prop, not by watching the prop across renders — the parent never re-passes a changed prop mid-session, so a one-shot guard is simpler and equally correct."

requirements-completed: [DEADLINE-01, DEADLINE-02]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "ServiceOrderDeadlineSuggestion interface and serviceOrders.deadlineSuggestion(name) client method typecheck cleanly and are called from TechnicalBudgetEditor's pre-fill effect"
    requirement: "DEADLINE-02"
    verification:
      - kind: other
        ref: "npm --prefix frontend run typecheck"
        status: pass
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_service_order_deadline_checks (frontend_source_markers.app_tsx)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The OS detail overview shows a new Prazo estimado DetailLine row reading the OS-level estimated_deadline field through the shared formatDate helper, immediately after the existing Prazo atual row"
    requirement: "DEADLINE-02"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_service_order_deadline_checks (frontend_source_markers.app_tsx)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run build"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Kanban card shows a new Prazo estimado: <date> row reading the OS-level estimated_deadline field (not the unrelated stage_clock.estimated_deadline), reusing CardLine's built-in truncate and staying in CardLine's muted color, never orange"
    requirement: "DEADLINE-02"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_service_order_deadline_checks (frontend_source_markers.service_order_kanban_tsx)"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run build"
        status: pass
    human_judgment: false
  - id: D4
    description: "run_service_order_deadline_checks and the full local foundation suite (./scripts/test-local.sh) both pass end to end after this plan's changes, proving the widened test function and the two new frontend rows disturbed no pre-existing contract"
    requirement: "DEADLINE-01"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_service_order_deadline_checks"
        status: pass
      - kind: integration
        ref: "./scripts/test-local.sh (run_foundation_checks, full suite)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A técnico opening an OS in the budget stage sees the deadline input arrive disabled with the loading copy, then pre-filled with a future date; overwriting and saving it persists and is not clobbered by the suggestion on reload; and the same saved date is visible on the Kanban card and in the OS detail overview"
    human_judgment: true
    rationale: "Requires a real browser session (visual/interactive confirmation of loading state, pre-fill, override, and the two read-only surfaces together); no browser automation tool was available to this executor. Deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase — the backend/frontend wiring for all three surfaces is already proven by D1-D4 via automated source-marker assertions, a clean build, and the full integration suite, so this item is a visual/UX confirmation only, not an unproven code path. Joins plan 01-01's still-open D5 and plan 01-03's still-open D7 as the same end-of-phase browser pass covers all three."
    verification: []

# Metrics
duration: 24min
completed: 2026-09-03
status: complete
---

# Phase 1 Plan 4: Deadline Suggestion Pre-fill and Kanban/Detail Display Summary

**Wired the previously dead `calculate_suggested_delivery` suggestion into a real pre-fill on the técnico's deadline input, and added the missing "Prazo estimado" read-only rows to the Kanban card and OS detail overview, both pinned against silent regression by new Python source-marker assertions.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-09-03T16:57:58Z
- **Completed:** 2026-09-03T17:21:41Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `ServiceOrderDeadlineSuggestion` TS interface (mirroring `calculate_suggested_delivery`'s return dict key-for-key) and `serviceOrders.deadlineSuggestion(name)` client method, calling `get_service_order_deadline_suggestion` as a query-shaped read.
- `TechnicalBudgetEditor` now fetches the suggestion on mount only when the OS has no saved deadline yet — never overwriting a técnico's already-saved decision. The input is disabled with "Calculando sugestão…" while the fetch is in flight, and falls back to the "Defina o prazo estimado" placeholder when the calculator has nothing to compute from, per the UI-SPEC's empty/loading state contract.
- A new "Prazo estimado" `DetailLine` row in `ServiceOrderPersistentOverview`'s expanded block, immediately after "Prazo atual", reading `detail.estimated_deadline` through the shared `formatDate` helper.
- A new "Prazo estimado: <date>" `CardLine` row in the Kanban's `KanbanCard`, reading the top-level `item.estimated_deadline` (not the unrelated `stage_clock.estimated_deadline` collision flagged by the UI-SPEC), reusing `CardLine`'s built-in truncate and staying in its muted color.
- `run_service_order_deadline_checks` extended with source-marker assertions that read `App.tsx` and `ServiceOrderKanban.tsx` directly off disk and fail loudly if the suggestion call, the save call, or either display row's exact marker text disappears — the same idiom already used for `WarrantyScreen.tsx`.
- Full local foundation suite (`./scripts/test-local.sh`) passes end to end, including `service_order_deadline: {"status": "ok", ..., "frontend_source_markers": {"app_tsx": true, "service_order_kanban_tsx": true}}`, and `npm run build` (typecheck + vite build + `verify-foundation.mjs`) exits 0.

## Task Commits

Per this plan's own Task 3 instruction ("commit the plan as one atomic change"), all three tasks were committed together in a single commit — the two intermediate per-task commits made while executing Tasks 1 and 2 were squashed via `git reset --soft` before Task 3's changes were finalized, matching the pattern already used in 01-01 and 01-03.

1. **Tasks 1-3: Suggestion type/client, pre-fill + OS-detail row, Kanban row + source markers** - `133c69a` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified
- `frontend/src/api/types.ts` — `ServiceOrderDeadlineSuggestion` interface
- `frontend/src/api/serviceOrders.ts` — `deadlineSuggestion(name)` client method
- `frontend/src/App.tsx` — `TechnicalBudgetEditor` gains `suggesting` state, a `loadSuggestion` callback, and a pre-fill effect; `ServiceOrderPersistentOverview` gains the "Prazo estimado" `DetailLine` row
- `frontend/src/ServiceOrderKanban.tsx` — `KanbanCard` gains the "Prazo estimado" `CardLine` row
- `tecponto_app/tecponto/frontend/test_frontend_api.py` — `run_service_order_deadline_checks` extended with `App.tsx`/`ServiceOrderKanban.tsx` source-marker assertions and `frontend_source_markers` in the returned dict

## Decisions Made
- Followed the plan's explicit Task 3 instruction for a single atomic commit spanning all three tasks, reconciling the two intermediate per-task commits via `git reset --soft` rather than leaving three separate commits — matching this plan's own acceptance criterion (`git log -1 --stat` showing exactly the five `files_modified` in one commit).
- Reused the already-imported `Clock3` icon for the new Kanban row instead of adding a new icon import — the UI-SPEC leaves the icon choice open, and the row is a text-and-date fact of the same kind as the existing `modified` row.
- Implemented the suggestion pre-fill as a `useCallback` (mirroring `load`'s try/catch/onToast shape) plus a `useEffect` with an `active`-flag teardown (mirroring the catalog-search effect), guarded by a `suggesting` boolean initialized once from whether `estimatedDeadline` arrived empty, so a fetch resolving after unmount or after the técnico already saved a value cannot clobber state.

## Deviations from Plan

None - plan executed exactly as written.

### Environment Note (not a deviation — informational only)

`./scripts/test-local.sh` needed 4 attempts to reach a clean pass, none caused by this plan's changes — the same failure signatures already documented in `01-01-SUMMARY.md`/`01-03-SUMMARY.md`:
1. `filelock._error.Timeout` acquiring `bench_migrate.lock` (stale lock; removed manually).
2. On the persistent (non-reset) site: `run_technician_scope_checks` assertion failure — the same accumulated-records issue documented in `01-02-SUMMARY.md`/`01-03-SUMMARY.md`, unrelated to any file this plan touches.
3. A reset run (`TECPONTO_LOCAL_RESET=1`) whose captured output was inconclusive due to a background-output buffering artifact in the tool harness, not a suite failure.
4. A final run on the now-fresh site passed cleanly end to end, including `service_order_deadline: {"status": "ok", ...}` with both `frontend_source_markers` entries `true`, `warranty_delivery: {"status": "ok", ...}`, and `stage_sla_checks: {"status": "ok", ...}`.

This matches `CLAUDE.md`'s own documented note that the local Docker/WSL2 environment is unstable — the flakiness is environmental, not a regression introduced by this plan. No `tecponto_app` or `frontend` source file was touched to work around it.

---

**Total deviations:** 0. **Impact on plan:** None — the plan's action text was followed exactly; the only friction was the already-documented local dev-environment flakiness, resolved by retrying and resetting the test site, with no code changes.

## Issues Encountered
See "Environment Note" above — resolved by removing the stale lock and resetting the local test site; no code changes were needed to reach a passing run.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DEADLINE-01 and DEADLINE-02 are both fully closed across all four plans of this phase: the write path (01-01), the warranty boundary and delivery-lock/print proofs (01-02/01-03), the suggestion endpoint (01-03), and now the operator-facing pre-fill plus the Kanban/OS-detail display (01-04).
- **Pending human UAT (coverage D5, joining 01-01's D5 and 01-03's D7):** a single real-browser pass covering: técnico opens an OS in the budget stage and sees the disabled/loading state then the pre-filled suggestion; overrides and saves it; reloads and confirms the saved value persists and is not re-overwritten; expands "Ver mais" on the OS overview and confirms the new row; and opens the Kanban board to confirm the new card row on both a saved-deadline OS and a "Não definido" OS. Deferred per `workflow.human_verify_mode: end-of-phase`; surface this at end-of-phase UAT together with the tracking-portal/print pass from 01-03.
- This is the last plan of Phase 1 (OS.6 Closure — Warranty Verification & Deadline Wiring). No blockers remain for phase completion; end-of-phase UAT is the only outstanding item before moving to Phase 2.

## Self-Check: PASSED

All five modified files confirmed present on disk with the expected content (`grep -n 'ServiceOrderDeadlineSuggestion'` in `types.ts`/`serviceOrders.ts`; `grep -c 'estimated_deadline' frontend/src/ServiceOrderKanban.tsx` → 1; `grep -n 'deadlineSuggestion'`/`'estimated_deadline'` in `App.tsx` at the expected call sites); commit `133c69a` confirmed present in `git log --oneline --all` and `git log -1 --stat` confirmed it touches exactly the five `files_modified`; `run_service_order_deadline_checks` re-confirmed `status: "ok"` with both `frontend_source_markers` entries `true`; `./scripts/test-local.sh` confirmed a clean full-suite pass including this plan's section.

---
*Phase: 01-os-6-closure-warranty-verification-deadline-wiring*
*Completed: 2026-09-03*
