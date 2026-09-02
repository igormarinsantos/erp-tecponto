# Technology Stack

**Analysis Date:** 2026-09-02

## Languages

**Primary:**
- **Python** 3.14.4 - Backend logic, Frappe/ERPNext framework, business rules
- **TypeScript** 5.7.2 - React frontend application, type-safe UI code
- **JavaScript** (React/JSX) - Frontend rendering and interactivity

**Secondary:**
- **HTML/CSS** - Web templates and styling foundations
- **Jinja2** - Frappe server-side templating for print formats and pages

## Runtime

**Environment:**
- **Python** 3.14.4 (backend server)
- **Node.js** v20.20.2 (frontend development and build)
- **Frappe Bench** (development/deployment framework for Frappe apps)

**Package Managers:**
- **npm** 10.8.2 - JavaScript/Node dependencies (`frontend/package.json`, `frontend/package-lock.json`)
- **pip** - Python dependencies (via Frappe bench, managed centrally)
- **Lockfile:** `frontend/package-lock.json` (present and committed)

## Frameworks

**Core:**
- **Frappe Framework** v16.0.0 (Python backend) - ERP framework, ORM, API layer, permission system
- **ERPNext** v16 (Frappe module) - Standard ERP functionality (inventory, accounting, sales)
- **HRMS** (Frappe module) - Human Resource Management System

**Frontend:**
- **React** 18.3.1 - UI component library, state management
- **Vite** 8.1.3 - Frontend build tool, dev server (port 5173 by default)
- **TypeScript** 5.7.2 - Type checking, strict mode enabled

**Styling:**
- **Tailwind CSS** 3.4.17 - Utility-first CSS framework
- **PostCSS** 8.4.49 - CSS processing
- **Autoprefixer** 10.4.20 - Browser compatibility prefixes
- **@fontsource/space-grotesk** 5.2.10 - Custom font (Space Grotesk)

**Icons:**
- **lucide-react** 0.468.0 - Icon component library

## Key Dependencies

**Critical:**
- **python-barcode** 0.16.1 (Python) - Barcode generation for POS/product labels
- **Frappe Framework 16.0.0** - Entire backend stack is built on Frappe

**Infrastructure:**
- **MariaDB** 10.6 - Primary relational database (`db_type: mariadb` in site config)
- **Redis** 6.2+ - Caching, task queues, WebSocket support (cache, queue, socketio)

**Frontend Build Chain:**
- **@vitejs/plugin-react** 6.0.3 - React/JSX plugin for Vite
- **@types/react** 18.3.18 - React TypeScript definitions
- **@types/react-dom** 18.3.5 - React DOM TypeScript definitions

## Configuration

**Environment:**
- Development mode enabled (`developer_mode: 1` in site config)
- Encryption key configured (database encryption at rest)
- Multi-app installation: `frappe`, `erpnext`, `hrms`, `tecponto_app`

**Database:**
- **Type:** MariaDB
- **Host:** Configurable per deployment (default: localhost)
- **Credentials:** Per-site database user (`_4b49d3063d2d4f46` pattern for isolation)
- **Connection:** TCP/IP, port 3306

**Caching & Queues:**
- **Redis Cache:** `redis://redis-cache:6379` (production), localhost:6379 (dev)
- **Redis Queue:** `redis://redis-queue:6379` (production), localhost:6379 (dev)
- **Redis SocketIO:** `redis://redis-queue:6379` (for WebSocket communication)

**Build Configuration:**
- `vite.config.ts` - Frontend build output to `../tecponto_app/public/frontend/`
- `tailwind.config.ts` - Tailwind CSS with design token system (custom color vars)
- `tsconfig.json` - TypeScript strict mode, ES2020 target
- `pyproject.toml` - Python project metadata, Ruff linting rules

## Frontend Build & Tooling

**Linting & Code Quality:**
- **ESLint** - JS/TS linting (`.eslintrc`, rules relaxed for legacy Frappe globals)
- **ruff** - Python linting and formatting (110 char line length, tabs for indentation)
- **prettier** - Code formatting (via pre-commit hooks)
- **pre-commit** - Git hook framework for automated checks

**TypeScript Configuration:**
- Target: ES2020
- Strict mode enabled
- React JSX factory: `react-jsx`
- Module resolution: Node

**Vite Build:**
- Base path: `/assets/tecponto_app/frontend/`
- Output directory: `../tecponto_app/public/frontend`
- Source maps enabled in production builds
- CSS bundled to single `assets/app.css`
- JS bundled to single `assets/app.js`

## Platform Requirements

**Development:**
- WSL Ubuntu (primary dev environment at `\\wsl$\Ubuntu\home\usuario\frappe-bench\`)
- Python 3.14.4+
- Node.js v20+
- npm 10+
- Git
- Frappe bench CLI (installed in virtual env)

**Production:**
- **Container:** Docker (Coolify-compatible)
- **Base Image:** frappe/frappe:version-16 (Debian-based)
- **Orchestration:** Coolify or Docker Compose
- **Reverse Proxy:** Nginx (Frappe standard)
- **Process Manager:** Gunicorn (backend), Node.js (frontend dev server replaced by static assets in prod)

**Runtime Stack (Production):**
- MariaDB 10.6 (external service)
- Redis 6.2+ (external service)
- Chromium/headless-shell (for PDF generation and print formats)

## Notable Technical Choices

**Frappe/ERPNext as Platform:**
- Inherits Frappe's permission system, document model, and API conventions
- Uses Frappe's `frappe.enqueue()` for async job processing
- RPC-based API pattern (`/api/method/...`) for backend calls

**React over Frappe Desk:**
- Custom React frontend for `tecponto_app` instead of Frappe's built-in web interface
- Communicates via Frappe RPC endpoints
- Handles complex workflows (service orders, POS, trades) in React

**Hybrid Architecture:**
- Backend: Pure Frappe/Python (business logic, data, security)
- Frontend: Pure React/TypeScript (UI/UX, state management)
- Glue: REST/RPC API over HTTP/FormData

---

*Stack analysis: 2026-09-02*
