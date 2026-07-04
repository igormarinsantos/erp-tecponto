from __future__ import annotations

import re
import unicodedata

import frappe
from erpnext.accounts.party import get_party_account
from frappe.utils import flt, nowdate


STATE_COMPRADO = "Comprado"
ITEM_GROUP_USED_DEVICES = "Aparelhos Usados"
STOCK_ENTRY_TYPE_MATERIAL_RECEIPT = "Material Receipt"
BUYBACK_REFERENCE_PREFIX = "BUYBACK"


def concretizar_compra(doc, method=None) -> None:
	if doc.get("workflow_state") != STATE_COMPRADO or doc.get("created_item"):
		return

	registrar_entrada_usado(doc, pay_customer=True)


def ensure_serial_batch_for_used_devices() -> None:
	if frappe.get_meta("Stock Settings").has_field("enable_serial_and_batch_no_for_item"):
		frappe.db.set_single_value("Stock Settings", "enable_serial_and_batch_no_for_item", 1)


def registrar_entrada_usado(doc, pay_customer: bool = True) -> str | None:
	if doc.get("created_item"):
		return doc.get("created_item")

	if _is_discard_destination(doc):
		return None

	_validate_buyback_doc(doc)

	item_code = _criar_item_usado(doc)
	warehouse = _warehouse_destino(doc)
	_criar_entrada_estoque(doc, item_code, warehouse)

	if pay_customer:
		_pagar_cliente(doc)

	doc.db_set("created_item", item_code, update_modified=False)
	doc.created_item = item_code
	return item_code


def _validate_buyback_doc(doc) -> None:
	if not doc.get("imei"):
		frappe.throw("Compra de aparelho usado exige IMEI / Serial.")

	if flt(doc.get("approved_value")) <= 0:
		frappe.throw("Compra de aparelho usado exige valor aprovado maior que zero.")

	if not doc.get("destination"):
		frappe.throw("Compra de aparelho usado exige destino.")

	if not frappe.db.exists("Item Group", ITEM_GROUP_USED_DEVICES):
		frappe.throw("Item Group Aparelhos Usados nao encontrado.")


def _criar_item_usado(doc) -> str:
	item_code = _item_code(doc)
	if frappe.db.exists("Item", item_code):
		return item_code

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": _item_name(doc),
			"item_group": ITEM_GROUP_USED_DEVICES,
			"stock_uom": _stock_uom(),
			"is_stock_item": 1,
			"is_sales_item": 1,
			"is_purchase_item": 1,
			"has_serial_no": 1,
			"valuation_method": frappe.db.get_single_value("Tecponto Settings", "valuation_method")
			or "Moving Average",
		}
	)
	item.insert(ignore_permissions=True)
	return item.name


def _criar_entrada_estoque(doc, item_code: str, warehouse: str) -> str:
	ensure_serial_batch_for_used_devices()

	existing = frappe.db.get_value(
		"Stock Entry",
		{
			"stock_entry_type": STOCK_ENTRY_TYPE_MATERIAL_RECEIPT,
			"docstatus": 1,
			"remarks": _stock_reference(doc),
		},
		"name",
	)
	if existing:
		return existing

	stock_entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": STOCK_ENTRY_TYPE_MATERIAL_RECEIPT,
			"purpose": STOCK_ENTRY_TYPE_MATERIAL_RECEIPT,
			"company": _default_company(),
			"posting_date": nowdate(),
			"remarks": _stock_reference(doc),
			"items": [
				{
					"item_code": item_code,
					"qty": 1,
					"t_warehouse": warehouse,
					"basic_rate": flt(doc.get("approved_value")),
					"serial_no": doc.get("imei"),
				}
			],
		}
	)
	stock_entry.insert(ignore_permissions=True)
	stock_entry.submit()
	return stock_entry.name


def _pagar_cliente(doc) -> str:
	existing = frappe.db.get_value(
		"Payment Entry",
		{
			"docstatus": 1,
			"reference_no": _payment_reference(doc),
		},
		"name",
	)
	if existing:
		return existing

	company = _default_company()
	amount = flt(doc.get("approved_value"))
	payment = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Pay",
			"company": company,
			"posting_date": nowdate(),
			"mode_of_payment": _mode_of_payment(company),
			"party_type": "Customer",
			"party": doc.get("customer"),
			"paid_from": _cash_or_bank_account(company),
			"paid_to": get_party_account("Customer", doc.get("customer"), company),
			"paid_amount": amount,
			"received_amount": amount,
			"reference_no": _payment_reference(doc),
			"reference_date": nowdate(),
			"remarks": "Buyback Tecponto {0}".format(doc.name),
		}
	)
	payment.insert(ignore_permissions=True)
	payment.submit()
	return payment.name


def _warehouse_destino(doc) -> str:
	destination = _normalize(doc.get("destination"))
	if destination == "venda":
		warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	elif destination == "pecas":
		warehouse = frappe.db.get_single_value("Tecponto Settings", "used_devices_warehouse")
	else:
		frappe.throw("Destino de compra de usado invalido.")

	if not warehouse:
		frappe.throw("Warehouse de destino nao configurado no Tecponto Settings.")

	return warehouse


def _is_discard_destination(doc) -> bool:
	return _normalize(doc.get("destination")) == "descarte"


def _item_code(doc) -> str:
	return "USADO-{0}".format(_clean_code(doc.get("imei")))


def _item_name(doc) -> str:
	parts = [doc.get("device_type"), doc.get("model"), doc.get("capacity"), doc.get("imei")]
	return " ".join(part for part in parts if part) or _item_code(doc)


def _stock_uom() -> str:
	return frappe.db.get_single_value("Stock Settings", "stock_uom") or "Nos"


def _default_company() -> str:
	company = frappe.defaults.get_user_default("Company")
	company = company or frappe.db.get_single_value("Global Defaults", "default_company")
	company = company or frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw("Empresa padrao nao encontrada.")
	return company


def _mode_of_payment(company: str) -> str:
	for mode in ("Pix", "Dinheiro", "Cash"):
		if frappe.db.exists("Mode of Payment", mode):
			return mode

	mode = frappe.db.get_value("Mode of Payment", {"enabled": 1}, "name")
	if not mode:
		frappe.throw("Forma de pagamento para buyback nao encontrada.")

	return mode


def _cash_or_bank_account(company: str) -> str:
	account = frappe.db.get_value(
		"Mode of Payment Account",
		{"parent": ["in", ["Pix", "Dinheiro", "Cash"]], "company": company},
		"default_account",
	)
	account = account or frappe.db.get_value(
		"Account",
		{"company": company, "is_group": 0, "account_type": ["in", ["Cash", "Bank"]]},
		"name",
	)
	if not account:
		frappe.throw("Conta caixa/banco para pagamento de buyback nao encontrada.")

	return account


def _payment_reference(doc) -> str:
	return "{0}-{1}".format(BUYBACK_REFERENCE_PREFIX, doc.name)


def _stock_reference(doc) -> str:
	return "Tecponto Buyback {0}".format(doc.name)


def _clean_code(value: str | None) -> str:
	cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value or "").strip("-").upper()
	return cleaned or frappe.generate_hash(length=8).upper()


def _normalize(value: str | None) -> str:
	normalized = unicodedata.normalize("NFKD", value or "")
	return "".join(char for char in normalized if not unicodedata.combining(char)).strip().lower()
