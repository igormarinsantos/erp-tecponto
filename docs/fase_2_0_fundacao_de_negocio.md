# Fase 2.0 — Fundação de negócio (base dos três pilares)

> **Contexto:** leia `00 — Contexto` e o contrato `Regras de Negócio Travadas` (seções F2, F4, F5, F6). Pré-requisito: **Fase 1 concluída** (todos os DocTypes e campos existem).
>
> Objetivo: ligar a **base transversal** que COMPRE, TROQUE e REPARE usam — antes de qualquer pilar. É quase toda **configuração**, pouca lógica pesada. Ao final, permissões, estoques, recebíveis de cartão e travas de preço estão de pé.

---

## Por que esta fase vem antes dos pilares
Os três pilares dependem de: quem vê o quê (perm levels), de qual estoque cada um consome, de como o cartão é recebido, e das travas de preço. Se isso não estiver pronto, cada pilar teria que reimplementar — retrabalho. Construímos a base uma vez.

---

## Passo 1 — Matriz de visibilidade (perm levels)

Referência: contrato F6. O padrão é "lança mas não vê" = **campos sensíveis em perm level 1**, invisíveis pra Atendente/Técnico.

1. Nos DocTypes com dado financeiro, coloque em **perm level 1** os campos: custo/valuation da peça, margem, `internal_notes`, `device_password`, débito de perda, `approved_value` de troca.
2. Em "Role Permission Manager", para cada DocType:
   - **perm level 0** (dados operacionais): Atendente e Técnico leem/escrevem o que lhes cabe.
   - **perm level 1** (dados financeiros): só `Tecponto Gestor` e `System Manager`.
3. **Técnico vê só as suas OS:** configure User Permission por `technician`, ou uma condição de permissão no `Service Order`.

Exporte como fixture (perms customizadas):
```python
fixtures += [{"dt": "Custom DocPerm"}]
```
```bash
bench --site tecponto.local export-fixtures
```

**Teste:** logue como Técnico → abra uma OS → o campo de custo da peça **não aparece**. Logue como Gestor → aparece.

## Passo 2 — Os dois estoques operacionais

Referência: contrato F2. Os depósitos já existem (Fase 0). Aqui você dá o **comportamento**.

1. Em `Tecponto Settings`, confirme `repair_warehouse = Peças - TEC` e `commercial_warehouse = Acessórios - TEC`.
2. **Regra de consumo automático** (será usada pelos pilares): OS puxa do `repair_warehouse`; POS/venda puxa do `commercial_warehouse`. Nesta fase, apenas garanta que os defaults de warehouse nos documentos apontem para o estoque certo.
3. **Transferência entre estoques exige Gestor:** o `Stock Entry` tipo *Material Transfer* entre os dois depósitos só pode ser submetido por `Tecponto Gestor`/Admin. Configure via permissão + (opcional) validação:
```python
def validate_transfer_role(doc, method):
    import frappe
    if doc.stock_entry_type == "Material Transfer":
        pares = {doc.get("from_warehouse"), doc.get("to_warehouse")}
        estoques = {frappe.db.get_single_value("Tecponto Settings", "repair_warehouse"),
                    frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")}
        if pares & estoques and not frappe.has_role("Tecponto Gestor"):
            frappe.throw("Transferência entre estoques exige o Gestor.")
```
Registre em `hooks.py`:
```python
doc_events = {
    "Stock Entry": {"validate": "tecponto_app.tecponto.stock.validate_transfer_role"}
}
```

**Teste:** como Atendente, tente transferir 1 peça do Reparo pro Comercial → bloqueado. Como Gestor → passa.

## Passo 3 — Custeio Média Móvel

Referência: contrato F5/17. Defina o método de valoração como **Moving Average** para os itens dos dois estoques (no Item ou no Item Group padrão). Confirme `valuation_method = Moving Average` em `Tecponto Settings` e nos Item Groups de peças e produtos.

## Passo 4 — Recebíveis de cartão

Referência: contrato F4. **O cartão não cai direto no caixa.**

1. Crie a **conta transitória** "Recebíveis de Cartão" (Accounting → Chart of Accounts, tipo Receivable/ativo). Aponte em `Tecponto Settings.acquirer_clearing_account`.
2. Ligue os **Mode of Payment** de cartão (Débito, Crédito à vista, Crédito parcelado) a **essa conta**, não ao banco/caixa.
3. Preencha a tabela `Tecponto Settings.card_fees` — uma linha por tipo:

| tipo | taxa_pct | settlement_days |
|---|---|---|
| Débito | 1.5 | 1 |
| Crédito à vista | 3.0 | 30 |
| Crédito 2x | 4.5 | 30 |
| Crédito 3x | 5.5 | 30 |

(valores de exemplo — você ajusta com os reais da sua adquirente.)

4. **Liquidação** (a conciliação quando a adquirente deposita) será um passo operacional: baixa o recebível, lança a **taxa como despesa**, credita o banco pelo líquido. Nesta fase, deixe a estrutura pronta; a automação/gateway é a Fase 5c.

**Teste:** registre uma venda de teste no crédito → o valor entra em "Recebíveis de Cartão", não no caixa. A venda fica **paga** (bruto).

## Passo 5 — Travas de preço

Referência: contrato F5. Duas travas coexistem:

1. **Desconto acima do limite → Gestor** (limite em `Tecponto Settings`).
2. **Piso de custo → nunca vender abaixo do custo sem Gestor** (`price_floor_block`).

Estrutura da validação (será chamada por REPARE e COMPRE ao definir preço):
```python
def validate_price_floor(rate, item_code, warehouse):
    import frappe
    if not frappe.db.get_single_value("Tecponto Settings", "price_floor_block"):
        return
    custo = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "valuation_rate") or 0
    if rate < custo and not frappe.has_role("Tecponto Gestor"):
        frappe.throw(f"Preço abaixo do custo ({custo}) exige aprovação do Gestor.")
```

**Teste:** como Atendente, tente vender uma peça abaixo do custo → bloqueado. Como Gestor → passa. Desconto normal (acima do custo) → livre.

## Passo 6 — RH pronto pra receber lançamentos

Referência: contrato F8. O Frappe HR (`hrms`) já foi instalado na Fase 0.

1. Confirme que cada Técnico tem um registro `Employee` vinculado ao `User`.
2. Crie os componentes salariais: **Comissão** (provento/earning) e **Débito por perda** (dedução/deduction). Eles serão alimentados pela lógica do REPARE (Fase 2.1) via `Additional Salary`.

Nesta fase só a estrutura; os lançamentos vêm com a comissão (2.1).

---

## Critério de "pronto"
- [ ] Técnico não vê custo/margem; Gestor vê (perm level testado).
- [ ] Técnico vê só as suas OS.
- [ ] Transferência entre os dois estoques bloqueada sem Gestor.
- [ ] Cartão posta em "Recebíveis de Cartão"; venda fica paga (bruto); `card_fees` preenchida.
- [ ] Venda abaixo do custo bloqueada sem Gestor.
- [ ] Employees dos técnicos existem; componentes de comissão e perda criados.
- [ ] `bench migrate` + `export-fixtures` + `git commit` limpos.

## Fechar a fase
```bash
bench --site tecponto.local export-fixtures
bench --site tecponto.local migrate
cd apps/tecponto_app && git add -A && git commit -m "feat: fundação de negócio — perm levels, estoques, recebíveis, travas (Fase 2.0)"
```

➡️ **Próximo:** Fase 2.1 — Pilar REPARE (workflow da OS, 3 aceites, reserva/baixa/perda de peça, fechamento idempotente, comissão, garantia).
