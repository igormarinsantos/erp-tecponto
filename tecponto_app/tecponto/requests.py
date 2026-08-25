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
	"pos_discount": {"label": "Desconto acima do limite", "doctype": "Customer"},
	"pos_price_floor": {"label": "Venda abaixo do custo", "doctype": "Customer"},
	"tradein_over_max": {"label": "Troca acima da tabela", "doctype": "Device Trade Evaluation"},
	"stock_transfer": {"label": "Transferência entre estoques", "doctype": "Stock Entry"},
	"billed_service_order_cancel": {"label": "Cancelar OS faturada", "doctype": "Service Order"},
	"courtesy_warranty": {"label": "Garantia-cortesia", "doctype": "Service Order"},
	"acceptance_selfie_exception": {"label": "Dispensar selfie do aceite", "doctype": "OS Acceptance"},
	"part_purchase_above_threshold": {"label": "Compra de peça acima do teto", "doctype": "Tecponto Part Request"},
}
MANAGER_ROLE = "Tecponto Gestor"
MANAGER_TYPES = {"service_order_discount", "pos_discount", "pos_price_floor", "tradein_over_max", "stock_transfer", "billed_service_order_cancel", "courtesy_warranty", "acceptance_selfie_exception", "part_purchase_above_threshold"}
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
	# A person with accumulated roles exercises the authority they already hold.
	# This does not turn into self-approval: no request exists to decide, and the
	# action is still executed through the ordinary server-side business path.
	if _has_approver_authority(approver_role):
		result = _execute_as_approver(request_type, reference_name, action_payload, reason)
		from tecponto_app.tecponto.user_access import audit_accumulated_role_action
		audit_accumulated_role_action(
			role=approver_role,
			action_type=request_type,
			reference_doctype=definition["doctype"],
			reference_name=reference_name,
			result=result,
		)
		return {
			"name": "",
			"status": "Executada",
			"request_type": definition["label"],
			"reason": reason,
			"reference_name": reference_name,
			"requested_by": frappe.session.user,
			"approver_role": approver_role,
			"expires_on": "",
			"executed_directly": True,
			"execution_result": result,
		}
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
	# Keep the request engine reliable for its own API path; the doc event covers other writers.
	from tecponto_app.tecponto.notify import on_request_created
	on_request_created(doc)
	return _serialize(doc)


@frappe.whitelist()
def approve_request(name: str) -> dict[str, Any]:
	request = _get_pending_request(name)
	if request.requested_by == frappe.session.user:
		frappe.throw(_("O solicitante não pode aprovar a própria solicitação."), frappe.PermissionError)
	_require_role(request.approver_role)
	payload = frappe.parse_json(request.action_payload)
	result = _execute_as_approver(payload["type"], request.reference_name, payload["data"], request.reason, request.name)
	request.status = "Aprovada"
	request.approved_by = frappe.session.user
	request.decision_date = now_datetime()
	request.execution_result = frappe.as_json(result)
	request.flags.notify_status_transition = True
	request.save(ignore_permissions=True)
	from tecponto_app.tecponto.notify import on_request_updated
	on_request_updated(request)
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
	request.flags.notify_status_transition = True
	request.save(ignore_permissions=True)
	from tecponto_app.tecponto.notify import on_request_updated
	on_request_updated(request)
	return _serialize(request)


def expire_requests() -> int:
	names = frappe.get_all("Tecponto Request", filters={"status": "Pendente", "expires_on": ["<", now_datetime()]}, pluck="name")
	for name in names:
		frappe.db.set_value("Tecponto Request", name, "status", "Expirada", update_modified=False)
	return len(names)


@frappe.whitelist()
def list_my_requests() -> list[dict[str, Any]]:
	_require_frontend_role()
	return [_serialize(row) for row in frappe.get_all("Tecponto Request", filters={"requested_by": frappe.session.user}, fields=["name", "status", "requested_by", "approver_role", "expires_on", "request_type", "reason", "reference_name"], order_by="creation desc", limit_page_length=50)]


@frappe.whitelist()
def list_pending_approvals() -> list[dict[str, Any]]:
	_require_frontend_role()
	roles = set(frappe.get_roles())
	filters = {"status": "Pendente"}
	rows = frappe.get_all("Tecponto Request", filters=filters, fields=["name", "status", "requested_by", "approver_role", "expires_on", "request_type", "reason", "reference_name"], order_by="creation desc", limit_page_length=50)
	return [_serialize(row) for row in rows if row.approver_role in roles or "System Manager" in roles or frappe.session.user == "Administrator"]


def _get_pending_request(name: str):
	request = frappe.get_doc("Tecponto Request", name)
	if request.status != "Pendente":
		frappe.throw(_("Esta solicitação não está pendente."), frappe.ValidationError)
	if get_datetime(request.expires_on) <= now_datetime():
		request.status = "Expirada"
		request.save(ignore_permissions=True)
		frappe.throw(_("Esta solicitação expirou."), frappe.ValidationError)
	return request


def _execute_as_approver(
	request_type: str,
	reference_name: str,
	data: dict[str, Any],
	reason: str = "",
	request_name: str = "",
) -> dict[str, Any]:
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
		if request_type in {"pos_discount", "pos_price_floor"}:
			from tecponto_app.tecponto.frontend.pos import pos_create_sale
			return pos_create_sale(data["sale_payload"])
		if request_type == "tradein_over_max":
			doc = frappe.get_doc("Device Trade Evaluation", reference_name)
			doc.approved_value = data["approved_value"]
			doc.save()
			return {"evaluation": doc.name, "approved_value": doc.approved_value}
		if request_type == "stock_transfer":
			from tecponto_app.tecponto.frontend.api import submit_approved_stock_transfer
			result = submit_approved_stock_transfer(reference_name)
			return {"stock_entry": result["item"]["name"], "docstatus": result["item"]["docstatus"]}
		if request_type == "billed_service_order_cancel":
			from tecponto_app.tecponto.service_order.billing import reverse_billed_service_order_invoice
			from tecponto_app.tecponto.frontend.api import move_service_order
			frappe.db.savepoint("billed_service_order_cancel")
			try:
				reversal = reverse_billed_service_order_invoice(reference_name)
				cancellation = move_service_order(reference_name, "Cancelado")
			except Exception:
				frappe.db.rollback(save_point="billed_service_order_cancel")
				raise
			return {**cancellation, **reversal}
		if request_type == "courtesy_warranty":
			doc = frappe.get_doc("Service Order", reference_name)
			doc.is_warranty = 1
			doc.original_service_order = data["original_service_order"]
			doc.courtesy_warranty = 1
			doc.courtesy_warranty_reason = reason
			doc.save()
			return {
				"service_order": doc.name,
				"original_service_order": doc.original_service_order,
				"courtesy_warranty": True,
			}
		if request_type == "acceptance_selfie_exception":
			doc = frappe.get_doc("OS Acceptance", reference_name)
			if doc.status != "Pendente":
				frappe.throw(_("Só é possível dispensar a selfie de um aceite pendente."), frappe.ValidationError)
			if doc.selfie_file:
				frappe.throw(_("Este aceite já possui uma selfie registrada."), frappe.ValidationError)
			doc.check_permission("write")
			doc.selfie_exception = 1
			doc.selfie_exception_reason = reason
			doc.selfie_exception_by = frappe.session.user
			doc.selfie_exception_on = now_datetime()
			doc.selfie_exception_request = request_name
			doc.save()
			return {"acceptance": doc.name, "selfie_exception": True}
		if request_type == "part_purchase_above_threshold":
			from tecponto_app.tecponto.part_requests import mark_part_request_ordered
			frappe.flags.approved_part_purchase_request = request_name
			try:
				return mark_part_request_ordered(
					reference_name,
					supplier=data["supplier"],
					expected_arrival=data["expected_arrival"],
					estimated_cost=data.get("estimated_cost"),
					approved_request=request_name,
				)
			finally:
				frappe.flags.approved_part_purchase_request = None
	frappe.throw(_("Executor de solicitação inválido."), frappe.ValidationError)


def _validate_payload(request_type: str, reference_name: str, data: dict[str, Any]) -> None:
	if request_type == "service_order_move" and not data.get("target_state"):
		frappe.throw(_("Informe o estado de destino."), frappe.ValidationError)
	if request_type == "service_order_discount" and "discount" not in data:
		frappe.throw(_("Informe o desconto solicitado."), frappe.ValidationError)
	if request_type in {"pos_discount", "pos_price_floor"} and not isinstance(data.get("sale_payload"), dict):
		frappe.throw(_("Informe os dados da venda."), frappe.ValidationError)
	if request_type == "tradein_over_max" and "approved_value" not in data:
		frappe.throw(_("Informe o valor da troca."), frappe.ValidationError)
	if request_type == "billed_service_order_cancel" and not frappe.db.get_value("Service Order", reference_name, "sales_invoice"):
		frappe.throw(_("A OS não está faturada."), frappe.ValidationError)
	if request_type == "courtesy_warranty":
		original_name = (data.get("original_service_order") or "").strip()
		if not original_name:
			frappe.throw(_("Informe a OS original para a garantia-cortesia."), frappe.ValidationError)
		order = frappe.get_doc("Service Order", reference_name)
		original = frappe.get_doc("Service Order", original_name)
		if order.get("sales_invoice"):
			frappe.throw(_("OS faturada nao pode ser convertida em garantia-cortesia."), frappe.ValidationError)
		if order.get("is_warranty"):
			frappe.throw(_("Esta OS ja e um retrabalho em garantia."), frappe.ValidationError)
		if original.get("workflow_state") != "Entregue":
			frappe.throw(_("A OS original precisa estar entregue."), frappe.ValidationError)
		if original.get("customer") != order.get("customer") or original.get("customer_device") != order.get("customer_device"):
			frappe.throw(_("A OS original precisa ser do mesmo cliente e aparelho."), frappe.ValidationError)
	if request_type == "acceptance_selfie_exception":
		doc = frappe.get_doc("OS Acceptance", reference_name)
		if doc.status != "Pendente":
			frappe.throw(_("Só é possível solicitar exceção para um aceite pendente."), frappe.ValidationError)
		if doc.selfie_file:
			frappe.throw(_("Este aceite já possui uma selfie registrada."), frappe.ValidationError)
	if request_type == "part_purchase_above_threshold":
		if not data.get("supplier") or not data.get("expected_arrival"):
			frappe.throw(_("Informe fornecedor e previsão de chegada."), frappe.ValidationError)
		if not frappe.db.exists("Tecponto Part Request", {"name": reference_name, "status": "Solicitada"}):
			frappe.throw(_("A solicitação de peça precisa estar em Solicitada para aprovação."), frappe.ValidationError)


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


def _has_approver_authority(role: str) -> bool:
	roles = set(frappe.get_roles())
	return frappe.session.user == "Administrator" or role in roles or "System Manager" in roles


@contextmanager
def _preserve_user():
	# Kept for symmetry with future async executors; approval never impersonates the requester.
	previous = frappe.session.user
	try:
		yield
	finally:
		# Test and shell calls may not carry a request session. This context never
		# changes user, so there is nothing to restore when no prior user exists.
		if previous:
			frappe.set_user(previous)


def _serialize(doc) -> dict[str, Any]:
	return {
		"name": doc.name,
		"status": doc.status,
		"request_type": doc.get("request_type"),
		"reason": doc.get("reason"),
		"reference_name": doc.get("reference_name"),
		"requested_by": doc.requested_by,
		"approver_role": doc.approver_role,
		"expires_on": str(doc.expires_on),
	}
