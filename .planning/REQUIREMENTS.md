# Requirements: Tecponto ERP

**Defined:** 2026-09-03
**Core Value:** O balcão consegue rodar o dia a dia real — check-in até retirada, PDV, trocas/garantias, caixa — sem quebrar no meio e sem vazar dado sensível. Confiança operacional vem antes de polimento visual.

## v1 Requirements

Requisitos deste marco (estabilização do sistema inteiro até o deploy do piloto). Cada um mapeia pra uma fase do roadmap.

### Auditoria e Estabilização (PDV, Trocas, Garantia, Caixa)

- [x] **AUDIT-01**: PDV processa venda com peça + mão de obra + depósito sem duplicar cobrança nem perder o valor do sinal (testado com transação real, não fixture)
- [x] **AUDIT-02**: Sessão de caixa não fecha com divergência sem motivo documentado; duas sessões concorrentes não abrem sem aviso
- [x] **AUDIT-03**: Avaliação de troca bloqueia conclusão sem checklist de condição preenchido
- [x] **AUDIT-04**: Guarda de custo/margem confirmada sem vazamento em PDV e trocas (não só na OS) — Atendente/Gestor/Técnico nunca recebem esse dado no payload
- [x] **AUDIT-05**: Garantia de aparelho usado (`Used Device Warranty`) tem expiração calculada e checada de verdade no momento da reivindicação, não só armazenada como dado

### Garantia de 90 Dias (fechamento OS.6)

- [x] **WARR-01**: Criar OS → entregar → tentar reivindicar garantia no dia 91 é bloqueado; no dia 89 passa (teste real de ponta a ponta, não só leitura de código)

### Prazo Único da OS (fechamento OS.6)

- [x] **DEADLINE-01**: Técnico define o prazo único da OS na etapa de orçamento — `estimated_deadline` (já existe a nível de OS) ganha caminho de escrita
- [x] **DEADLINE-02**: Prazo aparece na página de rastreio pública e nos formatos de impressão

### Edição Pós-Criação + Auditoria (fechamento OS.6)

- [x] **EDIT-01**: Atendente/Gestor pode editar contato da OS (nome/telefone) depois de criado, com log de auditoria (quem/quando/antes/depois), reusando o padrão `Tecponto Access Audit`
- [x] **EDIT-02**: Credencial do aparelho pode ser corrigida depois de criada, permanecendo mascarada, com log de auditoria
- [x] **EDIT-03**: Dados do cliente (nome/CPF) podem ser corrigidos, com log de auditoria
- [x] **EDIT-04**: A capacidade de edição nunca abre brecha pra alterar data de entrega (`pickup_date`) ou expiração de garantia (`warranty_expiry`) — permanecem imutáveis

### Design System

- [ ] **DESIGN-01**: Design system documentado (cores, tipografia, componentes) — não existe formalizado hoje
- [ ] **DESIGN-02**: Design system aplicado em passada única, só depois de todos os itens acima estarem funcionais e testados

### Deploy

- [ ] **DEPLOY-01**: Deploy real no Coolify validado para o piloto (Rafacel)
- [ ] **DEPLOY-02**: Impressão física e leitura de QR/código de barras validadas no ambiente real

## v2 Requirements

Reconhecidos pela pesquisa, mas fora do escopo deste marco (deferidos).

### Consolidação Técnica

- **TECH-01**: CI grep-gate anti-`frappe.set_user()` (reusa o mecanismo já existente do `verify-foundation.mjs`)
- **TECH-02**: Split gradual de `test_frontend_api.py` por domínio (`test_pos_api.py`, `test_cash_api.py`, `test_tradein_api.py`, `test_service_order_edit_api.py`)
- **TECH-03**: Split incremental de `App.tsx` (~9500 linhas) e `api.py` (~5300 linhas), trilhando cada área já auditada — nunca precedendo a auditoria

## Out of Scope

Explicitamente excluído deste marco. Documentado pra não reabrir depois.

| Feature | Reason |
|---------|--------|
| Multi-tenant / instância modelo escalável | Modelo atual é uma instância por cliente; escalar é decisão futura de produto |
| Fiscal (NF-e/NFS-e homologado) | Capítulo "produto" (quando for vender), fora do escopo até o deploy do piloto |
| SMTP (recuperação de senha, notificações) | Capítulo "produto" |
| Billing/trial | Capítulo "produto" |
| PWA (app do cliente/operador) | Capítulo "produto" |
| Autosave/rascunho | Pós-piloto, não bloqueia |
| Busca inteligente | Pós-piloto, não bloqueia |
| Portal configurável + banner LGPD | Pós-piloto, não bloqueia |
| Orçamento separado da OS (mudança de modelo) | Pós-piloto, não bloqueia |
| Reabrir uma OS "Entregue" pra correção geral (estilo RepairDesk) | Conflita com `_validate_delivery_dates_are_immutable` e a garantia de integridade da garantia — só edição pontual e auditada (EDIT-01/02/03), nunca reabertura completa |
| Campo de garantia com override livre por qualquer papel | Já bloqueado por design (`courtesy_warranty` exige Gestor + justificativa) — ampliar quebraria o gate de gestor |
| Segundo campo de prazo por serviço além do `estimated_deadline` OS-level | Reintroduziria a ambiguidade que este marco está fechando — um único prazo, definido pelo técnico no orçamento |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUDIT-01 | Phase 3 | Complete |
| AUDIT-02 | Phase 3 | Complete |
| AUDIT-03 | Phase 3 | Complete |
| AUDIT-04 | Phase 3 | Complete |
| AUDIT-05 | Phase 3 | Complete |
| WARR-01 | Phase 1 | Complete |
| DEADLINE-01 | Phase 1 | Complete |
| DEADLINE-02 | Phase 1 | Complete |
| EDIT-01 | Phase 2 | Complete |
| EDIT-02 | Phase 2 | Complete |
| EDIT-03 | Phase 2 | Complete |
| EDIT-04 | Phase 2 | Complete |
| DESIGN-01 | Phase 4 | Pending |
| DESIGN-02 | Phase 4 | Pending |
| DEPLOY-01 | Phase 5 | Pending |
| DEPLOY-02 | Phase 5 | Pending |

**Coverage:**

- v1 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-03*
*Last updated: 2026-09-03 after roadmap creation (ROADMAP.md, 5 phases)*
