from __future__ import annotations

import frappe
from frappe.utils import flt, getdate, nowdate


STATE_CANCELADO = "Cancelado"
STATE_EM_DIAGNOSTICO = "Em diagnóstico"
STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO = "Diagnosticado — aguardando orçamento"
STATE_AGUARDANDO_APROVACAO = "Aguardando aprovação"
MANAGER_ROLES = {"Tecponto Gestor", "System Manager"}


def validate_repare_rules(doc, method=None) -> None:
	_validate_path(doc)
	_validate_warranty(doc)
	_validate_sinal(doc)
	_validate_billed_cancellation(doc)
	_validate_diagnosis_handoff(doc)
	_validate_budget_submission(doc)
	_validate_rapid_execution(doc)


def _validate_path(doc) -> None:
	path = doc.get("caminho") or "Completo"
	if path not in {"Rápido", "Completo"}:
		frappe.throw("Caminho da OS inválido.")
	if doc.is_new():
		doc.caminho = path
		return
	previous = doc.get_doc_before_save()
	if previous and previous.get("caminho") == "Rápido" and path == "Completo" and not doc.get("path_conversion_reason"):
		frappe.throw("Converta a OS rápida pelo fluxo auditado, informando o motivo.")
	if previous and previous.get("caminho") == "Completo" and path == "Rápido":
		frappe.throw("Uma OS completa não pode voltar ao caminho rápido.")


def _validate_rapid_execution(doc) -> None:
	if doc.get("workflow_state") != "Em reparo" or (doc.get("caminho") or "Completo") != "Rápido":
		return
	previous = doc.get_doc_before_save() if not doc.is_new() else None
	if not previous or previous.get("workflow_state") != "Entrada criada":
		return
	if not _has_identified_budget_line(doc):
		frappe.throw("Caminho rápido exige preço e ao menos um serviço ou peça antes da execução.")


def _validate_diagnosis_handoff(doc) -> None:
	if doc.get("workflow_state") != STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO:
		return
	previous = doc.get_doc_before_save() if not doc.is_new() else None
	if not previous or previous.get("workflow_state") != STATE_EM_DIAGNOSTICO:
		return
	if not (doc.get("diagnosis_completed_at") and doc.get("pricing_responsibility")):
		frappe.throw("Conclua o diagnóstico técnico e repasse a precificação antes de avançar.")


def _validate_budget_submission(doc) -> None:
	"""Keep an empty quote from entering the customer approval stage.

	The rule lives on the document because the same workflow transition is exposed
	by both the Tecponto frontend and Frappe Desk. Zero-priced lines remain valid
	for warranty work; the requirement is a real, identified quote line.
	"""
	if doc.get("workflow_state") != STATE_AGUARDANDO_APROVACAO:
		return

	previous = doc.get_doc_before_save() if not doc.is_new() else None
	if previous and previous.get("workflow_state") == STATE_AGUARDANDO_APROVACAO:
		return

	if not doc.get("diagnosis_date"):
		doc.diagnosis_date = nowdate()

	if not _has_identified_budget_line(doc):
		frappe.throw("Inclua ao menos um serviço ou peça identificada no orçamento antes de solicitar aprovação.")


def _has_identified_budget_line(doc) -> bool:
	return any((row.get("item_code") or "").strip() for row in (doc.get("services") or [])) or any(
		(row.get("item_code") or "").strip() for row in (doc.get("parts") or [])
	)


def _validate_warranty(doc) -> None:
	if doc.get("courtesy_warranty"):
		if not doc.get("courtesy_warranty_reason"):
			frappe.throw("Garantia-cortesia exige justificativa.")

		if _field_became_true(doc, "courtesy_warranty") and not _user_is_manager():
			frappe.throw("Somente Gestor pode marcar garantia-cortesia.")

	if not doc.get("is_warranty"):
		_validate_delivery_dates_are_immutable(doc)
		return

	if not doc.get("original_service_order"):
		frappe.throw("OS de garantia exige OS original.")

	if doc.get("original_service_order") == doc.name:
		frappe.throw("OS de garantia nao pode apontar para ela mesma.")

	original = frappe.db.get_value(
		"Service Order",
		doc.original_service_order,
		["customer", "customer_device", "workflow_state", "warranty_expiry", "reported_defect"],
		as_dict=True,
	)
	if not original:
		frappe.throw("OS original nao existe.")
	if original.customer != doc.get("customer") or original.customer_device != doc.get("customer_device"):
		frappe.throw("OS de garantia deve apontar para um reparo entregue do mesmo cliente e aparelho.")
	if original.workflow_state != "Entregue":
		frappe.throw("OS original precisa estar entregue para abrir retrabalho em garantia.")

	warranty_expiry = original.warranty_expiry
	if not warranty_expiry:
		frappe.throw("OS original nao possui garantia vigente registrada.")

	# A rework continues the original warranty; it never starts a new one.
	# Copy on every validation so Desk/API payloads cannot replace the date.
	doc.warranty_expiry = warranty_expiry
	_validate_delivery_dates_are_immutable(doc)

	if doc.get("courtesy_warranty"):
		return

	if _normalize_defect(original.reported_defect) != _normalize_defect(doc.get("reported_defect")):
		frappe.throw("Retrabalho em garantia exige o mesmo defeito registrado na OS original.")

	if getdate(warranty_expiry) < getdate(nowdate()):
		frappe.throw("Garantia vencida. Use garantia-cortesia com justificativa do Gestor.")


def _validate_delivery_dates_are_immutable(doc) -> None:
	"""Prevent a later edit from extending a warranty already delivered."""
	if doc.is_new():
		return

	previous = doc.get_doc_before_save()
	if not previous or previous.get("workflow_state") != "Entregue":
		return

	for fieldname, label in (("pickup_date", "data de entrega"), ("warranty_expiry", "validade da garantia")):
		if str(previous.get(fieldname) or "") != str(doc.get(fieldname) or ""):
			frappe.throw(f"A {label} de uma OS entregue e imutavel.")


def _normalize_defect(value: str | None) -> str:
	return " ".join((value or "").casefold().split())


def _validate_sinal(doc) -> None:
	if doc.get("sinal_enabled") and flt(doc.get("sinal_value")) <= 0:
		frappe.throw("Sinal habilitado exige valor maior que zero.")


def _validate_billed_cancellation(doc) -> None:
	if doc.get("workflow_state") != STATE_CANCELADO or not doc.get("sales_invoice"):
		return

	if not _user_is_manager():
		frappe.throw("OS faturada so pode ser cancelada pelo Gestor.")

	from tecponto_app.tecponto.service_order.billing import has_full_billed_service_order_reversal

	if not has_full_billed_service_order_reversal(doc.name):
		frappe.throw("Estorne integralmente a nota vinculada antes de cancelar a OS faturada.")


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
