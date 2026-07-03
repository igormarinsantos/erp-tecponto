from __future__ import annotations

import frappe
from frappe.utils import flt, getdate, nowdate


STATE_CANCELADO = "Cancelado"
MANAGER_ROLES = {"Tecponto Gestor", "System Manager"}


def validate_repare_rules(doc, method=None) -> None:
	_validate_warranty(doc)
	_validate_sinal(doc)
	_validate_billed_cancellation(doc)


def _validate_warranty(doc) -> None:
	if doc.get("courtesy_warranty"):
		if not doc.get("courtesy_warranty_reason"):
			frappe.throw("Garantia-cortesia exige justificativa.")

		if _field_became_true(doc, "courtesy_warranty") and not _user_is_manager():
			frappe.throw("Somente Gestor pode marcar garantia-cortesia.")

	if not doc.get("is_warranty"):
		return

	if not doc.get("original_service_order"):
		frappe.throw("OS de garantia exige OS original.")

	if doc.get("original_service_order") == doc.name:
		frappe.throw("OS de garantia nao pode apontar para ela mesma.")

	warranty_expiry = frappe.db.get_value("Service Order", doc.original_service_order, "warranty_expiry")
	if doc.get("courtesy_warranty"):
		return

	if not warranty_expiry:
		frappe.throw("OS original nao possui garantia vigente registrada.")

	if getdate(warranty_expiry) < getdate(nowdate()):
		frappe.throw("Garantia vencida. Use garantia-cortesia com justificativa do Gestor.")


def _validate_sinal(doc) -> None:
	if doc.get("sinal_enabled") and flt(doc.get("sinal_value")) <= 0:
		frappe.throw("Sinal habilitado exige valor maior que zero.")


def _validate_billed_cancellation(doc) -> None:
	if doc.get("workflow_state") != STATE_CANCELADO or not doc.get("sales_invoice"):
		return

	if not _user_is_manager():
		frappe.throw("OS faturada so pode ser cancelada pelo Gestor.")


def _field_became_true(doc, fieldname: str) -> bool:
	if not doc.get(fieldname):
		return False

	if doc.is_new():
		return True

	previous = doc.get_doc_before_save()
	return not bool(previous and previous.get(fieldname))


def _user_is_manager() -> bool:
	if frappe.session.user == "Administrator":
		return True

	return bool(set(frappe.get_roles()) & MANAGER_ROLES)
