"""Small, server-owned switches and facts for a lean Tecponto operation."""

from __future__ import annotations

import frappe
from frappe.utils import cint


OPERATIONAL_ROLES = {
	"Tecponto Atendente",
	"Tecponto Tecnico",
	"Tecponto Gestor",
	"Tecponto Diretor",
}
TECHNICIAN_ROLE = "Tecponto Tecnico"


def technician_commissions_enabled() -> bool:
	"""Commission is opt-in for new, single-owner installations."""
	if not frappe.db.exists("DocType", "Tecponto Settings"):
		return False
	return bool(cint(frappe.db.get_single_value("Tecponto Settings", "use_technician_commission")))


def active_users_with_role(role: str) -> set[str]:
	"""Return enabled people, deduplicated even when they accumulate roles."""
	return {
		row.name
		for row in frappe.get_all("User", filters={"enabled": 1}, fields=["name"], limit_page_length=0)
		if role in frappe.get_roles(row.name)
	}


def active_operational_users() -> set[str]:
	return {
		row.name
		for row in frappe.get_all("User", filters={"enabled": 1}, fields=["name"], limit_page_length=0)
		if OPERATIONAL_ROLES.intersection(frappe.get_roles(row.name))
	}


def operation_shape() -> dict[str, int | bool]:
	"""Facts used by the UI; no presentation rule is trusted for permissions."""
	operational_users = active_operational_users()
	technicians = active_users_with_role(TECHNICIAN_ROLE)
	return {
		"active_operational_users": len(operational_users),
		"active_technicians": len(technicians),
		"single_operator": len(operational_users) == 1,
		"single_technician": len(technicians) == 1,
	}
