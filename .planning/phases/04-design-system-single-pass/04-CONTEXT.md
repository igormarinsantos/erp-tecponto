# Phase 4: Design System (Single Pass) - Context

**Gathered:** 2026-09-19
**Status:** Ready for planning

<domain>
## Phase Boundary

The application gets one documented, consistently-applied visual language, defined and applied only after Phases 1–3 are functional and tested (hard gate, already satisfied). Covers: formalizing the design system as documentation (DESIGN-01), applying it in a single consolidated pass across all four roles' screens (DESIGN-02), the carried-forward check-in wizard restructuring, and an OS-vs-PDV visual consistency check. Does NOT touch functional logic, backend behavior, or any of the 6 OS lifecycle locks — this phase is presentation-layer only, per `CLAUDE.md` §3.

</domain>

<decisions>
## Implementation Decisions

### Scope of the "single pass" (DESIGN-02)
- **D-01:** This is a documentation-and-polish pass, not a redesign. Scouting found the codebase is NOT greenfield here: `frontend/src/styles/tokens.css` already defines a complete token system (colors, fonts, radii, dark/light theme variants), `tailwind.config.ts` is already wired to those tokens, and `frontend/src/ui/` already has a real shared component library (`Button`, `Card`, `Modal`, `BadgeStatus`, `DataTable`, `Toast`, `Topbar`, `Sidebar`, `StatBar`, `ContextMenu`, `ListControls`, `HorizontalScroller`). A codebase-wide grep found only 2 instances of raw Tailwind gray/slate classes outside the token system in ~11,000 lines of screen code (`src/ui/BadgeStatus.tsx:bg-slate-400`, `src/CheckinWizard.tsx:bg-zinc-300`) against 2,875 uses of `tec-*` token classes — i.e., token consistency is already ~99%+.
- **D-02:** Concretely, this phase: (a) writes the formal design-system document grounded in what already exists (D-04 below), (b) fixes the 2 known drift instances, (c) does a light visual consistency pass screen-by-screen for spacing and typographic hierarchy (not a spacing-scale or shadow-system overhaul), (d) executes the check-in wizard restructuring and OS-vs-PDV check below. It explicitly does NOT redesign component variants, does NOT introduce a new spacing scale, and does NOT touch `App.tsx`'s size/structure (splitting it is `TECH-03`, an explicitly deferred v2 requirement in `REQUIREMENTS.md`, unrelated to visual design).

### Check-in wizard "Dados" step restructuring (carried forward from Phase 1 feedback)
- **D-03:** Split the wizard's "Dados" step into 3 sub-steps, growing the wizard from 5 to 7 steps total: **Cliente → Aparelho → Defeito → Estado físico → Acessórios → Fotos → Revisão**.
  - **Defeito**: `reported_defect` (relato do cliente/defeito), `entry_operating_condition` (condição de funcionamento), and the prior-repair-suggestion card (same-defect detection against `candidate.reported_defect`) — these are currently co-located around `CheckinWizard.tsx` lines ~1780–1910.
  - **Estado físico**: the `physicalStates` checklist (feeds `physical_state`).
  - **Acessórios**: the `accessories` checklist (feeds `accessories_received`) plus `attendance_notes`.
  - The `steps` array at `CheckinWizard.tsx:62` (`["Cliente", "Aparelho", "Dados", "Fotos", "Revisão"]`) is the concrete artifact to change. Validation gating (`dataReady`, currently requiring `reported_defect` + at least one `physicalStates` entry + `physical_state`) must be redistributed per sub-step rather than checked once at a single "Dados" gate.
  - This is purely a presentation/step-grouping change — the underlying payload fields, validation rules, and submit behavior stay identical.

### OS-vs-PDV visual consistency
- **D-05:** Compare OS screens (`App.tsx`, `ServiceOrderFlows.tsx`, `ServiceOrderKanban.tsx`) against PDV screens (`PosScreen.tsx` and related) and align visual presentation — colors, spacing, which `src/ui/*` components are used — wherever they diverge for equivalent UI patterns (e.g., a customer-info card, a status badge, an action button row).
- **D-06:** Visual-only. No flow/logic changes to either OS or PDV are in scope from this comparison — if a divergence is actually a functional inconsistency (not just visual), flag it under Deferred Ideas rather than fixing it here.

### Design system documentation format (DESIGN-01)
- **D-04:** A markdown file in the repository (e.g., `frontend/DESIGN_SYSTEM.md` or `docs/DESIGN_SYSTEM.md` — planner's discretion on exact path) documenting: the token system in `tokens.css` (color roles, typography, radii, spacing constants, dark/light theme variants) and the `src/ui/*` component library, each with a usage example pulled from real call sites already in the codebase. This is documentation of what exists, not a spec for what should be built — reflects D-01's "grounded in the actual current UI (not invented from scratch)" success criterion verbatim.

### Claude's Discretion
- Exact file path/name for the design-system markdown document.
- Exact wording/structure of the document beyond the two required sections (tokens, components).
- Whether `scripts/verify-foundation.mjs` gets a new guard for raw Tailwind gray/slate class usage (it currently only guards token *presence* and cost/margin leak terms, not token *consistency*) — a reasonable candidate to prevent the 2 known drift instances from recurring, but not required by any of the locked decisions above.
- Exact spacing/typography adjustments made during the "light visual consistency pass" — no specific pixel values or scale were locked; use judgment grounded in the existing token system, not a new one.

</decisions>

<specifics>
## Specific Ideas

No specific visual references given beyond what already exists in the codebase — the explicit instruction is to document and polish the current system, not introduce a new visual direction.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design system foundation (already exists — read before writing anything new)
- `frontend/src/styles/tokens.css` — the complete existing token system (colors as `--tp-*` CSS custom properties, fonts, radii, dark/light theme variants via `:root[data-tecponto-theme]`)
- `frontend/tailwind.config.ts` — how tokens are wired into Tailwind's `tec.*` color namespace, `borderRadius`, `fontFamily`, `boxShadow`
- `frontend/src/ui/` (whole directory) — the existing shared component library: `Button.tsx`, `Card.tsx`, `Modal.tsx`, `BadgeStatus.tsx`, `DataTable.tsx`, `Toast.tsx`, `Topbar.tsx`, `Sidebar.tsx`, `StatBar.tsx`, `ContextMenu.tsx`, `ListControls.tsx`, `HorizontalScroller.tsx`, `WhatsAppLogo.tsx`, `statBarVisuals.tsx`, `utils.ts`, `index.ts`
- `frontend/scripts/verify-foundation.mjs` — existing CI-enforced guard; checks token *presence* (`requiredTokens` list) and forbidden cost/margin terms leaking to frontend; does NOT currently check token-usage *consistency*

### Requirements and scope
- `.planning/REQUIREMENTS.md` — DESIGN-01, DESIGN-02 wording; also confirms `TECH-03` (splitting `App.tsx`/`api.py`) is an explicitly deferred v2 requirement, not part of this phase
- `.planning/ROADMAP.md` §"Phase 4: Design System (Single Pass)" — phase goal, success criteria, and the carried-forward Phase 1 feedback block (check-in wizard density, OS-vs-PDV consistency question) that this discuss-phase resolved
- `CLAUDE.md` §3 — design guidelines: reason about hierarchy before building, cosmetic polish only in this single consolidated pass, never tela-by-tela during functional phases (already honored — this phase exists because of that rule)

### Check-in wizard restructuring target
- `frontend/src/CheckinWizard.tsx` — `steps` array (line 62), the "Dados" step's current field grouping (`reported_defect`, `entry_operating_condition`, `physicalStates`/`physical_state`, `accessories`/`accessories_received`, `attendance_notes`), and the `dataReady` validation gate

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tokens.css` + `tailwind.config.ts`: the entire palette/typography/radius system to document, not redesign.
- `src/ui/*`: the entire shared component library to document, not rebuild.
- `scripts/verify-foundation.mjs`: existing enforcement pattern (throws on missing token, throws on forbidden term) — the natural place to add a consistency guard if the planner decides one is worth it (Claude's Discretion above).

### Established Patterns
- Token-first styling via `tec-*` Tailwind classes backed by `--tp-*` CSS custom properties is already the dominant, near-universal pattern (2,875 uses vs. 2 stray raw-color instances) — the design system to document already exists in practice, just not in writing.
- Foundation guard convention (`verify-foundation.mjs` throws with a clear Portuguese error message per violation) is the established style for any new automated consistency check.

### Integration Points
- The check-in wizard step-count change touches `CheckinWizard.tsx`'s `steps` array and whatever step-index logic reads it (progress indicator, next/back button gating, the `dataReady` validation gate) — all in the same file.
- OS-vs-PDV comparison touches `App.tsx`/`ServiceOrderFlows.tsx`/`ServiceOrderKanban.tsx` on one side and `PosScreen.tsx` on the other — no shared file to modify centrally; changes will be scattered per-screen, restyling to reuse existing `src/ui/*` components/tokens rather than introducing new ones.

</code_context>

<deferred>
## Deferred Ideas

- Splitting `App.tsx` (~9,700 lines) or `api.py` (~5,300 lines) — this is `TECH-03`, an explicitly deferred v2 requirement in `REQUIREMENTS.md`, unrelated to visual design and out of scope here.
- A new spacing scale, shadow/elevation system, or component-variant redesign — scouting found the existing system doesn't need this; if the visual consistency pass surfaces a genuine gap here, defer it rather than scope-creep into a redesign.
- Any OS-vs-PDV divergence that turns out to be *functional* (not visual) — e.g., different validation rules or different data shown for the same concept — gets flagged here for a future phase, not fixed during this visual-only comparison.
- Structural/component consolidation between OS and PDV (e.g., merging a duplicated customer-info card into one shared component) — user explicitly chose visual-only alignment for this phase; consolidation was the rejected "sim, visual e estrutural" option.

</deferred>

---

*Phase: 04-design-system-single-pass*
*Context gathered: 2026-09-19*
