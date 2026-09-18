from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


CUSTOMER_FRONTEND_FIELDS = {
	"Customer": [
		{
			"fieldname": "custom_nao_possui_cpf",
			"fieldtype": "Check",
			"insert_after": "custom_cpf",
			"label": "Não possui CPF",
			"module": "Tecponto",
		},
	]
}


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
	create_custom_fields(CUSTOMER_FRONTEND_FIELDS, update=True)

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

	# A cold shared assets.json cache (frappe.utils.get_assets_json) has been
	# observed returning None to whichever caller hits it first on a
	# brand-new site. Warming it here means a print/PDF-generating check
	# (e.g. run_pos_sale_checks -> pos_download_receipt) is never that
	# first caller. See tecponto_app.install._warm_assets_json_cache for
	# the same protection on real deployments.
	try:
		frappe.utils.get_assets_json()
	except Exception:
		pass
