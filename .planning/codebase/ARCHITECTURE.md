<!-- refreshed: 2026-09-02 -->
# Architecture

**Analysis Date:** 2026-09-02

## System Overview

Tecponto is a brownfield production ERP for phone repair, built on **Frappe Framework v16 (Python backend)** + **React 18 (TypeScript frontend)**. The core domain is the service order (OS) lifecycle: check-in (entrada) → diagnosis → budgeting → approval → repair execution → pickup/delivery (entregue).

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    React 18 Frontend (Vite + TypeScript)                 │
│  App.tsx → Role-based screens (Atendente/Técnico/Gestor/Diretor)        │
│  frontend/src/ — Components, API clients, UI library                    │
└────────────┬──────────────────────────────────────────────────────┬─────┘
             │ Frappe RPC (/api/method/...)                         │
             │ JSON FormData, CSRF-secured                          │
             ▼                                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│            Frappe Python Backend (tecponto_app/tecponto/)                │
│  API Layer: frontend/api.py (whitelisted methods)                        │
│  Domain Modules:                                                         │
│  • workflow.py — OS state machine (14 states, role-based transitions)   │
│  • acceptance.py — Digital/physical acceptance signatures + QR          │
│  • service_order/ — Budget, parts, payments, billing, commission       │
│  • cash.py — Cash drawer management & session tracking                  │
│  • permissions.py — Role scoping (restricted technicians see own work)  │
│  • tradein/ — Trade-in evaluation & buyback workflow                    │
│  • tracking.py — Public OS progress tracking (WhatsApp links)           │
└────────────┬──────────────────────────────────────────────────────┬─────┘
             │ Frappe Document Events (hooks.py)                     │
             │ Workflow state transitions + auto-triggers            │
             ▼                                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               Data Layer: Frappe Doctypes + MariaDB                      │
│  Service Order, OS Acceptance, OS Payment, Trade Evaluation, etc.        │
│  Workflow/Workflow State/Workflow Action (built-in Frappe types)        │
│  Custom doctypes: Tecponto Settings, Tecponto Part Request, etc.        │
└─────────────────────────────────────────────────────────────────────────┘
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

**Overall:** Frappe monolith with **separated concerns** — domain logic in Python, presentation in React via RPC.

**Key Characteristics:**
- **Workflow as source of truth** — Service Order state is managed by Frappe's built-in workflow engine (14 states + role-based transitions defined in `workflow.py`, applied via document events)
- **Role-based everything** — Frontend navigation, API method visibility, field display, and data scoping all driven by roles (Atendente/Tecnico/Gestor/Diretor)
- **Financial data protection at API level** — Cost/margin/profit fields excluded from safe field lists for non-Director roles; never serialized in payloads
- **Biometric acceptance workflow** — Device check-in/pickup requires digital or physical signatures; QR-based public links with expiring tokens
- **Technician scope isolation** — Restricted technicians (no other roles) see only their assigned service orders in list/detail APIs

## Layers

**Frontend Presentation Layer:**
- Purpose: User interface for all roles; screen navigation; form input; read-only display
- Location: `frontend/src/`
- Contains: React components, screen logic, API wrappers
- Depends on: API Client (RPC to Frappe)
- Used by: Browser clients (Web/mobile-responsive)

**API Bridge Layer:**
- Purpose: Whitelisted RPC methods; permission enforcement; data serialization
- Location: `tecponto_app/tecponto/frontend/api.py` + `api/` modules
- Contains: Frappe-decorated `@frappe.whitelist()` methods; role checks
- Depends on: Domain services, Frappe ORM
- Used by: React frontend (JSON-RPC calls)

**Domain/Business Logic Layer:**
- Purpose: Service order lifecycle, budget calculation, cash management, trade-in evaluation
- Location: `tecponto_app/tecponto/` — workflow.py, acceptance.py, service_order/*, cash.py, tradein/*, etc.
- Contains: Pure business logic; document event handlers; domain functions
- Depends on: Frappe framework, data model
- Used by: API bridge, document events (hooks.py)

**Data Model Layer:**
- Purpose: Frappe doctypes (Service Order, OS Acceptance, etc.) + custom fields
- Location: `tecponto_app/tecponto/doctype/` (metadata) + MariaDB
- Contains: Field definitions, validations (via **before_validate**, **validate** hooks)
- Depends on: Frappe ORM
- Used by: Domain logic, API serialization

## Data Flow

### Primary Request Path: Service Order Approval

1. **Frontend:** User submits budget decision (approve/reject) in `ServiceOrderFlows.tsx` dialog
2. **API Call:** `serviceOrders.decideBudget()` → RPC to `tecponto_app.tecponto.frontend.api.decide_service_order_budget`
3. **API Method (api.py:450):** 
   - Check role is in BUDGET_ALLOWED_ROLES (Atendente/Gestor/Tecnico)
   - Validate service order state is "Aguardando aprovação"
   - Update budget lines with decision (aprovado/reprovado)
   - Apply workflow transition → new state
4. **Workflow Engine (hooks.py, workflow.py):**
   - Frappe fires `on_update` hooks
   - Service order state changes (e.g., → "Aprovado")
5. **Document Events (hooks.py:306–314):**
   - `service_order.parts.processar_pecas()` — Reserve parts from stock
   - `service_order.billing.gerar_nota()` — Create sales invoice
   - `service_order.notify.on_service_order_updated()` — Queue notifications
6. **Response:** Updated ServiceOrderDetailResponse returned to frontend; Kanban view refetches and re-renders

### Secondary Flow: Technician Assignment

1. **Unassigned OS appears:** Technician views `list_unassigned_service_orders()`
2. **Claim action:** `serviceOrders.claim()` → API checks is_restricted_technician, assigns to caller
3. **Hooks fire:** `service_order.notify.on_service_order_updated()` queues assignment notification
4. **Scope updated:** Next queries for this user now include the claimed order (scoped by `technician` field in query)

**State Management:**
- **Frontend:** React local state + fetch-on-demand; no Redux/Zustand, URL params for list filters
- **Backend:** Service Order doctype fields (workflow_state, technician, budget_lines, etc.); Frappe's doc.save() persistence
- **Real-time:** No WebSocket; frontend polls for OS detail on screen focus (implicit via modal open)

## Key Abstractions

**Service Order (Core Entity):**
- Purpose: Encapsulates the full lifecycle of a repair ticket — from check-in to delivery
- Examples: `tecponto_app/tecponto/doctype/Service Order/` (metadata), `tecponto_app/tecponto/service_order/*.py` (domain logic)
- Pattern: Frappe Document with custom event handlers + workflow

**Budget (Nested in Service Order):**
- Purpose: Lists labor (services) and parts; cost & retail prices; technician vs. attendant pricing authority
- Examples: `service_order/budget.py`, `frontend/src/ServiceOrderFlows.tsx` (BudgetDecisionModal)
- Pattern: Child table rows + complex validation; locked after customer approval

**Acceptance (Separate Doctype):**
- Purpose: Records signatures (digital or physical) for entry/pickup; encrypted device passwords; LGPD consent
- Examples: `tecponto_app/tecponto/acceptance.py`, `tecponto_app/tecponto/doctype/OS Acceptance/`
- Pattern: One-time tokens with expiry; QR codes for public links; immutable evidence archive

**Workflow State (Frappe Built-In):**
- Purpose: Defines the 14 OS states + role-based transitions
- Examples: `workflow.py` (SERVICE_ORDER_WORKFLOW_STATES, SERVICE_ORDER_TRANSITIONS)
- Pattern: Declarative tuples → Frappe ORM creates workflow records on migration

**Cash Session (Drawer Lifecycle):**
- Purpose: Tracks cash-drawer open/close; operator assignments; reconciliation
- Examples: `cash.py`, `tecponto_app/tecponto/doctype/Tecponto Cash Session/`
- Pattern: State machine (open → adjustments logged → closed); operator-scoped

## Entry Points

**Frontend (User-Facing):**
- Location: `frontend/src/main.tsx` (React root) → `frontend/src/App.tsx` (router)
- Triggers: Browser navigation to `/tecponto`, `/tecponto/caixa`, `/tecponto/portal/<token>`, etc. (routes in hooks.py:395–402)
- Responsibilities: Render role-specific screens; dispatch API calls; handle auth redirection

**Backend (API Entry Points):**
- Location: `tecponto_app/tecponto/frontend/api.py` (60+ whitelisted methods)
- Triggers: React RPC calls to `/api/method/tecponto_app.tecponto.frontend.api.<method>`
- Responsibilities: Permission checks; domain function delegation; response serialization

**Document Events (Automatic Workflows):**
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

**What happens:** Cost fields logged to server logs or included in error messages, exposing profit margins to non-Directors

**Why it's wrong:** Violates the core security rule (Guard de Custo) — non-Directors must never see acquisition costs

**Do this instead:** 
- Never include cost fields in SAFE_SERVICE_ORDER_FIELDS (defined in `frontend/api.py:143`)
- Exclude cost from all list/detail serializations (api.py methods strip it explicitly)
- Use test sentinel values for cost fields in test logs to verify no leakage

### Workflow Transitions Bypassed in Frontend

**What happens:** UI allows clicking a workflow button (e.g., "Approve") without backend validation; state doesn't actually change

**Why it's wrong:** Creates false sense of action completion; data inconsistency between frontend display and database

**Do this instead:**
- All state transitions via `move_service_order()` API call (api.py:950) which validates transition is allowed
- Never call `update_entry()` to change workflow_state directly — always use move_service_order
- Test verifies workflow enforcement via `test_frontend_api.py` (workflow transition guards)

### Technician Scope Bypassed via Direct Query

**What happens:** Restricted technician constructs a Frappe query without applying scope filters, sees all service orders

**Why it's wrong:** Bypasses role-based isolation; technician sees others' work and financial data

**Do this instead:**
- Use `service_order_scope_filters()` from permissions.py in any aggregate query (list, kanban, statbar)
- Never call `frappe.get_all()` without explicit scope — always call `service_order_query()` for permission checks
- Whitelisted API methods already apply scope (api.py:100 calls `_apply_restriction_to_query()`)

## Error Handling

**Strategy:** Fail-fast with user-readable messages; log all permission denials; re-authenticate on 401

**Patterns:**
- **API errors:** Frappe throws `frappe.ValidationError` or `frappe.PermissionError` → extracted to message in frontend `isAuthRequiredMessage()` or generic toast
- **Workflow errors:** If transition not allowed, `apply_workflow()` raises exception; caught in api.py, message propagated to user
- **Technician scope:** `is_restricted_technician()` returns bool; if True, `service_order_query()` returns WHERE clause filtering results
- **Financial checks:** If non-Director tries to access director endpoint, permission check fails before querying

## Cross-Cutting Concerns

**Logging:** Frappe's built-in logger (errors logged to error_log doctype); access audit via `Tecponto Access Audit` doctype (user_access.py)

**Validation:** 
- Before OS creation: customer data, device info (CheckinWizard)
- Before state transitions: workflow rules enforce via `doc.check_permission()` + workflow_state matching
- Before budget approval: all budget lines must have prices

**Authentication:** 
- Session-based (Frappe cookie + CSRF token)
- Frontend detects 401/403 → fires `tecponto:session-expired` event → LoginScreen modal
- No OAuth/SSO configured; uses Frappe's built-in user/password

---

*Architecture analysis: 2026-09-02*
