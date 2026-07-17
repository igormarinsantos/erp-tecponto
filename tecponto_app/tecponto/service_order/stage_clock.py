from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

import frappe
from frappe.utils import flt, get_datetime, getdate, now_datetime

from tecponto_app.tecponto.service_order.stage_sla import (
	BUSINESS_DAY_END,
	add_commercial_business_hours,
	get_stage_slas,
)


TERMINAL_STATES = {"Entregue", "Cancelado", "Reprovado", "Orçamento expirado", "Sem conserto"}


def set_stage_entered_at(doc: Any, method: str | None = None) -> None:
	"""Maintain an automatic timestamp only when the workflow stage changes."""
	if doc.is_new():
		doc.stage_entered_at = doc.get("stage_entered_at") or doc.get("entry_date") or now_datetime()
	elif doc.has_value_changed("workflow_state"):
		doc.stage_entered_at = now_datetime()


def get_stage_clock(doc: Any, reference_datetime=None) -> dict[str, Any]:
	"""Return deadline state derived from the current stage and immutable timestamps."""
	now = get_datetime(reference_datetime) if reference_datetime else now_datetime()
	state = doc.get("workflow_state") or "Entrada criada"
	entered_at = get_datetime(doc.get("stage_entered_at") or doc.get("modified") or doc.get("entry_date") or now)
	sla_hours = _sla_hours_for_state(state)
	stage_deadline = add_commercial_business_hours(entered_at, sla_hours) if sla_hours > 0 and state not in TERMINAL_STATES else None
	estimated_deadline = _estimated_deadline_at(doc.get("estimated_deadline"))
	is_stage_overdue = bool(stage_deadline and now > stage_deadline)
	is_total_overdue = bool(estimated_deadline and now > estimated_deadline and state not in TERMINAL_STATES)
	return {
		"stage_entered_at": str(entered_at),
		"stage_sla_business_hours": sla_hours,
		"stage_deadline": str(stage_deadline or ""),
		"estimated_deadline": str(doc.get("estimated_deadline") or ""),
		"is_stage_overdue": is_stage_overdue,
		"is_total_overdue": is_total_overdue,
		"is_overdue": is_stage_overdue or is_total_overdue,
		"urgency": "overdue" if is_stage_overdue or is_total_overdue else "normal",
	}


def list_overdue_service_order_names(reference_datetime=None, filters: dict[str, Any] | None = None) -> list[str]:
	"""Single source for dashboard/list/agenda consumers; no persisted overdue flag."""
	filters = dict(filters or {})
	filters["workflow_state"] = ["not in", list(TERMINAL_STATES)]
	rows = frappe.get_all(
		"Service Order",
		filters=filters,
		fields=["name", "workflow_state", "stage_entered_at", "estimated_deadline", "entry_date", "modified"],
		limit_page_length=0,
	)
	return [row.name for row in rows if get_stage_clock(row, reference_datetime).get("is_overdue")]


def _sla_hours_for_state(state: str) -> float:
	# List/kanban serialisation can touch many OS in one request. Keep the editable
	# rows in request-local memory, never as a persisted overdue value.
	slas = getattr(frappe.local, "_tecponto_stage_sla_hours", None)
	if slas is None:
		slas = {
			row.workflow_state: max(0, flt(row.business_hours))
			for row in get_stage_slas()
			if row.active
		}
		frappe.local._tecponto_stage_sla_hours = slas
	return slas.get(state, 0)


def _estimated_deadline_at(value: Any) -> datetime | None:
	if not value:
		return None
	return datetime.combine(getdate(value), BUSINESS_DAY_END)
