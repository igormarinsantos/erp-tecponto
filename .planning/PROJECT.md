# Tecponto ERP

## What This Is

ERP para assistências técnicas de celular, sobre Frappe/ERPNext v16 (Python) + React/Vite/TypeScript. Cobre o ciclo completo de uma ordem de serviço (OS) — check-in, diagnóstico, orçamento, aprovação, execução, retirada — mais PDV, trocas/avaliações de usados, garantias e caixa. Em produção, com um piloto real na loja "Rafacel". Não é greenfield: já tem fundação, papéis (Atendente/Técnico/Gestor/Diretor), aceite por link/selfie, rastreio público, CI em 3 estágios e deploy via Coolify.

## Core Value

O balcão consegue rodar o dia a dia real — check-in até retirada, PDV, trocas/garantias, caixa — sem quebrar no meio e sem vazar dado sensível (custo/margem, senha do aparelho). Confiança operacional vem antes de polimento visual.

## Business Context

- **Customer**: loja "Rafacel" (piloto atual); modelo de instância por cliente (não multi-tenant ainda).
- **Revenue model**: ERP vertical para assistências técnicas — instância dedicada por cliente.
- **Success metric**: sistema roda o ciclo operacional completo sem erro em teste real (não só CI); zero bug crítico dos que já apareceram (sessão morrendo, dado sensível vazando, trava de negócio pulada) reaparecendo.
- **Strategy notes**: `STATUS_PROJETO.md`, `REGUA_PRODUTO.md`, `FRENTE_OS_plano_aprovado.md`, `AUDITORIA_SISTEMA.md` (fora do `.planning/` do GSD, na pasta de docs do projeto).

## Requirements

### Validated

- ✓ Motor de dados Frappe/ERPNext v16 com 4 papéis (Atendente/Técnico/Gestor/Diretor) e guard de custo no backend — existing
- ✓ Ciclo principal da OS (Entrada → Diagnóstico e Orçamento → Aprovação → Execução → Retirada) como trilho de etapas, testado ponta a ponta nesta sessão (8 bugs achados e corrigidos: sessão morrendo, aprovação sem evidência, aceite invisível, retirada travada, Kanban sem técnico, datas de fuso, indicadores cosméticos) — existing, `AUDITORIA_SISTEMA.md`
- ✓ PDV, aceite por link/selfie, rastreio público, agenda/prazos, gestão de usuários, identidade comercial configurável — existing (não testados nesta sessão)
- ✓ CI em 3 estágios (validação rápida → detecção de mudança de imagem → suíte de integração completa em site Frappe efêmero) — existing, verde no commit `ab29af3`
- ✓ Regra dos 90 dias de garantia (mesmo defeito grátis, defeito diferente com desconto) implementada em `service_order/policies.py` — existing, ponta a ponta ainda não confirmada

### Active

- [ ] Auditar PDV, trocas/avaliações, garantias e caixa com teste real ponta a ponta (mesmo rigor usado no ciclo de OS), catalogando e corrigindo bugs achados
- [ ] Fechar OS.6 (Execução e Retirada): confirmar garantia de 90 dias ponta a ponta (criar OS, entregar, tentar abrir garantia no dia 91 deve bloquear, no dia 89 deve passar)
- [ ] Fechar OS.6: prazo único da OS definido pelo técnico no orçamento (campo novo, hoje só existe `estimated_deadline` por linha de serviço)
- [ ] Fechar OS.6: permitir editar, depois de criado, contato da OS (nome/telefone), credencial do aparelho (mascarada + log de auditoria) e dados do cliente (nome/CPF)
- [ ] Definir e documentar um design system (cores, tipografia, componentes) — hoje não existe formalizado
- [ ] Aplicar o design system em passada única, depois de tudo funcional e estável (nunca antes)
- [ ] Preparar e validar deploy real no Coolify para o piloto (Rafacel), incluindo impressão física e leitura de QR/código de barras

### Out of Scope

- Multi-tenant / automação de instância modelo 2 — modelo atual é uma instância por cliente, escalar é decisão futura
- Fiscal (NF-e/NFS-e homologado), SMTP, billing/trial, PWA — capítulo "produto" (quando for vender), fora do escopo deste plano até deploy do piloto
- Autosave/rascunho, busca inteligente, portal configurável, orçamento separado da OS — pós-piloto, não bloqueiam

## Context

- Backend: Frappe Framework / ERPNext v16 (Python). Frontend: React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons. Banco: MariaDB 10.6, Redis.
- Repositório real: `/home/usuario/frappe-bench/apps/tecponto_app` (WSL Ubuntu, branch `version-16`). A pasta Windows `C:\Users\usuario\Desktop\TECPONTO ERP` guarda só documentos de planejamento pré-existentes, não é o repo.
- Sessão anterior a este projeto GSD: auditoria real (não fixture) do ciclo de OS achou e corrigiu 8 bugs + 3 bugs pré-existentes que travavam o CI (campo de senha renomeado sem atualizar teste, condição de transição de workflow nunca avaliada, teste chamando função que nunca existiu). CI fechou 100% verde no commit `ab29af3` (run `33671932429`).
- Codebase mapeado nesta sessão em `.planning/codebase/` (STACK, ARCHITECTURE, STRUCTURE, CONVENTIONS, TESTING, INTEGRATIONS, CONCERNS) — `CONCERNS.md` já aponta débito técnico adicional: `App.tsx` com ~9500 linhas, `api.py` com ~5300 linhas, bundle de 861kB sem code-splitting, lacunas de teste em reatribuição multi-técnico e expiração de link de rastreio.
- Motivação direta desta iniciativa: muitas alterações anteriores deixaram o sistema "mais confuso" e coisas que funcionavam pararam de funcionar — o usuário quer confiança real (testada, não só codada) antes de investir em design e deploy.

## Constraints

- **Segurança (não-negociável, `CLAUDE.md`)**: Atendente/Gestor/Técnico nunca veem custo/margem/lucro — só o Diretor, via endpoint dedicado. O backend nunca serializa custo pros outros papéis, não basta esconder no frontend.
- **Segurança**: senha/PIN/padrão do aparelho é dado sensível, armazenamento criptografado, sempre mascarado no frontend, revelado só sob ação intencional auditada. Testado continuamente com valores-sentinela.
- **Segurança**: as 6 travas de ciclo de vida da OS, gates de papel e validação de aceite biométrico/físico vivem no motor Python — o React é só apresentação.
- **Processo (`CLAUDE.md`)**: tarefas pequenas e atômicas, testar comportamento real de ponta a ponta antes de declarar pronto, commit isolado por tarefa, reiniciar servidor local após mudança Python (`--noreload`), CI de 3 estágios é a verdade final.
- **Design**: raciocinar hierarquia visual antes de construir; polimento estético em passada única no fim, não tela por tela durante a fase funcional.
- **Jurídico**: termos e aceite físico precisam de revisão de advogado antes do uso pra valer (ainda pendente, per `STATUS_PROJETO.md`).
- **Ambiente local**: Docker no Windows/WSL2 é instável (containers recebem shutdown normal sozinhos) — mitigado com `scripts/dev-local-server.sh`, mas testes locais longos podem precisar reiniciar db/redis no meio.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Escopo do plano é o sistema inteiro (OS + PDV + trocas/garantias + caixa), não só OS.6 | Muitas alterações anteriores quebraram partes que funcionavam — usuário quer confiança testada em tudo antes do deploy, não só na OS | — Pending |
| Prazo técnico vira um campo novo de prazo único da OS (definido pelo técnico no orçamento), não só o `estimated_deadline` por serviço que já existe | Decisão do usuário ao fechar a ambiguidade encontrada no código | — Pending |
| Design system é fase separada, só depois de tudo funcional/estável | Alinhado com o princípio já existente em `CLAUDE.md` (polimento em passada única no fim) e com o pedido explícito do usuário | — Pending |
| GSD inicializado dentro do repo real (WSL), não na pasta Windows de docs | `CLAUDE.md` proíbe tratar a pasta Windows como o repo de trabalho | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-02 after initialization*
