from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime


FRONTEND_ROLES = {"Tecponto Atendente", "Tecponto Tecnico", "Tecponto Gestor", "Tecponto Diretor", "System Manager"}
READY_FOR_PICKUP_REMINDER_DAYS = 3


def enqueue(user: str, template_key: str, context: dict[str, Any]) -> bool:
	"""Queue delivery and deliberately keep notification failures off the business path."""
	if not user or user == "Guest":
		return False
	try:
		# Tests execute delivery inline so fixture transactions cannot race the worker.
		# Production always stays asynchronous through frappe.enqueue below.
		if frappe.flags.in_test:
			send(user, template_key, context)
			return True
		frappe.enqueue(
			"tecponto_app.tecponto.notify.send",
			queue="short",
			user=user,
			template_key=template_key,
			context=context,
		)
		return True
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Tecponto notification enqueue failed")
		return False


def send(user: str, template_key: str, context: dict[str, Any]) -> str | None:
	"""Channel-agnostic delivery point. Today it persists in-app; channels plug in here later."""
	if _already_sent(user, template_key, context):
		return None
	template = _render(template_key, context)
	doc = frappe.get_doc(
		{
			"doctype": "Tecponto Notification",
			"recipient": user,
			"template_key": template_key,
			"notification_type": template["type"],
			"title": template["title"],
			"body": template["body"],
			"link": template["link"],
			"reference_doctype": context.get("reference_doctype"),
			"reference_name": context.get("reference_name"),
			"is_read": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def on_request_created(doc, method=None) -> None:
	for user in _users_with_role(doc.approver_role):
		enqueue(user, "request_created", {"request": doc.name, "request_type": doc.request_type, "reference_doctype": "Tecponto Request", "reference_name": doc.name})


def on_request_updated(doc, method=None) -> None:
	if not (doc.has_value_changed("status") or doc.flags.get("notify_status_transition")) or doc.status not in {"Aprovada", "Reprovada"}:
		return
	enqueue(doc.requested_by, "request_decided", {"request": doc.name, "status": doc.status, "request_type": doc.request_type, "reference_doctype": "Tecponto Request", "reference_name": doc.name})


def on_service_order_updated(doc, method=None) -> None:
	if not doc.has_value_changed("workflow_state"):
		return
	for user in {doc.get("attendant"), doc.get("technician")} - {None, ""}:
		enqueue(user, "service_order_state_changed", {"service_order": doc.name, "state": doc.workflow_state, "reference_doctype": "Service Order", "reference_name": doc.name})


def notify_due_service_orders() -> dict[str, int]:
	"""Run hourly: quote deadline inside 12 hours and pickup reminder after three days."""
	now = now_datetime()
	quote_count = 0
	pickup_count = 0
	for row in frappe.get_all(
		"Service Order",
		filters={"workflow_state": "Aguardando aprovação", "approval_deadline": ["between", [now, add_to_date(now, hours=12)]]},
		fields=["name", "attendant", "approval_deadline"],
	):
		if row.attendant and enqueue(row.attendant, "quote_expiring", {"service_order": row.name, "deadline": str(row.approval_deadline), "reference_doctype": "Service Order", "reference_name": row.name}):
			quote_count += 1
	cutoff = add_to_date(now, days=-READY_FOR_PICKUP_REMINDER_DAYS)
	for row in frappe.get_all(
		"Service Order",
		filters={"workflow_state": "Pronto para retirada", "modified": ["<=", cutoff]},
		fields=["name", "attendant"],
	):
		if row.attendant and enqueue(row.attendant, "ready_for_pickup", {"service_order": row.name, "days": READY_FOR_PICKUP_REMINDER_DAYS, "reference_doctype": "Service Order", "reference_name": row.name}):
			pickup_count += 1
	return {"quote_expiring": quote_count, "ready_for_pickup": pickup_count}


@frappe.whitelist()
def list_notifications(limit: int = 20) -> dict[str, Any]:
	_require_frontend_role()
	rows = frappe.get_all(
		"Tecponto Notification",
		filters={"recipient": frappe.session.user},
		fields=["name", "notification_type", "title", "body", "link", "reference_doctype", "reference_name", "is_read", "read_at", "creation"],
		order_by="creation desc",
		limit_page_length=max(1, min(int(limit or 20), 50)),
	)
	return {"items": [_serialize(row) for row in rows], "unread_count": frappe.db.count("Tecponto Notification", {"recipient": frappe.session.user, "is_read": 0})}


@frappe.whitelist()
def mark_notification_read(name: str) -> dict[str, Any]:
	_require_frontend_role()
	doc = _get_own_notification(name)
	if not doc.is_read:
		doc.is_read = 1
		doc.read_at = now_datetime()
		doc.save(ignore_permissions=True)
	return _serialize(doc)


@frappe.whitelist()
def mark_all_notifications_read() -> int:
	_require_frontend_role()
	return frappe.db.set_value("Tecponto Notification", {"recipient": frappe.session.user, "is_read": 0}, {"is_read": 1, "read_at": now_datetime()}, update_modified=False)


def _render(template_key: str, context: dict[str, Any]) -> dict[str, str]:
	service_order = context.get("service_order") or context.get("reference_name")
	request = context.get("request")
	if template_key == "request_created":
		return {"type": "approval", "title": "Nova solicitação para aprovação", "body": f"{context.get('request_type') or 'Solicitação'} aguarda sua decisão.", "link": f"/tecponto?view=overview&request={request}"}
	if template_key == "request_decided":
		return {"type": "approval", "title": f"Solicitação {str(context.get('status')).lower()}", "body": f"{context.get('request_type') or 'Sua solicitação'} recebeu uma decisão.", "link": f"/tecponto?view=overview&request={request}"}
	if template_key == "quote_expiring":
		return {"type": "deadline", "title": "Orçamento perto de expirar", "body": f"A OS {service_order} expira nas próximas 12 horas.", "link": _service_order_link(service_order)}
	if template_key == "ready_for_pickup":
		return {"type": "pickup", "title": "OS aguardando retirada", "body": f"A OS {service_order} está pronta há {context.get('days')} dias.", "link": _service_order_link(service_order)}
	return {"type": "service_order", "title": "OS atualizada", "body": f"A OS {service_order} mudou para {context.get('state') or 'novo estado'}.", "link": _service_order_link(service_order)}


def _service_order_link(name: str | None) -> str:
	return f"/tecponto?view=service-orders&order={name}" if name else "/tecponto?view=service-orders"


def _already_sent(user: str, template_key: str, context: dict[str, Any]) -> bool:
	# Event notifications are unique per event document; scheduler notices are unique per OS/template.
	filters = {"recipient": user, "template_key": template_key}
	if context.get("request"):
		filters["reference_name"] = context["request"]
	elif context.get("reference_name"):
		filters["reference_name"] = context["reference_name"]
	else:
		return False
	return bool(frappe.db.exists("Tecponto Notification", filters))


def _users_with_role(role: str) -> list[str]:
	# Resolve through Frappe's role service, which also covers roles provisioned by setup hooks.
	return [
		user.name
		for user in frappe.get_all("User", filters={"enabled": 1}, fields=["name"], limit_page_length=0)
		if role in frappe.get_roles(user.name)
	]


def notification_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return ""
	return f"`tabTecponto Notification`.recipient = {frappe.db.escape(user)}"


def notification_has_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or "System Manager" in frappe.get_roles(user) or doc.recipient == user


def _get_own_notification(name: str):
	doc = frappe.get_doc("Tecponto Notification", (name or "").strip())
	if doc.recipient != frappe.session.user:
		raise frappe.PermissionError(_("Esta notificação não pertence ao usuário atual."))
	return doc


def _require_frontend_role() -> None:
	if frappe.session.user == "Guest" or not (set(frappe.get_roles()) & FRONTEND_ROLES):
		raise frappe.PermissionError(_("Usuário sem papel operacional Tecponto."))


def _serialize(row) -> dict[str, Any]:
	return {"name": row.name, "type": row.notification_type, "title": row.title, "body": row.body, "link": row.link, "reference_doctype": row.reference_doctype, "reference_name": row.reference_name, "is_read": bool(row.is_read), "read_at": str(row.read_at or ""), "creation": str(row.creation or "")}
