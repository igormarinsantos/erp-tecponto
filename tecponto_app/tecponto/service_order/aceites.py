import frappe
from frappe.utils import add_days, now, nowdate


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


def require_link_acceptance_for_new_orders(doc, method=None) -> None:
	"""Mark every newly created OS as link-acceptance based.

	Existing rows remain explicitly legacy-compatible.  This is deliberately set in
	the model hook, so a Desk-created OS has exactly the same legal acceptance
	requirement as one created through the React check-in.
	"""
	if doc.is_new() and doc.meta.has_field("link_acceptance_required"):
		doc.link_acceptance_required = 1


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

	if doc.meta.has_field("entry_signature") and not doc.get("entry_signature"):
		frappe.throw("Assinatura de entrada e obrigatoria antes de iniciar o atendimento.")

	from tecponto_app.tecponto.acceptance import (
		assert_completed_acceptance_evidence,
		assert_completed_inoperative_device_term,
	)
	from tecponto_app.tecponto.service_order.inoperative_device import (
		requires_inoperative_device_term,
	)

	assert_completed_acceptance_evidence(
		doc.name,
		"Entrada",
		required=bool(doc.get("link_acceptance_required")),
	)
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
	# The public rejection flow records a mandatory reason but intentionally does
	# not collect selfie/signature. Those evidences are required only when the
	# customer authorizes the financially relevant repair.
	if approval_channel == "Link" and workflow_state == STATE_APROVADO:
		from tecponto_app.tecponto.acceptance import (
			assert_completed_acceptance_evidence,
			assert_completed_customer_supplied_part_term,
		)
		from tecponto_app.tecponto.service_order.customer_supplied_part import requires_customer_supplied_part_term

		assert_completed_acceptance_evidence(doc.name, "Orçamento", required=True)
		if requires_customer_supplied_part_term(doc):
			assert_completed_customer_supplied_part_term(doc.name)

	if workflow_state == STATE_APROVADO:
		from tecponto_app.tecponto.service_order.deadline import assert_budget_approval_within_deadline

		assert_budget_approval_within_deadline(doc)


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

	if not doc.get("is_warranty") and (doc.get("sales_invoice") or not doc.get("pickup_without_repair")):
		_exigir_nota_paga(doc)

	if not doc.get("customer_signature"):
		frappe.throw("Assinatura de retirada e obrigatoria.")

	from tecponto_app.tecponto.acceptance import assert_completed_acceptance_evidence

	assert_completed_acceptance_evidence(
		doc.name,
		"Retirada",
		required=bool(doc.get("link_acceptance_required")),
	)

	if doc.meta.has_field("warranty_expiry") and not doc.get("warranty_expiry"):
		doc.warranty_expiry = add_days(nowdate(), 90)


def _exigir_nota_paga(doc) -> None:
	if not doc.get("sales_invoice"):
		frappe.throw("Nao e possivel entregar sem nota emitida.")

	status = frappe.db.get_value("Sales Invoice", doc.sales_invoice, "status")
	if status != "Paid":
		frappe.throw("A nota precisa estar paga antes da entrega.")
