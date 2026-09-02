# Feature Research

**Domain:** Phone/device repair-shop management software (POS + repair ticket + trade-in + warranty + cash register)
**Researched:** 2026-09-02
**Confidence:** MEDIUM-HIGH (cross-referenced vendor documentation/marketing for RepairShopr, RepairDesk, RepairQ, MicroBiz, CellStore, XEPOS + codebase inspection of existing Tecponto implementation; no primary access to vendor admin panels, so exact UX details are inferred from public docs/comparison pages, not hands-on testing)

## Context: this is a stabilization milestone, not greenfield

Tecponto already has working doctypes/modules for everything in scope: `Tecponto Cash Session` / `Tecponto Cash Movement` / `Tecponto Cash Closing Count` (caixa), `Tecponto POS Sale Request` (PDV), `Trade In Operation` / `Device Trade Evaluation` / `Device Trade Evaluation Checklist` / `Device Trade Harvest Part` (trocas/avaliação de usados), `Used Device Warranty` (garantia de usados), `Tecponto Access Audit` (audit log genérico já existe: actor/affected_user/change_type/before_state/after_state), and `Tecponto Service Order Assignment Event` (precedente de doctype de auditoria dedicado por evento). The 90-day repair warranty rule is already coded in `service_order/policies.py` (`_validate_warranty`, `is_same_warranty_defect`, `_validate_delivery_dates_are_immutable`).

**What this means for research framing:** the question isn't "what features should we build" but "what does the industry consider correct/complete behavior for features that already exist, so we know what to test for and what gaps to close." The table below is framed accordingly — most items are already-built-but-unverified, not greenfield builds.

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing or broken = product feels incomplete or untrustworthy — this is the standard against which the stabilization audit should measure itself.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| POS checkout that understands tickets, parts, labor, taxes, deposits, warranties and trade-ins as one flow | Repair-vertical POS (RepairDesk, RepairQ, CellStore) is sold specifically on not being generic retail POS — checkout must recall an open ticket/quote and apply parts/labor/deposit lines without re-entry | HIGH (already built) | Tecponto: `Tecponto POS Sale Request` + service order billing. Audit target: does checkout ever silently drop a deposit (`sinal`) or double-charge a part already invoiced on the OS? |
| Cash drawer open/close with counted starting float, signed opening/closing, and a shift/Z-report reconciling expected vs counted cash | Universal retail POS pattern; absence is flagged in every POS-reconciliation guide as the #1 shrinkage/fraud vector | MEDIUM (already built) | Tecponto: `Tecponto Cash Session` + `Tecponto Cash Closing Count` + `Tecponto Cash Movement`. Audit target: can a session be closed with a discrepancy silently, or does it force a documented reason? Can two operators open concurrent sessions unintentionally? |
| Trade-in / used-device intake with condition checklist and IMEI/serial capture | Industry standard (RepairDesk, MicroBiz, XEPOS) — trade-in value and later resale/warranty depend on an auditable condition record at intake, not memory | MEDIUM (already built) | Tecponto: `Device Trade Evaluation` + `Device Trade Evaluation Checklist` + `Trade In Operation`. Audit target: does the checklist actually block trade-in completion if empty, mirroring the OS budget-line-required pattern already enforced in `policies.py`? |
| Warranty on resold used devices (fixed days, tied to the sales invoice, defect-scope defined) | Every reseller-facing POS in this niche ties warranty to serial + invoice, not to a manual paper trail | LOW (already built) | Tecponto: `Used Device Warranty` doctype (default 90 days, linked to `serial_no` + `sales_invoice`). Audit target: is `warranty_expiry` actually computed and enforced at claim time, or just stored as data with no gate? |
| A single, visible promised/due date per repair order that the customer and staff can both see | RepairShopr's SLA module and every competitor's "promised completion date" concept exist because a per-line-item deadline (which Tecponto has today via `estimated_deadline`) doesn't answer the one question a customer actually asks: "quando fica pronto?" | LOW–MEDIUM (net-new field + surfacing) | This is the OS.6 gap named in PROJECT.md. Must be visible on tracking page, print formats, and any WhatsApp/SMS-style notification, not just internal Kanban. |
| Ability to edit customer/contact/device info after intake, without re-creating the ticket | Every repair-ticket vendor treats this as baseline — intake data (phone number typos, wrong device model, updated CPF) is corrected constantly in real shop workflows; competitors gate this by role, not by disabling it | LOW–MEDIUM (net-new for OS contact + device credential; customer/CPF edit likely already possible via linked Customer doctype) | Must not break immutability rules already enforced elsewhere (`_validate_delivery_dates_are_immutable`) — editing contact/device fields must stay independent of financial/delivery-date locks. |
| Full audit trail (who, when, before→after) for any edit to customer PII or device credential | Repair-ticket systems market this explicitly ("permanent audit trail... key feature for compliance and accountability"); in Brazil this is not optional — LGPD treats device password/PIN as sensitive data requiring access logs, and "ausência de audit trail é interpretada como ausência de controle, não como ausência de infração" | LOW (infra exists) | Reuse or extend the existing `Tecponto Access Audit` doctype (already has actor/affected_user/change_type/occurred_on/before_state/after_state) rather than inventing a new audit mechanism — same shape already proven for `Tecponto Service Order Assignment Event`. |
| Warranty claim differentiates "same defect → free re-repair" vs "different defect → new paid/discounted order" | This is the de-facto standard across repair verticals (phone, auto) — every source describes exactly this two-branch policy; auto-repair sources are explicit that discounted-not-free is correct once outside strict scope | MEDIUM (already coded, needs E2E proof) | Tecponto: `_validate_warranty` + `is_same_warranty_defect` in `policies.py` already implement this. Gap per PROJECT.md: not yet proven end-to-end (create OS → deliver → day 91 blocked → day 89 passes). This is a **test-writing/verification task, not a feature-building task**. |
| Warranty expiry enforced server-side, not just displayed | Auto-repair and phone-repair sources agree: a warranty policy without an enforced cutoff is a documentation exercise, not a control — matches Tecponto's own security rule (backend is authority, React is presentation) | LOW (already coded) | `getdate(warranty_expiry) < getdate(nowdate())` throw already exists; audit should include a fixture/time-travel test forcing day 91 vs day 89, per the PROJECT.md acceptance test already specified. |
| Device access credential (password/PIN/pattern) always masked by default, revealed only via explicit, audited action | Table stakes specifically because this data type is what LGPD calls "dado sensível" — cross-referenced against Brazilian LGPD guidance: sensitive data requires stricter access control, encryption, shorter retention and *more frequent* auditing than standard data | LOW (already built per CLAUDE.md's sentinel-test rule) | `device_access_credential` is already a Frappe `Password` fieldtype (built-in masking) — the risk is not the field itself but every *other* surface (print formats, tracking page, WhatsApp templates, PDV receipts) that might echo it unmasked. Audit sentinel-test every surface, not just the field definition. |

### Differentiators (Competitive Advantage)

Not required for parity, but what shops actually notice and switch software over.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| A single OS-wide deadline surfaced on the public tracking link and print formats (not just internal) | Competitors' "SLA module" is mostly an internal ops tool; making the promise date customer-visible on the same public tracking page Tecponto already has is a low-cost extension of an existing differentiator (public tracking/aceite-por-link) | LOW (Tecponto already has public tracking infra — `tracking.py`) | This turns a table-stakes internal field into a trust-building customer-facing signal at near-zero extra cost, because the tracking page already exists. |
| Cost/margin guard enforced server-side across every module (PDV, trade-in, garantia, caixa), not just OS | Most repair-shop SaaS (RepairShopr, RepairDesk) expose cost/margin to any staff role with inventory access — a hard backend-enforced role wall across the *entire* system (not just tickets) is unusual in this vertical and is already a core Tecponto principle (CLAUDE.md §1) | HIGH (already built for OS; needs the same audit rigor extended to PDV/trade-in/caixa in this milestone) | This is the single most defensible differentiator this project has — worth explicitly verifying it holds in PDV/trade-in flows too, since those are newer/less-audited modules per PROJECT.md. |
| Warranty rework auto-links to and inherits the original OS's warranty window (cannot be reset by a new ticket) | Prevents the common shop-software failure mode of an employee accidentally (or deliberately) starting a "fresh" warranty clock on a rework ticket | LOW (already coded: `doc.warranty_expiry = warranty_expiry` copy-on-every-validation in `policies.py`) | Framed as a differentiator because most generic ticketing tools don't enforce this at the data layer — it's usually a manual/trust-based policy elsewhere. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|------------------|-------------|
| Letting staff "reopen" a delivered/closed OS to fix an unrelated mistake (à la RepairDesk's reopen-ticket feature) | Convenience — avoids creating a new ticket for small corrections | Directly conflicts with `_validate_delivery_dates_are_immutable` and the warranty-integrity guarantee (a reopened "Entregue" OS could silently extend/reset warranty dates or unlock price edits after invoicing) | Keep RepairQ's stricter model: once `workflow_state == "Entregue"`, only additive/non-financial edits (contact typo, credential correction) are allowed, each individually audited — never a full reopen. This is already the intended shape of PROJECT.md's "editar depois de criado" scope; don't let it grow into a general reopen. |
| A free-text/uncapped warranty override field editable by any role | Feels flexible for edge cases the policy didn't anticipate | Already explicitly blocked by design (`courtesy_warranty` requires Gestor + justification) — widening this to Atendente/Técnico would break the manager-gate pattern that's core to the security model | Keep `courtesy_warranty` Gestor-only with mandatory reason; if new edge cases appear, add them as new named branches in `policies.py`, not a generic override |
| Per-ticket custom/ad-hoc deadline fields set by any role at any stage | Seems like flexibility for special cases | Reintroduces exactly the ambiguity PROJECT.md is trying to close (today: only a per-service-line `estimated_deadline` exists, and it's unclear which one is "the" promise) — a second parallel deadline field would make the confusion worse, not better | One OS-wide deadline field, settable only by the technician at orçamento stage (per Key Decision already logged in PROJECT.md); per-service `estimated_deadline` stays as internal planning detail, not the customer-facing promise |
| Unmasking the device credential inline in any list/grid view "for convenience" | Saves a click for staff who look up the credential often | This is precisely the sentinel-tested leak surface CLAUDE.md calls out by name — a list view is the highest-risk surface because it's rendered in bulk, cached, and easy to screenshot/export | Keep credential reveal a single-record, explicit, audited action (already the Frappe `Password` fieldtype pattern) — never expose it in list/report views |
| Building a brand-new generic audit-log framework/doctype for this feature | The existing `Tecponto Access Audit` doctype's fields (actor/affected_user) read as user-permission-specific, tempting a "cleaner" new schema for check-in edits | Duplicating audit infrastructure fragments where auditors/devs have to look for history, and risks the new one being less rigorously permissioned than the proven one | Reuse or lightly extend `Tecponto Access Audit` (or replicate its exact shape as a new event-type doctype, following the `Tecponto Service Order Assignment Event` precedent) — don't invent a third pattern |

## Feature Dependencies

```
[OS-wide delivery deadline field]
    └──requires──> [Orçamento/budget stage already exists] (satisfied — orçamento stage exists)
    └──enhances──> [Public tracking page] (surfacing the promise date builds customer trust)

[Post-creation edit of check-in info]
    └──requires──> [Audit trail mechanism] (Tecponto Access Audit pattern)
    └──must NOT weaken──> [Delivery-date immutability rule] (_validate_delivery_dates_are_immutable)
    └──must NOT weaken──> [Device credential masking guarantee]

[90-day warranty E2E verification]
    └──requires──> [Time-travel/fixture test harness] (day 91 vs day 89 acceptance test named in PROJECT.md)
    └──depends on──> [warranty_expiry immutability already enforced in policies.py]

[PDV/trade-in/garantia/caixa stabilization audit]
    └──requires──> [Cost/margin guard verified in each module] (not just OS — this is the actual risk surface)
    └──uses same method as──> [OS cycle audit already done this session] (8 bugs found/fixed — same rigor should apply here)

[Design system application]
    └──requires──> [All functional stabilization above complete] (explicit constraint in CLAUDE.md — never polish before functional/stable)
```

### Dependency Notes

- **Post-creation edit requires audit trail:** LGPD framing makes this non-optional, not just good practice — an edit path to sensitive data (device credential) without a logged before/after state is itself the compliance gap, per LGPD sensitive-data guidance found in research.
- **Post-creation edit must not weaken delivery-date immutability:** the new "edit after creation" capability and the existing `_validate_delivery_dates_are_immutable` guard operate on overlapping doc fields; implementation must scope the new edit permission narrowly (contact name/phone, device credential, customer name/CPF) and explicitly exclude `pickup_date`/`warranty_expiry` from the editable set.
- **PDV/trade-in/garantia/caixa audit uses the same method as the OS audit:** PROJECT.md explicitly frames this as applying the proven method (find real bugs via real end-to-end testing, not fixtures) to the modules that weren't tested in the prior session — this is a process dependency, not a technical one.
- **Design system application requires everything above to be done:** hard-blocked by CLAUDE.md §3.2 — no exceptions, no "just this one screen while we're in there."

## MVP Definition

This is a stabilization milestone; "MVP" here means the minimum verified-correct state to call the milestone done, not a product launch MVP.

### Launch With (v1 of this milestone)

- [ ] PDV, trocas/avaliação, garantia-de-usados, caixa audited end-to-end with real transactions (not fixtures), bugs catalogued and fixed — mirrors the rigor already applied to the OS cycle
- [ ] 90-day repair-warranty rule proven end-to-end with a real create→deliver→day-91-blocked / day-89-passes test — the rule already exists in code; this closes the "não confirmada" gap
- [ ] Single OS-wide delivery deadline field, settable only by technician at orçamento stage, surfaced on tracking page + print formats
- [ ] Post-creation edit of OS contact (name/phone), device access credential, and customer data (name/CPF), each edit audited with before/after state via the existing audit-log pattern
- [ ] Cost/margin guard confirmed to hold in PDV/trade-in flows specifically (not just OS) — this is the actual security-critical item hiding inside "stabilize PDV/trade-in"

### Add After Validation (later, still pre-design-system)

- [ ] Deploy readiness checks (Coolify, print físico, leitura QR/código de barras) — explicitly sequenced after functional stability, per PROJECT.md Active list ordering

### Future Consideration (explicitly Out of Scope per PROJECT.md)

- [ ] Multi-tenant / instância modelo escalável — deferred, single-instance-per-client is the current model
- [ ] Fiscal (NF-e/NFS-e homologado), SMTP, billing/trial, PWA — explicit "capítulo produto" deferral
- [ ] Autosave/rascunho, busca inteligente, portal configurável, orçamento separado da OS — explicitly named as post-piloto, non-blocking

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|----------------------|----------|
| PDV/trade-in/garantia/caixa E2E audit + bugfix | HIGH | MEDIUM (testing-heavy, not building) | P1 |
| 90-day warranty E2E proof | HIGH (trust + legal exposure) | LOW (test-writing on existing code) | P1 |
| OS-wide single deadline | HIGH (customer-facing clarity) | LOW–MEDIUM | P1 |
| Post-creation edit + audit trail | MEDIUM–HIGH (LGPD + operational reality) | LOW–MEDIUM (infra exists) | P1 |
| Design system definition + single-pass application | MEDIUM (perceived quality) | MEDIUM | P2 (explicitly sequenced after P1s) |
| Deploy readiness (Coolify, impressão, QR) | HIGH (blocks piloto going live) | MEDIUM | P2 (sequenced last per PROJECT.md) |

## Competitor Feature Analysis

| Feature | RepairShopr | RepairDesk / RepairQ | Tecponto's approach |
|---------|-------------|------------------------|----------------------|
| Deadline/promise date | SLA module: assign a resolution-time promise per ticket or per contract | Ticket-level due dates as standard field; RepairDesk allows reopening closed tickets, RepairQ deliberately does not | Adopt RepairQ's stricter stance (no full reopen of "Entregue") but adopt the promise-date-as-customer-visible-signal idea via existing public tracking page |
| Cost/margin visibility | Role-based but generally exposed to any staff with inventory/reporting access | Similar — margin visibility tends to be a report-permission toggle, not a hard backend wall | Tecponto's backend-never-serializes-cost rule is stricter than typical vendor default — a genuine differentiator, worth protecting during the PDV/trade-in audit |
| Warranty same-defect vs different-defect | Not explicitly documented as a two-branch policy in available sources | Warranty tracked "alongside device info" per marketing copy; specific same/different-defect branching not documented publicly | Tecponto already codes this explicitly in `policies.py` — ahead of what's publicly described for competitors |
| Audit trail on edits | Ticket activity/timestamp history is standard | Same — timestamped update history is treated as baseline compliance feature | Tecponto's `Tecponto Access Audit` + per-event doctypes (`..._Assignment_Event`) are more structured (before/after state capture) than typical vendor "activity log" |
| Cash drawer reconciliation | Not distinctly documented per-product; general POS/retail pattern applies | Same — general retail POS pattern (Z-report, signed open/close) | Tecponto's `Tecponto Cash Session`/`Cash Closing Count` maps to this pattern already; audit should confirm discrepancies can't be silently closed |

## Sources

- [RepairQ vs RepairShopr — Capterra](https://www.capterra.com/computer-repair-shop-software/compare/158385-133945/RepairQ-vs-RepairShopr) — MEDIUM confidence (vendor-comparison aggregator)
- [RepairDesk vs RepairQ — RepairDesk Blog](https://blog.repairdesk.co/2024/03/15/repairdesk-vs-repairq-the-best-pos-software-for-cell-phone-repair-shops/) — MEDIUM confidence (vendor-authored, directional bias expected, cross-checked against SourceForge/Capterra)
- [RepairDesk vs RepairShopr — RepairDesk](https://www.repairdesk.co/repairdesk-vs-repairshopr/) — MEDIUM confidence (vendor-authored)
- [RepairDesk vs RepairShopr — CellSmartPOS](https://www.cellsmartpos.com/blog/repairdesk-vs-repairshopr) — MEDIUM confidence (third-party blog, still vendor-adjacent)
- [RepairDesk vs RepairQ vs RepairShopr — SourceForge](https://sourceforge.net/software/compare/RepairDesk-vs-RepairQ-vs-RepairShopr/) — MEDIUM confidence (aggregator)
- [Point of Sale Software for Repair Shops — RepairDesk](https://www.repairdesk.co/features/point-of-sale-software/) — MEDIUM confidence (vendor feature page)
- [Repair Store POS & Repair Tracking Software](https://www.repairstorepos.com/) — MEDIUM confidence (vendor site)
- [MicroBiz Electronics Store POS](https://microbiz.com/electronics-store-pos/) — MEDIUM confidence (vendor site, cross-referenced for trade-in/IMEI tracking claims)
- [Estimates — RepairShopr Help Center](https://repair.uservoice.com/knowledgebase/articles/1851796-estimates) — MEDIUM-HIGH confidence (official product docs)
- [Tickets — RepairShopr Help Center](https://repair.uservoice.com/knowledgebase/articles/1851781-tickets) — MEDIUM-HIGH confidence (official product docs)
- [Repair Ticket Management Software — RepairDesk](https://www.repairdesk.co/features/repair-ticket-management-software/) — MEDIUM confidence (vendor feature page)
- [Viewing the audit trail for tickets — BMC Track-It Docs](https://docs.bmc.com/xwiki/bin/view/More-Products/Track-IT/Track-It/Track-It-2025/Using/Using-For-technicians/Viewing-the-audit-trail-for-tickets/) — HIGH confidence (official product documentation, general ticketing not repair-specific but directly on-topic for audit-trail behavior)
- [POS Reconciliation in Retail — GoFTX](https://goftx.com/blog/pos-reconciliation-guide/) — MEDIUM confidence (industry blog, cross-referenced against Fit Small Business and Cointab)
- [Auto Repair Warranties: How to Write a Policy — Mechanics App](https://mechanics.app/blog/auto-repair-warranty-policy) — MEDIUM confidence (adjacent vertical — auto repair, not phone — used only for the same-defect/different-defect and time-boxed-warranty pattern, which generalizes across repair verticals)
- [Vazamento de dados pessoais em assistência técnica — LGPD Brasil](https://lgpdbrasil.com.br/vazamento-de-dados-pessoais-em-assistencia-tecnica-responsabilidades-e-implicacoes/) — MEDIUM-HIGH confidence (LGPD-focused legal/compliance content, directly on-topic for device-credential handling obligations)
- [Dados Sensíveis na LGPD — Barbieri Advogados](https://www.barbieriadvogados.com/dados-sensiveis-na-lgpd/) — MEDIUM-HIGH confidence (legal-practice content on sensitive-data audit/retention obligations)
- Codebase inspection (Read/Grep) of `tecponto_app/tecponto/service_order/policies.py`, `tecponto_app/tecponto/doctype/*` (service_order, tecponto_access_audit, used_device_warranty, trade_in_operation, device_trade_evaluation*, tecponto_cash_session, tecponto_cash_closing_count, tecponto_cash_movement, tecponto_pos_sale_request, tecponto_service_order_assignment_event) — HIGH confidence (primary source, current repo state)

---
*Feature research for: phone/device repair-shop management software (Tecponto ERP stabilization milestone)*
*Researched: 2026-09-02*
