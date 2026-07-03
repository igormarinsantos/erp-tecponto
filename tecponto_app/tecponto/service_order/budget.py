from __future__ import annotations

import frappe
from frappe.utils import flt, now_datetime

from tecponto_app.tecponto.service_order.deadline import (
	APPROVAL_BUSINESS_HOURS,
	add_business_hours,
)


STATE_AGUARDANDO_APROVACAO = "Aguardando aprova\u00e7\u00e3o"
STATE_APROVADO = "Aprovado"
APPROVAL_STATUS_APROVADO = "Aprovado"
APPROVAL_STATUS_PENDENTE = "Pendente"

SERVICE_BUDGET_FIELDS = ("item_code", "description", "qty", "rate", "technician")
PART_BUDGET_FIELDS = ("item_code", "qty", "warehouse", "rate", "technician")
NUMERIC_BUDGET_FIELDS = {"qty", "rate"}


def validate_budget_lock(doc, method=None) -> None:
	if _was_budget_locked(doc) and _budget_lines_changed(doc):
		return

	if _is_approved(doc) and not doc.get("quote_locked"):
		doc.quote_locked = 1
		doc.budget_version = doc.get("budget_version") or 1


def reset_locked_budget_if_changed(doc, method=None) -> None:
	if not (_was_budget_locked(doc) and _budget_lines_changed(doc)):
		return

	if doc.get("workflow_state") == STATE_AGUARDANDO_APROVACAO:
		return

	values = {
		"budget_version": (doc.get("budget_version") or 1) + 1,
		"quote_locked": 0,
		"approval_status": APPROVAL_STATUS_PENDENTE,
		"workflow_state": STATE_AGUARDANDO_APROVACAO,
		"approval_deadline": add_business_hours(
			now_datetime(),
			APPROVAL_BUSINESS_HOURS,
		),
	}
	frappe.db.set_value(doc.doctype, doc.name, values, update_modified=True)
	doc.update(values)


def _is_approved(doc) -> bool:
	return (
		doc.get("workflow_state") == STATE_APROVADO
		or doc.get("approval_status") == APPROVAL_STATUS_APROVADO
	)


def _was_budget_locked(doc) -> bool:
	if doc.get("quote_locked"):
		return True

	previous = _get_previous_doc(doc)
	return bool(previous and previous.get("quote_locked"))


def _budget_lines_changed(doc) -> bool:
	previous = _get_previous_doc(doc)
	if not previous:
		return False

	return (
		_line_signature(previous.get("services"), SERVICE_BUDGET_FIELDS)
		!= _line_signature(doc.get("services"), SERVICE_BUDGET_FIELDS)
		or _line_signature(previous.get("parts"), PART_BUDGET_FIELDS)
		!= _line_signature(doc.get("parts"), PART_BUDGET_FIELDS)
	)


def _get_previous_doc(doc):
	if getattr(doc, "_doc_before_save", None):
		return doc._doc_before_save

	if doc.is_new():
		return None

	return doc.get_doc_before_save()


def _line_signature(rows, fields: tuple[str, ...]) -> list[tuple]:
	signature = []
	for row in rows or []:
		signature.append(tuple(_normalized_value(row.get(field), field) for field in fields))
	return signature


def _normalized_value(value, field: str):
	if field in NUMERIC_BUDGET_FIELDS:
		return flt(value)

	return value or None
