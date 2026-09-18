# Phase 2: Audited Field-Edit for Post-Creation Corrections - Context

**Gathered:** 2026-09-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Atendente/Gestor can correct contact, device-credential, and customer-identity data on an already-created OS, with every change tracked, while delivery and warranty dates remain provably untouchable. Maps to EDIT-01 (OS contact), EDIT-02 (device credential), EDIT-03 (customer name/CPF), EDIT-04 (immutability guarantee for `pickup_date`/`warranty_expiry`). Does NOT reopen a delivered OS for general correction, and does NOT touch the `courtesy_warranty` override gate (both explicitly out of scope per REQUIREMENTS.md).

</domain>

<decisions>
## Implementation Decisions

### Audit trail mechanism
- **D-01:** Extend the existing `Tecponto Access Audit` doctype rather than create a parallel one. Relax `affected_user` (currently `Link` to `User`, `reqd=1`) to optional, and add generic `reference_doctype` / `reference_name` fields (Dynamic Link pattern) so a row can point at a `Service Order` or `Customer` instead of only a `User`. Existing User-scoped rows keep using `affected_user`; new EDIT-01/02/03 rows use `reference_doctype`/`reference_name` and leave `affected_user` empty. Reuses the doctype's existing immutability hooks (`validate_access_audit_immutable`, `prevent_access_audit_deletion`) and its `System Manager`-only read/report/export permission as-is — no new permission surface needed for the raw log.
- **D-02:** `change_type` (free `Data` field, already untyped) gets new literal values for this phase, e.g. `"os_contact_edit"`, `"device_credential_edit"`, `"customer_identity_edit"` — planner's discretion on exact strings, but they must be distinct per edit type so the log is filterable.

### Device credential audit content (security-critical)
- **D-03:** `before_state`/`after_state` for a device-credential edit (EDIT-02) must contain **only metadata** — e.g. `{"device_access_type": "PIN", "had_credential": true}` — and must **never** contain the raw credential value, a masked fragment, length, or any derivative of it, before or after. This is a hard rule, not a style preference: the credential is sensitive data under CLAUDE.md security rule #2, and the audit log is itself a channel that must pass the mandatory sentinel test (a unique sentinel value written as a credential must not appear in `Tecponto Access Audit` rows, same as it must not appear in OS lists, print formats, tracking links, or WhatsApp messages).
- **D-04:** For EDIT-01 (OS contact) and EDIT-03 (customer identity), `before_state`/`after_state` capture the actual field values changed (name/phone, name/CPF) — these are not sensitive under the CLAUDE.md rules, ordinary PII already visible to Atendente/Gestor.

### Access gate and justification
- **D-05:** All three edit types (EDIT-01/02/03) use the same role gate already established for check-in: `CHECKIN_ALLOWED_ROLES` = `{System Manager, Tecponto Atendente, Tecponto Gestor}` (`tecponto_app/tecponto/frontend/api.py:107`). Técnico is excluded, consistent with role separation elsewhere in the project.
- **D-06:** No typed justification/reason field is required for these edits. The automatic before/after snapshot is the evidence. This is different from `courtesy_warranty`/`path_conversion_reason`, which are policy *exceptions* needing a written rationale — a field correction is not a policy exception.

### Audit trail visibility
- **D-07:** The audit trail must be visible in the UI, not backend-only. Add a small inline indicator (e.g., "editado por {actor} em {date}") visible to Gestor/Diretor on the OS detail screen (for EDIT-01/02) and on the Customer-facing edit surface (for EDIT-03), sourced from the newest matching `Tecponto Access Audit` row for that `reference_doctype`/`reference_name`. Exact placement/component styling is planner/executor discretion — this phase is functional-first per `CLAUDE.md` section 3 (polish happens in the single design pass in Phase 4).

### Claude's Discretion
- Exact `change_type` string values.
- Exact shape/placement of the "editado por X em Y" UI indicator (which component, exact copy).
- Whether the new Customer-edit endpoint reuses `validate_customer_contact_document` as-is or wraps it (existing validator from `create_customer`, must be reused for CPF/contact-document validation consistency — not reinvented).

</decisions>

<specifics>
## Specific Ideas

No specific visual/interaction references given — this phase is functional-first per project design guidelines (structure/hierarchy reasoning happens per-screen at plan time, cosmetic polish deferred to Phase 4's single pass).

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Security rules (non-negotiable, apply directly to EDIT-02)
- `CLAUDE.md` §1.2 — Device password/PIN/pattern is sensitive data: encrypted at rest, always masked, revealed only under intentional audited action, mandatory sentinel testing across every channel (OS lists, print formats, tracking links, WhatsApp).
- `CLAUDE.md` §1.3 — Lifecycle locks and role gates live in the Python engine, never only in React; nothing may be bypassed even to make tests pass.

### Requirements and scope
- `.planning/REQUIREMENTS.md` lines 27-32 (EDIT-01 through EDIT-04) — exact requirement wording, including "reusando o padrão `Tecponto Access Audit`" for EDIT-01.
- `.planning/REQUIREMENTS.md` Out of Scope table — explicitly excludes reopening a delivered OS for general correction, and excludes loosening the `courtesy_warranty` gate.
- `.planning/ROADMAP.md` §"Phase 2: Audited Field-Edit for Post-Creation Corrections" — phase goal and success criteria.

### Existing patterns this phase extends
- `tecponto_app/tecponto/user_access.py` lines 220-289 — `_write_audit()` and `_access_snapshot()`: the exact shape being extended (D-01/D-02).
- `tecponto_app/tecponto/doctype/tecponto_access_audit/tecponto_access_audit.json` — current schema to be migrated (relax `affected_user`, add `reference_doctype`/`reference_name`).
- `tecponto_app/hooks.py` lines 282-285 — `doc_events["Tecponto Access Audit"]` immutability hook registration, applies to any row regardless of what it references.
- `tecponto_app/tecponto/service_order/policies.py` lines 152-167 — `_validate_delivery_dates_are_immutable()`, the existing EDIT-04 backstop (blocks `pickup_date`/`warranty_expiry`/`estimated_deadline` changes once `workflow_state == "Entregue"`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `update_service_order_entry` (`tecponto_app/tecponto/frontend/api.py:2441`) — **already implements EDIT-01 and EDIT-02's actual field edits today**, with zero audit logging. It edits `os_contact_name`/`os_contact_phone` and (via `_save_device_access_credential`) `device_access_type`/`device_access_credential`. Already gated by `_require_checkin_role()` and blocks editing once `workflow_state` is `Entregue`/`Cancelado`. Its field allowlist (`text_fields` set) structurally never touches `pickup_date`/`warranty_expiry`/`estimated_deadline` — EDIT-04 is already satisfied here by omission, should be covered by a regression test proving it, not just left implicit.
- `_save_device_access_credential` (`tecponto_app/tecponto/frontend/api.py:4753`) — "Rotate a device-owned credential; blank input preserves an existing secret." Already handles masking-on-write correctly (never echoes the value back). This phase adds the audit call around it, does not change its logic.
- `validate_customer_contact_document` (used by `create_customer`, `tecponto_app/tecponto/frontend/api.py:3439`) — CPF/RG/contact validation to reuse for the new Customer-edit endpoint (EDIT-03).
- `as_user()` helper (`tecponto_app/tecponto/permissions.py`) — safe privilege-escalation pattern from the prior audit fix; not expected to be needed here since edits run under the operator's own session, but available if a write path needs elevated privilege.

### Established Patterns
- `_write_audit(*, affected_user, change_type, before, after)` in `user_access.py` — the exact function signature/shape to extend (add optional `reference_doctype`/`reference_name` params) rather than write a second audit-writing function.
- Extend-don't-duplicate convention (from Phase 3's `03-CONTEXT.md`) — applies directly: extend `update_service_order_entry` and the `Tecponto Access Audit` doctype rather than building new parallel endpoints/doctypes for EDIT-01/02.
- `run_*_checks()` test-function shape (from Phase 3) — expected convention for this phase's new tests too (e.g. `run_edit_audit_checks()` in `test_frontend_api.py`).

### Integration Points
- EDIT-03 (Customer name/CPF) has **no existing update endpoint** — `create_customer` is creation-only. A new `@frappe.whitelist()` endpoint (e.g. `update_customer`) must be built, gated by the same `CHECKIN_ALLOWED_ROLES`, reusing `validate_customer_contact_document`.
- Frontend: OS contact/device-credential edit UI likely already has a form calling `update_service_order_entry` (check `frontend/src/App.tsx`/`ServiceOrderFlows.tsx` at plan/research time) — this phase adds the audit-indicator display, not a new edit form, for EDIT-01/02. EDIT-03 needs a new edit affordance since no endpoint existed before.

</code_context>

<deferred>
## Deferred Ideas

- Auditing/logging every time the device credential is *revealed* for the internal print label (`get_internal_service_order_print_context` in `tecponto_app/tecponto/service_order/print_formats.py:168` reveals the real credential with zero audit trail today) — discovered during scouting, appears to be a pre-existing gap relative to CLAUDE.md §1.2's "revelada somente sob ação intencional e autorizada, com registro de auditoria" rule, but it is a *reveal-for-print* audit gap, not a *post-creation correction* — out of this phase's scope as defined by EDIT-02's wording. Worth a separate follow-up.
- Extending the generic `reference_doctype`/`reference_name` audit pattern to other doctypes beyond Service Order/Customer — no other candidate identified yet, not needed until one appears.

</deferred>

---

*Phase: 02-audited-field-edit-for-post-creation-corrections*
*Context gathered: 2026-09-18*
