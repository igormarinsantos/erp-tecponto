# Phase 3: Systematic Audit — PDV → Trade-in → Warranty (Aparelho Usado) → Caixa - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-14
**Phase:** 3-systematic-audit-pdv-trade-in-warranty-aparelho-usado-caixa
**Areas discussed:** Fluxo real de garantia de aparelho usado, Priorização da fase

---

## Fluxo real de garantia de aparelho usado

| Option | Description | Selected |
|--------|-------------|----------|
| Vira uma OS normal, só bloqueando se vencida | Abrir Service Order, consultar Used Device Warranty primeiro | (usuário optou por descrever livremente) |
| Fluxo próprio, sem virar OS | | |
| Não sei / deixa eu descrever | | ✓ |

**User's choice (texto livre):** "quando o aparelho que ele comprou volta normalmente fazemos o reparo ai a gente abre uma nova os, mas que nao conta valor ne so pra ter controle e sendo assim reparamos, tambem tem a opcao de troca de aparelho mas é raro raro raro dificilmente"
**Notes:** Confirma que hoje é 100% manual — abrir OS "que não conta valor" é uma convenção operacional, não uma trava do sistema. Troca do aparelho existe mas é rara, fora do escopo de automação desta fase.

---

## Garantia vencida — o que acontece

| Option | Description | Selected |
|--------|-------------|----------|
| Vira OS normal cobrada | Mesmo padrão já usado na garantia de reparo (defeito diferente → OS normal com desconto) | ✓ |
| Bloquear e exigir aprovação do Gestor | | |

**User's choice:** Vira OS normal cobrada.
**Notes:** Confirma reusar o precedente conceitual já implementado em `policies.py` (`is_same_warranty_defect`) para a garantia de aparelho usado — mesmo espírito, doctype diferente.

---

## Priorização da fase

| Option | Description | Selected |
|--------|-------------|----------|
| Ligar os 4 órfãos primeiro | Fecha o maior buraco de CI com risco quase zero | ✓ |
| Seguir ordem original PDV→Trocas→Garantia→Caixa | | |

**User's choice:** Ligar os 4 órfãos primeiro.
**Notes:** Achado nesta sessão: `run_pos_sale_checks`, `run_warranty_mode_checks`, `run_pos_barcode_label_checks`, `run_pos_retail_barcode_catalog_checks` já existem, já são completos, e já passam — só nunca foram chamados por `run_foundation_checks`.

---

## Claude's Discretion

Nenhuma — usuário fechou todas as decisões relevantes desta fase.

## Deferred Ideas

- Troca de aparelho como resolução de garantia de usado (rara) — não automatizar/testar formalmente nesta fase.
