from __future__ import annotations

import frappe


TRADEIN_WORKFLOW_STATES = {
	"Aprovado para compra": "Primary",
	"Comprado": "Success",
}


def ensure_tradein_workflow_states() -> None:
	for state, style in TRADEIN_WORKFLOW_STATES.items():
		if frappe.db.exists("Workflow State", state):
			continue

		frappe.get_doc(
			{
				"doctype": "Workflow State",
				"workflow_state_name": state,
				"style": style,
			}
		).insert(ignore_permissions=True)
