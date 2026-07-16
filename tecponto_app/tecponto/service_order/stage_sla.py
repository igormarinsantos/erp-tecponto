from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate

from tecponto_app.tecponto.service_order.deadline import ensure_guarulhos_holiday_list, _get_holiday_dates


STAGE_SLA_DOCTYPE = "Tecponto Stage SLA"
SLA_EDITOR_ROLES = {"System Manager", "Tecponto Gestor", "Tecponto Diretor"}
BUSINESS_DAY_START = time(9, 0)
BUSINESS_DAY_END = time(18, 0)

# A blank SLA means no operational alert for that stage. It never means a blocked OS.
DEFAULT_STAGE_SLAS = (
	("Entrada criada", 4, "Tempo para iniciar o diagnóstico."),
	("Em diagnóstico", 48, "Tempo interno para concluir o diagnóstico."),
	("Aguardando aprovação", 48, "Prazo de resposta do cliente."),
	("Aguardando peça", 0, "Preencha apenas quando houver prazo do fornecedor."),
	("Pronto para retirada", 16, "Lembrete operacional após dois dias úteis."),
)


def ensure_stage_slas() -> None:
	"""Install editable defaults without overwriting a manager decision."""
	for workflow_state, business_hours, description in DEFAULT_STAGE_SLAS:
		if frappe.db.exists(STAGE_SLA_DOCTYPE, workflow_state):
			continue
		frappe.get_doc(
			{
				"doctype": STAGE_SLA_DOCTYPE,
				"workflow_state": workflow_state,
				"business_hours": business_hours,
				"description": description,
				"active": 1,
			}
		).insert(ignore_permissions=True)


def get_stage_slas() -> list[dict[str, Any]]:
	ensure_stage_slas()
	return frappe.get_all(
		STAGE_SLA_DOCTYPE,
		fields=["name", "workflow_state", "business_hours", "description", "active"],
		order_by="workflow_state asc",
	)


def save_stage_sla(payload: dict[str, Any]) -> dict[str, Any]:
	_require_sla_editor()
	workflow_state = (payload.get("workflow_state") or "").strip()
	if not workflow_state:
		frappe.throw(_("Informe a etapa do workflow."), frappe.ValidationError)
	doc = frappe.get_doc(STAGE_SLA_DOCTYPE, workflow_state) if frappe.db.exists(STAGE_SLA_DOCTYPE, workflow_state) else frappe.new_doc(STAGE_SLA_DOCTYPE)
	doc.update(
		{
			"workflow_state": workflow_state,
			"business_hours": max(0, flt(payload.get("business_hours"))),
			"description": (payload.get("description") or "").strip(),
			"active": 1 if payload.get("active", True) else 0,
		}
	)
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	return _serialize_sla(doc)


def calculate_suggested_delivery(
	start_datetime=None,
	service_duration: float = 0,
	service_duration_unit: str = "Horas",
	lead_time_business_hours: float = 0,
) -> dict[str, Any]:
	"""Suggest, never impose, a delivery date from operational SLA inputs."""
	ensure_stage_slas()
	start = get_datetime(start_datetime) if start_datetime else frappe.utils.now_datetime()
	slas = {row.workflow_state: flt(row.business_hours) for row in get_stage_slas() if cint(row.active)}
	base_stages = ("Entrada criada", "Em diagnóstico", "Aguardando aprovação")
	stage_hours = sum(slas.get(state, 0) for state in base_stages)
	service_hours = _duration_as_business_hours(service_duration, service_duration_unit)
	lead_time = max(0, flt(lead_time_business_hours))
	total_hours = stage_hours + service_hours + lead_time
	return {
		"suggested_delivery_date": str(add_commercial_business_hours(start, total_hours).date()) if total_hours else "",
		"total_business_hours": total_hours,
		"stage_business_hours": stage_hours,
		"service_business_hours": service_hours,
		"lead_time_business_hours": lead_time,
	}


def add_commercial_business_hours(start_datetime, hours: float, holiday_list: str | None = None) -> datetime:
	"""Advance only during Mon-Fri 09:00-18:00, excluding Guarulhos holidays."""
	current = get_datetime(start_datetime)
	remaining_seconds = max(0, flt(hours)) * 60 * 60
	holiday_dates = _get_holiday_dates(holiday_list or ensure_guarulhos_holiday_list())
	while remaining_seconds > 0:
		current = _normalise_business_time(current, holiday_dates)
		end_of_day = datetime.combine(getdate(current), BUSINESS_DAY_END)
		available = (end_of_day - current).total_seconds()
		consume = min(remaining_seconds, available)
		current += timedelta(seconds=consume)
		remaining_seconds -= consume
	return current


def _duration_as_business_hours(duration: float, unit: str) -> float:
	if (unit or "").strip() == "Dias úteis":
		return max(0, flt(duration)) * 9
	return max(0, flt(duration))


def _normalise_business_time(current: datetime, holiday_dates: set) -> datetime:
	while True:
		day = getdate(current)
		if day.weekday() >= 5 or day in holiday_dates:
			current = datetime.combine(day + timedelta(days=1), BUSINESS_DAY_START)
			continue
		start = datetime.combine(day, BUSINESS_DAY_START)
		end = datetime.combine(day, BUSINESS_DAY_END)
		if current < start:
			return start
		if current >= end:
			current = datetime.combine(day + timedelta(days=1), BUSINESS_DAY_START)
			continue
		return current


def _serialize_sla(doc: Any) -> dict[str, Any]:
	return {
		"name": doc.name,
		"workflow_state": doc.workflow_state,
		"business_hours": flt(doc.business_hours),
		"description": doc.description or "",
		"active": bool(doc.active),
	}


def _require_sla_editor() -> None:
	if not SLA_EDITOR_ROLES.intersection(set(frappe.get_roles(frappe.session.user))):
		frappe.throw(_("Apenas Gestor ou Diretor pode editar os SLAs."), frappe.PermissionError)
