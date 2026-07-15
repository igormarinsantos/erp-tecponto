# Fase 2.2 — Pilar TROQUE (guia otimizado para Codex)

> **Contexto:** `00_contexto` + contrato `Regras de Negócio Travadas` (Parte III = TROQUE). Pré-requisito: **Fase 2.1 (REPARE) concluída e testada**. DocTypes `Device Trade Evaluation` e `Trade-In Operation` já existem (Fase 1).

## INSTRUÇÕES PARA O CODEX (iguais às da 2.1)
- Um passo por vez: teste → `git commit`. Não avance com teste falhando.
- Não releia o contrato inteiro; as regras estão citadas por seção (T3, T4…).
- Toda lógica no módulo Tecponto. Nunca tocar o core. Idempotência onde marcado ⚠️.
- Config via `Tecponto Settings`. Ambiente Windows/PowerShell: **não use `&&`**, comandos em linhas separadas.
- Rode testes via `bench --site tecponto.localhost execute`.

---

## Passo 1 — Avaliação: checklist por tipo + faixa da tabela (contrato T3, T4)

No `Device Trade Evaluation`:
- `device_type` (iPhone/Android) define o **checklist** exibido. iPhone: bateria %, Face ID/Touch ID, iCloud limpo, tela original, chip/eSIM, estética A/B/C. Android: conta Google, root, + comuns.
- **Bloqueio iCloud/Google → barra automático** na aprovação: se o item de bloqueio estiver marcado, `frappe.throw` impede aprovar a compra.
- **Faixa da tabela** (`table_min`/`table_max`): o avaliador dá `approved_value` livre **dentro** da faixa; **acima do `table_max` exige Gestor**.

```python
def validar_avaliacao(doc, method=None):
    import frappe
    if doc.get("workflow_state") in ("Aprovado para compra", "Comprado"):
        if _tem_bloqueio(doc):                       # iCloud/Google marcado
            frappe.throw("Aparelho bloqueado (iCloud/Google) não pode ser comprado.")
        if doc.approved_value and doc.table_max and doc.approved_value > doc.table_max:
            needs = frappe.db.get_single_value("Tecponto Settings", "tradein_over_max_needs_manager")
            if needs and not frappe.has_role("Tecponto Gestor"):
                frappe.throw(f"Valor acima do máximo da tabela ({doc.table_max}) exige o Gestor.")
```
`hooks.py`: `"Device Trade Evaluation": {"validate": "tecponto_app.tecponto.tradein.evaluation.validar_avaliacao"}`

**Testes:** (a) iPhone com iCloud marcado → aprovação bloqueada; (b) `approved_value` acima do `table_max` como Atendente → bloqueado; como Gestor → passa; (c) dentro da faixa → livre. `git commit`.

---

## Passo 2 — Destinação: aparelho vira estoque (compra pura / buyback) (contrato T6)

Ao "Comprado", cria o Item de estoque (idempotente via `created_item`):
```python
def concretizar_compra(doc, method=None):
    import frappe
    if doc.get("workflow_state") != "Comprado" or doc.get("created_item"):
        return
    item = _criar_item_usado(doc)                    # Item Group "Aparelhos Usados", has_serial_no=1
    _criar_serial(item, doc.imei)                    # Serial No = IMEI
    _entrada_estoque(item, doc.approved_value, _warehouse_destino(doc))  # Purchase Receipt / Stock Entry
    _pagar_cliente(doc)                              # Payment Entry (buyback) — se não for troca
    doc.db_set("created_item", item)
```
> Destino define o warehouse: **Venda → Comercial**; **Peças → vai pro Passo 4 (canibalização)**; **Descarte → não cria item**.

**Testes:** buyback → Item criado (Aparelhos Usados) + Serial=IMEI + entrada no Comercial + Payment ao cliente; rodar de novo → não duplica (`created_item` já setado). `git commit`.

---

## Passo 3 — Trade-In Operation ATÔMICA (contrato T5) — ⚠️ NÚCLEO

A troca casada: **usado entra + aparelho sai + diferença**, tudo numa transação. Se qualquer perna falhar, **rollback total**.

```python
def confirmar_troca(doc, method=None):
    import frappe
    if doc.get("status") == "Concluída":             # idempotência
        return
    # regra: sem troca melhor-por-pior → diferença >= 0
    if (doc.difference or 0) < 0:
        frappe.throw("A diferença da troca não pode ser negativa (a loja não dá troco).")
    # trava de margem: valor do usado + desconto não pode gerar prejuízo sem Gestor
    _validar_margem_troca(doc)

    sp = frappe.db.savepoint("troca")                # ⚠️ ponto de rollback
    try:
        # PERNA 1 — entrada do usado (usa a avaliação → vira estoque)
        _entrada_usado(doc)                          # Passo 2 (destinação)
        # PERNA 2 — saída do aparelho do Comercial (baixa + fiscal de venda)
        _saida_aparelho(doc)                         # baixa Serial do device_out
        # diferença: forma de pagamento do delta
        _registrar_pagamento_diferenca(doc)
        doc.db_set("status", "Concluída")
    except Exception:
        frappe.db.rollback(save_point="troca")       # ⚠️ nada é gravado
        raise
```
> A atomicidade é o ponto crítico deste pilar. Use `savepoint` + `rollback`. Se a saída do aparelho falhar (aparelho já vendido, sem estoque), a entrada do usado **não pode** ficar gravada.

**Testes obrigatórios:**
1. Troca OK → usado entra, aparelho sai, diferença registrada, status Concluída.
2. **Forçar a perna 2 a falhar** (device_out sem estoque) → confirmar que a perna 1 **NÃO** ficou gravada (usado não entrou, nada persistido). ⚠️ este é o teste que prova a atomicidade.
3. Diferença negativa → bloqueado.
4. Rodar troca concluída de novo → não duplica.
`git commit`.

---

## Passo 4 — Canibalização via Repack (contrato T6)

Desmonta 1 usado (destino=Peças) em N peças, distribuindo o custo.
```python
def canibalizar(doc, method=None):
    import frappe
    # Stock Entry tipo "Repack": consome 1 aparelho usado, produz N peças
    se = frappe.new_doc("Stock Entry"); se.stock_entry_type = "Repack"
    se.append("items", {"item_code": doc.created_item, "qty": 1, "s_warehouse": _wh_usados()})
    for peca in doc.get("harvest_parts") or []:      # lista: peça + valor esperado + destino (Reparo/Comercial)
        se.append("items", {"item_code": peca.item_code, "qty": peca.qty,
                            "t_warehouse": _wh_por_destino(peca.destino),
                            "basic_rate": _rateio(peca, doc)})   # custo rateado por valor de venda esperado
    se.insert(); se.submit()
```
> Custo do aparelho **rateado por valor de venda esperado** (peça mais cara absorve mais); descarte = custo zero. Cada peça rastreável ao doador (lote = IMEI). **Destino de cada peça escolhido na desmontagem** (Reparo ou Comercial).

**Testes:** desmontar 1 usado → peças entram nos warehouses escolhidos; soma dos custos rateados ≈ custo do aparelho; peça marcada Reparo cai no estoque de Reparo, Comercial no Comercial. `git commit`.

---

## Critério de "pronto" da Fase 2.2 (rode tudo antes da 2.3)
- [ ] Checklist por tipo (iPhone/Android); bloqueio iCloud barra aprovação.
- [ ] Valor acima do máximo da tabela exige Gestor; dentro da faixa é livre.
- [ ] Buyback cria Item usado + Serial + entrada + pagamento (idempotente).
- [ ] Troca atômica: perna 2 falhando **não** grava a perna 1 (⚠️ teste 2 do Passo 3).
- [ ] Diferença negativa bloqueada.
- [ ] Canibalização distribui custo e manda cada peça pro estoque certo.
- [ ] `bench migrate` (0) + `export-fixtures` + `git commit` limpos.

➡️ **Próximo:** Fase 2.3 — COMPRE (POS de acessórios, compras, devoluções). O mais simples dos três pilares.
