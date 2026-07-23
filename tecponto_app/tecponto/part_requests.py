from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import flt, getdate, now_datetime, today

from tecponto_app.tecponto.permissions import is_restricted_technician
from tecponto_app.tecponto.workflow import _get_service_order_transitions


PART_REQUEST_DOCTYPE = "Tecponto Part Request"
PART_REQUEST_STATUS_REQUESTED = "Solicitada"
TECHNICAL_REQUESTER_ROLES = {"System Manager", "Tecponto Tecnico", "Tecponto Gestor", "Tecponto Diretor"}
PART_REQUEST_BUYER_ROLES = {"System Manager", "Tecponto Gestor", "Tecponto Diretor"}


def create_part_request(service_order: str, item: str = "", free_description: str = "", qty: float = 1, notes: str = "") -> dict[str, Any]:
	"""Register a technical need without issuing, buying or reserving stock yet."""
	_require_technical_requester()
	service_order = (service_order or "").strip()
	item = (item or "").strip()
	free_description = (free_description or "").strip()
	if not service_order:
		frappe.throw(_("Informe a ordem de serviço."), frappe.ValidationError)
	if not item and not free_description:
		frappe.throw(_("Selecione uma peça do catálogo ou descreva a peça necessária."), frappe.ValidationError)
	qty = flt(qty)
	if qty <= 0:
		frappe.throw(_("Informe uma quantidade maior que zero."), frappe.ValidationError)

	order = frappe.get_doc("Service Order", service_order)
	order.check_permission("read")
	if is_restricted_technician() and order.get("technician") != frappe.session.user:
		frappe.throw(_("Você só pode solicitar peça para as suas OS."), frappe.PermissionError)
	if item:
		_validate_repair_item(item)

	doc = frappe.get_doc(
		{
			"doctype": PART_REQUEST_DOCTYPE,
			"service_order": order.name,
			"item": item or None,
			"free_description": free_description or None,
			"qty": qty,
			"notes": (notes or "").strip() or None,
			"requested_by": frappe.session.user,
			"requested_at": now_datetime(),
			"status": PART_REQUEST_STATUS_REQUESTED,
		}
	)
	doc.insert(ignore_permissions=True)
	_move_order_to_waiting_part(order)
	return serialize_part_request(doc.as_dict())


def list_my_part_requests(limit: int = 100) -> dict[str, Any]:
	_require_technical_requester()
	limit = max(1, min(int(limit or 100), 200))
	filters: dict[str, Any] = {"requested_by": frappe.session.user}
	rows = frappe.get_list(
		PART_REQUEST_DOCTYPE,
		filters=filters,
		fields=["name", "service_order", "item", "free_description", "qty", "notes", "requested_by", "requested_at", "status", "modified"],
		order_by="requested_at desc, creation desc",
		limit_page_length=limit,
	)
	return {"items": [serialize_part_request(row) for row in rows], "count": len(rows)}


def list_repair_part_options(query: str = "", limit: int = 20) -> dict[str, Any]:
	"""Safe repair-catalog projection: never includes valuation/cost fields."""
	_require_technical_requester()
	query = (query or "").strip()
	limit = max(1, min(int(limit or 20), 50))
	groups = _repair_item_groups() or [""]
	filters: dict[str, Any] = {"disabled": 0, "is_stock_item": 1, "item_group": ["in", groups]}
	if query:
		filters["item_name"] = ["like", f"%{query}%"]
	rows = frappe.get_all("Item", filters=filters, fields=["name", "item_name", "item_group"], order_by="item_name asc", limit_page_length=limit)
	return {"items": [{"item_code": row.name, "item_name": row.item_name, "item_group": row.item_group} for row in rows], "count": len(rows)}


def list_purchase_part_requests(status: str = "open", query: str = "", limit: int = 100) -> dict[str, Any]:
	"""Buyer queue sorted by customer urgency. Cost is projected only to buyer roles."""
	_require_part_request_buyer()
	limit = max(1, min(int(limit or 100), 200))
	status = (status or "open").strip()
	query = (query or "").strip()
	conditions = ["1=1"]
	values: dict[str, Any] = {"limit": limit}
	if status == "open":
		conditions.append("request.status in ('Solicitada', 'Pedida')")
	elif status != "all":
		conditions.append("request.status = %(status)s")
		values["status"] = status
	if query:
		conditions.append("(request.name like %(query)s or request.service_order like %(query)s or request.item like %(query)s or request.free_description like %(query)s or request.notes like %(query)s)")
		values["query"] = f"%{query}%"
	rows = frappe.db.sql(
		f"""
		select
			request.name,
			request.service_order,
			request.item,
			request.free_description,
			request.qty,
			request.notes,
			request.requested_by,
			request.requested_at,
			request.status,
			request.supplier,
			request.expected_arrival,
			request.received_at,
			request.estimated_cost,
			request.cancellation_reason,
			request.modified,
			service_order.customer,
			service_order.technician,
			service_order.workflow_state,
			service_order.estimated_deadline,
			service_order.approval_deadline
		from `tabTecponto Part Request` request
		left join `tabService Order` service_order on service_order.name = request.service_order
		where {' and '.join(conditions)}
		order by
			case when service_order.estimated_deadline is null then 1 else 0 end,
			service_order.estimated_deadline asc,
			request.requested_at asc,
			request.creation asc
		limit %(limit)s
		""",
		values,
		as_dict=True,
	)
	items = [serialize_purchase_part_request(row) for row in rows]
	return {"items": items, "count": len(items), "statbar": _purchase_part_request_statbar()}


def mark_part_request_ordered(
	name: str,
	supplier: str,
	expected_arrival: str,
	estimated_cost: float | None = None,
	approved_request: str = "",
) -> dict[str, Any]:
	_require_part_request_buyer()
	doc = _get_part_request_for_buying(name, expected_status="Solicitada")
	supplier = (supplier or "").strip()
	expected_arrival = (expected_arrival or "").strip()
	if not supplier or not expected_arrival:
		frappe.throw(_("Informe fornecedor e previsão de chegada."), frappe.ValidationError)
	if not frappe.db.exists("Supplier", supplier):
		frappe.throw(_("Fornecedor não encontrado."), frappe.DoesNotExistError)
	cost = flt(estimated_cost)
	threshold = flt(frappe.db.get_single_value("Tecponto Settings", "purchase_approval_threshold") or 0)
	if threshold and cost > threshold and not _has_approved_purchase_context(approved_request):
		frappe.throw(_("Compra de peça acima do teto exige aprovação do Gestor."), frappe.PermissionError)
	doc.supplier = supplier
	doc.expected_arrival = expected_arrival
	doc.estimated_cost = cost
	doc.status = "Pedida"
	doc.save(ignore_permissions=True)
	return serialize_purchase_part_request(_reload_purchase_row(doc.name))


def mark_part_request_received(name: str) -> dict[str, Any]:
	_require_part_request_buyer()
	doc = _get_part_request_for_buying(name, expected_status="Pedida")
	doc.status = "Recebida"
	doc.received_at = now_datetime()
	doc.save(ignore_permissions=True)
	return serialize_purchase_part_request(_reload_purchase_row(doc.name))


def cancel_part_request(name: str, reason: str) -> dict[str, Any]:
	_require_part_request_buyer()
	doc = frappe.get_doc(PART_REQUEST_DOCTYPE, (name or "").strip())
	if doc.status in {"Recebida", "Cancelada"}:
		frappe.throw(_("Esta solicitação não pode mais ser cancelada."), frappe.ValidationError)
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Informe o motivo do cancelamento."), frappe.ValidationError)
	doc.status = "Cancelada"
	doc.cancellation_reason = reason
	doc.save(ignore_permissions=True)
	return serialize_purchase_part_request(_reload_purchase_row(doc.name))


def serialize_part_request(row: dict[str, Any]) -> dict[str, Any]:
	return {
		"name": row.get("name"),
		"service_order": row.get("service_order"),
		"item": row.get("item") or None,
		"free_description": row.get("free_description") or None,
		"qty": float(flt(row.get("qty"))),
		"notes": row.get("notes") or None,
		"requested_by": row.get("requested_by"),
		"requested_at": str(row.get("requested_at") or ""),
		"status": row.get("status") or PART_REQUEST_STATUS_REQUESTED,
		"modified": str(row.get("modified") or ""),
	}


def serialize_purchase_part_request(row: dict[str, Any]) -> dict[str, Any]:
	return {
		**serialize_part_request(row),
		"supplier": row.get("supplier") or None,
		"expected_arrival": str(row.get("expected_arrival") or ""),
		"received_at": str(row.get("received_at") or ""),
		"estimated_cost": float(flt(row.get("estimated_cost"))),
		"cancellation_reason": row.get("cancellation_reason") or None,
		"customer": row.get("customer") or None,
		"technician": row.get("technician") or None,
		"service_order_state": row.get("workflow_state") or None,
		"service_order_deadline": str(row.get("estimated_deadline") or row.get("approval_deadline") or ""),
		"is_late": bool(row.get("expected_arrival") and getdate(row.get("expected_arrival")) < getdate(today()) and row.get("status") == "Pedida"),
	}


def _require_technical_requester() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Faça login para solicitar peça."), frappe.PermissionError)
	if not set(frappe.get_roles(frappe.session.user)).intersection(TECHNICAL_REQUESTER_ROLES):
		frappe.throw(_("Somente a equipe técnica pode solicitar peça."), frappe.PermissionError)


def _require_part_request_buyer() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Faça login para acessar compras de peças."), frappe.PermissionError)
	if not set(frappe.get_roles(frappe.session.user)).intersection(PART_REQUEST_BUYER_ROLES):
		frappe.throw(_("Somente Gestor ou Diretor acompanha compras de peças."), frappe.PermissionError)


def _get_part_request_for_buying(name: str, expected_status: str):
	name = (name or "").strip()
	if not name:
		frappe.throw(_("Informe a solicitação de peça."), frappe.ValidationError)
	doc = frappe.get_doc(PART_REQUEST_DOCTYPE, name)
	if doc.status != expected_status:
		frappe.throw(_(f"Solicitação precisa estar em {expected_status}."), frappe.ValidationError)
	return doc


def _has_approved_purchase_context(approved_request: str) -> bool:
	return bool(approved_request and frappe.flags.approved_part_purchase_request == approved_request)


def _reload_purchase_row(name: str) -> dict[str, Any]:
	rows = frappe.db.sql(
		"""
		select
			request.name,
			request.service_order,
			request.item,
			request.free_description,
			request.qty,
			request.notes,
			request.requested_by,
			request.requested_at,
			request.status,
			request.supplier,
			request.expected_arrival,
			request.received_at,
			request.estimated_cost,
			request.cancellation_reason,
			request.modified,
			service_order.customer,
			service_order.technician,
			service_order.workflow_state,
			service_order.estimated_deadline,
			service_order.approval_deadline
		from `tabTecponto Part Request` request
		left join `tabService Order` service_order on service_order.name = request.service_order
		where request.name = %(name)s
		""",
		{"name": name},
		as_dict=True,
	)
	if not rows:
		frappe.throw(_("Solicitação de peça não encontrada."), frappe.DoesNotExistError)
	return rows[0]


def _purchase_part_request_statbar() -> list[dict[str, Any]]:
	month_start = getdate(today()).replace(day=1)
	late = frappe.db.count(PART_REQUEST_DOCTYPE, {"status": "Pedida", "expected_arrival": ["<", today()]})
	return [
		{"key": "requested", "label": "Solicitadas", "value": frappe.db.count(PART_REQUEST_DOCTYPE, {"status": "Solicitada"})},
		{"key": "ordered", "label": "Pedidas", "value": frappe.db.count(PART_REQUEST_DOCTYPE, {"status": "Pedida"})},
		{"key": "late", "label": "Atrasadas", "value": late},
		{"key": "received_month", "label": "Recebidas no mês", "value": frappe.db.count(PART_REQUEST_DOCTYPE, {"status": "Recebida", "received_at": [">=", month_start]})},
	]


def _move_order_to_waiting_part(order) -> None:
	if order.get("workflow_state") == "Aguardando peça":
		return
	for transition in _get_service_order_transitions():
		state, action, next_state = transition[:3]
		if state == order.get("workflow_state") and next_state == "Aguardando peça":
			apply_workflow(frappe.as_json({"doctype": order.doctype, "name": order.name}), action)
			return
	# The request remains valid even if a terminal/early workflow state cannot move.
	# It is a record of need, never a hidden blocker or a workflow bypass.


def _validate_repair_item(item: str) -> None:
	if not frappe.db.exists("Item", {"name": item, "disabled": 0, "is_stock_item": 1, "item_group": ["in", _repair_item_groups() or [""]]}):
		frappe.throw(_("Selecione uma peça ativa do catálogo de Reparo."), frappe.ValidationError)


def _repair_item_groups() -> list[str]:
	root = "Peças de Reparo"
	if not frappe.db.exists("Item Group", root):
		return []
	groups = [root]
	frontier = [root]
	while frontier:
		children = frappe.get_all("Item Group", filters={"parent_item_group": ["in", frontier]}, pluck="name")
		groups.extend(children)
		frontier = children
	return groups
