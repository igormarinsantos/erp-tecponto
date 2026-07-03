from __future__ import annotations

import frappe
from frappe.utils import flt, nowdate


DOCTYPE_PAYMENT_ENTRY = "Payment Entry"
DEFAULT_MODE_OF_PAYMENT = "Dinheiro"
MANAGER_ROLES = {"Tecponto Gestor", "System Manager"}


def processar_sinal(doc, method=None) -> str | None:
	return ensure_sinal_payment(doc)


def ensure_sinal_payment(doc, company: str | None = None) -> str | None:
	if not _should_create_sinal_payment(doc):
		return doc.get("sinal_payment_entry")

	existing = _get_existing_sinal_payment(doc)
	if existing:
		_set_service_order_value(doc, "sinal_payment_entry", existing)
		return existing

	company = company or _get_company(doc)
	amount = flt(doc.get("sinal_value"))
	currency = _get_currency(company)
	paid_from = _get_receivable_account(company)
	mode_of_payment = doc.get("mode_of_payment") or _get_default_mode_of_payment(company)
	paid_to = _get_payment_account(mode_of_payment, company)

	payment_entry = frappe.new_doc(DOCTYPE_PAYMENT_ENTRY)
	payment_entry.payment_type = "Receive"
	payment_entry.company = company
	payment_entry.posting_date = nowdate()
	payment_entry.mode_of_payment = mode_of_payment
	payment_entry.party_type = "Customer"
	payment_entry.party = doc.customer
	payment_entry.paid_from = paid_from
	payment_entry.paid_from_account_currency = _get_account_currency(paid_from, currency)
	payment_entry.paid_to = paid_to
	payment_entry.paid_to_account_currency = _get_account_currency(paid_to, currency)
	payment_entry.paid_amount = amount
	payment_entry.base_paid_amount = amount
	payment_entry.received_amount = amount
	payment_entry.base_received_amount = amount
	payment_entry.source_exchange_rate = 1
	payment_entry.target_exchange_rate = 1
	payment_entry.reference_no = _get_sinal_reference(doc)
	payment_entry.reference_date = nowdate()
	payment_entry.remarks = _get_sinal_remarks(doc)
	payment_entry.insert(ignore_permissions=True)
	payment_entry.submit()

	_set_service_order_value(doc, "sinal_payment_entry", payment_entry.name)
	return payment_entry.name


@frappe.whitelist()
def devolver_sinal_por_erro_nosso(service_order: str, reason: str) -> str:
	if not _user_is_manager():
		frappe.throw("Somente Gestor pode devolver sinal.")

	if "erro nosso" not in (reason or "").lower():
		frappe.throw("Devolucao de sinal exige justificativa marcada como erro nosso.")

	doc = frappe.get_doc("Service Order", service_order)
	if not (doc.get("sinal_enabled") and doc.get("sinal_payment_entry")):
		frappe.throw("OS nao possui sinal vinculado para devolucao.")

	existing = _get_existing_sinal_refund(doc)
	if existing:
		return existing

	company = _get_company(doc)
	amount = flt(doc.get("sinal_value"))
	currency = _get_currency(company)
	paid_from = _get_payment_account(doc.get("mode_of_payment") or _get_default_mode_of_payment(company), company)
	paid_to = _get_receivable_account(company)

	payment_entry = frappe.new_doc(DOCTYPE_PAYMENT_ENTRY)
	payment_entry.payment_type = "Pay"
	payment_entry.company = company
	payment_entry.posting_date = nowdate()
	payment_entry.mode_of_payment = doc.get("mode_of_payment") or _get_default_mode_of_payment(company)
	payment_entry.party_type = "Customer"
	payment_entry.party = doc.customer
	payment_entry.paid_from = paid_from
	payment_entry.paid_from_account_currency = _get_account_currency(paid_from, currency)
	payment_entry.paid_to = paid_to
	payment_entry.paid_to_account_currency = _get_account_currency(paid_to, currency)
	payment_entry.paid_amount = amount
	payment_entry.base_paid_amount = amount
	payment_entry.received_amount = amount
	payment_entry.base_received_amount = amount
	payment_entry.source_exchange_rate = 1
	payment_entry.target_exchange_rate = 1
	payment_entry.reference_no = _get_sinal_refund_reference(doc)
	payment_entry.reference_date = nowdate()
	payment_entry.remarks = "Devolucao de sinal da OS {0} por erro nosso: {1}".format(doc.name, reason)
	payment_entry.insert(ignore_permissions=True)
	payment_entry.submit()
	return payment_entry.name


def _should_create_sinal_payment(doc) -> bool:
	if doc.get("is_warranty"):
		return False

	return bool(doc.get("sinal_enabled")) and flt(doc.get("sinal_value")) > 0


def _get_existing_sinal_payment(doc) -> str | None:
	payment_entry = doc.get("sinal_payment_entry")
	if payment_entry and frappe.db.exists(DOCTYPE_PAYMENT_ENTRY, payment_entry):
		if frappe.db.get_value(DOCTYPE_PAYMENT_ENTRY, payment_entry, "docstatus") == 1:
			return payment_entry

	return frappe.db.get_value(
		DOCTYPE_PAYMENT_ENTRY,
		{
			"payment_type": "Receive",
			"party_type": "Customer",
			"party": doc.customer,
			"reference_no": _get_sinal_reference(doc),
			"docstatus": 1,
		},
		"name",
	)


def _get_existing_sinal_refund(doc) -> str | None:
	return frappe.db.get_value(
		DOCTYPE_PAYMENT_ENTRY,
		{
			"payment_type": "Pay",
			"party_type": "Customer",
			"party": doc.customer,
			"reference_no": _get_sinal_refund_reference(doc),
			"docstatus": 1,
		},
		"name",
	)


def _get_sinal_reference(doc) -> str:
	return "SINAL-{0}".format(doc.name)


def _get_sinal_refund_reference(doc) -> str:
	return "DEVOLUCAO-SINAL-{0}".format(doc.name)


def _get_sinal_remarks(doc) -> str:
	return "Sinal da OS {0}.".format(doc.name)


def _get_default_mode_of_payment(company: str) -> str | None:
	for mode_of_payment in (DEFAULT_MODE_OF_PAYMENT, "Pix", "Cash"):
		if frappe.db.exists("Mode of Payment", mode_of_payment) and _get_payment_account(mode_of_payment, company):
			return mode_of_payment

	return None


def _get_payment_account(mode_of_payment: str | None, company: str) -> str:
	if mode_of_payment and frappe.db.exists("Mode of Payment", mode_of_payment):
		mode = frappe.get_cached_doc("Mode of Payment", mode_of_payment)
		for account_row in mode.get("accounts") or []:
			if account_row.get("company") == company and account_row.get("default_account"):
				return account_row.default_account

	default_bank = frappe.get_cached_value("Company", company, "default_bank_account")
	if default_bank:
		return default_bank

	account = frappe.db.get_value(
		"Account",
		{
			"company": company,
			"account_type": ["in", ["Bank", "Cash"]],
			"is_group": 0,
		},
		"name",
		order_by="lft asc",
	)
	if account:
		return account

	frappe.throw("Conta de recebimento nao configurada para registrar o sinal.")


def _get_company(doc) -> str:
	company = doc.get("company") or frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw("Empresa padrao nao configurada para registrar o sinal.")

	return company


def _get_receivable_account(company: str) -> str:
	account = frappe.get_cached_value("Company", company, "default_receivable_account")
	if account:
		return account

	account = frappe.db.get_value(
		"Account",
		{
			"company": company,
			"account_type": "Receivable",
			"is_group": 0,
		},
		"name",
		order_by="lft asc",
	)
	if account:
		return account

	frappe.throw("Conta de clientes nao configurada para registrar o sinal.")


def _get_currency(company: str) -> str:
	return (
		frappe.get_cached_value("Company", company, "default_currency")
		or frappe.defaults.get_global_default("currency")
		or "BRL"
	)


def _get_account_currency(account: str, fallback: str) -> str:
	return frappe.get_cached_value("Account", account, "account_currency") or fallback


def _set_service_order_value(doc, fieldname: str, value) -> None:
	if doc.get(fieldname) == value:
		return

	frappe.db.set_value(doc.doctype, doc.name, fieldname, value, update_modified=False)
	doc.set(fieldname, value)


def _user_is_manager() -> bool:
	if frappe.session.user == "Administrator":
		return True

	return bool(set(frappe.get_roles()) & MANAGER_ROLES)
