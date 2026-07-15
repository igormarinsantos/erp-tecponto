# 00 — Contexto do Projeto Tecponto (leia isto primeiro)

> Este documento assume que **você não sabe nada** sobre a Tecponto, o negócio, nem necessariamente sobre Frappe/ERPNext. Ele te dá o contexto completo pra construir o sistema. Leia antes de qualquer código.

---

## 1. O que é a Tecponto

A **Tecponto** é uma **loja física de assistência técnica de celulares** em Guarulhos–SP, Brasil. Ela não faz só conserto — opera **três negócios ao mesmo tempo**, com peso parecido:

1. **COMPRE** — varejo. Vende acessórios (capinhas, películas, carregadores, cabos, fones) e aparelhos no balcão. É basicamente uma loja.
2. **TROQUE** — trade-in. O cliente entrega um celular usado (principalmente iPhone) e leva outro, pagando a diferença. A loja avalia, compra usados e revende.
3. **REPARE** — assistência técnica. Conserto de celulares: cliente traz o aparelho, a loja diagnostica, orça, o cliente aprova, o técnico conserta, o cliente paga e retira.

Esses três negócios são chamados de **pilares** no projeto. O sistema inteiro é organizado em torno deles.

## 2. O que estamos construindo

Um **ERP** (sistema de gestão) sob medida pra Tecponto, construído **em cima do ERPNext** (um ERP open-source) usando o **Frappe Framework** (a plataforma sobre a qual o ERPNext roda).

A ideia central: **não reinventar o ERP.** O ERPNext já tem clientes, estoque, vendas, compras, financeiro, PDV, permissões e relatórios prontos. A gente **customiza** ele pra virar o sistema da Tecponto, **sem nunca alterar o código-fonte do ERPNext** (o "core"). Toda a customização vive num app próprio chamado `tecponto_app`, separado e versionado no Git.

## 3. Stack técnica

- **Frappe Framework v16** — plataforma base (Python 3.12+).
- **ERPNext v16** — o ERP (módulos de negócio).
- **Frappe HR (`hrms`)** — módulo de RH/folha (comissão e descontos dos funcionários).
- **MariaDB 10.6+** — banco de dados.
- **Redis** — fila de tarefas em background e cache.
- **`tecponto_app`** — o app que estamos criando (todas as customizações).
- **Middleware fiscal externo** (PlugNotas / Focus NFe / NFe.io) — emite as notas fiscais brasileiras via API. O ERPNext não faz isso nativo.
- **Ubuntu 24.04** como servidor.

## 4. Vocabulário Frappe/ERPNext (glossário essencial)

Se você não conhece Frappe, leia isto — o resto dos documentos usa esses termos o tempo todo:

- **DocType** — é o "molde" de um tipo de registro (uma tabela + formulário + regras). Ex.: `Customer`, `Sales Invoice`. Criar um DocType é criar uma entidade do sistema.
- **Custom Field** — campo extra adicionado a um DocType que já existe (ex.: adicionar "WhatsApp" no `Customer`).
- **Child Table** — uma tabela dentro de um DocType (ex.: as linhas de peças dentro de uma Ordem de Serviço).
- **Single DocType** — um DocType com um registro único (usado pra configurações globais).
- **Workflow** — máquina de estados: define os status de um documento e quem pode mudar de um pro outro.
- **Perm level (nível de permissão)** — permite esconder **campos específicos** de certos papéis. Campo no nível 0 = todos veem; nível 1 = só quem tem permissão de nível 1. É como "o técnico lança a peça mas não vê o custo".
- **Role (papel)** — perfil de usuário (Atendente, Técnico, Gestor…).
- **Fixture** — um jeito de exportar customizações (Custom Fields, Workflows, Roles) como arquivos JSON versionáveis no Git.
- **hooks.py** — arquivo do app onde você "pendura" comportamento em eventos de documentos (ex.: "quando a OS for fechada, gere a nota").
- **doc_events** — os ganchos de ciclo de vida (validate, on_submit, on_cancel…) onde a lógica roda.
- **`frappe.enqueue`** — manda uma tarefa pra fila em background (assíncrono). Usado pra tudo que fala com sistemas externos, pra não travar a operação.
- **Scheduler** — tarefas agendadas (tipo cron): rodam diariamente (ex.: checar OS atrasada).
- **bench** — a ferramenta de linha de comando do Frappe (instalar, migrar, rodar).
- **`bench migrate`** — aplica ao banco as mudanças de DocTypes/fixtures.
- **`developer_mode`** — modo que faz o Frappe gravar em arquivo (versionável) tudo que você cria pela interface. **Tem que estar ligado no ambiente de desenvolvimento.**
- **Serial No / Batch** — rastreio de item por número de série (ex.: IMEI) ou lote (ex.: fornecedor de uma peça).
- **Stock Entry** — documento que movimenta estoque (entrada, saída, transferência). O tipo "Repack" (reempacotar) consome 1 item e produz vários — usamos pra **desmontar** um celular usado em peças.
- **Sales Invoice** — nota/fatura de venda. `update_stock` é um campo dela: se ligado, ela baixa o estoque; se desligado, só fatura.
- **POS** — o ponto de venda (PDV) do balcão.

### Vocabulário do negócio (Tecponto)

- **OS (Ordem de Serviço)** — o documento central do REPARE. Representa um conserto, do recebimento à retirada.
- **Aceite** — momento em que o cliente concorda com algo por assinatura (entrada, orçamento, retirada).
- **Orçamento** — o valor proposto pro conserto (mão de obra + peças).
- **Canibalizar / desmanche** — desmontar um celular usado pra aproveitar as peças boas.
- **Buyback** — comprar o usado do cliente pagando em dinheiro (sem troca).
- **Trade-in** — a troca casada: entra o usado, sai outro aparelho, cliente paga a diferença.
- **Recebíveis de cartão** — quando o cliente paga no cartão, quem paga a loja é a maquininha (adquirente), com desconto de taxa e prazo. O dinheiro não cai na hora nem inteiro.

### Vocabulário fiscal brasileiro (o dev provavelmente não conhece)

- **NFC-e / NF-e** — notas fiscais de **produto** (mercadoria). Emitidas pra estado (SEFAZ).
- **NFS-e** — nota fiscal de **serviço**. Emitida pra prefeitura (Guarulhos). A mão de obra do conserto é serviço.
- **Uma OS pode gerar DUAS notas:** a peça é produto (NFC-e), a mão de obra é serviço (NFS-e).
- **Simples Nacional** — regime de imposto simplificado pra pequenas empresas. A Tecponto está nele. Usa códigos **CSOSN**.
- **Certificado A1** — arquivo digital (.pfx) que assina as notas.
- **LC 116 item 14.01** — o código de serviço de "conserto/manutenção de aparelhos" (confirmar com contador).

## 5. Como a customização funciona (as 3 regras de ouro)

1. **Nunca toque no core.** Não edite arquivos em `apps/frappe` ou `apps/erpnext`. Tudo em `apps/tecponto_app`. Mudanças no core somem no próximo update.
2. **Duas formas de customizar, cada uma no seu lugar:**
   - Customizar um DocType nativo (ex.: campo no `Customer`) → **Custom Field + fixture**.
   - Criar uma entidade nova (Ordem de Serviço, Avaliação de Troca) → **DocType novo dentro do `tecponto_app`**, sempre com `module = "Tecponto"`.
3. **Lógica pesada ou externa é assíncrona.** Nada que fale com WhatsApp/SEFAZ/maquininha roda dentro da operação do balcão — vai pra fila (`frappe.enqueue`). Se um sistema externo cair, a loja não pode parar.

## 6. Regras invioláveis do sistema (decorrem do negócio)

- **Estoque baixa uma vez só.** Uma única fonte de verdade por movimentação. (No REPARE, a peça baixa no momento do uso.)
- **Não entrega sem nota paga.** A OS não pode ser "Entregue" sem Sales Invoice quitada.
- **Dois estoques que não se misturam:** Reparo (peças, só a OS consome) e Comercial (acessórios/aparelhos, só a venda consome). Transferir entre eles exige o Gestor.
- **O técnico lança, mas não vê custo/margem.** Perm levels escondem dados financeiros.
- **Troca é atômica:** as duas pernas (usado entra + aparelho sai) fecham juntas ou nenhuma.

## 7. Os documentos do projeto (e como lê-los)

- **`00 — Contexto`** (este) — o que é, o vocabulário, as regras de ouro.
- **`Regras de Negócio Travadas` (contrato)** — a **fonte da verdade** de todas as regras e de todos os campos. Sempre que houver dúvida de "como deve funcionar" ou "qual campo existe", a resposta está lá.
- **`01 — Roadmap de Fases`** — a ordem de construção, com o plano de cada fase (objetivo, o que construir, critério de pronto).
- **Guias de fase** (`Fase 0`, `Fase 1`, …) — o passo a passo executável de cada fase, com comandos e definições.

Ordem de leitura pra quem chega: **00 → contrato → 01 → guia da fase atual.**

## 8. Papéis de usuário

- **Atendente** — atende o balcão: cadastra cliente/aparelho, abre OS, vende no PDV, recebe pagamento, entrega. Não vê custo/margem/financeiro.
- **Técnico** — bancada: diagnostica, usa peças, conserta. Vê só as suas OS. Avalia usados na troca. Não vê financeiro.
- **Gestor** — aprova desconto/compra/troca acima de limites, ajusta estoque, fecha caixa, vê relatórios e margem.
- **Admin/Diretor** (System Manager) — acesso total, configura o sistema.
- **Cliente** — não tem login no sistema; interage por link público e WhatsApp.

---

### Em uma frase
A Tecponto é uma loja de três negócios (vender, trocar, consertar celulares) e estamos construindo o ERP dela customizando o ERPNext num app próprio, sem tocar no core, seguindo um contrato de regras já fechado, construído fase a fase.
