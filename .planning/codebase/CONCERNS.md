# Codebase Concerns

**Analysis Date:** 2026-09-02

## Tech Debt

**Monolithic Frontend Component (App.tsx):**
- Issue: Single React component contains 9500+ lines of code spanning all major UI workflows
- Files: `frontend/src/App.tsx`
- Impact: Extremely difficult to maintain, test, and refactor; high cognitive load; bundle size warning
- Fix approach: Break into feature-based modules (Services, Orders, POS, Administrative, etc.); use dynamic imports for code-splitting to address build warning about 861.62 kB chunk size (need to reach <500 kB per chunk)

**Large Backend API Module (api.py):**
- Issue: Single module contains 5306 lines covering multiple domains (service orders, POS, financial, tracking, product management)
- Files: `tecponto_app/tecponto/frontend/api.py`
- Impact: Mixed responsibilities make it hard to locate related code; changes in one area risk regression in another
- Fix approach: Extract domain-specific modules (e.g., `service_order_api.py`, `pos_api.py`, `financial_api.py`, `product_api.py`) with clear interfaces; keep `api.py` as a facade layer for endpoint decoration

**Accumulated Test Suite Size:**
- Issue: Main test file `test_frontend_api.py` has 8745 lines; difficult to navigate and maintain
- Files: `tecponto_app/tecponto/frontend/test_frontend_api.py`
- Impact: Hard to add new tests without duplicating setup logic; slow local test runs if full suite executed
- Fix approach: Split into domain-specific test modules (`test_service_order_api.py`, `test_pos_api.py`, etc.) with shared fixtures in `conftest.py`

---

## Known Bugs

**Session Corruption via frappe.set_user() — ✅ FIXED (but monitor for regression)**
- Symptom: Previously, any privileged operation would silently log out the user on next request with "User None not found"
- Files: `tecponto_app/tecponto/permissions.py` (helper `as_user()`), `tecponto_app/tecponto/acceptance.py`, `tecponto_app/tecponto/financial.py`, `tecponto_app/tecponto/frontend/pos.py`, `tecponto_app/tecponto/tracking.py`, `tecponto_app/tecponto/frontend/api.py`
- Root cause: `frappe.set_user()` corrupts `frappe.session.sid` in the response cookie, making it invalid
- Workaround: None; fix is mandatory
- Status: Fixed via `as_user()` context manager (2026-09-01, block A in AUDITORIA_SISTEMA.md). **Monitor:** Test suite includes `test_frontend_api.py` lines 275+, 462+, etc. that still use `frappe.set_user()` (acceptable in test setup code, not production). Production code now uses `as_user()` exclusively for privilege escalation.

**8 Workflow/Approval/Acceptance Bugs — ✅ ALL FIXED**
- See `AUDITORIA_SISTEMA.md` items #1-#8 for full details (bugs: approval evidence storage, cost field exposure, session corruption, kanban state bypass, timezone date display, status indicator timing, quote sent state, pickup loop)
- All 8 bugs identified during end-to-end testing (2026-09-01) and fixed in 6 commit blocks
- Fixed blocks: `1cb294a`, `9fcaab3`, `36ed156`, `443fd3d`, `d7bc397`, `14e3999`
- Additional pre-existing CI-blocking bugs also fixed

---

## Security Considerations

**Cost/Margin Guard Implementation (Verified Safe):**
- Risk: Non-Diretor roles viewing cost, margin, or profit data
- Files: `tecponto_app/tecponto/frontend/api.py` (SENSITIVE_FIELD_NAMES, `contains_sensitive_field()` validation), test file `test_frontend_api.py` (cost guard tests at lines 586, 794, 956, 983, 1421, 1490, 1817, 1916, 1971, 2115, 2335, 2470, 2575, 2857, 2981, 3083, 3158, 3216)
- Current mitigation: Test suite includes sentinels (forbidden values like 41.23, BUDGET_COST_GUARD_VALUATION) that are checked in every API response to catch accidental leakage
- Recommendations: The guard is solid (uses deny-list of field names + pattern matching). Continue enforcing in CI. Consider periodic security audit of API endpoints to verify no new cost fields are being added without going through this guard.

**Device Credential Masking (Verified Safe):**
- Risk: Device password/PIN/pattern exposed in API payloads or frontend UI
- Files: `frontend/src/api/types.ts` (has_device_access_credential boolean), `frontend/src/CheckinWizard.tsx` (input handling), backend service_order (stores encrypted credential)
- Current mitigation: Frontend displays only boolean flag `has_device_access_credential`, never the actual credential value. When credential needs to be revealed (password change dialog), it's via explicit `window.prompt()` interaction, not auto-displayed.
- Recommendations: Verify in production that credentials never appear in:
  - OS detail API responses (check `get_service_order_detail()` never includes the field)
  - WhatsApp/print communications (review `_send_order_communication()` and print format references)
  - Public tracking links (verify `decide_public_tracking_budget()` doesn't expose credential)
  - Logs/audit trails (no explicit audit-log testing for credential reveal yet)

**Workflow Lifecycle Locks in Backend (Verified Safe):**
- Risk: Workflow state transitions (6 main gates) only enforced in React, allowing direct API bypass
- Files: `tecponto_app/tecponto/service_order/workflow.py`, `tecponto_app/tecponto/frontend/api.py` (move_service_order, apply_workflow calls)
- Current mitigation: Frappe's native workflow engine validates all transitions server-side; backend never trusts frontend state. Gates for Kanban are validated in `move_service_order()`.
- Recommendations: Already in place and verified in testing. No immediate issue.

**SQL Injection / Parameterization (Generally Safe):**
- Issue: `api.py` line 1061 uses f-string in SQL but parameters are safe
- Files: `tecponto_app/tecponto/frontend/api.py:1061`
- Inspection: `where` variable is built from hardcoded conditions and escaped via `frappe.db.escape()` or passed as named parameters (e.g., `%(warehouse)s`). Safe.
- Recommendations: Continue using `frappe.db.sql()` with named parameter dicts; avoid inline string interpolation for user input.

---

## Performance Bottlenecks

**Large Frontend Bundle (211.41 kB gzipped, uncompressed 861.62 kB):**
- Problem: Single app.js chunk exceeds 500 kB uncompressed; affects first paint time
- Files: `frontend/src/App.tsx` (9500 lines), `frontend/vite.config.ts`
- Cause: Monolithic component structure + missing code-splitting
- Improvement path:
  1. Split App.tsx into logical route components (ServiceOrderModule, POSModule, AdministrationModule, etc.)
  2. Use React.lazy() + Suspense for route-based code-splitting
  3. Configure vite with `build.rollupOptions.output.manualChunks` to target <500 kB chunks
  4. Audit and defer non-critical imports (e.g., heavy icon libraries, formatting utilities)

**Database Query Patterns:**
- Issue: Some endpoints use `frappe.get_all()` without explicit `limit_page_length` parameter
- Files: `tecponto_app/tecponto/frontend/api.py` (lines 1035, 1037, 2096, 2100-2101, 2114, and others)
- Impact: Could return unbounded result sets on large datasets; risk of timeouts or memory exhaustion in production
- Safe cases: Most `get_all()` calls already have limits (e.g., `pluck="name", limit_page_length=100` at line 2096)
- Improvement: Audit all `get_all()` calls and add explicit limits where missing; add comments explaining the pagination strategy

**No Pagination Guidance in API Design:**
- Issue: Many list-returning endpoints don't document or enforce page size limits
- Impact: Clients could accidentally request millions of records
- Improvement: Add default `limit=100` to all list endpoints; provide offset/limit parameters for clients that need more

---

## Fragile Areas

**OS Workflow State Management (Post-Audit Risk):**
- Files: `tecponto_app/tecponto/service_order/workflow.py`, `frontend/src/ServiceOrderFlows.tsx` (approval, pickup modals)
- Why fragile: Workflow transitions depend on precise state machine rules. Audit found 4 separate state-transition bugs (items #1b, #4, pickup loop, kanban).
- Safe modification: Any change to workflow gates must be:
  1. Reviewed against `REGUA_PRODUTO.md` (expected journeys) and `FRENTE_OS_plano_aprovado.md` (stage design)
  2. Tested end-to-end in each role (Atendente, Técnico, Gestor, Diretor)
  3. Verified against CI test suite (especially `run_*_checks()` functions in test_frontend_api.py)
- Test coverage: Good coverage in test suite (`run_service_order_creation_checks()`, `run_os_status_checks()`, `run_no_repair_pickup_checks()`, etc.), but only primary flow paths tested in audit; edge cases (multi-technician dispatch, parallel approvals, cancellations) less certain

**Acceptance/Evidence Collection (Post-Audit Risk):**
- Files: `tecponto_app/tecponto/acceptance.py`, `frontend/src/ServiceOrderFlows.tsx` (PickupModal), `tecponto_app/tecponto/tracking.py`
- Why fragile: Audit found bugs in evidence storage visibility, physical acceptance state recovery, and digital link forging. Complex triple-path design (selfie/link/physical).
- Safe modification: Any change to acceptance must verify all 3 paths end-to-end:
  1. Digital link (customer self-confirmation via public tracking URL)
  2. Physical file (employee collects signed PDF/image locally, archives to database)
  3. Selfie/biometric (future; framework exists but not fully wired)
- Test coverage: `test_frontend_api.py` includes tests for entry/exit acceptance and evidences, but only "happy path" tested in audit; rollback/re-acceptance scenarios untested

**Multi-Role Permission Filters (Fragile Boundary):**
- Files: `tecponto_app/tecponto/permissions.py`, `tecponto_app/tecponto/frontend/api.py` (scope filters)
- Why fragile: Technician scope filtering uses `is_restricted_technician()` check; if this is bypassed or misapplied, technicians could access all OS instead of only their own
- Safe modification:
  1. All `get_all()` calls that return Service Order must explicitly include `service_order_scope_filters()` (lines 1035, 1037)
  2. List endpoints that skip this (e.g., Director-only views) must call `_require_director_role()` first
  3. Test coverage exists (`test_frontend_api.py:797-810` checks technician doesn't see others' OS) but should be extended to spot-check every new endpoint returning OS
- Test coverage: Moderate; permission guard tests exist but not comprehensive for all endpoints

---

## Scaling Limits

**Database Connection Pool / Frappe Session Density:**
- Current capacity: Tested with ~5504 OS records locally (per AUDITORIA_SISTEMA.md); CI environment creates site from scratch each run
- Limit: Unknown; depends on MariaDB pool size, Redis capacity, and Frappe bench configuration
- Scaling path: Load test with production-like data volume before pilot; monitor connection pool exhaustion in early production

**Storage for Evidence Files (Photos, PDFs, Signatures):**
- Current capacity: Entry photos and acceptance files stored in Frappe's file backend; local testing hasn't hit storage ceiling
- Limit: Not explicitly documented; depends on available disk and Frappe file storage configuration
- Scaling path: Plan for cleanup/archival of photos after legal retention period (marked as "verificar com advogado" in STATUS); implement retention policy before scaling to high OS volume

**Real-Time Multi-Technician Dispatch:**
- Current design: Pull/Dispatch mode uses polling and workflow state; no WebSocket or real-time notifications
- Limit: Assumes small technician team (2-3, based on test names like `active_technicians: 2`)
- Scaling path: If adding >10 technicians, implement real-time notification layer (WebSocket or Server-Sent Events) to notify available technicians immediately when work is pulled

---

## Fragile Areas (Continued)

**OS.6 Execution/Retirada Stage — Partially Verified:**
- Files: `frontend/src/ServiceOrderFlows.tsx` (PickupModal, lines 132-382), `tecponto_app/tecponto/frontend/api.py` (issue_acceptance, submit_pickup, etc.)
- What's confirmed: Basic digital link + physical acceptance flows work end-to-end; warranty 90-day default applied; pickup date recorded
- What's NOT confirmed (from STATUS_PROJETO.md items still open):
  1. **90-day warranty end-to-end not confirmed** — test creates warranty but no explicit verification that 90 days is enforced correctly
  2. **Technician-set deadline field not confirmed** — expected per REGUA_PRODUTO.md, but `estimated_deadline` only appears at service-line level in budget composition, not as OS-wide deadline set by technician. **CLARIFICATION NEEDED:** Is this by design (per-service deadlines) or incomplete?
  3. **Editing check-in info after creation not confirmed** — no explicit UI or API endpoint found for re-editing check-in fields post-creation (contact_name, contact_phone, device_access_credential, etc.). Field appears frozen post-creation.
- Risk: If OS.6 is considered "done" without verifying these 3 items, the feature is incomplete
- Recommendation: Run explicit end-to-end test for: (1) create OS, advance to Retirada, verify warranty applies and 90-day window is enforced; (2) open OS detail in Diagnosis stage, set technician deadline, verify it persists and displays; (3) open completed OS, attempt to edit contact info, verify behavior (should be read-only or audit-logged if editable)

**Incomplete Check-in Modification Support:**
- Files: `frontend/src/CheckinWizard.tsx`, `tecponto_app/tecponto/frontend/api.py` (create_service_order)
- Issue: STATUS_PROJETO.md lists "Editar info do check-in depois de criado" as a "próximo passo" but no code found
- Impact: If customer phone number or contact info is wrong, staff must create a new OS or manually patch the database
- Recommendation: Add a backend API to edit (customer contact info, device access credential masking, attendance notes) with audit logging of who changed what and when

---

## Missing Critical Features

**Contact Field Separation — Implemented but UX Unverified:**
- Feature: `order_contact` (specific to this OS) vs. registered customer contact
- Implementation: Fields exist in `service_order.json` (`contact_name`, `contact_phone`), `api.py`, `App.tsx`
- Status: Marked in STATUS_PROYECTO as "implementado, verificar UX no fluxo real"
- Risk: If UI doesn't clearly show which contact is being used, staff may not realize they're using outdated info
- Recommendation: Visual indicator (e.g., "Cliente cadastrado: João Silva / Contato desta OS: (81) 98765-4321") in OS detail

**Complementary Information Collection — Decision Pending:**
- Feature: Fields for "type", "preference", "origin" of OS
- Status: Marked as "DECISÃO PENDENTE: recolher opcional ou remover"
- Risk: If these fields are optional, they may be ignored in practice; if required, they're friction
- Recommendation: Decide based on product roadmap; if including, make mandatory and ensure workflow validation enforces them

---

## Test Coverage Gaps

**Warranty 90-Day End-to-End:**
- What's not tested: Full cycle of creating a service order, completing it with a 90-day warranty, then attempting to create a warranty OS 91 days later (should fail)
- Files affected: `tecponto_app/tecponto/service_order/policies.py` (warranty validation), test file
- Priority: HIGH — warranty is a legal commitment; miscalculation could result in disputes
- Fix: Add test that:
  1. Creates original OS, marks as delivered with `pickup_date` today
  2. Computes warranty expiry as today + 90 days
  3. Attempts to create warranty OS on day 91 (should fail)
  4. Creates warranty OS on day 89 (should succeed)

**Multi-Technician Dispatch Handoff:**
- What's not tested: Scenario where Gestor assigns to Tech A, Tech A declines (or doesn't start), Gestor reassigns to Tech B
- Files affected: `tecponto_app/tecponto/service_order/assignment.py`, workflow rules
- Priority: MEDIUM — affects day-to-day operations
- Fix: Add test for reassignment after initial assignment

**Public Tracking Link Expiry & Revocation:**
- What's not tested: Scenario where customer link is issued but then order status changes (e.g., approved via other channel); verify old link no longer works or redirects gracefully
- Files affected: `tecponto_app/tecponto/tracking.py`, `tecponto_app/tecponto/frontend/api.py` (public endpoints)
- Priority: MEDIUM — stale links could confuse customers
- Fix: Add test that issues link, transitions status, then tries to use link (should handle gracefully)

---

## Dependencies at Risk

**Frappe Framework Lock to v16:**
- Risk: Framework is pinned to v16; newer versions (v17+) may have breaking changes
- Impact: Inability to upgrade for security patches; accumulating technical debt
- Mitigation: ERPNext v16 is stable LTS; no immediate risk, but plan migration path
- Migration plan: Review breaking changes in v17+ changelog; test against new version in staging before committing to upgrade

**React 18 and TypeScript — Current Versions:**
- Risk: Build completes with no errors; TypeScript strict mode appears enforced (no `any` types visible)
- Impact: Low risk; dependencies are up-to-date
- Mitigation: Continue monitoring npm audit for vulnerabilities; run `npm audit` before each production deployment

---

## Architectural Constraints & Anti-Patterns

**Frontend State Management Anti-Pattern:**
- What happens: Each screen component manages its own state with `useState`; no centralized state machine or Redux-like pattern
- Why it's wrong: Difficult to coordinate between screens (e.g., if OS is updated in one screen, other screens don't auto-refresh unless explicitly refetched)
- Example: `ServiceOrderFlows.tsx` line 142 has local state for `acceptance`; if user navigates away and back, state is lost, leading to "button still disabled" bug (item #8 in AUDITORIA_SISTEMA.md, now fixed via server-side fallback)
- Do this instead: Consider React Query or SWR for server-state caching and synchronization; ensures consistent state across all screens without manual refetching

**Deeply Nested Conditional Rendering:**
- What happens: App.tsx contains deeply nested ternary operators and conditionals (e.g., checking user role, OS state, feature flags in sequence)
- Why it's wrong: Hard to follow the logic; easy to accidentally break one path when refactoring another
- Example: `App.tsx` diagnostic section rendering depends on `detail.diagnosis.completed_at`, status flags, and role checks all in one expression
- Do this instead: Extract rendering logic into named helper functions (e.g., `renderDiagnosisSection()`) that clearly separate concerns

---

## Known Issues Summary

| Issue | Severity | Status | Commit(s) | Notes |
|-------|----------|--------|-----------|-------|
| Session corruption (frappe.set_user) | CRITICAL | FIXED | 1cb294a | Monitor for regression; test suite covers |
| Approval impossible (manual channels) | CRITICAL | FIXED | 9fcaab3 | File input added to approval form |
| Approval without evidence (Link channel) | CRITICAL | FIXED | 9fcaab3 | Backend now validates channel permission |
| Aceite invisível na tela | HIGH | FIXED | 36ed156 | API now returns acceptance summary |
| Retirada loop impossível | HIGH | FIXED | 36ed156 | Frontend now checks server state on remount |
| Kanban sem técnico | MEDIUM | FIXED | 443fd3d | Now blocks Diagnóstico without technician |
| Datas atrasadas (timezone) | MEDIUM | FIXED | d7bc397 | Centralized date parser handles local interpretation |
| Status cosmético errado | LOW | FIXED | 14e3999 | Conditions corrected for visibility |
| CI test suite broken | CRITICAL | FIXED | ab29af3 | 3 pre-existing bugs found & fixed |
| Technician deadline unclear | MEDIUM | OPEN | N/A | Verify design: OS-level or service-level? |
| Check-in editing missing | MEDIUM | OPEN | N/A | No UI to re-edit post-creation |
| Warranty 90-day not fully tested | MEDIUM | OPEN | N/A | Need end-to-end + expiry edge case tests |

---

*Concerns audit: 2026-09-02*
