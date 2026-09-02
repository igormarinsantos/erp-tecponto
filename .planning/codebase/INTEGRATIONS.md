# External Integrations

**Analysis Date:** 2026-09-02

## APIs & External Services

**Payment Processing & Transactions:**
- Not detected in current codebase (payment processing appears to be handled internally via Frappe's POS Invoice and custom payment types)

**Communication Channels (Planned/Future):**
- **WhatsApp** - Planned integration mentioned in `tecponto_app/tecponto/tracking.py` ("Authorized internal API for future notification and WhatsApp channels")
  - Not yet implemented; infrastructure in place for async delivery
  - Use case: Tracking link delivery, order status notifications

**QR Code Generation:**
- Built-in via Frappe's `frappe.twofactor.get_qr_svg_code()` for tracking links
- Used in `tecponto_app/tecponto/tracking.py` for Service Order tracking portal QR codes

**Barcode Generation:**
- SDK: `python-barcode` 0.16.1
- Used for: Product labels, POS item barcodes, thermal receipt printing

## Data Storage

**Databases:**
- **Type/Provider:** MariaDB 10.6
  - Connection: Configured via `site_config.json` (host, port, user, password)
  - Client: Frappe ORM (Python) - abstracts SQL queries, handles migrations
  - Multiple databases per Frappe bench instance (one per site)

**File Storage:**
- **Approach:** Local filesystem only
  - Attachment directory: `[site]/private/files/` and `[site]/public/files/`
  - Managed by Frappe's file manager
  - Print formats (PDF, thermal) generated on-demand via server-side rendering

**Caching:**
- **Service:** Redis 6.2+
  - **Cache:** `redis://127.0.0.1:6379` (configurable via `redis_cache` in site config)
  - **Job Queue:** `redis://127.0.0.1:6379` (async task processing)
  - **WebSocket/Socket.IO:** `redis://127.0.0.1:6379` (real-time updates)
  - Used for: Session caching, permission caching, async job storage, rate limiting

## Authentication & Identity

**Auth Provider:**
- **Custom (Frappe Built-In)**
  - Implementation: Frappe's native user/password system stored in MariaDB
  - Session management: HTTP cookies (`sid` cookie), CSRF tokens (`X-Frappe-CSRF-Token`)
  - No external OAuth/OIDC providers integrated
  - Multi-factor authentication: Available via Frappe but not enabled by default

**User Roles (Tecponto Custom):**
- `Tecponto Atendente` (Attendant) - Counter/customer-facing
- `Tecponto Tecnico` (Technician) - Repair operations
- `Tecponto Gestor` (Manager) - Administrative oversight
- `Tecponto Diretor` (Director) - Financial/strategic access
- `System Manager` - Full system access (Frappe standard)

**Session Security:**
- CSRF token validation required on all POST requests (`X-Frappe-CSRF-Token` header)
- Credentials sent via same-origin form-data (no JSON-based auth transport)
- Session expires per Frappe configuration (typically 7 days idle timeout)

## Monitoring & Observability

**Error Tracking:**
- Not detected - errors logged to Frappe error log table (`frappe.log_error()` calls)
- No Sentry, DataDog, or third-party error service configured

**Logs:**
- **Approach:** Server-side only (Frappe standard logging)
  - File: `/home/usuario/frappe-bench/logs/` directory
  - Database: Error and audit logs stored in `frappe.Error Log` and custom `Tecponto Access Audit` doctypes
  - No centralized log aggregation (ELK, Splunk, CloudWatch) configured

**Audit Trail:**
- Custom: `Tecponto Access Audit` doctype for user access tracking
- Automatic recording on User creation, deletion, and role changes via hooks
- Service Order state changes tracked via `Service Order Tracking` doctype

## CI/CD & Deployment

**Hosting:**
- **Development:** Local WSL Ubuntu with Frappe bench
- **Production:** Docker containers (Coolify orchestration)
- **Registry:** GitHub Container Registry (GHCR)
  - Image: `ghcr.io/[owner]/erp-tecponto:version-16`

**CI Pipeline:**
- **Provider:** GitHub Actions (`.github/workflows/publish-image.yml`)
- **Trigger:** Push/PR to `version-16` branch
- **Stages:**
  1. **Detect changes** - Filters deployment changes
  2. **Validate** - Frontend typecheck + build, Python compilation
  3. **Integration** - Full Frappe suite on ephemeral MariaDB + Redis
  4. **Publish** - Build Docker image and push to GHCR

**Deployment Target:**
- **Container Runtime:** Docker/Docker Compose
- **Orchestration:** Coolify (Docker Compose-based)
- **Services:** Frappe app, Nginx, MariaDB, Redis (separate containers)
- **Environment:** Production site name = `erp.tecponto.sbs`

**Build Artifacts:**
- Docker image layers: Runtime (Frappe base) + Apps (ERPNext, HRMS, tecponto_app)
- Frontend assets: Vite-bundled JS/CSS in `tecponto_app/public/frontend/`
- Python artifacts: Compiled bytecode cached in `__pycache__/`

## Environment Configuration

**Required env vars:**
- `FRAPPE_IMAGE` - Docker image URI (default: `ghcr.io/igormarinsantos/erp-tecponto:version-16`)
- `SERVICE_PASSWORD_ADMIN` - Frappe Administrator password (production)
- `SERVICE_PASSWORD_DB` - MariaDB root password (production)
- `COMPANY_NAME` - Company legal name for ERP setup
- `COMPANY_ABBR` - 3-letter company abbreviation (accounting)
- `SITE_NAME` - Frappe site hostname (production: `erp.tecponto.sbs`)

**Optional env vars (defaults in bench config):**
- `db_host` - MariaDB host (default: `db` in Compose, `127.0.0.1` in dev)
- `db_port` - MariaDB port (default: 3306)
- `redis_cache`, `redis_queue`, `redis_socketio` - Redis URLs

**Secrets location:**
- **Development:** `.env` files in Frappe bench (git-ignored)
- **Production:** Coolify environment variables (managed via UI)
- **Database credentials:** `site_config.json` (encrypted at rest, file permissions restricted)

**No External Credential Management:**
- No AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault integration
- Secrets stored as environment variables and filesystem files with Unix permissions

## Webhooks & Callbacks

**Incoming:**
- **Frappe Webhooks:** Generic webhook framework available via Frappe (not actively used in Tecponto)
- Custom endpoints: None detected for webhook ingestion

**Outgoing:**
- **Future WhatsApp Delivery:** Async queue in place via `frappe.enqueue()`, but WhatsApp channel not wired
- **Email Notifications:** Frappe SMTP integration available (not configured in current installation)
- **No third-party SaaS callbacks:** No polling, no event subscriptions to external services

## Background Jobs & Task Processing

**Job Queue:**
- **Framework:** Frappe's async job processor (uses RQ library on Redis)
- **Queue:** `short` queue (default for Tecponto notifications)
- **Processing:** Worker processes spawned by Frappe bench in production
- **Examples:**
  - `tecponto_app.tecponto.notify.send` - In-app notification delivery
  - `tecponto_app.tecponto.requests.expire_requests` - Scheduled request expiration
  - `tecponto_app.tecponto.notify.notify_due_service_orders` - Hourly SLA reminders

**Schedulers (Frappe Scheduled Jobs):**
- No explicit scheduled jobs detected in current hooks
- Can be enabled via Frappe's scheduler system (requires cron or APScheduler)

## Data Exports & Integrations

**Frappe Standard Integrations (Available but Not Configured):**
- ERPNext standard APIs for accounting, inventory sync
- Frappe's bulk import/export via CSV/JSON
- Frappe's REST API for third-party integrations (not exposed externally)

**Tecponto-Specific Data Flows:**
- Service Order print formats → PDF/thermal output (local file system)
- Tracking links → QR codes (in-memory SVG generation)
- POS sales → Sales Invoice (Frappe document, stored in DB)
- Customer device data → Relational schema (MariaDB)

**No SaaS/Cloud Integrations:**
- No Stripe, Square, or payment gateway APIs
- No Shopify, WooCommerce, or e-commerce platform sync
- No CRM (Salesforce, HubSpot) data sync
- No accounting software (Quickbooks, Sage) export

## Security & Compliance

**API Authentication:**
- Frappe built-in role-based access control (permission checks on all DocType operations)
- Frontend enforces role rules before API calls via `roleConfig.tsx`
- Backend enforces via permission query conditions and has_permission hooks

**Data Protection:**
- Encryption key configured for sensitive fields (passwords, device credentials)
- No TLS/SSL configuration visible in local setup (handled by Nginx in production)
- Database password hashed via Frappe's standard password hashing

**Access Audit:**
- `Tecponto Access Audit` custom doctype logs all user additions/removals/changes
- Service Order access scoped by role and technician assignment
- Part Request access restricted by role-based filters

---

*Integration audit: 2026-09-02*
