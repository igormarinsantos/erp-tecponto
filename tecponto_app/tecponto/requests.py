from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime


REQUEST_TYPES = {
	"service_order_move": {"label": "Mover OS fora do papel", "doctype": "Service Order"},
	"service_order_discount": {"label": "Desconto acima do limite", "doctype": "Service Order"},
	"pos_price_floor": {"label": "Venda abaixo do custo", "doctype": "Sales Invoice"},
	"tradein_over_max": {"label": "Troca acima da tabela", "doctype": "Device Trade Evaluation"},
	"stock_transfer": {"label": "Transferência entre estoques", "doctype": "Stock Entry"},
	"billed_service_order_cancel": {"label": "Cancelar OS faturada", "doctype": "Service Order"},
}
MANAGER_ROLE = "Tecponto Gestor"
MANAGER_TYPES = {"service_order_discount", "pos_price_floor", "tradein_over_max", "stock_transfer", "billed_service_order_cancel"}
FRONTEND_ROLES = {"Tecponto Atendente", "Tecponto Tecnico", "Tecponto Gestor", "Tecponto Diretor", "System Manager"}


@frappe.whitelist()
def create_request(request_type: str, reference_name: str, reason: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_frontend_role()
	request_type = (request_type or "").strip()
	definition = REQUEST_TYPES.get(request_type)
	if not definition:
		frappe.throw(_("Tipo de solicitação inválido."), frappe.ValidationError)
	reference_name = (reference_name or "").strip()
	reason = (reason or "").strip()
	if not reference_name or not reason:
		frappe.throw(_("Solicitar aprovação exige documento e motivo."), frappe.ValidationError)
	if not frappe.db.exists(definition["doctype"], reference_name):
		frappe.throw(_("Documento de referência não encontrado."), frappe.DoesNotExistError)

	action_payload = _normalize_payload(payload)
	_validate_payload(request_type, reference_name, action_payload)
	approver_role = _approver_role(request_type, reference_name, action_payload)
	doc = frappe.get_doc({
		"doctype": "Tecponto Request",
		"request_type": definition["label"],
		"reference_doctype": definition["doctype"],
		"reference_name": reference_name,
		"reason": reason,
		"action_payload": frappe.as_json({"type": request_type, "data": action_payload}),
		"requested_by": frappe.session.user,
		"approver_role": approver_role,
		"status": "Pendente",
		"expires_on": add_to_date(now_datetime(), hours=72),
	})
	doc.insert(ignore_permissions=True)
	return _serialize(doc)


@frappe.whitelist()
def approve_request(name: str) -> dict[str, Any]:
	request = _get_pending_request(name)
	if request.requested_by == frappe.session.user:
		frappe.throw(_("O solicitante não pode aprovar a própria solicitação."), frappe.PermissionError)
	_require_role(request.approver_role)
	payload = frappe.parse_json(request.action_payload)
	result = _execute_as_approver(payload["type"], request.reference_name, payload["data"])
	request.status = "Aprovada"
	request.approved_by = frappe.session.user
	request.decision_date = now_datetime()
	request.execution_result = frappe.as_json(result)
	request.save(ignore_permissions=True)
	return _serialize(request)


@frappe.whitelist()
def reject_request(name: str) -> dict[str, Any]:
	request = _get_pending_request(name)
	if request.requested_by == frappe.session.user:
		frappe.throw(_("O solicitante não pode decidir a própria solicitação."), frappe.PermissionError)
	_require_role(request.approver_role)
	request.status = "Reprovada"
	request.approved_by = frappe.session.user
	request.decision_date = now_datetime()
	request.save(ignore_permissions=True)
	return _serialize(request)


def expire_requests() -> int:
	names = frappe.get_all("Tecponto Request", filters={"status": "Pendente", "expires_on": ["<", now_datetime()]}, pluck="name")
	for name in names:
		frappe.db.set_value("Tecponto Request", name, "status", "Expirada", update_modified=False)
	return len(names)


def _get_pending_request(name: str):
	request = frappe.get_doc("Tecponto Request", name)
	if request.status != "Pendente":
		frappe.throw(_("Esta solicitação não está pendente."), frappe.ValidationError)
	if get_datetime(request.expires_on) <= now_datetime():
		request.status = "Expirada"
		request.save(ignore_permissions=True)
		frappe.throw(_("Esta solicitação expirou."), frappe.ValidationError)
	return request


def _execute_as_approver(request_type: str, reference_name: str, data: dict[str, Any]) -> dict[str, Any]:
	with _preserve_user():
		# The approved user's real session executes the ordinary business path again.
		if request_type == "service_order_move":
			from tecponto_app.tecponto.frontend.api import move_service_order
			return move_service_order(reference_name, data["target_state"])
		if request_type == "service_order_discount":
			doc = frappe.get_doc("Service Order", reference_name)
			doc.discount = data["discount"]
			doc.save()
			return {"service_order": doc.name, "discount": doc.discount}
		if request_type == "pos_price_floor":
			from tecponto_app.tecponto.frontend.pos import pos_create_sale
			return pos_create_sale(data["sale_payload"])
		if request_type == "tradein_over_max":
			doc = frappe.get_doc("Device Trade Evaluation", reference_name)
			doc.approved_value = data["approved_value"]
			doc.save()
			return {"evaluation": doc.name, "approved_value": doc.approved_value}
		if request_type == "stock_transfer":
			doc = frappe.get_doc("Stock Entry", reference_name)
			doc.submit()
			return {"stock_entry": doc.name, "docstatus": doc.docstatus}
		if request_type == "billed_service_order_cancel":
			from tecponto_app.tecponto.frontend.api import move_service_order
			return move_service_order(reference_name, "Cancelado")
	frappe.throw(_("Executor de solicitação inválido."), frappe.ValidationError)


def _validate_payload(request_type: str, reference_name: str, data: dict[str, Any]) -> None:
	if request_type == "service_order_move" and not data.get("target_state"):
		frappe.throw(_("Informe o estado de destino."), frappe.ValidationError)
	if request_type == "service_order_discount" and "discount" not in data:
		frappe.throw(_("Informe o desconto solicitado."), frappe.ValidationError)
	if request_type == "pos_price_floor" and not isinstance(data.get("sale_payload"), dict):
		frappe.throw(_("Informe os dados da venda."), frappe.ValidationError)
	if request_type == "tradein_over_max" and "approved_value" not in data:
		frappe.throw(_("Informe o valor da troca."), frappe.ValidationError)
	if request_type == "billed_service_order_cancel" and not frappe.db.get_value("Service Order", reference_name, "sales_invoice"):
		frappe.throw(_("A OS não está faturada."), frappe.ValidationError)


def _approver_role(request_type: str, reference_name: str, data: dict[str, Any]) -> str:
	if request_type in MANAGER_TYPES:
		return MANAGER_ROLE
	doc = frappe.get_doc("Service Order", reference_name)
	# Resolve the transition role from workflow metadata without trusting the requester.
	transitions = frappe.get_all("Workflow Transition", filters={"parent": "Service Order", "state": doc.workflow_state, "next_state": data["target_state"]}, fields=["allowed"])
	if not transitions:
		frappe.throw(_("Transição de OS inválida."), frappe.ValidationError)
	return transitions[0].allowed


def _normalize_payload(payload: str | dict[str, Any] | None) -> dict[str, Any]:
	if payload is None:
		return {}
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw(_("Dados da solicitação inválidos."), frappe.ValidationError)
	return payload


def _require_frontend_role() -> None:
	if frappe.session.user == "Guest" or not (set(frappe.get_roles()) & FRONTEND_ROLES):
		raise frappe.PermissionError(_("Usuário sem papel Tecponto."))


def _require_role(role: str) -> None:
	roles = set(frappe.get_roles())
	if frappe.session.user != "Administrator" and role not in roles and "System Manager" not in roles:
		raise frappe.PermissionError(_("Seu papel não pode aprovar esta solicitação."))


@contextmanager
def _preserve_user():
	# Kept for symmetry with future async executors; approval never impersonates the requester.
	previous = frappe.session.user
	try:
		yield
	finally:
		frappe.set_user(previous)


def _serialize(doc) -> dict[str, Any]:
	return {"name": doc.name, "status": doc.status, "requested_by": doc.requested_by, "approver_role": doc.approver_role, "expires_on": str(doc.expires_on)}
