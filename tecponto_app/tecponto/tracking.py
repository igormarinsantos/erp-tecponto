"""Public, read-only projection for Service Order tracking links."""

from __future__ import annotations

import hashlib
import secrets
from typing import Any
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_url, now_datetime


TRACKING_DOCTYPE = "Service Order Tracking"
ACTIVE_STATUS = "Ativo"
INVALID_LINK_MESSAGE = "Este link de rastreio não está disponível. Peça um novo link à Tecponto."
TRACKING_STAGES = (
	"Entrada criada",
	"Em diagnóstico",
	"Aguardando aprovação",
	"Aguardando peça",
	"Em reparo",
	"Teste final",
	"Pronto para retirada",
	"Entregue",
)


def issue_tracking_link(service_order: str) -> dict[str, str]:
	"""Issue a new opaque tracking link after checking the operator's OS access."""
	order = frappe.get_doc("Service Order", service_order)
	order.check_permission("read")

	frappe.db.set_value(
		TRACKING_DOCTYPE,
		{"service_order": order.name, "status": ACTIVE_STATUS},
		"status",
		"Revogado",
		update_modified=False,
	)
	token = secrets.token_urlsafe(32)
	doc = frappe.get_doc(
		{
			"doctype": TRACKING_DOCTYPE,
			"service_order": order.name,
			"status": ACTIVE_STATUS,
			"token_hash": _token_hash(token),
			"expires_on": add_days(now_datetime(), 90),
			"issued_by": frappe.session.user,
		}
	)
	doc.insert(ignore_permissions=True)
	return {
		"tracking": doc.name,
		"link": f"{get_url()}/tecponto/rastreio/{token}",
		"expires_on": str(doc.expires_on),
	}


@frappe.whitelist(allow_guest=True)
def get_public_tracking(token: str) -> dict[str, Any]:
	"""Return only customer-safe tracking information for a valid opaque token."""
	doc = _get_valid_tracking(token)
	if not doc:
		return {"valid": False, "message": INVALID_LINK_MESSAGE}

	order = frappe.get_doc("Service Order", doc.service_order)
	device = _get_device(order.customer_device)
	awaiting_approval = order.get("workflow_state") == "Aguardando aprovação"
	return {
		"valid": True,
		"tracking": {
			"expires_on": str(doc.expires_on),
		},
		"service_order": {
			"number": order.name,
			"workflow_state": order.get("workflow_state") or "Entrada criada",
			"device": _device_label(device),
			"imei_suffix": _imei_suffix(device.get("imei_serial")),
			"reported_defect": order.get("reported_defect") or "Não informado",
			"approval_deadline": str(order.get("approval_deadline") or "") if awaiting_approval else "",
			"warranty_expiry": str(order.get("warranty_expiry") or "") if order.get("workflow_state") == "Entregue" else "",
		},
		"budget": _public_budget(order) if awaiting_approval else None,
		"approval": _public_approval(order),
		"timeline": _build_timeline(order),
		"whatsapp_url": "https://wa.me/?text=" + quote(f"Olá, preciso de ajuda com a OS {order.name}."),
	}


@frappe.whitelist(allow_guest=True)
def decide_public_tracking_budget(token: str, decision: str, notes: str = "") -> dict[str, Any]:
	"""Re-execute the existing budget decision flow for the holder of a valid tracking link."""
	tracking = _get_valid_tracking(token)
	if not tracking:
		frappe.throw(_(INVALID_LINK_MESSAGE), frappe.PermissionError)

	decision = (decision or "").strip()
	notes = (notes or "").strip()
	if decision not in {"approve", "reject"}:
		frappe.throw(_("Informe se o orçamento foi aprovado ou reprovado."), frappe.ValidationError)
	if decision == "reject" and not notes:
		frappe.throw(_("Informe o motivo da reprovação."), frappe.ValidationError)

	order = frappe.get_doc("Service Order", tracking.service_order)
	if order.get("workflow_state") != "Aguardando aprovação":
		frappe.throw(_("Este orçamento não está mais disponível para decisão."), frappe.ValidationError)
	if order.get("approval_deadline") and order.approval_deadline <= now_datetime():
		frappe.throw(_("O prazo de aprovação deste orçamento expirou."), frappe.ValidationError)

	actor = tracking.issued_by
	allowed_roles = {"System Manager", "Tecponto Atendente", "Tecponto Gestor"}
	if not actor or not set(frappe.get_roles(actor)).intersection(allowed_roles):
		frappe.throw(_("Este link não pode mais registrar uma decisão. Peça um novo link à Tecponto."), frappe.PermissionError)

	# The token authorizes the customer decision; the existing motor still runs under
	# the accountable operator, with its normal role checks and workflow validation.
	previous_user = frappe.session.user
	try:
		frappe.set_user(actor)
		from tecponto_app.tecponto.frontend.api import decide_service_order_budget

		decide_service_order_budget(
			order.name,
			{"decision": decision, "channel": "Link", "notes": notes},
		)
	finally:
		frappe.set_user(previous_user)

	return {
		"completed": True,
		"decision": decision,
		"tracking": get_public_tracking(token),
	}


def _get_valid_tracking(token: str):
	token = (token or "").strip()
	if len(token) < 24:
		return None
	name = frappe.db.get_value(TRACKING_DOCTYPE, {"token_hash": _token_hash(token)}, "name")
	if not name:
		return None
	doc = frappe.get_doc(TRACKING_DOCTYPE, name)
	if doc.status != ACTIVE_STATUS:
		return None
	if doc.expires_on <= now_datetime():
		doc.db_set("status", "Expirado", update_modified=False)
		return None
	return doc


def _get_device(device_name: str | None) -> dict[str, Any]:
	if not device_name:
		return {}
	return frappe.db.get_value(
		"Customer Device",
		device_name,
		["brand", "model", "color", "imei_serial"],
		as_dict=True,
	) or {}


def _device_label(device: dict[str, Any]) -> str:
	return " ".join(str(value) for value in (device.get("brand"), device.get("model"), device.get("color")) if value) or "Aparelho não informado"


def _imei_suffix(imei: str | None) -> str:
	value = (imei or "").strip()
	return f"•••• {value[-4:]}" if value else "Não informado"


def _public_budget(order: Any) -> dict[str, Any]:
	def line(row: Any, fallback: str = "") -> dict[str, Any]:
		quantity = flt(row.get("qty") or 0)
		unit_price = flt(row.get("rate") or 0)
		return {
			"description": row.get("description") or frappe.db.get_value("Item", row.get("item_code"), "item_name") or fallback or "Item não informado",
			"quantity": quantity,
			"unit_price": unit_price,
			"line_total": quantity * unit_price,
		}

	return {
		"services": [line(row, "Serviço") for row in order.get("services") or []],
		"parts": [line(row, "Peça") for row in order.get("parts") or []],
		"total": flt(order.get("grand_total") or 0),
		"version": int(order.get("budget_version") or 1),
	}


def _public_approval(order: Any) -> dict[str, str] | None:
	status = order.get("approval_status")
	if not status or status == "Pendente":
		return None
	return {"status": status, "date": str(order.get("approval_date") or "")}


def _build_timeline(order: Any) -> list[dict[str, Any]]:
	current_state = order.get("workflow_state") or "Entrada criada"
	try:
		current_index = TRACKING_STAGES.index(current_state)
	except ValueError:
		current_index = -1

	timeline = []
	for index, stage in enumerate(TRACKING_STAGES):
		is_current = stage == current_state
		is_completed = current_index >= index and not is_current
		timeline.append(
			{
				"stage": stage,
				"state": "current" if is_current else "completed" if is_completed else "future",
				"at": str(order.get("entry_date") or order.get("creation") or "") if index == 0 else str(order.get("modified") or "") if is_current else "",
			}
		)
	if current_index < 0:
		timeline.append({"stage": current_state, "state": "current", "at": str(order.get("modified") or "")})
	return timeline


def _token_hash(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()
