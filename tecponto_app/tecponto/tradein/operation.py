from __future__ import annotations

import frappe
from erpnext.accounts.party import get_party_account
from frappe.utils import flt, nowdate

from tecponto_app.tecponto.tradein.buyback import (
	_cash_or_bank_account,
	_default_company,
	_mode_of_payment,
	registrar_entrada_usado,
)


STATE_PENDENTE = "Pendente"
STATE_CONCLUIDA = "Concluída"
STATE_CONFIRMADA = "Confirmada"
MANAGER_ROLES = {"Tecponto Gestor", "System Manager"}
STOCK_ENTRY_TYPE_MATERIAL_ISSUE = "Material Issue"


def confirmar_troca(doc, method=None) -> None:
	if doc.get("atomic_status") in {STATE_CONCLUIDA, STATE_CONFIRMADA}:
		return

	if doc.get("atomic_status") != STATE_PENDENTE:
		return

	_validar_diferenca(doc)
	evaluation = frappe.get_doc("Device Trade Evaluation", doc.get("evaluation"))
	_validar_margem_troca(doc, evaluation)

	savepoint = "trade_in_operation"
	frappe.db.savepoint(savepoint)
	try:
		used_item = registrar_entrada_usado(evaluation, pay_customer=False)
		sale_stock_entry = _saida_aparelho(doc)
		_registrar_pagamento_diferenca(doc)
		doc.db_set(
			{
				"atomic_status": STATE_CONCLUIDA,
				"used_device_fiscal_ref": used_item,
				"sale_fiscal_ref": sale_stock_entry,
			},
			update_modified=False,
		)
		doc.atomic_status = STATE_CONCLUIDA
		doc.used_device_fiscal_ref = used_item
		doc.sale_fiscal_ref = sale_stock_entry
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def _validar_diferenca(doc) -> None:
	if flt(doc.get("difference")) < 0:
		frappe.throw("A diferença da troca não pode ser negativa.")


def _validar_margem_troca(doc, evaluation) -> None:
	if _user_is_manager():
		return

	item_code = _device_out_item_code(doc)
	output_cost = _valuation_rate(item_code, _commercial_warehouse())
	consideration = flt(evaluation.get("approved_value")) + flt(doc.get("difference"))

	if output_cost and consideration < output_cost:
		frappe.throw("Troca abaixo do custo exige Gestor.")


def _saida_aparelho(doc) -> str:
	existing = frappe.db.get_value(
		"Stock Entry",
		{"docstatus": 1, "remarks": _sale_reference(doc)},
		"name",
	)
	if existing:
		return existing

	serial = _get_available_output_serial(doc)
	warehouse = _commercial_warehouse()
	stock_entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": STOCK_ENTRY_TYPE_MATERIAL_ISSUE,
			"purpose": STOCK_ENTRY_TYPE_MATERIAL_ISSUE,
			"company": _default_company(),
			"posting_date": nowdate(),
			"remarks": _sale_reference(doc),
			"items": [
				{
					"item_code": serial.item_code,
					"qty": 1,
					"s_warehouse": warehouse,
					"basic_rate": _valuation_rate(serial.item_code, warehouse),
					"serial_no": serial.serial_no,
				}
			],
		}
	)
	stock_entry.insert(ignore_permissions=True)
	stock_entry.submit()
	return stock_entry.name


def _registrar_pagamento_diferenca(doc) -> str | None:
	amount = flt(doc.get("difference"))
	if amount <= 0:
		return None

	existing = frappe.db.get_value(
		"Payment Entry",
		{"docstatus": 1, "reference_no": _difference_reference(doc)},
		"name",
	)
	if existing:
		return existing

	company = _default_company()
	payment = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"company": company,
			"posting_date": nowdate(),
			"mode_of_payment": doc.get("payment_mode") or _mode_of_payment(company),
			"party_type": "Customer",
			"party": doc.get("customer"),
			"paid_from": get_party_account("Customer", doc.get("customer"), company),
			"paid_to": _cash_or_bank_account(company),
			"paid_amount": amount,
			"received_amount": amount,
			"reference_no": _difference_reference(doc),
			"reference_date": nowdate(),
			"remarks": "Diferença da troca Tecponto {0}".format(doc.name),
		}
	)
	payment.insert(ignore_permissions=True)
	payment.submit()
	return payment.name


def _get_available_output_serial(doc):
	if not doc.get("device_out"):
		frappe.throw("Trade-in exige aparelho de saída.")

	serial = frappe.db.get_value(
		"Serial No",
		doc.get("device_out"),
		["name", "serial_no", "item_code", "warehouse", "status"],
		as_dict=True,
	)
	if not serial:
		frappe.throw("Aparelho de saída não encontrado.")

	warehouse = _commercial_warehouse()
	if serial.warehouse != warehouse:
		frappe.throw("Aparelho de saída sem estoque no Comercial.")

	return serial


def _device_out_item_code(doc) -> str:
	item_code = frappe.db.get_value("Serial No", doc.get("device_out"), "item_code")
	if not item_code:
		frappe.throw("Aparelho de saída não encontrado.")
	return item_code


def _valuation_rate(item_code: str, warehouse: str | None = None) -> float:
	if warehouse:
		valuation_rate = frappe.db.get_value(
			"Bin",
			{"item_code": item_code, "warehouse": warehouse},
			"valuation_rate",
		)
		if valuation_rate is not None:
			return flt(valuation_rate)

	return flt(frappe.get_cached_value("Item", item_code, "valuation_rate"))


def _commercial_warehouse() -> str:
	warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	if not warehouse:
		frappe.throw("Warehouse Comercial não configurado no Tecponto Settings.")
	return warehouse


def _user_is_manager() -> bool:
	if frappe.session.user == "Administrator":
		return True

	return bool(set(frappe.get_roles()) & MANAGER_ROLES)


def _difference_reference(doc) -> str:
	return "TRADEIN-DIFF-{0}".format(doc.name)


def _sale_reference(doc) -> str:
	return "Tecponto Trade-In Saida {0}".format(doc.name)
