# Phase 1: OS.6 Closure — Warranty Verification & Deadline Wiring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-03
**Phase:** 1-os-6-closure-warranty-verification-deadline-wiring
**Areas discussed:** Escopo do teste de garantia, Quem/quando define o prazo, UX do campo de prazo, Onde e como aparece

---

## Escopo do teste de garantia

| Option | Description | Selected |
|--------|-------------|----------|
| Estender `run_warranty_delivery_checks()` | Adicionar as 2 asserções de limite (dia 89/91) no teste já existente e já wired no CI | ✓ (Claude's discretion) |
| Escrever teste novo dedicado | Um `run_*_checks()` separado só pra essa fronteira | |

**User's choice:** Delegado ("o que for melhor").
**Notes:** Achado de código que motivou a decisão: `run_warranty_delivery_checks()` já cobre rework/config/defeito-diferente/vencido(-10 dias); só faltava o limite exato.

---

## Quem/quando define o prazo

| Option | Description | Selected |
|--------|-------------|----------|
| Só Técnico, na etapa de orçamento, opcional, editável até "Entregue" | Consistente com o lock já existente de `pickup_date`/`warranty_expiry` | ✓ (Claude's discretion) |
| Obrigatório pra enviar orçamento | Trava adicional na submissão do orçamento | |
| Editável a qualquer momento, mesmo após entrega | | |

**User's choice:** Delegado.
**Notes:** Comentário existente em `api.py:2253` ("Prazo pertence ao diagnóstico/orçamento, não à Entrada") confirma a intenção original de design.

---

## UX do campo de prazo

| Option | Description | Selected |
|--------|-------------|----------|
| Sugestão pré-preenchida via `calculate_suggested_delivery()` | Reusa código morto já existente, editável pelo técnico | ✓ (Claude's discretion) |
| Campo livre sem sugestão | Técnico digita a data do zero | |

**User's choice:** Delegado.
**Notes:** `calculate_suggested_delivery()` nunca é chamado em produção hoje — achado confirmado por grep completo do repo.

---

## Onde e como aparece

| Option | Description | Selected |
|--------|-------------|----------|
| Reusar label "Prazo estimado" já existente nas impressões | Consistência de copy, sem inventar texto novo | ✓ (Claude's discretion) |
| Nova copy específica por superfície | | |

**User's choice:** Delegado.
**Notes:** Label já usada em `print_formats.py:587,647`; parser de data já padronizado em `frontend/src/utils/date.ts` (trabalho desta mesma sessão).

---

## Claude's Discretion

Todas as 4 áreas foram decididas por Claude após o usuário delegar explicitamente ("o que for melhor"), com base em evidência concreta do código (grep/leitura direta), não em suposição. Ver `01-CONTEXT.md` para as decisões D-01 a D-06.

## Deferred Ideas

Nenhuma — a discussão ficou dentro do escopo da fase.
