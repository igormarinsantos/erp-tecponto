# Roadmap: Tecponto ERP — Stabilization Milestone

## Overview

The system already runs the full OS cycle in production for one pilot store (Rafacel), but three module clusters (PDV, trocas/garantias, caixa) have never been audited with the same real end-to-end rigor already proven on the OS cycle, two OS.6 gaps remain open (warranty boundary proof, deadline wiring), and there is no capability to correct data after an OS is created. This milestone closes all of that, then — and only then — applies a single documented design-system pass and validates a real Coolify deploy for the pilot. The five phases below move in dependency/risk order: cheap, isolated OS.6 closures first; the new audited-edit capability next (highest security surface, built once and reused); the systematic PDV→Trade-in→Warranty→Caixa audit third (dependency-ordered internally, since Caixa aggregates the others); design system fourth (hard-gated behind everything functional, per `CLAUDE.md`); deploy readiness last (validated against the now-stable, now-styled system).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: OS.6 Closure — Warranty Verification & Deadline Wiring** - Prove the 90-day warranty boundary end-to-end and wire the existing `estimated_deadline` field to a real write path and UI
- [ ] **Phase 2: Audited Field-Edit for Post-Creation Corrections** - Let Atendente/Gestor correct contact, device credential, and customer identity on an existing OS, fully audited, without touching immutable delivery/warranty dates
- [ ] **Phase 3: Systematic Audit — PDV → Trade-in → Warranty (Aparelho Usado) → Caixa** - Real end-to-end audit and bugfix of the remaining unaudited modules, in dependency order, including the cost/margin guard extension
- [ ] **Phase 4: Design System (Single Pass)** - Document and apply one consistent design system, hard-gated until everything above is functional and tested
- [ ] **Phase 5: Deploy Readiness — Coolify Pilot** - Validate a real production deploy for Rafacel, including physical printing and QR/barcode scanning

## Phase Details

### Phase 1: OS.6 Closure — Warranty Verification & Deadline Wiring
**Goal**: The OS lifecycle closes correctly — the 90-day warranty boundary is provably enforced, and every OS carries one visible, technician-set delivery deadline.
**Depends on**: Nothing (first phase)
**Requirements**: WARR-01, DEADLINE-01, DEADLINE-02
**Success Criteria** (what must be TRUE):
  1. Creating an OS, delivering it, and attempting to claim warranty on day 91 is blocked; the same claim on day 89 succeeds — tested against real dates on a live site, not mocked or read from code
  2. The technician can set a single estimated deadline for the OS during the diagnosis/budget step, and it persists after save
  3. The deadline set by the technician appears on the Kanban board, the OS detail view, the public tracking page, and the printed formats (orçamento/laudo) — all four reading the same field
  4. No second/competing deadline field is introduced — only the existing `estimated_deadline` is wired and used
**Plans**: 4 plans

Plans:
- [ ] 01-01-PLAN.md — Tracer: técnico deadline write path end to end (endpoint, role gate, serializers, TS contract, budget-screen input)
- [ ] 01-02-PLAN.md — Prove the 90-day warranty boundary live at days 89, 90 and 91
- [ ] 01-03-PLAN.md — Lock the deadline at delivery, add the SLA suggestion endpoint, prove the portal and print surfaces
- [ ] 01-04-PLAN.md — Suggestion pre-fill plus the Kanban card and OS detail overview rows

**UI hint**: yes

### Phase 2: Audited Field-Edit for Post-Creation Corrections
**Goal**: Atendente/Gestor can correct contact, device-credential, and customer-identity data on an already-created OS, with every change tracked, while delivery and warranty dates remain provably untouchable.
**Depends on**: Phase 1
**Requirements**: EDIT-01, EDIT-02, EDIT-03, EDIT-04
**Success Criteria** (what must be TRUE):
  1. Atendente/Gestor edits the OS contact name/phone after creation; the OS detail view shows the new value, and an audit record shows who changed it, when, and the before/after values
  2. The device access credential can be corrected after creation; it remains masked in every view before and after the edit, and the audit record never contains the plaintext value — only that it changed
  3. Customer name/CPF can be corrected after creation, with the same who/when/before/after audit trail
  4. Attempting to alter `pickup_date` or `warranty_expiry` through the edit capability (API or UI, any role) is rejected — these fields remain immutable
  5. Edit audit records cannot be modified or deleted by any role once written — a direct attempt to edit or delete an existing record fails
**Plans**: TBD
**UI hint**: yes

### Phase 3: Systematic Audit — PDV → Trade-in → Warranty (Aparelho Usado) → Caixa
**Goal**: The rest of day-to-day operation — sales, trade-ins, used-device warranty, cash sessions — survives a real end-to-end transaction without losing money, skipping a required check, or leaking cost/margin data, with the same rigor already proven on the OS cycle.
**Depends on**: Phase 2
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05
**Success Criteria** (what must be TRUE):
  1. A real PDV sale combining a part + labor + a deposit is processed once, for the correct total, with the deposit applied exactly once — verified against a live transaction, not a fixture
  2. Closing a cash session with an undocumented divergence is blocked until a reason is entered; opening a second concurrent session triggers a warning instead of opening silently
  3. Completing a trade-in evaluation without filling the condition checklist is blocked
  4. Querying PDV and trade-in data as Atendente, Gestor, or Técnico never returns cost, margin, or profit fields — confirmed by inspecting the actual API response payload, not just the UI
  5. Claiming warranty on a used device past its calculated expiration date is blocked by the server; a claim within the window succeeds
**Plans**: TBD

### Phase 4: Design System (Single Pass)
**Goal**: The application has one documented, consistently-applied visual language, defined and applied only after every phase above is stable and tested — never interleaved with functional work.
**Depends on**: Phase 3 (hard-gated — per `CLAUDE.md`, this phase cannot start until Phases 1-3 are functional and tested)
**Requirements**: DESIGN-01, DESIGN-02
**Success Criteria** (what must be TRUE):
  1. A design system document exists defining colors, typography, and core components, grounded in the actual current UI (not invented from scratch)
  2. Every screen across all four roles reflects the documented design system after one consolidated pass — applied once, not iterated tela-by-tela
  3. The full behavioral test suite (OS, PDV, trade-in, warranty, caixa) still passes after the visual pass, and a live click-through of each journey confirms nothing functional broke
**Plans**: TBD
**UI hint**: yes

### Phase 5: Deploy Readiness — Coolify Pilot
**Goal**: The system runs for real in production on Coolify for the Rafacel pilot, including physical printing and barcode/QR scanning.
**Depends on**: Phase 4
**Requirements**: DEPLOY-01, DEPLOY-02
**Success Criteria** (what must be TRUE):
  1. The application is deployed and reachable on Coolify in the target production environment for the Rafacel pilot
  2. A real OS/PDV document prints correctly on the physical thermal/A4 printer used in-store
  3. A real barcode/QR code, from a printed label or the tracking page, scans and resolves correctly in the real environment
  4. The core day-to-day flow (check-in → PDV/caixa → retirada) runs once end-to-end in the deployed environment without error
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. OS.6 Closure — Warranty Verification & Deadline Wiring | 0/4 | Planned | - |
| 2. Audited Field-Edit for Post-Creation Corrections | 0/TBD | Not started | - |
| 3. Systematic Audit — PDV → Trade-in → Warranty → Caixa | 0/TBD | Not started | - |
| 4. Design System (Single Pass) | 0/TBD | Not started | - |
| 5. Deploy Readiness — Coolify Pilot | 0/TBD | Not started | - |
