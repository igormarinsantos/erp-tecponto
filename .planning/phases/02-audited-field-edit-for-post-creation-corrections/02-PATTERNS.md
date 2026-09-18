# Phase 2: Audited Field-Edit for Post-Creation Corrections - Pattern Map

**Mapped:** 2026-09-18
**Files analyzed:** 7 (new/modified)
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tecponto_app/tecponto/doctype/tecponto_access_audit/tecponto_access_audit.json` | model (doctype schema) | CRUD | itself (current schema) | exact — migration, not replacement |
| `tecponto_app/tecponto/user_access.py` (`_write_audit`, `_access_snapshot`) | service (audit writer) | event-driven | itself (`_write_audit`, `audit_accumulated_role_action`) | exact — extend signature |
| `tecponto_app/tecponto/frontend/api.py` — `update_service_order_entry` (~2441) | controller (whitelisted RPC) | request-response / CRUD | itself, plus `_decide_service_order_budget`'s audit-adjacent flow | exact — add audit call |
| `tecponto_app/tecponto/frontend/api.py` — new `update_customer` | controller (whitelisted RPC) | request-response / CRUD | `create_customer` (3439) | exact — same doctype, sibling verb |
| `tecponto_app/tecponto/service_order/policies.py` — `_validate_delivery_dates_are_immutable` | middleware (doc validate hook) | event-driven | n/a (reference-only, not modified) | exact, read-only |
| `frontend/src/App.tsx` — `editEntry` handler + `ServiceOrderStageScreenContent` "entrada" render + `IdentityCard` | component | request-response | itself (existing `editEntry`/`IdentityCard`) | exact — extend, don't replace |
| `tecponto_app/tecponto/frontend/test_frontend_api.py` — new `run_edit_audit_checks()` | test | batch/end-to-end | `run_pos_tradein_cost_guard_checks` (9205) and sibling `run_*_checks` | exact — established convention |

## Pattern Assignments

### `tecponto_app/tecponto/doctype/tecponto_access_audit/tecponto_access_audit.json`

**Analog:** itself — current schema (full file, 21 lines), read via `Read`.

Current relevant fields:
```json
{"fieldname":"affected_user","fieldtype":"Link","label":"Usuário afetado","options":"User","reqd":1,"in_list_view":1,"read_only":1},
{"fieldname":"change_type","fieldtype":"Data","label":"Tipo de alteração","reqd":1,"in_list_view":1,"read_only":1},
```
`field_order` is `["actor", "affected_user", "change_type", "occurred_on", "before_state", "after_state"]`.

**Migration required (D-01):**
1. Change `affected_user`: remove `"reqd":1` (make optional). Keep `Link`/`User`/`in_list_view`/`read_only`.
2. Add two new fields after `affected_user` in both `fields` and `field_order`, following the project's Dynamic Link convention (see `Service Order`'s own `Comment`/other reference usages in `api.py`, e.g. `"reference_doctype": "Service Order", "reference_name": doc.name` used as plain dict keys in `audit_accumulated_role_action`'s `before` payload — that was a workaround for the *absence* of real fields; this migration finally gives them real columns):
   ```json
   {"fieldname":"reference_doctype","fieldtype":"Link","label":"Tipo de referência","options":"DocType","in_list_view":1,"read_only":1},
   {"fieldname":"reference_name","fieldtype":"Dynamic Link","label":"Referência","options":"reference_doctype","in_list_view":1,"read_only":1}
   ```
3. Do not touch `permissions` (`System Manager` only, `read/report/export/print`) — D-01 says no new permission surface needed.
4. Do not touch `doc_events` hook registration in `hooks.py:282-285` — it applies to the doctype by name regardless of new fields, no change needed there.
5. `track_changes` stays `0` (this doctype's own audit fields don't need meta-auditing).

No `frappe.db.exists` migration script is normally required for JSON-only doctype field additions in Frappe — a `bench migrate` picks up the JSON diff. Confirm this is this project's convention by checking for a `patches.txt` entry pattern elsewhere in the app before assuming no patch is needed.

---

### `tecponto_app/tecponto/user_access.py` — extend `_write_audit` / `_access_snapshot`

**Analog:** itself, lines 220-289 (already read in full).

**Current signature** (line ~264):
```python
def _write_audit(*, affected_user: str, change_type: str, before: dict, after: dict) -> None:
	if not frappe.db.exists("DocType", AUDIT_DOCTYPE):
		return
	frappe.get_doc(
		{
			"doctype": AUDIT_DOCTYPE,
			"actor": frappe.session.user,
			"affected_user": affected_user,
			"change_type": change_type,
			"before_state": json.dumps(before, ensure_ascii=True, sort_keys=True),
			"after_state": json.dumps(after, ensure_ascii=True, sort_keys=True),
			"occurred_on": now_datetime(),
		}
	).insert(ignore_permissions=True)
```

**Extension pattern (D-01/D-02):** widen the signature to accept optional `affected_user`, `reference_doctype`, `reference_name` — do NOT write a second function. Existing callers (`audit_user_creation`, `audit_password_change`, `audit_accumulated_role_action`, the enable/disable/roles-changed caller at the top of the file) keep passing only `affected_user` and are unaffected as long as the new params default to `None`/`""`.

```python
def _write_audit(
	*,
	affected_user: str | None = None,
	change_type: str,
	before: dict,
	after: dict,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
) -> None:
	if not frappe.db.exists("DocType", AUDIT_DOCTYPE):
		return
	doc_fields: dict[str, Any] = {
		"doctype": AUDIT_DOCTYPE,
		"actor": frappe.session.user,
		"change_type": change_type,
		"before_state": json.dumps(before, ensure_ascii=True, sort_keys=True),
		"after_state": json.dumps(after, ensure_ascii=True, sort_keys=True),
		"occurred_on": now_datetime(),
	}
	if affected_user:
		doc_fields["affected_user"] = affected_user
	if reference_doctype and reference_name:
		doc_fields["reference_doctype"] = reference_doctype
		doc_fields["reference_name"] = reference_name
	frappe.get_doc(doc_fields).insert(ignore_permissions=True)
```

Because `Tecponto Access Audit` currently requires `affected_user` (`reqd=1`), this extension is only safe **after** the JSON migration above relaxes that constraint — sequence the plan so the schema migration lands first (or in the same task) before this Python change is exercised.

**New public entrypoint to add (called from `api.py`'s edit endpoints), following the exact shape of `audit_accumulated_role_action` (lines ~279-296):**
```python
def audit_reference_field_edit(*, change_type: str, reference_doctype: str, reference_name: str, before: dict, after: dict) -> None:
	"""Record a post-creation field correction against a Service Order or Customer, not a User."""
	_write_audit(
		change_type=change_type,
		before=before,
		after=after,
		reference_doctype=reference_doctype,
		reference_name=reference_name,
	)
```
This mirrors `audit_accumulated_role_action`'s call shape (`_write_audit(affected_user=..., change_type=..., before={...}, after={...})`) but omits `affected_user` per D-01 ("new EDIT-01/02/03 rows... leave `affected_user` empty").

**Reading the latest audit row for the UI indicator (D-07)** — no existing "latest row" reader exists yet; add one alongside, following the `frappe.get_all` idiom used throughout `api.py` (e.g. `get_customer_device_history`'s `frappe.get_all("Service Order", filters=..., order_by="entry_date desc", limit_page_length=30)`):
```python
def get_latest_reference_audit(reference_doctype: str, reference_name: str) -> dict | None:
	rows = frappe.get_all(
		AUDIT_DOCTYPE,
		filters={"reference_doctype": reference_doctype, "reference_name": reference_name},
		fields=["actor", "change_type", "occurred_on"],
		order_by="occurred_on desc",
		limit_page_length=1,
	)
	return rows[0] if rows else None
```

---

### `tecponto_app/tecponto/frontend/api.py` — `update_service_order_entry` (line 2441)

**Analog:** itself (full function, lines 2441-2464, already read).

**Current shape:**
```python
@frappe.whitelist()
def update_service_order_entry(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Edit only check-in facts; workflow, gates and budget stay under their own motors."""
	_require_checkin_role()
	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("write")
	if doc.get("workflow_state") in {"Entregue", "Cancelado"}:
		frappe.throw(_("A entrada não pode ser editada após o encerramento da OS."), frappe.ValidationError)
	data = _parse_payload(payload)
	text_fields = {
		"reported_defect", "physical_state", "attendance_notes", "entry_operating_condition",
		"accessories_received", "os_contact_name", "os_contact_phone",
	}
	for fieldname in text_fields:
		if fieldname in data:
			doc.set(fieldname, (data.get(fieldname) or "").strip())
	if "device_access_type" in data or "device_access_credential" in data:
		_save_device_access_credential(doc.customer_device, data)
	if not (doc.reported_defect or "").strip() or not (doc.physical_state or "").strip():
		frappe.throw(_("Defeito relatado e estado físico são obrigatórios na Entrada."), frappe.ValidationError)
	if doc.entry_operating_condition not in ENTRY_OPERATING_CONDITIONS:
		frappe.throw(_("Condição de funcionamento inválida."), frappe.ValidationError)
	doc.save(ignore_permissions=True)
	return get_service_order_detail(doc.name)
```

**Wiring pattern (EDIT-01/EDIT-02 audit):** capture before-state for `os_contact_name`/`os_contact_phone` BEFORE mutating `doc`, and before/after device-credential metadata (never the raw value, per D-03) around the `_save_device_access_credential` call. Write the audit call(s) after `doc.save(...)` succeeds (mirrors `_write_audit` being called only on confirmed state changes elsewhere in `user_access.py`, e.g. the enable/disable audit at the top of the file which only fires `if before != after`).

```python
before_contact = {"os_contact_name": doc.os_contact_name, "os_contact_phone": doc.os_contact_phone}
...
if "device_access_type" in data or "device_access_credential" in data:
	before_credential_meta = {
		"device_access_type": doc.device_access_type,
		"had_credential": bool(frappe.db.get_value("Customer Device", doc.customer_device, "device_access_credential")),
	}
	_save_device_access_credential(doc.customer_device, data)
	after_credential_meta = {
		"device_access_type": data.get("device_access_type") or before_credential_meta["device_access_type"],
		"had_credential": True,
	}
...
doc.save(ignore_permissions=True)

after_contact = {"os_contact_name": doc.os_contact_name, "os_contact_phone": doc.os_contact_phone}
if before_contact != after_contact:
	audit_reference_field_edit(
		change_type="os_contact_edit",
		reference_doctype="Service Order",
		reference_name=doc.name,
		before=before_contact,
		after=after_contact,
	)
if credential_touched:
	audit_reference_field_edit(
		change_type="device_credential_edit",
		reference_doctype="Service Order",
		reference_name=doc.name,
		before=before_credential_meta,
		after=after_credential_meta,
	)
return get_service_order_detail(doc.name)
```

**Import needed at top of `api.py`** (mirrors existing `from tecponto_app.tecponto.customer import (...)` at line 16-19):
```python
from tecponto_app.tecponto.user_access import audit_reference_field_edit, get_latest_reference_audit
```

**Sentinel-test discipline (D-03):** `before_credential_meta`/`after_credential_meta` must contain only `device_access_type` and `had_credential` (boolean) — never `data.get("device_access_credential")`, never a length, never a masked fragment. This is the exact shape given in CONTEXT.md D-03.

**EDIT-04 regression test target:** `text_fields` set never includes `pickup_date`/`warranty_expiry`/`estimated_deadline` — a test should assert that passing those keys in `payload` has no effect (silently ignored, since they're not in `text_fields` and `_parse_payload` doesn't special-case them), proving the existing behavior rather than only trusting `_validate_delivery_dates_are_immutable` in `policies.py`.

---

### `tecponto_app/tecponto/frontend/api.py` — new `update_customer` endpoint

**Analog:** `create_customer`, lines 3439-3460 (already read in full).

```python
@frappe.whitelist()
def create_customer(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Create an individual customer from the counter without opening core Customer."""
	_require_checkin_role()
	data = _parse_payload(payload)
	validate_customer_contact_document(data)

	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": data["customer_name"].strip(),
			"customer_type": "Individual",
			"mobile_no": (data.get("mobile_no") or data.get("custom_whatsapp") or "").strip(),
			"custom_whatsapp": (data.get("custom_whatsapp") or data.get("mobile_no") or "").strip(),
			"custom_cpf": (data.get("custom_cpf") or "").strip(),
			"custom_rg": (data.get("custom_rg") or "").strip(),
			CUSTOMER_NO_CPF_FIELD: 1 if data.get(CUSTOMER_NO_CPF_FIELD) else 0,
			"email_id": (data.get("email_id") or "").strip(),
		}
	)
	customer.insert(ignore_permissions=True)
	item = frappe.db.get_value("Customer", customer.name, list(SAFE_CUSTOMER_FIELDS), as_dict=True)
	return {"item": _serialize_customer(item)}
```

**New `update_customer` — same validation call, `frappe.get_doc("Customer", name)` + `.save()` instead of insert, with before/after snapshot restricted to name/CPF per D-04 (EDIT-03 scope is customer name/CPF specifically, not full contact re-creation — RG/phone/email changes are Claude's discretion whether to fold in, but the audited fields per requirement are name + CPF):**

```python
@frappe.whitelist()
def update_customer(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Correct an existing individual customer's identity fields (name/CPF), audited."""
	_require_checkin_role()
	customer = frappe.get_doc("Customer", (name or "").strip())
	customer.check_permission("write")
	data = _parse_payload(payload)
	validate_customer_contact_document({**customer.as_dict(), **data})

	before = {"customer_name": customer.customer_name, "custom_cpf": customer.custom_cpf}
	if "customer_name" in data:
		customer.customer_name = data["customer_name"].strip()
	if "custom_cpf" in data:
		customer.custom_cpf = (data.get("custom_cpf") or "").strip()
	customer.save(ignore_permissions=True)
	after = {"customer_name": customer.customer_name, "custom_cpf": customer.custom_cpf}

	if before != after:
		audit_reference_field_edit(
			change_type="customer_identity_edit",
			reference_doctype="Customer",
			reference_name=customer.name,
			before=before,
			after=after,
		)
	item = frappe.db.get_value("Customer", customer.name, list(SAFE_CUSTOMER_FIELDS), as_dict=True)
	return {"item": _serialize_customer(item)}
```

**Note:** `validate_customer_contact_document` (in `tecponto_app/tecponto/customer.py:21-40`, already read in full) requires `customer_name`, `phone`, and CPF/RG rules on the FULL data dict — merging `customer.as_dict()` with the partial `data` payload is necessary so the existing phone/RG values (not being edited) don't fail the "obrigatório" checks. This is the "wraps it" option flagged as Claude's discretion in CONTEXT.md; wrapping (merge before validate) is the safer choice for a partial-update endpoint since `create_customer` only ever validates a full payload.

---

### `tecponto_app/tecponto/service_order/policies.py` — `_validate_delivery_dates_are_immutable` (reference only, NOT modified)

**Location:** lines 152-167, already read in full.
```python
def _validate_delivery_dates_are_immutable(doc) -> None:
	"""Prevent a later edit from extending a warranty already delivered."""
	if doc.is_new():
		return
	previous = doc.get_doc_before_save()
	if not previous or previous.get("workflow_state") != "Entregue":
		return
	for fieldname, label in (
		("pickup_date", "data de entrega"),
		("warranty_expiry", "validade da garantia"),
		("estimated_deadline", "prazo estimado"),
	):
		if str(previous.get(fieldname) or "") != str(doc.get(fieldname) or ""):
			frappe.throw(f"A {label} de uma OS entregue e imutavel.")
```
This is the EDIT-04 backstop, invoked as a `doc.validate` hook (confirm exact hook registration in `hooks.py` if the plan needs to reference the wiring — not required to touch this file at all this phase).

---

### `frontend/src/App.tsx` — audit indicator on the "entrada" stage screen

**Analog:** itself. `editEntry` handler (lines 4915-4941) and the "entrada" render block (lines 4942-4960), already read in full. `IdentityCard` component (lines 5712-5732+), already read.

Current render for the identity card that should host the indicator:
```tsx
<IdentityCard
  action={whatsappUrl ? <a ...>Abrir WhatsApp</a> : undefined}
  icon={<UserRound size={20} />}
  lines={[["Cliente", customerLabel], ["Contato desta OS", detail.os_contact_name || customerLabel], ["Telefone desta OS", detail.os_contact_phone || ...], ["E-mail", ...], ["Atendente", detail.attendant ?? "Não definido"]]}
  title="Cliente"
/>
```

**Pattern to extend (D-07):** `IdentityCard`'s `lines` prop is `Array<[string, string]>` — append a conditional `["Editado por", "..."]` line, OR add a small caption below the card body using the same `text-tec-muted` styling used elsewhere (e.g. line 4867's `text-xs font-semibold text-tec-muted` label pattern). Source the value from a new field returned by `get_service_order_detail` (backend), e.g. `detail.entry_audit?.actor` / `.occurred_on`, populated server-side via `get_latest_reference_audit("Service Order", doc.name)` inside `get_service_order_detail` (line 1467+, already located — the return dict starts at `"name": doc.name, ...`).

```tsx
{detail.entry_audit ? (
  <p className="mt-2 text-xs text-tec-muted">
    Editado por {detail.entry_audit.actor} em {formatDateTime(detail.entry_audit.occurred_on)}
  </p>
) : null}
```
(`formatDateTime`-equivalent helper — check for an existing date formatter already imported in `App.tsx`, e.g. search for `toLocaleDateString`/`Intl.DateTimeFormat` usage, before introducing a new one.)

**API type update needed:** `ServiceOrderDetailResponse` (type definition, likely in `frontend/src/api/serviceOrders.ts` or a shared types file) needs a new optional `entry_audit?: { actor: string; occurred_on: string; change_type: string } | null` field to match the backend addition.

**EDIT-03 new edit affordance:** no existing UI edits `Customer` name/CPF from this screen. Follow the exact `editEntry` prompt-based pattern (lines 4915-4941: sequential `window.prompt` calls, null-checks to allow cancel, try/catch calling the API and toasting) as the minimum viable interaction, reusing `serviceOrders.updateEntry`-style API helper module structure — add a `customers.update(name, payload)` method to whichever API module wraps customer endpoints (find via `grep customer_name` in `frontend/src/api/`), mirroring `updateEntry`'s shape in `serviceOrders.ts`:
```ts
updateEntry(name: string, payload: Record<string, string>) {
	return rpc<ServiceOrderDetailResponse>(`${API}.update_service_order_entry`, { body: { name, payload } });
},
```

---

### `tecponto_app/tecponto/frontend/test_frontend_api.py` — new `run_edit_audit_checks()`

**Analog:** `run_pos_tradein_cost_guard_checks` (line 9205+, already read the opening ~55 lines) and the general `run_*_checks() -> dict` convention (20+ sibling functions found via grep, e.g. `run_used_device_warranty_claim_checks`, `run_post_sale_checks`).

**Shape to follow:**
```python
def run_edit_audit_checks() -> dict:
	"""..."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		customer = _get_or_create_demo_customer()
		# ... build a real Service Order fixture via existing check-in helpers ...
		frappe.db.commit()

		frappe.set_user(attendant)
		# exercise update_service_order_entry with a device-credential sentinel value
		sentinel = f"SENTINEL-{frappe.generate_hash(length=10)}"
		updated = update_service_order_entry(so_name, {"device_access_type": "PIN", "device_access_credential": sentinel, ...})

		# assert Tecponto Access Audit rows never contain the sentinel anywhere
		audit_rows = frappe.get_all("Tecponto Access Audit", filters={"reference_name": so_name}, fields=["before_state", "after_state"])
		for row in audit_rows:
			if sentinel in (row.before_state or "") or sentinel in (row.after_state or ""):
				raise AssertionError("Sentinela vazou para a trilha de auditoria de acesso.")

		# assert Técnico role is blocked from update_service_order_entry / update_customer
		frappe.set_user(technician)
		try:
			update_service_order_entry(so_name, {"os_contact_name": "x"})
			raise AssertionError("Técnico não deveria poder editar a Entrada.")
		except frappe.PermissionError:
			pass

		return {"ok": True, ...}
	finally:
		frappe.set_user(previous_user)
```

Reuse `_find_or_create_user`, `_get_or_create_demo_customer`, `ensure_frontend_foundation`, `frappe.generate_hash` — all already present as test helpers in this file (seen used by `run_pos_tradein_cost_guard_checks`).

## Shared Patterns

### Audit-write single choke point
**Source:** `tecponto_app/tecponto/user_access.py::_write_audit` (lines 264-277)
**Apply to:** every EDIT-01/02/03 write path. Never insert a `Tecponto Access Audit` doc directly from `api.py` — always go through `_write_audit`/`audit_reference_field_edit` so the immutability/permission model stays centralized in one module.

### Role gate
**Source:** `tecponto_app/tecponto/frontend/api.py:107-112` (`CHECKIN_ALLOWED_ROLES`), enforced via `_require_checkin_role()` (line 275-277: `if set(frappe.get_roles(frappe.session.user)).intersection(CHECKIN_ALLOWED_ROLES): return` then implicit throw otherwise — read the full function body before use to confirm the throw branch).
**Apply to:** `update_service_order_entry` (already has it) and the new `update_customer` (must add it, same call, first line of function body).

### Sensitive-field non-leak discipline
**Source:** CLAUDE.md §1.2 + D-03 (`{"device_access_type": ..., "had_credential": bool}` shape) + existing precedent `audit_password_change` in `user_access.py` (`before={"credential": "withheld"}, after={"credential": "changed"}` — never the actual password).
**Apply to:** device-credential audit rows only. Contact/name/CPF audit rows use real values (D-04) — do not over-apply this masking pattern there.

## No Analog Found

None — every file in scope has a strong same-role, same-data-flow analog already in the codebase.

## Metadata

**Analog search scope:** `tecponto_app/tecponto/{user_access.py, frontend/api.py, frontend/test_frontend_api.py, customer.py, service_order/policies.py, doctype/tecponto_access_audit/}`, `frontend/src/{App.tsx, api/serviceOrders.ts}`
**Files scanned:** 9 read/grepped directly, plus targeted greps across `frontend/src/`
**Pattern extraction date:** 2026-09-18
