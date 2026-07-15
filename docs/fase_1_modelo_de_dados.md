# Fase 1 — Modelo de dados (os substantivos)

> **Contexto:** leia antes `00 — Contexto` (o que é a Tecponto, glossário Frappe/negócio) e o contrato `Regras de Negócio Travadas` (fonte da verdade dos campos). Este guia é o passo a passo.
>
> Pré-requisito: **Fase 0 concluída** (ERPNext rodando, `tecponto_app` instalado, `developer_mode = 1`).
> Objetivo: criar **todos os objetos de negócio e suas relações** — sem comportamento ainda. Ao final, dá pra cadastrar cliente → aparelho → OS por tela, com os links funcionando. Nenhuma automação é esperada nesta fase.

---

## ⚠️ Atualização v4 — campos e DocTypes que este guia precisa incluir

As seções abaixo mostram o núcleo dos DocTypes. Como o contrato evoluiu para a v4 (pilares + análise fria), **adicione também os campos e entidades a seguir**. A lista completa e autoritativa está na seção "Deltas para a Fase 1" do contrato.

**`Service Order` — campos adicionais:**
`diagnosis_fee_enabled`, `diagnosis_fee_value` · `approval_deadline`, `approval_channel` (Select: Presencial/Telefone/WhatsApp/Link), `approved_by_attendant` · `quote_locked` (Check), `budget_version` (Int) · `is_warranty` (Check), `original_service_order` (Link), `courtesy_warranty` (Check), `courtesy_warranty_reason` · `sinal_enabled`, `sinal_value`, `sinal_payment_entry` · `additional_damage` (Check), `additional_damage_cause` · `picked_up_by_third_party` (Check), `third_party_doc`, `third_party_auth` · campos de estadia · `formal_notice_log` (Table, notificações de abandono).

**`Service Order Service` (child):** adicionar `technician` (Link → Employee) — base da comissão por linha.

**`Service Order Part` (child):** adicionar `outcome` (Select: Usada no reparo / Perdida) · `loss_reason` (Select: — / Perda da loja / Responsabilidade do técnico / Garantia do fornecedor) · `batch_no` (Link → Batch) · `stock_entry` (Link, read-only) · `reservation` (Link — reserva criada na aprovação).

**`Customer Device`:** `imei_serial` passa a ser **obrigatório** quando ligado a uma OS.

**`Item` (Custom Fields fiscais):** `custom_ncm`, `custom_cfop`, `custom_origem`, `custom_cest`, `custom_service_code_lc116`, `custom_nbs`, `custom_cnae`. Custo/valuation em **perm level 1**.

**`Customer` (Custom Fields):** além de WhatsApp/CPF/RG → `custom_cnpj`, `custom_ie`, `custom_im`.

**`Device Trade Evaluation` — campos adicionais:** `device_type` (Select: iPhone/Android) · `checklist` (child table, itens variam por tipo) · `table_min`, `table_max` (faixa da tabela) · `suggested_value`, `approved_value`, `approver` · `destination` (Venda/Peças/Descarte) · `created_item`.

**Novo DocType `Trade-In Operation`** (orquestra a troca casada): `customer` · `evaluation` (Link → Device Trade Evaluation) · `device_out` (aparelho de saída, Serial/IMEI do estoque Comercial) · `difference` (Currency, ≥ 0) · `payment_mode` · status atômico · refs fiscais das duas pernas.

**`Tecponto Settings` (Single) — campos adicionais:** `regime_tributario` (default Simples Nacional) · `fiscal_provider`, `fiscal_certificate` · `commission_pct` (20), `commission_labor_only` (Check) · estadia (`valor_diaria`, `carencia_dias`, `teto`) · `abandono_prazo_dias` · `acquirer_clearing_account` · `price_floor_block` (Check) · `card_fees` (Table: tipo, taxa_pct, settlement_days) · `repair_warehouse`, `commercial_warehouse` · `reorder_level` (3) · `purchase_approval_threshold` · `valuation_method` (Média Móvel) · `used_device_warranty_days` (90) · `tradein_over_max_needs_manager` (Check).

> Nada disso tem lógica ainda — são só campos/estruturas. A lógica (workflow, cálculos, atomicidade) vem na Fase 2.

---

## Como criar DocType nesta fase (leia antes)

Há dois caminhos, e os dois geram os mesmos arquivos versionados:

1. **Pela interface (recomendado para você):** menu → "DocType" → New. Em cada DocType, defina **Module = `Tecponto`**. Com `developer_mode` ligado, o Frappe escreve `apps/tecponto_app/tecponto_app/tecponto/doctype/<nome>/` com `.json`, `.py`, `.js`.
2. **Por arquivo (para um builder IA):** criar direto o `<nome>.json` + `<nome>.py` na pasta acima e rodar `bench migrate`. O JSON de exemplo está no fim deste documento.

> **Regra de ouro:** Module sempre = `Tecponto`. É isso que faz o arquivo cair no app e não sumir do Git.

As tabelas abaixo são a **fonte da verdade dos campos** — valem para os dois caminhos.

---

## Passo 1 — Custom Fields no `Customer`

Vá em "Customize Form" → selecione **Customer** → adicione:

| Label | Fieldname | Tipo | Notas |
|---|---|---|---|
| WhatsApp | `custom_whatsapp` | Data | com DDD |
| CPF | `custom_cpf` | Data | (ou use o `tax_id` nativo) |
| RG | `custom_rg` | Data | quando não houver CPF |
| Observações | `custom_observacoes` | Text | |

> Bairro/endereço **não** vira campo aqui — use o **Address** nativo (já tem bairro/cidade/UF).

## Passo 2 — Custom Fields no `Item`

"Customize Form" → **Item** → adicione:

| Label | Fieldname | Tipo | Notas |
|---|---|---|---|
| Localização/Gaveta | `custom_drawer_location` | Data | onde a peça fica |
| Modelos compatíveis | `custom_compatible_models` | Small Text | ex.: "iPhone 11, 11 Pro" |
| Tipo de peça | `custom_part_type` | Select | Tela\nBateria\nConector\nFlex\nPlaca\nCâmera\nBotão\nInsumo\nAcessório |

> Estoque mínimo: use o **Reorder Level** nativo do Item, não crie campo.

## Passo 3 — Exportar as customizações como fixtures

Edite `apps/tecponto_app/tecponto_app/hooks.py` e adicione:

```python
fixtures = [
    {"dt": "Custom Field", "filters": [["dt", "in", ["Customer", "Item"]]]},
    {"dt": "Property Setter", "filters": [["doc_type", "in", ["Customer", "Item"]]]},
]
```
Depois:
```bash
bench --site tecponto.local export-fixtures
```

---

## Passo 4 — DocType `Customer Device` (Aparelho do Cliente)

Settings: **Module = Tecponto**, **Naming = "Autoincrement" ou por campo**, **Track Changes = on**.

| Label | Fieldname | Tipo | Opções/Notas |
|---|---|---|---|
| Cliente | `customer` | Link | Customer — **obrigatório** |
| Marca | `brand` | Data | |
| Modelo | `model` | Data | |
| Cor | `color` | Data | |
| IMEI / Serial | `imei_serial` | Data | marcar como índice |
| Capacidade | `capacity` | Select | 32GB\n64GB\n128GB\n256GB\n512GB\n1TB |
| Senha/Padrão | `device_password` | Data | **perm level 1** (sensível) |
| Estado geral | `general_state` | Small Text | |
| Observações | `notes` | Text | |
| Fotos | `photos` | Attach Image (ou Table) | |
| Data de cadastro | `registration_date` | Date | default Today |

Relação: **1 Customer → N Customer Device**. O "histórico de OS" não é campo — aparece sozinho como *Connections* (a Fase 2 liga a OS a este DocType).

---

## Passo 5 — DocType `Service Order` (Ordem de Serviço) — principal

Settings: **Module = Tecponto**, **Is Submittable = NÃO** (o ciclo vem por Workflow na Fase 2), **Naming = By "Naming Series"**, **Track Changes = on**.
Série: `OS-.YYYY.-.#####`

Organize em seções (Section Break). Campos:

**Identificação**
| Label | Fieldname | Tipo | Notas |
|---|---|---|---|
| Série | `naming_series` | Select | `OS-.YYYY.-.#####` |
| Cliente | `customer` | Link → Customer | obrigatório |
| Aparelho | `customer_device` | Link → Customer Device | filtrado pelo cliente |
| Data de entrada | `entry_date` | Datetime | default Now |
| Atendente | `attendant` | Link → User | |
| Técnico | `technician` | Link → User | |
| Prioridade | `priority` | Select | Baixa\nNormal\nAlta\nUrgente |
| Status (workflow) | `workflow_state` | Link → Workflow State | preenchido pelo Workflow (Fase 2) |

**Entrada**
| Label | Fieldname | Tipo |
|---|---|---|
| Defeito relatado | `reported_defect` | Small Text |
| Observações do atendimento | `attendance_notes` | Text |
| Estado físico de entrada | `physical_state` | Small Text |
| Acessórios recebidos | `accessories_received` | Small Text |
| Fotos de entrada | `entry_photos` | Attach / Table |

**Diagnóstico** (seção dentro da OS no MVP)
| Label | Fieldname | Tipo |
|---|---|---|
| Problema encontrado | `problem_found` | Text |
| Causa provável | `probable_cause` | Small Text |
| Solução recomendada | `recommended_solution` | Small Text |
| Prazo estimado | `estimated_deadline` | Date |
| Observações do diagnóstico | `diagnosis_notes` | Text |
| Data do diagnóstico | `diagnosis_date` | Date |

**Orçamento**
| Label | Fieldname | Tipo | Notas |
|---|---|---|---|
| Serviços/Mão de obra | `services` | Table → Service Order Service | |
| Peças | `parts` | Table → Service Order Part | |
| Total mão de obra | `labor_total` | Currency | calculado (Fase 2) |
| Total peças | `parts_total` | Currency | calculado (Fase 2) |
| Desconto | `discount` | Currency | |
| Total geral | `grand_total` | Currency | calculado (Fase 2) |

**Aprovação**
| Label | Fieldname | Tipo |
|---|---|---|
| Status da aprovação | `approval_status` | Select (Pendente\nAprovado\nReprovado) |
| Aprovado por | `approved_by` | Link → User |
| Data da aprovação | `approval_date` | Datetime |
| Observação da aprovação | `approval_notes` | Small Text |

**Financeiro**
| Label | Fieldname | Tipo | Notas |
|---|---|---|---|
| Forma de pagamento | `mode_of_payment` | Link → Mode of Payment | |
| Sales Invoice | `sales_invoice` | Link → Sales Invoice | **read-only** (preenchido pelo sistema na Fase 2) |

**Retirada**
| Label | Fieldname | Tipo |
|---|---|---|
| Data de retirada | `pickup_date` | Datetime |
| Retirado por | `picked_up_by` | Data |
| Documento de quem retirou | `picked_up_doc` | Data |
| Fotos finais | `pickup_photos` | Attach / Table |
| Assinatura | `customer_signature` | Signature |
| Observação da retirada | `pickup_notes` | Small Text |

**Interno**
| Label | Fieldname | Tipo | Notas |
|---|---|---|---|
| Observações internas | `internal_notes` | Text | **perm level 1** |

---

## Passo 6 — Child tables da OS

**`Service Order Part`** (Settings: **Is Child Table = on**, Module Tecponto):
| Label | Fieldname | Tipo |
|---|---|---|
| Item | `item_code` | Link → Item |
| Quantidade | `qty` | Float |
| Depósito | `warehouse` | Link → Warehouse |
| Custo | `valuation_rate` | Currency (read-only) |
| Preço | `rate` | Currency |
| Técnico | `technician` | Link → User |
| Data de uso | `used_date` | Date |

**`Service Order Service`** (Is Child Table = on):
| Label | Fieldname | Tipo |
|---|---|---|
| Item de serviço | `item_code` | Link → Item |
| Descrição | `description` | Small Text |
| Quantidade | `qty` | Float |
| Valor | `rate` | Currency |

---

## Passo 7 — DocType `Device Trade Evaluation` (Avaliação de Troca)

Settings: Module Tecponto, Naming Series `TROCA-.YYYY.-.####`.

| Label | Fieldname | Tipo |
|---|---|---|
| Cliente | `customer` | Link → Customer |
| Descrição do aparelho | `evaluated_device_desc` | Data |
| Modelo | `model` | Data |
| Estado físico | `physical_state` | Select |
| Capacidade | `capacity` | Select |
| Bloqueio iCloud/Google | `icloud_google_lock` | Check |
| Tem nota fiscal | `has_invoice` | Check |
| Defeitos | `defects` | Text |
| Valor sugerido | `suggested_value` | Currency |
| Valor aprovado | `approved_value` | Currency |
| Aprovado por | `approved_by` | Link → User |
| Destino | `destination` | Select (Venda\nPeças\nDescarte) |
| Status | `workflow_state` | Link → Workflow State (Fase 2) |
| Item criado | `created_item` | Link → Item (read-only, Fase 2) |

---

## Passo 8 — DocType `Tecponto Settings` (Single)

Settings: Module Tecponto, **Is Single = on**.

| Label | Fieldname | Tipo |
|---|---|---|
| Depósito padrão de peças | `default_parts_warehouse` | Link → Warehouse |
| Depósito de acessórios | `default_accessories_warehouse` | Link → Warehouse |
| Depósito de usados | `used_devices_warehouse` | Link → Warehouse |
| Item de mão de obra padrão | `default_labor_item` | Link → Item |
| Limite de desconto sem aprovação | `discount_limit` | Currency |
| Provedor de notificação | `notification_provider` | Select (Nenhum\nLog\nWhatsApp Oficial\nEvolution) |

Depois de criar, **preencha** apontando para os registros da Fase 0 (`Peças - TEC`, `Acessórios - TEC`, `Aparelhos Usados - TEC`, `MO-REPARO`). Provedor = `Nenhum` por enquanto.

---

## Passo 9 — Criar as Roles

Em "Role" → New (apenas criar; permissões finas vêm na Fase 2):
- `Tecponto Atendente`
- `Tecponto Tecnico`
- `Tecponto Gestor`

---

## Passo 10 — Teste de integração (validar relações)

Pela interface, crie e confirme que os links funcionam:
1. Um **Customer** com WhatsApp/CPF preenchidos.
2. Um **Customer Device** ligado a esse cliente.
3. Uma **Service Order** que seleciona o cliente e, ao escolher o cliente, lista só os aparelhos dele.
4. Adicione 1 peça e 1 serviço nas child tables (sem esperar cálculo automático — isso é Fase 2).
5. Uma **Device Trade Evaluation** de teste.

---

## Critério de "pronto"

- [ ] Os 5 DocTypes existem **com Module = Tecponto** e geraram pasta em `apps/tecponto_app/.../doctype/`.
- [ ] Custom Fields de Customer e Item aparecem e estão nas fixtures.
- [ ] `bench --site tecponto.local migrate` roda sem erro.
- [ ] Consegue criar a cadeia Cliente → Aparelho → OS com links corretos.
- [ ] As 3 roles existem.
- [ ] `Tecponto Settings` preenchido.

## Fechar a fase

```bash
bench --site tecponto.local export-fixtures
bench --site tecponto.local migrate
cd apps/tecponto_app
git add -A && git commit -m "feat: data model — doctypes e custom fields (Fase 1)"
```

➡️ **Próximo:** Fase 2 — Workflow da OS + lógica que gera a Sales Invoice (baixa de estoque idempotente) + permissões por role.

---

## Anexo — JSON de exemplo (para builder IA): `customer_device.json`

```json
{
  "doctype": "DocType",
  "name": "Customer Device",
  "module": "Tecponto",
  "custom": 0,
  "naming_rule": "Autoincrement",
  "track_changes": 1,
  "fields": [
    {"fieldname": "customer", "label": "Cliente", "fieldtype": "Link", "options": "Customer", "reqd": 1, "in_list_view": 1},
    {"fieldname": "brand", "label": "Marca", "fieldtype": "Data"},
    {"fieldname": "model", "label": "Modelo", "fieldtype": "Data", "in_list_view": 1},
    {"fieldname": "color", "label": "Cor", "fieldtype": "Data"},
    {"fieldname": "imei_serial", "label": "IMEI / Serial", "fieldtype": "Data", "search_index": 1},
    {"fieldname": "capacity", "label": "Capacidade", "fieldtype": "Select", "options": "\n32GB\n64GB\n128GB\n256GB\n512GB\n1TB"},
    {"fieldname": "device_password", "label": "Senha/Padrão", "fieldtype": "Data", "permlevel": 1},
    {"fieldname": "general_state", "label": "Estado geral", "fieldtype": "Small Text"},
    {"fieldname": "notes", "label": "Observações", "fieldtype": "Text"},
    {"fieldname": "photos", "label": "Fotos", "fieldtype": "Attach Image"},
    {"fieldname": "registration_date", "label": "Data de cadastro", "fieldtype": "Date", "default": "Today"}
  ],
  "permissions": [
    {"role": "Tecponto Atendente", "read": 1, "write": 1, "create": 1},
    {"role": "Tecponto Gestor", "read": 1, "write": 1, "create": 1, "delete": 1},
    {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "permlevel": 0},
    {"role": "Tecponto Gestor", "read": 1, "write": 1, "permlevel": 1}
  ]
}
```
Acompanha um `customer_device.py` mínimo:
```python
import frappe
from frappe.model.document import Document

class CustomerDevice(Document):
    pass
```
