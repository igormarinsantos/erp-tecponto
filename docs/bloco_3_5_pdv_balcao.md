# Bloco 3.5-PDV — Ponto de venda do balcão (guia otimizado para Codex)

> **Contexto:** o botão "Lançar venda" do Atendente (hoje Pendente 3.5) vira um PDV real no front Tecponto. Pré-requisito: pilar COMPRE (Fase 2.3) já existe no motor — este bloco é a **cara** dele no front + um endpoint de venda cirúrgico.
>
> **Ponto crítico de segurança:** a venda NÃO usa a role nativa `Sales User` (rejeitada — abria 68 permissões e nem liberava POS). A venda é feita por um **endpoint whitelisted no motor** que executa a venda com permissão do backend; o Atendente aciona, o motor faz. O Atendente nunca ganha acesso direto a estoque/relatório/custo.

## PRINCÍPIOS
1. **Venda pelo motor, não pela role.** Endpoint `pos_create_sale(itens, forma_pagamento)` roda a venda server-side (baixa Comercial, recebíveis se cartão, cupom). O Atendente só chama; sem Sales User.
2. **Nunca expor custo.** O PDV busca item e mostra **preço de venda** (`standard_rate`), nunca `valuation_rate`. Reusar o `search_budget_items` já blindado (Fase 3.1d-plus) ou endpoint equivalente com o mesmo guard.
3. **Só estoque Comercial.** O PDV vende do `commercial_warehouse`; nunca do Reparo (mesma trava do POS Profile da 2.3).
4. **Mesma disciplina:** sub-bloco por vez → teste → commit. Windows/PowerShell sem `&&`.

## STACK
- Tela de PDV no front (React), dentro do `/tecponto`, acionada pelo "Lançar venda".
- **Leitor de código de barras físico (USB):** funciona como teclado — digita o número + Enter. A tela tem um campo com foco que escuta esse input e resolve o item por `barcode`. Sem câmera, sem getUserMedia.
- Endpoint de venda no `tecponto_app` reusando o POS/consolidação da Fase 2.3.

---

## 3.5-PDV-1 — Tela de venda + busca dupla (bipe OU nome)
- Layout PDV: campo de leitura (foco automático, escuta o leitor), lista de itens da venda (nome, qtd, preço, subtotal), total grande, botão finalizar.
- **Dois caminhos de adicionar item:**
  1. **Bipe** (item COM barcode): leitor digita o número → busca por `barcode` → adiciona à venda. Barcode não encontrado → aviso "produto não cadastrado" (sem travar; atendente busca por nome).
  2. **Busca por nome** (item SEM barcode): campo de busca → seleciona → adiciona. Cobre os acessórios a granel sem etiqueta.
- Ajustar quantidade, remover linha, aplicar desconto (respeitando o **piso de custo** da Fase 2.0 — desconto abaixo do custo exige Gestor).
- Guard: nenhum custo/margem no payload do PDV.
**Teste:** adicionar item por bipe (simular input de teclado terminando em Enter) e por nome; total soma certo; barcode inexistente avisa sem quebrar; guard `leaked_fields: []`. `git commit`.

## 3.5-PDV-2 — Finalização da venda (endpoint cirúrgico)
- Endpoint `pos_create_sale` no motor: recebe itens + forma de pagamento; valida piso de custo; cria a venda (POS/Sales Invoice da 2.3) baixando do **Comercial**; cartão → conta de **recebíveis**; retorna número da venda + dados do cupom.
- Formas: Pix, Dinheiro, Débito, Crédito (à vista/parcelado) — as taxas/liquidação da Fase 2.0.
- **Pagamento misto** (parte Pix, parte cartão) suportado.
- Idempotência: reenvio da mesma venda não duplica.
- Emitir/abrir **cupom** para impressão (Print Format simples, ou reusar estrutura de impressão existente).
**Teste:** finalizar venda pela interface → baixa do Comercial (não do Reparo), cartão em recebíveis, cupom gerado; Atendente NÃO tem role Sales User e mesmo assim a venda ocorre (via endpoint); reenvio não duplica. `git commit`.

## 3.5-PDV-3 — Etiqueta de código de barras (para itens sem barcode)
- Na tela de item/produto (ou no cadastro de acessório): botão **gerar código de barras** para itens que não têm um.
- Gera um `barcode` no Item (campo nativo do ERPNext) + **Print Format de etiqueta** com o código impresso (igual à etiqueta QR da OS, mas com barcode) para colar no produto.
- Depois de etiquetado, o item passa a ser vendável por bipe (3.5-PDV-1).
**Teste:** gerar barcode para um item sem código → barcode salvo no Item → etiqueta imprime → bipar essa etiqueta no PDV encontra o item. `git commit`.

---

## Critério de "pronto" do 3.5-PDV
- [ ] "Lançar venda" abre o PDV real (o "Pendente 3.5" some).
- [ ] Adicionar item por bipe (leitor USB) E por busca de nome, ambos funcionando.
- [ ] Venda finaliza via endpoint cirúrgico — Atendente vende SEM Sales User; sem acesso a custo/estoque/relatório.
- [ ] Baixa do Comercial; cartão em recebíveis; pagamento misto; cupom.
- [ ] Piso de custo respeitado (desconto abaixo do custo exige Gestor).
- [ ] Gerar+imprimir etiqueta de barcode para itens sem código; depois vendáveis por bipe.
- [ ] Guard de custo verde em todas as telas do PDV.

## Nota de go-live
- Equipamento: **leitor de código de barras USB** (pistola) no balcão — entra na checklist junto da impressora térmica (etiquetas QR/barcode/cupom) e do tablet de aceite (bloco 3.6).
