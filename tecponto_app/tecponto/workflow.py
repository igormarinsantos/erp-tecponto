import frappe


WORKFLOW_NAME = "Service Order"
SERVICE_ORDER_DOCTYPE = "Service Order"

ROLE_ATTENDANT = "Tecponto Atendente"
ROLE_MANAGER = "Tecponto Gestor"
ROLE_TECHNICIAN = "Tecponto Tecnico"
ROLE_SYSTEM_MANAGER = "System Manager"

STATE_ENTRADA_CRIADA = "Entrada criada"
STATE_EM_DIAGNOSTICO = "Em diagn\u00f3stico"
STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO = "Diagnosticado \u2014 aguardando or\u00e7amento"
STATE_AGUARDANDO_APROVACAO = "Aguardando aprova\u00e7\u00e3o"
STATE_APROVADO = "Aprovado"
STATE_REPROVADO = "Reprovado"
STATE_ORCAMENTO_EXPIRADO = "Or\u00e7amento expirado"
STATE_AGUARDANDO_PECA = "Aguardando pe\u00e7a"
STATE_EM_REPARO = "Em reparo"
STATE_TESTE_FINAL = "Teste final"
STATE_PRONTO_RETIRADA = "Pronto para retirada"
STATE_ENTREGUE = "Entregue"
STATE_SEM_CONSERTO = "Sem conserto"
STATE_CANCELADO = "Cancelado"

SERVICE_ORDER_WORKFLOW_STATES = (
	(STATE_ENTRADA_CRIADA, (ROLE_ATTENDANT, ROLE_MANAGER), "Info"),
	(STATE_EM_DIAGNOSTICO, (ROLE_TECHNICIAN, ROLE_MANAGER), "Info"),
	(STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO, (ROLE_ATTENDANT, ROLE_TECHNICIAN, ROLE_MANAGER), "Warning"),
	(STATE_AGUARDANDO_APROVACAO, (ROLE_ATTENDANT, ROLE_MANAGER), "Warning"),
	(STATE_APROVADO, (ROLE_TECHNICIAN, ROLE_MANAGER), "Success"),
	(STATE_REPROVADO, (ROLE_ATTENDANT, ROLE_MANAGER), "Danger"),
	(STATE_ORCAMENTO_EXPIRADO, (ROLE_ATTENDANT, ROLE_MANAGER), "Warning"),
	(STATE_AGUARDANDO_PECA, (ROLE_TECHNICIAN, ROLE_MANAGER), "Warning"),
	(STATE_EM_REPARO, (ROLE_TECHNICIAN, ROLE_MANAGER), "Info"),
	(STATE_TESTE_FINAL, (ROLE_TECHNICIAN, ROLE_MANAGER), "Info"),
	(STATE_PRONTO_RETIRADA, (ROLE_ATTENDANT, ROLE_MANAGER), "Success"),
	(STATE_ENTREGUE, (ROLE_ATTENDANT, ROLE_MANAGER), "Success"),
	(STATE_SEM_CONSERTO, (ROLE_TECHNICIAN, ROLE_MANAGER), "Danger"),
	(STATE_CANCELADO, (ROLE_MANAGER,), "Danger"),
)

SERVICE_ORDER_TRANSITIONS = (
	(STATE_ENTRADA_CRIADA, STATE_EM_DIAGNOSTICO, STATE_EM_DIAGNOSTICO, ROLE_TECHNICIAN),
	(STATE_ENTRADA_CRIADA, STATE_EM_DIAGNOSTICO, STATE_EM_DIAGNOSTICO, ROLE_MANAGER),
	(STATE_EM_DIAGNOSTICO, STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO, STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO, ROLE_TECHNICIAN),
	(STATE_EM_DIAGNOSTICO, STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO, STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO, ROLE_MANAGER),
	(STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO, STATE_AGUARDANDO_APROVACAO, STATE_AGUARDANDO_APROVACAO, ROLE_ATTENDANT),
	(STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO, STATE_AGUARDANDO_APROVACAO, STATE_AGUARDANDO_APROVACAO, ROLE_MANAGER),
	(STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO, STATE_EM_DIAGNOSTICO, STATE_EM_DIAGNOSTICO, ROLE_TECHNICIAN),
	(STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO, STATE_EM_DIAGNOSTICO, STATE_EM_DIAGNOSTICO, ROLE_MANAGER),
	(STATE_AGUARDANDO_APROVACAO, STATE_APROVADO, STATE_APROVADO, ROLE_ATTENDANT),
	(STATE_AGUARDANDO_APROVACAO, STATE_APROVADO, STATE_APROVADO, ROLE_MANAGER),
	(STATE_AGUARDANDO_APROVACAO, STATE_REPROVADO, STATE_REPROVADO, ROLE_ATTENDANT),
	(STATE_AGUARDANDO_APROVACAO, STATE_REPROVADO, STATE_REPROVADO, ROLE_MANAGER),
	(
		STATE_AGUARDANDO_APROVACAO,
		"Expirar or\u00e7amento",
		STATE_ORCAMENTO_EXPIRADO,
		ROLE_SYSTEM_MANAGER,
		"False",
	),
	(STATE_APROVADO, STATE_AGUARDANDO_PECA, STATE_AGUARDANDO_PECA, ROLE_TECHNICIAN),
	(STATE_APROVADO, STATE_AGUARDANDO_PECA, STATE_AGUARDANDO_PECA, ROLE_MANAGER),
	(STATE_APROVADO, STATE_EM_REPARO, STATE_EM_REPARO, ROLE_TECHNICIAN),
	(STATE_APROVADO, STATE_EM_REPARO, STATE_EM_REPARO, ROLE_MANAGER),
	(STATE_EM_REPARO, STATE_TESTE_FINAL, STATE_TESTE_FINAL, ROLE_TECHNICIAN),
	(STATE_TESTE_FINAL, STATE_PRONTO_RETIRADA, STATE_PRONTO_RETIRADA, ROLE_TECHNICIAN),
	(STATE_REPROVADO, "Liberar para retirada", STATE_PRONTO_RETIRADA, ROLE_ATTENDANT),
	(STATE_REPROVADO, "Liberar para retirada", STATE_PRONTO_RETIRADA, ROLE_MANAGER),
	(STATE_ORCAMENTO_EXPIRADO, "Liberar para retirada", STATE_PRONTO_RETIRADA, ROLE_ATTENDANT),
	(STATE_ORCAMENTO_EXPIRADO, "Liberar para retirada", STATE_PRONTO_RETIRADA, ROLE_MANAGER),
	(STATE_SEM_CONSERTO, "Liberar para retirada", STATE_PRONTO_RETIRADA, ROLE_MANAGER),
	(STATE_PRONTO_RETIRADA, STATE_ENTREGUE, STATE_ENTREGUE, ROLE_ATTENDANT),
	(STATE_PRONTO_RETIRADA, STATE_ENTREGUE, STATE_ENTREGUE, ROLE_MANAGER),
)

SEM_CONSERTO_FROM_STATES = (
	STATE_ENTRADA_CRIADA,
	STATE_EM_DIAGNOSTICO,
	STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO,
	STATE_AGUARDANDO_APROVACAO,
	STATE_APROVADO,
	STATE_AGUARDANDO_PECA,
	STATE_EM_REPARO,
	STATE_TESTE_FINAL,
)

CANCELABLE_STATES = (
	STATE_ENTRADA_CRIADA,
	STATE_EM_DIAGNOSTICO,
	STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO,
	STATE_AGUARDANDO_APROVACAO,
	STATE_APROVADO,
	STATE_REPROVADO,
	STATE_ORCAMENTO_EXPIRADO,
	STATE_AGUARDANDO_PECA,
	STATE_EM_REPARO,
	STATE_TESTE_FINAL,
	STATE_PRONTO_RETIRADA,
	STATE_SEM_CONSERTO,
)


def get_service_order_workflow_state_names() -> list[str]:
	return [state for state, _roles, _style in SERVICE_ORDER_WORKFLOW_STATES]


def get_service_order_workflow_action_names() -> list[str]:
	return sorted({transition[1] for transition in _get_service_order_transitions()})


def _get_service_order_transitions() -> list[tuple]:
	transitions = list(SERVICE_ORDER_TRANSITIONS)

	transitions.extend(
		(state, STATE_SEM_CONSERTO, STATE_SEM_CONSERTO, ROLE_TECHNICIAN)
		for state in SEM_CONSERTO_FROM_STATES
	)
	transitions.extend(
		(state, STATE_CANCELADO, STATE_CANCELADO, ROLE_MANAGER)
		for state in CANCELABLE_STATES
	)

	return transitions


def _ensure_workflow_state(state: str, style: str) -> None:
	if frappe.db.exists("Workflow State", state):
		doc = frappe.get_doc("Workflow State", state)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Workflow State",
				"workflow_state_name": state,
			}
		)

	doc.style = style
	doc.save(ignore_permissions=True)


def _ensure_workflow_action(action: str) -> None:
	if frappe.db.exists("Workflow Action Master", action):
		return

	frappe.get_doc(
		{
			"doctype": "Workflow Action Master",
			"workflow_action_name": action,
		}
	).insert(ignore_permissions=True)


def _state_rows() -> list[dict]:
	rows = []
	for state, roles, _style in SERVICE_ORDER_WORKFLOW_STATES:
		for role in roles:
			rows.append(
				{
					"state": state,
					"doc_status": "0",
					"allow_edit": role,
				}
			)

	return rows


def _transition_rows() -> list[dict]:
	rows = []
	for transition in _get_service_order_transitions():
		state, action, next_state, allowed = transition[:4]
		row = {
			"state": state,
			"action": action,
			"next_state": next_state,
			"allowed": allowed,
			"allow_self_approval": 1,
		}
		if len(transition) > 4:
			row["condition"] = transition[4]
		rows.append(row)

	return rows


def ensure_service_order_workflow() -> None:
	if not frappe.db.exists("DocType", SERVICE_ORDER_DOCTYPE):
		return

	for state, _roles, style in SERVICE_ORDER_WORKFLOW_STATES:
		_ensure_workflow_state(state, style)

	for action in get_service_order_workflow_action_names():
		_ensure_workflow_action(action)

	if frappe.db.exists("Workflow", WORKFLOW_NAME):
		workflow = frappe.get_doc("Workflow", WORKFLOW_NAME)
	else:
		workflow = frappe.get_doc(
			{
				"doctype": "Workflow",
				"workflow_name": WORKFLOW_NAME,
				"document_type": SERVICE_ORDER_DOCTYPE,
			}
		)

	workflow.document_type = SERVICE_ORDER_DOCTYPE
	workflow.workflow_state_field = "workflow_state"
	workflow.is_active = 1
	workflow.override_status = 0
	workflow.send_email_alert = 0
	workflow.set("states", _state_rows())
	workflow.set("transitions", _transition_rows())
	workflow.save(ignore_permissions=True)
