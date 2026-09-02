# Architecture Research — Integrating This Milestone Into the Existing Tecponto Architecture

**Domain:** Brownfield Frappe/ERPNext v16 + React ERP (phone-repair vertical) — stabilization milestone
**Researched:** 2026-09-02
**Confidence:** HIGH (all findings verified directly against the actual repository source, not general Frappe patterns)

This is not "what does a repair-shop ERP look like" research — the system already exists and is mapped in `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `CONCERNS.md`. This document answers: **how do the four milestone capabilities (audited field-edit, OS-level deadline, App.tsx/api.py split, systematic audit pass) fit into the architecture that's already there, without weakening its security gates?**

---

## Standard Architecture (Reaffirmed)

```
┌──────────────────────────────────────────────────────────────────┐
│  React 18 SPA (Vite/TS) — App.tsx (~9500 lines) + frontend/src/*  │
│  Presentation only. No business authority.                        │
└───────────────────────────┬────────────────────────────────────────┘
                             │ Frappe RPC (/api/method/…)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  API Bridge — tecponto_app/tecponto/frontend/api.py (~5300 lines) │
│  @frappe.whitelist() thin wrappers: role check → domain call →    │
│  SAFE_*_FIELDS serialization                                      │
└───────────────────────────┬────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  Domain modules — service_order/*, tradein/*, cash.py, workflow.py│
│  Business authority lives here. Frappe doc_events (hooks.py) wire │
│  validate/on_update hooks to these modules.                       │
└───────────────────────────┬────────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  Doctypes + MariaDB. Frappe workflow engine = state-machine truth │
└──────────────────────────────────────────────────────────────────┘
```

Nothing in this milestone changes this shape. Every recommendation below is "extend the existing layering," not "introduce a new layer."

---

## (a) Audit-logged field-edit for already-created records

**Finding — a working precedent already exists and should be cloned, not reinvented.** `tecponto_app/tecponto/user_access.py` implements exactly the pattern this milestone needs, for a different entity (native `User` accounts):

- Doctype `Tecponto Access Audit` (`tecponto_app/tecponto/doctype/tecponto_access_audit/tecponto_access_audit.json`): `actor`, `affected_user`, `change_type`, `occurred_on`, `before_state` (Long Text/JSON), `after_state` (Long Text/JSON). `read_only: 1` on every field, no `allow_rename`, `System Manager`-only read permission.
- Immutability enforced in Python, not just doctype flags: `hooks.py` wires `"Tecponto Access Audit": {"validate": validate_access_audit_immutable, "on_trash": prevent_access_audit_deletion}` — `validate_access_audit_immutable` throws if `not doc.is_new()`, `prevent_access_audit_deletion` always throws. This is the actual enforcement of "audit trail is append-only," and it lives in the backend per `CLAUDE.md` rule #3.
- Write path is a single private helper, `_write_audit(affected_user, change_type, before, after)`, called from every mutation point — never ad hoc `frappe.get_doc({...}).insert()` scattered around.
- **Sensitive-value handling precedent:** `audit_password_change()` never stores the credential itself — it stores the sentinel strings `{"credential": "withheld"}` → `{"credential": "changed"}`. This is the template for auditing the device-access-credential edit: the audit log must record *that* it changed and *who* changed it, never the plaintext before/after value, mirroring the existing device-credential masking pattern in `device_credentials.py`/`frontend/src/api/types.ts` (`has_device_access_credential: boolean` — frontend never sees the value, only a flag).

**Recommendation:**

1. Add a new immutable doctype, e.g. `Tecponto Service Order Edit Audit` (or generalize now as `Tecponto Field Audit` with `reference_doctype`/`reference_name` columns so it also covers future post-creation edits beyond OS) — same shape as `Tecponto Access Audit`: `actor`, `reference_name` (Service Order), `field`, `before_state`, `after_state`, `occurred_on`, immutable via the same `validate`/`on_trash` guard pair registered in `hooks.py`.
2. New domain module `tecponto_app/tecponto/service_order/post_creation_edit.py` (follows the existing `service_order/` sub-domain convention — see `budget.py`, `deadline.py`, `assignment.py`) containing an explicit **allowlist** of editable fields (`contact_name`, `contact_phone`, `device_access_type`/`device_access_credential`, customer `customer_name`/`custom_cpf` via a controlled Customer-doc update) and one function, e.g. `edit_service_order_fields(name, fields: dict) -> dict`, that:
   - Rejects any key not in the allowlist (do not accept `workflow_state` or any budget/pricing field here — that would silently reopen the "Workflow Transitions Bypassed" anti-pattern already documented in `.planning/codebase/ARCHITECTURE.md`).
   - Diffs old vs. new per field, writes one audit row per changed field (or one row with a field-list in `after_state` — match the granularity `Tecponto Access Audit` uses: one row per logical change event).
   - For `device_access_credential` specifically: never places the plaintext in `before_state`/`after_state`; stores `{"credential": "withheld"}` → `{"credential": "changed"}` exactly like `audit_password_change`.
3. `frontend/api.py` gets a thin `@frappe.whitelist()` wrapper (a few lines, role-gated with a new or existing role constant such as `CHECKIN_ALLOWED_ROLES`) that calls into the new module — keeping `api.py`'s existing "thin dispatcher" convention intact rather than adding another 100-line inline block to an already 5300-line file.
4. Frontend: a small edit affordance in the OS detail view (`ServiceOrderFlows.tsx` or a new `ServiceOrderEditModal.tsx`), masked credential input reusing the existing check-in credential-entry UX pattern from `CheckinWizard.tsx`.

**Open question to resolve in discuss-phase, not in research:** whether edits should be blocked once the OS reaches `Entregue` (post-warranty-relevant states) or always allowed-but-audited. Architecturally either is cheap (a single state check in `edit_service_order_fields`), so this is a product decision, not a technical constraint — flag it, don't pre-decide it.

**Component boundary:** `post_creation_edit.py` talks only to the Service Order doc, the new audit doctype, and (for customer fields) the Customer doc via `frappe.get_doc("Customer", ...)`. It must **not** import from `budget.py`, `workflow.py`, or `permissions.py`'s cost-guard logic — it's a narrow, single-purpose module, which is exactly what makes it safe to add without touching the fragile areas `CONCERNS.md` already flags (OS Workflow State Management, Acceptance/Evidence).

---

## (b) Single OS-level deadline composing with per-line `estimated_deadline`

**Finding — the premise needs correcting before this is built.** `estimated_deadline` is **already an OS-level field**, not a per-service-line field:

- `tecponto_app/tecponto/doctype/service_order/service_order.json` line 342: `{"fieldname": "estimated_deadline", "fieldtype": "Date", "label": "Prazo estimado"}` — one field, directly on Service Order, in the Diagnosis section. There is no per-line deadline column anywhere in the budget child table (`service_order/budget.py` has no `deadline`-named field; grep across the whole `service_order/` package confirms `estimated_deadline` never appears on a child-table doctype).
- It is already **fully wired on the read side**: `stage_clock.py` uses it to compute `is_total_overdue` (overdue-vs-now comparison against terminal states); `kanban.py` fetches it as a board field; `pending.py` (the agenda/pending-actions view) filters and orders by it (`"estimated_deadline asc, modified desc"`); `print_formats.py` prints "Prazo estimado: {{ tp.estimated_deadline }}" on two templates (laudo técnico / orçamento).
- It is **completely unwired on the write side**: it does not appear in `SAFE_SERVICE_ORDER_FIELDS` (`frontend/api.py:143`, the allowlist used for list/detail serialization), and a full-repo grep of every `.tsx` file returns **zero matches** — no input, no display, anywhere in the frontend. The only place `frontend/api.py` touches it is line 2255, `order.estimated_deadline = None`, which *clears* it (part of a reset/reopen flow) — nothing sets a real value.

**Conclusion:** the "campo novo... hoje só existe estimated_deadline por linha de serviço" framing in `PROJECT.md` does not match the code. There is no per-line deadline to compose with. There is exactly one OS-level field that already has correct overdue/kanban/print/agenda semantics wired up and is simply missing (1) a safe-field entry for API read, (2) a write path, and (3) a UI control.

**Recommendation:**

1. **Reuse `estimated_deadline`, do not add a second competing field.** Adding a genuinely new field (e.g. `os_deadline`) would create two dates with overlapping meaning, forcing every consumer of overdue logic (`stage_clock.py`, `kanban.py`, `pending.py`, print formats — four independent call sites) to pick one or reconcile both, which is exactly the kind of "things that worked stopped working" risk this milestone exists to eliminate.
2. Wire it in three small, independently testable steps (good phase-slicing):
   - Backend: add `estimated_deadline` to `SAFE_SERVICE_ORDER_FIELDS` (read path) and add it to the allowlist of fields the technician's diagnosis/budget-submission endpoint accepts (write path) — likely the same endpoint that currently handles `probable_cause`/`recommended_solution` at diagnosis time, since those sit in the same doctype section and are already technician-writable.
   - Frontend: one date input in the diagnosis/budget screen (`App.tsx` around the "Diagnóstico e orçamento" stage heading at line 4948, or wherever `ServiceOrderFlows.tsx`/diagnosis component collects `probable_cause`/`recommended_solution`), plus display of the value in Kanban card, OS detail header, and (already works) print formats.
   - Backend: role-gate the write to whoever "sets it in the orçamento" per the product decision — likely `BUDGET_ALLOWED_ROLES` (Atendente/Gestor/Técnico), consistent with how budget decisions are already gated.
3. Only if product genuinely wants **per-service-line** granularity *in addition* to the OS-wide date (e.g., "troca de tela: 2 dias" shown per budget line, rolling up to the OS date as a derived max/min) is new schema required — a `deadline` column on the budget child table plus a small aggregation function. This is materially bigger (schema migration + child-table UI + roll-up logic) and should be explicitly confirmed as wanted, not assumed, before scoping a phase around it. Recommend surfacing this distinction directly to the user during roadmap/discuss-phase rather than silently picking one interpretation.
4. Keep the fieldname `estimated_deadline` (only change is wiring it up + maybe the label) to avoid touching the four existing call sites (`stage_clock.py`, `kanban.py`, `pending.py`, `print_formats.py`) that already reference the string correctly.

**Data flow for this feature once wired:**
```
Technician (diagnosis/budget screen)
   → PUT estimated_deadline via new/extended API method (role-gated)
   → doc.save() — Service Order.estimated_deadline persisted
   → read by: stage_clock.set_stage_entered_at() [overdue calc]
              kanban.py [board sort/badge]
              pending.py [agenda ordering]
              print_formats.py [printed documents]
   → displayed to: Kanban card, OS detail, printed orçamento/laudo
```
No new component boundary is introduced — this is filling in a gap in an existing, already-correct data flow.

---

## (c) Safely splitting App.tsx / api.py mid-stabilization

**Principle, grounded in the project's own stated process (`CLAUDE.md` §2):** "tarefas pequenas e atômicas," "testar comportamento real de ponta a ponta," "commit isolado por tarefa." A big-bang App.tsx/api.py rewrite violates all three at once — it's one giant diff, hard to test behaviorally end-to-end in one pass, and impossible to commit atomically. The architecture answer is **sequencing and boundary discipline**, not a rewrite plan.

**Sequencing recommendation — refactor follows audit, area by area, never precedes it:**

1. Run the systematic audit (item d) against the **current** file structure first, while it still has whatever test coverage exists. Fixing bugs in the existing shape keeps risk isolated to logic, not logic-plus-structure simultaneously.
2. Only *after* an area (e.g. PDV) has fresh passing `run_pos_*_checks()` coverage, extract that area's functions out of `api.py`/`App.tsx` in a **separate, mechanical commit** with no logic changes — then immediately re-run that area's tests to prove behavior parity before moving to the next area.
3. Never mix "extract module" commits with "change behavior" commits. This is a direct application of the existing "commit isolado por tarefa" rule to structural work.

**Backend split — the codebase already demonstrates the target shape; extend it, don't invent a new one.** `service_order/*.py` (budget, parts, payments, billing, commission, assignment, aceites, print_formats, stage_clock, stage_sla, deadline, device_credentials, inoperative_device, kanban) and `tradein/*.py` are already properly decomposed domain modules; `api.py`'s job is supposed to be a thin dispatcher (role-check → call domain function → serialize with a `SAFE_*_FIELDS` allowlist), and mostly is. The 5300 lines accumulated because *new* logic was sometimes written inline in `api.py` instead of in a domain module. Two moves:
   - **New capabilities in this milestone go straight into new small domain modules** (`post_creation_edit.py` for item a; extend `deadline.py` for item b) with only a thin wrapper in `api.py` — this stops the file from growing further rather than shrinking it, but it's the cheapest correct move available right now.
   - **The highest-risk part of splitting the existing 5300 lines is the whitelist dotted-path.** Frappe resolves `@frappe.whitelist()` methods by their fully-qualified dotted path (`tecponto_app.tecponto.frontend.api.<method_name>`), and the React client calls that exact string (see `frontend/src/api/client.ts` + each `frontend/src/api/*.ts` module). Moving a function to `service_order_api.py`/`pos_api.py`/`financial_api.py`/`product_api.py` changes its RPC path. Any such move must update the frontend's call site in the **same commit** and be verified through the full 3-stage CI (the project's own stated "verdade final de integração"), not just a local smoke test — a silent path mismatch would surface as a 404 in production, exactly the "things that worked stopped working" failure mode this milestone is meant to prevent.

**Frontend split — also has a demonstrated target shape already.** `frontend/src/*Screen.tsx` (CheckinWizard, ServiceOrderKanban, ServiceOrderFlows, PosScreen, QuotesCrmScreen, 30+ files) is the extracted-screen pattern; `App.tsx`'s 9500 lines are mostly still-inline screens plus router/dispatch glue that hasn't been extracted yet. Same rule as backend: extract one role-panel branch at a time into its own `*Screen.tsx`, verify that panel manually end-to-end for each of the four roles it's visible to, commit, move to the next branch. `React.lazy()` + `Suspense` per newly-extracted screen is a natural way to also chip at the 861 kB bundle-size warning already logged in `CONCERNS.md` — but bundle size should be a **side effect** of the correctness-driven split, not the reason to reorder it.

**Test-file split as a safe warm-up.** `test_frontend_api.py` (8745 lines) has the exact same problem as the two production files, but splitting it is much lower risk (no production behavior at stake) — recommend doing this first, splitting by the same domain boundaries (`test_pos_api.py`, `test_tradein_api.py`, `test_warranty_api.py`, `test_cash_api.py`, shared fixtures in `conftest.py`). This both reduces immediate pain and rehearses the exact domain boundaries that the later `api.py` split should follow.

---

## (d) Structuring the systematic audit pass (PDV/trade-in/warranty/caixa) for regression coverage, not just a bug list

**The project already has a proven mechanism for this — the OS-cycle audit that just happened.** `AUDITORIA_SISTEMA.md` describes exactly the loop to repeat: real (non-fixture) end-to-end walk of the flow in-role → log numbered findings → fix in small commits → encode the flow permanently as a `run_<area>_checks()` function in the test suite. `test_frontend_api.py` already contains 60+ such functions (e.g. `run_technician_assignment_checks`, `run_warranty_mode_checks`, `run_pos_sale_checks`, `run_cash_session_checks`) — this is a stable, scaling pattern (one broad integration-style check function per flow, not micro unit tests), and it already partially covers three of the four target areas:

| Area | Existing check functions (partial coverage found) |
|------|-----------------------------------------------------|
| PDV | `run_pos_sale_checks`, `run_pos_barcode_label_checks`, `run_pos_retail_barcode_catalog_checks`, `run_pos_cash_integration_checks` |
| Trade-in | `run_tradein_frontend_checks` |
| Warranty | `run_warranty_mode_checks`, `run_warranty_delivery_checks` |
| Caixa | `run_cash_session_checks`, `run_cash_closing_checks`, `run_service_order_cash_checks` |

**Implication for the roadmap: this is not a from-scratch test-authoring effort.** The audit's real job in each area is to walk the actual UI/role flow and find where production behavior diverges from what these existing check functions assert (they may be stale, incomplete, or passing against a narrower path than the real one) — then extend or harden them, following the same "found bug → fixed → encoded as permanent check" loop, not just widen coverage in the abstract.

**Recommended audit order, based on actual data-flow dependencies between the four areas (not an arbitrary list order):**

1. **PDV first.** Self-contained relative to the others; also the origin of `sales_invoice`/cash-movement writes the other areas depend on.
2. **Trade-in second.** `tradein/buyback.py` creates purchase/inventory records that PDV *can* later sell, but core PDV sale-flow testing doesn't require traded-in stock specifically — testing trade-in next (rather than folding it into PDV) keeps its evaluation/buyback/cannibalization state machine (`tradein/workflow.py`) isolated and auditable on its own, before its output is trusted as an input to anything else.
3. **Warranty third.** Depends on a correctly-delivered OS (`Entregue` state, `pickup_date`) — already exercised by the OS-cycle audit that just finished — so it's the cheapest of the remaining three to validate now; `service_order/policies.py`'s 90-day rule is the concrete target (`CONCERNS.md`'s own recommended test: create OS → deliver → day 91 warranty attempt should fail, day 89 should pass).
4. **Caixa last.** `cash.py` is the aggregation point — it records movements triggered by both PDV sales invoices and OS pickups/payments (`record_sales_invoice_cash_movements`, hooked from `on_update`/billing flows). Reconciliation bugs in caixa are often actually upstream bugs in PDV or OS payment recording surfacing at close-out. Auditing caixa before the other three are verified risks chasing symptoms instead of causes; auditing it last, once PDV/trade-in/warranty are already known-correct, means any caixa discrepancy found is more likely a genuine caixa-layer bug.

**Component boundaries relevant to this ordering:**

```
PDV (pos.py, frontend/pos.py) ──sales_invoice──┐
Trade-in (tradein/*.py) ──inventory (optional)──┤
Service Order pickup/warranty (service_order/*, policies.py) ──payment/delivery──┤
                                                                                  ▼
                                                                    Cash (cash.py) — aggregation
```

**Output structure per area (repeatable, matches the existing `AUDITORIA_SISTEMA.md` shape):** numbered findings log → atomic fix commit(s) referencing finding numbers → one new/extended `run_<area>_checks()` landed in the (now-split, per item c) domain-specific test file → CI green before moving to the next area. This is what turns "audit" into "regression coverage" rather than a one-time bug hunt: the check function is what survives after the audit session ends.

---

## Anti-Patterns to Avoid in This Milestone

### Anti-Pattern: Generic "edit any field" endpoint
**What people do:** Build one flexible `update_service_order(name, fields: dict)` endpoint that accepts arbitrary field names from the frontend, for convenience.
**Why it's wrong:** Directly reopens the documented "Workflow Transitions Bypassed" anti-pattern — an arbitrary-field endpoint is a backdoor around `move_service_order()`'s transition validation and around the cost-guard field allowlists.
**Do this instead:** A narrow, explicit allowlist per edit capability (contact fields, device credential, customer identity), each in its own small function, as described in (a).

### Anti-Pattern: Refactor-then-audit
**What people do:** Split App.tsx/api.py first "to make the audit easier to navigate," then audit the new structure.
**Why it's wrong:** Combines two independent sources of risk (structural move + behavioral bug) in the same window, with no passing regression coverage yet to prove the move didn't change behavior — exactly the failure mode ("muitas alterações anteriores deixaram o sistema mais confuso") this milestone exists to stop.
**Do this instead:** Audit against current structure, build regression coverage per area, then extract that area — per (c) and (d) above.

### Anti-Pattern: Treating estimated_deadline as needing new schema without checking existing wiring
**What people do:** Add a new `os_deadline`/`prazo_os` field because the requirement doc says "campo novo."
**Why it's wrong:** Creates two overlapping date fields, forcing four independent consumers (`stage_clock.py`, `kanban.py`, `pending.py`, `print_formats.py`) to reconcile which one is authoritative — a self-inflicted version of the exact "confusão" the milestone is trying to eliminate.
**Do this instead:** Wire up the existing `estimated_deadline` field (read allowlist + write path + UI) per (b), confirmed against actual grep evidence that it is unused, not per-line.

---

## Build/Audit Order Summary (for roadmap phase sequencing)

1. **Warranty 90-day end-to-end verification** (closes an already-open OS.6 item, no structural risk, cheapest win, uses existing `policies.py` + extends `run_warranty_mode_checks`).
2. **OS-level `estimated_deadline` wiring** (b) — small, additive, no schema change, no refactor dependency.
3. **Audited field-edit capability** (a) — new isolated module + new audit doctype, cloned from the proven `user_access.py`/`Tecponto Access Audit` pattern; independent of (2).
4. **Systematic audit pass** (d), in the dependency order PDV → Trade-in → Warranty (already partly covered by step 1) → Caixa, each area landing its own regression checks.
5. **Incremental structural split** (c) of `api.py`/`App.tsx`/`test_frontend_api.py`, area-by-area, strictly trailing each area's audit in step 4 — never ahead of it.
6. Design-system application pass — explicitly out of scope for this document; per `CLAUDE.md` design §3 and `PROJECT.md` Active items, this is a separate, later, single-pass phase after 1–5 are stable, not interleaved with them.

Steps 1–3 have no ordering dependency on each other and can be sequenced/parallelized freely; step 4 has an internal order (justified above); step 5 must trail step 4 area-by-area; step 6 trails everything.

---

## Sources

- `tecponto_app/tecponto/user_access.py` (audit-doctype precedent, immutability enforcement pattern)
- `tecponto_app/tecponto/doctype/tecponto_access_audit/tecponto_access_audit.json` (audit doctype shape)
- `tecponto_app/hooks.py` lines 270–329 (doc_events wiring for audit immutability and Service Order hooks)
- `tecponto_app/tecponto/doctype/service_order/service_order.json` (confirms `estimated_deadline` is OS-level, not per-line)
- `tecponto_app/tecponto/service_order/stage_clock.py`, `kanban.py`, `pending.py`, `print_formats.py` (confirmed read-side usage of `estimated_deadline`)
- `tecponto_app/tecponto/frontend/api.py` lines 143–163 (`SAFE_SERVICE_ORDER_FIELDS`), line 2255 (only write touches `estimated_deadline`, and only to clear it)
- Full-repo grep of `frontend/src/**/*.tsx` for `estimated_deadline` — zero matches (confirms no UI wiring exists)
- `tecponto_app/tecponto/service_order/device_credentials.py`, `frontend/src/api/types.ts` (`has_device_access_credential` masking precedent)
- `tecponto_app/tecponto/frontend/test_frontend_api.py` — `run_*_checks()` function inventory (confirms existing partial coverage for PDV/trade-in/warranty/caixa)
- `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `CONCERNS.md` (this session's prior codebase mapping — required reading, treated as ground truth for the "current state" baseline)
- `.planning/PROJECT.md` (milestone requirements and prior key decisions)

---
*Architecture research for: Tecponto ERP stabilization milestone (audit-logged edit, OS deadline, App.tsx/api.py split, systematic audit pass)*
*Researched: 2026-09-02*
