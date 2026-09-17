---
phase: 03-systematic-audit-pdv-trade-in-warranty-aparelho-usado-caixa
plan: 04
subsystem: used-device-warranty
tags: [frappe, python, service-order, used-device-warranty, validation-gate, check-in]

# Dependency graph
requires:
  - phase: 03-01
    provides: used_device_warranty_lookup baseline in run_foundation_checks (consultar_garantia_usado's read-only role gate)
provides:
  - "Service Order carries used_device_warranty (Link) and used_device_warranty_no_charge (Check), both read-only, server-set only"
  - "is_warranty_active(warranty_name, reference_date) — the single role-free expiry comparison, reused by consultar_garantia_usado and by the validate hook"
  - "_validate_used_device_warranty_no_charge, called from validate_repare_rules: an OS marked no-charge under used-device warranty cannot carry a positive grand_total, an unlinked warranty, or an inactive one"
  - "_apply_used_device_warranty_coverage, called unconditionally from create_service_order_checkin: looks up the device's serial, links a covered warranty and zeros the OS automatically, or lets an expired one fall through to a normal charged OS with a recorded reason"
affects: []

# Actuals (#2632)
actuals:
  tokens: 3500
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single source of truth for an expiry comparison shared across a role-gated read path and a role-free validate hook: is_warranty_active(warranty_name, reference_date) lives in used_device_warranty.py; consultar_garantia_usado computes under_warranty through it instead of duplicating the getdate(expiry) >= getdate(reference) comparison"
    - "A dedicated no-charge marker instead of reusing an existing courtesy flag when the existing flag carries an incompatible role gate: used_device_warranty_no_charge is new precisely because courtesy_warranty is gated behind _field_became_true + manager-only, which would reject every Atendente check-in"
    - "Coverage decided entirely server-side at claim time, from the stored warranty record, evaluated against entry_date (not today) — the client payload carries no coverage flag the check-in could assert"

key-files:
  created: []
  modified:
    - tecponto_app/tecponto/doctype/service_order/service_order.json
    - tecponto_app/tecponto/used_device_warranty.py
    - tecponto_app/tecponto/service_order/policies.py
    - tecponto_app/tecponto/frontend/api.py
    - tecponto_app/tecponto/frontend/test_frontend_api.py

key-decisions:
  - "used_device_warranty and used_device_warranty_no_charge are both read_only:1 in the doctype JSON — the counter never types them; only the server (check-in helper) sets them, and the validate hook is the only place that can reject them."
  - "_apply_used_device_warranty_coverage runs unconditionally after the existing is_warranty/original_service_order branch, regardless of whether that branch fired — per the plan, the lookup needs no new payload flag and no React change; a device with no used-device warranty record is simply untouched."
  - "consultar_garantia_usado's PermissionError is allowed to surface uncaught from _apply_used_device_warranty_coverage — if CHECKIN_ALLOWED_ROLES and WARRANTY_LOOKUP_ROLES ever drift apart, check-in must fail loudly rather than silently skip coverage."
  - "Task 3 is a single commit (test-only), not a RED/GREEN pair, because the production code it proves was already built and committed in Tasks 1-2 — matching the same precedent set in 03-03's Task 2 (gate + proof landed together)."

patterns-established:
  - "is_warranty_active(warranty_name, reference_date=None) as the one place the used-device-warranty expiry comparison lives — any future caller (role-gated or not) goes through this helper, never re-derives getdate(expiry) >= getdate(reference)."

requirements-completed: [AUDIT-05]

coverage:
  - id: D1
    description: "Checking in a device whose Used Device Warranty is still inside its window (89 days ahead) produces an OS automatically marked no-charge, linked to the warranty record"
    requirement: "AUDIT-05"
    verification:
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_used_device_warranty_claim_checks -> covered_no_charge: true, covered_warranty == covered order's used_device_warranty"
        status: pass
    human_judgment: false
  - id: D2
    description: "Checking in a device whose Used Device Warranty has expired (1 day past) produces an ordinary charged OS with a recorded reason, per D-04"
    requirement: "AUDIT-05"
    verification:
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_used_device_warranty_claim_checks -> expired_charged_normally: true, expiry date found in attendance_notes"
        status: pass
    human_judgment: false
  - id: D3
    description: "A Service Order marked no-charge under used-device warranty cannot carry a positive grand_total — the server refuses the save"
    requirement: "AUDIT-05"
    verification:
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_used_device_warranty_claim_checks -> covered_priced_save_blocked: true (add_service_order_budget_line raised frappe.ValidationError)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A serial with no used-device warranty record produces an OS byte-identical to today's behavior"
    requirement: "AUDIT-05"
    verification:
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_used_device_warranty_claim_checks -> no_warranty_order created with both fields unset, nothing raised"
        status: pass
    human_judgment: false
  - id: D5
    description: "The covered OS's payload carries no cost, margin or profit field"
    requirement: "AUDIT-05"
    verification:
      - kind: integration
        ref: "run_used_device_warranty_claim_checks -> leaked_fields: []"
        status: pass
    human_judgment: false
  - id: D6
    description: "The doctype JSON schema change (two new fields) migrates cleanly and the existing lookup/delivery suites are unaffected by the is_warranty_active refactor"
    requirement: "AUDIT-05"
    verification:
      - kind: integration
        ref: "bench --site local-ci.local migrate; run_used_device_warranty_lookup_checks; run_warranty_delivery_checks"
        status: pass
    human_judgment: false
  - id: D7
    description: "The check-in helper does not disturb ordinary check-in behavior or the existing repair-warranty-mode path"
    requirement: "AUDIT-05"
    verification:
      - kind: integration
        ref: "run_os2_checkin_choice_checks; run_warranty_mode_checks"
        status: pass
    human_judgment: false

duration: 65min
completed: 2026-09-17
status: complete
---

# Phase 3 Plan 04: Used-Device Warranty Claim Enforcement (AUDIT-05) Summary

**A used-device warranty is now a real, server-checked claim at repair time: check-in links a covered warranty and zeros the budget automatically, an expired one falls through to an ordinary charged OS with a recorded reason, and the engine refuses to let the no-charge marker coexist with a charge**

## Performance

- **Duration:** ~65 min
- **Started:** 2026-09-17
- **Completed:** 2026-09-17
- **Tasks:** 3 / 3
- **Files modified:** 5
- **Commits:** 3

## Task Commits

1. **Task 1 — the no-charge marker field and the engine rule:** `312eb9a` — added `used_device_warranty` (Link, read-only) and `used_device_warranty_no_charge` (Check, read-only) to the Service Order `warranty_section`; added `is_warranty_active(warranty_name, reference_date)` to `used_device_warranty.py` and refactored `consultar_garantia_usado` to compute `under_warranty` through it; added `_validate_used_device_warranty_no_charge` to `policies.py`, called from `validate_repare_rules` right after `_validate_warranty`.
2. **Task 2 — link and apply coverage at check-in (D-03, D-04):** `5b7a65a` — added `_apply_used_device_warranty_coverage(order, device_name)`, called unconditionally in `create_service_order_checkin` after the existing `is_warranty`/`original_service_order` block and before `order.insert(...)`; surfaced both new fields on the Service Order detail payload's `warranty` block.
3. **Task 3 — prove claim-time enforcement in CI (TDD):** `41cbe82` — added `run_used_device_warranty_claim_checks`, wired into `run_foundation_checks` as `used_device_warranty_claim`; proves all three cases (covered/89 days, expired/-1 day, no warranty) plus the priced-save rejection and the sensitive-field guard.

## Verification Results

```
bench --site local-ci.local migrate: EXIT 0, no errors (after removing one stale
bench_migrate.lock left by an earlier container crash mid-migration — see Issues Encountered)

run_used_device_warranty_lookup_checks:
{"warranty": "UDW-00330", "attendant_allowed": true, "technician_blocked": true, "guest_blocked": true}

run_warranty_delivery_checks:
{"status": "ok", "pickup_date": "2026-09-17", "original_warranty_expiry": "2026-12-16",
 "rework_inherits_original_expiry": true, "different_defect_is_normal": true,
 "different_defect_manual_value": 137.45, "customer_part_excluded_from_warranty": true,
 "new_configured_warranty_expiry": "2026-10-17", "screen_queries": ["customer", "imei", "os"],
 "expired_opens_normal_charged": true, "boundary_day_89_allowed": true,
 "boundary_day_90_allowed": true, "boundary_day_91_blocked": true}

run_os2_checkin_choice_checks:
{"status": "ok", "credential_types": ["Alfanumérica", "PIN", "Padrão de desenho"],
 "initial_budget_persisted": true, "conditional_entry_term": true}

run_warranty_mode_checks:
{"status": "ok", "proactive_warranty_candidate": "OS-2026-00121", "warranty_order": "OS-2026-00122",
 "original_service_order": "OS-2026-00121", "labor_price": 0.0, "catalog_service": "TPS-00344",
 "part_stock_entry": "MAT-STE-2026-00069", "part_qty_before": 13.0, "part_qty_after": 12.0,
 "part_cost_recorded": true, "sensitive_guard": {"leaked_fields": []}}

run_used_device_warranty_claim_checks (the three claim cases):
{"covered_warranty": "UDW-00346", "covered_order": "OS-2026-00123", "covered_no_charge": true,
 "covered_priced_save_blocked": true,
 "expired_warranty": "UDW-00349", "expired_order": "OS-2026-00124", "expired_charged_normally": true,
 "no_warranty_order": "OS-2026-00125", "leaked_fields": []}
```

**The three claim-time cases, called out explicitly:**
- **Covered (89 days ahead):** `covered_order` `OS-2026-00123` created with `used_device_warranty_no_charge` truthy and `used_device_warranty` == `UDW-00346`; a subsequent priced budget line + save raised `frappe.ValidationError` (`covered_priced_save_blocked: true`).
- **Expired (1 day in the past):** `expired_order` `OS-2026-00124` created with both fields unset; the expiry date (`UDW-00349`'s `warranty_expiry`) landed in `attendance_notes`; a priced budget line + save succeeded normally (`expired_charged_normally: true`, `grand_total` > 0).
- **No warranty:** `no_warranty_order` `OS-2026-00125` created with both fields unset, nothing raised — byte-identical to pre-plan behavior.

`run_foundation_checks` was attempted end-to-end but aborted before reaching `used_device_warranty_claim` — see Issues Encountered. Wiring was confirmed by direct grep instead (both the assignment at line 350 and the return-dict key at line 435 are present) plus the standalone pass above.

## Files Created/Modified
- `tecponto_app/tecponto/doctype/service_order/service_order.json` — `used_device_warranty` (Link -> Used Device Warranty, read-only) and `used_device_warranty_no_charge` (Check, read-only) added to `warranty_section`, immediately after `courtesy_warranty_reason` in both `field_order` and `fields`.
- `tecponto_app/tecponto/used_device_warranty.py` — new `is_warranty_active(warranty_name, reference_date=None)`; `consultar_garantia_usado` now computes `under_warranty` through it instead of a second inline comparison.
- `tecponto_app/tecponto/service_order/policies.py` — new `_validate_used_device_warranty_no_charge`, called from `validate_repare_rules` after `_validate_warranty`.
- `tecponto_app/tecponto/frontend/api.py` — new `_apply_used_device_warranty_coverage`, called from `create_service_order_checkin`; Service Order detail payload's `warranty` block now includes `used_device_warranty` and `used_device_warranty_no_charge`.
- `tecponto_app/tecponto/frontend/test_frontend_api.py` — new `run_used_device_warranty_claim_checks`, wired into `run_foundation_checks` next to `used_device_warranty_lookup`.

## Deviations from Plan

None — plan executed exactly as written. Both design facts flagged in the plan's `<context>` (the dedicated field instead of reusing `courtesy_warranty`; the role-free `is_warranty_active` helper for the validate hook) were followed verbatim, not re-litigated.

## Issues Encountered

1. **Stale `bench_migrate.lock` after a mid-migration container crash.** The `tecponto-local-server` container exited (`ExitCode=255`) once during Task 1's `bench --site local-ci.local migrate`, consistent with the documented pre-existing Docker Desktop/WSL2 host RAM constraint (see `03-01-SUMMARY.md`, `03-03-SUMMARY.md`). Bringing the container back up with `./scripts/dev-local-server.sh up` was not sufficient on its own this time — the crash left `/home/frappe/frappe-bench/sites/local-ci.local/locks/bench_migrate.lock` behind, and the retried migrate failed immediately with `LockTimeoutError` rather than re-attempting the migration. Removed the stale lock file (`rm -f .../locks/bench_migrate.lock`) — safe because the crash meant no migration process was still holding it — then the retried migrate completed cleanly with no errors. No code change; purely an artifact of the environmental crash.
2. **`run_foundation_checks` did not reach `used_device_warranty_claim`.** The suite aborted earlier, inside `run_technician_scope_checks`, with `AssertionError: Contador de OS do técnico ignorou o escopo da atribuição.` This is the exact known, pre-existing, unrelated local-data-volume issue already documented in `03-01-SUMMARY.md` (key-decisions: "an accumulated fixture count exceeding `list_service_orders`' pagination limit... does not reproduce on a fresh CI site"). Confirmed unrelated to this plan by running `run_technician_scope_checks` standalone — it fails identically, with the same assertion, independent of any file this plan touches. Per this plan's own execution instructions, this is not this plan's problem to fix. Verified the new function's wiring instead via: (a) standalone `run_used_device_warranty_claim_checks` passing all three cases plus the sensitive-field guard, and (b) direct source inspection confirming both the `run_foundation_checks` assignment and its return-dict key are present.

## Next Phase Readiness

AUDIT-05 is closed. This was the last numbered plan of Phase 3 (AUDIT-01 through AUDIT-05 all complete: 03-01 wired the 4 orphaned PDV/warranty-mode tests plus the cash concurrent-session proof; 03-02 audited the cost/margin guard; 03-03 closed the trade-in checklist gap; 03-04 built the used-device-warranty claim enforcement described here). `used_device_warranty` and `used_device_warranty_no_charge` are now part of the Service Order contract for any later phase.

## Self-Check: PASSED

All 5 modified source files and this SUMMARY.md confirmed present on disk; all 3 task commits (`312eb9a`, `5b7a65a`, `41cbe82`) confirmed in `git log`.

---
*Phase: 03-systematic-audit-pdv-trade-in-warranty-aparelho-usado-caixa*
*Completed: 2026-09-17*
