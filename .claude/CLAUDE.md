<!-- GSD:project-start source:PROJECT.md -->

## Project

**Tecponto ERP**

ERP para assistências técnicas de celular, sobre Frappe/ERPNext v16 (Python) + React/Vite/TypeScript. Cobre o ciclo completo de uma ordem de serviço (OS) — check-in, diagnóstico, orçamento, aprovação, execução, retirada — mais PDV, trocas/avaliações de usados, garantias e caixa. Em produção, com um piloto real na loja "Rafacel". Não é greenfield: já tem fundação, papéis (Atendente/Técnico/Gestor/Diretor), aceite por link/selfie, rastreio público, CI em 3 estágios e deploy via Coolify.

**Core Value:** O balcão consegue rodar o dia a dia real — check-in até retirada, PDV, trocas/garantias, caixa — sem quebrar no meio e sem vazar dado sensível (custo/margem, senha do aparelho). Confiança operacional vem antes de polimento visual.

### Constraints

- **Segurança (não-negociável, `CLAUDE.md`)**: Atendente/Gestor/Técnico nunca veem custo/margem/lucro — só o Diretor, via endpoint dedicado. O backend nunca serializa custo pros outros papéis, não basta esconder no frontend.
- **Segurança**: senha/PIN/padrão do aparelho é dado sensível, armazenamento criptografado, sempre mascarado no frontend, revelado só sob ação intencional auditada. Testado continuamente com valores-sentinela.
- **Segurança**: as 6 travas de ciclo de vida da OS, gates de papel e validação de aceite biométrico/físico vivem no motor Python — o React é só apresentação.
- **Processo (`CLAUDE.md`)**: tarefas pequenas e atômicas, testar comportamento real de ponta a ponta antes de declarar pronto, commit isolado por tarefa, reiniciar servidor local após mudança Python (`--noreload`), CI de 3 estágios é a verdade final.
- **Design**: raciocinar hierarquia visual antes de construir; polimento estético em passada única no fim, não tela por tela durante a fase funcional.
- **Jurídico**: termos e aceite físico precisam de revisão de advogado antes do uso pra valer (ainda pendente, per `STATUS_PROJETO.md`).
- **Ambiente local**: Docker no Windows/WSL2 é instável (containers recebem shutdown normal sozinhos) — mitigado com `scripts/dev-local-server.sh`, mas testes locais longos podem precisar reiniciar db/redis no meio.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- **Python** 3.14.4 - Backend logic, Frappe/ERPNext framework, business rules
- **TypeScript** 5.7.2 - React frontend application, type-safe UI code
- **JavaScript** (React/JSX) - Frontend rendering and interactivity
- **HTML/CSS** - Web templates and styling foundations
- **Jinja2** - Frappe server-side templating for print formats and pages

## Runtime

- **Python** 3.14.4 (backend server)
- **Node.js** v20.20.2 (frontend development and build)
- **Frappe Bench** (development/deployment framework for Frappe apps)
- **npm** 10.8.2 - JavaScript/Node dependencies (`frontend/package.json`, `frontend/package-lock.json`)
- **pip** - Python dependencies (via Frappe bench, managed centrally)
- **Lockfile:** `frontend/package-lock.json` (present and committed)

## Frameworks

- **Frappe Framework** v16.0.0 (Python backend) - ERP framework, ORM, API layer, permission system
- **ERPNext** v16 (Frappe module) - Standard ERP functionality (inventory, accounting, sales)
- **HRMS** (Frappe module) - Human Resource Management System
- **React** 18.3.1 - UI component library, state management
- **Vite** 8.1.3 - Frontend build tool, dev server (port 5173 by default)
- **TypeScript** 5.7.2 - Type checking, strict mode enabled
- **Tailwind CSS** 3.4.17 - Utility-first CSS framework
- **PostCSS** 8.4.49 - CSS processing
- **Autoprefixer** 10.4.20 - Browser compatibility prefixes
- **@fontsource/space-grotesk** 5.2.10 - Custom font (Space Grotesk)
- **lucide-react** 0.468.0 - Icon component library

## Key Dependencies

- **python-barcode** 0.16.1 (Python) - Barcode generation for POS/product labels
- **Frappe Framework 16.0.0** - Entire backend stack is built on Frappe
- **MariaDB** 10.6 - Primary relational database (`db_type: mariadb` in site config)
- **Redis** 6.2+ - Caching, task queues, WebSocket support (cache, queue, socketio)
- **@vitejs/plugin-react** 6.0.3 - React/JSX plugin for Vite
- **@types/react** 18.3.18 - React TypeScript definitions
- **@types/react-dom** 18.3.5 - React DOM TypeScript definitions

## Configuration

- Development mode enabled (`developer_mode: 1` in site config)
- Encryption key configured (database encryption at rest)
- Multi-app installation: `frappe`, `erpnext`, `hrms`, `tecponto_app`
- **Type:** MariaDB
- **Host:** Configurable per deployment (default: localhost)
- **Credentials:** Per-site database user (`_4b49d3063d2d4f46` pattern for isolation)
- **Connection:** TCP/IP, port 3306
- **Redis Cache:** `redis://redis-cache:6379` (production), localhost:6379 (dev)
- **Redis Queue:** `redis://redis-queue:6379` (production), localhost:6379 (dev)
- **Redis SocketIO:** `redis://redis-queue:6379` (for WebSocket communication)
- `vite.config.ts` - Frontend build output to `../tecponto_app/public/frontend/`
- `tailwind.config.ts` - Tailwind CSS with design token system (custom color vars)
- `tsconfig.json` - TypeScript strict mode, ES2020 target
- `pyproject.toml` - Python project metadata, Ruff linting rules

## Frontend Build & Tooling

- **ESLint** - JS/TS linting (`.eslintrc`, rules relaxed for legacy Frappe globals)
- **ruff** - Python linting and formatting (110 char line length, tabs for indentation)
- **prettier** - Code formatting (via pre-commit hooks)
- **pre-commit** - Git hook framework for automated checks
- Target: ES2020
- Strict mode enabled
- React JSX factory: `react-jsx`
- Module resolution: Node
- Base path: `/assets/tecponto_app/frontend/`
- Output directory: `../tecponto_app/public/frontend`
- Source maps enabled in production builds
- CSS bundled to single `assets/app.css`
- JS bundled to single `assets/app.js`

## Platform Requirements

- WSL Ubuntu (primary dev environment at `\\wsl$\Ubuntu\home\usuario\frappe-bench\`)
- Python 3.14.4+
- Node.js v20+
- npm 10+
- Git
- Frappe bench CLI (installed in virtual env)
- **Container:** Docker (Coolify-compatible)
- **Base Image:** frappe/frappe:version-16 (Debian-based)
- **Orchestration:** Coolify or Docker Compose
- **Reverse Proxy:** Nginx (Frappe standard)
- **Process Manager:** Gunicorn (backend), Node.js (frontend dev server replaced by static assets in prod)
- MariaDB 10.6 (external service)
- Redis 6.2+ (external service)
- Chromium/headless-shell (for PDF generation and print formats)

## Notable Technical Choices

- Inherits Frappe's permission system, document model, and API conventions
- Uses Frappe's `frappe.enqueue()` for async job processing
- RPC-based API pattern (`/api/method/...`) for backend calls
- Custom React frontend for `tecponto_app` instead of Frappe's built-in web interface
- Communicates via Frappe RPC endpoints
- Handles complex workflows (service orders, POS, trades) in React
- Backend: Pure Frappe/Python (business logic, data, security)
- Frontend: Pure React/TypeScript (UI/UX, state management)
- Glue: REST/RPC API over HTTP/FormData

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- React components: PascalCase with descriptive names (`PosScreen.tsx`, `ApprovalRequestModal.tsx`, `ServiceCatalogScreen.tsx`)
- API modules: camelCase (`serviceOrders.ts`, `partRequests.ts`, `productCategories.ts`)
- Type definition modules: camelCase (`types.ts`)
- Utility/helper files: camelCase (`utils.ts`, `auth.ts`)
- Directories: kebab-case for utility directories (`src/api/`, `src/ui/`, `src/pos/`)
- Python modules: snake_case (`frontend_api.py`, `test_frontend_api.py`)
- Python test helper functions: `_check_*()` and `_ensure_*()` prefix pattern
- React components: PascalCase, descriptive names that end with "Screen" or "Modal" for top-level screens
- Event handlers: `on{EventName}` pattern (e.g., `onCashierSaleCompleted`, `onToast`, `onClose`, `onCreated`)
- Conditional/guard functions: `has*()` or `is*()` or `contains*()` prefix (e.g., `hasAccumulatedApproverAuthority`, `isAuthRequiredMessage`)
- API wrapper functions: camelCase, action-oriented (e.g., `searchTechnicalBudgetServices`, `addTechnicalBudgetLine`, `convertFastServiceOrder`)
- Python module functions: snake_case with descriptive action verbs (e.g., `open_store_cash_session`, `get_service_order_detail`, `save_technical_diagnosis`)
- Python role-checking functions: `_require_*_role()` pattern (e.g., `_require_login()`, `_require_checkin_role()`, `_require_budget_edit_role()`)
- Python test helper functions: `run_*_checks()` for major test suites, `_check_*()` for specific checks
- React state: camelCase (`barcode`, `scanStatus`, `customer`, `cartItems`, `completedSale`)
- Constants: UPPER_SNAKE_CASE in Python (`STATE_ENTRADA_CRIADA`, `SENSITIVE_FIELD_NAMES`, `SAFE_SERVICE_ORDER_FIELDS`)
- Type discriminators: kebab-case for enum values (e.g., `"pos_discount"`, `"pos_price_floor"`, `"Entrada criada"`)
- Request/Response types: descriptive plurals or specific suffixes (e.g., `ServiceOrderListResponse`, `BudgetItemSearchResponse`)
- React component props: `{ComponentName}Props` interface (e.g., `PosScreenProps`, `ApprovalRequestModalProps`)
- Type aliases: PascalCase, descriptive (e.g., `RolePanel`, `NavigationTarget`, `PosScanFeedback`)
- Custom error classes: Named with `Error` suffix and descriptive prefix (e.g., `AuthRequiredError`, `NoOperationalRoleError`)
- Type discriminators: specific string literals (e.g., `"atendente" | "tecnico" | "gestor" | "diretor"`)
- Record types for dynamic key-value: `Record<string, unknown>` or `Record<string, T>`

## Code Style

- Indentation: Tabs (4 spaces for Python/JavaScript per `.editorconfig`)
- Max line length: 99 characters for Python, 110 characters per Ruff config
- End of line: LF (Unix line endings)
- Final newline: Required in all files
- Trailing whitespace: Trimmed
- Character encoding: UTF-8
- ESLint: Root `.eslintrc` with loose configuration — most rules are off or warning-only
- TypeScript: Strict mode enabled (`strict: true`), case-sensitive filenames required
- Ruff (Python): Selected rules: F, E, W, I, UP, B, RUF — many are ignored for Frappe compatibility
- Python formatting: Double quotes preferred per `[tool.ruff.format]` (quote-style = "double")
- Python imports: Organized at module top with absolute imports and `from __future__ import annotations`
- Python docstrings: Triple-quoted strings on line after function signature (e.g., `"""Open the single physical drawer; sales integration arrives..."""`)
- Inline comments: Sparse; code should be self-documenting. Only comment non-obvious logic.
- Portuguese: Used in error messages, comments, and docstrings where appropriate (both Portuguese and English acceptable)

## Import Organization

- No configured path aliases in `tsconfig.json`; use relative or absolute imports within `src/`
- Python: Absolute imports from `tecponto_app` package root (e.g., `from tecponto_app.tecponto.pending import action_for_service_order`)
- Barrel exports: Used in `src/api/index.ts` and `src/ui/index.ts` for public APIs

## Error Handling

- Python backend: Raise exceptions using `frappe.throw()` with user-friendly Portuguese messages; use `AssertionError` in tests with descriptive messages
- React frontend: Catch errors in try-catch blocks, check `instanceof Error` before accessing message
- API client: Custom error classes (`AuthRequiredError`, `NoOperationalRoleError`) for specific error conditions
- Error checking: Always verify error is an instance before extracting message: `error instanceof Error ? error.message : "Fallback message"`
- Message extraction: Use `extractFrappeErrorMessage()` utility to parse nested Frappe error payloads
- User feedback: Show extracted error message or generic fallback message to user via toast/alert

## Logging

- Frontend: `console.log()`, `console.error()` (no dedicated logging library)
- ESLint rule: `no-console` is warn-level only, allowing console output for debugging
- Backend: Frappe's built-in logging via `frappe.log_error()` for critical issues
- Use `console.log()` for development debugging only
- Keep production code free of logging unless it's a critical operational event
- Use Portuguese user-facing messages in error toasts
- Backend logging: Wrap critical operations in try-catch, log via Frappe if needed

## Comments

- Explain WHY, not WHAT (code already shows WHAT)
- Document non-obvious security decisions (e.g., why a field is masked)
- Explain complex business logic not evident from code
- Mark intentional workarounds or backward-compatibility decisions
- Used sparingly
- Keep docstrings for public API functions in Python
- React components: Use TypeScript interface comments only if needed beyond the props interface itself

## Function Design

- Functions should be small and focused (single responsibility)
- React components: Typical component is 100–300 lines; break into sub-components if larger
- Python functions: Typical function is 30–80 lines; refactor if exceeding 100 lines
- React: Use single props object (interface) rather than multiple parameters
- Python: Use type hints (`param: Type`) and positional/keyword-only parameters as appropriate
- Pass related parameters together (e.g., `{ ...filters, limit_per_column: 18 }`)
- React components: Return JSX (functional component pattern)
- Python API functions: Return `dict[str, Any]` for JSON-serializable API responses
- Functions should always return consistent types; use unions sparingly

## Module Design

- API modules export an object with methods: `export const serviceOrders = { method1() { ... }, method2() { ... } }`
- UI components export function or object
- Types exported as `export type` or `export interface`
- Barrel exports in `index.ts` files for public APIs
- `src/ui/index.ts`: Exports all UI components and types
- `src/api/index.ts`: Exports all API service objects and type definitions

## React Patterns

- Use `useState` for local component state
- Use `useEffect` for side effects; always include dependency array
- Use `useCallback` for memoized event handlers
- Use `useMemo` for expensive computations
- Use `useRef` for DOM references and persistent values across renders
- Named with `on{EventName}` pattern in component props
- Use `useCallback` to memoize if passed to child components
- Always check for `null` before calling (React best practice)

## Python Backend Patterns

- Public API functions marked with `@frappe.whitelist()` decorator
- Private helpers prefixed with `_` (e.g., `_require_login()`)
- Type hints on all public functions using `from __future__ import annotations`
- Return types as `dict[str, Any]` for API endpoints
- Guard functions: `_require_*_role()` pattern that raises `frappe.PermissionError` if check fails
- Applied at function entry point before any business logic
- Example: `_require_checkin_role()`, `_require_budget_edit_role()`, `_require_director_financial_access()`
- Define `SENSITIVE_FIELD_NAMES` set: Contains field names that should never leak to non-Director roles
- Define `SAFE_*_FIELDS` tuples: Whitelist of fields safe to return for each role (e.g., `SAFE_SERVICE_ORDER_FIELDS`)
- Backend validates and filters before returning payload to frontend

## UI Component Patterns

- `"primary"`: Orange background, call-to-action
- `"secondary"`: Field-like background, default button
- `"ghost"`: No background, text-only, hover reveals background
- `"danger"`: Red tint, destructive action
- Use Tailwind tokens with `--tp-*` prefix for theming
- Colors: `--tp-bg`, `--tp-panel`, `--tp-orange`, `--tp-green`, `--tp-blue`, `--tp-purple`, `--tp-amber`, `--tp-red`
- Border: `--tp-border`
- Text colors: `--tp-text`, `--tp-muted`, `--tp-subtle`, `--tp-ink` (darkest)
- Utilities: `--tp-field` (field background)

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **App.tsx** | Main React router; screen switching; global state (user/role/auth) | `frontend/src/App.tsx` |
| **API Client** | Frappe RPC wrapper; error handling; auth expiry detection | `frontend/src/api/client.ts` |
| **ServiceOrder screens** | Kanban/List/Detail views; workflow transitions; budget editing | `frontend/src/ServiceOrderKanban.tsx`, `frontend/src/ServiceOrderFlows.tsx` |
| **CheckinWizard** | Device entry form; customer search/creation; device registration | `frontend/src/CheckinWizard.tsx` |
| **frontend/api.py** | Whitelisted API methods; permission checks; data serialization | `tecponto_app/tecponto/frontend/api.py` |
| **workflow.py** | OS state machine definition; role-based transitions; state colors | `tecponto_app/tecponto/workflow.py` |
| **service_order/*.py** | Budget management, parts tracking, payments, billing, commissions | `tecponto_app/tecponto/service_order/` |
| **acceptance.py** | Digital signature issuance; QR token generation; acceptance recording | `tecponto_app/tecponto/acceptance.py` |
| **permissions.py** | Role-based query scoping; technician-only data filtering | `tecponto_app/tecponto/permissions.py` |
| **cash.py** | Cash session lifecycle; drawer reconciliation; movement logging | `tecponto_app/tecponto/cash.py` |

## Pattern Overview

- **Workflow as source of truth** — Service Order state is managed by Frappe's built-in workflow engine (14 states + role-based transitions defined in `workflow.py`, applied via document events)
- **Role-based everything** — Frontend navigation, API method visibility, field display, and data scoping all driven by roles (Atendente/Tecnico/Gestor/Diretor)
- **Financial data protection at API level** — Cost/margin/profit fields excluded from safe field lists for non-Director roles; never serialized in payloads
- **Biometric acceptance workflow** — Device check-in/pickup requires digital or physical signatures; QR-based public links with expiring tokens
- **Technician scope isolation** — Restricted technicians (no other roles) see only their assigned service orders in list/detail APIs

## Layers

- Purpose: User interface for all roles; screen navigation; form input; read-only display
- Location: `frontend/src/`
- Contains: React components, screen logic, API wrappers
- Depends on: API Client (RPC to Frappe)
- Used by: Browser clients (Web/mobile-responsive)
- Purpose: Whitelisted RPC methods; permission enforcement; data serialization
- Location: `tecponto_app/tecponto/frontend/api.py` + `api/` modules
- Contains: Frappe-decorated `@frappe.whitelist()` methods; role checks
- Depends on: Domain services, Frappe ORM
- Used by: React frontend (JSON-RPC calls)
- Purpose: Service order lifecycle, budget calculation, cash management, trade-in evaluation
- Location: `tecponto_app/tecponto/` — workflow.py, acceptance.py, service_order/*, cash.py, tradein/*, etc.
- Contains: Pure business logic; document event handlers; domain functions
- Depends on: Frappe framework, data model
- Used by: API bridge, document events (hooks.py)
- Purpose: Frappe doctypes (Service Order, OS Acceptance, etc.) + custom fields
- Location: `tecponto_app/tecponto/doctype/` (metadata) + MariaDB
- Contains: Field definitions, validations (via **before_validate**, **validate** hooks)
- Depends on: Frappe ORM
- Used by: Domain logic, API serialization

## Data Flow

### Primary Request Path: Service Order Approval

### Secondary Flow: Technician Assignment

- **Frontend:** React local state + fetch-on-demand; no Redux/Zustand, URL params for list filters
- **Backend:** Service Order doctype fields (workflow_state, technician, budget_lines, etc.); Frappe's doc.save() persistence
- **Real-time:** No WebSocket; frontend polls for OS detail on screen focus (implicit via modal open)

## Key Abstractions

- Purpose: Encapsulates the full lifecycle of a repair ticket — from check-in to delivery
- Examples: `tecponto_app/tecponto/doctype/Service Order/` (metadata), `tecponto_app/tecponto/service_order/*.py` (domain logic)
- Pattern: Frappe Document with custom event handlers + workflow
- Purpose: Lists labor (services) and parts; cost & retail prices; technician vs. attendant pricing authority
- Examples: `service_order/budget.py`, `frontend/src/ServiceOrderFlows.tsx` (BudgetDecisionModal)
- Pattern: Child table rows + complex validation; locked after customer approval
- Purpose: Records signatures (digital or physical) for entry/pickup; encrypted device passwords; LGPD consent
- Examples: `tecponto_app/tecponto/acceptance.py`, `tecponto_app/tecponto/doctype/OS Acceptance/`
- Pattern: One-time tokens with expiry; QR codes for public links; immutable evidence archive
- Purpose: Defines the 14 OS states + role-based transitions
- Examples: `workflow.py` (SERVICE_ORDER_WORKFLOW_STATES, SERVICE_ORDER_TRANSITIONS)
- Pattern: Declarative tuples → Frappe ORM creates workflow records on migration
- Purpose: Tracks cash-drawer open/close; operator assignments; reconciliation
- Examples: `cash.py`, `tecponto_app/tecponto/doctype/Tecponto Cash Session/`
- Pattern: State machine (open → adjustments logged → closed); operator-scoped

## Entry Points

- Location: `frontend/src/main.tsx` (React root) → `frontend/src/App.tsx` (router)
- Triggers: Browser navigation to `/tecponto`, `/tecponto/caixa`, `/tecponto/portal/<token>`, etc. (routes in hooks.py:395–402)
- Responsibilities: Render role-specific screens; dispatch API calls; handle auth redirection
- Location: `tecponto_app/tecponto/frontend/api.py` (60+ whitelisted methods)
- Triggers: React RPC calls to `/api/method/tecponto_app.tecponto.frontend.api.<method>`
- Responsibilities: Permission checks; domain function delegation; response serialization
- Location: Defined in `hooks.py` (doc_events, after_migrate, scheduler_events)
- Triggers: Frappe ORM on Service Order validate/save/update; scheduled tasks (hourly/daily)
- Responsibilities: Derived data (commissions, notifications), cross-doctype consistency (parts reservation, invoices)

## Architectural Constraints

- **Threading:** Single-threaded event loop (Frappe request-scoped); async operations via Frappe job queue (for background tasks)
- **Global state:** Service Order is a Frappe document — mutable, persisted; permission checks via `doc.check_permission()` before reads/writes
- **Circular imports:** None known; domain modules import each other linearly (e.g., api.py imports service_order.*, cash.py imports workflow for state names)
- **No caching:** Frontend state is ephemeral; repeated queries hit backend (no cache layer)
- **Single database:** MariaDB shared between Frappe core and Tecponto app
- **CSRF protection:** All POST requests require Frappe CSRF token (auto-included in RPC client)

## Anti-Patterns

### Financial Data Leaking via Debug/Logging

- Never include cost fields in SAFE_SERVICE_ORDER_FIELDS (defined in `frontend/api.py:143`)
- Exclude cost from all list/detail serializations (api.py methods strip it explicitly)
- Use test sentinel values for cost fields in test logs to verify no leakage

### Workflow Transitions Bypassed in Frontend

- All state transitions via `move_service_order()` API call (api.py:950) which validates transition is allowed
- Never call `update_entry()` to change workflow_state directly — always use move_service_order
- Test verifies workflow enforcement via `test_frontend_api.py` (workflow transition guards)

### Technician Scope Bypassed via Direct Query

- Use `service_order_scope_filters()` from permissions.py in any aggregate query (list, kanban, statbar)
- Never call `frappe.get_all()` without explicit scope — always call `service_order_query()` for permission checks
- Whitelisted API methods already apply scope (api.py:100 calls `_apply_restriction_to_query()`)

## Error Handling

- **API errors:** Frappe throws `frappe.ValidationError` or `frappe.PermissionError` → extracted to message in frontend `isAuthRequiredMessage()` or generic toast
- **Workflow errors:** If transition not allowed, `apply_workflow()` raises exception; caught in api.py, message propagated to user
- **Technician scope:** `is_restricted_technician()` returns bool; if True, `service_order_query()` returns WHERE clause filtering results
- **Financial checks:** If non-Director tries to access director endpoint, permission check fails before querying

## Cross-Cutting Concerns

- Before OS creation: customer data, device info (CheckinWizard)
- Before state transitions: workflow rules enforce via `doc.check_permission()` + workflow_state matching
- Before budget approval: all budget lines must have prices
- Session-based (Frappe cookie + CSRF token)
- Frontend detects 401/403 → fires `tecponto:session-expired` event → LoginScreen modal
- No OAuth/SSO configured; uses Frappe's built-in user/password

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
