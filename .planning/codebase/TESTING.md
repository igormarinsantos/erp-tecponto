# Testing Patterns

**Analysis Date:** 2026-09-02

## Test Framework

**Frontend:**
- No unit/integration test framework (Jest, Vitest, etc.) configured
- Testing strategy: TypeScript strict mode compilation + build-time guards
- Test runner: `npm run build` (typecheck → vite build → security verification)
- Location: `frontend/` directory validation via `frontend/scripts/verify-foundation.mjs`

**Backend:**
- Custom Frappe-based test framework (not pytest-style)
- Test runner: `bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_foundation_checks`
- Location: `tecponto_app/tecponto/frontend/test_frontend_api.py`
- Execution context: Ephemeral Frappe site with MariaDB + Redis

**Run Commands:**
```bash
# Frontend validation (typecheck + build + guards)
cd frontend
npm run build

# Backend full suite (Docker-based local testing)
./scripts/test-local.sh

# Backend single run (requires Frappe site setup)
bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_foundation_checks

# Reset and re-run backend tests
TECPONTO_LOCAL_RESET=1 ./scripts/test-local.sh
```

## Test File Organization

**Location:**
- Frontend: No test files. Validation happens at build time.
- Backend: Single consolidated test file at `tecponto_app/tecponto/frontend/test_frontend_api.py`

**Naming:**
- Test modules: `test_*.py` pattern
- Test functions: `run_*_checks()` for major test suites (e.g., `run_foundation_checks()`, `run_budget_presentation_checks()`)
- Helper functions: `_check_*()` for specific test scenarios (e.g., `_check_company_identity()`, `_check_sensitive_guard()`)
- Fixture functions: `_find_or_create_*()` and `_ensure_*()` patterns

**Test File Structure:**
```
tecponto_app/tecponto/frontend/test_frontend_api.py
  │
  ├─ run_foundation_checks()              # Main entry point for foundation suite
  │   ├─ Ensures Frappe bootstrap
  │   ├─ Creates fixture users by role
  │   ├─ Calls all dependent test suites
  │   └─ Returns aggregated results
  │
  ├─ run_*_checks()                       # Major test suites
  │   ├─ run_technician_assignment_checks()
  │   ├─ run_diagnosis_handoff_checks()
  │   ├─ run_budget_presentation_checks()
  │   ├─ run_device_credential_non_leak_checks()
  │   ├─ run_service_catalog_checks()
  │   └─ ... (many more)
  │
  ├─ _check_*()                           # Specific scenario checks
  │   ├─ _check_company_identity()
  │   ├─ _check_sensitive_guard()
  │   ├─ _check_director_financial_guard()
  │   └─ ... (many more)
  │
  └─ _find_or_create_*() / _ensure_*()   # Fixture helpers
      ├─ _find_or_create_user(role)
      ├─ _ensure_default_test_cash_session()
      └─ _ensure_pos_demo_records()
```

## Frontend Validation Strategy

**Typecheck:**
- TypeScript strict mode compilation via `tsc --noEmit`
- Enforces type safety on all source code
- Catches type errors before build

**Build:**
- Vite build process compiles React + Tailwind CSS
- Generates optimized `app.js` and `app.css` in `tecponto_app/public/frontend/assets/`
- Verifies no syntax errors in bundled output

**Security Guards (verify-foundation.mjs):**
Location: `frontend/scripts/verify-foundation.mjs`

The build script performs four critical security checks:

1. **Required Build Files Check:**
   - Verifies presence of `app.js` and `app.css` in build output
   - Fails if build artifacts are missing

2. **Design Token Verification:**
   - Scans `frontend/src/styles/tokens.css` for required CSS custom properties:
     - `--tp-bg`, `--tp-panel`, `--tp-orange`, `--tp-green`, `--tp-blue`, `--tp-purple`, `--tp-amber`, `--tp-red`
   - Ensures design system tokens are complete

3. **Forbidden Frontend Terms Scan:**
   - Searches all TypeScript/CSS source files for sensitive financial terms:
     - `"valuation_rate"`, `"buying_rate"`, `"purchase_rate"`, `"gross_profit"`, `"commission"`, `"stock_value"`
   - **Whitelisted exceptions** (permitted only in specific files):
     - `commission` term: Allowed in `frontend/src/api/earnings.ts` (technician earnings view)
     - `commission` term: Also allowed as feature flag `technician_commissions_enabled` (boolean only, never numeric)
     - `valuation_rate` term: Allowed in `frontend/src/RegistryEditorModal.tsx` and `frontend/src/api/types.ts` (Director-only registry)
     - `cost`, `gross_profit` terms: Allowed in `frontend/src/api/serviceOrders.ts` and `frontend/src/App.tsx` (Director financial views)
   - Throws error if any forbidden term appears outside whitelist
   - Error message format: `"Termo sensível no front ({term}): {file}"`

4. **Service Order Workflow Validation:**
   - Verifies all required workflow stages are hardcoded in component:
     - `"Entrada"`, `"Diagnóstico e orçamento"`, `"Aprovação"`, `"Execução"`, `"Retirada"`
   - Checks that all service order actions remain connected:
     - `serviceOrders.saveDiagnosis`
     - `serviceOrders.completeDiagnosis`
     - `serviceOrders.addBudgetLine`
     - `serviceOrders.decideBudget`
     - `serviceOrders.setPartOutcome`
     - `serviceOrders.collectPayment`
     - `serviceOrders.completePickup`

**Verification Approach:**
```javascript
// Example: Search for forbidden terms with whitelisted exceptions
const forbiddenFrontendTerms = [
  "valuation_rate",
  "buying_rate",
  "purchase_rate",
  "gross_profit",
  "commission",
  "stock_value",
];

for (const file of sourceFiles) {
  const body = readFileSync(file, "utf8");
  for (const term of forbiddenFrontendTerms) {
    // Skip permitted locations
    if (term === "commission" && file === permittedOwnEarningsApi) continue;
    if (term === "valuation_rate" && file === permittedDirectorRegistryEditor) continue;
    if (["cost", "gross_profit"].includes(term) && file === permittedDirectorFinancialApi) continue;

    if (body.includes(term)) {
      throw new Error(`Termo sensível no front (${term}): ${file}`);
    }
  }
}
```

## Backend Test Structure

**Test Suite Organization:**

Foundation tests are organized hierarchically:

```
run_foundation_checks()
  ├─ Setup & Bootstrap
  │   ├─ ensure_frontend_foundation()
  │   ├─ Create users by role
  │   └─ Initialize default cash session
  │
  ├─ Core Permission Guards (run first)
  │   ├─ run_user_access_control_checks()
  │   ├─ run_user_management_api_checks()
  │   └─ run_administrative_center_checks()
  │
  ├─ Foundation API Checks
  │   ├─ _check_company_identity()
  │   ├─ _check_role_panels()
  │   ├─ _check_service_order_api()
  │   ├─ _check_sensitive_guard()
  │   └─ _check_dashboard_metrics()
  │
  ├─ Workflow & Business Logic
  │   ├─ run_technician_assignment_checks()
  │   ├─ run_diagnosis_handoff_checks()
  │   ├─ run_budget_presentation_checks()
  │   ├─ run_os2_checkin_choice_checks()
  │   ├─ run_os3_cohesive_diagnosis_and_budget_checks()
  │   ├─ run_os4_approval_and_quotes_crm_checks()
  │   └─ run_os5_workflow_automations_checks()
  │
  ├─ Financial & Operational
  │   ├─ run_technician_budget_leak_checks()
  │   ├─ run_budget_presentation_checks()
  │   ├─ run_technician_commission_checks()
  │   ├─ run_cash_session_checks()
  │   └─ run_service_order_cash_checks()
  │
  ├─ Public & Portal Features
  │   ├─ run_public_tracking_checks()
  │   ├─ run_public_acceptance_checks()
  │   ├─ run_tracking_lifecycle_checks()
  │   └─ run_unified_portal_checks()
  │
  ├─ Data & Asset Management
  │   ├─ run_product_category_checks()
  │   ├─ run_product_variant_checks()
  │   ├─ run_service_catalog_checks()
  │   └─ run_tradein_frontend_checks()
  │
  └─ [Commit DB and run dependent suites]
      ├─ run_action_request_checks()
      ├─ run_notification_checks()
      ├─ run_daily_action_checks()
      └─ run_cashier_mode_checks()
```

**Key Characteristics:**
- Tests are end-to-end: Call real API functions, verify behavior, check database state
- No mocking of Frappe framework itself; tests run against real ORM/database
- Database commits between major test groups to isolate transaction scope
- User context switching: Tests use `frappe.set_user()` to verify role-based access
- Fixture creation: Tests create minimal documents needed for each scenario
- Cleanup: Implicit via test isolation; fixture data is scoped to test execution

## Test Structure Pattern

**Typical Test Function:**
```python
def run_technician_assignment_checks(manager: str, attendant: str, technician: str) -> dict:
	"""Test that technicians can be properly assigned to service orders."""
	previous_user = frappe.session.user
	try:
		# 1. Setup: Create fixture data
		service_order = frappe.new_doc("Service Order")
		service_order.update({
			"customer": customer,
			"attendant": attendant,
		})
		service_order.insert()

		# 2. Execute: Call API function
		frappe.set_user(attendant)
		result = assign_service_order(
			name=service_order.name,
			technician=technician,
		)

		# 3. Assert: Verify result
		if result.get("technician") != technician:
			raise AssertionError(f"Technician não foi atribuído corretamente: {result}")

		# 4. Verify state: Check database
		updated_order = frappe.get_doc("Service Order", service_order.name)
		if updated_order.technician != technician:
			raise AssertionError(f"Service Order não persistiu a atribuição do técnico.")

		return {"passed": True, "message": "Technician assignment works"}

	except Exception as e:
		return {"passed": False, "error": str(e)}

	finally:
		frappe.set_user(previous_user)
```

**Common Patterns:**

1. **User Context Management:**
   ```python
   previous_user = frappe.session.user
   try:
   	frappe.set_user("user@example.com")
   	# Test logic here
   finally:
   	frappe.set_user(previous_user)
   ```

2. **Role Permission Checks:**
   ```python
   def _check_director_financial_guard(director: str, manager: str, technician: str, attendant: str) -> dict:
   	"""Verify that financial data is only visible to Director role."""
   	try:
   		frappe.set_user(director)
   		result = get_director_financial_summary()
   		if "cost" not in result or "margin" not in result:
   			raise AssertionError("Director should see financial data")

   		frappe.set_user(attendant)
   		result = list_service_orders()
   		if "cost" in str(result) or "margin" in str(result):
   			raise AssertionError("Attendant should NOT see cost/margin data")

   		return {"passed": True}
   	except Exception as e:
   		return {"passed": False, "error": str(e)}
   ```

3. **Fixture Creation:**
   ```python
   def _find_or_create_user(role: str) -> str:
   	"""Find existing test user or create one with specified role."""
   	email = f"test-{role}@example.local"
   	user = frappe.db.exists("User", email)
   	if user:
   		return user

   	user_doc = frappe.new_doc("User")
   	user_doc.update({
   		"email": email,
   		"first_name": role,
   		"roles": [{"role": role}],
   	})
   	user_doc.insert(ignore_permissions=True)
   	return user_doc.email
   ```

## Error Handling & Assertions

**Pattern:**
- Raise `AssertionError` with descriptive Portuguese error message
- Include context (what was expected vs what was found)
- Always use `raise AssertionError("Message here")` not `assert condition`
- Wrap checks in try-finally to ensure cleanup

**Example:**
```python
try:
	identity = get_company_identity()
	if identity["display_name"] != brand_name:
		raise AssertionError("Tecponto Settings não prevaleceu sobre o nome técnico do aplicativo.")
	if {"valuation_rate", "cost", "margin"} & set(identity):
		raise AssertionError("A projeção pública de identidade contém dado financeiro proibido.")
finally:
	settings.update(original)  # Restore original state
```

## Test Fixtures & Factories

**User Creation:**
- `_find_or_create_user(role: str) -> str`: Returns email of user with specified role
- Roles: `"Tecponto Atendente"`, `"Tecponto Tecnico"`, `"Tecponto Gestor"`, `"Tecponto Diretor"`

**Default Fixtures:**
```python
users = {
	"Tecponto Atendente": "test-attendant@example.local",
	"Tecponto Tecnico": "test-technician@example.local",
	"Tecponto Gestor": "test-manager@example.local",
	"Tecponto Diretor": "test-director@example.local",
}

# Cash session
_ensure_default_test_cash_session(users["Tecponto Atendente"])

# POS demo data
_ensure_pos_demo_records()

# Supplier for part requests
_ensure_part_request_supplier()

# Item for repairs
_ensure_part_request_repair_item()
```

**Fixture Cleanup:**
- Implicit: Tests create documents scoped to test execution
- Database rollback happens via transaction management
- Explicit cleanup in finally blocks when needed for cross-test state

## Coverage & CI Pipeline

**Frontend Coverage:**
- No code coverage percentage tracked
- All source files must pass TypeScript strict mode
- All source files scanned for forbidden terms
- Build artifacts required before any deployment

**Backend Coverage:**
- No code coverage percentage tracked
- Full integration suite runs against ephemeral Frappe site
- All major workflows (OS, POS, Warranty, etc.) have explicit test suites
- Security checks for sensitive data non-leakage are mandatory

**CI Pipeline (`.github/workflows/publish-image.yml`):**

**Stage 1: Fast Validation** (runs on every PR/push)
- Checkout repository
- Set up Node.js
- Run frontend build: `npm run build` (typecheck + build + guards)
- Python compilation check: `python3 -m compileall -q tecponto_app`

**Stage 2: Change Detection**
- Detect if runtime container image changed
- If runtime Containerfile or dependencies changed, build ephemeral image
- Otherwise, pull pre-built image from GHCR

**Stage 3: Full Frappe Integration**
- Start Docker services: MariaDB 10.6 + Redis 6.2
- Create ephemeral Frappe site
- Install ERPNext + HRMS + Tecponto app
- Run: `bench execute tecponto_app.tecponto.frontend.test_frontend_api.run_foundation_checks`
- On success: Publish image to GHCR (if on version-16 branch)

**Test Isolation:**
- Each CI run gets fresh MariaDB and Redis containers
- Site created fresh or reset via environment variable
- No cross-test state pollution

## Local Testing

**Script:** `./scripts/test-local.sh`

**Behavior:**
- Creates persistent Docker network and volumes (for speed on repeated runs)
- Bootstraps Frappe site on first run, reuses on subsequent runs
- Runs full foundation test suite via `bench execute`
- Exposes test site at `local-ci.local` (accessible from host if configured)

**Key Environment Variables:**
```bash
TECPONTO_LOCAL_RESET=1      # Discard persistent volumes and start fresh
TECPONTO_LOCAL_DETACH=1     # Run container in background, show logs tail
TECPONTO_EXPORT_FIXTURES=1  # Export fixture data after tests (for inspection)
TECPONTO_TEST_IMAGE=...     # Use custom image instead of ghcr.io published
TECPONTO_TEST_PULL=1        # Force pull latest image before running
```

**Example Usage:**
```bash
# Fresh run (reset persistent data)
TECPONTO_LOCAL_RESET=1 ./scripts/test-local.sh

# Detached mode (keep running, tail logs)
TECPONTO_LOCAL_DETACH=1 ./scripts/test-local.sh
docker logs -f tecponto-local-test-runner

# Export fixture data for debugging
TECPONTO_EXPORT_FIXTURES=1 ./scripts/test-local.sh
```

## Test Types

**Unit Tests:**
- Not used; codebase relies on integration tests instead
- Individual function logic verified via integration checks

**Integration Tests:**
- All tests in `test_frontend_api.py` are integration tests
- Test entire workflows: API → Frappe ORM → Database
- Use real Frappe document types and business logic
- Verify data persistence and state transitions

**E2E Tests:**
- Not formally implemented with a test runner
- Public portal tests (tracking, acceptance) in `run_public_tracking_checks()`, `run_public_acceptance_checks()`
- Simulate user actions and verify rendered output

**Security Tests:**
- Sensitive field non-leakage checks (financial data by role)
- Device credential masking verification
- Budget data filtering verification
- Frontend forbidden terms scanning (build-time guard)

## Common Test Scenarios

**Service Order Lifecycle:**
```python
# 1. Create service order (checkin)
service_order = create_service_order_checkin(
	customer=customer,
	device=device,
	problem_description="...",
)

# 2. Diagnose and create budget
save_technical_diagnosis(
	name=service_order.name,
	diagnosis="...",
)
add_service_order_budget_line(name=service_order.name, ...)

# 3. Approve budget
decide_service_order_budget(
	name=service_order.name,
	decision="Aprovado",
)

# 4. Execute (technician claims/completes work)
claim_service_order(name=service_order.name)
set_service_order_part_outcome(...)  # Mark parts used

# 5. Payment and pickup
receive_service_order_payment(...)
issue_os_acceptance(name=service_order.name)  # Get signature
```

**Role-Based Access Verification:**
```python
for user_email in [attendant, technician, manager, director]:
	frappe.set_user(user_email)
	try:
		result = get_service_order_detail(order_name)
		# Verify result contains only fields allowed for this role
		if "cost" in result and "Diretor" not in get_user_roles(user_email):
			raise AssertionError("Cost data leaked to non-Director")
	except frappe.PermissionError:
		# Expected for some roles on some operations
		pass
```

---

*Testing analysis: 2026-09-02*
