---
phase: 03-systematic-audit-pdv-trade-in-warranty-aparelho-usado-caixa
verified: 2026-09-18T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 3: Systematic Audit — PDV → Trade-in → Warranty (Aparelho Usado) → Caixa Verification Report

**Phase Goal:** The rest of day-to-day operation — sales, trade-ins, used-device warranty, cash sessions — survives a real end-to-end transaction without losing money, skipping a required check, or leaking cost/margin data, with the same rigor already proven on the OS cycle.
**Verified:** 2026-09-18
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A real PDV sale combining a part + labor + a deposit is processed once, for the correct total, with the deposit applied exactly once — verified against a live transaction | ✓ VERIFIED | `run_pos_sale_checks` (`test_frontend_api.py:5678`) creates a real Sales Invoice against a real DB (not a mock), asserts exact stock deduction, exact card-fee GL delta, idempotent replay (`replay["idempotent_replay"]`, invoice count unchanged), role gate, and floor-price guard. A separate pre-existing OS billing test (`test_frontend_api.py:~7965-7975`) proves an advance/sinal payment received before `gerar_nota()` is allocated into the generated invoice exactly once (`outstanding_amount < grand_total`) and the remaining balance zeroes out on final payment — together these cover "part + labor + deposit, applied once" end to end. Both are wired into `run_foundation_checks` and exercised on real CI (see below). |
| 2 | Closing a cash session with an undocumented divergence is blocked until a reason is entered; opening a second concurrent session triggers a block instead of opening silently | ✓ VERIFIED | `open_cash_session` (`cash.py:56-64`) hard-blocks a second session at the same `cash_point`/`business_date` (`frappe.throw`, stricter than "warns" — accepted per 03-CONTEXT.md D-02). `run_cash_session_checks` asserts `second_open_blocked: true` (`test_frontend_api.py:7592-7615`). `run_cash_closing_checks` asserts `undocumented_divergence_blocked: true` (line 7867). |
| 3 | Completing a trade-in evaluation without filling the condition checklist is blocked | ✓ VERIFIED | `_validate_checklist_complete` (`tradein/evaluation.py:108`) throws if any checklist row's `result` is blank, called from `validar_avaliacao` (line 43-47) gated by `_is_approval_attempt`. `run_tradein_frontend_checks` asserts `checklist_incomplete_blocked: true` and `checklist_completed_then_approved: true`. React wiring (`getTradeinChecklistTemplate`/`setTradeinChecklistResults`) confirmed present and called in `frontend/src/App.tsx` (lines 7760, 7923) — the create modal and detail modal both collect/edit answers. Additionally confirmed live in the browser on the deployed Coolify site (iPhone 6-row / Android 5-row checklist, incomplete submission blocked). |
| 4 | Querying PDV and trade-in data as Atendente, Gestor, or Técnico never returns cost, margin, or profit fields — confirmed by inspecting the actual API response payload | ✓ VERIFIED | `run_pos_tradein_cost_guard_checks` (`test_frontend_api.py:9205`) payload-inspects 8 previously-unaudited endpoints (`pos_lookup_retail_barcode`, `pos_list_retail_item_groups`, `pos_generate_item_barcode`, `pos_register_retail_product`, `pos_receive_retail_stock`, `list_trade_evaluations`, `get_sale_post_sale_detail`, `list_sales`) under all 3 roles, using **real valuation_rate values** as `forbidden_values` (not just field names), and includes an explicit non-vacuity self-check (`vacuity_probe`) proving the guard can actually fire before trusting a "no leak" result. Zero leaks found across all 3 roles. Read the function body directly — it is a real, substantive test, not a stub. |
| 5 | Claiming warranty on a used device past its calculated expiration date is blocked by the server; a claim within the window succeeds | ✓ VERIFIED | `_apply_used_device_warranty_coverage` (`frontend/api.py:2366`), called unconditionally from `create_service_order_checkin` (line 2314), looks up the device serial via `consultar_garantia_usado(serial_no, reference_date=order.entry_date)` and either links the warranty + zeroes the OS (`used_device_warranty_no_charge = 1`) when `under_warranty`, or leaves the OS as an ordinary charged repair with a recorded reason when expired. `_validate_used_device_warranty_no_charge` (`policies.py:136`) independently re-checks `is_warranty_active` and rejects a no-charge OS with a positive `grand_total` or an inactive/unlinked warranty — this is real double enforcement (check-in AND validate hook), not just a UI-time decision. `run_used_device_warranty_claim_checks` proves all 3 cases (covered/89 days, expired/-1 day, no warranty) plus the priced-save rejection and the sensitive-field guard. `CHECKIN_ALLOWED_ROLES` and `WARRANTY_LOOKUP_ROLES` were confirmed to be the exact same role set (`{System Manager, Tecponto Atendente, Tecponto Gestor}`), so the SUMMARY's claim that the `PermissionError` path can't silently diverge is correct. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tecponto_app/tecponto/frontend/test_frontend_api.py` — `run_foundation_checks` calls all 4 orphaned checks | 4 new calls + return keys | ✓ VERIFIED | `pos_sale_check`, `warranty_mode_check`, `pos_barcode_label_check`, `pos_retail_barcode_catalog_check` all present as local vars (lines 350-369) and in the return dict (lines 435-451) |
| `tecponto_app/tecponto/frontend/test_frontend_api.py` — `run_cash_session_checks` concurrent-session assertion | `second_open_blocked` key | ✓ VERIFIED | Lines 7592-7615 |
| `tecponto_app/tecponto/frontend/test_frontend_api.py` — `run_pos_tradein_cost_guard_checks` | new function, wired | ✓ VERIFIED | Lines 9193-9351+, wired at line 366 |
| `tecponto_app/tecponto/tradein/evaluation.py` — `_validate_checklist_complete` called from `validar_avaliacao` | validate-hook gate | ✓ VERIFIED | Lines 43-47, 108-118 |
| `tecponto_app/tecponto/frontend/api.py` — `get_tradein_checklist_template`/`set_tradein_checklist_results` | whitelisted endpoints | ✓ VERIFIED | Confirmed present and called from React (`balcao.ts`/`App.tsx`) |
| `frontend/src/App.tsx` — checklist collection in create/detail modals | React wiring | ✓ VERIFIED | `getTradeinChecklistTemplate` (line 7923), `setTradeinChecklistResults` (line 7760) |
| `tecponto_app/tecponto/doctype/service_order/service_order.json` — `used_device_warranty`/`used_device_warranty_no_charge` fields | new read-only fields | ✓ VERIFIED (via code reading in `policies.py`/`api.py` which reference these fields consistently; JSON not independently re-read but usage is fully consistent) |
| `tecponto_app/tecponto/service_order/policies.py` — `_validate_used_device_warranty_no_charge` called from `validate_repare_rules` | validate-hook gate | ✓ VERIFIED | Line 17 (call site), 136-148 (body) |
| `tecponto_app/tecponto/frontend/api.py` — `_apply_used_device_warranty_coverage` called from `create_service_order_checkin` | check-in gate | ✓ VERIFIED | Line 2314 (call), 2366-2392 (body) |
| `.planning/WINDOWS.md` — 0 open entries | ledger clean | ✓ VERIFIED | `gsd-tools windows status` → `open_count: 0`, `fixed_count: 2`, both entries independently readable and consistent with 03-05-SUMMARY's account |

### Key Link Verification

| From | To | Via | Status |
|------|-----|-----|--------|
| `run_foundation_checks` return dict | 6 new keys this phase added | direct grep of return dict | ✓ WIRED — all present: `pos_sale`, `pos_barcode_label`, `pos_retail_barcode_catalog`, `warranty_mode`, `pos_tradein_cost_guard`, `used_device_warranty_claim` |
| `create_service_order_checkin` | `consultar_garantia_usado` | serial lookup by `Customer Device.imei_serial` | ✓ WIRED |
| `validate_repare_rules` | `_validate_used_device_warranty_no_charge` | validate hook dispatcher | ✓ WIRED |
| `validar_avaliacao` | `_validate_checklist_complete` | validate hook dispatcher, ordered before `_validate_approved_value_range` per SUMMARY's documented reasoning | ✓ WIRED |
| GitHub Actions `publish-image.yml` | actual phase-3 commits (`312eb9a`, `5b7a65a`, `41cbe82`, `274a18d`, `d59234f`, `554bfe9`, `51087b2`, `786e73e`, `f9d280b`, and the 6 bugfix commits) | `git log`/`git branch --contains` ancestry check | ✓ WIRED — all are ancestors of the green run's head commit `148d5276` |

### CI / Probe Execution

| Check | Command | Result | Status |
|-------|---------|--------|--------|
| GitHub Actions run 35367244684 | `gh run view 35367244684` | 4/4 jobs succeeded: Detect runtime image changes, Fast frontend and Python validation (`npm run build` confirmed in workflow source), Full Frappe integration suite (5m17s), Publish GHCR image | ✓ PASS |
| Commit ancestry | `git log --oneline version-16 -15`, `git branch --contains 41cbe82` | All phase-3 plan commits confirmed ancestors of the green CI head (`148d5276`); the one later commit (`64083f7`) is docs-only (`.planning/STATE.md` + `03-05-SUMMARY.md`), confirmed via `git show --stat` | ✓ PASS |
| WINDOWS.md ledger | `gsd-tools windows status` | `open_count: 0`, `fixed_count: 2`, both entries have `resolved_at` timestamps and match 03-05-SUMMARY's bug-fix account | ✓ PASS |

### Anti-Patterns Found

Scanned all key files touched by this phase (`tradein/evaluation.py`, `frontend/api.py`, `used_device_warranty.py`, `service_order/policies.py`, `cash.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/"not yet implemented" — **zero matches**. No debt markers found.

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| AUDIT-01 | PDV real-transaction sale, deposit applied once | ✓ SATISFIED (code) | See Truth #1 above |
| AUDIT-02 | Caixa divergence + concurrent-session blocks | ✓ SATISFIED (code) | See Truth #2 above |
| AUDIT-03 | Trade-in checklist completion gate | ✓ SATISFIED (code + live human verification) | See Truth #3 above |
| AUDIT-04 | Cost/margin guard across PDV/trade-in | ✓ SATISFIED (code) | See Truth #4 above |
| AUDIT-05 | Used-device-warranty claim enforcement | ✓ SATISFIED (code) | See Truth #5 above |

**⚠️ Bookkeeping discrepancy found (not a functional gap):** `.planning/REQUIREMENTS.md` still shows `[ ]` / "Pending" for **AUDIT-01, AUDIT-02, and AUDIT-04** (only AUDIT-03 and AUDIT-05 are checked `[x]`/"Complete"), despite all five being functionally proven above and all five listed as `requirements-completed` across the phase's own plan SUMMARYs. `.planning/STATE.md` is similarly stale: `status: executing`, `stopped_at: Completed 03-04-PLAN.md` (not 03-05), `completed_phases: 0`, `percent: 0%`. This is a tracking-file gap, not a code gap — the task brief's premise that "all requirements are marked complete in REQUIREMENTS.md" does not hold for the file as it stands and should be corrected (checkbox flips + STATE.md phase-completion fields) before `/gsd-ship`, so the project's own bookkeeping doesn't contradict its own audit trail.

### Human Verification Required

None outstanding for this verification pass — the two counter journeys that changed behavior in this phase (trade-in checklist, used-device-warranty claim) already received human sign-off per 03-05-SUMMARY.md (live browser drive-through on `erp.tecponto.sbs` for the checklist journey; user's own final review, "foi perfeito", covering the deployed site as a whole). This verifier did not re-drive the UI itself but independently confirmed: the CI run that gates this claim actually passed (not just narrated), and the code paths described are real, wired, and non-vacuous.

### Gaps Summary

No functional gaps found. All 5 ROADMAP success criteria for Phase 3 are backed by real, substantive, wired code — not stubs — and by a real, independently-verified green CI run (not just SUMMARY narration). WINDOWS.md is confirmed at 0 open entries.

One non-blocking bookkeeping gap: `.planning/REQUIREMENTS.md` and `.planning/STATE.md` have not been updated to reflect Phase 3's actual completion (see Requirements Coverage section above). Recommend fixing these tracking files before shipping, since they currently understate what has actually been proven.

---

*Verified: 2026-09-18*
*Verifier: Claude (gsd-verifier)*
