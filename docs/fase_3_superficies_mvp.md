# Fase 3 — Superfícies de balcão / MVP (guia otimizado para Codex)

> **Contexto:** `00_contexto` + contrato (R2 aceites, F6 visibilidade). Pré-requisito: **Fase 2 completa** (ciclo cruzado verde). Objetivo: a loja consegue **operar de verdade** — telas, impressos, assinatura, dashboards.
>
> **Estratégia em dois níveis** (decisão do dono):
> - **Nível 1 (esta fase):** tudo dentro do ERPNext nativo — Kanban, Number Cards, dashboards por papel, print formats, workspace. Rápido, robusto, atualizável. A loja roda com isso.
> - **Nível 2 (fase futura, pós-go-live):** front-end próprio com o visual das 5 telas de referência (imagens do dono), consumindo a API do `tecponto_app`. NÃO é escopo desta fase.
>
> As 5 telas de referência servem AQUI como **especificação de conteúdo** (o que cada papel precisa ver), não como layout a copiar.

## INSTRUÇÕES PARA O CODEX (iguais às anteriores)
- Um passo por vez: teste → commit. Windows/PowerShell: sem `&&`.
- Tudo com `module = Tecponto` (workspaces, dashboards, cards, prints viram arquivos do app). Schema/config → migrate 0 + export-fixtures.
- Interface em **português brasileiro**.

---

## Passo 1 — Kanban de OS + cores por status

1. Ative a visão **Kanban** na lista de `Service Order`, colunas = `workflow_state`: Entrada criada → Em diagnóstico → Aguardando aprovação → Aguardando peça → Em reparo → Teste final → Pronto para retirada (+ Entregue/Cancelado/Sem conserto ocultáveis).
2. **Cores por estado** (via indicator/list settings): Entrada=cinza, Diagnóstico=azul, Aguardando aprovação=laranja, Aguardando peça=roxo, Em reparo=azul-escuro, Pronto=verde, Atrasada/Expirado=vermelho.
3. Card do Kanban mostra: nº OS, cliente, aparelho, prazo (`approval_deadline`/`estimated_deadline`).

**Teste:** Kanban abre com as colunas certas; arrastar uma OS entre colunas respeita o workflow (transição inválida é rejeitada — ex.: Atendente não arrasta pra "Em diagnóstico"). `git commit`.

---

## Passo 2 — Print Formats (os impressos do balcão)

Quatro impressos (Print Format, module Tecponto, em PT-BR):
1. **Termo de Entrada (check-in):** dados do cliente/aparelho, IMEI, estado físico declarado, riscos/trincos, acessórios recebidos, aviso de senha, consentimento LGPD, aviso de não-retirada/estadia, campo de assinatura. (contrato R2.1)
2. **Termo de Retirada:** serviços executados, peças trocadas, valores, garantia (`warranty_expiry` — 90 dias), quem retirou (terceiro se for o caso), assinatura. Inclui variante "retirada sem reparo" (recusa/expirado). (R2.3)
3. **OS / Orçamento:** o documento pro cliente decidir — diagnóstico, itens, valores, validade de 48h úteis (`approval_deadline`).
4. **Etiqueta com QR Code:** pequena, pro saquinho do aparelho — nº OS, cliente, aparelho + QR que abre a OS. Técnico escaneia e cai direto no documento.

**Teste:** gerar PDF dos 4 a partir de uma OS real; QR da etiqueta resolve pra URL da OS. `git commit`.

---

## Passo 3 — Assinatura digital nos aceites

1. Campos tipo **Signature** nos pontos dos 3 aceites (entrada e retirada na OS — o de orçamento pode ser o registro de canal já implementado + assinatura quando presencial).
2. A validação existente dos aceites (Fase 2.1 Passo 2) passa a aceitar a assinatura capturada em tela (tablet/celular do balcão).

**Teste:** assinar na tela → assinatura salva na OS e aparece no PDF do termo. `git commit`.

---

## Passo 4 — Dashboards por papel (especificação extraída das 5 telas de referência)

Um **Workspace** por papel, com Number Cards + Charts + atalhos. Conteúdo (o QUE mostrar, vindo das telas do dono):

**4a. Workspace ATENDENTE** (refs: imgs 1 e 5)
- Cards: Vendas do dia (R$) · OS aguardando aprovação (qtd + R$) · OS prontas para retirada (qtd + R$) · Aguardando peça · Novas hoje · Atrasadas.
- Lista "precisam de você": OS + vendas com status, ordenadas por atualização.
- Atalhos: Lançar venda (POS) · Nova OS · Buscar cliente · Cadastrar cliente/aparelho · Avaliar troca.
- **NÃO mostrar:** margem, custo, comissão de ninguém (perm levels da 2.0 já garantem; o workspace não deve nem tentar).

**4b. Workspace TÉCNICO** (ref: img 2)
- Cards: Minhas OS · Aguardando peça · Diagnósticos hoje · Prontas para teste · Garantias/retornos.
- Fila técnica: minhas OS por etapa com prazo e prioridade (cores).
- Resumo do dia: diagnósticos feitos, reparos finalizados, tempo médio.
- Atalhos: Atualizar diagnóstico · Solicitar peça (Material Request) · Finalizar reparo.
- **NÃO mostrar:** faturamento da loja, custo das peças, comissão de outros.

**4c. Workspace GESTOR** (ref: img 3)
- Cards: Vendas do dia · OS em andamento · OS atrasadas · Ticket médio · Peças em baixa (reorder ≤3) · Meta do dia.
- Operação da loja: todas as OS/vendas com técnico, atendente, prazo, valor.
- Equipe hoje: carga por técnico (OS abertas por pessoa).
- Alertas de estoque (por estoque: Reparo e Comercial separados) + Aprovações pendentes (descontos, compras acima do teto, trocas acima do máximo).

**4d. Workspace DIRETOR** (ref: img 4)
- Cards: Faturamento do mês · Vendas de acessórios · OS concluídas · Margem estimada · Ticket médio · Satisfação (se houver).
- Charts: faturamento por período · mix de receita (serviços × acessórios × peças) · top serviços · retrabalho % (OS de garantia ÷ total — qualidade).
- Metas e resultados (se configuradas).

**Teste:** logar com um usuário de cada papel → o workspace certo abre, os números batem com os dados reais, e nenhum card vaza dado financeiro pra Atendente/Técnico. `git commit`.

---

## Passo 5 — Relatórios essenciais

Reports (module Tecponto): OS por status/técnico/período · Tempo médio de reparo · Peças mais usadas · Vendas por dia (POS + OS separados e somados) · Recebíveis de cartão em aberto · Estoque crítico por depósito · Comissões por técnico/período · Garantias ativas (reparo + usados vendidos).

**Teste:** cada report roda e os totais batem com os documentos. `git commit`.

---

## Critério de "pronto" da Fase 3 = MVP OPERACIONAL
- [ ] Kanban de OS com cores funcionando e respeitando workflow.
- [ ] 4 impressos gerando PDF corretos (com QR na etiqueta).
- [ ] Assinatura em tela salva e sai no termo.
- [ ] 4 workspaces por papel, sem vazamento financeiro.
- [ ] Reports essenciais rodando.
- [ ] **Ensaio geral:** simular um dia de loja — abrir OS com termo+assinatura, técnico pelo Kanban, orçamento impresso, aprovação, reparo, nota, retirada assinada + uma venda POS + uma troca. Tudo pela interface, sem console.

Se o ensaio geral passar: **a loja pode operar**. → Próxima: Fase 4 (espinha de notificação).
