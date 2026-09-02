# Project Research Summary

**Project:** Tecponto ERP — stabilization milestone (PDV/trocas/garantia/caixa audit, OS.6 closure, design system, Coolify deploy)
**Domain:** Brownfield Frappe/ERPNext v16 + React 18/Vite/TS ERP for a phone-repair shop (POS + repair ticket + trade-in + warranty + cash register)
**Researched:** 2026-09-02
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is not a greenfield build — it is a stabilization milestone on a working Frappe/ERPNext v16 + React 18 system that already has, for every module in scope, a working doctype/domain layer (PDV via `Tecponto POS Sale Request`, caixa via `Tecponto Cash Session`/`Cash Movement`/`Cash Closing Count`, trade-in via `Trade In Operation`/`Device Trade Evaluation*`, warranty via `Used Device Warranty` + `service_order/policies.py`'s 90-day rule). The prior OS-cycle audit already proved the right method for this kind of work — real end-to-end testing against a live site (not fixtures), found 8+3 real bugs, and left a reusable `run_<area>_checks()` test pattern and an `as_user()` fix for a `frappe.set_user()` session-corruption anti-pattern found at 10 call sites. The research's core conclusion is: apply that exact proven method to the three unaudited modules (PDV, trade-in/warranty, caixa), in dependency order, before touching structure (App.tsx/api.py split) or visuals (design system).

The recommended approach has four structural pillars, all reinforced independently by STACK, ARCHITECTURE, and PITFALLS research: (1) audit precedes and is decoupled from refactor — never restructure code and hunt bugs in the same window; (2) new capabilities (audited field-edit, OS-wide deadline) are added as narrow, explicit modules/allowlists cloned from the proven `Tecponto Access Audit`/`as_user()` patterns, never as generic "patch any field" endpoints; (3) `estimated_deadline` is confirmed via direct grep to already be an OS-level field with a fully-wired read side and zero write path — this is a "finish wiring" task, not a new-field task, correcting an earlier premise; (4) design-system application and Coolify deploy prep are sequenced last/parallel respectively, never ahead of functional stability, per CLAUDE.md's own explicit rule.

The dominant risk category across all four research files is security regression through a new channel that the old guards don't cover — a recurring `frappe.set_user()` reappearance in unaudited modules, a new edit/audit-log endpoint that skips the `contains_sensitive_field()` deny-list, Frappe's native `track_changes`/Version doctype leaking cost or credential data through an unguarded desk/report channel, or the audit log itself storing the plaintext device credential. Every one of these has a known, cheap, already-proven mitigation in this repo (the `as_user()` context manager, a CI grep-gate, routing new endpoints through the existing sanitization function, a purpose-built field-scoped audit doctype) — the risk is not technical difficulty, it's forgetting to apply a known fix to a new surface. Secondary risks are boundary-condition blindness (day-89-vs-91 warranty, caixa reconciliation only tested per-transaction-type) and an unbounded "stabilize everything" scope with no stopping criterion.

## Key Findings

### Recommended Stack

No stack change — Frappe 16/ERPNext v16/React 18/Vite/TS/Tailwind stays as-is. The stack research is entirely about practices to add on top: split the 8,745-line `test_frontend_api.py` by domain before adding more tests; use v16-current `frappe.tests.IntegrationTestCase`/`UnitTestCase` (not the deprecated `FrappeTestCase`) for any new pytest-style tests; add a CI grep-gate blocking `frappe.set_user(` outside `as_user()`/tests; extend the sentinel-value discipline to every new endpoint this milestone adds; keep the `estimated_deadline` field a plain doctype field (not a workflow state); prefer synchronous execution over `frappe.enqueue()` for anything touching cash/financial state, since a silently-timed-out background job on caixa data is a worse failure than a slower request.

**Core technologies:**
- Frappe 16 / ERPNext v16 — confirmed unchanged; PDV/caixa are custom-built on ERPNext primitives (`Sales Invoice`, `Stock Entry`), not ERPNext's own POS Invoice/POS Closing Entry module
- React 18.3.1 / Vite 8.1.3 / TypeScript 5.7.2 / Tailwind — confirmed unchanged, no version work needed
- `as_user()` context manager (`permissions.py`) — the proven, root-caused fix for the `frappe.set_user()` session-corruption anti-pattern; reuse mechanically wherever it recurs

### Expected Features

Framed correctly by FEATURES.md as "what does the industry consider correct/complete behavior for features that already exist" — not a features-to-build list. Cross-referenced against RepairShopr/RepairDesk/RepairQ/MicroBiz/CellStore/XEPOS and Brazilian LGPD guidance on sensitive-data handling.

**Must have (table stakes, mostly already built, needs audit/verification):**
- POS checkout unifying tickets/parts/labor/taxes/deposits/warranties/trade-ins as one flow (audit target: silent deposit drop, double-charge)
- Cash drawer open/close with counted float and forced-reason discrepancy handling (audit target: silent-discrepancy close, concurrent sessions)
- Trade-in intake with condition checklist + IMEI/serial capture, and checklist that actually blocks completion if empty
- Used-device warranty tied to serial+invoice with server-side enforced expiry, not just stored data
- A single, visible, customer-facing promised delivery date per OS (the OS.6 gap — wire up existing `estimated_deadline`)
- Post-creation edit of contact/device-credential/CPF, gated by role, independent of the immutable delivery-date rule
- Full audit trail (who/when/before-after) for PII/credential edits — LGPD treats absence of audit trail as evidence of lack of control, not absence of infraction
- Warranty claim two-branch logic (same defect -> free re-repair; different defect -> new paid order) — already coded in `policies.py`, needs E2E proof
- Device access credential always masked, revealed only via explicit audited action

**Should have (differentiators):**
- OS-wide deadline surfaced on the existing public tracking page + print formats (low-cost extension of infra that already exists)
- Cost/margin guard enforced server-side across every module (PDV/trade-in/garantia/caixa), not just OS — this is the project's most defensible differentiator vs. competitors, who typically expose margin to any staff role with inventory access
- Warranty rework auto-inheriting the original OS's warranty window (already coded, prevents accidental clock-reset)

**Defer (explicitly out of scope per PROJECT.md):**
- Reopening a delivered/closed OS for arbitrary edits (anti-feature — breaks immutability/warranty integrity guarantees)
- Free-text/uncapped warranty override editable by any role (already correctly Gestor-gated via `courtesy_warranty`)
- Per-ticket ad-hoc deadline fields settable by any role (would recreate the exact ambiguity this milestone closes)
- Multi-tenant, fiscal (NF-e/NFS-e), SMTP, billing/trial, PWA, autosave, busca inteligente — all explicit post-piloto/"capitulo produto" deferrals

### Architecture Approach

No architectural layer changes. The system is a clean 4-layer stack (React SPA -> `frontend/api.py` thin dispatcher -> domain modules under `service_order/*`/`tradein/*`/`cash.py` -> Frappe doctypes/MariaDB workflow engine), and every recommendation is "extend this shape," not "add a new layer." The audited field-edit capability clones the already-proven `Tecponto Access Audit`/`user_access.py` pattern (immutable doctype, `validate`/`on_trash` hooks enforcing append-only, sentinel-value credential handling) into a new narrow `post_creation_edit.py` module with a hard-coded field allowlist. `estimated_deadline` needs only a read-allowlist entry, a write path, and a UI control — not new schema. Structural splitting of `App.tsx`/`api.py`/`test_frontend_api.py` must strictly trail each area's audit (never precede it), one area at a time, with "extract module" and "change behavior" kept in separate commits — and any function moved to a new module changes its Frappe RPC dotted-path, requiring a same-commit frontend update.

**Major components:**
1. `frontend/api.py` (thin dispatcher, ~5300 lines) — role check -> domain call -> `SAFE_*_FIELDS` serialization; new capabilities should add thin wrappers here, not inline logic
2. Domain modules (`service_order/*.py`, `tradein/*.py`, `cash.py`, `pos.py`) — actual business authority; new work (post-creation edit, deadline write path) belongs in new small modules following this convention
3. `Tecponto Access Audit` (and the proposed sibling audit doctype) — immutable, append-only, sentinel-value-disciplined audit trail; the reusable pattern for any new "who changed what" requirement
4. `cash.py` — the system's aggregation point; records movements from both PDV sales and OS pickups/payments, which is why caixa must be audited last (its bugs are often upstream PDV/OS bugs surfacing at close-out)

### Critical Pitfalls

1. `frappe.set_user()` anti-pattern reappearing in unaudited modules (PDV/trade-in/caixa) — the OS-only fix pass didn't eliminate the pattern codebase-wide; run a full-repo grep for `frappe.set_user(` and `frappe.session.user =` before/during this audit and add a CI grep-gate so it can't silently reappear in new code either.
2. Frappe's native `track_changes`/Version doctype leaking cost or credential data — do not use it for the new audit-log feature; it captures the entire document diff through a channel the custom `contains_sensitive_field()` guard doesn't cover. Build a purpose-specific, field-scoped audit doctype instead.
3. New edit/audit-log endpoint reusing full-record serialization, or logging the credential's plaintext before/after value — every new endpoint's response must route through the existing sanitization gate, and the credential field must be special-cased in the audit log (log that it changed, never the value) — this is the single highest-risk new surface this milestone introduces.
4. Boundary conditions look right in code review but are unverified in reality — the 90-day warranty rule and caixa reconciliation must be tested at the actual boundary (day 89 vs day 91; mixed cash+card+trade-in+warranty transactions in one register session) using the real date-comparison/reconciliation code path, not a code read or single-transaction-type test.
5. "Stabilize everything" has no built-in stopping criterion — define the specific user journeys that constitute "audited enough" per module before starting, or the audit phase can expand indefinitely.

## Implications for Roadmap

Based on combined research, the ARCHITECTURE.md "Build/Audit Order Summary" is the most concrete, dependency-grounded phase sequence available and should be the roadmap's backbone:

### Phase 1: Warranty 90-day end-to-end verification
**Rationale:** Closes an already-open OS.6 item; no structural risk; cheapest win; the logic already exists in `policies.py` and only needs boundary-condition proof (day 89 pass / day 91 block) using the real date-comparison path, not mocks.
**Delivers:** A live, non-mocked test proving the warranty boundary is correct, extending `run_warranty_mode_checks`.
**Addresses:** FEATURES.md table-stakes "warranty expiry enforced server-side" and "same-defect vs different-defect" items.
**Avoids:** Pitfall 7 (static review confirms logic exists but not that the boundary is correct) and Pitfall 9 (false confidence from existing happy-path test coverage).

### Phase 2: OS-level `estimated_deadline` wiring
**Rationale:** Small, additive, no schema change, no refactor dependency; the field is already fully wired on the read side (`stage_clock.py`, `kanban.py`, `pending.py`, print formats) and only missing a `SAFE_SERVICE_ORDER_FIELDS` entry, a write path, and a UI control.
**Delivers:** Technician-settable OS-wide deadline visible on Kanban, OS detail, tracking page, and print formats.
**Addresses:** FEATURES.md table-stakes "single visible promised date" and differentiator "deadline surfaced on public tracking page."
**Uses:** Existing public tracking infra (`tracking.py`), existing `BUDGET_ALLOWED_ROLES`-style role gating.

### Phase 3: Audited field-edit capability (contact, device credential, CPF)
**Rationale:** Independent of Phase 2; clones the proven `Tecponto Access Audit`/`user_access.py` pattern rather than inventing new infrastructure.
**Delivers:** Three narrow, explicit edit handlers (never a generic patch-any-field endpoint) plus a new immutable, field-scoped audit doctype; credential changes logged as "changed," never with plaintext values.
**Implements:** ARCHITECTURE.md's `post_creation_edit.py` module design, isolated from `budget.py`/`workflow.py`/cost-guard logic.
**Avoids:** Pitfalls 3, 4, 5, 6 (Version-doctype leak, new-endpoint cost leak, credential-in-audit-log, generic-endpoint scope creep) — this phase carries the highest concentration of security-critical pitfalls in the whole milestone and needs sentinel tests written in the same commit as each new endpoint.

### Phase 4: Systematic audit pass — PDV -> Trade-in -> Warranty -> Caixa
**Rationale:** Dependency-ordered, not arbitrary: PDV is self-contained and the origin of cash-movement writes others depend on; trade-in's evaluation/buyback state machine should be validated in isolation before its output is trusted as PDV input; warranty is cheapest to validate next (already partly covered by Phase 1); caixa is the aggregation point and must go last so its discrepancies are diagnosed as genuine caixa bugs, not upstream PDV/OS bugs surfacing at close-out.
**Delivers:** Numbered findings log -> atomic fix commits -> extended/hardened `run_<area>_checks()` per area landed in a split, domain-specific test file, CI green before moving to the next area.
**Addresses:** FEATURES.md's P1 "PDV/trade-in/garantia/caixa E2E audit + bugfix" and the cost/margin guard extension to PDV/trade-in specifically (the project's most defensible differentiator, least audited so far).
**Avoids:** Pitfall 1 (session anti-pattern recurrence), Pitfall 8 (caixa reconciliation bugs invisible to isolated-transaction-type tests — must test a mixed-transaction-type scenario in one register session), Pitfall 10 (unbounded audit scope — define journeys and done-criteria before starting each area).

### Phase 5: Incremental structural split (App.tsx / api.py / test_frontend_api.py)
**Rationale:** Must strictly trail Phase 4's audit, area by area — refactor-then-audit combines two independent risk sources in one window with no regression coverage to prove the move didn't change behavior.
**Delivers:** Test-file split first (lowest risk, rehearses domain boundaries) using the same `test_pos_api.py`/`test_tradein_api.py`/`test_cash_api.py` boundaries as Phase 4; then mechanical, logic-free extraction of each already-audited area from `api.py`/`App.tsx` into domain modules/`*Screen.tsx` files, one commit per area, re-tested immediately after each extraction.
**Uses:** STACK.md's recommendation to route any new capability straight into a small domain module from the start, so the 5300/9500-line files stop growing even before the split begins.

### Phase 6: Design-system application (single pass)
**Rationale:** Hard-blocked by CLAUDE.md section 3 until all functional work above is stable — explicitly sequenced last among app-code phases.
**Delivers:** One consolidated visual pass across the now-stabilized, now-partially-decomposed component tree.
**Avoids:** Pitfall 11 (retrofitting a design system onto a still-monolithic, deeply-nested `App.tsx` is the single riskiest moment in the sequence) and Pitfall 12 (CI-green after a markup refactor proves compilation, not that the UI still works) — this phase needs its own exit gate: re-run the full behavioral suite plus a live click-through of the OS/PDV/warranty/caixa journeys before moving to deploy.

### Phase 7 (parallel-start, finalized last): Deploy readiness — Coolify, print, QR/barcode
**Rationale:** Infra validation (printer drivers, thermal-format, barcode scanner, SSL/DNS, backup/restore) is not logically dependent on app-code stability and cannot be discovered by code audit — sequencing it last-by-default only because it's listed last risks zero schedule buffer before pilot go-live.
**Delivers:** An early lightweight Coolify staging deploy started in parallel with Phase 4/5 to validate infra-only concerns, with the final phase handling only cutover and pilot-specific configuration.
**Avoids:** Pitfall 13 (deploy-readiness treated as the last checkbox instead of a parallel track).

### Phase Ordering Rationale

- Phases 1-3 have no ordering dependency on each other and could in principle be parallelized, but are listed in ascending risk/cost order (cheapest, most isolated wins first) per ARCHITECTURE.md's explicit "Build/Audit Order Summary."
- Phase 4 has an internal dependency order grounded in actual data flow (PDV -> Trade-in -> Warranty -> Caixa), not an arbitrary list order — caixa is the shared aggregation point downstream of the other three.
- Phase 5 must strictly trail Phase 4's per-area audits — this is the load-bearing anti-pattern-avoidance decision in the entire roadmap (refactor-then-audit is explicitly flagged as a failure mode this milestone exists to stop).
- Phase 6 is hard-gated behind Phases 1-5 by the project's own CLAUDE.md rule, not by this research — the research adds the how (verification gate), not the whether.
- Phase 7's validation should start early/parallel (per Pitfall 13) even though its cutover is necessarily last — this is a scheduling nuance the roadmap should preserve rather than flattening into a single late phase.

### Research Flags

Phases likely needing deeper research during planning:
- Phase 3 (audited field-edit): needs a discuss-phase decision on whether edits should be blocked once OS reaches `Entregue`, or always allowed-but-audited — architecturally cheap either way, but explicitly flagged in ARCHITECTURE.md as an open product question, not a technical constraint to pre-decide.
- Phase 4 (caixa sub-area): the mixed-transaction-type reconciliation test scenario needs to be designed against this app's actual custom `cash.py` logic (not ERPNext's POS module, which doesn't apply) — worth a focused look at `cash.py`'s current bucket-handling before writing the test.
- Phase 5 (App.tsx/api.py split): the RPC dotted-path risk when moving functions between modules needs verification against the actual `frontend/src/api/*.ts` call sites for each function moved — a full-repo grep pass at the start of this phase, not assumed research knowledge.

Phases with standard patterns (skip research-phase):
- Phase 1 (warranty verification): logic already exists, method already proven (OS audit's own timezone-bug precedent gives a clear test template).
- Phase 2 (deadline wiring): architecture research already fully traced the read/write data flow and confirmed no schema change is needed.
- Phase 6 (design system): CLAUDE.md already defines the process (single pass, structure-before-cosmetics); pitfalls research supplies the verification gate.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | HIGH where grounded in this repo's own code (`as_user()` docstring, grep audits of `workflow_state` writes and PDV/caixa doctypes) or official Frappe v16 migration wiki; MEDIUM where sourced from community forum/GitHub-issue precedent (background-job soft caps, multi-role-per-state workflow bug) |
| Features | MEDIUM-HIGH | Cross-referenced against multiple repair-vertical POS vendors (RepairShopr, RepairDesk, RepairQ, MicroBiz) and LGPD legal-compliance sources, but no hands-on access to competitor admin panels — UX specifics inferred from public docs/marketing, not verified first-hand; codebase-grounded claims (existing doctypes, `policies.py` logic) are HIGH |
| Architecture | HIGH | All findings verified directly against actual repository source this session, including a direct grep correction of an earlier premise about `estimated_deadline` |
| Pitfalls | MEDIUM-HIGH | Grounded directly in this repo's own audit evidence (`CONCERNS.md`, `PROJECT.md`, the documented `set_user()` fix); the specific `set_user()` session/cookie-corruption failure mode itself was not independently corroborated by a third-party source and rests on this repo's own fixed-and-documented bug — flagged transparently in PITFALLS.md rather than presented as externally verified |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- Whether Service Order's Workflow doctype has any state with more than one role permitted to edit (a known longstanding Frappe bug where only the first-configured role actually gets edit rights) has not been empirically checked against this repo's specific config — flag for direct verification early in Phase 3 or 4.
- The exact business rule for CPF/contact editability across different OS workflow states (can CPF be corrected after pickup?) is not yet decided — surface explicitly as a Phase 3 acceptance-criteria question, not an assumption.
- Whether product wants per-service-line deadline granularity in addition to the OS-wide deadline (distinct from the OS-wide field) was raised but not resolved in ARCHITECTURE.md — recommend surfacing directly to the user during Phase 2 discuss-phase rather than assuming either interpretation.
- `pos.py`/`cash.py` have not yet been grepped for unbounded `get_all()` calls (missing `limit_page_length`) — extrapolated as likely from a documented sibling-module pattern in `api.py`, not yet confirmed; should be part of Phase 4's audit checklist.

## Sources

### Primary (HIGH confidence)
- This repository — `tecponto_app/tecponto/permissions.py`, `user_access.py`, `doctype/tecponto_access_audit/tecponto_access_audit.json`, `hooks.py`, `doctype/service_order/service_order.json`, `service_order/stage_clock.py`/`kanban.py`/`pending.py`/`print_formats.py`, `frontend/api.py`, `frontend/test_frontend_api.py` — direct code inspection this session
- `.planning/codebase/ARCHITECTURE.md`, `STRUCTURE.md`, `CONCERNS.md`, `TESTING.md` — prior codebase-mapping session, treated as ground truth
- `.planning/PROJECT.md` — milestone scope and prior key decisions
- Frappe/frappe GitHub wiki, "Migrating to version 16": https://github.com/frappe/frappe/wiki/Migrating-to-version-16

### Secondary (MEDIUM confidence)
- Frappe official docs, Background Jobs: https://docs.frappe.io/framework/user/en/api/background_jobs
- Frappe Framework testing docs: https://docs.frappe.io/framework/user/en/testing
- Frappe Document Versioning / Track Changes docs: https://docs.frappe.io/erpnext/user/manual/en/document-versioning, https://frappe.io/blog/erpnext-features/versioning-and-audit-trail
- `frappe/erpnext` GitHub issues #7582, #16616 (POS cash reconciliation precedent, not a direct dependency)
- `frappe/frappe` GitHub issues on Workflow multi-role-per-state permission bug
- Frappe community forum, "Set temporary frappe.session.user": https://discuss.frappe.io/t/set-temporary-frappe-session-user/105420
- RepairShopr/RepairDesk/RepairQ/MicroBiz/CellStore/XEPOS vendor docs and comparison pages (see FEATURES.md for full list)
- LGPD-focused legal/compliance sources on sensitive-data handling (lgpdbrasil.com.br, Barbieri Advogados)

### Tertiary (LOW confidence)
- General brownfield-modernization sequencing risk source (solguruz.com) — generic industry source, used only to corroborate the general stabilize-then-redesign-then-deploy sequencing pattern, not any project-specific claim

---
*Research completed: 2026-09-02*
*Ready for roadmap: yes*
