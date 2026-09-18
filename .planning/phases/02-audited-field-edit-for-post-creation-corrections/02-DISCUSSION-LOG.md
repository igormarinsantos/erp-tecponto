# Phase 2: Audited Field-Edit for Post-Creation Corrections - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-18
**Phase:** 2-audited-field-edit-for-post-creation-corrections
**Areas discussed:** Doctype de auditoria, Auditoria da credencial do aparelho, Gate de acesso e justificativa, Visibilidade da trilha de auditoria

---

## Doctype de auditoria

| Option | Description | Selected |
|--------|-------------|----------|
| Estender `Tecponto Access Audit` | Adicionar `reference_doctype`/`reference_name` genéricos, reusar para User/OS/Customer | ✓ |
| Criar doctype paralelo novo | Ex.: "Tecponto Edit Audit", mesma estrutura mas separado | |

**User's choice:** Pediu recomendação explícita ("qual é o recomendado?") em vez de escolher direto.
**Assistant's recommendation (accepted):** Estender o doctype existente — o requisito já pede reuso literal do padrão, os hooks de imutabilidade e a permissão já existem e servem pra qualquer linha, e uma trilha única é mais fácil de auditar. Único ajuste necessário: relaxar `affected_user` (hoje `Link` obrigatório pra `User`) e adicionar campos de Dynamic Link genéricos.

---

## Auditoria da credencial do aparelho

| Option | Description | Selected |
|--------|-------------|----------|
| Só metadado, nunca o valor | Registra só tipo de acesso e booleano de existência; nunca o valor real, nem mascarado | ✓ |
| Guardar versão mascarada | Comprimento/último caractere da credencial no log | |

**User's choice:** Só metadado, nunca o valor.
**Notes:** Consistente com CLAUDE.md §1.2 — a credencial nunca pode trafegar fora do campo `Password` criptografado, nem no próprio log de auditoria que existe pra proteger justamente esse dado.

---

## Gate de acesso e justificativa

| Option | Description | Selected |
|--------|-------------|----------|
| Atendente+Gestor, sem justificativa obrigatória | Mesmo gate de `update_service_order_entry` hoje; antes/depois automático já é a evidência | ✓ |
| Exigir justificativa por escrito | Motivo digitado, gravado junto no audit log | |
| Restringir a Gestor apenas | Atendente não participa | |

**User's choice:** Atendente+Gestor, sem justificativa obrigatória.
**Notes:** Diferente de `courtesy_warranty`/`path_conversion_reason` (exceções de política que precisam de motivo) — aqui é correção pontual de dado cadastral, o snapshot automático já basta.

---

## Visibilidade da trilha de auditoria

| Option | Description | Selected |
|--------|-------------|----------|
| Só backend | Log gravado e imutável, consultável só via relatório/DocType list (System Manager/Diretor) | |
| Trilho visível na tela | Indicador tipo "editado por Fulano em DD/MM" na tela da OS/Cliente pro Gestor/Diretor | ✓ |

**User's choice:** Trilho visível na tela.

---

## Claude's Discretion

- Exato valor de string de `change_type` por tipo de edição.
- Forma/posicionamento exato do indicador "editado por X em Y" na UI.
- Se o novo endpoint de edição de Customer reusa `validate_customer_contact_document` diretamente ou embrulha ela.

## Deferred Ideas

- Log de auditoria toda vez que a credencial do aparelho é **revelada** pra impressão interna (`get_internal_service_order_print_context`) — achado durante o scouting desta fase, é uma lacuna pré-existente separada (reveal-for-print, não correção pós-criação), fora do texto literal de EDIT-02. Vale um follow-up dedicado.
- Estender o padrão genérico de `reference_doctype`/`reference_name` pra outros doctypes além de Service Order/Customer — nenhum candidato identificado ainda.
