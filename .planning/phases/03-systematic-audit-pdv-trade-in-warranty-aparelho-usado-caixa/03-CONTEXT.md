# Phase 3: Systematic Audit — PDV → Trade-in → Warranty (Aparelho Usado) → Caixa - Context

**Gathered:** 2026-09-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Real end-to-end audit and bugfix of the remaining unaudited modules (PDV, trade-in, used-device warranty, caixa), mirroring the rigor already proven on the OS cycle audit and Phase 1. Covers AUDIT-01 through AUDIT-05. Unlike Phase 1, most of this phase's work is discovering and closing gaps in an already-substantial codebase rather than wiring one net-new field — with one genuine exception (D-05, a real missing feature).

</domain>

<decisions>
## Implementation Decisions

### Priority and sequencing
- **D-01:** Wire the 4 already-passing, already-complete, but never-called test functions into `run_foundation_checks` FIRST, before any new test-writing: `run_pos_sale_checks`, `run_warranty_mode_checks`, `run_pos_barcode_label_checks`, `run_pos_retail_barcode_catalog_checks` (all in `tecponto_app/tecponto/frontend/test_frontend_api.py`). Confirmed via live standalone execution this session — all four return `status: "ok"` against the current codebase. This closes the single largest CI blind spot at near-zero risk before any other work in this phase. — **Reversibility:** reversible — adding a function call to the suite, trivially removable.

### AUDIT-01 (PDV)
- Satisfied primarily by D-01 (wiring `run_pos_sale_checks`, `run_pos_barcode_label_checks`, `run_pos_retail_barcode_catalog_checks`) plus `run_warranty_mode_checks` for the repair-warranty-mode PDV interaction. These already prove: stock deduction (commercial vs repair warehouse), card-fee/clearing-account posting, idempotent replay (no duplicate invoice/stock/GL), receipt PDF generation, cost/margin non-leak, and role gates (Técnico blocked from finalizing PDV sales). No new test-writing expected for AUDIT-01 unless wiring surfaces a real failure.

### AUDIT-02 (Caixa)
- **D-02:** The "closing with undocumented divergence is rejected" behavior is already implemented and tested (`run_cash_closing_checks`, already wired — assertion "Fechamento com divergência foi aceito sem motivo"). The "concurrent session" half of AUDIT-02 is already enforced in code — `tecponto_app/tecponto/cash.py:56-64`, `open_cash_session()` hard-blocks (`frappe.throw`) a second session at the same `cash_point`/`business_date` with `"Já existe um caixa aberto no ponto {0}."` — stricter than the original "warns" wording, which is acceptable (a hard block is safer than a warning-but-allow). **Action needed:** add one new test assertion (extending `run_cash_session_checks`, per the established extend-don't-duplicate pattern from Phase 1's D-01) proving this existing block actually fires — no production code change expected here, just closing a test-coverage gap on already-correct behavior.

### AUDIT-03 (Trocas / checklist)
- **Confirmed genuine gap:** zero occurrences of "checklist" anywhere in the Python codebase or test suite (verified by grep). The `Device Trade Evaluation Checklist` doctype exists but nothing today validates it's filled before a `Device Trade Evaluation` or `Trade-In Operation` can complete. The planner/executor must first investigate the actual current data model (does the checklist child table even get populated by the existing UI today? what does "conclusão" mean operationally — evaluation approval, or the trade-in operation itself?) before designing the validation gate — this was not fully resolved during discussion and is explicitly handed to planning/research, not assumed here.

### AUDIT-04 (Cost/margin guard)
- Partial existing coverage: `_check_pos_item_cost_guard` (wired in `run_foundation_checks`) plus `contains_sensitive_field` assertions already present inside the orphaned PDV/warranty-mode tests being wired in D-01. Task for this phase: confirm this guard genuinely covers every new/recently-touched PDV and trade-in response surface (not just the ones already checked) — audit for gaps, don't assume full coverage just because *a* cost guard exists.

### AUDIT-05 (Garantia de aparelho usado) — genuine new feature, not just a test gap
- **D-03 (real-world flow, confirmed by user):** Quando um aparelho usado vendido sob garantia volta com defeito, o balcão hoje abre uma OS de reparo **manualmente marcada para não cobrar valor** (controle interno, sem cobrança) — um processo inteiramente manual hoje, sem nenhuma verificação automática. Troca do aparelho é uma resolução alternativa, mas rara ("raro raro raro dificilmente") — **fora do escopo de automação desta fase**, só não pode ficar quebrada pelo que for construído aqui.
- **D-04 (confirmed):** quando a `Used Device Warranty` do aparelho **já venceu**, o reparo volta a ser uma OS normal, cobrada — mesmo padrão já usado na garantia de reparo (`is_same_warranty_defect` / defeito diferente vira OS normal com desconto, `policies.py`). Reusar esse precedente conceitual, não inventar um terceiro padrão de garantia.
- **Confirmed via grep:** zero references to `Used Device Warranty`/`used_device_warranty` anywhere in `frontend/api.py` or `service_order/*.py` — hoje não existe NENHUMA ligação entre a garantia de aparelho usado e a criação/orçamento de uma Service Order. Este é trabalho de feature nova (linkar `Used Device Warranty` por serial/IMEI no check-in, e zerar automaticamente o orçamento quando coberto), não apenas fechamento de lacuna de teste — **flagar isso ao usuário no início do planning como uma extensão de escopo real, não escondê-la dentro de "auditoria"**.
- `consultar_garantia_usado()` (`used_device_warranty.py:55`) já calcula `under_warranty` corretamente — reusar essa função como a fonte de verdade do gate, não recalcular a lógica de expiração em outro lugar.

### Claude's Discretion
Nenhuma — todas as decisões relevantes foram fechadas com o usuário nesta discussão, incluindo o comportamento de garantia vencida (D-04) e a priorização (D-01).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### PDV (AUDIT-01) — orphaned tests to wire
- `tecponto_app/tecponto/frontend/test_frontend_api.py:5650` (`run_pos_sale_checks`), `:2369` (`run_warranty_mode_checks`), `:5820` (`run_pos_barcode_label_checks`), `:5935` (`run_pos_retail_barcode_catalog_checks`) — all confirmed passing standalone this session; `run_foundation_checks` (around line ~316-370) is where each `run_*_checks()` call needs to be added, following the exact pattern of neighboring calls like `cashier_mode_checks = run_cashier_mode_checks()`.

### Caixa (AUDIT-02)
- `tecponto_app/tecponto/cash.py:31-64` (`open_cash_session`, the existing concurrent-session hard block)
- `tecponto_app/tecponto/frontend/test_frontend_api.py:7415` (`run_cash_session_checks`, already wired — extend this, per Phase 1's D-01 precedent, rather than writing a new function)
- `tecponto_app/tecponto/frontend/test_frontend_api.py:7652` (`run_cash_closing_checks`, already wired, already tests divergence-blocking)

### Trocas (AUDIT-03)
- `tecponto_app/tecponto/doctype/device_trade_evaluation/device_trade_evaluation.json`, `tecponto_app/tecponto/doctype/device_trade_evaluation_checklist/device_trade_evaluation_checklist.json` — the doctypes involved; planner must read these directly, no existing Python logic references them by name yet
- `tecponto_app/tecponto/frontend/test_frontend_api.py:6820` (`run_tradein_frontend_checks`, already wired but does not test checklist completeness — extend it once the gate exists)

### Garantia de usado (AUDIT-05)
- `tecponto_app/tecponto/used_device_warranty.py` — `consultar_garantia_usado()` (line 55, the expiration-check source of truth to reuse), `_upsert_warranty()` (line 101, where `warranty_expiry` is computed on sale)
- `tecponto_app/tecponto/service_order/policies.py` — `_validate_warranty`, `is_same_warranty_defect` (the analogous repair-warranty pattern to mirror conceptually for "expired → normal charged OS", NOT to directly reuse code from, since these operate on `Service Order.original_service_order`, a different relationship than a `Used Device Warranty` record)
- `tecponto_app/tecponto/frontend/api.py` — `create_service_order_checkin` (where the new Used Device Warranty lookup-and-zero-budget logic would need to hook in, likely near where `is_warranty`/`original_service_order` are currently set)
- `tecponto_app/tecponto/frontend/test_frontend_api.py:8523` (`run_used_device_warranty_lookup_checks`, already wired but only tests lookup/display, not claim-time enforcement — this phase adds the enforcement test, likely as a new function given the different trigger point, unlike the other AUDIT items which extend existing functions)

### Data model reference (verified this session)
- Full doctype Link-field relationship graph and a live referential-integrity check (13 relations, 0 orphaned records) — see `STATUS_PROJETO.md` "Mapa de Dados" section (Windows planning folder) for the complete verified graph and doctype role descriptions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- 4 orphaned-but-complete PDV/warranty-mode test functions (D-01) — production-quality, just need one line each in `run_foundation_checks`
- `consultar_garantia_usado()` — ready-made expiration check, reuse rather than reimplement
- The repair-warranty "different defect → normal charged OS" pattern (`policies.py`) — conceptual precedent for AUDIT-05's expired-warranty behavior, not directly reusable code (different relationship model)

### Established Patterns
- Every existing `run_*_checks()` function follows: `frappe.set_user`/impersonation → `ensure_frontend_foundation()` → create fixtures → assert observable behavior → `contains_sensitive_field` guard → role-gate check → return a status dict. New tests this phase should match this shape for consistency.
- Extend-don't-duplicate: Phase 1 established the pattern of adding assertions to an existing `run_*_checks()` function rather than writing a parallel one when the domain already has live CI coverage (D-01 in Phase 1's CONTEXT.md, reused here for D-02/D-03).

### Integration Points
- `create_service_order_checkin` (`api.py`) is almost certainly where the new Used Device Warranty → free-repair-OS logic attaches, given it's the single check-in entry point and already has an `is_warranty`/`original_service_order` branch to extend conceptually alongside.
- The checklist-completion gate (AUDIT-03) likely belongs in a `validate` hook on `Device Trade Evaluation` or `Trade-In Operation`, mirroring how `Service Order`'s `validate_repare_rules` hook works — exact attachment point is planning/research work, not decided here.

</code_context>

<specifics>
## Specific Ideas

Nenhuma referência visual ou de exemplo específico foi dada nesta discussão além do fluxo operacional descrito em D-03/D-04.

</specifics>

<deferred>
## Deferred Ideas

- **Troca de aparelho como resolução de garantia de usado** — mencionada pelo usuário como existente mas muito rara ("raro raro raro dificilmente"). Não entra no escopo de automação/teste desta fase; qualquer gate construído para D-03/D-04 não deve quebrar esse caminho manual raro, mas também não precisa testá-lo formalmente agora.

### Reviewed Todos (not folded)
Nenhum.

</deferred>

---

*Phase: 3-systematic-audit-pdv-trade-in-warranty-aparelho-usado-caixa*
*Context gathered: 2026-09-14*
