frappe.listview_settings["Service Order"] = {
	add_fields: [
		"workflow_state",
		"approval_deadline",
		"estimated_deadline",
		"customer",
		"customer_device",
	],

	get_indicator(doc) {
		if (is_overdue(doc)) {
			return [__("Atrasada"), "red", "workflow_state,not in,Entregue,Cancelado,Sem conserto"];
		}

		const state = doc.workflow_state || __("Sem status");
		const colors = {
			"Entrada criada": "gray",
			"Em diagnóstico": "light-blue",
			"Diagnosticado — aguardando orçamento": "yellow",
			"Aguardando aprovação": "orange",
			"Aguardando peça": "purple",
			"Em reparo": "blue",
			"Teste final": "cyan",
			"Pronto para retirada": "green",
			"Orçamento expirado": "red",
			Entregue: "green",
			Cancelado: "gray",
			"Sem conserto": "red",
		};

		return [__(state), colors[state] || "gray", `workflow_state,=,${state}`];
	},
};

function is_overdue(doc) {
	if (doc.workflow_state === "Orçamento expirado") {
		return true;
	}

	if (["Entregue", "Cancelado", "Sem conserto"].includes(doc.workflow_state)) {
		return false;
	}

	const deadline = doc.approval_deadline || doc.estimated_deadline;
	if (!deadline) {
		return false;
	}

	return frappe.datetime.str_to_obj(deadline) < frappe.datetime.str_to_obj(frappe.datetime.now_datetime());
}
