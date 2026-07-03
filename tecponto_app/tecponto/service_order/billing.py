from __future__ import annotations

import frappe
from frappe.utils import date_diff, flt, nowdate

from tecponto_app.tecponto.service_order.advance import ensure_sinal_payment
from tecponto_app.tecponto.service_order.parts import OUTCOME_USADA


DOCTYPE_SALES_INVOICE = "Sales Invoice"
STATE_PRONTO_RETIRADA = "Pronto para retirada"
STATE_REPROVADO = "Reprovado"
STATE_ORCAMENTO_EXPIRADO = "Or\u00e7amento expirado"
STATE_SEM_CONSERTO = "Sem conserto"
STATE_CANCELADO = "Cancelado"
DIAGNOSIS_FEE_STATES = {STATE_REPROVADO, STATE_ORCAMENTO_EXPIRADO}
SIGNAL_RETENTION_STATES = {
	STATE_REPROVADO,
	STATE_ORCAMENTO_EXPIRADO,
	STATE_SEM_CONSERTO,
	STATE_CANCELADO,
}
INVOICE_STATES = {STATE_PRONTO_RETIRADA} | SIGNAL_RETENTION_STATES


def gerar_nota(doc, method=None):
	if doc.sales_invoice:
		return doc.sales_invoice

	if doc.get("is_warranty"):
		return None

	if doc.get("workflow_state") not in INVOICE_STATES:
		return None

	company = _get_company(doc)
	si = frappe.new_doc(DOCTYPE_SALES_INVOICE)
	si.customer = doc.customer
	si.company = company
	si.update_stock = 0
	si.set_posting_time = 1
	si.posting_date = nowdate()
	si.due_date = nowdate()
	si.currency = _get_currency(company)
	si.conversion_rate = 1
	si.selling_price_list = _get_selling_price_list()
	si.price_list_currency = si.currency
	si.plc_conversion_rate = 1
	si.remarks = "Fechamento da OS {0}.".format(doc.name)

	debit_to = _get_receivable_account(company)
	if debit_to:
		si.debit_to = debit_to

	if _is_final_repair_invoice(doc):
		_append_repair_items(doc, si, company)
		_aplicar_estadia(doc, si, company)
		_aplicar_desconto(doc, si)

	_aplicar_taxa_diagnostico(doc, si, company)
	_alocar_sinal(doc, si, company)

	if not si.get("items"):
		if doc.get("workflow_state") in SIGNAL_RETENTION_STATES:
			return None

		frappe.throw("Nao ha itens cobraveis para gerar a nota da OS {0}.".format(doc.name))

	si.insert(ignore_permissions=True)
	si.submit()
	doc.db_set("sales_invoice", si.name, update_modified=False)
	doc.sales_invoice = si.name
	return si.name


def _append_repair_items(doc, si, company: str) -> None:
	for service_row in doc.get("services") or []:
		_append_invoice_item(
			si,
			item_code=service_row.get("item_code"),
			qty=service_row.get("qty"),
			rate=service_row.get("rate"),
			description=service_row.get("description"),
			company=company,
		)

	for part_row in doc.get("parts") or []:
		if part_row.get("outcome") != OUTCOME_USADA:
			continue

		_append_invoice_item(
			si,
			item_code=part_row.get("item_code"),
			qty=part_row.get("qty"),
			rate=part_row.get("rate"),
			warehouse=part_row.get("warehouse"),
			company=company,
		)


def _append_invoice_item(
	si,
	*,
	item_code: str | None,
	qty,
	rate,
	company: str,
	description: str | None = None,
	warehouse: str | None = None,
) -> None:
	if not item_code:
		frappe.throw("Item obrigatorio para gerar a nota.")

	if flt(qty) <= 0:
		return

	row = {
		"item_code": item_code,
		"qty": flt(qty),
		"rate": flt(rate),
		"conversion_factor": 1,
	}

	if description:
		row["description"] = description

	if warehouse:
		row["warehouse"] = warehouse

	income_account = _get_income_account(company)
	if income_account:
		row["income_account"] = income_account

	cost_center = _get_cost_center(company)
	if cost_center:
		row["cost_center"] = cost_center

	si.append("items", row)


def _aplicar_taxa_diagnostico(doc, si, company: str | None = None) -> None:
	if doc.get("workflow_state") not in DIAGNOSIS_FEE_STATES:
		return

	if not doc.get("diagnosis_fee_enabled"):
		return

	diagnosis_fee = flt(doc.get("diagnosis_fee_value"))
	if diagnosis_fee <= 0:
		return

	_append_invoice_item(
		si,
		item_code=_get_labor_item(),
		qty=1,
		rate=diagnosis_fee,
		description="Taxa de diagnostico da OS {0}".format(doc.name),
		company=company or _get_company(doc),
	)


def _alocar_sinal(doc, si, company: str | None = None) -> None:
	if not doc.get("sinal_enabled") or flt(doc.get("sinal_value")) <= 0:
		return

	company = company or _get_company(doc)
	payment_entry = ensure_sinal_payment(doc, company=company)
	if not payment_entry:
		return

	sinal_value = flt(doc.get("sinal_value"))
	if doc.get("workflow_state") in SIGNAL_RETENTION_STATES:
		_append_invoice_item(
			si,
			item_code=_get_labor_item(),
			qty=1,
			rate=sinal_value,
			description="Retencao de sinal da OS {0}".format(doc.name),
			company=company,
		)

	allocated_amount = min(sinal_value, _invoice_total(si))
	if allocated_amount <= 0:
		return

	payment_doc = frappe.get_doc("Payment Entry", payment_entry)
	si.append(
		"advances",
		{
			"reference_type": "Payment Entry",
			"reference_name": payment_entry,
			"remarks": payment_doc.get("remarks"),
			"advance_amount": sinal_value,
			"allocated_amount": allocated_amount,
			"ref_exchange_rate": 1,
			"difference_posting_date": si.posting_date,
		},
	)


def _aplicar_estadia(doc, si, company: str | None = None) -> None:
	if not doc.get("estadia_enabled"):
		return

	estadia_total = _calcular_estadia(doc)
	_set_doc_value(doc, "estadia_total", estadia_total)
	if estadia_total <= 0:
		return

	_append_invoice_item(
		si,
		item_code=_get_labor_item(),
		qty=1,
		rate=estadia_total,
		description="Estadia da OS {0}".format(doc.name),
		company=company or _get_company(doc),
	)


def _aplicar_desconto(doc, si) -> None:
	discount = flt(doc.get("discount"))
	if discount <= 0:
		return

	si.apply_discount_on = "Grand Total"
	si.discount_amount = discount


def _calcular_estadia(doc) -> float:
	start_date = doc.get("estadia_start_date")
	if not start_date:
		frappe.throw("Estadia habilitada exige data de inicio.")

	daily_value = flt(doc.get("estadia_daily_value")) or flt(
		frappe.db.get_single_value("Tecponto Settings", "valor_diaria")
	)
	if daily_value <= 0:
		frappe.throw("Estadia habilitada exige valor de diaria maior que zero.")

	grace_days = doc.get("estadia_grace_days")
	if grace_days in (None, ""):
		grace_days = frappe.db.get_single_value("Tecponto Settings", "carencia_dias")

	chargeable_days = max(date_diff(nowdate(), start_date) - int(grace_days or 0), 0)
	total = flt(chargeable_days * daily_value)

	labor_total = _service_total(doc)
	configured_cap = flt(doc.get("estadia_cap_value")) or flt(
		frappe.db.get_single_value("Tecponto Settings", "teto")
	)
	caps = [value for value in (configured_cap, labor_total) if value > 0]
	if caps:
		total = min(total, min(caps))

	return total


def _invoice_total(si) -> float:
	total = sum(flt(row.get("qty")) * flt(row.get("rate")) for row in si.get("items") or [])
	if si.get("apply_discount_on") == "Grand Total":
		total -= flt(si.get("discount_amount"))

	return max(total, 0)


def _service_total(doc) -> float:
	return sum(flt(row.get("qty")) * flt(row.get("rate")) for row in doc.get("services") or [])


def _is_final_repair_invoice(doc) -> bool:
	return doc.get("workflow_state") == STATE_PRONTO_RETIRADA


def _set_doc_value(doc, fieldname: str, value) -> None:
	if flt(doc.get(fieldname)) == flt(value):
		return

	frappe.db.set_value(doc.doctype, doc.name, fieldname, value, update_modified=False)
	doc.set(fieldname, value)


def _get_company(doc) -> str:
	if doc.get("company"):
		return doc.company

	for part_row in doc.get("parts") or []:
		warehouse = part_row.get("warehouse")
		if not warehouse:
			continue

		company = frappe.get_cached_value("Warehouse", warehouse, "company")
		if company:
			return company

	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw("Empresa padrao nao configurada para gerar a nota.")

	return company


def _get_receivable_account(company: str) -> str | None:
	company_default = frappe.get_cached_value("Company", company, "default_receivable_account")
	if company_default:
		return company_default

	return frappe.db.get_value(
		"Account",
		{
			"company": company,
			"account_type": "Receivable",
			"is_group": 0,
		},
		"name",
		order_by="lft asc",
	)


def _get_currency(company: str) -> str:
	return (
		frappe.get_cached_value("Company", company, "default_currency")
		or frappe.defaults.get_global_default("currency")
		or "BRL"
	)


def _get_selling_price_list() -> str | None:
	return (
		frappe.db.get_single_value("Selling Settings", "selling_price_list")
		or frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
	)


def _get_labor_item() -> str:
	settings_item = frappe.db.get_single_value("Tecponto Settings", "default_labor_item")
	if settings_item and frappe.db.exists("Item", settings_item):
		return settings_item

	item = frappe.db.get_value(
		"Item",
		{
			"is_stock_item": 0,
			"is_sales_item": 1,
		},
		"name",
	)
	if item:
		return item

	frappe.throw("Item padrao de mao de obra nao configurado.")


def _get_income_account(company: str) -> str | None:
	company_default = frappe.get_cached_value("Company", company, "default_income_account")
	if company_default:
		return company_default

	return frappe.db.get_value(
		"Account",
		{
			"company": company,
			"root_type": "Income",
			"is_group": 0,
		},
		"name",
		order_by="lft asc",
	)


def _get_cost_center(company: str) -> str | None:
	company_default = frappe.get_cached_value("Company", company, "cost_center")
	if company_default:
		return company_default

	return frappe.db.get_value(
		"Cost Center",
		{
			"company": company,
			"is_group": 0,
		},
		"name",
		order_by="lft asc",
	)
