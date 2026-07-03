from __future__ import annotations

import frappe
from frappe.utils import flt, nowdate

from tecponto_app.tecponto.service_order.parts import OUTCOME_USADA


DOCTYPE_SALES_INVOICE = "Sales Invoice"
STATE_PRONTO_RETIRADA = "Pronto para retirada"


def gerar_nota(doc, method=None):
	if doc.sales_invoice:
		return doc.sales_invoice

	if doc.get("workflow_state") != STATE_PRONTO_RETIRADA:
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

	_aplicar_taxa_diagnostico(doc, si)
	_alocar_sinal(doc, si)
	_aplicar_desconto(doc, si)

	if not si.get("items"):
		frappe.throw("Nao ha itens cobraveis para gerar a nota da OS {0}.".format(doc.name))

	si.insert(ignore_permissions=True)
	si.submit()
	doc.db_set("sales_invoice", si.name, update_modified=False)
	doc.sales_invoice = si.name
	return si.name


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


def _aplicar_taxa_diagnostico(doc, si) -> None:
	# Hook reservado para o Passo 8/R4: reprovado/expirado cobra somente a taxa.
	return None


def _alocar_sinal(doc, si) -> None:
	# Hook reservado para o Passo 8/R9: alocar adiantamento contra a nota.
	return None


def _aplicar_desconto(doc, si) -> None:
	discount = flt(doc.get("discount"))
	if discount <= 0:
		return

	si.apply_discount_on = "Grand Total"
	si.discount_amount = discount


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
