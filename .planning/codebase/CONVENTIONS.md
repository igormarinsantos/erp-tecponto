# Coding Conventions

**Analysis Date:** 2026-09-02

## Naming Patterns

**Files:**
- React components: PascalCase with descriptive names (`PosScreen.tsx`, `ApprovalRequestModal.tsx`, `ServiceCatalogScreen.tsx`)
- API modules: camelCase (`serviceOrders.ts`, `partRequests.ts`, `productCategories.ts`)
- Type definition modules: camelCase (`types.ts`)
- Utility/helper files: camelCase (`utils.ts`, `auth.ts`)
- Directories: kebab-case for utility directories (`src/api/`, `src/ui/`, `src/pos/`)
- Python modules: snake_case (`frontend_api.py`, `test_frontend_api.py`)
- Python test helper functions: `_check_*()` and `_ensure_*()` prefix pattern

**Functions:**
- React components: PascalCase, descriptive names that end with "Screen" or "Modal" for top-level screens
- Event handlers: `on{EventName}` pattern (e.g., `onCashierSaleCompleted`, `onToast`, `onClose`, `onCreated`)
- Conditional/guard functions: `has*()` or `is*()` or `contains*()` prefix (e.g., `hasAccumulatedApproverAuthority`, `isAuthRequiredMessage`)
- API wrapper functions: camelCase, action-oriented (e.g., `searchTechnicalBudgetServices`, `addTechnicalBudgetLine`, `convertFastServiceOrder`)
- Python module functions: snake_case with descriptive action verbs (e.g., `open_store_cash_session`, `get_service_order_detail`, `save_technical_diagnosis`)
- Python role-checking functions: `_require_*_role()` pattern (e.g., `_require_login()`, `_require_checkin_role()`, `_require_budget_edit_role()`)
- Python test helper functions: `run_*_checks()` for major test suites, `_check_*()` for specific checks

**Variables:**
- React state: camelCase (`barcode`, `scanStatus`, `customer`, `cartItems`, `completedSale`)
- Constants: UPPER_SNAKE_CASE in Python (`STATE_ENTRADA_CRIADA`, `SENSITIVE_FIELD_NAMES`, `SAFE_SERVICE_ORDER_FIELDS`)
- Type discriminators: kebab-case for enum values (e.g., `"pos_discount"`, `"pos_price_floor"`, `"Entrada criada"`)
- Request/Response types: descriptive plurals or specific suffixes (e.g., `ServiceOrderListResponse`, `BudgetItemSearchResponse`)

**Types & Interfaces:**
- React component props: `{ComponentName}Props` interface (e.g., `PosScreenProps`, `ApprovalRequestModalProps`)
- Type aliases: PascalCase, descriptive (e.g., `RolePanel`, `NavigationTarget`, `PosScanFeedback`)
- Custom error classes: Named with `Error` suffix and descriptive prefix (e.g., `AuthRequiredError`, `NoOperationalRoleError`)
- Type discriminators: specific string literals (e.g., `"atendente" | "tecnico" | "gestor" | "diretor"`)
- Record types for dynamic key-value: `Record<string, unknown>` or `Record<string, T>`

## Code Style

**Formatting:**
- Indentation: Tabs (4 spaces for Python/JavaScript per `.editorconfig`)
- Max line length: 99 characters for Python, 110 characters per Ruff config
- End of line: LF (Unix line endings)
- Final newline: Required in all files
- Trailing whitespace: Trimmed
- Character encoding: UTF-8

**Linting:**
- ESLint: Root `.eslintrc` with loose configuration — most rules are off or warning-only
- TypeScript: Strict mode enabled (`strict: true`), case-sensitive filenames required
- Ruff (Python): Selected rules: F, E, W, I, UP, B, RUF — many are ignored for Frappe compatibility
- Python formatting: Double quotes preferred per `[tool.ruff.format]` (quote-style = "double")
- Python imports: Organized at module top with absolute imports and `from __future__ import annotations`

**Comments & Docstrings:**
- Python docstrings: Triple-quoted strings on line after function signature (e.g., `"""Open the single physical drawer; sales integration arrives..."""`)
- Inline comments: Sparse; code should be self-documenting. Only comment non-obvious logic.
- Portuguese: Used in error messages, comments, and docstrings where appropriate (both Portuguese and English acceptable)

## Import Organization

**Order:**
1. `from __future__ import annotations` (Python only, must be first)
2. Standard library imports (`os`, `sys`, `json`, `re`, `datetime`, etc.)
3. Third-party imports (`frappe`, `react`, `@types/*`, etc.)
4. Local/relative imports (other modules in the app)

**Path Aliases:**
- No configured path aliases in `tsconfig.json`; use relative or absolute imports within `src/`
- Python: Absolute imports from `tecponto_app` package root (e.g., `from tecponto_app.tecponto.pending import action_for_service_order`)
- Barrel exports: Used in `src/api/index.ts` and `src/ui/index.ts` for public APIs

**Example (Python):**
```python
from __future__ import annotations

import hashlib
import json
from typing import Any

import frappe
from frappe.utils import add_days, flt

from tecponto_app.tecponto.customer import assert_existing_customer_is_complete
from tecponto_app.tecponto.pending import action_for_service_order
```

**Example (TypeScript):**
```typescript
import { useCallback, useEffect, useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { pos, type CashSessionSummary } from "./api";
import { Button, Modal } from "./ui";
import { KeyboardShortcuts } from "./pos/KeyboardShortcuts";
```

## Error Handling

**Patterns:**
- Python backend: Raise exceptions using `frappe.throw()` with user-friendly Portuguese messages; use `AssertionError` in tests with descriptive messages
- React frontend: Catch errors in try-catch blocks, check `instanceof Error` before accessing message
- API client: Custom error classes (`AuthRequiredError`, `NoOperationalRoleError`) for specific error conditions
- Error checking: Always verify error is an instance before extracting message: `error instanceof Error ? error.message : "Fallback message"`
- Message extraction: Use `extractFrappeErrorMessage()` utility to parse nested Frappe error payloads
- User feedback: Show extracted error message or generic fallback message to user via toast/alert

**Python Example:**
```python
def open_store_cash_session(opening_amount: float = 0, idempotency_key: str = "") -> dict[str, Any]:
	"""Open the single physical drawer; sales integration arrives in cash phase 4.2."""
	_require_pos_role()
	return open_cash_session(
		opening_amount=opening_amount,
		idempotency_key=idempotency_key,
		opened_by=frappe.session.user,
	)
```

**TypeScript Example:**
```typescript
try {
	const result = await pos.getCashSession();
	setCashSession(result.session);
} catch (error) {
	onToast(error instanceof Error ? error.message : "Não foi possível consultar o caixa.", "error");
}
```

## Logging

**Framework:**
- Frontend: `console.log()`, `console.error()` (no dedicated logging library)
- ESLint rule: `no-console` is warn-level only, allowing console output for debugging
- Backend: Frappe's built-in logging via `frappe.log_error()` for critical issues

**Patterns:**
- Use `console.log()` for development debugging only
- Keep production code free of logging unless it's a critical operational event
- Use Portuguese user-facing messages in error toasts
- Backend logging: Wrap critical operations in try-catch, log via Frappe if needed

## Comments

**When to Comment:**
- Explain WHY, not WHAT (code already shows WHAT)
- Document non-obvious security decisions (e.g., why a field is masked)
- Explain complex business logic not evident from code
- Mark intentional workarounds or backward-compatibility decisions

**Example:**
```python
# The registry endpoint omits this key for every role except Diretor. The
# modal may render that server-authorized, read-only value, while backend
# tests prove the key never reaches Attendente or Técnico payloads.
if term == "valuation_rate" and (file == permittedDirectorRegistryEditor or file == permittedDirectorRegistryTypes):
	continue
```

**JSDoc/TSDoc:**
- Used sparingly
- Keep docstrings for public API functions in Python
- React components: Use TypeScript interface comments only if needed beyond the props interface itself

## Function Design

**Size:**
- Functions should be small and focused (single responsibility)
- React components: Typical component is 100–300 lines; break into sub-components if larger
- Python functions: Typical function is 30–80 lines; refactor if exceeding 100 lines

**Parameters:**
- React: Use single props object (interface) rather than multiple parameters
- Python: Use type hints (`param: Type`) and positional/keyword-only parameters as appropriate
- Pass related parameters together (e.g., `{ ...filters, limit_per_column: 18 }`)

**Return Values:**
- React components: Return JSX (functional component pattern)
- Python API functions: Return `dict[str, Any]` for JSON-serializable API responses
- Functions should always return consistent types; use unions sparingly

**Example (Python API):**
```python
@frappe.whitelist()
def get_service_order_detail(name: str) -> dict[str, Any]:
	_require_frontend_role()
	# ... implementation
	return {
		"order": {...},
		"metadata": {...}
	}
```

**Example (React Component):**
```typescript
interface SaleItemsProps {
	items: PosCartLine[];
	onRemove: (index: number) => void;
	onUpdateQty: (index: number, qty: number) => void;
}

export function SaleItems({ items, onRemove, onUpdateQty }: SaleItemsProps) {
	return (
		<div>
			{items.map((item, idx) => (
				<div key={idx}>...</div>
			))}
		</div>
	);
}
```

## Module Design

**Exports:**
- API modules export an object with methods: `export const serviceOrders = { method1() { ... }, method2() { ... } }`
- UI components export function or object
- Types exported as `export type` or `export interface`
- Barrel exports in `index.ts` files for public APIs

**Example (API module):**
```typescript
export const serviceOrders = {
	detail(name: string) {
		return rpc<ServiceOrderDetailResponse>(`${API}.get_service_order_detail`, { query: { name } });
	},
	list(params: number | ServiceOrderQueryParams = 20) {
		const query = typeof params === "number" ? { limit: params } : params;
		return rpc<ServiceOrderListResponse>(`${API}.list_service_orders`, { query });
	},
	// ... more methods
};
```

**Barrel Files:**
- `src/ui/index.ts`: Exports all UI components and types
- `src/api/index.ts`: Exports all API service objects and type definitions

## React Patterns

**Hooks:**
- Use `useState` for local component state
- Use `useEffect` for side effects; always include dependency array
- Use `useCallback` for memoized event handlers
- Use `useMemo` for expensive computations
- Use `useRef` for DOM references and persistent values across renders

**Component Pattern:**
```typescript
interface MyComponentProps {
	prop1: string;
	onAction: (value: string) => void;
}

export function MyComponent({ prop1, onAction }: MyComponentProps) {
	const [state, setState] = useState(false);

	const handleAction = useCallback(() => {
		onAction("value");
		setState(!state);
	}, [state, onAction]);

	return (
		<div>...</div>
	);
}
```

**Event Handlers:**
- Named with `on{EventName}` pattern in component props
- Use `useCallback` to memoize if passed to child components
- Always check for `null` before calling (React best practice)

## Python Backend Patterns

**Module Structure:**
- Public API functions marked with `@frappe.whitelist()` decorator
- Private helpers prefixed with `_` (e.g., `_require_login()`)
- Type hints on all public functions using `from __future__ import annotations`
- Return types as `dict[str, Any]` for API endpoints

**Role-Based Access:**
- Guard functions: `_require_*_role()` pattern that raises `frappe.PermissionError` if check fails
- Applied at function entry point before any business logic
- Example: `_require_checkin_role()`, `_require_budget_edit_role()`, `_require_director_financial_access()`

**Sensitive Data Protection:**
- Define `SENSITIVE_FIELD_NAMES` set: Contains field names that should never leak to non-Director roles
- Define `SAFE_*_FIELDS` tuples: Whitelist of fields safe to return for each role (e.g., `SAFE_SERVICE_ORDER_FIELDS`)
- Backend validates and filters before returning payload to frontend

**Example:**
```python
SENSITIVE_FIELD_NAMES = {
	"cost",
	"margin",
	"commission",
	"gross_profit",
	"valuation_rate",
}

SAFE_SERVICE_ORDER_FIELDS = (
	"name",
	"customer",
	"entry_date",
	"technician",
	# ... but NOT margin, cost, etc.
)

def get_service_order_detail(name: str) -> dict[str, Any]:
	_require_frontend_role()
	order = frappe.get_doc("Service Order", name)
	# Backend filters to SAFE_SERVICE_ORDER_FIELDS before returning
	return {"order": {field: order.get(field) for field in SAFE_SERVICE_ORDER_FIELDS}}
```

## UI Component Patterns

**Button Variants:**
- `"primary"`: Orange background, call-to-action
- `"secondary"`: Field-like background, default button
- `"ghost"`: No background, text-only, hover reveals background
- `"danger"`: Red tint, destructive action

**CSS Tokens:**
- Use Tailwind tokens with `--tp-*` prefix for theming
- Colors: `--tp-bg`, `--tp-panel`, `--tp-orange`, `--tp-green`, `--tp-blue`, `--tp-purple`, `--tp-amber`, `--tp-red`
- Border: `--tp-border`
- Text colors: `--tp-text`, `--tp-muted`, `--tp-subtle`, `--tp-ink` (darkest)
- Utilities: `--tp-field` (field background)

**Example (Component with Tailwind):**
```typescript
export function Button({ variant = "secondary", className, ...props }: ButtonProps) {
	return (
		<button
			className={cx(
				"rounded-control px-4 text-sm font-semibold",
				"focus:outline-none focus:ring-2 focus:ring-tec-orange/70",
				variants[variant],
				className,
			)}
			{...props}
		/>
	);
}
```

---

*Convention analysis: 2026-09-02*
