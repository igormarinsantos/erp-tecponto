# Phase 1: OS.6 Closure — Warranty Verification & Deadline Wiring - Context

**Gathered:** 2026-09-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Two independent, low-risk closures of the OS.6 backlog:
1. Prove the 90-day repair warranty boundary is enforced end-to-end (create → deliver → day-91 blocked / day-89 passes).
2. Wire the existing OS-level `estimated_deadline` field to a real write path (technician sets it during diagnosis/budget) and confirm it surfaces everywhere it's already read (Kanban, OS detail, public tracking, print formats).

No new deadline field. No new warranty mechanism. No touching `pickup_date`/`warranty_expiry` immutability.

</domain>

<decisions>
## Implementation Decisions

### Warranty boundary test
- **D-01:** Extend the existing `run_warranty_delivery_checks()` (`tecponto_app/tecponto/frontend/test_frontend_api.py:2528`, already wired into `run_foundation_checks` and already passing in CI) with explicit boundary assertions: a claim attempt at `warranty_expiry - 1 day` (day 91 equivalent) is blocked, and at `warranty_expiry` itself or one day before (day 89 equivalent) succeeds. Do NOT write a new standalone test function — reuse the fixtures/users this test already sets up (original OS delivered via `_deliver_warranty_test_order`).

### Deadline ownership and timing
- **D-02:** Only the Técnico role sets `estimated_deadline`, only during the diagnosis/budget (orçamento) stage — matches the existing code comment `# Prazo pertence ao diagnóstico/orçamento, não à Entrada` (`api.py:2253`), which already resets it to `None` at check-in.
- **D-03:** Setting the deadline is **optional**, not a blocking requirement for budget submission. `_validate_budget_submission` in `policies.py` already enforces a real quote line is required; adding a second hard requirement here isn't justified by any current product signal — don't add one speculatively.
- **D-04:** The deadline stays editable by the Técnico until the OS reaches `workflow_state == "Entregue"` — same lock point already enforced for `pickup_date`/`warranty_expiry` via `_validate_delivery_dates_are_immutable` in `policies.py`. Keeps the immutability boundary consistent across all "delivery promise" fields rather than inventing a separate lock rule for this one. — **Reversibility:** reversible — this is a validation-function check, easy to relax or tighten later without a migration.

### Deadline input UX
- **D-05:** Pre-fill the deadline input with a suggestion computed by `calculate_suggested_delivery()` (`tecponto_app/tecponto/service_order/stage_sla.py:77`) — this function already exists, already sums the configured stage SLAs (`Entrada criada` → `Aguardando aprovação`) plus service duration and lead time, and is currently **dead code** (never called from any production path — confirmed via full-repo grep this session). The technician sees the suggestion and can override it; it's a starting point, not an imposed value.

### Surfacing
- **D-06:** Reuse the exact label already present in print formats — `"Prazo estimado:"` (`print_formats.py:587,647`) — for any new surface (Kanban badge, OS detail, tracking page) instead of inventing new copy. Reuse the shared `parseServerDate` date parser (`frontend/src/utils/date.ts`, added earlier this session) for consistent local-date formatting everywhere the deadline is displayed — do not write a new date-formatting function.

### Claude's Discretion
User delegated all 4 gray areas ("o que for melhor") after being shown the codebase evidence above. Decisions D-01 through D-06 were made by Claude based on that evidence — flagged here in case the user wants to revisit any of them before or during planning.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Warranty
- `tecponto_app/tecponto/service_order/policies.py` — `_validate_warranty`, `_validate_delivery_dates_are_immutable`, `is_same_warranty_defect` (the enforcement logic to test the boundary against)
- `tecponto_app/tecponto/service_order/aceites.py:163` — where `warranty_expiry` is originally computed (`add_days(doc.pickup_date, get_operation_config()["default_warranty_days"])`, default 90)
- `tecponto_app/tecponto/frontend/test_frontend_api.py:2528` (`run_warranty_delivery_checks`) — the existing test to extend, not replace

### Deadline
- `tecponto_app/tecponto/doctype/service_order/service_order.json:342` — the existing `estimated_deadline` field definition (OS-level, confirmed via grep — not per-service-line)
- `tecponto_app/tecponto/frontend/api.py:2253-2255` — check-in code that clears the field with the explicit "belongs to diagnosis/budget" comment
- `tecponto_app/tecponto/service_order/stage_sla.py:77` (`calculate_suggested_delivery`) — dead-code deadline-suggestion function to reuse
- `tecponto_app/tecponto/service_order/stage_clock.py`, `tecponto_app/tecponto/service_order/kanban.py`, `tecponto_app/tecponto/pending.py`, `tecponto_app/tecponto/tracking.py`, `tecponto_app/tecponto/service_order/print_formats.py` — all existing read sites for `estimated_deadline`, already working, only need the new write path to start populating them
- `frontend/src/api/serviceOrders.ts` (`addTechnicalBudgetLine` and neighbors) — existing frontend API module for the budget-composition screen; the new deadline-setting call belongs here
- `frontend/src/App.tsx:~4150` — existing budget-composition UI section (inline in the App.tsx monolith — no separate BudgetStage component exists yet) where the new deadline input attaches
- `frontend/src/utils/date.ts` (`parseServerDate`) — shared date parser to reuse for display

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `calculate_suggested_delivery()` (`stage_sla.py`) — ready-made deadline-suggestion calculator, currently orphaned
- `run_warranty_delivery_checks()` (`test_frontend_api.py`) — extensive existing warranty test harness (fixtures, users, delivery helper `_deliver_warranty_test_order`) to extend rather than duplicate
- `parseServerDate` (`frontend/src/utils/date.ts`) — shared local-date parser from this session's earlier bugfix work

### Established Patterns
- Delivery-time immutability lock (`_validate_delivery_dates_are_immutable`) already covers `pickup_date`/`warranty_expiry` — Phase 1 should extend this same pattern to `estimated_deadline` rather than invent a new lock mechanism (see D-04)
- `Tecponto Settings.default_warranty_days` (default 90, configurable) is the single source of truth for the warranty window — already respected by both `aceites.py` and the existing test

### Integration Points
- Frontend: `frontend/src/api/serviceOrders.ts` → `frontend/src/App.tsx` budget-composition section (~line 4150)
- Backend: new whitelisted endpoint (or extension of an existing budget-related one) in `tecponto_app/tecponto/frontend/api.py`, writing `estimated_deadline` on `Service Order`, gated to Técnico role only

</code_context>

<specifics>
## Specific Ideas

No specific UI mockup or exact wording was requested beyond reusing the existing "Prazo estimado" label (D-06). No specific date-format preference beyond the existing `parseServerDate` convention.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (User deferred the discussion itself to Claude's judgment rather than raising out-of-scope ideas.)

</deferred>

---

*Phase: 1-os-6-closure-warranty-verification-deadline-wiring*
*Context gathered: 2026-09-03*
