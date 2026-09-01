"""Narrow, atomic ownership hand-offs for Service Orders."""

from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha1
from typing import Any

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import flt, get_datetime, now_datetime

from tecponto_app.tecponto.lean_operations import TECHNICIAN_ROLE, active_users_with_role, operation_shape
from tecponto_app.tecponto.operation_config import get_operation_config
from tecponto_app.tecponto.service_order.stage_sla import BUSINESS_DAY_END, BUSINESS_DAY_START, _commercial_holiday_dates

AUDIT_DOCTYPE = "Tecponto Service Order Assignment Event"
MANAGER_ROLES = {"System Manager", "Tecponto Gestor"}
TERMINAL_STATES = {"Entregue", "Cancelado", "Reprovado", "Orçamento expirado", "Sem conserto"}


def assignment_config() -> dict[str, Any]:
	return get_operation_config()["technician_assignment"]


def claim(service_order: str, actor: str) -> dict[str, Any]:
	_require_technician(actor)
	if not operation_shape()["single_technician"]:
		_require_mode("Pull")
	return _change(service_order, actor, actor, "Claim", expected_assigned=False)


def auto_assign_single_technician(service_order: str, actor: str) -> dict[str, Any] | None:
	"""Assign a new OS to the sole technician without bypassing entry gates."""
	shape = operation_shape()
	if shape["active_technicians"] == 0:
		frappe.throw(
			_("Ative ao menos um usuário com o papel Técnico antes de criar uma OS."),
			frappe.ValidationError,
		)
	if not shape["single_technician"]:
		return None
	technicians = active_users_with_role(TECHNICIAN_ROLE)
	if len(technicians) != 1:
		return None
	technician = next(iter(technicians))
	result = _change(
		service_order,
		technician,
		actor,
		"AutoAssign",
		observation="Atribuição automática: único técnico ativo.",
		expected_assigned=False,
	)
	result["advanced"] = advance_auto_assigned_entry(service_order)
	return result


def advance_auto_assigned_entry(service_order: str) -> bool:
	"""Attempt the real workflow; preserve ownership when an entry gate blocks it."""
	if frappe.db.get_value("Service Order", service_order, "workflow_state") != "Entrada criada":
		return False
	if not frappe.db.exists(AUDIT_DOCTYPE, {"service_order": service_order, "event_type": "AutoAssign"}):
		return False
	savepoint = f"tp_auto_advance_{sha1(service_order.encode()).hexdigest()[:12]}"
	frappe.db.savepoint(savepoint)
	previous_user = frappe.session.user
	try:
		# This is a server-owned consequence of the audited automatic assignment.
		# Administrator supplies workflow authority; document hooks still enforce
		# photo, acceptance, biometrics and every lifecycle gate.
		frappe.set_user("Administrator")
		apply_workflow(
			frappe.as_json({"doctype": "Service Order", "name": service_order}),
			"Em diagnóstico",
		)
		return True
	except (frappe.ValidationError, frappe.PermissionError):
		frappe.db.rollback(save_point=savepoint)
		frappe.clear_messages()
		return False
	finally:
		frappe.set_user(previous_user)


def assign(service_order: str, technician: str, actor: str, observation: str = "") -> dict[str, Any]:
	_require_manager(actor)
	_require_technician(technician)
	mode = assignment_config()["mode"]
	observation = (observation or "").strip()
	if mode == "Dispatch":
		return _change(service_order, technician, actor, "Assign", observation=observation, expected_assigned=False)
	if mode == "Pull":
		if not observation:
			frappe.throw(_("Informe a justificativa da intervenção no modo Pull."), frappe.ValidationError)
		return _change(service_order, technician, actor, "Intervention", observation=observation, expected_assigned=False)
	frappe.throw(_("Modo de atribuição inválido."), frappe.ValidationError)


def transfer(service_order: str, technician: str, actor: str, observation: str) -> dict[str, Any]:
	_require_manager(actor)
	_require_technician(technician)
	observation = (observation or "").strip()
	if not observation:
		frappe.throw(_("Informe o motivo da transferência."), frappe.ValidationError)
	return _change(service_order, technician, actor, "Transfer", observation=observation, expected_assigned=True)


def list_unassigned(actor: str, limit: int = 100) -> dict[str, Any]:
	roles = set(frappe.get_roles(actor))
	is_manager = actor == "Administrator" or bool(roles.intersection(MANAGER_ROLES))
	is_technician = TECHNICIAN_ROLE in roles
	mode = assignment_config()["mode"]
	sole_technician_cleanup = is_technician and operation_shape()["single_technician"]
	if not is_manager and not (is_technician and (mode == "Pull" or sole_technician_cleanup)):
		frappe.throw(_("Esta fila não está disponível para seu papel ou modo de atribuição."), frappe.PermissionError)
	terminal_tuple = tuple(TERMINAL_STATES)
	rows = frappe.db.sql(
		"""
		SELECT name, customer, customer_device, entry_date, attendant, technician, priority, workflow_state, stage_entered_at, reported_defect, approval_status, approval_deadline, sales_invoice, modified, creation
		FROM `tabService Order`
		WHERE (technician IS NULL OR technician = '')
		  AND (workflow_state NOT IN %(terminal)s OR workflow_state IS NULL)
		ORDER BY creation ASC
		LIMIT %(limit)s
		""",
		{"terminal": terminal_tuple, "limit": max(1, min(int(limit or 100), 1000))},
		as_dict=True,
	)
	threshold = flt(assignment_config()["alert_hours"])
	for row in rows:
		waiting = business_hours_between(row.creation, now_datetime())
		row["unassigned_waiting_hours"] = waiting
		row["unassigned_overdue"] = bool(threshold and waiting >= threshold)
	return {"items": rows, "count": len(rows), "mode": mode, "alert_hours": threshold}


def _change(service_order: str, technician: str, actor: str, event_type: str, observation: str = "", expected_assigned: bool = False) -> dict[str, Any]:
	service_order = (service_order or "").strip()
	if not service_order:
		frappe.throw(_("Informe a ordem de serviço."), frappe.ValidationError)
	savepoint = f"tp_assign_{sha1(f'{service_order}:{actor}'.encode()).hexdigest()[:12]}"
	frappe.db.savepoint(savepoint)
	try:
		rows = frappe.db.sql(
			"SELECT name, technician, workflow_state FROM `tabService Order` WHERE name=%s FOR UPDATE",
			(service_order,), as_dict=True,
		)
		if not rows:
			frappe.throw(_("Ordem de serviço não encontrada."), frappe.DoesNotExistError)
		row = rows[0]
		previous = (row.technician or "").strip()
		if row.workflow_state in TERMINAL_STATES:
			frappe.throw(_("Não é possível atribuir uma OS encerrada."), frappe.ValidationError)
		if expected_assigned and not previous:
			frappe.throw(_("A OS está sem técnico; use atribuir em vez de transferir."), frappe.ValidationError)
		if not expected_assigned and previous:
			frappe.throw(_("Esta OS já foi assumida por outro técnico."), frappe.ValidationError)
		if previous == technician:
			frappe.throw(_("A OS já está atribuída a este técnico."), frappe.ValidationError)
		doc = frappe.get_doc("Service Order", service_order)
		doc.technician = technician
		doc.save(ignore_permissions=True)
		# Pull means the technician is starting work now. Move only the initial
		# stage through Frappe's workflow so every entry-acceptance gate remains
		# authoritative and the assignment rolls back if a gate rejects it.
		if event_type == "Claim" and row.workflow_state == "Entrada criada":
			apply_workflow(
				frappe.as_json({"doctype": doc.doctype, "name": doc.name}),
				"Em diagnóstico",
			)
		audit = frappe.get_doc({
			"doctype": AUDIT_DOCTYPE,
			"service_order": service_order,
			"event_type": event_type,
			"previous_technician": previous,
			"new_technician": technician,
			"performed_by": actor,
			"assignment_mode": assignment_config()["mode"],
			"observation": (observation or "").strip(),
			"occurred_at": now_datetime(),
		})
		audit.insert(ignore_permissions=True)
		return {"service_order": service_order, "technician": technician, "event": audit.name}
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def business_hours_between(start: Any, end: Any) -> float:
	start_at, end_at = get_datetime(start), get_datetime(end)
	if end_at <= start_at:
		return 0.0
	holidays = _commercial_holiday_dates()
	total = 0.0
	day = start_at.date()
	while day <= end_at.date():
		if day.weekday() < 5 and day not in holidays:
			window_start = datetime.combine(day, BUSINESS_DAY_START)
			window_end = datetime.combine(day, BUSINESS_DAY_END)
			left, right = max(start_at, window_start), min(end_at, window_end)
			if right > left:
				total += (right - left).total_seconds() / 3600
		day += timedelta(days=1)
	return round(total, 2)


def _require_mode(expected: str) -> None:
	if assignment_config()["mode"] != expected:
		frappe.throw(_("A operação está configurada no modo {0}.").format(assignment_config()["mode"]), frappe.PermissionError)


def _require_manager(user: str) -> None:
	if user != "Administrator" and not MANAGER_ROLES.intersection(set(frappe.get_roles(user))):
		frappe.throw(_("Somente o Gestor pode distribuir ou transferir OS."), frappe.PermissionError)


def _require_technician(user: str) -> None:
	if not user or not frappe.db.exists("User", {"name": user, "enabled": 1}) or TECHNICIAN_ROLE not in frappe.get_roles(user):
		frappe.throw(_("Selecione um técnico ativo."), frappe.ValidationError)
