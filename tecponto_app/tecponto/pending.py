from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, now_datetime, today

from tecponto_app.tecponto.service_order import stage_clock


FRONTEND_ROLES = {
	"System Manager",
	"Tecponto Atendente",
	"Tecponto Tecnico",
	"Tecponto Gestor",
	"Tecponto Diretor",
}
PANEL_ROLES = {
	"atendente": "Tecponto Atendente",
	"tecnico": "Tecponto Tecnico",
	"gestor": "Tecponto Gestor",
	"diretor": "Tecponto Diretor",
}
STATE_ACTIONS = {
	"Entrada criada": ("Aguardar tecnico", "muted"),
	"Em diagn\u00f3stico": ("Diagnosticar", "blue"),
	"Aguardando aprova\u00e7\u00e3o": ("Cobrar aceite", "amber"),
	"Aguardando pe\u00e7a": ("Acompanhar peca", "orange"),
	"Em reparo": ("Acompanhar reparo", "blue"),
	"Pronto para retirada": ("Chamar retirada", "green"),
	"Entregue": ("Concluida", "muted"),
	"Reprovado": ("Retirada sem reparo", "orange"),
	"Or\u00e7amento expirado": ("Retirada sem reparo", "orange"),
}


def action_for_service_order_state(state: str | None) -> dict[str, str]:
	label, tone = STATE_ACTIONS.get(state or "", ("Abrir OS", "muted"))
	return {"label": label, "tone": tone}


@frappe.whitelist()
def list_daily_actions(panel: str | None = None) -> dict[str, Any]:
	panels = _resolve_panels(panel)
	derived_by_key = {
		item["key"]: item
		for resolved_panel in panels
		for item in _derived_actions(resolved_panel)
	}
	derived = _sort_actions(list(derived_by_key.values()))
	manual = _manual_actions()
	return {
		"derived": derived,
		"manual": manual,
		"items": _sort_actions([*derived, *manual]),
		"count": len(derived) + len(manual),
	}


@frappe.whitelist()
def create_manual_task(title: str, due_date: str | None = None, reference_doctype: str | None = None, reference_name: str | None = None) -> dict[str, Any]:
	_require_frontend_role()
	title = (title or "").strip()
	due_date = str(due_date or "").strip()
	if due_date.lower() in {"undefined", "null"}:
		due_date = ""
	if not title:
		frappe.throw(_("Informe o titulo da tarefa."), frappe.ValidationError)
	if len(title) > 140:
		frappe.throw(_("O titulo da tarefa deve ter no maximo 140 caracteres."), frappe.ValidationError)
	if reference_doctype and reference_name and not frappe.db.exists(reference_doctype, reference_name):
		frappe.throw(_("Documento relacionado nao encontrado."), frappe.DoesNotExistError)
	doc = frappe.get_doc(
		{
			"doctype": "Tecponto Task",
			"title": title,
			"due_date": due_date or today(),
			"reference_doctype": reference_doctype or None,
			"reference_name": reference_name or None,
			"status": "Aberta",
			"owner_user": frappe.session.user,
		}
	)
	doc.insert(ignore_permissions=True)
	return _serialize_manual_task(doc)


@frappe.whitelist()
def complete_manual_task(name: str) -> dict[str, Any]:
	_require_frontend_role()
	doc = frappe.get_doc("Tecponto Task", name)
	if doc.owner_user != frappe.session.user and frappe.session.user != "Administrator":
		frappe.throw(_("Voce so pode concluir suas proprias tarefas."), frappe.PermissionError)
	if doc.status != "Concluida":
		doc.status = "Concluida"
		doc.completed_at = now_datetime()
		doc.save(ignore_permissions=True)
	return _serialize_manual_task(doc)


def _derived_actions(panel: str) -> list[dict[str, Any]]:
	if panel == "atendente":
		return _attendant_actions()
	if panel == "tecnico":
		return _technician_actions()
	if panel in {"gestor", "diretor"}:
		return _manager_actions()
	return []


def _attendant_actions() -> list[dict[str, Any]]:
	user = frappe.session.user
	rows = frappe.get_all(
		"Service Order",
		filters={"attendant": user, "workflow_state": ["in", ["Aguardando aprova\u00e7\u00e3o", "Pronto para retirada", "Reprovado", "Or\u00e7amento expirado"]]},
		fields=_clock_fields(),
		order_by="modified desc",
		limit_page_length=50,
	)
	items = [_service_order_action(row, "atendente") for row in rows]
	items.extend(_rejected_request_actions())
	return _sort_actions(items)


def _technician_actions() -> list[dict[str, Any]]:
	user = frappe.session.user
	rows = frappe.get_all(
		"Service Order",
		filters={"technician": user, "workflow_state": ["in", ["Em diagn\u00f3stico", "Aguardando pe\u00e7a", "Em reparo"]]},
		fields=_clock_fields(),
		order_by="modified asc",
		limit_page_length=50,
	)
	return _sort_actions([_service_order_action(row, "tecnico") for row in rows])


def _manager_actions() -> list[dict[str, Any]]:
	items: list[dict[str, Any]] = []
	roles = set(frappe.get_roles())
	if "Tecponto Gestor" in roles or "System Manager" in roles or frappe.session.user == "Administrator":
		for row in frappe.get_all(
			"Tecponto Request",
			filters={"status": "Pendente", "approver_role": "Tecponto Gestor"},
			fields=["name", "request_type", "reason", "expires_on", "creation"],
			order_by="creation asc",
			limit_page_length=50,
		):
			items.append(
				_action(
					key=f"request:{row.name}",
					title="Decidir solicitacao",
					description=row.request_type or "Solicitacao aguardando aprovacao",
					urgency="high",
					link="/tecponto?view=overview#approval-requests",
					reference_doctype="Tecponto Request",
					reference_name=row.name,
				),
			)
	for row in frappe.get_all(
		"Service Order",
		filters={"workflow_state": ["not in", list(stage_clock.TERMINAL_STATES)]},
		fields=_clock_fields(),
		order_by="modified asc",
		limit_page_length=50,
	):
		items.append(_service_order_action(row, panel="gestor"))
	return _sort_actions(items)


def _rejected_request_actions() -> list[dict[str, Any]]:
	return [
		_action(
			key=f"request:{row.name}",
			title="Revisar solicitacao reprovada",
			description=row.request_type or "Solicitacao reprovada",
			urgency="normal",
			link="/tecponto?view=overview#approval-requests",
			reference_doctype="Tecponto Request",
			reference_name=row.name,
		)
		for row in frappe.get_all(
			"Tecponto Request",
			filters={"requested_by": frappe.session.user, "status": "Reprovada"},
			fields=["name", "request_type"],
			order_by="modified desc",
			limit_page_length=20,
		)
	]


def _service_order_action(row: Any, panel: str) -> dict[str, Any]:
	state = row.workflow_state
	state_action = action_for_service_order_state(state)
	clock = stage_clock.get_stage_clock(row)
	urgency = _clock_urgency(clock)
	urgency_sort_at = _clock_sort_at(clock, row)
	return _action(
		key=f"service-order:{row.name}",
		title=state_action["label"],
		description=f"{row.name} - {row.customer or 'Cliente nao informado'}",
		urgency=urgency,
		urgency_sort_at=urgency_sort_at,
		group_key=f"service-order:{state or 'sem-etapa'}",
		group_label=f"OS {str(state or 'sem etapa').lower()}",
		link=f"/tecponto?view=service-orders&order={row.name}",
		reference_doctype="Service Order",
		reference_name=row.name,
		tone="orange" if urgency == "overdue" else state_action["tone"],
	)


def _manual_actions() -> list[dict[str, Any]]:
	return [
		{
			**_serialize_manual_task(row),
			"kind": "manual",
			"urgency": "overdue" if row.due_date and getdate(row.due_date) < getdate(today()) else "due_today" if row.due_date and getdate(row.due_date) == getdate(today()) else "scheduled",
			"urgency_sort_at": str(row.due_date or "9999-12-31"),
			"group_key": "manual-task",
			"group_label": "Tarefas manuais",
		}
		for row in frappe.get_all(
			"Tecponto Task",
			filters={"owner_user": frappe.session.user, "status": "Aberta"},
			fields=["name", "title", "due_date", "reference_doctype", "reference_name", "status", "owner_user"],
			order_by="due_date asc, creation asc",
			limit_page_length=50,
		)
	]


def _serialize_manual_task(doc: Any) -> dict[str, Any]:
	return {
		"name": doc.name,
		"title": doc.title,
		"due_date": str(doc.get("due_date") or ""),
		"reference_doctype": doc.get("reference_doctype"),
		"reference_name": doc.get("reference_name"),
		"status": doc.status,
	}


def _action(**values: Any) -> dict[str, Any]:
	return {"kind": "derived", "tone": "orange", **values}


def _sort_actions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
	priority = {"overdue": 0, "due_today": 1, "scheduled": 2, "high": 0, "normal": 1, "low": 2}
	return sorted(
		items,
		key=lambda item: (
			priority.get(item["urgency"], 1),
			item.get("urgency_sort_at") or "9999-12-31 23:59:59",
			item["title"],
		),
	)


def _clock_fields() -> list[str]:
	return ["name", "workflow_state", "customer", "modified", "entry_date", "stage_entered_at", "estimated_deadline"]


def _clock_urgency(clock: dict[str, Any]) -> str:
	if clock.get("is_overdue"):
		return "overdue"
	today_value = getdate(today())
	for value in (clock.get("stage_deadline"), clock.get("estimated_deadline")):
		if value and getdate(value) <= today_value:
			return "due_today"
	return "scheduled"


def _clock_sort_at(clock: dict[str, Any], row: Any) -> str:
	"""Earliest actual deadline first makes the most overdue work surface first."""
	candidates = [
		get_datetime(value)
		for value in (clock.get("stage_deadline"), clock.get("estimated_deadline"), row.get("stage_entered_at"), row.get("entry_date"))
		if value
	]
	return str(min(candidates)) if candidates else "9999-12-31 23:59:59"


def _resolve_panel(panel: str | None) -> str:
	return _resolve_panels(panel)[0]


def _resolve_panels(panel: str | None) -> list[str]:
	_require_frontend_role()
	requested = (panel or "").strip().lower()
	roles = set(frappe.get_roles())
	available = [
		candidate
		for candidate in ("gestor", "tecnico", "atendente", "diretor")
		if PANEL_ROLES[candidate] in roles or "System Manager" in roles or frappe.session.user == "Administrator"
	]
	if requested == "unified":
		return available or ["diretor"]
	if requested in PANEL_ROLES and (PANEL_ROLES[requested] in roles or "System Manager" in roles or frappe.session.user == "Administrator"):
		return [requested]
	if available:
		return [available[0]]
	return ["diretor"]


def _require_frontend_role() -> None:
	if frappe.session.user == "Guest" or not (set(frappe.get_roles()) & FRONTEND_ROLES):
		raise frappe.PermissionError(_("Usuario sem papel Tecponto."))
