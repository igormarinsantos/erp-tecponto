# Fase 2.1 — Pilar REPARE (guia otimizado para Codex)

> **Contexto:** `00_contexto` + contrato `Regras de Negócio Travadas` (Parte IV = REPARE). Pré-requisito: **Fase 2.0 concluída e testada** (perm levels, estoques, recebíveis, travas). Este é o guia mais crítico do projeto.

## INSTRUÇÕES PARA O CODEX (leia uma vez, siga sempre)
- Trabalhe **um passo por vez**. Após cada passo: rode o teste do passo, e só então `git commit`. Não avance com teste falhando.
- **Não releia o contrato inteiro a cada passo.** As regras necessárias já estão citadas aqui por seção (R2, R6…). Consulte o contrato só se algo não estiver especificado.
- Toda lógica vai em `apps/tecponto_app/tecponto_app/tecponto/` (módulo Tecponto). **Nunca** edite `apps/frappe` ou `apps/erpnext`.
- Registre handlers em `hooks.py` **uma vez** (bloco `doc_events`), agrupando por DocType.
- Use `frappe.db.get_single_value("Tecponto Settings", <campo>)` para toda config. Nada hardcoded.
- **Idempotência é obrigatória** onde indicado: antes de criar documento, cheque se já existe. Rodar duas vezes não pode duplicar.
- Não refatore código não relacionado. Não crie testes além dos indicados.
- Rode testes via `bench --site tecponto.local execute` ou `bench --site tecponto.local console`.

---

## Passo 1 — Workflow da OS (contrato R3)

Crie o Workflow `Service Order`. Estados e transições (papel que pode):

| De → Para | Papel |
|---|---|
| Entrada criada → Em diagnóstico | Técnico, Gestor |
| Em diagnóstico → Aguardando aprovação | Técnico, Gestor |
| Aguardando aprovação → Aprovado | Atendente, Gestor |
| Aguardando aprovação → Reprovado | Atendente, Gestor |
| Aguardando aprovação → Orçamento expirado | (scheduler, Passo 3) |
| Aprovado → Aguardando peça / Em reparo | Técnico, Gestor |
| Em reparo → Teste final | Técnico |
| Teste final → Pronto para retirada | Técnico |
| Pronto para retirada → Entregue | Atendente, Gestor |
| (qualquer técnico) → Sem conserto | Técnico |
| (quase qualquer) → Cancelado | Gestor |

Crie via script (reproduzível/versionável), depois exporte como fixture:
```python
# bench execute — cria o Workflow uma vez (idempotente)
import frappe
if not frappe.db.exists("Workflow", "Service Order"):
    wf = frappe.get_doc({"doctype":"Workflow","workflow_name":"Service Order",
      "document_type":"Service Order","workflow_state_field":"workflow_state","is_active":1,
      "states":[ ... ],"transitions":[ ... ]})  # preencher conforme tabela acima
    wf.insert()
```
Adicione ao `fixtures` do hooks: `Workflow`, `Workflow State`, `Workflow Action Master`.
**Teste:** crie uma OS; como Atendente tente "Em diagnóstico" → bloqueado; como Técnico → passa. `git commit`.

---

## Passo 2 — Os três aceites (contrato R2)

Handler `validate` / `on_update` no `Service Order`:
```python
def validate_aceites(doc, method):
    import frappe
    # Check-in: não sai de "Entrada criada" sem foto de entrada + assinatura
    if doc.workflow_state != "Entrada criada":
        if not doc.entry_photos:
            frappe.throw("Foto de entrada é obrigatória antes de iniciar o atendimento.")
    # Autorização: ao aprovar, exige canal + atendente + data
    if doc.approval_status == "Aprovado":
        if not (doc.approval_channel and doc.approved_by_attendant):
            frappe.throw("Registre o canal e o atendente da aprovação.")
        if not doc.approval_date:
            doc.approval_date = frappe.utils.now()
    # Entrega: bloqueia sem Sales Invoice paga
    if doc.workflow_state == "Entregue":
        _exigir_nota_paga(doc)
        if not doc.customer_signature:
            frappe.throw("Assinatura de retirada é obrigatória.")
        if not doc.get("warranty_expiry"):
            doc.warranty_expiry = frappe.utils.add_days(frappe.utils.nowdate(), 90)  # R8

def _exigir_nota_paga(doc):
    import frappe
    if not doc.sales_invoice:
        frappe.throw("Não é possível entregar sem nota emitida.")
    status = frappe.db.get_value("Sales Invoice", doc.sales_invoice, "status")
    if status not in ("Paid",):
        frappe.throw("A nota precisa estar paga antes da entrega.")
```
`hooks.py`: `"Service Order": {"validate": "tecponto_app.tecponto.service_order.aceites.validate_aceites"}`
**Teste:** tentar "Entregue" sem `sales_invoice` → bloqueado. `git commit`.

---

## Passo 3 — Prazo de 48h úteis + expiração (contrato R5)

Ao entrar em "Aguardando aprovação", grave `approval_deadline = agora + 48h úteis` (pula fim de semana e feriados via Holiday List de Guarulhos). Scheduler diário expira as vencidas.
```python
def set_deadline(doc, method):
    import frappe
    if doc.workflow_state == "Aguardando aprovação" and not doc.approval_deadline:
        doc.approval_deadline = _add_business_hours(frappe.utils.now_datetime(), 48)  # helper c/ Holiday List

# scheduler_events (hooks.py) → "daily"
def expirar_orcamentos():
    import frappe
    vencidas = frappe.get_all("Service Order", filters={
        "workflow_state":"Aguardando aprovação",
        "approval_deadline":["<", frappe.utils.now()]})
    for r in vencidas:
        d = frappe.get_doc("Service Order", r.name)
        d.workflow_state = "Orçamento expirado"
        # se diagnosis_fee_enabled → marcar cobrança da taxa (Passo 6 fatura)
        d.save(ignore_permissions=True)
```
**Teste:** OS com deadline no passado → scheduler move pra "Orçamento expirado". `git commit`.

---

## Passo 4 — Orçamento imutável/versionado (contrato R5)

```python
def travar_orcamento(doc, method):
    import frappe
    if doc.approval_status == "Aprovado" and not doc.quote_locked:
        doc.quote_locked = 1
        doc.budget_version = (doc.budget_version or 1)
    # se editar serviços/peças depois de travado → nova versão + volta pra aprovação
    if doc.quote_locked and doc.has_value_changed("services") or doc.has_value_changed("parts"):
        if doc.workflow_state not in ("Aguardando aprovação",):
            doc.budget_version = (doc.budget_version or 1) + 1
            doc.quote_locked = 0
            doc.approval_status = "Pendente"
            doc.workflow_state = "Aguardando aprovação"
```
**Teste:** editar peça numa OS aprovada → `budget_version` sobe e volta pra "Aguardando aprovação". `git commit`.

---

## Passo 5 — Peça: reserva → baixa no uso → 3 perdas (contrato R6) — NÚCLEO

Regras: reserva na aprovação; baixa **no uso** (Stock Entry Material Issue do `repair_warehouse`); 3 classes de perda; **liberar reserva ao reprovar/cancelar** (⚠️ auditoria).

```python
# 5a. Ao aprovar: reservar peças (idempotente por linha)
def reservar_pecas(doc, method):
    import frappe
    if doc.approval_status != "Aprovado":
        return
    for p in doc.parts:
        if p.reservation:            # já reservado → skip (idempotência)
            continue
        p.reservation = _criar_reserva(p.item_code, p.qty, p.warehouse, doc.name)

# 5b. Ao usar a peça (outcome definido): baixa 1x e roteia perda
def baixar_peca(part_row, doc):
    import frappe
    if part_row.stock_entry:         # já baixada → skip (idempotência)
        return
    se = _material_issue(part_row.item_code, part_row.qty, part_row.warehouse)  # Stock Entry
    part_row.stock_entry = se
    _liberar_reserva(part_row.reservation)
    if part_row.outcome == "Perdida":
        _rotear_perda(part_row, doc)   # ver 5c

# 5c. Roteamento das 3 classes de perda (R6)
def _rotear_perda(p, doc):
    import frappe
    if p.loss_reason == "Perda da loja":
        pass  # já saiu do estoque; custo vira despesa/sucata via Cost Center
    elif p.loss_reason == "Responsabilidade do técnico":
        _criar_deducao_hr(p.technician, _custo(p))   # Additional Salary (deduction)
    elif p.loss_reason == "Garantia do fornecedor":
        _marcar_devolucao_fornecedor(p)              # trilha de claim

# 5d. Ao reprovar/cancelar: liberar reservas NÃO usadas (⚠️ CRÍTICO)
def liberar_reservas(doc, method):
    import frappe
    if doc.workflow_state in ("Reprovado","Cancelado","Sem conserto"):
        for p in doc.parts:
            if p.reservation and not p.stock_entry:
                _liberar_reserva(p.reservation)
                p.reservation = None
```
> Reserva: use `Stock Reservation Entry` nativo se a versão suportar contra a OS; senão, implemente reserva mínima (registro que decrementa disponível). O que importa: **uma 2ª OS enxerga que a peça acabou**, e reprovar **devolve** a disponibilidade.

**Testes (rodar todos):**
1. Aprovar OS → peça reservada.
2. Usar peça (outcome=Usada) → estoque baixa **1x**; rodar de novo → **não** baixa de novo.
3. Peça outcome=Perdida + loss_reason=Técnico → dedução criada no HR.
4. Reprovar OS com peça reservada e não usada → reserva **liberada**.
`git commit`.

---

## Passo 6 — Fechamento: 1 Sales Invoice idempotente sem re-baixar (contrato R7)

```python
def gerar_nota(doc, method):
    import frappe
    if doc.sales_invoice:            # ⚠️ IDEMPOTÊNCIA: já tem nota → nunca gera outra
        return
    si = frappe.new_doc("Sales Invoice")
    si.customer = doc.customer
    si.update_stock = 0             # ⚠️ estoque já saiu no uso (Passo 5) — NÃO re-baixar
    # linhas de serviço (mão de obra)
    for s in doc.services:
        si.append("items", {"item_code": s.item_code, "qty": s.qty, "rate": s.rate})
    # linhas de peças COBRÁVEIS (outcome == Usada)
    for p in doc.parts:
        if p.outcome == "Usada no reparo":
            si.append("items", {"item_code": p.item_code, "qty": p.qty, "rate": p.rate,
                                "warehouse": p.warehouse})
    # taxa de diagnóstico: se reprovado/expirado e habilitada → cobra só a taxa (R4)
    _aplicar_taxa_diagnostico(doc, si)
    # sinal: se houver adiantamento, alocar contra a nota (R9)
    _alocar_sinal(doc, si)
    _aplicar_desconto(doc, si)
    si.insert(); si.submit()
    doc.db_set("sales_invoice", si.name)
```
**Teste:** fechar OS → 1 nota com serviço+peças usadas, `update_stock=0`; rodar de novo → **mesma** nota (não cria 2ª); estoque não muda no fechamento. `git commit`.

---

## Passo 7 — Comissão 20% por linha de serviço (contrato R10)

```python
def gerar_comissao(doc, method):
    import frappe
    if doc.is_warranty:             # garantia/retrabalho não comissiona
        return
    pct = frappe.db.get_single_value("Tecponto Settings", "commission_pct") or 20
    for s in doc.services:          # comissão POR LINHA, para o técnico da linha
        if not s.technician:
            continue
        valor = (s.rate * s.qty) * pct/100
        _additional_salary(s.technician, valor, ref=doc.name)  # provento no HR (idempotente por ref+linha)
```
**Teste:** fechar OS com 2 serviços de técnicos diferentes → 2 comissões, cada uma p/ seu técnico. OS de garantia → 0 comissão. `git commit`.

---

## Passo 8 — Garantia, sinal, estadia, cancelamento faturado (R8/R9/R11/R12)

- **Garantia (R8):** `warranty_expiry` no delivery (Passo 2 já grava). OS de garantia = `is_warranty=1` + `original_service_order`; grátis, fora de faturamento/comissão. Peça diferente → nova OS normal. Cortesia: só Gestor, com `courtesy_warranty_reason`.
- **Sinal (R9):** toggle cria adiantamento (Payment Entry) ligado; retido se reprova (vira receita → NFS-e); devolução só por erro nosso (ação Gestor).
- **Estadia (R11):** se `cobra_estadia`, calcula diária após carência, com teto.
- **Cancelamento faturado (R12):** OS com `sales_invoice` só cancela por Gestor, dentro da janela fiscal.
**Teste:** entregar OS → `warranty_expiry` = hoje+90d; cancelar OS faturada como Atendente → bloqueado. `git commit`.

---

## Critério de "pronto" da Fase 2.1 (rode tudo antes do 2.2)
- [ ] Ciclo entrada→diagnóstico→aprovação→reparo→pronto→entregue roda com papéis certos.
- [ ] Não entrega sem nota paga.
- [ ] Peça baixa **1x** no uso; fechar não re-baixa.
- [ ] Fechar 2x → **1** nota (idempotência).
- [ ] Reprovar libera reserva (⚠️).
- [ ] 3 classes de perda roteiam certo (loja/técnico→HR/fornecedor).
- [ ] Comissão 20% por linha; garantia não comissiona.
- [ ] `warranty_expiry` = entrega+90d.
- [ ] `bench migrate` + `export-fixtures` + `git commit` limpos.

➡️ **Próximo:** Fase 2.2 — TROQUE (avaliação checklist, tabela com faixa, Trade-In Operation atômica, canibalização Repack).
