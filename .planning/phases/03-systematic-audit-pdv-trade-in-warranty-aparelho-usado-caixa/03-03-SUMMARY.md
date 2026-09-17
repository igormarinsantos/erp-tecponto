---
phase: 03-systematic-audit-pdv-trade-in-warranty-aparelho-usado-caixa
plan: 03
subsystem: trade-in
tags: [frappe, python, react, typescript, trade-in, checklist, validation-gate]

# Dependency graph
requires:
  - phase: 03-02
    provides: cost/margin non-leak baseline on trade-in endpoints (_serialize_trade_evaluation stayed clean while checklist was added to it)
provides:
  - "Device Trade Evaluation approval is blocked in the Python engine (validate hook, both React and Desk entry points) while any condition-checklist row is unanswered"
  - "get_tradein_checklist_template / set_tradein_checklist_results — the read/answer path that makes the gate satisfiable from React"
  - "React trade-in create modal and detail modal both collect/edit checklist answers, sourced only from the server template"
affects: []

# Actuals (#2632)
actuals:
  tokens: 7000
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single source of truth for a child-table's expected rows: checklist_template() in tradein/evaluation.py wraps the existing IPHONE_CHECKLIST/ANDROID_CHECKLIST constants; both the create-time payload and the React modals consume this, never a second hard-coded list"
    - "Write path ships before the gate, in a separate commit: Task 1 (read/write) landed with zero behavior change before Task 2 (the gate) could ever block anything, so no intermediate commit left the trade-in flow unusable"
    - "Approval-attempt scoping (_is_approval_attempt) reused verbatim for a new validator, mirroring _validate_blocked_device, so drafts stay saveable while _sync_checklist pre-populates blank rows"

key-files:
  created: []
  modified:
    - tecponto_app/tecponto/tradein/evaluation.py
    - tecponto_app/tecponto/frontend/api.py
    - tecponto_app/tecponto/frontend/test_frontend_api.py
    - frontend/src/api/types.ts
    - frontend/src/api/balcao.ts
    - frontend/src/api/index.ts
    - frontend/src/App.tsx

key-decisions:
  - "_validate_checklist_complete is called from validar_avaliacao immediately after _validate_blocked_device, BEFORE _validate_approved_value_range — not last. This was required, not optional: the run_action_request_checks over-table-max fixture (line ~5502) sets approved_value=150 against table_max=100 with no device_type-driven checklist rows answered. If the checklist gate ran after the table-max check, the table-max throw would fire first and the checklist gate would never be exercised by that fixture, contradicting the plan's own read_first analysis (which explicitly describes the checklist gate intercepting that call for 'the wrong reason' once it exists). Ordering the gate before the range check makes that failure mode real, which is exactly why the fixture needed its checklist pre-answered and its assertion tightened to check for the table-max wording specifically."
  - "_get_evaluation_checklist runs one extra frappe.get_all query per evaluation inside _serialize_trade_evaluation (used by both list_trade_evaluations and every single-evaluation read). Accepted as the plan's own explicit design (child tables cannot be fetched via frappe.db.get_value) — call volume on this admin-facing panel is low enough that this is not a performance concern."
  - "Extended TradeEvaluationSummary (not just CreateTradeEvaluationPayload) with a required checklist field, and added frontend/src/api/index.ts to the modified-files list beyond the plan's frontmatter. Both were necessary for App.tsx's existing barrel import pattern (`from \"./api\"`) to see the new type, and for the Detalhe da avaliação modal to display/edit the already-populated checklist of an EXISTING evaluation — the plan's own back-compat note requires a UI path to answer pre-existing evaluations' checklists, and the detail modal (where set_tradein_approved_value is already wired) is the natural existing surface for that recovery path, matching the plan's requirement that both getTradeinChecklistTemplate and setTradeinChecklistResults appear as source markers in App.tsx."

patterns-established:
  - "checklist_template(device_type) as the one function every consumer (create endpoint validation, test fixtures, React create modal) calls to get the expected rows — no second copy of IPHONE_CHECKLIST/ANDROID_CHECKLIST anywhere"

requirements-completed: [AUDIT-03]

coverage:
  - id: D1
    description: "Approving a Device Trade Evaluation whose condition checklist still has an unanswered row is rejected by the Python engine"
    requirement: "AUDIT-03"
    verification:
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_tradein_frontend_checks -> checklist_incomplete_blocked: true"
        status: pass
    human_judgment: false
  - id: D2
    description: "The same evaluation, once every row is answered, approves exactly as before — the gate blocks incompleteness, not trade-ins"
    requirement: "AUDIT-03"
    verification:
      - kind: integration
        ref: "bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_tradein_frontend_checks -> checklist_completed_then_approved: true"
        status: pass
    human_judgment: false
  - id: D3
    description: "The counter can answer the checklist through the React trade-in flow without opening Frappe Desk"
    requirement: "AUDIT-03"
    verification:
      - kind: integration
        ref: "npm run build (typecheck + token/font guard) passed; run_tradein_frontend_checks source-marker assertion confirms getTradeinChecklistTemplate and setTradeinChecklistResults are wired in App.tsx"
        status: pass
    human_judgment: false
  - id: D4
    description: "Evaluations created before this change can still be completed, by answering their checklist through the new endpoint"
    requirement: "AUDIT-03"
    verification:
      - kind: integration
        ref: "set_tradein_checklist_results applied to an evaluation whose checklist rows were blank at creation, then set_tradein_approved_value succeeded"
        status: pass
    human_judgment: false
  - id: D5
    description: "Existing fixtures the gate legitimately trips (marketplace listing/reporting inserts, over-table-max request) still pass once repaired"
    requirement: "AUDIT-03"
    verification:
      - kind: integration
        ref: "run_marketplace_listing_checks, run_marketplace_reporting_checks, run_action_request_checks all pass"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-17
status: complete
---

# Phase 3 Plan 03: Trade-in Checklist Completion Gate (AUDIT-03) Summary

**A blank Device Trade Evaluation checklist now blocks approval in the Python engine at the moment of approval attempt; the write path and React wiring that make the gate answerable ship in the same plan, so no trade-in flow was left bricked**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-17
- **Completed:** 2026-09-17
- **Tasks:** 3 / 3
- **Files modified:** 7
- **Commits:** 3

## Task Commits

1. **Task 1 — read/write path:** `d59234f` — `checklist_template()`, `CHECKLIST_RESULT_VALUES`, `get_tradein_checklist_template`, `set_tradein_checklist_results`, `_get_evaluation_checklist`, extended `create_trade_evaluation`. No gate yet; verified `run_tradein_frontend_checks` behavior unchanged.
2. **Task 2 — the gate + fixture repairs (TDD):** `274a18d` — `_validate_checklist_complete` wired into `validar_avaliacao`; 3 fixtures repaired (`run_tradein_frontend_checks`'s `create_evaluation` helper, both marketplace trade-in inserts); the over-table-max assertion in `run_action_request_checks` tightened to check the raised message names the table maximum; AUDIT-03 proof (`checklist_incomplete_blocked`, `checklist_completed_then_approved`) added.
3. **Task 3 — React wiring:** `554bfe9` — `TradeEvaluationChecklistRow` type, `getTradeinChecklistTemplate`/`setTradeinChecklistResults` client methods, checklist collection in the create modal, checklist display/edit in the detail modal (the pre-existing-evaluation recovery path), source-marker assertion pinning both endpoints in App.tsx.

## Verification Results

```
run_tradein_frontend_checks:
{"attendant": "front-atendente@tecponto.local", "buyback_item": "USADO-TP-FRONT-TRADE-SAIDA-BFA7956DE2",
 "operation": "TRIN-2026-0004", "operation_idempotent": true, "below_cost_blocked_for_attendant": true,
 "technician_blocked": true, "leaked_fields": [],
 "checklist_incomplete_blocked": true, "checklist_completed_then_approved": true}

run_marketplace_listing_checks: {"variant": "TPM-CAPA-6A8047E-PT", ..., "attendant_blocked": true, "leaked_fields": []}
run_marketplace_reporting_checks: {"parent_category": "Acessórios", ..., "trade_category": "Aparelhos Usados", "leaked_fields": []}
run_action_request_checks: {"status": "ok", ..., "tradein_over_max": {"request": "TPR-00323", "evaluation": "TROCA-2026-0015", "executed": true}, ...}

npm run build: typecheck passed, vite build succeeded, "Fundação frontend verificada: build, tokens e fonte sem termos sensíveis."
git grep over frontend/src/ for the 6 literal checklist item names (Bateria %, Face ID/Touch ID, iCloud limpo, Tela original,
Chip/eSIM, Conta Google limpa, Estetica A/B/C): NO MATCHES — confirmed no second hard-coded list.
```

## Files Created/Modified
- `tecponto_app/tecponto/tradein/evaluation.py` — `CHECKLIST_RESULT_VALUES`, `checklist_template()`, `_validate_checklist_complete()` called from `validar_avaliacao` right after `_validate_blocked_device`.
- `tecponto_app/tecponto/frontend/api.py` — `get_tradein_checklist_template`, `set_tradein_checklist_results`, `_validate_checklist_payload_entries`, `_get_evaluation_checklist`; `create_trade_evaluation` extended with an optional `checklist` payload key (byte-for-byte identical behavior when omitted); `_serialize_trade_evaluation` now includes a `checklist` key (no cost/margin/valuation field).
- `tecponto_app/tecponto/frontend/test_frontend_api.py` — new imports; `run_tradein_frontend_checks`'s `create_evaluation` helper now pre-answers the checklist; two marketplace fixtures (`run_marketplace_listing_checks`, `run_marketplace_reporting_checks`) pre-answer their inserted trade-in's checklist; `run_action_request_checks`'s over-table-max fixture pre-answers its checklist and its assertion now checks the raised message for the table-max wording; AUDIT-03 proof and source-marker assertion added to `run_tradein_frontend_checks`.
- `frontend/src/api/types.ts` — `TradeEvaluationChecklistRow`; `checklist?` added to `CreateTradeEvaluationPayload`; `checklist` added (required) to `TradeEvaluationSummary`.
- `frontend/src/api/balcao.ts` — `getTradeinChecklistTemplate`, `setTradeinChecklistResults`.
- `frontend/src/api/index.ts` — re-exports `TradeEvaluationChecklistRow` (not in the plan's `files_modified` list; required so App.tsx's existing `from "./api"` barrel import sees the new type — see Deviations).
- `frontend/src/App.tsx` — `TradeEvaluationCreateModal` loads the expected rows on open/device-type change and blocks client-side submit until every row is answered; `TradeEvaluationDetailModal` displays/edits the already-populated checklist of an existing evaluation with a "Salvar checklist" action — the recovery path for pre-existing evaluations.

## Back-Compatibility Note (per plan's explicit instruction)

Device Trade Evaluations that already existed before this plan shipped have blank checklist results (their rows were auto-populated by `_sync_checklist` with `check_item`/`expected_value` only, never `result`). After this plan, **approving one of them now requires answering its checklist first** — through `set_tradein_checklist_results` (wired into the React "Detalhe da avaliação" modal as "Salvar checklist") or directly through the Frappe Desk child-table grid. This is intended behavior, not a regression: it is the whole point of AUDIT-03. Recording it here so it is not re-discovered as a "bug" during pilot rollout when an attendant tries to approve an old, pre-plan evaluation and gets blocked until the checklist is filled in.

## Deviations from Plan

### Auto-fixed / Rule-2 additions

**1. [Rule 2 — missing critical functionality] `frontend/src/api/index.ts` added to modified files, not listed in plan frontmatter**
- **Found during:** Task 3
- **Issue:** App.tsx imports all API types through the `from "./api"` barrel (`index.ts`), not directly from `./api/types`. Adding `TradeEvaluationChecklistRow` to `types.ts` alone would not make it visible to App.tsx.
- **Fix:** Added `TradeEvaluationChecklistRow` to the barrel's re-export list in `index.ts`, matching the existing pattern for every other trade-in type.
- **Files modified:** `frontend/src/api/index.ts`
- **Commit:** `554bfe9`

**2. [Rule 2 — missing critical functionality] `TradeEvaluationSummary` extended with `checklist`, and the "Detalhe da avaliação" modal extended to display/edit it, both beyond the plan's literal read_first line references**
- **Found during:** Task 3
- **Issue:** The plan's acceptance criteria require both `getTradeinChecklistTemplate` and `setTradeinChecklistResults` to appear as source markers in App.tsx, and the plan's own back-compat note explicitly requires pre-existing evaluations to be answerable "through set_tradein_checklist_results ... or the Desk grid" — implying a real UI path for `set_tradein_checklist_results`, not just a client method that nothing calls. The create modal alone only exercises `getTradeinChecklistTemplate` (new evaluations get checklist at creation time); nothing in the plan's create-modal read_first calls the answer/recovery endpoint.
- **Fix:** Added `checklist` to `TradeEvaluationSummary` (the backend serializer already returns it) and wired the existing "Detalhe da avaliação" modal — the surface that already handles `set_tradein_approved_value` for existing evaluations — to display each row with a select and a "Salvar checklist" button calling `setTradeinChecklistResults`. This is the natural, already-existing surface for the plan's own back-compat recovery path.
- **Files modified:** `frontend/src/api/types.ts`, `frontend/src/App.tsx`
- **Commit:** `554bfe9`

### Implementation clarification (not a deviation, documented for future readers)

**Validator ordering in `validar_avaliacao`:** the plan's task 2 acceptance criteria describes `_validate_checklist_complete` as "the fourth" validator call, which could be read as "called last." It is instead called third — immediately after `_validate_blocked_device`, before `_validate_approved_value_range` — making the dispatcher's total line count four, which is what the action text ("as a fourth line, after `_validate_blocked_device(doc)`") literally specifies. This ordering is not a style choice: the plan's own read_first section for the `run_action_request_checks` over-table-max fixture only makes sense (and only requires the fixture repair the plan describes) if the checklist gate fires before the table-max range check would otherwise short-circuit it. Verified empirically — the fixture's tightened assertion (checking the raised message names the table maximum) passes, confirming the checklist gate does not mask the table-max check once both are satisfied together.

## Issues Encountered

Same pre-existing local Docker Desktop/WSL2 flakiness documented in `03-01-SUMMARY.md` and `03-02-SUMMARY.md` — the `tecponto-local-server` container spontaneously exited (`OOMKilled=false`, `ExitCode=255` / `ExitCode=1` after a mid-migration `MySQLdb.OperationalError`) twice during this plan's execution, once after the Task 1 restart and once after the Task 2 restart. Both times resolved by `./scripts/dev-local-server.sh up` and retrying the same verification command with no code changes — consistent with the documented environmental issue, not a defect introduced by this plan.

## Next Phase Readiness

AUDIT-03 is closed. This was the last plan of Phase 3's numbered sequence covering AUDIT-01 through AUDIT-04 (AUDIT-05, the used-device-warranty free-repair-OS feature, is tracked separately per `03-CONTEXT.md`'s D-05 scope note).

## Self-Check: PASSED

All 7 modified source files and this SUMMARY.md confirmed present on disk; all 3 task commits (`d59234f`, `274a18d`, `554bfe9`) confirmed in `git log`.

---
*Phase: 03-systematic-audit-pdv-trade-in-warranty-aparelho-usado-caixa*
*Completed: 2026-09-17*
