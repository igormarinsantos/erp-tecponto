from __future__ import annotations

import frappe


FRONTEND_ROLES = (
	"Tecponto Atendente",
	"Tecponto Tecnico",
	"Tecponto Gestor",
	"Tecponto Diretor",
)

LEGACY_WORKSPACE_DEFAULTS = (
	"Tecponto Atendente",
	"Tecponto Tecnico",
	"Tecponto Gestor",
	"Tecponto Diretor",
)


def ensure_frontend_foundation() -> None:
	for role in FRONTEND_ROLES:
		if frappe.db.exists("Role", role):
			continue

		doc = frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role,
				"desk_access": 1,
			}
		)
		doc.insert(ignore_permissions=True)

	frappe.db.sql(
		"""
		update `tabUser`
		set default_workspace = null
		where default_workspace in %(workspaces)s
		""",
		{"workspaces": LEGACY_WORKSPACE_DEFAULTS},
	)
