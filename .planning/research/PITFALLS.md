# Pitfalls Research

**Domain:** Auditing/stabilizing a brownfield Frappe/ERPNext repair-shop ERP (PDV, trade-in/warranty, caixa) with strict role-based financial guards, ahead of a design-system pass and a single-pilot-customer Coolify deploy.
**Researched:** 2026-09-02
**Confidence:** MEDIUM-HIGH (grounded directly in this repo's own audit evidence — `CONCERNS.md`, `PROJECT.md` — plus general Frappe/ERPNext framework behavior and brownfield-rollout domain knowledge; web corroboration for the Frappe-specific `set_user()`/versioning claims was thin, see Sources)

## Critical Pitfalls

### Pitfall 1: "Grep once, declare fixed" — the session anti-pattern reappears in the modules not yet audited

**What goes wrong:**
The OS audit found `frappe.set_user()` misuse at **10 call sites** across `permissions.py`, `acceptance.py`, `financial.py`, `frontend/pos.py`, `tracking.py`, and `frontend/api.py`, and fixed all of them with an `as_user()` context manager. But `frontend/pos.py` is explicitly in that list — meaning the PDV module already had at least one instance. Trade-in/warranty and caixa code, written under the same historical habits, are very likely to contain the same pattern in call sites that weren't touched during the OS-only fix pass (e.g. cash-register open/close as a privileged operation performed "as" another user, trade-in valuation lookups that temporarily elevate to read cost data).

**Why it happens:**
The fix was scoped to the files touched during the OS audit. A codebase-wide anti-pattern doesn't get eliminated by fixing the instances discovered on one flow — it gets eliminated by searching for the *pattern*, not the *symptom*. Copy-paste-driven development means the same risky idiom shows up wherever a developer needed "run this as another user" and reached for the nearest existing example, which was `frappe.set_user()` before the fix existed.

**How to avoid:**
Before starting the PDV/trade-in/caixa audit, run a full-repo grep for `frappe.set_user(` (excluding test files, where it's acceptable in setup code) and for near-variants: `frappe.session.user =`, direct session mutation, or any local helper that isn't `as_user()`. Treat any hit outside `as_user()`'s own implementation as a must-fix before that module is considered audited — not as a "nice to catch while we're there."

**Warning signs:**
- Symptom in production: user gets logged out or sees "User None not found" after a privileged action (cash close, trade-in cost lookup, warranty override) — the exact symptom already seen once.
- Code smell: any function that needs to read/write as a different user without going through `as_user()`.

**Phase to address:**
PDV/trade-in/caixa audit phase — as a mandatory pre-check *before* live end-to-end testing begins, not something discovered mid-flow by accident.

---

### Pitfall 2: Fixed-in-files ≠ fixed-in-pattern — regression enters through new edit/audit-log code

**What goes wrong:**
The new "editable OS fields with audit log" work (contact, device credential, CPF) is new code being written *during* this same milestone. If whoever implements the audit-logging needs "run this write as the Diretor to bypass a field-level restriction" or similar, it's structurally the same temptation that produced the original 10 `set_user()` call sites — and it would be a *brand new* instance of an anti-pattern the team just spent a whole session eradicating.

**Why it happens:**
Anti-pattern eradication is treated as a one-time cleanup event instead of a standing constraint. Once the "fixed" commit lands, attention moves on, and new code written afterward isn't checked against the same rule unless it's enforced structurally (lint rule, code review checklist, or a strict `as_user()`-only convention documented in `CLAUDE.md`/`CONVENTIONS.md`).

**How to avoid:**
Add `frappe.set_user(` (outside test files) to a CI grep-gate or lint rule that fails the build. This turns tribal knowledge ("we know not to do this") into an enforced constraint, matching the project's own rule that security protections live in the engine, not in memory.

**Warning signs:** New PR/commit touching privilege-elevation logic without importing `as_user()`.

**Phase to address:** Editable-fields-with-audit-log phase (OS.6 gap #3) and as a standing CI check going forward.

---

### Pitfall 3: Frappe's built-in Version/Track-Changes doctype becomes an unguarded leak channel for cost data

**What goes wrong:**
Frappe ships a native "Track Changes" feature (the `Version` doctype) that snapshots a full before/after JSON diff of a document on every save, once `track_changes` is enabled on a DocType. If the team reaches for this built-in mechanism to satisfy "audit-logged edit capability" for Service Order fields, it will capture *the entire document diff*, not just the fields it was turned on for — including cost/margin fields if they live on the same document, or the raw device credential if it's ever briefly present in cleartext during a save cycle. The custom `SENSITIVE_FIELD_NAMES` deny-list in `api.py` guards *the frontend API response path* — it does nothing to guard Frappe's own generic Version/Activity Log UI or the standard `get_list`/`get_doc` calls a Diretor-adjacent role could reach through desk access or a report.

**Why it happens:**
"Audit log" sounds like it maps directly onto Frappe's built-in versioning feature, and enabling it is a one-line checkbox — a much cheaper implementation path than a custom audit table with an explicit allow-list of loggable fields. The cost/credential guard rules were designed against the custom `frontend/api.py` surface, not against Frappe's native doctype machinery, so nobody is thinking about this channel when they flip the checkbox.

**How to avoid:**
Do **not** use generic Frappe `track_changes` on Service Order (or any doctype carrying cost/credential fields) for this feature. Build a purpose-specific audit log (custom child table or separate doctype) that only ever stores the specific fields being made editable (contact name/phone, masked credential reference, CPF) and is served through the same guarded API surface and role checks as everything else. If `track_changes` is already enabled anywhere on Service Order for other reasons, audit what desk/report access exists to the Version doctype for non-Director roles.

**Warning signs:** `track_changes: 1` present in `service_order.json` (or any doctype with cost/credential fields) combined with any non-Director role having desk access or a report that can reach the Version doctype.

**Phase to address:** Editable-fields-with-audit-log phase (OS.6 gap #3) — verify with a sentinel test *before* writing the feature, per the security-consultation rule in `CLAUDE.md`.

---

### Pitfall 4: The new edit endpoint reuses the record's full serialization, leaking cost through a side door

**What goes wrong:**
The cleanest implementation path for "edit contact/credential/CPF" is to add an update endpoint that saves the field and returns the updated record so the frontend can refresh its state. If that return payload is built from the same `frappe.get_doc(...).as_dict()` (or similar) as internal code rather than routed through the existing sanitization/deny-list function used by the read endpoints, it re-introduces a cost/margin leak on a brand-new endpoint that the existing sentinel tests never touch (because they were written against the endpoints that existed *before* this feature).

**Why it happens:**
New endpoints are easy to build by pattern-matching an existing "create" or "get" handler, and easy to forget that the safety property (`contains_sensitive_field()` filtering) is a manual step applied at each endpoint, not something enforced by a type system or middleware that would catch a missing call.

**How to avoid:**
Route every new endpoint's response — not just the payload of the field being edited — through the same `contains_sensitive_field()`/deny-list gate used elsewhere in `api.py`. Add a sentinel-value test for the *new* endpoint specifically (reusing the existing `BUDGET_COST_GUARD_VALUATION`-style sentinel pattern already in `test_frontend_api.py`), for each of the three fields being made editable and for every role that can call the endpoint.

**Warning signs:** New endpoint added to `api.py` without a corresponding new sentinel assertion added to `test_frontend_api.py` in the same commit.

**Phase to address:** Editable-fields-with-audit-log phase.

---

### Pitfall 5: Masking is a UI convention, not a storage guarantee — the audit log can leak the credential even when the screen doesn't

**What goes wrong:**
The device credential is already correctly masked in the UI (`has_device_access_credential` boolean, explicit reveal via prompt). But "audit-logged edit" implies storing a record of *what changed*. If the audit-log write logs `old_value` / `new_value` naively for the credential field the same way it does for contact name or CPF, the plaintext (or decrypted) credential ends up sitting in the audit log table — a completely new storage location that was never in scope for the original encrypted-storage design, and that the existing sentinel tests (scoped to OS detail/print/WhatsApp/tracking channels per `CONCERNS.md`) do not cover.

**Why it happens:**
Generic audit-logging code treats all fields uniformly ("log before/after for every changed field") because that's the simplest, most reusable implementation. The credential field's special handling is easy to forget when it's just one of three fields being wired into a shared edit-and-log code path.

**How to avoid:**
Explicitly special-case the credential field in the audit log: log *that* it changed (and who/when), never the before/after value. Extend the sentinel test suite to also assert the sentinel credential value never appears in the audit log table/response — `CONCERNS.md` already flags "no explicit audit-log testing for credential reveal yet" as an open gap.

**Warning signs:** Audit log schema has generic `old_value`/`new_value` text columns applied uniformly to all three editable fields without a field-type-aware exception.

**Phase to address:** Editable-fields-with-audit-log phase — this is the single highest-risk new surface this milestone introduces for the device-credential guard.

---

### Pitfall 6: Editable fields quietly reopen state that the 6 workflow locks were built to protect

**What goes wrong:**
Once an edit capability exists on an "already created" record, there's a natural next step — someone (this milestone or a future one) extends it to more fields "while we're in there." If contact/credential/CPF editing is implemented as a general-purpose "patch this OS" endpoint rather than three narrowly-scoped field updates, it becomes trivial to accidentally allow editing fields that interact with workflow state, warranty date math, or pricing — silently bypassing the 6 lifecycle gates that are supposed to live only in the engine.

**Why it happens:**
Narrow, single-purpose endpoints feel like more code to write than one generic "update service order fields" endpoint with a whitelist parameter. The generic version is a much easier trap to fall into during a fast-moving stabilization milestone, and every future feature request ("can we also let Atendente fix a typo in X?") becomes a one-line change to that whitelist instead of a deliberate new review.

**How to avoid:**
Build three explicit, narrow endpoints/handlers (or one endpoint with a hard-coded, non-configurable field allow-list) — not a generic patch-any-field mechanism. Explicitly test that the endpoint rejects attempts to touch any field outside the allow-list, and that it works identically regardless of the OS's current workflow state (or explicitly documents which states permit editing, if that's a real business rule — e.g. can CPF be corrected after pickup?).

**Warning signs:** Endpoint signature accepts an arbitrary `field_name`/`value` pair instead of three named parameters.

**Phase to address:** Editable-fields-with-audit-log phase; call out explicitly in the phase's acceptance criteria which fields are (and are not) editable in which OS states.

---

### Pitfall 7: Static code review confirms the 90-day warranty *logic* exists but cannot confirm the *boundary* is correct

**What goes wrong:**
`policies.py` implementing the 90-day rule "looks right" on read — but the OS core audit already found a timezone-driven date-parsing bug once (`d7bc397`, item in the fixed-bugs list). Date-boundary arithmetic (day 90 passes, day 91 blocks) is exactly the class of bug that hides behind correct-looking code: an off-by-one in `add_days` vs. inclusive/exclusive comparison, or a timezone conversion that shifts the effective calendar day near midnight, will pass a code read and only surface when a real clock value crosses the boundary.

**Why it happens:**
Reviewers verify that the *formula* matches the stated business rule ("today + 90 days"), not that the *comparison operator* and *timezone handling* around it are correct — and those are precisely where the previous timezone bug lived, in the same general area of the codebase (service order dates).

**How to avoid:**
This is explicitly called out as untested in `CONCERNS.md` — treat it as mandatory, not optional: create an OS, mark delivered with a controlled `pickup_date`, then test warranty-eligibility at exactly day 89 (should pass) and exactly day 91 (should block), using the system's actual date-comparison code path (not a mocked date library) so timezone handling is exercised for real. Also test day 90 itself and confirm which side of the boundary it's supposed to fall on per the stated business rule (mesmo defeito grátis até quando, exatamente).

**Warning signs:** Test suite has a test named something like `test_warranty_90_days` that only checks the "happy path" (warranty applies at all) without asserting the exact boundary day.

**Phase to address:** OS.6 closure phase (90-day warranty end-to-end gap) — this is already an explicit Active requirement in `PROJECT.md`.

---

### Pitfall 8: Caixa (cash register) reconciliation bugs only appear under concurrent, cross-module load — never in isolated code review

**What goes wrong:**
Cash-register open/close reconciliation math can be verified correct in isolation (one sale, one close) through static review or a single-transaction test, and still drift under real conditions: a PDV sale, a trade-in credit applied against a new purchase, and a no-charge warranty repair all touching the same open caixa session concurrently. Rounding, double-counting, or a missed payment-method bucket only shows up when multiple transaction types interleave against the same session — exactly the scenario a code reviewer reading `caixa`/`pos` logic in isolation won't reconstruct mentally.

**Why it happens:**
Financial reconciliation logic is usually written and reviewed per-transaction-type, but the register itself is a shared, stateful accumulator across all transaction types simultaneously. Cross-module interaction bugs are structurally invisible to a single-module code review.

**How to avoid:**
The live end-to-end audit of caixa must explicitly include a scenario that opens one register session and runs at least one of each transaction type (cash sale, card sale, trade-in credit applied, no-charge warranty completion) before closing it, then verifies the closing total reconciles to the sum of what actually happened — not just that each transaction type individually "looks right" in the ledger.

**Warning signs:** Existing tests for caixa open/close only ever run a single transaction type per test case.

**Phase to address:** PDV/trade-in/caixa audit phase — design the end-to-end test scenario explicitly around cross-module interleaving, not per-module isolation.

---

### Pitfall 9: "Has tests" is mistaken for "tests the boundary" — coverage exists but proves nothing about the risky edge

**What goes wrong:**
`CONCERNS.md` already documents this pattern for OS: `test_frontend_api.py` has extensive coverage, but "only happy path paths tested in audit; edge cases... less certain." The same trap applies to PDV/trade-in/caixa: the presence of tests creates false confidence that the module is "covered," when the tests exercise the common case and never touch the specific boundary (91st day, exact caixa close total, concurrent trade-in valuation, cost guard on a *new* endpoint) that actually matters for financial correctness.

**Why it happens:**
Test count and coverage percentage are easy to check; boundary-condition coverage is not — it requires someone to explicitly think through "what's the adversarial or edge-case input here" for each financial rule, which is slower and less mechanical than writing a happy-path test.

**How to avoid:**
For every financial/time-boxed rule being audited (warranty window, caixa close, trade-in valuation, cost guard on each role×endpoint pair), explicitly write down the boundary condition being tested *before* writing the test, and confirm the test actually exercises that exact boundary — not just "a" value in the successful range.

**Warning signs:** A test's assertion checks that an operation "succeeds" or "returns 90" without ever testing the value one unit past the boundary in either direction.

**Phase to address:** PDV/trade-in/caixa audit phase and OS.6 closure phase — apply as a review checklist item, not just a testing habit.

---

### Pitfall 10: "Stabilize everything" has no stopping criterion — the audit phase can expand indefinitely

**What goes wrong:**
The OS core audit — one module — found 8 real bugs plus 3 pre-existing CI-blocking bugs through live testing. Applying "the same rigor" to three more entire modules (PDV, trade-in/warranty, caixa) without a bounded scope or explicit stopping criterion risks the audit phase never actually finishing, because live end-to-end testing is generative: every bug fixed can reveal an adjacent untested path, and "confidence" is a feeling, not a checklist that terminates.

**Why it happens:**
The motivation for this milestone is explicitly "muitas alterações anteriores deixaram o sistema mais confuso... quer confiança real" — an emotional/trust goal rather than a bounded technical one. Trust-seeking work is naturally open-ended unless someone defines what "audited enough" means in advance.

**How to avoid:**
Before starting each module's audit, write down the specific user journeys that constitute "the real day-to-day flow" for that module (mirroring how `REGUA_PRODUTO.md` scoped the OS journey) and treat the audit as complete when those specific journeys pass end-to-end with no known critical/high bugs — not when the auditor "feels confident." Log lower-priority findings (the way `CONCERNS.md`'s tech-debt/scaling sections already do) rather than chasing them to zero before moving on.

**Warning signs:** Audit phase duration significantly exceeds the OS audit's timebox without a defined list of "done" criteria; new findings keep arriving in categories unrelated to the original scope (e.g., discovering frontend architecture debt while looking for a caixa bug).

**Phase to address:** PDV/trade-in/caixa audit phase — define scope and done-criteria explicitly at phase-planning time, before execution starts.

---

### Pitfall 11: Retrofitting a design system onto a 9500-line monolithic component is the single riskiest moment in this sequence — and it's scheduled last, right before deploy

**What goes wrong:**
`App.tsx` is already flagged as having deeply nested conditional rendering tied to role/state/feature-flag checks (`CONCERNS.md`). A "design system applied in one pass at the end" necessarily touches markup and class names across this same file, in the same nested-conditional regions that were just carefully stabilized during the audit phases. Sweeping visual changes in a monolithic, deeply-nested component are exactly the conditions under which a change to one rendering path accidentally breaks a sibling path — the same failure mode item #8 in the OS audit already demonstrated (local state lost on navigation, masked by an unrelated code path).

**Why it happens:**
"Polish at the end, in one pass" is a deliberate, sound principle (per `CLAUDE.md`) for *avoiding wasted cosmetic iteration* — but it also means the highest-blast-radius change (touching nearly every screen's markup) lands *after* the confidence-building work is done and *immediately before* production deploy, with the least remaining time to catch a regression before the pilot customer sees it.

**How to avoid:**
Do not treat "design system pass" as risk-free just because it's "only visual." Re-run the full behavioral test suite (not just visual/typecheck) after the design pass, and re-run a live end-to-end smoke test of the core journeys (OS cycle, PDV, warranty, caixa) *after* the design pass and *before* deploy — the design phase needs its own verification gate, not just a build-passes check. Consider scoping the design pass to avoid touching the most fragile, deeply-nested regions (workflow state rendering, acceptance modals) more than strictly necessary, or extracting those into named render functions *before* restyling them (per the anti-pattern fix already recommended in `CONCERNS.md`) so the visual change and the structural change aren't tangled together in the same diff.

**Warning signs:** Design-system PR/commit has a large diff touching `App.tsx` workflow/acceptance rendering blocks with no corresponding test changes or re-run of the live audit scenarios.

**Phase to address:** Design-system application phase — add an explicit "re-verify the previously-audited flows" step as an exit criterion, not just visual QA.

---

### Pitfall 12: CI passing after the design pass proves the code compiles, not that the UI still works — markup-coupled tests can pass while the real screen is broken

**What goes wrong:**
If any tests (frontend or the guard-oriented sentinel tests) assert on DOM structure, specific class names, or element ordering that a design-system pass will change, then either (a) the tests break and get "fixed" by loosening the assertion to make CI green again — silently reducing coverage exactly when it matters most — or (b) the tests never touched that structure at all, so CI stays green while a real interaction (a button that no longer triggers its handler after a markup refactor) is broken. `CLAUDE.md`'s own rule ("nunca declarar pronto sem testar o fluxo real") exists precisely because CI-green and works-in-the-browser are not the same guarantee — this project already knows that from the OS audit ("botões que apenas aparecem na tela mas não executam a ação").

**Why it happens:**
The path of least resistance when a design refactor breaks a brittle test is to adjust the test to match the new markup, treating the test as an obstacle rather than a signal.

**How to avoid:**
After the design-system pass, don't rely on CI-green alone — repeat a live click-through of the core journeys (the same discipline used for the OS audit) specifically targeting the screens with the biggest visual diff. Treat any test that had to be "loosened" to pass post-design-change as a flag to manually re-verify that specific interaction live.

**Warning signs:** Git diff on the design-system commit includes changes to test files (assertion loosening) alongside markup changes, with no corresponding live-verification note.

**Phase to address:** Design-system application phase, as the exit gate before moving to deploy prep.

---

### Pitfall 13: Deploy-readiness (Coolify, printing, QR/barcode) treated as the last checkbox instead of a parallel track — infra surprises land with zero buffer before go-live

**What goes wrong:**
Physical printing and QR/barcode reading depend on hardware, drivers, and network conditions that have nothing to do with application code correctness and cannot be discovered by any amount of code audit or CI. If Coolify deploy prep only starts after stabilization and design-system work are both fully done, any infrastructure surprise (printer driver incompatibility, thermal-print format issue, barcode scanner input handling, SSL/DNS misconfiguration, backup/restore not actually validated) is discovered with no schedule slack left before the pilot customer needs the system live.

**Why it happens:**
The milestone's phases are naturally sequenced by *logical dependency* (can't polish an unstable app, can't deploy an unpolished one) — but infra validation isn't logically dependent on app-code stability at all. Sequencing it last by default, just because it's listed last, conflates "must be validated last" with "must be started last."

**How to avoid:**
Start a lightweight Coolify staging deploy *early* — even while the audit phases are still in progress — using whatever build currently exists, specifically to validate the pieces that are infra-only and code-independent: physical printer output format, QR/barcode scan-to-lookup flow, SSL/domain setup, backup/restore. Treat "final" deploy prep (last phase) as a *cutover*, not a *first attempt*.

**Warning signs:** No Coolify staging environment exists until the deploy-prep phase begins; printer/QR hardware hasn't been tested against the app at all before that point.

**Phase to address:** Should be pulled earlier — recommend a lightweight infra-validation spike parallel to the audit phases, with the dedicated deploy-prep phase at the end handling only the final cutover and pilot-specific configuration.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Generic "patch any field" edit endpoint instead of 3 named handlers | Less code to write for the audit-log feature | Reopens workflow-lock and cost-guard bypass risk every time a new field is added later | Never for this project — role/state guards are non-negotiable per `CLAUDE.md` |
| Enabling Frappe's built-in `track_changes` instead of a purpose-built audit log | Zero custom code, one checkbox | Cost/credential leak through an unguarded native Frappe UI/API channel | Only for doctypes with no sensitive fields |
| Testing warranty/caixa boundaries via code review instead of a live clock-crossing test | Faster to "call it done" | Off-by-one/timezone bug ships to the pilot's actual legal warranty commitment | Never for financial/legal time-boxed rules |
| Deferring Coolify staging until the last phase | Simpler phase sequencing on paper | Infra surprises surface with no buffer before pilot go-live | Never for a single, real, deadline-driven pilot rollout |
| Loosening a test assertion to make CI green after a design-system markup change | Unblocks the commit quickly | Silently removes the safety net exactly where the biggest diff just landed | Never without a live re-verification note in the same commit |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| Coolify production deploy | Treating it as a final step validated only after everything else is "done" | Stand up staging early, validate infra-only concerns (SSL, printing, scanning, backups) in parallel with app audit phases |
| Physical thermal/A4 printing | Assuming a format that renders correctly on screen/PDF preview also prints correctly on the actual thermal hardware | Test print output on the real device model the pilot store uses, specifically re-checking the device-credential masking sentinel on the printed output (already an explicit `CONCERNS.md` recommendation) |
| QR/barcode scanning | Assuming scanner input behaves like keyboard input in all edge cases (special characters, scan speed, focus loss) | Test with the actual scanner hardware against the real lookup endpoint before deploy, not just a manually-typed code in dev |
| Frappe `Version`/Track Changes doctype | Reaching for it as "the audit log" without checking what it exposes to non-Director roles | Build a purpose-specific, field-scoped audit log routed through the same guard as the rest of the API |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Caixa reconciliation logic verified only per-transaction-type | Closing totals look right in isolated tests, drift in real concurrent use | Test one register session with all transaction types interleaved before close | First real day with mixed PDV + trade-in + warranty traffic on one register |
| `get_all()` calls without `limit_page_length` (already flagged in `CONCERNS.md`) in newly-audited PDV/trade-in/caixa endpoints | Slow or unbounded queries as record volume grows | Audit every new/touched endpoint for explicit limits during this milestone's work, not just the ones already flagged | Once the pilot accumulates months of PDV/caixa transaction history |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| New edit/audit-log endpoint bypasses the existing `contains_sensitive_field()` deny-list | Cost/margin leaks to Atendente/Gestor/Técnico through a brand-new channel the old sentinel tests don't cover | Route every new endpoint response through the existing guard function; add a new sentinel test per new endpoint/role pair |
| Native Frappe `track_changes`/Version doctype enabled on a doctype carrying cost or credential fields | Leak through Frappe's own desk/report UI, invisible to the custom API guard | Use a purpose-built, field-scoped audit log instead; if `track_changes` exists anywhere on Service Order already, audit non-Director desk access to Version |
| Audit log stores raw before/after values uniformly for all editable fields, including device credential | Plaintext credential lands in a new, untested storage location | Special-case the credential field: log the fact of change, never the value |
| `frappe.set_user()` reappearing in PDV/trade-in/caixa code not covered by the original fix pass | Session corruption, same "User None not found" bug recurring in a new module | Full-repo grep for the pattern before/during this milestone's audit; add a CI grep-gate going forward |
| Generic "patch any field" edit endpoint | Could be extended to bypass workflow-lock-protected fields (pricing, state) without a deliberate review | Named, narrow handlers with a hard-coded field allow-list |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Edit capability added with no visible indicator of "this was edited" | Attendant or director can't tell a contact/CPF was corrected after the fact, undermining trust in the record | Surface a lightweight "editado por X em Y" indicator on the OS detail screen, sourced from the audit log |
| Design-system pass changes visual hierarchy of already-stable screens without re-validating the primary action per screen | Staff trained on the old layout for the primary action (e.g., where "aprovar orçamento" lives) get confused or click the wrong control right when the pilot is going live | Re-apply the "reason about hierarchy and primary action before building" principle from `CLAUDE.md` per screen during the design pass, not just visually restyle in place |
| Caixa close screen doesn't clearly separate cash/card/trade-in-credit/warranty-no-charge buckets | Staff can't self-verify the close total matches physical cash on hand, leading to end-of-day reconciliation disputes | Explicitly break out each payment/credit type in the close summary, matching the end-to-end test scenario used in the audit |

## "Looks Done But Isn't" Checklist

- [ ] **Session anti-pattern fix:** Verify with a full-repo grep, not just "the files touched during the OS audit" — confirm zero `frappe.set_user()` outside `as_user()` and test setup, across PDV/trade-in/caixa too.
- [ ] **Audit-logged edit capability:** Verify the audit log itself (not just the UI) never contains the device credential in plaintext, using the sentinel-value discipline already used elsewhere in this project.
- [ ] **90-day warranty rule:** Verify day 89 passes and day 91 blocks using the system's real date-comparison code path (not a mocked date), not just that "a" warranty test exists.
- [ ] **Caixa close:** Verify reconciliation with a mixed-transaction-type scenario (cash + card + trade-in credit + no-charge warranty) in one register session, not just single-transaction-type tests.
- [ ] **Cost guard on new endpoints:** Verify every new endpoint added this milestone (edit endpoints, PDV/trade-in endpoints touched during audit) has its own sentinel test, not just inherited coverage from pre-existing endpoints.
- [ ] **Design-system pass:** Verify the previously-audited OS/PDV/trade-in/caixa journeys still work live (click-through, not just CI-green) after the visual pass lands.
- [ ] **Coolify deploy:** Verify physical printing and QR/barcode scanning against real pilot-store hardware before go-live, not just in a browser preview or emulator.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|-----------------|
| `set_user()` anti-pattern found late in PDV/trade-in/caixa | LOW | Apply the already-proven `as_user()` context manager fix pattern; this is a known, mechanical fix from the OS audit |
| Cost/credential leak found via native Frappe Version doctype after audit-log feature ships | MEDIUM | Disable `track_changes` on the affected doctype, purge existing Version records containing sensitive data, migrate to a purpose-built audit log |
| Warranty boundary off-by-one discovered after pilot go-live | HIGH (legal/customer trust exposure) | Immediate hotfix + manual review of any warranty decisions made near the boundary during the affected window; disclose/correct with the pilot customer if a wrong decision was made |
| Design-system pass broke a previously-audited flow, caught only after deploy | MEDIUM-HIGH | Roll back the specific screen's markup change (not the whole design system), re-verify live, redeploy; this is why the live re-verification gate matters more than CI-green |
| Infra surprise (printer/QR) discovered at go-live because staging deploy was skipped | HIGH (pilot customer's first real-day experience) | Emergency on-site troubleshooting with no buffer; avoidable entirely by staging early per Pitfall 13 |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| Session anti-pattern recurrence (1, 2) | PDV/trade-in/caixa audit phase | Full-repo grep for `frappe.set_user(` outside `as_user()`/tests; zero hits |
| Version-doctype cost/credential leak (3) | Editable-fields-with-audit-log phase | Sentinel test confirms cost/margin/credential absent from Version doctype and any desk-accessible history view for non-Director roles |
| New-endpoint cost leak (4) | Editable-fields-with-audit-log phase | New sentinel test per new endpoint × role combination |
| Credential in audit log (5) | Editable-fields-with-audit-log phase | Sentinel credential value asserted absent from audit log storage/response |
| Generic patch-endpoint scope creep (6) | Editable-fields-with-audit-log phase | Test confirms endpoint rejects fields outside the explicit allow-list |
| Warranty boundary off-by-one (7) | OS.6 closure phase (90-day warranty) | Live test at day 89 (pass) and day 91 (block) against real date-comparison code |
| Caixa concurrent reconciliation (8) | PDV/trade-in/caixa audit phase | End-to-end scenario mixing all transaction types in one register session, close total verified |
| False confidence from existing test coverage (9) | PDV/trade-in/caixa audit + OS.6 closure phases | Explicit boundary-condition list written before testing; each boundary has a dedicated test |
| Unbounded audit scope (10) | PDV/trade-in/caixa audit phase | Journeys-to-cover list and done-criteria defined at phase planning, before execution |
| Design-system regression risk on monolithic component (11, 12) | Design-system application phase | Live re-click-through of previously-audited journeys after the visual pass, plus scrutiny of any loosened test assertions |
| Deploy/infra surprises with no buffer (13) | Should start earlier, in parallel with audit phases; finalized in deploy-prep phase | Coolify staging + real printer/scanner hardware validated before the dedicated deploy-prep phase begins its final cutover work |

## Sources

- `.planning/codebase/CONCERNS.md` (this repo, written 2026-09-02) — direct evidence of the `frappe.set_user()` anti-pattern, its 10 call sites, the 8+3 bugs found in the OS audit, and the explicit open gaps for warranty/check-in-edit/technician-deadline (HIGH confidence — direct codebase evidence).
- `.planning/PROJECT.md` (this repo) — milestone scope, Active requirements, and stated motivation ("muitas alterações anteriores deixaram o sistema mais confuso") (HIGH confidence — direct project context).
- Frappe Framework documentation on Document Versioning / Track Changes: https://docs.frappe.io/erpnext/user/manual/en/document-versioning and https://frappe.io/blog/erpnext-features/versioning-and-audit-trail (MEDIUM confidence — official docs confirm the Version doctype captures full before/after JSON diffs on save; the specific leak-channel risk for this project's cost/credential guard is this researcher's domain inference, not a documented Frappe security advisory).
- General brownfield-modernization sequencing risk (phased rollout vs. big-bang, ~70% failure rate cited for large-scale transformations): https://solguruz.com/blog/brownfield-development-guide/ (MEDIUM-LOW confidence — generic industry source, not Frappe/ERPNext-specific; used only to corroborate the general "stabilize-then-redesign-then-deploy" sequencing risk pattern, not any project-specific claim).
- Web search for a documented public report of the specific `frappe.set_user()` session/cookie-corruption failure mode did not surface a corroborating third-party source; this pitfall's technical grounding rests on this repo's own fixed-and-documented bug (`CONCERNS.md`, commit `1cb294a`) rather than an external reference — flagged here for transparency rather than presented as independently verified.

---
*Pitfalls research for: Frappe/ERPNext brownfield repair-shop ERP — audit/stabilize/design-system/deploy milestone*
*Researched: 2026-09-02*
