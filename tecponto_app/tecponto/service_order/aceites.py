import frappe
from frappe.utils import add_days, now, nowdate


STATE_ENTRADA_CRIADA = "Entrada criada"
STATE_ENTREGUE = "Entregue"
APPROVAL_STATUS_APROVADO = "Aprovado"


def validate_aceites(doc, method=None) -> None:
	_validate_entry_acceptance(doc)
	_validate_approval_acceptance(doc)
	_validate_delivery_acceptance(doc)


def _validate_entry_acceptance(doc) -> None:
	if not doc.get("workflow_state") or doc.get("workflow_state") == STATE_ENTRADA_CRIADA:
		return

	if not doc.get("entry_photos"):
		frappe.throw("Foto de entrada e obrigatoria antes de iniciar o atendimento.")

	if doc.meta.has_field("entry_signature") and not doc.get("entry_signature"):
		frappe.throw("Assinatura de entrada e obrigatoria antes de iniciar o atendimento.")

	from tecponto_app.tecponto.acceptance import assert_completed_acceptance_evidence

	assert_completed_acceptance_evidence(doc.name, "Entrada")


def _validate_approval_acceptance(doc) -> None:
	if doc.get("approval_status") != APPROVAL_STATUS_APROVADO:
		return

	if not (doc.get("approval_channel") and doc.get("approved_by_attendant")):
		frappe.throw("Registre o canal e o atendente da aprovacao.")

	if not doc.get("approval_date"):
		doc.approval_date = now()


def _validate_delivery_acceptance(doc) -> None:
	if doc.get("workflow_state") != STATE_ENTREGUE:
		return

	if not doc.get("is_warranty"):
		_exigir_nota_paga(doc)

	if not doc.get("customer_signature"):
		frappe.throw("Assinatura de retirada e obrigatoria.")

	from tecponto_app.tecponto.acceptance import assert_completed_acceptance_evidence

	assert_completed_acceptance_evidence(doc.name, "Retirada")

	if doc.meta.has_field("warranty_expiry") and not doc.get("warranty_expiry"):
		doc.warranty_expiry = add_days(nowdate(), 90)


def _exigir_nota_paga(doc) -> None:
	if not doc.get("sales_invoice"):
		frappe.throw("Nao e possivel entregar sem nota emitida.")

	status = frappe.db.get_value("Sales Invoice", doc.sales_invoice, "status")
	if status != "Paid":
		frappe.throw("A nota precisa estar paga antes da entrega.")
