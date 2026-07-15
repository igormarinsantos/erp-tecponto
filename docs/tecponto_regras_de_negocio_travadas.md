# Tecponto ERP — Regras de Negócio Travadas (v4 — organizada por pilar)

> Contrato de implementação definitivo. Estruturado como o negócio real: uma **Fundação comum** e **três pilares** — COMPRE (varejo), TROQUE (trade-in), REPARE (assistência). É a fonte da verdade que a Fase 2 implementa.
>
> Avisos: pontos fiscais/legais confirmar com contador/advogado. Especificação de sistema, não parecer profissional. **Sem pendências abertas.**

---

# ARQUITETURA

```
FUNDAÇÃO COMUM  (cliente · 2 estoques · fiscal · caixa/cartão ·
                 permissões+visibilidade · notificação · auditoria · RH)
        │
   ┌────┼──────────────────┐
   ▼    ▼                  ▼
 COMPRE          TROQUE             REPARE
 varejo/POS      trade-in iPhone    assistência/OS
```

Os três pilares têm peso parecido e são setores separados. Tudo que é transversal fica na Fundação; cada pilar tem seu documento principal e suas regras.

---

# PARTE I — FUNDAÇÃO COMUM

## F1. Cliente
- `Customer` nativo + Custom Fields: WhatsApp, CPF/CNPJ, IE, IM, RG, observações. Endereço via `Address`.
- Consentimento LGPD (optin) registrado. Anonimização a pedido **preserva** documentos fiscais (retenção legal ~11 anos).

## F2. Dois estoques (por propósito)
- **Reparo** — peças. Só a **OS** consome. Custo/margem só pro Gestor.
- **Comercial** — acessórios, produtos e aparelhos (novos/usados) para revenda. Só **POS/venda** consome.
- Consumo automático pelo lado certo (OS→Reparo, POS→Comercial).
- Reposição, estoque crítico e giro **por estoque**. Nível de reposição padrão = **3**.
- **Transferência entre estoques = Stock Transfer registrado, exige Gestor.**
- Item que vende E conserta: mesmo item em dois depósitos; baixa do depósito correto.
- **Custeio = Média Móvel** nos dois (base do piso de custo).

## F3. Fiscal
- Regime = **Simples Nacional** → CSOSN; CBS/IBS obrigatório só a partir de 2027.
- **Duas notas por operação quando há produto + serviço:** produto → NFC-e/NF-e; serviço → NFS-e.
- Guarulhos → **Padrão Nacional da NFS-e** (obrigatório 2026; Emissor Nacional p/ Simples set/2026). Serviço ≈ **LC 116 item 14.01** (confirmar CNAE/NBS).
- Módulo `fiscal` → **middleware** (PlugNotas/Focus/NFe.io) via API/webhook, provedor por config. Certificado A1.
- **Emissão não-atômica:** emite o que autorizar; a outra fica **pendente/contingência com alerta**. Falha da prefeitura não trava a venda.
- Itens carregam NCM, CFOP, origem, CEST, (serviço) código LC116/NBS/CNAE — **desde o cadastro**.

## F4. Caixa, cartão & recebíveis
- Formas: Pix, Dinheiro, Débito, Crédito à vista, Crédito parcelado; **pagamento misto** suportado.
- **Cartão não cai direto no caixa:** vai para **conta transitória de recebíveis** (acquirer clearing). A venda sai **PAGA** (bruto).
- **Taxas configuráveis por tipo** (débito/à vista/2x/3x…) + **prazo de liquidação** (D+1/D+30/por parcela). Auto-sync ao conectar gateway.
- Liquidação (manual→auto): baixa recebível + **taxa como despesa** + banco pelo líquido. **Chargeback** absorvido pela conta de recebíveis.
- POS: **sangria/suprimento** e **diferença de caixa** no fechamento; **estorno/devolução** → nota de crédito.
- Dashboard mostra **todas as visões**: Faturamento (bruto), Recebido (líquido no cronograma), e demais indicadores.

## F5. Preço & travas
- Preço vem da **Price List**; toggle edita **só na operação** (não altera cadastro), com **motivo obrigatório**.
- **Piso de custo (trava dura):** não vende **abaixo do custo** sem Gestor. Desconto normal livre; furar o custo, não.
- Desconto acima do limite → Gestor. (Trava de desconto e trava de custo coexistem.)

## F6. Permissões & matriz de visibilidade
Roles: `Tecponto Atendente`, `Tecponto Tecnico`, `Tecponto Gestor`, System Manager. Técnico vê só **suas** OS.
Padrão "lança mas não vê" = **campos diferentes em perm levels diferentes** (técnico lança a peça no nível 0; custo é outro campo no nível 1, invisível).

| Dado | Atendente | Técnico | Gestor | Admin |
|---|---|---|---|---|
| Preço de venda | vê/cobra | — | vê | vê |
| Custo/valuation | — | **lança, não vê** | vê | vê |
| Margem/lucro | — | — | vê | vê |
| Comissão própria | — | vê a própria | vê todas | vê todas |
| Comissão de outros | — | — | vê | vê |
| Senha do aparelho | lança (mascarada) | lê c/ log | vê | vê |
| Dados fiscais cliente | lança/vê | — | vê | vê |
| Relatórios financeiros | — | — | vê | vê |
| Débito de perda | — | vê o próprio | vê todos | vê todos |
| Valor de troca acima do máximo | — | avalia | **aprova** | aprova |

## F7. Notificação
- Event-driven: mudança de estado → `doc_event` → `frappe.enqueue` (assíncrono).
- `notify.send(template_key)` agnóstica de provedor. Prioridade: **WhatsApp → Fiscal → Maquininha** (5a/5b/5c). Entradas por webhook.

## F8. RH (Frappe HR)
- App `hrms`. Recebe **comissão** (provento) e **desconto por perda do técnico** (dedução).

## F9. Auditoria
- Track Changes na OS/operações (quem mudou preço, status, valor). Visão de auditoria pro Gestor (antifraude).

## F10. Abandono (⚠️ jurídico)
- Sem prazo federal fixo; presumir abandono é abusivo (CDC 51 IV). Prazo **configurável**.
- Termo de entrada avisa por escrito; **notificação formal com comprovante** logada; destino final = **ação manual do Gestor**, nunca automático.

## F11. Escopo / multi-loja
- **Single-store.** Filial futura = **instância replicada** deste sistema (dados/fiscal/caixa próprios), não multi-loja compartilhada.

---

# PARTE II — PILAR COMPRE (varejo)

## C1. Operação
- Venda **principalmente presencial** via **POS nativo**; acessórios e produtos do **estoque Comercial**.
- Marketplace = futuro (princípio travado: estoque único + reserva por canal + preço por canal).

## C2. Regras
- **Sem comissão de venda** — só o técnico comissiona (REPARE). Vendedor não ganha.
- **Troca de acessório** (produto por produto) e **devolução/estorno** → nota de crédito/devolução.
- Baixa automática do **Comercial**; fechamento de caixa com sangria/suprimento (F4).

## C3. Compras (abastece os dois estoques)
- **À vista por padrão**, com **opção de contas a pagar** (fornecedor a prazo) disponível.
- **Aprovação de compra** acima de teto configurável → **Gestor**.
- Entrada por `Purchase Receipt`; `Material Request` (falta de peça/produto) → pedido, integrado à reposição.

---

# PARTE III — PILAR TROQUE (trade-in, principalmente iPhone)

## T1. Natureza
Transação **casada de duas pernas**: entra o usado do cliente **e** sai um aparelho do estoque Comercial; cliente paga a **diferença**. É um setor próprio, com avaliação técnica.

## T2. Fluxo (dois papéis + gestor)
```
Técnico avalia (checklist) → valor sugerido
   → Gestor aprova o valor (se acima do máximo da tabela)
   → Atendente concretiza a venda/troca
```

## T3. Avaliação
- **Checklist por tipo de aparelho** (iPhone / Android, extensível). iPhone: bateria %, Face ID/Touch ID, iCloud limpo, tela original, chip/eSIM, estética A/B/C. Android: conta Google, root, + comuns.
- **Bloqueio iCloud/Google → barrado** (não aceita em troca).
- **Tabela de valores por modelo/estado com faixa (mín–máx)** — mantida por você (entra depois; estrutura nasce agora).

## T4. Valor & margem
- Avaliador é **livre dentro da faixa** (mín–máx). **Acima do máximo → exige Gestor.**
- **Sem troca melhor-por-pior:** diferença sempre ≥ 0 (cliente paga ou zera; a loja não dá troco).
- **Trava de margem:** valor dado no usado + desconto no aparelho de saída não podem gerar prejuízo sem Gestor.

## T5. As duas pernas (atômico)
```
Trade-In Operation (orquestra)
  ├── ENTRADA: usado avaliado → valor de troca (funciona como pagamento)
  ├── SAÍDA: 1 aparelho do estoque Comercial (novo ou seminovo, Serial/IMEI)
  ├── DIFERENÇA (≥ 0) → forma de pagamento (Pix/cartão/dinheiro)
  └── confirmar = ATÔMICO (as duas pernas ou nenhuma):
        • usado entra no estoque → Destinação (T6)
        • aparelho de saída baixa do Comercial + garantia de venda
        • fiscal das duas pernas (compra do usado + venda do aparelho)
```
- Se uma perna falha (aparelho de saída com defeito, usado bloqueado) → transação não fecha.

## T6. Destinação do usado recebido (por compra pura OU troca)
- Ao entrar: `Item` (Aparelhos Usados) + `Serial No` (IMEI) + entrada de estoque + pagamento/abatimento.
- Destino: **Venda** (vira produto do estoque **Comercial** → alimenta o COMPRE) · **Peças** (canibaliza) · **Descarte**.
- **Compra pura (buyback):** uma perna só (cliente vende e sai com dinheiro/Pix) — usa a mesma avaliação/entrada, sem perna de saída.
- **Canibalização = Stock Entry "Repack":** consome 1 usado, produz N peças; você **lista as peças e o custo de cada uma**; custo do aparelho **rateado por valor de venda esperado** (ou manual); descarte = custo zero; cada peça rastreável ao doador (lote = IMEI). **Destino de cada peça: Reparo ou Comercial.**

---

# PARTE IV — PILAR REPARE (assistência técnica)

## R1. Aparelho & IMEI
- `Customer Device` (propriedade do cliente, não é estoque). 1 cliente → N aparelhos; 1 OS → 1 aparelho.
- **IMEI obrigatório** ao entrar na OS. Senha mascarada (perm level 1) + log de acesso.

## R2. Os TRÊS aceites
1. **Check-in:** aceita o estado declarado antes da bancada; assinatura + **fotos obrigatórias** travam estado/riscos/senha/acessórios/LGPD/avisos. Técnico não abre sem isso.
2. **Autorização de reparo:** registra **canal** (presencial/telefone/WhatsApp/link) + atendente + timestamp.
3. **Retirada:** confirma recebimento; **inicia a garantia**. Termo mesmo em "sem conserto".
- Terceiro (não-dono) traz/retira → registra identidade + autorização. Recusa → remontagem + termo sem reparo.

## R3. Ciclo (workflow)
Entrada → Em diagnóstico → Aguardando aprovação → (Aprovado | Reprovado | Expirado) → Aguardando peça → Em reparo → Teste final → Pronto → Entregue. Saídas: Cancelado, Sem conserto.
- Reprovado/expirado é definitivo (retomar = nova OS). **"Entregue" bloqueado sem nota paga.**

## R4. Diagnóstico & taxa
- Seção na OS. Taxa **grátis por padrão** (toggle + valor). Aprovou no prazo → **abatida**; reprovou/expirou → cobra **só a taxa** (→ NFS-e).

## R5. Orçamento
- **Completo (sem aprovação parcial):** aprova/reprova o orçamento inteiro. Mudar escopo = **técnico altera a OS** → revisão versionada → reaprovação.
- **Imutável após aprovação** (`quote_locked`, `budget_version`). Prazo = **48h úteis** (Holiday List Guarulhos) do envio; expirou → cobra taxa → abandono.

## R6. Peças
- **Reserva na aprovação → baixa no uso.** Aprovado, reserva (resolve "última peça, dois reparos"); reprovar/cancelar antes do uso libera a reserva.
- Baixa no uso via `Stock Entry` Material Issue. Desfecho por linha: **Usada** (cobrável) | **Perdida**.
- **3 classes de perda:** Loja (sucata) · Técnico (→ desconto em folha) · Fornecedor (→ devolução). **DOA** → fornecedor; nota só cobra a que funcionou.
- Rastreio **lote+fornecedor** (`batch_no`). **Reversão** de baixa por engano. **Dano na bancada** registrado (foto de entrada é a defesa).

## R7. Fechamento & nota
- **1 Sales Invoice** (mão de obra + peças cobráveis), **sem re-baixar** (`update_stock OFF`), **idempotente** (`sales_invoice` trava dupla). Split fiscal peça/serviço (F3).

## R8. Garantia
- **90 dias** (peça trocada + mão de obra), da entrega. Mesma peça/defeito → OS de garantia grátis (`is_warranty`), **fora de faturamento/comissão**. Peça diferente → nova OS paga.
- **Garantia-cortesia:** Gestor concede fora do prazo com **justificativa**.

## R9. Sinal
- Opcional, não vem aplicado. Ligado → adiantamento vinculado, abatido. **Retido** se reprova/desiste (→ NFS-e). **Devolução só por erro nosso** (Gestor).

## R10. Comissão
- **Só mão de obra, 20% fixo, por linha de serviço** (cada linha tem `technician`; permite vários por OS). **Exclui** garantia/retrabalho. Feed HR como provento.

## R11. Estadia
- Desligada por padrão; só cobrável se avisada no termo. `valor_diaria` + `carencia_dias` + `teto` (≤ valor do serviço). Dissuasor.

## R12. Cancelamento faturado
- OS já com nota → cancelar/estornar **só Gestor**, dentro da janela fiscal; fora dela, nota de devolução.

---

# DELTAS PARA A FASE 1 (campos por área)

**Customer:** custom_cnpj, custom_ie, custom_im (+ WhatsApp/CPF/RG/obs já previstos).
**Customer Device:** imei_serial **obrigatório** em OS.
**Service Order:** diagnosis_fee_enabled/value · approval_deadline/channel/approved_by_attendant · quote_locked/budget_version · is_warranty/original_service_order/courtesy_warranty(+reason) · sinal_enabled/value/payment_entry · additional_damage(+cause) · picked_up_by_third_party/third_party_doc/auth · estadia · formal_notice_log.
**Service Order Service (child):** technician (sem status por linha — aprova em bloco).
**Service Order Part (child):** outcome · loss_reason · batch_no · stock_entry · reservation.
**Trade-In Operation (novo):** customer · evaluation(link) · device_out(Serial/IMEI) · difference · payment · atomic status · fiscal refs.
**Device Trade Evaluation:** device_type · checklist(child por tipo) · table_min/table_max · suggested_value · approved_value · approver · destination · created_item.
**Item:** custom_ncm/cfop/origem/cest · service_code_lc116/nbs/cnae · valuation em perm level 1.
**Tecponto Settings:** regime_tributario · fiscal_provider/certificate · commission_pct(20)/labor_only · estadia_* · abandono_prazo_dias · acquirer_clearing_account · price_floor_block · card_fees(table) · repair_warehouse · commercial_warehouse · reorder_level(3) · purchase_approval_threshold · valuation_method(Média Móvel) · used_device_warranty_days(90) · tradein_over_max_needs_manager.

---

### Resumo em uma frase
Uma Fundação comum (cliente, dois estoques por propósito, fiscal Simples com duas notas não-atômicas, cartão via recebíveis, matriz de visibilidade, notificação, RH, auditoria) sob três pilares: **COMPRE** (varejo/POS sem comissão), **TROQUE** (trade-in iPhone com checklist por tipo, tabela com faixa, acima do máximo exige Gestor, duas pernas atômicas alimentando o Comercial) e **REPARE** (três aceites, orçamento completo imutável, peça com reserva/baixa no uso/3 perdas/piso de custo, comissão 20% MO por linha, garantia 90d + cortesia, fechamento fiscal idempotente).


---

# AUDITORIA DE FLUXOS (veredito)

Os quatro fluxos (macro, amarras de estoque, troca atômica, integrações) foram auditados contra este contrato. **Nenhum erro estrutural.** As amarras fecham: usuários→pilares→fundação→integrações; o usado do TROQUE alimenta COMPRE e REPARE sem ficar órfão; a troca é atômica; integrações assíncronas e agnósticas.

**Três requisitos técnicos que a implementação NÃO pode esquecer:**
1. **Atomicidade da troca (Fase 2.2):** as duas pernas dentro de uma transação de banco, com rollback se qualquer uma falhar. Nunca "meio feito".
2. **Fiscal não-atômico (Fase 5b):** job diário que reprocessa notas pendentes/contingência, senão uma nota fica esquecida.
3. **Liberação de reserva (Fase 2.1):** ao reprovar/cancelar, a reserva de peça tem que ser liberada de forma confiável, senão peça fica presa a OS morta.
