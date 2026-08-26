from __future__ import annotations

import frappe
from frappe.utils import date_diff, flt, nowdate

from tecponto_app.tecponto.financial import native_financial_posting
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
	if doc.get("pickup_without_repair"):
		return None

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

	# ERPNext resolves the Customer receivable account during insert. The OS
	# transition has already been authorized; only that native posting is elevated.
	with native_financial_posting():
		si.insert(ignore_permissions=True)
		si.submit()
	doc.db_set("sales_invoice", si.name, update_modified=False)
	doc.sales_invoice = si.name
	return si.name


def reverse_billed_service_order_invoice(service_order: str) -> dict:
	"""Create the remaining native invoice return before cancelling a billed OS.

	A Service Order is never allowed to become ``Cancelado`` while its submitted
	Sales Invoice remains financially effective.  Existing partial returns are
	respected: only the outstanding quantities are returned, then the workflow
	transition may proceed.  The caller is the approval engine under a Gestor's
	real session; no requester permission is impersonated here.
	"""
	order = frappe.get_doc("Service Order", service_order)
	from tecponto_app.tecponto.service_order.policies import _user_is_manager

	if not _user_is_manager():
		frappe.throw("Somente Gestor pode estornar a nota de uma OS faturada.")
	if not order.get("sales_invoice"):
		frappe.throw("A OS não está faturada.")

	invoice = frappe.get_doc(DOCTYPE_SALES_INVOICE, order.sales_invoice)
	if invoice.docstatus != 1 or invoice.is_return:
		frappe.throw("A nota vinculada não está disponível para estorno.")

	remaining = _remaining_invoice_return_lines(invoice)
	if not remaining:
		return {"sales_invoice": invoice.name, "return_invoice": None, "already_reversed": True}

	# Reuse the post-sale builder so POS payments retain their original payment
	# split and regular invoices remain ERPNext-native returns.
	from tecponto_app.tecponto.frontend.api import _build_sales_return, _run_post_sale_mutation

	# A Gestor has already passed the cancellation gate above. ERPNext's mapper
	# additionally demands Sales Invoice create permission, which this operational
	# role intentionally does not hold. Elevate only the native return posting
	# scope; the user session is restored by _run_post_sale_mutation immediately.
	with _run_post_sale_mutation():
		return_doc = _build_sales_return({"invoice": invoice.name, "items": remaining})
		return_doc.remarks = f"Estorno integral para cancelamento da OS {order.name}."
		return_doc.insert(ignore_permissions=True)
		return_doc.submit()
	return {
		"sales_invoice": invoice.name,
		"return_invoice": return_doc.name,
		"already_reversed": False,
	}


def has_full_billed_service_order_reversal(service_order: str) -> bool:
	"""Whether every invoice line tied to a billed OS has a submitted return."""
	invoice_name = frappe.db.get_value("Service Order", service_order, "sales_invoice")
	if not invoice_name:
		return True
	invoice = frappe.get_doc(DOCTYPE_SALES_INVOICE, invoice_name)
	if invoice.docstatus != 1 or invoice.is_return:
		return False
	return not _remaining_invoice_return_lines(invoice)


def _remaining_invoice_return_lines(invoice) -> list[dict]:
	returned_rows = frappe.db.sql(
		"""
		select item_code, abs(sum(qty)) as qty
		from `tabSales Invoice Item`
		where docstatus = 1 and parenttype = 'Sales Invoice'
		and parent in (
			select name from `tabSales Invoice`
			where return_against = %(invoice)s and is_return = 1 and docstatus = 1
		)
		group by item_code
		""",
		{"invoice": invoice.name},
		as_dict=True,
	)
	returned_by_item = {row.item_code: flt(row.qty) for row in returned_rows}
	remaining = []
	for row in invoice.items:
		available = flt(row.qty) - returned_by_item.get(row.item_code, 0)
		if available > 0:
			remaining.append({"item_code": row.item_code, "qty": available})
	return remaining


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
	company = company or _get_company(doc)
	payment_entries: list[str] = []
	if doc.get("sinal_enabled") and flt(doc.get("sinal_value")) > 0:
		legacy_entry = ensure_sinal_payment(doc, company=company)
		if legacy_entry:
			payment_entries.append(legacy_entry)

	# New OS receipts use their own idempotent operational record but remain
	# native Payment Entries. Allocate all advances when ERPNext creates the note.
	from tecponto_app.tecponto.service_order.payments import pending_advance_payment_entries

	payment_entries.extend(pending_advance_payment_entries(doc.name))
	seen: set[str] = set()
	for payment_entry in payment_entries:
		if not payment_entry or payment_entry in seen:
			continue
		seen.add(payment_entry)
		payment_doc = frappe.get_doc("Payment Entry", payment_entry)
		amount = flt(payment_doc.get("paid_amount"))
		if amount <= 0:
			continue
		if doc.get("workflow_state") in SIGNAL_RETENTION_STATES:
			_append_invoice_item(
				si,
				item_code=_get_labor_item(),
				qty=1,
				rate=amount,
				description="Retencao de sinal da OS {0}".format(doc.name),
				company=company,
			)
		allocated_amount = min(amount, _invoice_total(si))
		if allocated_amount <= 0:
			continue
		si.append(
			"advances",
			{
				"reference_type": "Payment Entry",
				"reference_name": payment_entry,
				"remarks": payment_doc.get("remarks"),
				"advance_amount": amount,
				"allocated_amount": allocated_amount,
				"ref_exchange_rate": 1,
				"difference_posting_date": si.posting_date,
			},
		)


def _aplicar_estadia(doc, si, company: str | None = None) -> None:
	from tecponto_app.tecponto.operation_config import get_operation_config

	storage = get_operation_config()["storage_fee"]
	if storage["enabled"] and not doc.get("estadia_enabled"):
		# Storage is a per-store policy. Persist the server-derived values so the
		# generated invoice remains auditable even if settings change later.
		doc.estadia_enabled = 1
		doc.estadia_start_date = doc.get("pickup_date") or doc.get("entry_date") or nowdate()
		doc.estadia_daily_value = flt(storage["amount"], 2)
		doc.estadia_grace_days = int(storage["start_days"])
		frappe.db.set_value(
			doc.doctype,
			doc.name,
			{
				"estadia_enabled": 1,
				"estadia_start_date": doc.estadia_start_date,
				"estadia_daily_value": doc.estadia_daily_value,
				"estadia_grace_days": doc.estadia_grace_days,
			},
			update_modified=False,
		)
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
