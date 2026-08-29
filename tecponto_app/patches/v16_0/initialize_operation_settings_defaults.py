"""Initialize operation defaults for Settings singletons created before Block 1."""

from __future__ import annotations

import frappe


OPERATION_DEFAULTS = {
	"technician_assignment_mode": "Dispatch",
	"unassigned_technician_alert_hours": 4,
	"enable_repair_pillar": 1,
	"enable_buy_pillar": 1,
	"enable_tradein_pillar": 1,
	"use_technician_commission": 0,
	"diagnostic_fee_enabled": 0,
	"diagnostic_fee_amount": 0,
	"storage_fee_enabled": 0,
	"storage_fee_amount": 0,
	"storage_fee_start_days": 30,
	"storage_fee_abandonment_days": 90,
	"diagnosis_only_enabled": 0,
	"payment_advance_enabled": 1,
	"payment_installments_enabled": 1,
	"payment_device_tradein_enabled": 1,
	"default_warranty_days": 90,
}


def _is_uninitialized(value: object) -> bool:
	"""Distinguish a missing legacy singleton key from an explicit zero choice."""
	return value is None or (isinstance(value, str) and not value.strip())


def execute() -> None:
	"""Backfill only absent/blank operation keys after the Settings schema is synced."""
	if not frappe.db.exists("DocType", "Tecponto Settings"):
		return

	current = frappe.db.get_singles_dict("Tecponto Settings")
	updates = {
		fieldname: default
		for fieldname, default in OPERATION_DEFAULTS.items()
		if _is_uninitialized(current.get(fieldname))
	}
	if updates:
		frappe.db.set_single_value("Tecponto Settings", updates, update_modified=False)
