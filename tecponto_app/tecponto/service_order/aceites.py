import frappe
from frappe.utils import add_days, now, nowdate

from tecponto_app.tecponto.operation_config import get_operation_config


STATE_ENTRADA_CRIADA = "Entrada criada"
STATE_ENTREGUE = "Entregue"
STATE_APROVADO = "Aprovado"
STATE_REPROVADO = "Reprovado"
APPROVAL_STATUS_APROVADO = "Aprovado"
APPROVAL_STATUS_REPROVADO = "Reprovado"
STATE_PRONTO_RETIRADA = "Pronto para retirada"
NO_REPAIR_PICKUP_STATES = {"Reprovado", "Orçamento expirado", "Sem conserto"}
REMOTE_APPROVAL_CHANNELS = {"WhatsApp", "Telefone"}


def validate_aceites(doc, method=None) -> None:
	_validate_entry_acceptance(doc)
	_validate_approval_acceptance(doc)
	_validate_delivery_acceptance(doc)


def mark_pickup_without_repair(doc, method=None) -> None:
	"""Preserve the no-repair route after the workflow reaches Entregue."""
	if doc.get("workflow_state") != STATE_PRONTO_RETIRADA:
		return
	previous = doc.get_doc_before_save() if not doc.is_new() else None
	if previous and previous.get("workflow_state") in NO_REPAIR_PICKUP_STATES:
		doc.pickup_without_repair = 1


def _validate_entry_acceptance(doc) -> None:
	if not doc.get("workflow_state") or doc.get("workflow_state") == STATE_ENTRADA_CRIADA:
		return

	if not doc.get("entry_photos"):
		frappe.throw("Foto de entrada e obrigatoria antes de iniciar o atendimento.")

	# O termo de entrada existe somente quando a loja declarou que vai ligar ou
	# testar o aparelho. Entradas sem teste seguem sem aceite intermediário.
	if not doc.get("link_acceptance_required"):
		return

	from tecponto_app.tecponto.acceptance import (
		assert_completed_acceptance_evidence,
		assert_completed_inoperative_device_term,
		has_completed_physical_acceptance,
	)
	from tecponto_app.tecponto.service_order.inoperative_device import (
		requires_inoperative_device_term,
	)

	assert_completed_acceptance_evidence(doc.name, "Entrada", required=True)
	if doc.meta.has_field("entry_signature") and not doc.get("entry_signature") and not has_completed_physical_acceptance(doc.name, "Entrada"):
		frappe.throw("Assinatura de entrada ou via física arquivada é obrigatória antes de iniciar o atendimento.")
	if requires_inoperative_device_term(doc):
		assert_completed_inoperative_device_term(doc.name)


def _validate_approval_acceptance(doc) -> None:
	workflow_state = doc.get("workflow_state")
	if workflow_state not in {STATE_APROVADO, STATE_REPROVADO}:
		return

	expected_status = APPROVAL_STATUS_APROVADO if workflow_state == STATE_APROVADO else APPROVAL_STATUS_REPROVADO
	if doc.get("approval_status") != expected_status:
		frappe.throw("Use o fluxo de aprovação para registrar a decisão do orçamento.")

	if not (doc.get("approval_channel") and doc.get("approved_by_attendant")):
		frappe.throw("Registre o canal e o atendente da aprovacao.")

	if not doc.get("approval_date"):
		doc.approval_date = now()

	if workflow_state == STATE_REPROVADO and not (doc.get("approval_notes") or "").strip():
		frappe.throw("Registre o motivo da reprovação do orçamento.")

	approval_channel = doc.get("approval_channel")
	if approval_channel in REMOTE_APPROVAL_CHANNELS and not _has_quote_dispatch_evidence(doc):
		frappe.throw("Registre o envio do orçamento antes de confirmar uma decisão remota.")
	# Budget approval is deliberately lightweight. A public link is itself the
	# decision channel; manual channels retain a real uploaded/linked record.
	if approval_channel != "Link" and workflow_state == STATE_APROVADO:
		if not _has_manual_approval_evidence(doc):
			frappe.throw("Aprovação manual (balcão/whatsapp/telefone) exige comprovante, termo assinado ou documento anexado à OS.")

	if workflow_state == STATE_APROVADO:
		from tecponto_app.tecponto.service_order.deadline import assert_budget_approval_within_deadline

		assert_budget_approval_within_deadline(doc)


def _has_manual_approval_evidence(doc) -> bool:
	from tecponto_app.tecponto.acceptance import has_completed_physical_acceptance

	if has_completed_physical_acceptance(doc.name, "Orçamento"):
		return True
	if doc.meta.has_field("customer_signature") and doc.get("customer_signature"):
		return True
	if doc.meta.has_field("approval_attachment") and doc.get("approval_attachment"):
		return True
	if frappe.db.exists("File", {"attached_to_doctype": doc.doctype, "attached_to_name": doc.name}):
		return True
	comms = frappe.get_all("Communication", filters={"reference_doctype": doc.doctype, "reference_name": doc.name}, fields=["name"])
	if comms:
		comm_names = [c.name for c in comms]
		if frappe.db.exists("File", {"attached_to_doctype": "Communication", "attached_to_name": ["in", comm_names]}):
			return True
	return False


def _has_quote_dispatch_evidence(doc) -> bool:
	return bool(
		frappe.db.exists(
			"Communication",
			{
				"reference_doctype": doc.doctype,
				"reference_name": doc.name,
				"subject": ["like", "Orçamento enviado%"],
			},
		)
	)


def _validate_delivery_acceptance(doc) -> None:
	if doc.get("workflow_state") != STATE_ENTREGUE:
		return

	previous = doc.get_doc_before_save() if not doc.is_new() else None
	is_delivery_transition = not previous or previous.get("workflow_state") != STATE_ENTREGUE

	if not doc.get("is_warranty") and (doc.get("sales_invoice") or not doc.get("pickup_without_repair")):
		_exigir_nota_paga(doc)

	from tecponto_app.tecponto.acceptance import assert_completed_acceptance_evidence, has_completed_physical_acceptance

	assert_completed_acceptance_evidence(
		doc.name,
		"Retirada",
		required=bool(doc.get("link_acceptance_required")),
	)
	if not doc.get("customer_signature") and not has_completed_physical_acceptance(doc.name, "Retirada"):
		frappe.throw("Assinatura de retirada ou via física arquivada é obrigatória.")

	# Delivery is the legal and operational start of a normal warranty. The
	# resulting dates are written once, so later settings changes cannot rewrite
	# a warranty already granted.
	if not is_delivery_transition:
		return

	if doc.meta.has_field("pickup_date"):
		doc.pickup_date = nowdate()

	if not doc.meta.has_field("warranty_expiry"):
		return

	if doc.get("is_warranty"):
		if not doc.get("warranty_expiry"):
			frappe.throw("Retrabalho em garantia exige a validade registrada da OS original.")
		return

	doc.warranty_expiry = add_days(doc.pickup_date, get_operation_config()["default_warranty_days"])


def _exigir_nota_paga(doc) -> None:
	if not doc.get("sales_invoice"):
		frappe.throw("Nao e possivel entregar sem nota emitida.")

	status = frappe.db.get_value("Sales Invoice", doc.sales_invoice, "status")
	if status != "Paid":
		frappe.throw("A nota precisa estar paga antes da entrega.")
