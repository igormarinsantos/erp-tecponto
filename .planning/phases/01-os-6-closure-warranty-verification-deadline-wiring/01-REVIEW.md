---
phase: 01-os-6-closure-warranty-verification-deadline-wiring
reviewed: 2026-09-03T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - tecponto_app/tecponto/frontend/api.py
  - tecponto_app/tecponto/frontend/test_frontend_api.py
  - tecponto_app/tecponto/service_order/policies.py
  - tecponto_app/tecponto/service_order/print_formats.py
  - tecponto_app/tecponto/service_order/stage_sla.py
  - frontend/src/App.tsx
  - frontend/src/ServiceOrderKanban.tsx
  - frontend/src/api/serviceOrders.ts
  - frontend/src/api/types.ts
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: fixed
fixed: 2026-09-03T00:00:00Z
fixed_commit: f39c371
---

# Phase 1: Code Review Report

**Reviewed:** 2026-09-03
**Depth:** standard
**Files Reviewed:** 9
**Status:** fixed (both warnings resolved directly in commit `f39c371`; info notes left as-is per their own "not worth a standalone change" recommendation)

## Summary

Reviewed the diff between `046bd4d` and `HEAD` (branch `version-16`) for the `estimated_deadline` write path added by this phase: the new `set_service_order_estimated_deadline` / `get_service_order_deadline_suggestion` RPC endpoints, the widened `SAFE_SERVICE_ORDER_FIELDS`/serializers, the `estimated_deadline` entry added to `_validate_delivery_dates_are_immutable`, the new `sum_service_business_hours` helper, the laudo técnico print line, and the frontend wiring in `App.tsx` / `ServiceOrderKanban.tsx` / `api/serviceOrders.ts` / `api/types.ts`.

Cross-checked against the three non-negotiable project rules:
- **Cost/margin guard:** `estimated_deadline` is a `Date` field, unrelated to cost/margin/valuation. It was added consistently to `SAFE_SERVICE_ORDER_FIELDS`, `_serialize_service_order`, `get_service_order_detail`, `get_service_order_kanban`, the public portal payload (`tracking.py`, pre-existing, not touched this phase) and all three print contexts. No cost/margin field was widened alongside it. No leak found.
- **Device credential guard:** Not touched by this diff. `_save_device_access_credential` and password-masking paths are untouched.
- **Backend-enforced locks:** Both new gates are enforced server-side, not just hidden in the UI:
  - `_require_technician_deadline_role()` restricts the RPC to `System Manager` / `Tecponto Tecnico` roles, called before any other logic in both new endpoints.
  - `doc.check_permission("write"/"read")` additionally scopes a role-only-Técnico user to *their own assigned* Service Order via the existing `service_order_has_permission` hook (`tecponto_app/tecponto/permissions.py`), so a técnico cannot write another técnico's OS deadline just by holding the role.
  - The workflow-stage gate (`workflow_state == STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO`) and the delivered-OS immutability lock (`_validate_delivery_dates_are_immutable`) are both enforced inside `policies.py`/`api.py`, independent of any frontend check — confirmed this matches documented design decisions D-02/D-03/D-04 in `01-CONTEXT.md`.

No BLOCKER-level defects found. Two WARNING-level robustness gaps and two INFO-level quality notes below.

## Warnings

### WR-01: "Salvar prazo" button allows submitting an empty deadline, guaranteeing a doomed round trip — ✅ FIXED (`f39c371`)

**File:** `frontend/src/App.tsx:4177`
**Issue:** The save button is only disabled by `busy || suggesting`:
```tsx
<Button disabled={busy || suggesting} onClick={async () => { setBusy(true); try { const response = await serviceOrders.setEstimatedDeadline(serviceOrder, deadline); ... } ... }}>Salvar prazo</Button>
```
If the suggestion fetch fails or returns no date (`suggested_delivery_date === ""`, a case the backend explicitly supports — see `run_service_order_deadline_checks`'s "empty suggestion" case) and the técnico does not type a date, `deadline` stays `""`. The button remains clickable, the RPC call fires, and the backend always rejects it with `frappe.throw(_("Prazo estimado inválido."))`. This is not a security or data-integrity problem (the backend correctly rejects it), but it is a guaranteed-to-fail action reachable from the UI with no client-side guard — exactly the "button that appears but doesn't do anything useful" class of issue the project's rite of work (CLAUDE.md §2.2) calls out.
**Fix:**
```tsx
<Button disabled={busy || suggesting || !deadline} onClick={...}>Salvar prazo</Button>
```

### WR-02: No lower-bound validation lets a técnico save a past-dated `estimated_deadline`, instantly marking the OS overdue — ✅ FIXED (`f39c371`, plus a new `past_date_rejected` assertion in `run_service_order_deadline_checks`)

**File:** `tecponto_app/tecponto/frontend/api.py:1974-1995` (backend), `frontend/src/App.tsx:4177` (frontend `<input type="date">` has no `min`)
**Issue:** `set_service_order_estimated_deadline` only validates that the input parses as a date (`getdate(...)`); it never checks that the parsed date is `>= nowdate()`. `stage_clock.py`'s existing overdue computation (`is_total_overdue = bool(estimated_deadline and now > estimated_deadline and state not in TERMINAL_STATES)`) will immediately flag the OS as overdue the instant a past date is saved — e.g., a técnico typo of `2025-09-03` instead of `2026-09-03` silently produces an "atrasada" OS with no error, no confirmation, and no visual warning before the save completes. It is correctable (the endpoint permits re-saving while the OS is still in the budget stage), but nothing catches the mistake at entry time.
**Fix:** Reject or at least warn on a parsed date earlier than `nowdate()` in the backend endpoint, and mirror it with `min={new Date().toISOString().slice(0, 10)}` on the frontend `<input type="date">`.

## Info

### IN-01: `set_service_order_estimated_deadline`'s date parsing swallows all exceptions indiscriminately

**File:** `tecponto_app/tecponto/frontend/api.py:1979-1983`
**Issue:**
```python
try:
    parsed_deadline = getdate(estimated_deadline) if (estimated_deadline or "").strip() else None
except Exception:
    parsed_deadline = None
if not parsed_deadline:
    frappe.throw(_("Prazo estimado inválido."), frappe.ValidationError)
```
The bare `except Exception` is functionally fine here (any parse failure correctly becomes a `ValidationError`), but it is broad enough to also mask genuine bugs (e.g. an `AttributeError` from an unexpected payload type) as "invalid date," which slightly increases the cost of future debugging. This mirrors an existing pattern elsewhere in the file, so it's a minor consistency note rather than a new anti-pattern.
**Fix:** Narrow to `except (ValueError, TypeError):` if this endpoint is revisited; not worth a standalone change today.

### IN-02: `frontend/src/api/serviceOrders.ts` import block mixes tabs and spaces around the new `ServiceOrderDeadlineSuggestion` entry

**File:** `frontend/src/api/serviceOrders.ts:11`
**Issue:** The new import line is tab-indented while sibling lines in the same `import type { ... }` block use two-space indentation (a pre-existing inconsistency in this file that the new line continues rather than introduces):
```ts
	ServiceOrderDeadlineSuggestion,
	ServiceOrderDetailResponse,
  ServiceOrderKanbanResponse,
```
**Fix:** Normalize to the file's dominant indentation style (spaces) next time this block is touched; not worth a standalone whitespace-only diff.

---

_Reviewed: 2026-09-03_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
