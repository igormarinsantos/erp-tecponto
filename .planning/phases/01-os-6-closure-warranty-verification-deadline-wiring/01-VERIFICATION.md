---
phase: 01-os-6-closure-warranty-verification-deadline-wiring
verified: 2026-09-03T00:00:00Z
status: human_needed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open an OS in 'Diagnosticado — aguardando orçamento' with técnico pricing as the Técnico user. Confirm the deadline input arrives disabled with 'Calculando sugestão…', then pre-fills with a future date once the SLA suggestion resolves. Overwrite the date, click 'Salvar prazo', reload the page, and confirm the saved value persisted and was not clobbered by the suggestion."
    expected: "Loading state shows, then pre-fill appears; overriding and saving persists across reload; the Salvar prazo button stays disabled while the field is empty."
    why_human: "Requires a real browser session (visual/interactive confirmation of loading state, pre-fill timing, and reload persistence). No browser automation tool was available to any executor this phase. Backend round-trip (save -> detail read-back -> summary read-back) and the WR-01 button-disable fix are already proven by the live `run_service_order_deadline_checks` execution performed during this verification (see Behavioral Spot-Checks) — this item is a visual/UX confirmation only, not an unproven code path."
  - test: "Open the public tracking link of an OS whose técnico has set a deadline. Confirm the 'Previsão' block shows that date instead of the 'Atualização em breve' fallback. Print the orçamento, orçamento discriminado and laudo técnico from the OS screen and confirm the same date appears on all three under 'Prazo estimado'."
    expected: "Tracking page shows the real date in the Previsão block; all three printed documents show 'Prazo estimado: <date>'."
    why_human: "Requires a real browser session and printed-document visual confirmation. No browser automation tool was available to any executor this phase. The backend/template proof (deadline reaching the guest payload and rendering under the correct label in all three templates) is already proven by the live `run_service_order_deadline_checks` execution performed during this verification (portal_shows_deadline: true, print_shows_deadline: all three true) — this item is a visual/UX confirmation only, not an unproven code path."
  - test: "Open the Kanban board and confirm every card shows a 'Prazo estimado' line — a real date on the OS whose deadline was saved, and 'Não definido' on the others — in the same muted tone as the rows above it, with no layout break on a long customer name. Expand 'Ver mais' on an OS detail overview and confirm the 'Prazo estimado' row shows the same date."
    expected: "Kanban card and OS detail overview both display the correct deadline value, muted color, with CardLine's built-in truncate handling any overflow."
    why_human: "Requires visual confirmation of rendering, color, and truncation behavior in a real browser. No browser automation tool was available to any executor this phase. The wiring (both rows read the correct top-level `estimated_deadline` field, not the unrelated `stage_clock.estimated_deadline` collision) is confirmed by source inspection and pinned by automated source-marker assertions (frontend_source_markers.app_tsx / service_order_kanban_tsx, both true in the live run) — this item is a visual/UX confirmation only, not an unproven code path."
---

# Phase 1: OS.6 Closure — Warranty Verification & Deadline Wiring Verification Report

**Phase Goal:** The OS lifecycle closes correctly — the 90-day warranty boundary is provably enforced, and every OS carries one visible, technician-set delivery deadline.
**Verified:** 2026-09-03
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Sourced from ROADMAP.md Phase 1 Success Criteria (the contract) merged with PLAN frontmatter `must_haves.truths` across all four plans.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Creating an OS, delivering it, and attempting to claim warranty on day 91 is blocked; the same claim on day 89 (and day 90, the inclusive boundary) succeeds — tested against real dates on a live site, not mocked or read from code | ✓ VERIFIED | Live-executed `run_warranty_delivery_checks` on the dev server during this verification (not the SUMMARY's prior run): `boundary_day_89_allowed: true, boundary_day_90_allowed: true, boundary_day_91_blocked: true, status: "ok"`. Boundary lives in `_validate_warranty` (policies.py:131, inclusive `<` comparison); `warranty_expiry` anchored to delivery via `aceites.py`. |
| 2 | The technician can set a single estimated deadline for the OS during the diagnosis/budget step, and it persists after save | ✓ VERIFIED | `set_service_order_estimated_deadline` (api.py:1974) is role-gated (`TECHNICIAN_DEADLINE_ROLES = {"System Manager", "Tecponto Tecnico"}`, api.py:116), stage-gated to `STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO`. Live run: `deadline_saved: "2026-09-08"`, `detail_returns_deadline: true`, `summary_returns_deadline: true`, `attendant_blocked: true`. |
| 3 | The deadline set by the technician appears on the Kanban board, the OS detail view, the public tracking page, and the printed formats (orçamento/laudo) — all four reading the same field | ✓ VERIFIED | Field source-inspected in all four surfaces: `ServiceOrderKanban.tsx:549` (`item.estimated_deadline`), `App.tsx:4486` (`DetailLine label="Prazo estimado" value={detail.estimated_deadline...}`), `tracking.py:154` (`order.get("estimated_deadline")`), `print_formats.py` lines 587/647/709 (`grep -c 'Prazo estimado:'` → 3, all three formats). Live run confirms `portal_shows_deadline: true`, `portal_leak_free: true`, `print_shows_deadline: {orcamento: true, orcamento_discriminado: true, laudo_tecnico: true}`, `print_leak_free: true`. All four read the single top-level `estimated_deadline` field, confirmed distinct from the unrelated `stage_clock.estimated_deadline` naming collision by source inspection. |
| 4 | No second/competing deadline field is introduced — only the existing `estimated_deadline` is wired and used | ✓ VERIFIED | `git diff 046bd4d..HEAD --stat -- '*.json'` shows zero doctype JSON changes (no new field added to Service Order). All backend/frontend code reads/writes the single existing `estimated_deadline` field; `sum_service_business_hours`/`calculate_suggested_delivery` compute a *suggestion*, never a second persisted date. |
| 5 | An Atendente calling the deadline endpoint is rejected by the backend with a permission error, not merely hidden in the UI | ✓ VERIFIED | `_require_technician_deadline_role()` (api.py:291) intersects session roles against `TECHNICIAN_DEADLINE_ROLES` and throws `frappe.PermissionError`. Live run: `attendant_blocked: true`. |
| 6 | Once an OS reaches `workflow_state == "Entregue"`, changing `estimated_deadline` is rejected by the engine with the same message shape already used for `pickup_date`/`warranty_expiry`; before delivery it stays freely editable | ✓ VERIFIED | `_validate_delivery_dates_are_immutable` (policies.py:135-149) widened with `("estimated_deadline", "prazo estimado")` tuple entry, called from both `_validate_warranty` branches (policies.py:94, 123). Live run: `delivered_lock_blocked: true`, `untouched_save_allowed: true`, `editable_before_delivery: true`. |
| 7 | `get_service_order_deadline_suggestion` returns a suggested date computed from configured stage SLAs plus the OS's own service durations, and returns an empty suggestion rather than a fabricated date when there is nothing to compute from | ✓ VERIFIED | `get_service_order_deadline_suggestion` (api.py:2000) calls `stage_sla.sum_service_business_hours` + `calculate_suggested_delivery`, read-only (`doc.check_permission("read")`, no `.save()`). Live run: `suggestion_service_business_hours: 18.0`, `suggestion_total_business_hours: 126.0`, `suggestion_delivery_date: "2026-09-24"`, `empty_suggestion_is_empty: true`, `suggestion_writes_nothing: true`. |
| 8 | A past-dated deadline is rejected by the server (WR-02 fix), and the "Salvar prazo" button cannot be clicked while the field is empty (WR-01 fix) | ✓ VERIFIED | Commit `f39c371` confirmed on HEAD (`git show f39c371`): backend adds `if parsed_deadline < getdate(today()): frappe.throw(...)` (api.py:1986-1987); frontend adds `min={...}` and `disabled={busy || suggesting || !deadline}` (App.tsx:4177, source-inspected). Live run: `past_date_rejected: true`. New `past_date_rejected` assertion confirmed wired into both the test body and the returned dict. |
| 9 | The write path, the suggestion endpoint and the portal/print payload widen no cost/margin/credential leak surface | ✓ VERIFIED | Live run: `sensitive_guard.leaked_fields: []`, `portal_leak_free: true`, `print_leak_free: true` — checked via `contains_sensitive_field` across Atendente/Gestor/Técnico role impersonation and the Guest portal payload. |

**Score:** 9/9 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tecponto_app/tecponto/frontend/api.py` | `TECHNICIAN_DEADLINE_ROLES`, `_require_technician_deadline_role`, `set_service_order_estimated_deadline`, `get_service_order_deadline_suggestion`, allowlist/serializer entries | ✓ VERIFIED | All symbols present, source-inspected at lines 116, 161, 291, 1498, 1974-2016, 4179 |
| `tecponto_app/tecponto/frontend/test_frontend_api.py` | `run_service_order_deadline_checks`, extended `run_warranty_delivery_checks`, wired into `run_foundation_checks` | ✓ VERIFIED | Both functions live-executed successfully during this verification, returning `status: "ok"` with all claimed keys |
| `tecponto_app/tecponto/service_order/policies.py` | `estimated_deadline` entry in `_validate_delivery_dates_are_immutable` | ✓ VERIFIED | Line 147, third tuple entry, source-inspected |
| `tecponto_app/tecponto/service_order/stage_sla.py` | `sum_service_business_hours(rows)` public helper | ✓ VERIFIED | Line 101, source-inspected |
| `tecponto_app/tecponto/service_order/print_formats.py` | "Prazo estimado" line in all 3 print formats incl. laudo técnico | ✓ VERIFIED | `grep -c` reports 3 (lines 587, 647, 709) |
| `frontend/src/api/types.ts` | `estimated_deadline` on `ServiceOrderSummary`/`ServiceOrderDetailResponse`, `ServiceOrderDeadlineSuggestion` interface | ✓ VERIFIED | Lines 426, 440, 513, 476 |
| `frontend/src/api/serviceOrders.ts` | `setEstimatedDeadline`, `deadlineSuggestion` client methods | ✓ VERIFIED | Lines 46, 48-49 |
| `frontend/src/App.tsx` | Deadline input + "Salvar prazo" button, `estimatedDeadline` prop, `DetailLine` "Prazo estimado" row | ✓ VERIFIED | Lines 4012, 4177, 4486; typecheck/build passes clean |
| `frontend/src/ServiceOrderKanban.tsx` | `CardLine` "Prazo estimado" row reading top-level field | ✓ VERIFIED | Line 549, correctly reads `item.estimated_deadline` not `stage_clock.estimated_deadline` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `SAFE_SERVICE_ORDER_FIELDS` allowlist | `_serialize_service_order` / `get_service_order_detail` | DB fetch allowlist entry (line 161) feeds both serializers | ✓ WIRED | Confirmed present; live run shows non-empty `estimated_deadline` in both summary and detail payloads |
| `TechnicalBudgetEditor` (App.tsx) | `serviceOrders.setEstimatedDeadline` | `onClick` handler at line 4177 | ✓ WIRED | Source-confirmed call site; live backend round-trip confirmed |
| `TechnicalBudgetEditor` | `serviceOrders.deadlineSuggestion` | pre-fill `useEffect`/`useCallback` (per SUMMARY, source markers confirm) | ✓ WIRED | `frontend_source_markers.app_tsx: true` in live run |
| `_validate_warranty` (both branches) | `_validate_delivery_dates_are_immutable` | direct call at policies.py:94, 123 | ✓ WIRED | No new call site needed, widened tuple is live the moment `validate` runs — confirmed by live `delivered_lock_blocked: true` |
| `get_service_order_deadline_suggestion` | `stage_sla.calculate_suggested_delivery` | direct call, first production caller | ✓ WIRED | Confirmed by source + live non-trivial suggestion output (`suggestion_total_business_hours: 126.0`) |
| `tracking.py:get_public_portal` | Guest payload | pre-existing serialization, now populated | ✓ WIRED / ✓ FLOWING | Live run: `portal_shows_deadline: true` for a Guest-impersonated call with a real tracking token |
| Kanban `CardLine` | `item.estimated_deadline` (not `stage_clock.estimated_deadline`) | direct read, naming-collision risk explicitly checked | ✓ WIRED | Source-confirmed at line 549; `grep -c` confirms exactly one occurrence |

### Behavioral Spot-Checks

Executed live against the dev server during this verification (not reused from SUMMARY.md claims).

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `run_service_order_deadline_checks` end-to-end (write, read-back, role-gate, validation, immutability lock, suggestion, portal, print, cost-guard, past-date rejection, frontend markers) | `bench --site local-ci.local execute ...run_service_order_deadline_checks` | `{"status": "ok", "deadline_saved": "2026-09-08", ..., "past_date_rejected": true, "sensitive_guard": {"leaked_fields": []}, "delivered_lock_blocked": true, ..., "portal_shows_deadline": true, "print_shows_deadline": {"orcamento": true, "orcamento_discriminado": true, "laudo_tecnico": true}, "frontend_source_markers": {"app_tsx": true, "service_order_kanban_tsx": true}}` | ✓ PASS |
| `run_warranty_delivery_checks` 90-day boundary at days 89/90/91 | `bench --site local-ci.local execute ...run_warranty_delivery_checks` | `{"status": "ok", ..., "boundary_day_89_allowed": true, "boundary_day_90_allowed": true, "boundary_day_91_blocked": true}` | ✓ PASS |
| Frontend build (typecheck + vite build + `verify-foundation.mjs` token/financial-term guard) | `npm --prefix frontend run build` | Exit 0; "Fundação frontend verificada: build, tokens e fonte sem termos sensíveis." | ✓ PASS |
| No debt markers (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) introduced in phase-modified files | `git diff 046bd4d..HEAD -- <8 phase files> \| grep -iE 'TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER'` | No matches (only a legitimate HTML `placeholder=` attribute) | ✓ PASS |
| No Service Order doctype schema change (ROADMAP success criterion 4) | `git diff 046bd4d..HEAD --stat -- '*.json' \| grep -i doctype` | No matches | ✓ PASS |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` convention; verification uses the project's own `bench execute` integration-check pattern instead, run live above.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| WARR-01 | 01-02 | 90-day repair warranty boundary provably enforced at days 89/90/91, live create→deliver→claim | ✓ SATISFIED | Live-executed `run_warranty_delivery_checks`, all three boundary keys `true`. REQUIREMENTS.md marks `[x]` and traceability table shows "Complete" for Phase 1. |
| DEADLINE-01 | 01-01, 01-03, 01-04 | Technician defines the single OS deadline at the budget step; `estimated_deadline` gains a write path | ✓ SATISFIED | Write endpoint role/stage-gated and live-proven; immutability lock live-proven; frontend input live-source-confirmed. REQUIREMENTS.md marks `[x]`, "Complete". |
| DEADLINE-02 | 01-03, 01-04 | Deadline appears on public tracking page and print formats | ✓ SATISFIED | Live run confirms portal + all 3 print formats show the deadline with no leak. REQUIREMENTS.md marks `[x]`, "Complete". |

No orphaned requirements: REQUIREMENTS.md traceability table maps exactly WARR-01, DEADLINE-01, DEADLINE-02 to Phase 1, and all three appear in at least one plan's `requirements:` frontmatter field (01-01: DEADLINE-01; 01-02: WARR-01; 01-03: DEADLINE-01, DEADLINE-02; 01-04: DEADLINE-01, DEADLINE-02).

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers, no empty stub returns, no hardcoded-empty props, and no swallowed-exception anti-patterns beyond the one already noted and accepted in `01-REVIEW.md` (IN-01, a broad `except Exception` in date parsing that correctly converts to `ValidationError` — explicitly assessed as not worth a standalone fix).

### Code Review Fix Verification (01-REVIEW.md)

`01-REVIEW.md` reported `status: fixed`, `fixed_commit: f39c371`, resolving 2 WARNING-level findings (0 critical). Independently verified in this pass:

- **WR-01** (empty-deadline submit not disabled): confirmed fixed — `frontend/src/App.tsx:4177` now reads `disabled={busy || suggesting || !deadline}` (source-inspected, matches the review's prescribed fix exactly).
- **WR-02** (no past-date lower bound): confirmed fixed — `tecponto_app/tecponto/frontend/api.py:1986-1987` now rejects `parsed_deadline < getdate(today())` with `frappe.ValidationError`; frontend input gained `min={new Date().toISOString().slice(0, 10)}`. New `past_date_rejected` assertion confirmed present in `test_frontend_api.py` and confirmed `true` in a live execution during this verification (not merely trusted from the commit message).
- Commit `f39c371` confirmed present on `HEAD`'s ancestry (`git log --oneline -3` shows it two commits back from current HEAD `259e961`), touching exactly the 3 files the commit message and REVIEW.md claim.
- INFO-level findings (IN-01, IN-02) were explicitly left as-is by the review's own "not worth a standalone change" recommendation — consistent, no action expected.

### Human Verification Required

3 items — all UI/browser visual confirmations deferred by every executor this phase per the project's `workflow.human_verify_mode: end-of-phase` setting (confirmed present in `.planning/config.json:32`). None of these represents an unproven backend/wiring code path — every underlying behavior each item covers was independently re-proven live during this verification pass (see Behavioral Spot-Checks above), not merely trusted from SUMMARY.md.

### 1. Técnico deadline pre-fill / override / persist round-trip (01-01 D5, 01-04 D5)

**Test:** As Técnico, open an OS in "Diagnosticado — aguardando orçamento" with técnico pricing. Confirm the deadline input arrives disabled with "Calculando sugestão…", then pre-fills with a future date. Overwrite it, click "Salvar prazo", reload, and confirm the saved value persisted and was not overwritten by the suggestion.
**Expected:** Loading → pre-fill → override → save → reload → persisted value shown; "Salvar prazo" stays disabled while the field is empty.
**Why human:** Requires a real browser session; no browser automation tool was available to any executor this phase. Backend round-trip and the WR-01 disabled-button fix are independently confirmed by this verification's own live `run_service_order_deadline_checks` execution.

### 2. Public tracking portal + print format visual confirmation (01-03 D7)

**Test:** Open the public tracking link of an OS with a saved deadline; confirm the "Previsão" block shows the date. Print the orçamento, orçamento discriminado and laudo técnico and confirm "Prazo estimado" appears on all three.
**Expected:** Real date visible on the tracking page and all three printed documents.
**Why human:** Requires a real browser session and printed-document confirmation. The underlying payload/template proof (`portal_shows_deadline`, `print_shows_deadline` for all three formats) is independently confirmed by this verification's own live execution.

### 3. Kanban card + OS detail overview visual confirmation (01-04 D5, shared with item 1)

**Test:** Open the Kanban board and confirm every card shows "Prazo estimado" (real date or "Não definido"), muted tone, no layout break. Expand "Ver mais" on an OS and confirm the detail row shows the same date.
**Expected:** Correct value, correct muted color, no overflow/layout break.
**Why human:** Requires visual rendering confirmation. The field-read correctness (top-level `estimated_deadline`, not the colliding `stage_clock.estimated_deadline`) is independently confirmed by source inspection and by this verification's live `frontend_source_markers` check.

### Gaps Summary

No gaps. All 9 derived observable truths (ROADMAP Phase 1 success criteria merged with plan-level must-haves) are ✓ VERIFIED against the live codebase — not merely against SUMMARY.md claims. Both automated integration checks (`run_service_order_deadline_checks`, `run_warranty_delivery_checks`) were re-executed live during this verification and returned `status: "ok"` with every claimed key `true`, including the code-review fix commit's new `past_date_rejected` assertion. The frontend build passes clean. No debt markers, no schema drift, no requirement left unmapped.

The only outstanding item is the honestly-declared, project-standard-compliant deferral of 3 browser-only visual confirmations (técnico UI round-trip, tracking portal/print visual check, Kanban/detail visual check) to end-of-phase human UAT — this is a `human_needed` status per this project's verification standard, not a pass-with-caveats and not a fail. Every backend/wiring behavior underlying those 3 items has independent, freshly-executed automated proof from this verification pass.

---

_Verified: 2026-09-03_
_Verifier: Claude (gsd-verifier)_
