---
phase: 02-audited-field-edit-for-post-creation-corrections
verified: 2026-09-19T03:36:58Z
status: passed
score: 10/10 must-haves verified
behavior_unverified: 0
overrides_applied: 0
coincidental_reliance_items: []
---

# Phase 2: Audited Field-Edit for Post-Creation Corrections Verification Report

**Phase Goal:** Atendente/Gestor can correct contact, device-credential, and customer-identity data on an already-created OS, with every change tracked, while delivery and warranty dates remain provably untouchable.
**Verified:** 2026-09-19T03:36:58Z
**Status:** passed
**Re-verification:** No — initial verification

## Method

This verification did not rely on SUMMARY.md prose as evidence. For every claim it:
1. Read the actual production code (`api.py`, `user_access.py`, `tecponto_access_audit.json`, `hooks.py`, `App.tsx`, `balcao.ts`, `types.ts`) line by line against the plan's `must_haves`.
2. Independently re-ran the full foundation suite (`./scripts/test-local.sh`, real MariaDB/Redis/Frappe one-off container against `local-ci.local`, ~7 minutes, `bench migrate` + `run_foundation_checks`) from scratch in this session — not a re-quote of a prior run.
3. Independently re-ran `npm run build` (tsc --noEmit + vite build + verify-foundation.mjs) in this session.
4. Checked GitHub Actions CI (`gh run list`) directly against the commit hash the SUMMARY names.
5. Read the git diff of the fix commit (`cacbb21`) to confirm the documented `update_customer` 403 fix is exactly what shipped.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Atendente/Gestor edits OS contact name/phone after creation; detail view shows new value; audit record shows who/when/before/after (EDIT-01) | ✓ VERIFIED | `update_service_order_entry` (api.py:2453) computes `before_contact`/`after_contact`, calls `audit_reference_field_edit(change_type="os_contact_edit", ...)` only when changed; `get_service_order_detail` returns `entry_audit` gated to `AUDIT_INDICATOR_ROLES`. Independently re-ran `run_edit_audit_checks` (nested in a fresh full-suite run): `"edit_audit_checks": {"status": "ok", "audit_row_written": true, "change_type": "os_contact_edit", ...}` |
| 2 | Device credential can be corrected after creation; remains masked in every view before/after; audit record never contains plaintext, only that it changed (EDIT-02) | ✓ VERIFIED | `_save_device_access_credential` (api.py:4854) unchanged, never echoes the secret; new code (api.py:2469-2513) computes `before_credential_meta`/`after_credential_meta` from `device_access_type` presence only (`frappe.db.get_value`, never `get_password`/`get_decrypted_password` — confirmed `grep -c 'get_password\|get_decrypted_password' api.py` = 0). Fresh suite run: `device_credential_metadata_only: true`, `sentinel_not_in_access_audit: true`, `detail_masked_after_rotation: true`; `run_device_credential_non_leak_checks` embedded in the same run reports `"channels": ["access_audit", "budget", "communication", "customer_documents", "public_link"]`, `"sentinel_not_leaked": true` |
| 3 | Customer name/CPF can be corrected after creation, with same who/when/before/after audit trail (EDIT-03) | ✓ VERIFIED | `update_customer` (api.py:3513) reuses `validate_customer_contact_document` via merge-wrap, writes `customer_identity_edit` audit rows with real (unmasked) before/after values per D-04. Fresh suite run: `customer_identity_audited` implied by `partial_edit_passes_validator: true`, `invalid_cpf_rejected: true`, `technician_blocked_from_customer_edit: true`, `customer_audit_role_gated: true` all true |
| 4 | Attempting to alter `pickup_date`/`warranty_expiry` through the edit capability (API or UI, any role) is rejected (EDIT-04) | ✓ VERIFIED | `text_fields` allowlist in `update_service_order_entry` structurally excludes the three date fields (read at api.py:2462-2465 — only `reported_defect`, `physical_state`, `attendance_notes`, `entry_operating_condition`, `accessories_received`, `os_contact_name`, `os_contact_phone`); `_validate_delivery_dates_are_immutable` (policies.py) is the independent engine-level backstop, untouched by this phase. Fresh suite run: `delivery_dates_ignored_by_edit: true`, `closed_os_edit_blocked: true`, `delivery_dates_immutable_on_delivered_os: true` |
| 5 | Edit audit records cannot be modified or deleted by any role once written | ✓ VERIFIED | `hooks.py:282-285` registers `validate_access_audit_immutable`/`prevent_access_audit_deletion` on `Tecponto Access Audit`, byte-identical before/after this phase (`git diff --stat` confirmed empty across all phase-02 commits). Fresh suite run: `immutability_survives_migration: true` |
| 6 | Tecponto Access Audit doctype migration (D-01) lands exactly as specified: `affected_user` optional, `reference_doctype`/`reference_name` added, `permissions`/`track_changes`/`hooks.py` unchanged | ✓ VERIFIED | Read `tecponto_access_audit.json` directly: `field_order` is the exact 8-entry list, no `reqd` on `affected_user`, `permissions` is byte-identical (`System Manager` only) |
| 7 | Device-credential audit content is metadata-only, never the raw credential, a fragment, or its length (D-03, GEMINI.md §1.2) | ✓ VERIFIED | Read the credential-audit code path directly: only `device_access_type`/`had_credential`/`credential_rotated` keys are ever constructed; presence derived via `frappe.db.get_value`, never decryption. Fresh suite run's own key-whitelist assertion (Test 2) and substring/length non-leak scan (Test 3) and site-wide sentinel scan both passed live in this session, not just quoted from a prior SUMMARY |
| 8 | `update_customer` is gated by `CHECKIN_ALLOWED_ROLES` (D-05) and reuses (never reimplements) `validate_customer_contact_document` | ✓ VERIFIED | `_require_checkin_role()` is `update_customer`'s first statement (api.py:3515); `grep -c 'def validate_customer_contact_document' api.py` = 0 (no copy pasted); merge-wrap (`{**customer.as_dict(), **data}`) confirmed by direct read |
| 9 | The real permission bug (`update_customer` 403 for an attendant correcting a customer they didn't create) is actually fixed, not just claimed | ✓ VERIFIED | Read `git show cacbb21` diff directly: `customer.save(ignore_permissions=True)` is wrapped in `with as_user("Administrator"):`; `as_user` (permissions.py:74) is confirmed to be the safe session-scoped escalation helper (touches only `frappe.session.user` and permission caches, never `.sid`/`.data` — unlike `frappe.set_user()`), not a security bypass. CI green on this exact commit (see below) |
| 10 | Full regression suite: the widened `_write_audit` and the doctype migration did not break the pre-existing User-scoped audit path or any other of the ~90 check groups | ✓ VERIFIED | Independently re-ran the ENTIRE `run_foundation_checks` suite from scratch this session (fresh `bench migrate` + full suite, not a partial re-run): top-level `"status": "ok"`; `user_access_checks: {"status": "ok", ..., "audit_recorded": true, "audit_update_blocked": true, "audit_delete_blocked": true}`; `user_management_checks: {"status": "ok", ...}` — both check groups the plan specifically named as at-risk from the widened `_write_audit` pass clean |

**Score:** 10/10 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `tecponto_access_audit.json` | migrated schema (D-01) | ✓ VERIFIED | Read directly, matches spec exactly |
| `tecponto_app/tecponto/user_access.py` | widened `_write_audit`, new `audit_reference_field_edit`/`get_latest_reference_audit` | ✓ VERIFIED | Read directly (lines 268-321); single `_write_audit` definition (`grep -c 'def _write_audit'` = 1) |
| `tecponto_app/tecponto/frontend/api.py` | audit wiring in `update_service_order_entry`; new `update_customer`; `entry_audit`/`customer_audit` on detail | ✓ VERIFIED | Read directly at all four call sites |
| `tecponto_app/tecponto/frontend/test_frontend_api.py` | `run_edit_audit_checks()` covering all four requirements, wired into `run_foundation_checks` | ✓ VERIFIED | Read the ~550-line function directly; confirmed wired at lines 356/442; independently executed, all facts true |
| `frontend/src/api/types.ts` | `ReferenceAuditIndicator`, `entry_audit`/`customer_audit`, `UpdateCustomerPayload`/`UpdateCustomerResponse` | ✓ VERIFIED | Read directly; all types present and exported |
| `frontend/src/api/balcao.ts` | `updateCustomer(name, payload)` | ✓ VERIFIED | Read directly, calls `${API}.update_customer` |
| `frontend/src/App.tsx` | `editEntry`/`editCustomer` handlers, two audit-indicator captions | ✓ VERIFIED | Read directly (lines 4914-4993); both handlers call the real API, refetch, and re-render via `onUpdated`; both captions render conditionally on `detail.entry_audit`/`detail.customer_audit` |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `update_service_order_entry` | `Tecponto Access Audit` | `audit_reference_field_edit` (single choke point) | WIRED | Read directly; `grep -c 'audit_reference_field_edit'` in api.py = 4 (1 import + 3 real call sites: contact, credential, customer identity) — no second writer |
| `update_customer` | `validate_customer_contact_document` | merge-wrap of `customer.as_dict()` + payload | WIRED | Read directly; validator genuinely re-invoked, not duplicated (0 copies in api.py) |
| `get_service_order_detail` | `get_latest_reference_audit` | `AUDIT_INDICATOR_ROLES` gate | WIRED | Read directly at both `entry_audit` and `customer_audit` keys; role-gated identically |
| `App.tsx` button handlers | `serviceOrders.updateEntry` / `balcao.updateCustomer` | real RPC calls, real refetch via `onUpdated` | WIRED | Read directly — not a placeholder button; the customer-edit path additionally re-fetches full detail via `serviceOrders.detail()` before re-rendering, so the indicator reflects real server state |
| CI pipeline | `run_foundation_checks` + `npm run build` | `.github/workflows/publish-image.yml` | WIRED | Confirmed the workflow actually executes `bench --site ... execute ... run_foundation_checks` and `npm run build`, not merely an image publish |

### Live Re-Execution Evidence (this session, not quoted from SUMMARY.md)

```
$ ./scripts/test-local.sh   (fresh one-off container against real MariaDB/Redis, full bench migrate + run_foundation_checks)
...
{"status": "ok", ... "edit_audit_checks": {"status": "ok", "audit_row_written": true, "change_type": "os_contact_edit",
 "no_op_writes_nothing": true, "manager_sees_entry_audit": true, "attendant_sees_no_entry_audit": true,
 "immutability_survives_migration": true, "technician_blocked": true, "user_scoped_audit_backwards_compatible": true,
 "frontend_source_markers": {"app_tsx": true}, "device_credential_audit_written": true,
 "device_credential_metadata_only": true, "credential_rotated_flag_honest": true,
 "untouched_edit_writes_no_audit_row": true, "sentinel_not_in_access_audit": true,
 "detail_masked_after_rotation": true, "delivery_dates_ignored_by_edit": true, "closed_os_edit_blocked": true,
 "delivery_dates_immutable_on_delivered_os": true, "technician_blocked_from_credential_edit": true,
 "customer_identity_audited": true, "partial_edit_passes_validator": true, "invalid_cpf_rejected": true,
 "technician_blocked_from_customer_edit": true, "customer_audit_role_gated": true,
 "frontend_customer_edit_pinned": true} ...
 "device_credential_guard": {"status": "ok", "sentinel_not_leaked": true,
 "channels": ["access_audit", "budget", "communication", "customer_documents", "public_link"],
 "unauthorized_technician_blocked": true} ...
 "user_access_checks": {"status": "ok", ..., "audit_recorded": true, "audit_update_blocked": true, "audit_delete_blocked": true}
 "user_management_checks": {"status": "ok", ...} }
```

```
$ npm --prefix frontend run build
✓ built in 2.58s
Fundação frontend verificada: build, tokens e fonte sem termos sensíveis.
```

```
$ gh run list --limit 10 --json conclusion,status,url,headBranch,headSha
{"conclusion":"success","headSha":"cacbb217215619fed5165def1402b29e86aa827e", ...}   <- the update_customer fix commit
```

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| EDIT-01 | 02-01 | OS contact correction, audited | ✓ SATISFIED | Truths 1, 6, artifacts, key links above |
| EDIT-02 | 02-02 | Device credential correction, masked, audited metadata-only | ✓ SATISFIED | Truths 2, 7 above |
| EDIT-03 | 02-03 | Customer name/CPF correction, audited with real values | ✓ SATISFIED | Truths 3, 8, 9 above |
| EDIT-04 | 02-02 (regression proof) | Delivery/warranty dates immutable through the edit capability | ✓ SATISFIED | Truth 4 above (two independent layers: allowlist omission + engine-level `_validate_delivery_dates_are_immutable`) |

No orphaned requirements — REQUIREMENTS.md maps exactly EDIT-01 through EDIT-04 to Phase 2, and all four appear in plan frontmatter `requirements:` fields.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`HACK`/`PLACEHOLDER` markers found in any file this phase modified. No stub returns (`return null`/`return {}`/empty-handler patterns) found in the new endpoint or handler code — every new code path performs a real database read/write and every button handler performs a real network call with error handling and a post-write refetch.

### Human Verification (already performed, not re-litigated here)

02-04's `checkpoint:human-verify` task was executed and its verdict recorded verbatim in `02-04-SUMMARY.md`: all five counter journeys (OS contact edit, device credential edit, customer identity edit with all four CPF sub-cases, audit-trail role gating, date immutability) were walked on a live browser session against a real OS (`OS-2026-00250`) as `front-atendente@tecponto.local`/`front-gestor@tecponto.local`, using `window.prompt` stubbing to drive the native-dialog UI (a documented, disclosed technique, not a mock of server behavior). This verification did not need to re-request human sign-off because the SUMMARY's verdict is itself concrete, falsifiable evidence (specific OS name, specific users, a real defect found and the exact root cause) rather than a bare "looks good" claim — and this session independently re-confirmed the underlying code and the automated suite behind it.

### Gaps Summary

No gaps block phase closure. One residual item is worth carrying forward as a WARNING (not a blocker, and already self-disclosed in the 02-02/02-03 SUMMARYs rather than hidden):

**WARNING — no automated regression test exercises the exact cross-operator scenario that caused the real `update_customer` 403 bug.** The `run_edit_audit_checks` EDIT-03 fixture customer is created *as the same attendant* who later edits it (`frappe.set_user(attendant)` before `create_customer`, confirmed by direct read at test_frontend_api.py:3470-3479) — this was a deliberate, documented choice to satisfy Contact-ownership `if_owner=1` for the *fixture's own unrelated setup needs*, but it also means the automated suite structurally cannot reproduce the exact bug pattern (an attendant correcting a customer's Contact they don't own) that the human/browser pass caught. The fix itself (`with as_user("Administrator"):`) was verified three independent ways in this session — direct code read of the diff, a fresh full-suite pass showing no regression, and CI green on the fix commit — so the *fix* is not in question. What's missing is a standing automated tripwire: if a future refactor accidentally removes the `as_user("Administrator")` wrap, the existing automated suite would not catch it because its fixture avoids the exact condition that exposes the bug. This is the same gap the 02-02 SUMMARY separately flagged for the device-credential mutation-test spot-check (also not performed, blocked by the harness's own safety classifier, and also self-disclosed). Recommend a follow-up test (not required to close this phase, since GEMINI.md's own bar — a human walking the real flow — was met) that creates the fixture customer as `Administrator` or a *different* attendant before having a second attendant call `update_customer` on it, asserting success rather than a `PermissionError`.

This does not block the phase: EDIT-03's requirement is "corrected, with audit trail," and that is proven true against the live system by direct code inspection, a fresh independent full-suite run, and CI. The missing piece is defense-in-depth against a *regression* of an already-fixed bug, not evidence that the bug is still present.

---

_Verified: 2026-09-19T03:36:58Z_
_Verifier: Claude (gsd-verifier)_
