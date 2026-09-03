# Phase 1: OS.6 Closure — Warranty Verification & Deadline Wiring - Pattern Map

**Mapped:** 2026-09-03
**Files analyzed:** 8 (3 backend new/modified, 1 test extension, 4 frontend new/modified — one frontend surface, tracking.js, requires zero change per UI-SPEC)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tecponto_app/tecponto/frontend/api.py` — new `set_service_order_estimated_deadline` (or similarly named) whitelisted endpoint | controller (whitelisted RPC handler) | request-response / CRUD (single-field write) | `add_service_order_budget_line` (`api.py:1877-1960`) + `_require_budget_edit_role` (`api.py:282-286`) | exact (same file, same stage, same role-gate pattern, same doc-level single-field write shape) |
| `tecponto_app/tecponto/service_order/policies.py` — extend `_validate_delivery_dates_are_immutable` to cover `estimated_deadline` | model/validation hook | event-driven (doc `validate` lifecycle hook) | `_validate_delivery_dates_are_immutable` itself (`policies.py:135-146`) | exact — this is a targeted extension of the existing function, not a new one |
| `tecponto_app/tecponto/frontend/test_frontend_api.py` — extend `run_warranty_delivery_checks` | test | request-response (integration/end-to-end assertion) | `run_warranty_delivery_checks` itself (`test_frontend_api.py:2528-2711`) | exact — extension, not new function (per D-01) |
| `frontend/src/App.tsx` — new deadline `<input type="date">` inside `TechnicalBudgetEditor` | component (form control) | request-response (fetch suggestion → user edits → save) | `TechnicalBudgetEditor` itself (`App.tsx:4122-4165`), specifically the `customerPartDescription` input + its inline save button (`App.tsx:4160`) | exact — same component, same inline-input-plus-button idiom already used for the "Adicionar do cliente" control |
| `frontend/src/App.tsx` — new `DetailLine` row in `ServiceOrderPersistentOverview` | component (read-only display row) | request-response (render from already-fetched detail) | `ServiceOrderPersistentOverview`'s existing "Prazo atual" `DetailLine` (`App.tsx:4468`) | exact — literally the row directly above/beside where the new row is added, same component |
| `frontend/src/ServiceOrderKanban.tsx` — new `CardLine` row in `KanbanCard` | component (read-only display row) | request-response (render from already-fetched summary) | Existing `CardLine` rows in `KanbanCard` (`ServiceOrderKanban.tsx:544-549`), `CardLine` helper itself (`ServiceOrderKanban.tsx:568-574`) | exact — same card, same helper, add a 5th sibling row |
| `frontend/src/api/serviceOrders.ts` — new API client method | service (RPC client wrapper) | request-response | `addTechnicalBudgetLine` (`serviceOrders.ts:53-55`) and neighboring `serviceOrders` object methods | exact — same file, same `rpc<T>(...)` wrapper idiom |
| `frontend/src/api/types.ts` — new top-level `estimated_deadline` field on `ServiceOrderSummary` / `ServiceOrderDetailResponse` | type/model definition | n/a (type contract) | `approval_deadline: string;` on both interfaces (`types.ts:439`, `types.ts:503`) | exact — same shape (`string`, not optional, server always returns `""` when unset) |

## Pattern Assignments

### `tecponto_app/tecponto/frontend/api.py` (controller, request-response/CRUD)

**Analog:** `add_service_order_budget_line` (`api.py:1877-1960`) + role guard `_require_budget_edit_role` (`api.py:282-286`)

**Role gate pattern** — per D-02, gate must be Técnico-only, NOT the broader `BUDGET_ALLOWED_ROLES` used by `add_service_order_budget_line` (that set includes checkin/attendant roles too). Use the narrower `TECHNICIAN_COMMISSION_ROLES = {"System Manager", "Tecponto Tecnico"}` (`api.py:115`) as the model for a new, purpose-specific guard, following the exact shape of `_require_budget_edit_role`:
```python
def _require_budget_edit_role() -> None:
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(BUDGET_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem permissão para compor orçamento na OS."), frappe.PermissionError)
```
New guard should intersect against `{"System Manager", "Tecponto Tecnico"}` (mirroring `TECHNICIAN_COMMISSION_ROLES` at `api.py:115`) and throw a message like `"Somente o técnico responsável pode definir o prazo estimado."`.

**Core write pattern** (mirror `add_service_order_budget_line`, `api.py:1913-1960`):
```python
doc = frappe.get_doc("Service Order", (name or "").strip())
doc.check_permission("write")
...
doc.save(ignore_permissions=True)
return get_service_order_detail(doc.name)
```
Follow this exactly: load doc, `check_permission("write")`, mutate the one field, `doc.save(ignore_permissions=True)` (this triggers the `validate` hook chain including `policies.py`'s validators), return `get_service_order_detail(doc.name)` (`api.py:1453`) so the frontend gets a consistent refreshed detail payload — same shape `TechnicalBudgetEditor`'s own save calls already expect.

**Validation pattern for the write** — reuse `frappe.throw(_(...), frappe.ValidationError)` idiom used throughout this file, e.g.:
```python
if qty <= 0:
	frappe.throw(_("Quantidade precisa ser maior que zero."), frappe.ValidationError)
```
Apply analogous input validation to the incoming date string (e.g. reject if not parseable via `getdate`), and enforce D-02's stage restriction (`doc.workflow_state == "Diagnosticado — aguardando orçamento"`) with the same `frappe.throw` pattern — do not silently no-op on wrong stage.

**Precedent to explicitly NOT copy:** the check-in code that clears the field —
```python
# Prazo pertence ao diagnóstico/orçamento, não à Entrada.
order.estimated_deadline = None
```
(`api.py:2254-2255`) — stays untouched; it establishes *why* the new endpoint exists (nothing sets this field yet outside check-in's clear-to-None) and confirms no other write path needs adjustment.

---

### `tecponto_app/tecponto/service_order/policies.py` (model/validation, event-driven)

**Analog:** `_validate_delivery_dates_are_immutable` itself (`policies.py:135-146`), the exact function to extend per D-04:
```python
def _validate_delivery_dates_are_immutable(doc) -> None:
	"""Prevent a later edit from extending a warranty already delivered."""
	if doc.is_new():
		return

	previous = doc.get_doc_before_save()
	if not previous or previous.get("workflow_state") != "Entregue":
		return

	for fieldname, label in (("pickup_date", "data de entrega"), ("warranty_expiry", "validade da garantia")):
		if str(previous.get(fieldname) or "") != str(doc.get(fieldname) or ""):
			frappe.throw(f"A {label} de uma OS entregue e imutavel.")
```
**Extension:** add `("estimated_deadline", "prazo estimado")` as a third tuple entry in the `for fieldname, label in (...)` loop — zero new logic, just widen the existing tuple. This function is already called from both `_validate_warranty` branches (`policies.py:94` and `policies.py:123`), so no new call site is needed.

**Caller context** (do not modify, just confirms wiring):
```python
if not doc.get("is_warranty"):
	_validate_delivery_dates_are_immutable(doc)
	return
...
doc.warranty_expiry = warranty_expiry
_validate_delivery_dates_are_immutable(doc)
```

---

### `tecponto_app/tecponto/frontend/test_frontend_api.py` (test, request-response/integration)

**Analog:** `run_warranty_delivery_checks` itself (`test_frontend_api.py:2528-2711`) — extend, do not duplicate (D-01).

**Fixture/helper reuse pattern:**
```python
original_name = _create_action_request_service_order(attendant)
original = frappe.get_doc("Service Order", original_name)
...
_deliver_warranty_test_order(original)
original.db_set(
	{"workflow_state": "Entregue", "pickup_date": original.pickup_date, "warranty_expiry": original.warranty_expiry},
	update_modified=False,
)
```
`_deliver_warranty_test_order` (`test_frontend_api.py:2714-2725`) is the shared delivery helper — reuse it verbatim, do not write a new delivery path.

**Assertion idiom to copy** for the day-91/day-89 boundary check:
```python
if str(original.pickup_date) != nowdate() or str(original.warranty_expiry) != expected_original_expiry:
	raise AssertionError("Garantia normal não foi calculada a partir da data de entrega configurada.")
```
and the blocked-claim try/except idiom already used later in the same function for the expired-warranty case:
```python
expired_warranty_blocked = False
try:
	create_service_order_checkin({...})
except frappe.ValidationError:
	expired_warranty_blocked = True
if not expired_warranty_blocked:
	raise AssertionError("Motor aceitou retrabalho com garantia expirada.")
```
Add the new day-91 (`warranty_expiry - 1 day`, blocked) and day-89 (`warranty_expiry` or one day before, succeeds) assertions using this exact `try/except frappe.ValidationError` + `raise AssertionError(...)` shape, inserted into the existing function body (near the existing expired-warranty block around line 2661-2678), and extend the returned `dict` (`test_frontend_api.py:2695-2706`) with new boundary-result keys — do not add a `return` before the function's existing `finally` cleanup block (`test_frontend_api.py:2707-2711`), which resets `default_warranty_days`, deletes the temp catalog service, and restores `frappe.session.user`.

---

### `frontend/src/App.tsx` — deadline input in `TechnicalBudgetEditor` (component, request-response)

**Analog:** `TechnicalBudgetEditor` itself (`App.tsx:4122-4165`), specifically the customer-part inline input+button pattern (`App.tsx:4160`):
```tsx
{kind === "part" ? <div className="mt-2 flex gap-2">
  <input className="tp-input" onChange={(event) => setCustomerPartDescription(event.target.value)} placeholder="Ou descreva uma peça fornecida pelo cliente" value={customerPartDescription} />
  <Button disabled={busy || !customerPartDescription.trim()} onClick={async () => {
    setBusy(true);
    try {
      setBudget(await serviceOrders.addTechnicalBudgetLine(serviceOrder, { type: "part", description: customerPartDescription, qty: 1, selling_price: 0, source: "Cliente" }));
      setCustomerPartDescription("");
    } catch (caught) { onToast(caught instanceof Error ? caught.message : "Não foi possível adicionar a peça do cliente.", "error"); }
    finally { setBusy(false); }
  }}>Adicionar do cliente</Button>
</div> : null}
```
Copy this exact `useState` + `.tp-input` + `Button` (no `variant` prop → `secondary`, per UI-SPEC) + `try/catch/finally` shape for the new "Salvar prazo" control. Toast error fallback per UI-SPEC copywriting contract: `"Não foi possível salvar o prazo."`.

**Load/suggestion-fetch pattern** — mirror the existing `load` callback + `useEffect`:
```tsx
const load = useCallback(async () => {
	try { setBudget(await serviceOrders.technicalBudget(serviceOrder)); }
	catch (caught) { onToast(caught instanceof Error ? caught.message : "Não foi possível carregar o orçamento.", "error"); }
}, [onToast, serviceOrder]);

useEffect(() => { void load(); }, [load]);
```
Use this same `useCallback` + `useEffect` shape to fetch the `calculate_suggested_delivery` pre-fill suggestion on mount, with a `disabled={busy}` loading state as already established throughout this component (e.g. `Button disabled={busy || ...}`).

---

### `frontend/src/App.tsx` — `ServiceOrderPersistentOverview` display row (component, request-response display)

**Analog:** the existing "Prazo atual" row in the same `dl` (`App.tsx:4468`):
```tsx
{open ? <><DetailLine label="Prioridade" value={detail.priority ?? "Normal"} /><DetailLine label="Defeito relatado" value={detail.reported_defect ?? "Não informado"} /><DetailLine label="Prazo atual" value={detail.approval_deadline ? formatDate(detail.approval_deadline) : "Não definido"} /><DetailLine label="Atualizada" value={formatDate(detail.modified)} /></> : null}
```
Add a new `<DetailLine label="Prazo estimado" value={detail.estimated_deadline ? formatDate(detail.estimated_deadline) : "Não definido"} />` as a sibling inside the same `open ? <>...</> : null` block, per UI-SPEC surface 3 and D-06. **Note:** per D-06/UI-SPEC, use the shared `parseServerDate`-backed `formatDate` helper already used here (not a new formatter) — same call shape as the neighboring `Prazo atual`/`Atualizada` rows.

`DetailLine` itself (`App.tsx:7092-7096`, reuse verbatim, no changes needed):
```tsx
function DetailLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-tec-muted">{label}</dt>
      <dd className="max-w-[68%] text-right font-semibold text-tec-subtle">{value}</dd>
```

---

### `frontend/src/ServiceOrderKanban.tsx` — `KanbanCard` display row (component, request-response display)

**Analog:** existing `CardLine` rows (`ServiceOrderKanban.tsx:544-549`):
```tsx
<div className="mt-3 space-y-2 text-xs text-tec-muted">
  <CardLine icon={<Wrench size={14} />} text={item.reported_defect ?? "Defeito não informado"} />
  <CardLine icon={<UserRound size={14} />} text={`Técnico: ${item.technician ?? "Sem técnico"}`} />
  <CardLine icon={<UserRound size={14} />} text={`Recebido por: ${item.attendant ?? "Não informado"}`} />
  <CardLine icon={<Clock3 size={14} />} text={formatDate(item.modified)} />
</div>
```
Add a 5th sibling: `<CardLine icon={<Clock3 size={14} />} text={item.estimated_deadline ? \`Prazo estimado: ${formatDate(item.estimated_deadline)}\` : "Prazo estimado: Não definido"} />` (icon stays `text-tec-muted`, not orange, per UI-SPEC color contract; reuse `Clock3` icon already imported for the `modified` row, or reuse whichever neutral icon reads best — UI-SPEC doesn't mandate a specific icon, only that it must NOT be orange).

`CardLine` helper itself (`ServiceOrderKanban.tsx:568-574`, reuse verbatim — has built-in `truncate`):
```tsx
function CardLine({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <p className="flex min-w-0 items-center gap-2">
      <span className="shrink-0 text-tec-muted">{icon}</span>
      <span className="truncate">{text}</span>
    </p>
```

**Naming collision guard (critical):** `item.stage_clock?.estimated_deadline` already exists (`ServiceOrderKanban.tsx:521,562`, `types.ts:426`) and is an unrelated per-stage SLA value — the new row MUST read the new top-level `item.estimated_deadline`, not `item.stage_clock.estimated_deadline`.

---

### `frontend/src/api/serviceOrders.ts` (service, request-response)

**Analog:** `addTechnicalBudgetLine` and neighboring methods (`serviceOrders.ts:44-64`):
```ts
technicalBudget(name: string) {
	return rpc<TechnicalBudgetResponse>(`${TECHNICAL_BUDGET_API}.get_budget`, { query: { name } });
},
...
addTechnicalBudgetLine(name: string, payload: Record<string, unknown>) {
	return rpc<TechnicalBudgetResponse>(`${TECHNICAL_BUDGET_API}.add_line`, { body: { name, payload } });
},
```
New method belongs in the same `serviceOrders` object (`serviceOrders.ts:40`), pointed at the new `api.py` endpoint via the existing `API` constant (`serviceOrders.ts:27`, `const API = "tecponto_app.tecponto.frontend.api";`) — NOT `TECHNICAL_BUDGET_API`, since the new endpoint lives in `api.py` per CONTEXT.md, not the separate `technical_budget` module:
```ts
setEstimatedDeadline(name: string, estimatedDeadline: string) {
	return rpc<ServiceOrderDetailResponse>(`${API}.set_service_order_estimated_deadline`, { body: { name, estimated_deadline: estimatedDeadline } });
},
```
Also add a method for fetching the suggestion, following the same `rpc<T>(..., { query: {...} })` pattern as `technicalBudget`/`searchTechnicalBudgetServices` (GET-shaped, no body) if the suggestion needs its own endpoint rather than being embedded in `get_service_order_detail`.

Import list convention (`serviceOrders.ts:1-25`) — add any new response type name to the existing `import type { ... } from "./types"` block, matching the existing alphabetized-ish grouping style already in place (no strict alpha order enforced, just append near related names like `ServiceOrderDetailResponse`).

---

### `frontend/src/api/types.ts` (type/model contract)

**Analog:** `approval_deadline: string;` on both `ServiceOrderSummary` (`types.ts:439`) and `ServiceOrderDetailResponse` (`types.ts:503`).

Add `estimated_deadline: string;` as a new **top-level** field (not inside `stage_clock`) on both interfaces, directly beside `approval_deadline` for readability:
```ts
export interface ServiceOrderSummary {
  ...
  approval_status: string | null;
  approval_deadline: string;
  estimated_deadline: string;   // NEW — top-level OS deadline, distinct from stage_clock.estimated_deadline
  pickup_date: string | null;
  modified: string;
  ...
}
```
**Do not** touch the existing `stage_clock?: { ...; estimated_deadline: string; ... }` block (`types.ts:422-431`) — that is the unrelated per-stage SLA clock value flagged by the UI-SPEC naming-collision warning.

---

## Shared Patterns

### Whitelisted-endpoint role gate + doc save
**Source:** `api.py:282-286` (`_require_budget_edit_role`) and `api.py:1913-1960` (`add_service_order_budget_line` body)
**Apply to:** the new `api.py` endpoint. Pattern: `_require_<specific>_role()` → `frappe.get_doc(...)` → `check_permission("write")` → mutate → `doc.save(ignore_permissions=True)` → return `get_service_order_detail(doc.name)`.

### Backend serializer functions to extend
**Source:** `_serialize_service_order` (`api.py:4100-4124`, builds `ServiceOrderSummary` payload) and `get_service_order_detail` (`api.py:1453` onward, builds `ServiceOrderDetailResponse` payload, `approval_deadline` shown at `api.py:1488`)
**Apply to:** both must gain a `"estimated_deadline": str(item.get("estimated_deadline") or ""),` / `str(doc.get("estimated_deadline") or ""),` line, mirroring the exact `approval_deadline` serialization idiom already present in each. Also add `"estimated_deadline"` to `SAFE_SERVICE_ORDER_FIELDS` (`api.py:143-163`) — the DB fetch field allowlist that both serializers draw from — right after `"approval_deadline"` (`api.py:159`).

### Delivery-immutability lock (backend)
**Source:** `_validate_delivery_dates_are_immutable` (`policies.py:135-146`)
**Apply to:** the `estimated_deadline` field, per D-04 — widen the existing field/label tuple, no new function.

### Date display / formatting (frontend)
**Source:** `frontend/src/utils/date.ts` (`parseServerDate`), consumed via `formatDate` used throughout `App.tsx`/`ServiceOrderKanban.tsx` (e.g. `App.tsx:4468`, `ServiceOrderKanban.tsx:548`)
**Apply to:** every display surface (Kanban row, `DetailLine` row) — never write a new date formatter, per D-06 / UI-SPEC.

### Error-toast convention (frontend)
**Source:** repeated `catch (caught) { onToast(caught instanceof Error ? caught.message : "<fallback>", "error"); }` idiom, e.g. `App.tsx:4152`, `App.tsx:4170`
**Apply to:** the new deadline-save action's catch block, with fallback `"Não foi possível salvar o prazo."` per UI-SPEC copywriting contract.

### "Não definido" fallback copy (frontend)
**Source:** `App.tsx:4468` (`detail.approval_deadline ? formatDate(...) : "Não definido"`)
**Apply to:** both new read-only display rows (Kanban `CardLine`, OS-detail `DetailLine`) per UI-SPEC copywriting contract — reuse verbatim, do not invent new fallback copy.

## No Analog Found

None — all 8 files/surfaces have a strong, same-file or same-pattern analog in the existing codebase.

## Metadata

**Analog search scope:** `tecponto_app/tecponto/frontend/api.py`, `tecponto_app/tecponto/service_order/policies.py`, `tecponto_app/tecponto/service_order/stage_sla.py`, `tecponto_app/tecponto/frontend/test_frontend_api.py`, `tecponto_app/tecponto/service_order/kanban.py`, `frontend/src/App.tsx`, `frontend/src/ServiceOrderKanban.tsx`, `frontend/src/api/serviceOrders.ts`, `frontend/src/api/types.ts`
**Files scanned:** 9
**Pattern extraction date:** 2026-09-03
