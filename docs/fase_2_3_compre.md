# Fase 2.3 — Pilar COMPRE (guia otimizado para Codex)

> **Contexto:** `00_contexto` + contrato (Parte II = COMPRE + F4 caixa). Pré-requisito: **Fase 2.2 (TROQUE) concluída**. Este é o pilar mais simples: quase tudo é módulo nativo do ERPNext (POS, Buying) — pouca lógica nova, mais configuração + travas.

## INSTRUÇÕES PARA O CODEX (iguais às anteriores)
- Um passo por vez: teste → commit. Windows/PowerShell: sem `&&`.
- Schema/config mudou → migrate 0 + export-fixtures no commit. Só código → não precisa.
- Config via `Tecponto Settings`. Nunca tocar o core.

---

## Passo 1 — POS de acessórios (contrato C1, C2)

Quase tudo configuração nativa:
1. Crie um **POS Profile** "Tecponto Balcão": warehouse = `commercial_warehouse` (Acessórios - TEC), formas de pagamento (Pix, Dinheiro, Débito, Crédito — as de cartão apontando pra conta de recebíveis da Fase 2.0), naming series própria.
2. Confirme que a venda POS **baixa do Comercial** (nunca do Reparo).
3. **Sem comissão de venda** — não criar nenhum gancho de comissão em POS/Sales Invoice de venda direta (a comissão existente é só do REPARE, por linha de serviço).

Crie o POS Profile via script idempotente (versionável) + fixture.
**Testes:** (a) venda POS de um acessório → baixa do Comercial, pagamento em recebíveis se cartão; (b) venda POS **não** gera Additional Salary de comissão; (c) tentar vender item que só tem estoque no Reparo → sem estoque no POS (não vaza do Reparo). `git commit`.

---

## Passo 2 — Venda de aparelho usado com garantia (contrato C2)

Aparelho usado (criado pelo TROQUE) vendido no balcão:
1. Venda com **Serial No obrigatório** (o IMEI sai junto na nota).
2. Ao vender, grave a garantia: **90 dias, só defeito de fábrica** (`used_device_warranty_days` do Settings). Sugestão: campo/registro de garantia ligado ao Serial vendido (data da venda + expiry), pra consulta futura quando o cliente voltar.

**Testes:** (a) vender usado sem informar Serial → bloqueado; (b) venda OK → Serial marcado como entregue, garantia registrada com expiry = venda + 90d. `git commit`.

---

## Passo 3 — Devolução e troca de acessório (contrato C2, F4)

Usar o fluxo nativo de **nota de crédito/devolução** (Sales Invoice Return):
1. Devolução de acessório → return invoice, item **volta ao estoque Comercial**, valor devolvido (ou crédito).
2. Troca produto-por-produto → devolução + nova venda (dois documentos, rastreável).
3. Se o pagamento original foi cartão, a devolução ajusta a conta de **recebíveis** (não o caixa).

**Testes:** (a) devolver um acessório vendido → estoque do Comercial volta a subir, return invoice ligada à original; (b) devolução de venda em cartão → movimento na conta de recebíveis. `git commit`.

---

## Passo 4 — Compras (contrato C3)

1. Fluxo nativo: `Purchase Order` → `Purchase Receipt` → `Purchase Invoice`. Entrada de peças no **Reparo**, de produtos no **Comercial** (warehouse por item/pedido).
2. **Compra à vista por padrão**, mas contas a pagar disponível (não travar prazo).
3. **Trava de aprovação:** Purchase Order acima de `purchase_approval_threshold` (Settings) exige **Gestor** pra submeter.
4. `Material Request` do técnico (falta de peça) → vira PO; integra com o reorder level 3 já configurado.

```python
def validar_teto_compra(doc, method=None):
    import frappe
    teto = frappe.db.get_single_value("Tecponto Settings", "purchase_approval_threshold")
    if teto and doc.grand_total > teto and not frappe.has_role("Tecponto Gestor"):
        frappe.throw(f"Compra acima de {teto} exige aprovação do Gestor.")
```
**Testes:** (a) PO abaixo do teto como Atendente → passa; acima → bloqueado; como Gestor → passa; (b) Purchase Receipt de peça entra no Reparo, de acessório no Comercial. `git commit`.

---

## Critério de "pronto" da Fase 2.3 — e da FASE 2 INTEIRA
- [ ] POS vende do Comercial, cartão em recebíveis, sem comissão de venda.
- [ ] Usado vendido com Serial + garantia 90d fábrica registrada.
- [ ] Devolução volta estoque e ajusta recebíveis quando cartão.
- [ ] Compra acima do teto exige Gestor; entradas caem no estoque certo.
- [ ] migrate 0 + fixtures + commits limpos.

### Teste de integração da Fase 2 completa (os 3 pilares juntos)
Rodar o ciclo cruzado que amarra tudo:
1. **TROQUE:** cliente troca um iPhone usado por um seminovo do estoque (troca atômica).
2. O usado entra e é **canibalizado**: tela → estoque Reparo, carcaça → Comercial.
3. **REPARE:** uma OS usa a tela canibalizada (reserva → baixa → nota → comissão).
4. **COMPRE:** o cliente compra uma capinha no POS (baixa do Comercial, cartão em recebíveis).
5. Conferir: estoques corretos nos dois depósitos, nenhuma baixa dupla, comissão só na OS, recebíveis com os valores de cartão.

Se esse ciclo fechar, a **FASE 2 INTEIRA está pronta** → próxima: Fase 3 (superfícies/MVP).
