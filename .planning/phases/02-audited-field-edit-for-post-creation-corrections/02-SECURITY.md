---
phase: "2"
slug: "audited-field-edit-for-post-creation-corrections"
status: verified
threats_open: 0
asvs_level: 1
created: "2026-09-19"
---

# Phase 2 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| React client → `update_service_order_entry` / `update_customer` / `get_service_order_detail` | Untrusted operator-supplied payloads (contact, credential, identity edits) cross here; role and field allowlist enforcement is server-side | OS contact PII, device credential (write-only), customer PII |
| `update_service_order_entry` → `Tecponto Access Audit` | The credential-handling write path into a persistent, `System Manager`-readable store — the highest-risk edge this phase introduces | Device credential metadata only (never the secret) |
| Application code → `Tecponto Access Audit` doctype (schema migration) | The audit log is append-only evidence; the migrated schema (relaxed `affected_user`, new `reference_doctype`/`reference_name`) must not widen who can read it | Audit rows for both User-scoped (pre-existing) and reference-scoped (new) changes |
| `get_service_order_detail` payload → operational roles | Every new key (`entry_audit`, `customer_audit`) widens an already-guarded payload also served to restricted technicians | Actor/change_type/timestamp of edits — never before/after state, never the credential |
| React client → new `update_customer` RPC | A brand-new whitelisted write surface onto the `Customer` doctype; inherits none of the existing endpoints' protections automatically | Customer name, CPF |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Information Disclosure | `tecponto_access_audit.json` schema migration | high | mitigate | `permissions` left byte-identical (`System Manager` only), asserted by schema check; prior User-scoped rows have empty `reference_doctype`/`reference_name` so `get_latest_reference_audit`'s dual-field filter structurally cannot match them | closed |
| T-02-02 | Information Disclosure | `entry_audit` key on `get_service_order_detail` | high | mitigate | Populated only for `AUDIT_INDICATOR_ROLES` (System Manager/Gestor/Diretor), `None` otherwise; verified live: `front-atendente` → `null`, `front-gestor` → real entry. `_serialize_reference_audit` emits only actor/change_type/occurred_on, never before/after_state | closed |
| T-02-03 | Repudiation | `Tecponto Access Audit` rows | high | mitigate | `validate_access_audit_immutable`/`prevent_access_audit_deletion` unchanged in `hooks.py`; `immutability_survives_migration: true` confirmed by fresh suite run | closed |
| T-02-04 | Spoofing | `actor` field on new audit rows | medium | mitigate | `_write_audit` sets `actor` from `frappe.session.user` only; verified live — audit row for a cross-operator edit attributed `front-atendente@tecponto.local`, not the escalated `Administrator` | closed |
| T-02-05 | Elevation of Privilege | `update_service_order_entry` | high | mitigate | `_require_checkin_role()` + `check_permission("write")` unchanged; `technician_blocked: true` confirmed by fresh suite run | closed |
| T-02-06 | Tampering | `pickup_date`/`warranty_expiry` via the edit endpoint | high | transfer | Transferred to 02-02's explicit EDIT-04 regression; `delivery_dates_ignored_by_edit`/`closed_os_edit_blocked`/`delivery_dates_immutable_on_delivered_os` all confirmed `true`, independently re-verified against a live OS's baseline dates | closed |
| T-02-07 | Information Disclosure | OS contact name/phone in `before_state`/`after_state` | low | accept | D-04: ordinary PII already visible to Atendente/Gestor; raw rows remain System-Manager-only read | closed (accepted) |
| T-02-08 | Information Disclosure | device credential in `before_state`/`after_state` | critical | mitigate | D-03 metadata-only shape read directly in code (`device_access_type`/`had_credential`/`credential_rotated` only); `grep -c 'get_password\|get_decrypted_password'` returns 0 in `api.py`; sentinel scan (`sentinel_not_in_access_audit: true`) confirmed live | closed |
| T-02-09 | Information Disclosure | audit log as unenumerated leak channel | high | mitigate | `access_audit` added to `run_device_credential_non_leak_checks`'s channel list, confirmed live: `channels: [..., "access_audit"]` | closed |
| T-02-10 | Information Disclosure | credential re-exposed post-rotation | high | mitigate | `detail_masked_after_rotation: true` confirmed; personally verified via real browser edit — rotated value never appeared on screen, then reload-confirmed | closed |
| T-02-11 | Tampering | delivery/warranty dates via credential edit payload | high | mitigate | `text_fields` allowlist structurally excludes them; `_validate_delivery_dates_are_immutable` backstop on delivered OS; both proven live | closed |
| T-02-12 | Elevation of Privilege | new branch inside `update_service_order_entry` | high | mitigate | `technician_blocked_from_credential_edit: true` confirmed live | closed |
| T-02-13 | Repudiation | a credential rotation leaving no trace | medium | mitigate | Audit call guarded by `credential_touched and before != after`; `credential_rotated_flag_honest: true` confirmed | closed |
| T-02-14 | Denial of Service | unbounded audit row growth | low | accept | Append-only by design; no-op short-circuit already prevents churn; single-store pilot scale | closed (accepted) |
| T-02-15 | Elevation of Privilege | `update_customer` bypassing `CHECKIN_ALLOWED_ROLES` | high | mitigate | `_require_checkin_role()` mandated first statement; `technician_blocked_from_customer_edit: true` confirmed. **Hardened during this security review's own verification pass**: real browser/one-off-container testing found `update_customer` 403ing for a legitimate attendant correcting a customer they did not create (ERPNext `Customer.on_update → create_primary_contact()` saving the linked Contact without an `ignore_permissions` passthrough) — fixed in `cacbb21` via `as_user("Administrator")` scoped to the single `save()` call, confirmed the audit row still attributes the real operator, and pinned with a new regression test (`cross_operator_edit_allowed`, commit `029cc5f`) so this exact class of gap cannot silently regress | closed |
| T-02-16 | Tampering | partial-update path writing an invalid Customer record | high | mitigate | `validate_customer_contact_document` reused against merged `customer.as_dict()` + payload; `invalid_cpf_rejected: true` confirmed live, including a re-test against a correctly-configured fixture after an initial false result traced to an unrelated `custom_nao_possui_cpf` flag on the first fixture tried (not a code defect — a test-setup artifact) | closed |
| T-02-17 | Tampering | endpoint widened beyond EDIT-03's named fields | medium | mitigate | Only `customer_name`/`custom_cpf` assigned, each behind a key-presence check; confirmed by direct code read | closed |
| T-02-18 | Information Disclosure | new PII on the OS detail payload | medium | mitigate | `custom_cpf` deliberately not added to the customer detail interface; `customer_audit_role_gated: true` confirmed live (attendant → `null`, manager → real) | closed |
| T-02-19 | Information Disclosure | customer name/CPF in `before_state`/`after_state` | low | accept | D-04: ordinary PII already visible to Atendente/Gestor at the counter; raw rows remain System-Manager-only read | closed (accepted) |
| T-02-20 | Repudiation | an identity correction leaving no trace | high | mitigate | `customer_identity_audited: true` and `no_op_writes_nothing` confirmed; `audit_reference_field_edit` is the sole writer | closed |
| T-02-21 | Spoofing | a dead UI button that appears to save but does not | medium | mitigate | Personally driven through the real browser UI (Journeys 1–3) with a full page re-navigation between edit and check — confirmed server-side persistence, not optimistic local state | closed |
| T-02-22 | Tampering | widened `_write_audit` regressing the pre-existing User-scoped audit path | high | mitigate | `gsd-verifier` independently re-ran the full foundation suite fresh (not a SUMMARY re-quote): `user_access_checks`/`user_management_checks` both still pass in full | closed |
| T-02-23 | Information Disclosure | credential visible on a surface nobody wrote an assertion for | high | mitigate | Personally drove Journey 2 in the real browser — screen, toast, OS list scanned by page-text extraction, sentinel absent throughout, on top of the automated site-wide sentinel scan | closed |
| T-02-24 | Spoofing | a correction button rendering without persisting | high | mitigate | Journeys 1 and 3 required a full page re-navigation before accepting the result — real server-side persistence confirmed, not client cache | closed |
| T-02-25 | Information Disclosure | audit indicator leaking to the wrong role | medium | mitigate | Personally verified both directions live via `get_service_order_detail` as `front-atendente` (null) and `front-gestor` (real entries) for both `entry_audit` and `customer_audit` | closed |
| T-02-26 | Tampering | a stale container passing the suite against unmigrated schema | medium | mitigate | CI builds an ephemeral site from scratch on every run — confirmed green twice (`cacbb21` run 35417761552, `f88302c` run 35419347993), which cannot be stale by construction | closed |
| T-02-27 | Denial of Service | host instability consuming phase budget / masking real defects | medium | accept | Known, separately tracked (`AUDITORIA_SISTEMA.md`, 5.9GB RAM host). Materialized worse than expected this phase (a full WSL2 VM self-reboot mid-session) — worked around throughout via disposable one-off containers against the persistent site/DB volumes; CI relied on as the non-negotiable integration truth per GEMINI.md §4 | closed (accepted) |
| T-02-SC | Tampering | npm/pip/cargo installs | n/a | accept | No package-manager install task in any of the 4 plans or this security review's own regression-test addition; no `package.json`/requirements change. Package-legitimacy gate not triggered | closed (accepted) |

*Status: open · closed · open — below {block_on} threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-02-01 | T-02-07 | OS contact name/phone are ordinary PII already visible to Atendente/Gestor on the OS detail screen; raw audit rows stay System-Manager-only | Discuss-phase decision D-04 | 2026-09-18 |
| R-02-02 | T-02-14 | Append-only audit growth is the intended design at single-store pilot scale; no-op short-circuit already bounds churn | Plan 02-02 threat model | 2026-09-18 |
| R-02-03 | T-02-19 | Customer name/CPF are ordinary PII already visible to Atendente/Gestor at the counter; applying credential-grade masking here would destroy the before/after evidence EDIT-03 requires | Discuss-phase decision D-04 | 2026-09-18 |
| R-02-04 | T-02-27 | Chronic local Docker/WSL2 host instability (5.9GB RAM) is a pre-existing, separately-tracked environment issue, not a phase-introduced risk; CI is the accepted integration-truth substitute per GEMINI.md §4 | Plan 02-04 threat model | 2026-09-18 |
| R-02-05 | T-02-SC | No new dependency introduced anywhere in this phase, including its own security-review regression test | This review | 2026-09-19 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-19 | 27 (+ 4× T-02-SC, one per plan) | 27 (+4) | 0 | Claude (orchestrator), retroactive from PLAN.md threat models — register_authored_at_plan_time: true, ASVS L1 short-circuit; evidence drawn from direct code reads and live re-execution performed during this phase's execution and closure, not from SUMMARY.md prose alone. One mitigation (T-02-15) was actively hardened during this review's own verification pass, with a new regression test added. |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-19
