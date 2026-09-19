# Phase 4: Design System (Single Pass) - Pattern Map

**Mapped:** 2026-09-19
**Files analyzed:** 6 (2 modified for token drift, 1 restructured wizard, 2 optional drift extensions, 1 new doc)
**Analogs found:** 5 / 6 (the new doc file has no analog — it's original content by nature)

**Verification note:** all line numbers below were re-read from the actual files on disk during this
pass (not copied blindly from `04-UI-SPEC.md`). Two discrepancies vs. the UI-SPEC were found and are
called out inline.

---

## File Classification

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|-----------------|---------------|
| `frontend/src/ui/BadgeStatus.tsx` | component (shared UI) | transform (status string → token class) | itself — other entries in its own `toneClasses` map (lines 22-28) | exact (self-consistency fix) |
| `frontend/src/CheckinWizard.tsx` (`colorMap` in `ColorChip`) | component (wizard-local) | transform | same file, `colorMap`'s own token-backed entries (`Azul: "bg-tec-blue"`, `Dourado: "bg-tec-amber"`) | exact (self-consistency fix) |
| `frontend/src/CheckinWizard.tsx` (steps/stepper/gating restructure) | component (wizard orchestrator) | request-response (multi-step form state machine) | same file's existing 5-step pattern (`steps`, `stepDescriptions`, `WizardStepper`, `StepStatusBanner`, `canContinue`) — restructuring is additive/index-driven, not a new pattern | exact (self-extension) |
| `frontend/src/App.tsx` (budget-decision card, lines ~4570-5210) | component (embedded in controller-ish screen file) | request-response | `frontend/src/PosScreen.tsx` (`Button variant="danger"`/`variant="primary"` usage, line ~552/569) and `frontend/src/ui/BadgeStatus.tsx` (token-backed pill pattern) | role-match (token-compliant reference in same app) |
| `frontend/src/ServiceOrderKanban.tsx` (lines 521, 563) | component (list/card renderer) | transform (className string composition) | `frontend/src/PosScreen.tsx` (zero raw semantic-color classes) as the "target state," and `frontend/src/ui/BadgeStatus.tsx`'s `toneClasses` for the `tec-red` token name | role-match |
| `frontend/DESIGN_SYSTEM.md` (new, path is planner's discretion per D-04) | doc | — | no analog (first design-system doc in repo) — content sourced directly from `tokens.css`, `tailwind.config.ts`, `src/ui/*`, and this PATTERNS.md's excerpts | no analog |
| `frontend/scripts/verify-foundation.mjs` (optional new guard, Claude's Discretion) | config/utility (CI guard script) | batch (static analysis over source tree) | itself — existing `forbiddenFrontendTerms` loop (lines 50-82) is the template for a new "forbidden raw color class" loop | exact (self-extension) |

---

## Pattern Assignments

### `frontend/src/ui/BadgeStatus.tsx` (component, transform) — drift fix #1

**Analog:** itself, lines 22-28 (the other 6 entries in the same map)

**Full file already read in full (49 lines) — current state, verified:**
```typescript
// line 3
type BadgeTone = "orange" | "green" | "blue" | "purple" | "amber" | "red" | "slate";

// lines 22-30 — toneClasses map, the pattern to replicate for the fix
const toneClasses: Record<BadgeTone, string> = {
  orange: "bg-tec-orange/20 text-tec-orange ring-tec-orange/25",
  green: "bg-tec-success/20 text-tec-success ring-tec-success/25",
  blue: "bg-tec-blue/20 text-tec-blue ring-tec-blue/25",
  purple: "bg-tec-purple/20 text-tec-purple ring-tec-purple/25",
  amber: "bg-tec-amber/20 text-tec-amber ring-tec-amber/25",
  red: "bg-tec-red/20 text-tec-red ring-tec-red/25",
  slate: "bg-slate-400/10 text-slate-300 ring-slate-400/20",  // <-- LINE 29, THE DRIFT
};
```

**Fix pattern (exact string substitution, matches sibling entries' `bg-{tone}/20 text-{tone} ring-{tone}/25` shape — UI-SPEC's proposed `/10`+`/20` alpha for slate was inconsistent with siblings; use the dominant `/20`+`/25` shape actually used by all 6 other entries):**
```typescript
  slate: "bg-tec-muted/20 text-tec-muted ring-tec-muted/25",
```
(Confirm `--tp-muted`/`tec-muted` token exists in `tokens.css` before applying — UI-SPEC asserts it does; not independently re-verified in this pass since `tec-muted` is used pervasively elsewhere in `CheckinWizard.tsx`, e.g. lines 672, 677, 690, confirming it's a real token class.)

No other changes needed — `getBadgeStatusToneClass` (line 32-34) and `BadgeStatus` (line 36-49) consume the map generically and need no edits.

---

### `frontend/src/CheckinWizard.tsx` — `ColorChip` `colorMap` (component, transform) — drift fix #2

**Verified location: line 2472** (matches UI-SPEC exactly).

**Full context, lines 2459-2484 (already read in full):**
```typescript
function ColorChip({
  active,
  color,
  onClick,
}: {
  active: boolean;
  color: string;
  onClick: () => void;
}) {
  const colorMap: Record<string, string> = {
    Azul: "bg-tec-blue",
    Branco: "bg-white",
    Dourado: "bg-tec-amber",
    Prata: "bg-zinc-300",       // <-- LINE 2472, THE DRIFT
    Preto: "bg-black",
    Rosa: "bg-pink-400",
  };
  return (
    <OptionChip
      active={active}
      icon={<span className={`block h-4 w-4 rounded-full border border-tec-border/25 ${colorMap[color] ?? "bg-tec-field"}`} />}
      label={color}
      onClick={onClick}
    />
  );
}
```

**Fix:** `Prata: "bg-zinc-300"` → `Prata: "bg-tec-subtle"` (per UI-SPEC's D-02b, exact match). Leave `Branco`, `Preto`, `Rosa` untouched — those are literal device-color swatches, not app-chrome drift (documented exception in UI-SPEC, confirmed correct: there is no brand token for literal white/black/pink).

---

### `frontend/src/CheckinWizard.tsx` — wizard 5→7 step restructuring (component, request-response state machine)

**All line numbers below independently re-verified against the live file (discrepancies vs. UI-SPEC noted):**

**1. `steps` array — verified at line 62 (matches UI-SPEC):**
```typescript
// line 62, current
const steps = ["Cliente", "Aparelho", "Dados", "Fotos", "Revisão"];
```

**2. `stepDescriptions` array — verified at lines 63-69 (UI-SPEC said 63-69, actual is 63-69, matches; note current index-2 text differs slightly from what UI-SPEC implies as "index 2" baseline):**
```typescript
// lines 63-69, current (5 entries)
const stepDescriptions = [
  "Identifique ou cadastre o cliente antes de continuar.",
  "Identifique ou cadastre o aparelho vinculado a este cliente.",
  "Registre o relato do cliente e o estado físico do aparelho.",
  "Registre as fotos obrigatórias para validar o check-in.",
  "Revise os dados, confirme as declarações e colete a assinatura.",
];
```
Note: the current index-2 description ("Registre o relato do cliente e o estado físico do aparelho.") is the single sentence being split into the new index-2 (Defeito) and index-3 (Estado físico) descriptions per the UI-SPEC's Interaction Contract table — use UI-SPEC's exact 7-entry replacement text verbatim (already drafted there).

**3. `canContinue` gate — verified at line 398 (UI-SPEC said "around line 398", confirmed exact):**
```typescript
// line 396
const dataReady = Boolean(serviceOrder.reported_defect.trim() && serviceSelections.physicalStates.length && serviceOrder.physical_state.trim());
// line 398
const canContinue = [customerReady, deviceReady, dataReady, photoReady, true][step] ?? false;
```
This single combined `dataReady` must be split into 3 index-position entries per UI-SPEC's Interaction Contract table (Defeito: `reported_defect` check only; Estado físico: `physicalStates.length` check only; Acessórios: always `true`). The array literal grows from 5 to 7 entries; `photoReady`/`true` shift from indices 3/4 to 5/6.

**4. `WizardStepper` — verified function body at lines 648-685 (UI-SPEC said 648-685, exact match):**
```typescript
// line 649 — icons array, THE key line to change
const icons = [UserRound, Smartphone, ClipboardCheck, Camera, PenLine];

// line 652 — grid column count, THE other key line to change
<div className="grid grid-cols-5 gap-2 sm:gap-3">
```
Everything else in the function (`steps.map`, `done`/`active` boolean logic, connector-line rendering lines 659-665, circle rendering 666-676, label rendering 677-679) is already index/length-driven off `steps` and `icons[index]` — confirmed no other edits needed once both arrays grow to 7. `ShieldCheck` (line 37) and `PackageCheck` (line 30) are already imported in the file's import block (lines 10-46); `Wrench` is NOT currently imported (verified against the full import list at lines 10-46) and must be added.

**5. `StepStatusBanner` — verified function body at lines 687-701 (UI-SPEC said 687-696, actual function extends to 701; the target line is 691, UI-SPEC's claim of hardcoded "5" confirmed exact):**
```typescript
// line 691 — hardcoded step count, THE line to change
<span className="font-semibold text-white">Etapa {step + 1} de 5</span>
```
Fix: `de 5` → `de {steps.length}`.

**6. `ServiceDataStep` content redistribution — verified full function body at lines 1738-1977 (UI-SPEC's claimed range 1791-1977 covers only the JSX return; the function signature/props start at 1738):**

Confirmed structure to split into 3 branches (current single `step === 2` branch renders all of this):
- Lines 1793-1815: "Contato e acesso desta OS" `WizardCard` — check-in-level settings (contact override, access credential, caminho, payment timing, initial budget). **Not named in D-03's scope** — UI-SPEC flags this correctly; this content currently sits at the top of the old combined step and has no explicit new home in the 3-way split. Planner must decide: keep it pinned to the first of the 3 new sub-steps (Defeito, index 2) or relocate elsewhere — flag as an open question for the plan.
- Lines 1816-1854: "Retrabalho em garantia" `WizardCard` (warranty candidate same-defect detection) — same "no explicit new home named" situation as above; UI-SPEC's D-03 groups the warranty card into "Defeito" (line 22 of CONTEXT.md: "the prior-repair-suggestion card ... co-located around lines ~1780-1910"), so this should move to the Defeito sub-step (index 2) along with the operating-condition/reported_defect content below.
- Lines 1861-1904: "Condição de funcionamento" `ChipGroup` (line 1866) + `will_power_on_test` toggle (line 1862) + helper text — → **Defeito** sub-step (index 2).
- Lines 1906-1922 (left column of the 2-col grid): `reported_defect` `TextArea` (line 1908) + "Acessórios recebidos" `ChipGroup` (line 1910) — the `TextArea` → **Defeito** (index 2); the accessories `ChipGroup` → **Acessórios** (index 4), per D-03.
- Lines 1924-1947 (right column, top): "Local do problema"/"Funções com teste limitado" `ChipGroup` (line 1927) — → **Estado físico** sub-step (index 3).
- Lines 1949-1960 (right column, bottom): "Estado físico declarado" `CheckboxGrid` (line 1950) — → **Estado físico** sub-step (index 3).
- Lines 1965-1975: "Observações da entrada" `TextArea` (feeds `attendance_notes`) — → **Acessórios** sub-step (index 4), per D-03's exact grouping.

**Toggle helper (line 1783-1789) and props/local derived values (`isFullyOperational`, `isPartiallyOperational`, `normalizedDefect`, lines 1780-1782) are shared across the new sub-steps** — keep them computed once at the top of whatever component/branch structure replaces the single `ServiceDataStep`, not duplicated per branch.

---

### `frontend/src/App.tsx` — budget-decision card token drift (component, request-response)

**Analog:** `frontend/src/PosScreen.tsx` (100% token-compliant `Button` usage) + `frontend/src/ui/BadgeStatus.tsx` (token-backed pill pattern)

**Verified exact current lines (all confirmed present, matches UI-SPEC's list exactly):**
```typescript
// line 4578 — approved badge
<span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
// line 4582 — rejected badge
<span className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 px-2.5 py-0.5 text-xs font-semibold text-rose-400">
// line 4586 — expired badge
<span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-400">
// line 4590 — pending badge
<span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-400">
// line 4632 — approve button raw override
<Button className="bg-emerald-600 hover:bg-emerald-500 text-white" icon={<CheckCircle2 size={16} />} onClick={...} type="button">
// line 4640 — reject button raw override
<Button className="border-rose-500/40 text-rose-400 hover:bg-rose-500/10" icon={<XCircle size={16} />} onClick={...} type="button" variant="secondary">
// line 4654 — approve form container
<form className="mt-4 rounded-control border border-emerald-500/30 bg-emerald-950/10 p-4 space-y-3" ...>
// line 4657
<h4 className="text-sm font-bold text-emerald-400">Confirmar Aprovação do Orçamento</h4>
// line 4713 — reject form container (structurally mirrors 4654)
// line 4716
<h4 className="text-sm font-bold text-rose-400">Registrar Reprovação / Recusa do Orçamento</h4>
// line 4757 — reject submit button raw override
<Button className="bg-rose-600 hover:bg-rose-500 text-white" disabled={submitting} type="submit">
// line 5206
return <Card className="border-emerald-500/30 bg-emerald-950/10 p-5">
// line 5208
<CheckCircle2 className="text-emerald-400" size={18} />
```

**Reference target pattern from `PosScreen.tsx` (verified: line 552 uses `variant="primary"`, line 569 uses `variant="danger"` with no raw className color override, e.g. `}} variant="danger">Limpar venda</Button>`):** Buttons should use `Button`'s built-in `variant` prop (`primary`/`danger`, see `frontend/src/ui/Button.tsx` full source below) instead of raw `className` overrides. Badge pills should reuse `BadgeStatus`'s tone pattern (`bg-tec-{tone}/20 text-tec-{tone} ring-tec-{tone}/25`) rather than hand-rolled `bg-emerald-500/15 ... text-emerald-400` markup — UI-SPEC's recommendation to consider adding a `success` variant to `Button` (currently only `primary`/`secondary`/`ghost`/`danger` exist, verified in full source below) is Claude's Discretion since D-02b's lock names only the 2 BadgeStatus/ColorChip instances; this App.tsx cleanup is the "additional drift, planner's discretion whether to fold in" category.

**`Button.tsx` full source (11 lines of variants, already read in full) — the variant map new code must extend or reuse:**
```typescript
type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-tec-orange text-tec-ink shadow-glow hover:bg-tec-digital-orange",
  secondary: "border border-tec-border/20 bg-tec-field text-tec-text hover:border-tec-orange/50",
  ghost: "text-tec-subtle hover:bg-tec-field hover:text-tec-text",
  danger: "bg-tec-red/20 text-red-100 ring-1 ring-tec-red/40 hover:bg-tec-red/30",
};
```
Note: `danger`'s own text color (`text-red-100`) is itself a minor pre-existing drift (raw Tailwind gray-adjacent red-100, not a `tec-*` token) — not named in any locked decision; flag but do not fix unless planner chooses to extend scope, since D-02b names only the 2 BadgeStatus/ColorChip drifts as locked.

**Token equivalents to use for the App.tsx fixes (straight string substitution, verified against `BadgeStatus.tsx`'s existing `green`/`red`/`amber` tone classes):**
- `emerald-400/500/600/950` → `tec-success` (or `tec-green`, both map to the same success semantic per UI-SPEC's Color table)
- `rose-400/500/600/950` → `tec-red`
- `amber-400/500` → `tec-amber`

**Additional scattered drift (App.tsx:7412, 1459, 3050, 3174) — not independently re-verified in this pass (UI-SPEC's line numbers for these were not re-checked; treat as unverified leads, re-grep before editing):**
```
App.tsx:7412 — border-red-500/25 bg-red-500/10 text-red-300 → border-tec-red/25 bg-tec-red/10 text-tec-red
App.tsx:1459,3050,3174 — text-red-100, text-red-400 → text-tec-red
```

---

### `frontend/src/ServiceOrderKanban.tsx` — overdue indicator token drift (component, transform)

**Verified exact current lines (matches UI-SPEC exactly):**
```typescript
// line 521
item.stage_clock?.is_overdue && "border-red-500/60 ring-1 ring-red-500/25",
// line 563
{item.stage_clock?.is_overdue ? <span className="shrink-0 text-xs font-bold text-red-400">Atrasada</span> : null}
```

**Fix (straight substitution, matches `BadgeStatus.tsx`'s `red` tone token name):**
```typescript
// line 521
item.stage_clock?.is_overdue && "border-tec-red/60 ring-1 ring-tec-red/25",
// line 563
{item.stage_clock?.is_overdue ? <span className="shrink-0 text-xs font-bold text-tec-red">Atrasada</span> : null}
```

This is the concrete OS-vs-PDV alignment target (D-05): `PosScreen.tsx` has zero raw semantic-color classes (grep-verified: only `variant="danger"`/`variant="primary"` and token classes found in this pass), while this Kanban card is the outlier.

---

## Shared Patterns

### Token naming convention
**Source:** `frontend/src/ui/BadgeStatus.tsx` lines 22-28
**Apply to:** all 3 drift-fix locations (BadgeStatus, ColorChip, App.tsx, ServiceOrderKanban.tsx)
```typescript
// The established alpha-suffix convention for tone-based backgrounds/text/rings:
{tone}: "bg-tec-{tone}/20 text-tec-{tone} ring-tec-{tone}/25"
```

### Button variant discipline
**Source:** `frontend/src/ui/Button.tsx` (full file, 35 lines) + `frontend/src/PosScreen.tsx` line 569 (`variant="danger"` usage with no className override)
**Apply to:** `App.tsx`'s budget-decision buttons (lines 4632, 4640, 4757) if planner chooses to extend the single pass beyond the 2 locked fixes.
```typescript
// Existing correct call-site pattern (PosScreen.tsx line ~569):
<Button ... variant="danger">Limpar venda</Button>
// vs. the drift pattern in App.tsx (raw className color override instead of variant prop):
<Button className="bg-emerald-600 hover:bg-emerald-500 text-white" ...>
```

### CI guard extension pattern (if planner takes up the Claude's-Discretion option)
**Source:** `frontend/scripts/verify-foundation.mjs` lines 50-82 (existing `forbiddenFrontendTerms` loop over `collectFiles(src)`)
```javascript
// Existing loop shape to replicate for a new "forbidden raw color class" check:
const sourceFiles = collectFiles(join(root, "src"));
for (const file of sourceFiles) {
  const body = readFileSync(file, "utf8");
  for (const term of forbiddenFrontendTerms) {
    // ... permitted-file exceptions ...
    if (body.includes(term)) {
      throw new Error(`Termo sensível no front (${term}): ${file}`);
    }
  }
}
```
A new guard would need a regex (e.g. `/\b(?:bg|text|border|ring)-(?:red|rose|emerald|green|amber|slate|zinc|gray)-\d{2,3}\b/`) with explicit exceptions for the documented legitimate cases (`ColorChip`'s `Branco`/`Preto`/`Rosa` literal-color swatches in `CheckinWizard.tsx`) — mirror the existing `permittedOwnEarningsApi`-style named-exception pattern (lines 27-30, 57-77) rather than inventing a new exception mechanism.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/DESIGN_SYSTEM.md` (or `docs/DESIGN_SYSTEM.md`, planner's discretion per D-04) | doc | — | First formal design-system document in the repo — no prior analog exists. Source content directly from: `frontend/src/styles/tokens.css` (not read line-by-line in this pass — already fully characterized in `04-UI-SPEC.md`'s Color/Typography/Spacing tables, which the planner/executor should cite directly), `frontend/tailwind.config.ts`, and the `src/ui/*` component list in UI-SPEC.md's Component Inventory table (already accurate and verified against the actual `src/ui/` directory structure referenced throughout this pass). |

---

## Metadata

**Analog search scope:** `frontend/src/ui/`, `frontend/src/CheckinWizard.tsx`, `frontend/src/App.tsx`, `frontend/src/ServiceOrderKanban.tsx`, `frontend/src/PosScreen.tsx`, `frontend/scripts/verify-foundation.mjs`
**Files read in full or targeted-range:** `BadgeStatus.tsx` (49 lines, full), `Button.tsx` (35 lines, full), `verify-foundation.mjs` (115 lines, full), `CheckinWizard.tsx` (targeted: lines 1-100, 648-701, 1738-1977, 2459-2484, plus grep-located line hits), `App.tsx` (targeted: lines 4570-4669, plus grep hits for 4578-5208), `ServiceOrderKanban.tsx` (grep-targeted lines 521, 563), `PosScreen.tsx` (grep-targeted for `variant=` and token usage)
**Pattern extraction date:** 2026-09-19
**Discrepancies found vs. `04-UI-SPEC.md`:** `StepStatusBanner`'s function body actually spans lines 687-701 (UI-SPEC said 687-696 — UI-SPEC's range only covered the JSX return's first half, not the closing tags); `ServiceDataStep`'s full function (including the props/type signature) starts at line 1738, not 1791 as UI-SPEC's JSX-only range implied — both are minor range-boundary discrepancies, not factual errors; all specific line-content claims (steps array, colorMap drift, App.tsx/Kanban raw colors) were confirmed byte-for-byte accurate.
