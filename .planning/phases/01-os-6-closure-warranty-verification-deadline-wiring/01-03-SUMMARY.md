---
phase: 01-os-6-closure-warranty-verification-deadline-wiring
plan: 03
subsystem: service-order
tags: [frappe, python, service-order, deadline, immutability, sla, print-formats, public-tracking]

# Dependency graph
requires:
  - phase: 01-os-6-closure-warranty-verification-deadline-wiring
    provides: "01-01's set_service_order_estimated_deadline write path and estimated_deadline payload wiring; this plan hardens and proves it"
provides:
  - "estimated_deadline joins pickup_date and warranty_expiry in _validate_delivery_dates_are_immutable — locked from the moment an OS reaches Entregue, freely editable before that"
  - "sum_service_business_hours(rows) public helper in stage_sla.py, and get_service_order_deadline_suggestion(name) — a role-gated, read-only endpoint giving calculate_suggested_delivery its first production caller"
  - "Prazo estimado line in the laudo técnico print template, closing the last of the three print formats named in ROADMAP Phase 1 success criterion 3"
  - "Live proof that a técnico-saved deadline reaches the guest tracking portal and all three print documents (orçamento, orçamento discriminado, laudo técnico) with no cost/margin/credential leak"
affects: []

# Actuals (#2632)
actuals:
  tokens: 8000
  tasks: 3
  commits: 1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Delivery-immutability lock stays a single shared function (_validate_delivery_dates_are_immutable) widened by one tuple entry per new delivery-promise field, never a bespoke per-field lock"
    - "A dead, already-written calculation function (calculate_suggested_delivery) gets its first production caller through a thin, purpose-specific public wrapper (sum_service_business_hours) rather than an import of a private helper across module boundaries"
    - "Print-format proofs render the real template functions via frappe.render_template(template, {\"doc\": order}) against a live document, not a static string match, so a template regression is caught the same way a public-tracking-portal regression is"

key-files:
  created: []
  modified:
    - tecponto_app/tecponto/service_order/policies.py
    - tecponto_app/tecponto/service_order/stage_sla.py
    - tecponto_app/tecponto/frontend/api.py
    - tecponto_app/tecponto/service_order/print_formats.py
    - tecponto_app/tecponto/frontend/test_frontend_api.py

key-decisions:
  - "Followed the plan's explicit Task 3 instruction to commit all three tasks as a single atomic change rather than the default per-task commit protocol — squashed the two intermediate per-task commits (Task 1, Task 2) via git reset --soft before Task 3's changes were ready, then committed all five files together, matching this plan's own acceptance criterion (git log -1 --stat showing exactly the five files_modified)."
  - "Built the delivered-OS fixture for the immutability proof by reusing _deliver_warranty_test_order (sets pickup_without_repair, entry_signature, customer_signature, link_acceptance_required) before db_set-ing workflow_state/pickup_date/warranty_expiry, rather than a bare db_set of the three delivery fields alone — a bare db_set left the doc failing _validate_delivery_acceptance's own 'nota emitida' and 'link_acceptance_required' checks on any subsequent save(), which would have made every save() fail for a reason unrelated to the deadline lock and produced a false-positive delivered_lock_blocked result."
  - "Zeroed every configured Tecponto Stage SLA (restored in a finally block) rather than skip the 'nothing to sum' truth from the plan's must_haves — this is the only way to prove get_service_order_deadline_suggestion returns an empty suggestion instead of a fabricated one when there is genuinely nothing to compute from."

patterns-established:
  - "When a plan's own action text calls for a single atomic commit spanning tasks (contrast with the executor's default per-task commit), follow the plan's explicit instruction and reconcile any intermediate per-task commits via git reset --soft before the final commit, rather than leaving multiple commits that fail the plan's own acceptance criterion."

requirements-completed: [DEADLINE-01, DEADLINE-02]

coverage:
  - id: D1
    description: "Once an OS reaches workflow_state Entregue, changing estimated_deadline is rejected by the engine with the same message shape already used for pickup_date and warranty_expiry"
    requirement: "DEADLINE-01"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_service_order_deadline_checks (delivered_lock_blocked)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Before delivery, the técnico can change an already-saved estimated_deadline as many times as needed, and an untouched save on a delivered OS still succeeds (the lock triggers on change, not on presence)"
    requirement: "DEADLINE-01"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_service_order_deadline_checks (editable_before_delivery, untouched_save_allowed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "get_service_order_deadline_suggestion returns a suggested date computed from configured stage SLAs plus the OS's own service durations (Dias úteis rows converting at 9 business hours/unit), and never writes estimated_deadline"
    requirement: "DEADLINE-02"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_service_order_deadline_checks (suggestion_service_business_hours, suggestion_total_business_hours, suggestion_writes_nothing)"
        status: pass
    human_judgment: false
  - id: D4
    description: "get_service_order_deadline_suggestion returns an empty suggestion, not a fabricated date, when there is nothing to compute from (zeroed stage SLAs, no service rows)"
    requirement: "DEADLINE-02"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_service_order_deadline_checks (empty_suggestion_is_empty)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The deadline saved by the técnico appears on the public tracking portal payload for a guest holding a valid token, and in the rendered orçamento, orçamento discriminado and laudo técnico print formats under the label Prazo estimado, with no cost/margin/credential leak"
    requirement: "DEADLINE-02"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_service_order_deadline_checks (portal_shows_deadline, portal_leak_free, print_shows_deadline, print_leak_free)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Widening the immutability tuple and adding the SLA helper disturbed neither the pre-existing warranty-delivery lock nor the pre-existing stage-SLA/calculate_suggested_delivery contract, and the full local foundation suite passes end to end"
    requirement: "DEADLINE-01"
    verification:
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_warranty_delivery_checks"
        status: pass
      - kind: integration
        ref: "tecponto_app.tecponto.frontend.test_frontend_api.run_stage_sla_checks"
        status: pass
      - kind: integration
        ref: "./scripts/test-local.sh (run_foundation_checks, full suite)"
        status: pass
    human_judgment: false
  - id: D7
    description: "A human opening the public tracking link of an OS with a saved deadline sees the date in the Previsão block instead of the Atualização em breve fallback, and the same date appears on the printed orçamento and laudo técnico from the OS screen"
    human_judgment: true
    rationale: "Requires a real browser session and printed-document visual confirmation; no browser automation tool was available to this executor. Deferred to end-of-phase UAT per workflow.human_verify_mode=end-of-phase (the plan's Task 3 <verify> carries this as a <human-check> alongside its <automated> checks) — the backend/template proof (deadline reaching the payload and rendering under the correct label) is already proven by D5 via the automated integration check, so this item is a visual/UX confirmation only, not an unproven code path."
    verification: []

# Metrics
duration: 75min
completed: 2026-09-03
status: complete
---

# Phase 1 Plan 3: Delivery-Lock, Deadline Suggestion, and Portal/Print Proof Summary

**Widened the existing delivery-immutability lock to cover `estimated_deadline`, gave the previously dead `calculate_suggested_delivery` its first production caller through a new role-gated read-only endpoint, and proved live that a técnico-saved deadline reaches the public tracking portal and all three print formats (including a new laudo técnico line) with zero cost/margin/credential leakage.**

## Performance

- **Duration:** 75 min
- **Started:** 2026-09-03T14:15:00Z
- **Completed:** 2026-09-03T15:30:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `_validate_delivery_dates_are_immutable` (`policies.py`) now locks `estimated_deadline` the instant an OS reaches `Entregue`, using the exact same field/label-tuple mechanism already governing `pickup_date` and `warranty_expiry` — no new function, no new call site. Proven live: a real `doc.save()` on a delivered OS with a changed deadline is rejected; the same save with the deadline untouched succeeds; and the deadline can be changed twice on a budget-stage OS before delivery, with the second value winning.
- `sum_service_business_hours(rows)` — a new public helper in `stage_sla.py`, placed directly after `calculate_suggested_delivery` — sums a Service Order's own service-row durations into business hours, so `api.py` never has to import the private `_duration_as_business_hours` across module boundaries.
- `get_service_order_deadline_suggestion(name)` — a new whitelisted endpoint in `api.py`, gated by the same `_require_technician_deadline_role()` guard as the write endpoint, read-only, calling `calculate_suggested_delivery` with the OS's own computed service hours. This is the calculator's first production caller since it was written — previously only exercised by a standalone test.
- The laudo técnico print template gained the missing "Prazo estimado" line (closing ROADMAP Phase 1 success criterion 3), reusing the exact label and `tp.estimated_deadline` context key the two orçamento formats already use — `grep -c 'Prazo estimado:' print_formats.py` now reports 3.
- `run_service_order_deadline_checks` was extended with the delivered-lock/untouched-save/editable-before-delivery proof, the suggestion proof (a Dias-úteis service row contributing 9 business hours/unit, an empty-input case with zeroed stage SLAs returning an empty suggestion instead of a fabricated date), and the portal/print proof — a guest-held tracking token's public portal payload and all three rendered print documents show the técnico's saved deadline, with `contains_sensitive_field` confirming no leak in either surface.
- `run_warranty_delivery_checks` and `run_stage_sla_checks` still return `status: "ok"`, confirming the widened immutability tuple and the new SLA helper disturbed neither pre-existing contract. The full local foundation suite (`./scripts/test-local.sh`) passed end to end on a freshly reset site.

## Task Commits

Per this plan's own Task 3 instruction ("commit the whole plan as one atomic change"), all three tasks were committed together in a single commit — the two intermediate per-task commits made while executing Tasks 1 and 2 were squashed via `git reset --soft` before Task 3's changes were finalized, so the final state matches the plan's acceptance criterion of one commit touching exactly the five `files_modified`.

1. **Tasks 1-3: Lock the deadline at delivery, suggest it from the SLAs, and prove it on the portal and prints** - `40c390c` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified
- `tecponto_app/tecponto/service_order/policies.py` — `_validate_delivery_dates_are_immutable` widened with `("estimated_deadline", "prazo estimado")`
- `tecponto_app/tecponto/service_order/stage_sla.py` — new `sum_service_business_hours(rows)` public helper
- `tecponto_app/tecponto/frontend/api.py` — new `get_service_order_deadline_suggestion(name)` whitelisted endpoint
- `tecponto_app/tecponto/service_order/print_formats.py` — new "Prazo estimado" line in `_laudo_tecnico_html`
- `tecponto_app/tecponto/frontend/test_frontend_api.py` — `run_service_order_deadline_checks` extended with the delivery-lock, suggestion, and portal/print proofs; new `get_service_order_deadline_suggestion` import

## Decisions Made
- Followed the plan's explicit Task 3 instruction for a single atomic commit spanning all three tasks, reconciling the two intermediate per-task commits made along the way via `git reset --soft` rather than leaving three separate commits — the plan's own acceptance criterion required `git log -1 --stat` to show exactly the five `files_modified` in one commit.
- Built the delivered-OS test fixture by reusing `_deliver_warranty_test_order` (which sets `pickup_without_repair`, `entry_signature`, `customer_signature`, and the in-memory validation pass) before persisting `workflow_state`/`pickup_date`/`warranty_expiry`/`pickup_without_repair`/`entry_signature`/`customer_signature`/`link_acceptance_required` via `db_set` — a bare `db_set` of only the three delivery fields (as a first attempt) left the OS failing `_validate_delivery_acceptance`'s unrelated "nota emitida" and acceptance-evidence checks on every subsequent save, producing a false-positive lock result rather than proving the deadline-specific rule.
- Zeroed every configured `Tecponto Stage SLA` row (restored in a `finally` block) to exercise the "nothing to compute from" truth for the suggestion endpoint, rather than treating it as untestable — this is the only way to prove the endpoint returns an empty string instead of fabricating a date.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] First delivered-OS test fixture attempt produced a false-positive lock result**
- **Found during:** Task 1 verification
- **Issue:** The first fixture attempt used a bare `db_set` of `workflow_state`/`pickup_date`/`warranty_expiry` to force the OS into "Entregue" state, exactly as the plan's read_first recipe described for the *warranty* test's fixture. But my fixture then called a real `doc.save()` afterward (to prove the deadline lock), and `_validate_delivery_acceptance` (in `aceites.py`) runs on every save while `workflow_state == "Entregue"`, independently requiring either a paid `sales_invoice` or `pickup_without_repair`, plus acceptance evidence. Without those, every save failed with "Nao e possivel entregar sem nota emitida." regardless of whether `estimated_deadline` changed — so the "delivered_lock_blocked" and "untouched_save_allowed" assertions were both proving the wrong thing.
- **Fix:** Called `_deliver_warranty_test_order(editable_order)` before the `db_set`, and extended the `db_set` payload to also persist `pickup_without_repair`, `entry_signature`, `customer_signature`, and `link_acceptance_required: 0` — the same fields that helper sets in memory — so a fresh `frappe.get_doc()` load in the immutability-proof code sees a doc that passes every unrelated delivery-acceptance check and isolates the deadline lock as the only thing under test.
- **Files modified:** `tecponto_app/tecponto/frontend/test_frontend_api.py`
- **Verification:** `run_service_order_deadline_checks` — `delivered_lock_blocked: true` and `untouched_save_allowed: true` both confirmed for the correct reason (verified interactively via a temporary debug print before removing it).
- **Committed in:** `40c390c` (final atomic commit)

**2. [Rule 1 - Bug] Empty-suggestion test case initially failed on a permission check unrelated to the suggestion logic**
- **Found during:** Task 2 verification
- **Issue:** The OS created for the "nothing to compute from" case had no `technician` field assigned, so `get_service_order_deadline_suggestion`'s `doc.check_permission("read")` rejected the técnico session with `frappe.PermissionError` — an access-control failure, not a proof of the suggestion logic.
- **Fix:** Assigned the OS's `technician` field to the test técnico via `db_set` before calling the suggestion endpoint, matching the pattern already used for the durations-carrying fixture earlier in the same function.
- **Files modified:** `tecponto_app/tecponto/frontend/test_frontend_api.py`
- **Verification:** `run_service_order_deadline_checks` — `empty_suggestion_is_empty: true`.
- **Committed in:** `40c390c` (final atomic commit)

### Environment Note (not a deviation — informational only)

`./scripts/test-local.sh` needed 5 attempts to reach a clean pass, none caused by this plan's changes — all four failure signatures exactly match ones already documented in `01-01-SUMMARY.md`/`01-02-SUMMARY.md`:
1. `filelock._error.Timeout` acquiring `bench_migrate.lock` (stale lock from a prior interrupted run; removed manually).
2. On the persistent (non-reset) site: `run_technician_scope_checks` assertion failure — the same accumulated-records issue documented in `01-02-SUMMARY.md`.
3. On a freshly reset site (`TECPONTO_LOCAL_RESET=1`): `run_technician_part_request_checks` `frappe.exceptions.PermissionError: Usuário sem papel operacional.` — the exact same pre-existing failure signature documented in `01-01-SUMMARY.md` and `01-02-SUMMARY.md`.
4. Retry on the same reset site: `_pickle.PicklingError: Can't pickle <class 'frappe.model.document.LazyUser'>` inside `bench migrate`'s `after_migrate` → `sync_fixtures` → background-job enqueue path — the same Frappe/rq framework issue already documented in both prior summaries, occurring before the foundation-check suite even starts.
5. Fifth attempt passed cleanly end-to-end, including `service_order_deadline: {"status": "ok", ...}`, `warranty_delivery: {"status": "ok", ...}`, and `stage_sla_checks: {"status": "ok", ...}`.

Separately, the persistent `local-ci.local` site behind `scripts/dev-local-server.sh` continued to exhibit the same `Workflow` doctype resync bug documented in `01-01-SUMMARY.md` (the `Em diagnóstico → Diagnosticado — aguardando orçamento` transition silently disappearing after a `bench migrate`/server restart). Worked around identically each time it recurred: delete and recreate the `Workflow` doc (`frappe.delete_doc("Workflow", "Service Order", force=True)` then `ensure_service_order_workflow()`) directly against the dev-local-server's site. No `tecponto_app` source file was touched to work around this — it is a data/cache-only issue specific to the persistent dev container, confirmed unrelated because the separately-provisioned `test-local.sh` site never hit it.

---

**Total deviations:** 2 auto-fixed (both Rule 1 - test fixture bugs discovered and fixed while proving the plan's own behaviors, not scope creep), plus documented environmental flakiness consistent with prior plans in this phase.
**Impact on plan:** No production code deviated from the plan's specified action. Both auto-fixes were entirely within the new test code added by this plan, correcting the test fixtures to isolate the behavior actually under test.

## Issues Encountered
See "Environment Note" above — resolved by retrying `./scripts/test-local.sh` until a clean run was obtained, and by re-applying the documented `Workflow` doctype resync workaround against the persistent dev server whenever it recurred. No `tecponto_app` source changes were needed to reach a passing run.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DEADLINE-01 and DEADLINE-02 are both closed: the deadline is immutable from delivery onward (proven via a live `doc.save()`), the suggestion endpoint exists and is read-only/role-gated/reuses the SLA calculator, and the deadline is proven to reach the public tracking portal and all three print formats with the cost/margin/credential guard intact.
- **Pending human UAT (coverage D7):** a real browser pass confirming the tracking portal's "Previsão" block shows the saved date (not the "Atualização em breve" fallback), and that the printed orçamento and laudo técnico both show the same date. Deferred per `workflow.human_verify_mode: end-of-phase`; surface this at end-of-phase UAT alongside plan 01-01's still-open coverage D5 (técnico UI round-trip).
- Plan 01-04 (deadline-suggestion frontend display) can proceed — it builds on `get_service_order_deadline_suggestion`, the endpoint this plan just shipped.
- No blockers for the remaining phase plans.

## Self-Check: PASSED

All five modified files confirmed present on disk with the expected content (`grep -c 'Prazo estimado:' print_formats.py` → 3; `grep -n 'prazo estimado' policies.py` → 1; `grep -n 'sum_service_business_hours'` present in both `stage_sla.py` and `api.py`); commit `40c390c` confirmed present in `git log --oneline --all` and `git log -1 --stat` confirmed it touches exactly the five `files_modified`; `run_service_order_deadline_checks`, `run_warranty_delivery_checks`, and `run_stage_sla_checks` all re-confirmed `status: "ok"` after the commit; `./scripts/test-local.sh` confirmed a clean full-suite pass including this plan's section.

---
*Phase: 01-os-6-closure-warranty-verification-deadline-wiring*
*Completed: 2026-09-03*
