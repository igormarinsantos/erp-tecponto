"""Server-owned operational configuration for each Tecponto installation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import frappe
from frappe.utils import cint, flt


DEFAULT_OPERATION_CONFIG: dict[str, Any] = {
	"pillars": {"repair": True, "buy": True, "tradein": True},
	"technician_commissions_enabled": False,
	"diagnostic_fee": {"enabled": False, "amount": 0.0},
	"storage_fee": {"enabled": False, "amount": 0.0, "start_days": 30, "abandonment_days": 90},
	"diagnosis_only_enabled": False,
	"payments": {"advance_enabled": True, "installments_enabled": True, "device_tradein_enabled": True},
	"default_warranty_days": 90,
}


def get_operation_config() -> dict[str, Any]:
	"""Return the single presentation-safe operation contract for the frontend.

	Business behavior remains server-owned in its dedicated services. This contract
	exists so no UI surface reads ``Tecponto Settings`` independently.
	"""
	if not frappe.db.exists("DocType", "Tecponto Settings"):
		return deepcopy(DEFAULT_OPERATION_CONFIG)

	settings = frappe.get_single("Tecponto Settings")
	return {
		"pillars": {
			"repair": bool(cint(settings.get("enable_repair_pillar", 1))),
			"buy": bool(cint(settings.get("enable_buy_pillar", 1))),
			"tradein": bool(cint(settings.get("enable_tradein_pillar", 1))),
		},
		"technician_commissions_enabled": bool(cint(settings.get("use_technician_commission"))),
		"diagnostic_fee": {
			"enabled": bool(cint(settings.get("diagnostic_fee_enabled"))),
			"amount": flt(settings.get("diagnostic_fee_amount")),
		},
		"storage_fee": {
			"enabled": bool(cint(settings.get("storage_fee_enabled"))),
			"amount": flt(settings.get("storage_fee_amount")),
			"start_days": cint(settings.get("storage_fee_start_days") or 30),
			"abandonment_days": cint(settings.get("storage_fee_abandonment_days") or 90),
		},
		"diagnosis_only_enabled": bool(cint(settings.get("diagnosis_only_enabled"))),
		"payments": {
			"advance_enabled": bool(cint(settings.get("payment_advance_enabled", 1))),
			"installments_enabled": bool(cint(settings.get("payment_installments_enabled", 1))),
			"device_tradein_enabled": bool(cint(settings.get("payment_device_tradein_enabled", 1))),
		},
		"default_warranty_days": cint(settings.get("default_warranty_days") or 90),
	}
