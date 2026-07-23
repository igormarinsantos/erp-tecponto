from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import flt, now_datetime

from tecponto_app.tecponto.permissions import is_restricted_technician
from tecponto_app.tecponto.workflow import _get_service_order_transitions


PART_REQUEST_DOCTYPE = "Tecponto Part Request"
PART_REQUEST_STATUS_REQUESTED = "Solicitada"
TECHNICAL_REQUESTER_ROLES = {"System Manager", "Tecponto Tecnico", "Tecponto Gestor", "Tecponto Diretor"}


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


def _require_technical_requester() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Faça login para solicitar peça."), frappe.PermissionError)
	if not set(frappe.get_roles(frappe.session.user)).intersection(TECHNICAL_REQUESTER_ROLES):
		frappe.throw(_("Somente a equipe técnica pode solicitar peça."), frappe.PermissionError)


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
