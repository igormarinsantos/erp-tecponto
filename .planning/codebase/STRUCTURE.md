# Codebase Structure

**Analysis Date:** 2026-09-02

## Directory Layout

```
tecponto_app/                          # Root: git repository
├── frontend/                           # React 18 SPA (built → public/)
│   ├── src/
│   │   ├── App.tsx                     # Main router; role-based screen dispatch
│   │   ├── main.tsx                    # React entry point
│   │   ├── api/                        # API client modules
│   │   │   ├── client.ts               # Frappe RPC wrapper
│   │   │   ├── index.ts                # Exports all API methods
│   │   │   ├── serviceOrders.ts        # Service order CRUD
│   │   │   ├── balcao.ts               # Attendant operations
│   │   │   ├── checkin.ts              # Device check-in
│   │   │   ├── pos.ts                  # Point-of-sale
│   │   │   ├── cash*.ts                # Cash management
│   │   │   ├── types.ts                # TypeScript interfaces for all API responses
│   │   │   └── ...                     # Other domain APIs
│   │   ├── *Screen.tsx                 # Role/function-specific screens (30+)
│   │   │   ├── CheckinWizard.tsx       # Device entry workflow
│   │   │   ├── ServiceOrderKanban.tsx  # Kanban board view
│   │   │   ├── ServiceOrderFlows.tsx   # Budget/approval/pickup flows
│   │   │   ├── PosScreen.tsx           # Point-of-sale UI
│   │   │   ├── QuotesCrmScreen.tsx     # Quote follow-up CRM
│   │   │   └── ...
│   │   ├── ui/                         # Reusable UI components
│   │   ├── utils/                      # Helper functions (formatters, validators)
│   │   ├── styles/                     # Tailwind CSS + custom styles
│   │   └── assets/                     # Images, icons
│   ├── package.json                    # Dependencies (React, Vite, TypeScript, Tailwind)
│   ├── vite.config.ts                  # Vite build config
│   ├── tailwind.config.ts              # Tailwind theming
│   ├── tsconfig.json                   # TypeScript strict mode
│   └── index.html                      # Entry HTML (mounts #tecponto-root)
│
├── tecponto_app/                       # Python backend (Frappe app)
│   ├── hooks.py                        # Frappe hooks: doctypes, workflows, events, fixtures
│   ├── __init__.py
│   ├── config/
│   │   └── *.py                        # Config modules (branding, desk sidebar, etc.)
│   ├── tecponto/                       # Domain logic (core modules)
│   │   ├── __init__.py
│   │   ├── workflow.py                 # Service Order state machine (14 states)
│   │   ├── acceptance.py               # Digital acceptance + QR tokens
│   │   ├── cash.py                     # Cash drawer management
│   │   ├── permissions.py              # Role-based query scoping
│   │   ├── tracking.py                 # Public OS tracking links
│   │   ├── financial.py                # Director financial queries
│   │   ├── service_order/              # Service Order sub-domain
│   │   │   ├── budget.py               # Budget calculation & locking
│   │   │   ├── parts.py                # Part reservation & outcome tracking
│   │   │   ├── payments.py             # Payment collection
│   │   │   ├── billing.py              # Sales invoice generation
│   │   │   ├── commission.py           # Technician commission calculation
│   │   │   ├── assignment.py           # Technician claim/assign/transfer
│   │   │   ├── aceites.py              # Acceptance signature handling
│   │   │   ├── print_formats.py        # PDF/label generation
│   │   │   ├── stage_clock.py          # Stage entry timestamp
│   │   │   ├── stage_sla.py            # SLA tracking per stage
│   │   │   ├── deadline.py             # Budget approval deadline
│   │   │   ├── device_credentials.py   # Encrypted device passwords
│   │   │   ├── inoperative_device.py   # Inoperative terms
│   │   │   └── kanban.py               # Kanban board configuration
│   │   ├── tradein/                    # Trade-in domain
│   │   │   ├── evaluation.py           # Device buyback evaluation
│   │   │   ├── buyback.py              # Purchase & inventory
│   │   │   ├── cannibalization.py      # Parts harvesting
│   │   │   ├── operation.py            # Trade-in operation tracking
│   │   │   └── workflow.py             # Trade-in workflow states
│   │   ├── frontend/                   # API bridge layer
│   │   │   ├── api.py                  # 60+ whitelisted RPC methods
│   │   │   ├── pos.py                  # POS-specific endpoints
│   │   │   ├── setup.py                # Migration fixtures
│   │   │   └── test_frontend_api.py    # API test suite
│   │   ├── doctype/                    # Frappe doctype controllers (36 custom types)
│   │   │   └── <doctype_name>/
│   │   │       ├── <doctype_name>.py   # Controller with validate/on_update hooks
│   │   │       ├── <doctype_name>.json # Metadata (fields, perms)
│   │   │       └── ...
│   │   ├── posix payment flows
│   │   ├── cash.py                     # Cash session management
│   │   ├── pos.py                      # POS configuration & item prep
│   │   ├── cashier.py                  # Cashier operator identity
│   │   ├── customer.py                 # Customer validation
│   │   ├── service_catalog.py          # Service template catalog
│   │   ├── technical_budget.py         # Technical budget (alternative to service budget)
│   │   ├── user_access.py              # Access audit & user role validation
│   │   ├── notify.py                   # Notification queuing
│   │   ├── part_requests.py            # Part request workflow
│   │   ├── requests.py                 # Generic request handling
│   │   ├── product_categories.py       # Retail product hierarchy
│   │   ├── product_variants.py         # Variant attribute management
│   │   ├── listing_metadata.py         # E-commerce listings metadata
│   │   ├── stock.py                    # Warehouse & valuation defaults
│   │   ├── pricing.py                  # Service/product price validation
│   │   ├── purchasing.py               # Purchase order approval thresholds
│   │   ├── hr.py                       # HR foundation (technician roles)
│   │   ├── used_device_warranty.py     # Warranty for sold used devices
│   │   └── ... (other domain modules)
│   ├── fixtures/                       # Frappe JSON fixtures (data seeded on migrate)
│   │   └── *.json
│   ├── patches/                        # Migration scripts
│   │   ├── v*/
│   │   └── ...
│   ├── public/                         # Static assets (built frontend, images, etc.)
│   │   ├── dist/                       # Vite build output → frontend .js/.css
│   │   ├── images/
│   │   └── ...
│   ├── templates/                      # Jinja2 templates for Frappe pages
│   │   ├── base.html                   # Custom base template (branding)
│   │   └── ...
│   └── www/                            # Public website pages
│       ├── tecponto/                   # Main SPA route
│       ├── portal/                     # Public acceptance portal
│       ├── aceite/                     # Digital signature acceptance
│       ├── rastreio/                   # Public tracking
│       └── ...
│
├── scripts/                            # Utility scripts
│   ├── test-local.sh                   # Run backend test suite in container
│   └── ...
│
├── docs/                               # Documentation (markdown)
├── deployment/                         # Docker/infra configs
├── artifacts/                          # Design mockups & planning docs (70+ dirs)
│
├── .planning/                          # GSD planning directory
│   └── codebase/                       # This analysis directory
│       ├── ARCHITECTURE.md             # (this file)
│       └── STRUCTURE.md                # (you're reading it)
│
├── CLAUDE.md                           # Project permanent rules (security, workflow, design)
├── GEMINI.md                           # Mirror of CLAUDE.md (kept in sync)
├── pyproject.toml                      # Python package metadata
├── .pre-commit-config.yaml             # Pre-commit hooks
├── .eslintrc                           # ESLint rules
└── README.md
```

## Directory Purposes

**frontend/src/:**
- Purpose: React application source code
- Contains: Components (screens, modals, UI library), API clients, type definitions, styles
- Key files: `App.tsx` (router), `CheckinWizard.tsx` (entry flow), `ServiceOrderKanban.tsx` (main view)

**frontend/src/api/:**
- Purpose: API abstraction layer — one module per domain (serviceOrders, balcao, cash, etc.)
- Contains: Frappe RPC wrappers; TypeScript interfaces for all responses
- Key files: `client.ts` (low-level RPC), `types.ts` (all type definitions), `index.ts` (exports)

**tecponto_app/tecponto/:**
- Purpose: Business logic and domain models
- Contains: Python functions organized by domain (service_order, tradein, cash, etc.), doctype controllers, event handlers
- Key files: `workflow.py` (state machine), `acceptance.py` (signatures), `frontend/api.py` (API bridge)

**tecponto_app/tecponto/service_order/:**
- Purpose: Service Order subdomain — all logic related to repair tickets
- Contains: Budget management, parts tracking, payments, commissions, printing, acceptance
- Key files: `budget.py`, `parts.py`, `payments.py`, `billing.py`

**tecponto_app/tecponto/frontend/:**
- Purpose: Bridge between React frontend and Frappe backend
- Contains: Whitelisted API methods (60+); serialization logic; permission checks
- Key file: `api.py` (main endpoint)

**tecponto_app/public/dist/:**
- Purpose: Vite build output — minified React + CSS bundle
- Contents: `index.*.js`, `style.*.css`, `index.html`
- Generated: On `npm run build` in frontend/; copied to public/ by build hook

**tecponto_app/www/:**
- Purpose: Frappe website routes (public pages)
- Contains: SPA entry point (tecponto/), public portals (portal, aceite, rastreio)
- Key file: `tecponto/` (renders index.html with React)

## Key File Locations

**Entry Points:**
- `frontend/src/main.tsx` — React app mount point (ReactDOM.createRoot)
- `frontend/src/App.tsx` — Router logic; role-based screen dispatch
- `tecponto_app/www/tecponto/` — Frappe page that renders React SPA
- `tecponto_app/tecponto/frontend/api.py` — Frappe RPC endpoint for all backend calls

**Configuration:**
- `tecponto_app/hooks.py` — Frappe hooks (workflows, doctypes, events, routes, etc.)
- `frontend/vite.config.ts` — Vite build settings
- `frontend/tailwind.config.ts` — Tailwind CSS theme
- `frontend/tsconfig.json` — TypeScript strictness

**Core Logic:**
- `tecponto_app/tecponto/workflow.py` — Service Order state machine
- `tecponto_app/tecponto/frontend/api.py` — 60+ API methods
- `tecponto_app/tecponto/service_order/budget.py` — Budget validation
- `tecponto_app/tecponto/acceptance.py` — Digital acceptance & QR generation

**Testing:**
- `tecponto_app/tecponto/frontend/test_frontend_api.py` — Backend API test suite (pytest)
- `frontend/src/api/client.ts` — Error types used in tests
- No Jest/Vitest tests in frontend (only backend)

## Naming Conventions

**Files:**
- Python: snake_case (e.g., `workflow.py`, `part_requests.py`)
- React components: PascalCase ending in Screen/Modal/Panel (e.g., `CheckinWizard.tsx`, `ServiceOrderKanban.tsx`)
- API modules: camelCase (e.g., `serviceOrders.ts`, `balcao.ts`)
- Types: PascalCase with Suffix (Response, Payload, etc.) (e.g., `ServiceOrderDetailResponse`, `CheckinPayload`)

**Directories:**
- Python modules: snake_case plural (e.g., `service_order/`, `doctype/`, `tradein/`)
- React directories: lowercase (e.g., `api/`, `ui/`, `utils/`, `styles/`)

**Database/Doctypes:**
- PascalCase (e.g., `Service Order`, `OS Acceptance`, `Tecponto Settings`)
- Frappe auto-translates to table names (e.g., `Service Order` → `tabService Order`)

**Workflow States:**
- Title case in Portuguese (e.g., `Entrada criada`, `Em diagnóstico`, `Aguardando aprovação`)
- Defined in `workflow.py` as module constants (STATE_ENTRADA_CRIADA, etc.)

## Where to Add New Code

**New Feature (e.g., SMS notifications):**
- Backend logic: `tecponto_app/tecponto/notify.py` (extend notify_due_service_orders)
- Frontend hook: `frontend/src/App.tsx` (add screen if UI needed)
- API method: `tecponto_app/tecponto/frontend/api.py` (add @frappe.whitelist() method)
- Tests: `tecponto_app/tecponto/frontend/test_frontend_api.py` (add test case)

**New Screen (e.g., Compliance Reports):**
- Component: `frontend/src/ComplianceReportsScreen.tsx` (follows naming pattern)
- Navigation: Add to App.tsx route dispatch + roleConfig.tsx
- API methods: `frontend/src/api/reports.ts` (new module)
- Backend: `tecponto_app/tecponto/compliance.py` (new domain module)

**New Doctype (e.g., Service Review):**
- Metadata: Create via Frappe Desk UI → auto-generates `tecponto_app/tecponto/doctype/service_review/`
- Controller: Add validation/event handlers in `service_review.py`
- Hooks: Register in `hooks.py` (fixtures, permissions, doc_events)
- API: Add read/create/update methods in `frontend/api.py`

**New Service Order Sub-Feature (e.g., Warranty Registration):**
- Logic: `tecponto_app/tecponto/service_order/warranty.py` (follows sub-domain pattern)
- Controller hook: Register in `hooks.py` doc_events["Service Order"]["on_update"]
- API: Add method to `frontend/api.py`
- Frontend: Add flow/modal to `ServiceOrderFlows.tsx` or new modal

**Shared Utilities:**
- Backend: `tecponto_app/tecponto/<module_name>.py` (e.g., `pricing.py` for shared pricing logic)
- Frontend: `frontend/src/utils/` (e.g., `formatters.ts` for date/currency formatting)

**UI Components (Reusable):**
- Location: `frontend/src/ui/` — Button, Modal, Card, etc.
- Pattern: Functional components with TypeScript props interface

## Special Directories

**artifacts/:**
- Purpose: Design mockups, planning documents, phase artifacts (NOT code)
- Generated: Yes (manually created during design/planning phases)
- Committed: Yes (version controlled for design history)
- Note: 70+ subdirectories tracking feature phases (fase_3_1_*, bloco_*, etc.)

**fixtures/:**
- Purpose: Frappe JSON data seeded on migrate (roles, workflows, settings)
- Generated: No (manually crafted)
- Committed: Yes (part of app distribution)

**patches/:**
- Purpose: Migration scripts (v0_1, v0_2, etc.) run on `bench migrate`
- Generated: Yes (as needed for schema changes)
- Committed: Yes (applied in order, never removed)

**.planning/codebase/:**
- Purpose: GSD codebase analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: Yes (by gsd-map-codebase tool)
- Committed: Yes (tracked for documentation history)

**public/dist/:**
- Purpose: Vite build output (minified React bundle)
- Generated: Yes (from `npm run build` in frontend/)
- Committed: Yes (in production deployments; can be .gitignore'd in CI)

**node_modules/, __pycache__/:**
- Purpose: Dependency caches
- Generated: Yes (auto-generated)
- Committed: No (.gitignore'd)

---

*Structure analysis: 2026-09-02*
