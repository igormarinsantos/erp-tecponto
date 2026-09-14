# Phase 3: Systematic Audit — PDV → Trade-in → Warranty (Aparelho Usado) → Caixa - Pattern Map

**Mapped:** 2026-09-14
**Files analyzed:** 6 (all modifications to existing files — no net-new files except possibly a new test function for AUDIT-05)
**Analogs found:** 6 / 6 (all patterns found in-repo; no RESEARCH.md needed since CONTEXT.md already carries direct line-level grounding)

## File Classification

| File to Modify | Role | Data Flow | Closest Analog (same file, neighboring pattern) | Match Quality |
|---|---|---|---|---|
| `tecponto_app/tecponto/frontend/test_frontend_api.py` — wire 4 orphaned tests into `run_foundation_checks` | test | batch/request-response | neighboring `run_*_checks()` wiring lines 316-387 (same file) | exact |
| `tecponto_app/tecponto/frontend/test_frontend_api.py` — extend `run_cash_session_checks` | test | CRUD assertion | existing `technician_blocked` role-gate block inside same function (lines 7493-7500) | exact |
| `tecponto_app/tecponto/frontend/test_frontend_api.py` — extend `run_tradein_frontend_checks` (checklist completeness) | test | CRUD assertion | existing `below_floor_blocked` validation-error assertion pattern (lines 6866-6874) in same function | exact |
| `device_trade_evaluation_checklist` completeness gate | model/validate-hook | event-driven (doctype validate) | `tecponto_app/tecponto/service_order/policies.py::validate_repare_rules` (dispatcher) + `tecponto_app/tecponto/tradein/evaluation.py::validar_avaliacao` (dispatcher already exists on this exact doctype) | exact — gate should be added as one more private function called from `validar_avaliacao`, not a new hook |
| `tecponto_app/tecponto/used_device_warranty.py` reuse (`consultar_garantia_usado`) | service/utility | request-response (lookup, read-only) | itself — reused as-is, no new analog needed | exact |
| `tecponto_app/tecponto/frontend/api.py::create_service_order_checkin` — new Used-Device-Warranty free-repair-OS branch | controller/endpoint | request-response | its own existing `is_warranty`/`original_service_order` branch (lines 2296-2306), which itself mirrors `is_same_warranty_defect` from `policies.py` | exact — same file, same function, adjacent branch to extend |
| new used-device-warranty claim-enforcement test | test | request-response assertion | `run_used_device_warranty_lookup_checks` (lines 8523-8570) for the fixture-creation shape; `run_tradein_frontend_checks`'s `frappe.ValidationError` try/except assertion shape for the enforcement check itself | strong |

## Pattern Assignments

### D-01: Wire 4 orphaned test functions into `run_foundation_checks`

**Analog:** the existing wiring block, `tecponto_app/tecponto/frontend/test_frontend_api.py:316-387` inside `run_foundation_checks`.

**Core pattern** (lines 343-354, showing the exact style to copy — one local variable assignment per check, no arguments needed for parameterless checks):
```python
tradein_frontend_check = run_tradein_frontend_checks()
post_sale_checks = run_post_sale_checks()
used_device_warranty_lookup = run_used_device_warranty_lookup_checks()
warranty_delivery_check = run_warranty_delivery_checks()
service_order_deadline_checks = run_service_order_deadline_checks()
budget_presentation_check = run_budget_presentation_checks()
print_document_checks = run_print_document_checks()
device_credential_guard = run_device_credential_non_leak_checks()
```
Add, following this exact shape (each is parameterless per CONTEXT.md's confirmation):
```python
pos_sale_check = run_pos_sale_checks()
warranty_mode_check = run_warranty_mode_checks()
pos_barcode_label_check = run_pos_barcode_label_checks()
pos_retail_barcode_catalog_check = run_pos_retail_barcode_catalog_checks()
```
Then add each new local variable's key to the `return {...}` dict at the bottom of `run_foundation_checks` (starting line 388 `return {"status": "ok",`) — every existing check variable above appears as a dict entry there; follow the same key-naming convention (snake_case matching the variable name).

**Placement note:** Insert near thematically related neighbors — `pos_sale_check`/`pos_barcode_label_check`/`pos_retail_barcode_catalog_check` fit naturally near line 356 (`pos_cost_guard = _check_pos_item_cost_guard(...)`) and `warranty_mode_check` fits naturally near line 345 (`used_device_warranty_lookup`) or near line 331-333 (cash/warranty cluster) — either placement is safe since these are independent local assignments with no ordering dependency, but keep thematically adjacent for readability.

---

### D-02 (AUDIT-02): Extend `run_cash_session_checks` with concurrent-session assertion

**Analog:** the function's own existing role-gate assertion pattern, `tecponto_app/tecponto/frontend/test_frontend_api.py:7493-7500`:
```python
frappe.set_user(technician)
technician_blocked = False
try:
    open_store_cash_session(50, f"tp-cash-tech-{frappe.generate_hash(length=20)}")
except frappe.PermissionError:
    technician_blocked = True
if not technician_blocked:
    raise AssertionError("Técnico conseguiu abrir o caixa da loja.")
```

**Production code being asserted against** — `tecponto_app/tecponto/cash.py:56-64` (`open_cash_session`), the existing hard block:
```python
existing_session = frappe.db.get_value(
    CASH_SESSION_DOCTYPE,
    {"session_key": session_key},
    ["name", "status"],
    as_dict=True,
)
if existing_session:
    message = _("Já existe um caixa aberto no ponto {0}.").format(point) if existing_session.status == SESSION_OPEN else _("O caixa deste ponto já foi fechado hoje.").format(point)
    frappe.throw(message, frappe.ValidationError)
```

**New assertion to add** (same shape as the technician-blocked check above, but asserting `frappe.ValidationError` instead of `PermissionError`, using the same `cash_point` already opened earlier in the function at line 7423/7427-7432):
```python
second_open_blocked = False
try:
    open_cash_session(
        opening_amount=50,
        idempotency_key=f"tp-cash-concurrent-{frappe.generate_hash(length=20)}",
        opened_by=attendant,
        cash_point=cash_point,  # same cash_point/business_date already opened above
    )
except frappe.ValidationError:
    second_open_blocked = True
if not second_open_blocked:
    raise AssertionError("Segunda abertura de caixa no mesmo ponto não foi bloqueada.")
```
Add `second_open_blocked` (or equivalent name) to this function's own `return {...}` dict.

---

### AUDIT-03: Device Trade Evaluation checklist-completeness gate

**Ground truth investigated (this was explicitly unresolved in CONTEXT.md):**

1. **The checklist child table IS populated today**, but only with expected *item names + expected values* — never with results. The population happens automatically inside the existing `validate` hook, not by any UI action:
   - `tecponto_app/tecponto/tradein/evaluation.py:39-66` — `validar_avaliacao` (the doctype's registered `validate` hook, wired in `hooks.py:320-321`) calls `_sync_checklist(doc)` on every save, which auto-appends any missing expected rows (from `IPHONE_CHECKLIST`/`ANDROID_CHECKLIST` constants, lines 18-33) with `check_item` + `expected_value` set, but **`result` and `notes` are left blank** — those are the only fields a human/UI can subsequently fill in via the child grid.
   - Confirmed no other code path writes to `checklist` — `grep -rn "checklist" tecponto_app/tecponto --include=*.py` returns only `tradein/evaluation.py` hits (definitions + this sync logic). No frontend JS or `frontend/api.py` endpoint touches the `checklist` field at all today — it is edited directly through the standard Frappe desk child-table grid on the `Device Trade Evaluation` form (there is no dedicated React/API path).

2. **"Complete" has no existing formal definition** — but the closest existing precedent for "is this row problematic" is `_has_blocking_checklist_result` (lines 85-92), which only checks for `icloud`/`conta google` markers with `result` in `{"atencao", "reprovado"}`, and is only invoked at approval time via `_is_approval_attempt(doc)` (lines 77-82, 117-118: `doc.get("workflow_state") in APPROVED_STATES or bool(doc.get("approved_value"))`). This function scans **all** rows regardless of item, so it is the concrete template to generalize: **"complete" = every row in `doc.get("checklist")` has a non-empty `result`** (i.e. no row where `result` is falsy), checked only at approval-attempt time (same `_is_approval_attempt` gate), mirroring how the icloud block is scoped only to approval, not to every save. This avoids blocking early free-form drafts, consistent with `_sync_checklist` auto-populating rows before any human has had a chance to fill them in.

**Analog for the new validation function's registration/dispatch style** — `tecponto_app/tecponto/tradein/evaluation.py:39-42` (`validar_avaliacao`, the existing dispatcher already wired as this doctype's `validate` hook — no new hook registration needed, add the new function as one more call inside this dispatcher):
```python
def validar_avaliacao(doc, method=None) -> None:
    _sync_checklist(doc)
    _validate_blocked_device(doc)
    _validate_approved_value_range(doc)
```
Add a fourth call, e.g. `_validate_checklist_complete(doc)`, following this exact pattern — a private function using the same `_is_approval_attempt(doc)` gate as `_validate_blocked_device`:
```python
def _validate_blocked_device(doc) -> None:
    if not _is_approval_attempt(doc):
        return
    if doc.get("icloud_google_lock") or _has_blocking_checklist_result(doc):
        frappe.throw("Aparelho com bloqueio iCloud/Google nao pode ser aprovado para troca.")
```

**Analog for the test extension** — `tecponto_app/tecponto/frontend/test_frontend_api.py:6866-6874` inside `run_tradein_frontend_checks`, the existing below-floor-value `frappe.ValidationError` assertion shape:
```python
below_floor = create_evaluation(suffix="PISO", value=100)
below_floor = set_tradein_approved_value(below_floor["name"], 100)["item"]
below_floor_blocked = False
try:
    confirm_tradein_operation({"evaluation": below_floor["name"], "device_out": output["name"], "difference": 0})
except frappe.ValidationError:
    below_floor_blocked = True
if not below_floor_blocked:
    raise AssertionError("Atendente confirmou troca abaixo do custo após a elevação do hook.")
```
New checklist-incomplete test should follow the same shape: create an evaluation, set `approved_value` (triggers `_is_approval_attempt`), leave checklist `result` fields blank, assert `frappe.ValidationError` is raised on save/approval.

**Note on doctype JSON files:** No JSON schema change is required — `Device Trade Evaluation Checklist` already has the `result` (Select: `\nOK\nAtenção\nReprovado\nN/A`) and `check_item` fields needed; the gate is pure Python logic in `tradein/evaluation.py`, not a doctype-definition change.

---

### AUDIT-05: Used Device Warranty → free-repair-OS check-in gate

**Analog for the conceptual "expired → normal charged OS" pattern (read for concept only, per CONTEXT.md D-04 — do NOT reuse code directly, different relationship model):** `tecponto_app/tecponto/service_order/policies.py:157-160`:
```python
def is_same_warranty_defect(original_service_order: str, reported_defect: str | None) -> bool:
    """Classify only the defect; identity/coverage remain enforced by the warranty policy."""
    original_defect = frappe.db.get_value("Service Order", original_service_order, "reported_defect")
    return bool(original_defect and _normalize_defect(original_defect) == _normalize_defect(reported_defect))
```

**Reuse directly (source of truth for expiration):** `tecponto_app/tecponto/used_device_warranty.py:54-89` (`consultar_garantia_usado`) — already computes `under_warranty` (line 88: `expiry >= reference`) and enforces the read-permission role gate (`_require_warranty_lookup_role`, lines 92-98). Call this function directly from the checkin path rather than re-querying `Used Device Warranty` / recomputing expiry.

**Attachment point — `tecponto_app/tecponto/frontend/api.py:2296-2306`, the existing `is_warranty`/`original_service_order` branch in `create_service_order_checkin`** (this is the exact adjacent code to extend, not just a nearby example):
```python
order.is_warranty = cint(data["service_order"].get("is_warranty"))
order.original_service_order = (data["service_order"].get("original_service_order") or "").strip() or None
if order.is_warranty and order.original_service_order:
    original = frappe.db.get_value("Service Order", order.original_service_order, ["customer", "customer_device", "workflow_state"], as_dict=True)
    if not original or original.customer != customer_name or original.customer_device != device_name or original.workflow_state != STATE_ENTREGUE:
        frappe.throw(_("A garantia precisa apontar para uma OS entregue do mesmo cliente e aparelho."), frappe.ValidationError)
    from tecponto_app.tecponto.service_order.policies import is_same_warranty_defect
    if not is_same_warranty_defect(order.original_service_order, order.reported_defect):
        order.is_warranty = 0
        marker = _("Defeito diferente da OS original {0}: atendimento convertido em OS normal, com valor definido no orçamento.").format(order.original_service_order)
        order.attendance_notes = "\n".join(filter(None, [order.attendance_notes, marker]))
```
New logic should sit as a parallel/adjacent `elif` or additional branch: given a serial/IMEI on `data["device"]` (device already resolved via `_get_or_create_checkin_device` at line 2264, before this block), call `consultar_garantia_usado(serial_no)`; if `exists` and `under_warranty`, mark the new OS with whatever field(s) the planner designs for "free/no-charge repair under used-device warranty" (D-03 confirms this is currently a **manual** no-charge marking — investigate existing `Service Order` fields for a no-charge/courtesy flag, e.g. `courtesy_warranty` used in `policies.py:85-91`, as a strong candidate to reuse conceptually, since it already requires a reason and is gated to managers — planner must decide whether the new automatic gate sets this field or a new dedicated one). If `under_warranty` is `False` (expired), per D-04 the OS proceeds as a normal charged OS — no special handling needed, just do not set the free/courtesy marker (mirrors `is_same_warranty_defect` returning `False` → `order.is_warranty = 0` falling through to normal OS creation).

**Analog for the new claim-enforcement test's fixture-creation shape** — `tecponto_app/tecponto/frontend/test_frontend_api.py:8523-8546` (`run_used_device_warranty_lookup_checks`), the exact `Used Device Warranty` doc-creation fixture to reuse:
```python
serial_no = f"TP-UDW-GUARD-{frappe.generate_hash(length=12)}"
warranty = frappe.get_doc(
    {
        "doctype": "Used Device Warranty",
        "serial_no": serial_no,
        "customer": customer,
        "item_code": _get_demo_item(is_stock_item=1),
        "sales_invoice": "TEST-USED-WARRANTY",
        "sale_date": nowdate(),
        "warranty_days": 90,
        "warranty_expiry": add_days(nowdate(), 90),
        "coverage": "Defeito de fábrica",
    }
)
warranty.insert(ignore_permissions=True, ignore_links=True)
frappe.db.commit()
```
Per CONTEXT.md, this should be a **new function** (`run_used_device_warranty_claim_checks` or similar), not an extension of the lookup-checks function, since the trigger point differs (checkin-time claim vs. read-only lookup). Add its call to `run_foundation_checks` following the D-01 wiring pattern above, and add its return value to the dict.

---

## Shared Patterns

### `run_*_checks()` function shape (applies to all new/extended test functions)
**Source:** every function in `test_frontend_api.py` (e.g. `run_tradein_frontend_checks`, `run_cash_session_checks`, `run_used_device_warranty_lookup_checks`)
**Apply to:** any new test function or extension in this phase
```python
def run_x_checks() -> dict:
    """One-line docstring stating the security/business invariant being proven."""
    previous_user = frappe.session.user
    try:
        frappe.set_user("Administrator")  # or omit if not needed
        ensure_frontend_foundation()
        attendant = _find_or_create_user("Tecponto Atendente")
        # ... fixtures, role switches via frappe.set_user(...) ...
        # ... assertions via `raise AssertionError(...)` on failure ...
        leaks = contains_sensitive_field({...})
        if leaks:
            raise AssertionError(f"... vazou campos sensíveis: {', '.join(leaks)}")
        return {...}  # dict of observable results
    finally:
        frappe.set_user(previous_user)
```

### Doctype validate-hook dispatcher pattern
**Source:** `tecponto_app/tecponto/service_order/policies.py:14-21` (`validate_repare_rules`) and `tecponto_app/tecponto/tradein/evaluation.py:39-42` (`validar_avaliacao`)
**Apply to:** the new checklist-completeness gate (AUDIT-03) — add as one more private `_validate_*` function called from the existing dispatcher already wired in `hooks.py`; never register a second `validate` hook for the same doctype.

### Role-gated `frappe.throw` with typed exception
**Source:** used consistently across `cash.py`, `used_device_warranty.py`, `tradein/evaluation.py`, `service_order/policies.py`
```python
frappe.throw(_("Mensagem em português para o usuário."), frappe.ValidationError)
```
or `frappe.PermissionError` for role/authorization failures. **Apply to:** any new production-code gate in this phase (checklist completeness, used-device-warranty claim enforcement).

## No Analog Found

None — every file/change in this phase's scope has a direct, concrete in-repo analog (often the very same function being extended). No RESEARCH.md fallback patterns were needed.

## Metadata

**Analog search scope:** `tecponto_app/tecponto/frontend/test_frontend_api.py`, `tecponto_app/tecponto/frontend/api.py`, `tecponto_app/tecponto/cash.py`, `tecponto_app/tecponto/tradein/evaluation.py`, `tecponto_app/tecponto/service_order/policies.py`, `tecponto_app/tecponto/used_device_warranty.py`, `tecponto_app/hooks.py`, `tecponto_app/tecponto/doctype/device_trade_evaluation/*`, `tecponto_app/tecponto/doctype/device_trade_evaluation_checklist/*`
**Files scanned:** 9 (all read directly, all git-tracked source under the WSL repo root — no `.gsd`/plugin-mirror paths involved in this phase)
**Pattern extraction date:** 2026-09-14
