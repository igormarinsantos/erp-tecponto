# Fase 3 (reformulada) — Front-end Tecponto (guia otimizado para Codex)

> **Decisão do dono:** em vez de polir a interface do Frappe, construímos o **front-end próprio da Tecponto** — as 5 telas de referência (imagens anexadas pelo dono) — consumindo a API do `tecponto_app`. Sem pressa, sem gambiarra.
>
> Pré-requisito: Fase 2 completa (ciclo cruzado verde) + caçada de encoding concluída (`c649766`).

## PRINCÍPIOS INEGOCIÁVEIS (leia duas vezes)
1. **O front é 100% casca.** Toda regra de negócio permanece no `tecponto_app` (Fases 2.x). O front NUNCA: calcula comissão, decide se pode entregar, baixa estoque, valida margem. Ele chama a API e exibe. Se uma regra parecer faltar na API, a solução é expor um endpoint whitelisted no app — nunca reimplementar a regra em JavaScript.
2. **Segurança no servidor.** O que o papel não pode ver, a API não retorna (perm levels da 2.0). O front não "esconde" dado que chegou — se chegou dado sensível a quem não devia, o bug é na API e é lá que se conserta.
3. **O Frappe Desk continua vivo** como sala de máquinas (configurações, fixtures, relatórios exóticos, admin). O front cobre a OPERAÇÃO (5 telas + fluxos). Não reconstruir telas de administração profunda.
4. **Mesma disciplina:** uma etapa por vez → teste → commit. Windows/PowerShell: sem `&&`; usar `scripts/use_utf8.ps1` antes de sessões que geram arquivos.

## STACK (decidida — não reabrir)
- **React 18 + Vite + TypeScript**, servido pelo próprio Frappe (pasta `frontend/` dentro do `tecponto_app`, build para `tecponto_app/public/frontend`, página `/tecponto` via `website_route_rules`). Sem servidor extra, deploy junto do app.
- **frappe-react-sdk** (ou chamadas fetch tipadas à REST/RPC do Frappe) para dados; autenticação pela **sessão do Frappe** (login existente, roles existentes).
- **Tailwind CSS** com design tokens extraídos das imagens de referência (tema dark, laranja Tecponto como accent, cores de status iguais às do Kanban).
- Roteamento por papel: ao logar, a role define o painel inicial (Atendente/Técnico/Gestor/Diretor).

---

## Etapa 3.0 — Fundação do front
**Constrói:**
- Scaffold `frontend/` (Vite+React+TS+Tailwind) dentro do app; build integrado; página `/tecponto` servida pelo Frappe com sessão.
- **Autenticação/roles:** usuário logado no Frappe entra direto; `get_logged_user` + roles determinam o painel; logout.
- **Camada de API** (`src/api/`): cliente tipado com funções por domínio (serviceOrders.list, serviceOrders.approve, pos.createSale...). Toda chamada nomeada, nada de fetch solto em componente.
- **Design system** (`src/ui/`): tokens (cores/tipografia/espaçamento das imagens), componentes base — Card de métrica, Badge de status (cores do workflow), Tabela, Sidebar, Topbar com busca, Botão, Modal, Toast.
- **Guard de dados sensíveis:** teste automatizado que loga como Técnico e verifica que respostas da API usadas pelo front NÃO contêm campos de custo/margem/comissão de outros.

**Teste da 3.0:** login como cada papel → painel-esqueleto correto abre com nome/role; API tipada retorna lista de OS real; tema dark com tokens aplicado; guard de sensíveis passa. `git commit`.

---

## Etapa 3.1 — Atendente (refs: imagens 1 e 5) — a mais importante
**Painel:** cards (Vendas do dia · OS aguardando aprovação qtd+R$ · Prontas p/ retirada qtd+R$ · Aguardando peça · Novas hoje · Atrasadas) · lista "Atendimentos que precisam de você" (tipo, cliente, descrição, status colorido, responsável, tempo) · atalhos do balcão · alertas/pendências.
**Kanban de OS** (img 5): colunas = workflow, drag respeitando transições (a API do workflow decide; transição inválida → toast de erro do servidor).
**Fluxos completos (modais/páginas):**
- **Nova OS / check-in:** cliente (buscar/criar) → aparelho (buscar/criar, IMEI obrigatório) → defeito/estado/acessórios → fotos → **assinatura de entrada em canvas** → imprime Termo de Entrada + Etiqueta QR (PDFs do motor).
- **Aprovação de orçamento:** exibir orçamento, aprovar/reprovar com canal + atendente (regras do motor: 48h, trava de versão).
- **Retirada:** conferência, assinatura de retirada em canvas, Termo de Retirada, entrega (motor bloqueia sem nota paga — exibir o erro com clareza).

**Teste da 3.1:** ciclo completo de uma OS REAL pela interface nova (criar → assinar → aprovar → [técnico via Desk] → retirar) sem tocar o Desk no papel de atendente; Kanban arrasta e transição proibida é rejeitada com mensagem; números dos cards batem com o banco. `git commit` (pode ser um por bloco: painel / kanban / fluxos).

---

## Etapa 3.2 — Técnico (ref: imagem 2)
**Painel:** Minhas OS · Aguardando peça · Diagnósticos hoje · Prontas p/ teste · Garantias/retornos · fila técnica (SÓ as OS do técnico logado — User Permission em ação) com etapa/prazo/prioridade · resumo do dia.
**Fluxos:** abrir OS da fila → preencher diagnóstico → adicionar peças (busca no estoque de Reparo; sem custo visível — a API já não manda) → registrar uso/perda (com as 3 classes) → solicitar peça (Material Request) → finalizar reparo/teste.
**Teste:** dois técnicos reais → cada um vê só as suas; diagnosticar e usar peça pela interface (baixa 1x no motor); campo de custo ausente na resposta da API e na tela. `git commit`.

---

## Etapa 3.3 — Gestor (ref: imagem 3)
**Painel:** vendas do dia · OS em andamento/atrasadas · ticket médio · peças em baixa (por estoque) · meta do dia · operação da loja (todas as OS/vendas) · equipe hoje (carga por técnico) · alertas de estoque · **aprovações pendentes** (descontos, compras acima do teto, trocas acima do máximo, garantia-cortesia) com ação de aprovar/reprovar inline.
**Teste:** aprovar pela interface uma compra acima do teto e uma troca acima do máximo (motor valida a role); números batem. `git commit`.

---

## Etapa 3.4 — Diretor (ref: imagem 4)
**Painel executivo:** faturamento do mês · vendas de acessórios · OS concluídas · margem estimada · ticket médio · gráficos (faturamento por período, mix de receita, top serviços, % retrabalho) · metas e resultados · movimentos principais.
**Teste:** números conferem com os reports do motor. `git commit`.

---

## Etapa 3.5 — Fluxos transversais
- **POS / venda rápida** na interface (busca produto do Comercial, pagamento com formas, cartão → recebíveis; consolidação continua a do motor).
- **Avaliação de troca + Trade-In:** checklist por tipo, faixa da tabela, operação de troca (o motor garante atomicidade).
- **Busca global** (Ctrl+K): cliente, OS, IMEI, produto.
- **Impressões** acessíveis de qualquer tela relevante (termos, orçamento, etiqueta).
**Teste:** venda POS + troca completa pela interface; busca acha por IMEI. `git commit`.

---

## Critério de "pronto" da Fase 3 = MVP OPERACIONAL (novo)
- [ ] Login por papel abre o painel certo; Desk não é necessário para a operação diária de Atendente e Técnico.
- [ ] **Ensaio geral do dono:** simular um dia de loja inteiro NA INTERFACE NOVA — abrir OS com assinatura, técnico pela fila, orçamento, aprovação, reparo, nota, retirada assinada, uma venda POS, uma troca. Sem console, sem Desk (exceto papéis de gestão onde previsto).
- [ ] Guard de dados sensíveis passando (Técnico/Atendente sem custo/margem/comissão alheia).
- [ ] Nenhuma regra de negócio implementada em JS (revisão: o front só chama API).
- [ ] Encoding limpo (scanner `check_encoding.py` no pre-commit pegando tudo).

→ Depois: Fase 4 (espinha de notificação) — que já vai nascer com o front pronto para exibir os avisos.
