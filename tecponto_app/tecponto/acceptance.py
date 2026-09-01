from __future__ import annotations

import hashlib
import os
import secrets
from base64 import b64decode

import frappe
from frappe import _
from frappe.twofactor import get_qr_svg_code
from frappe.utils.file_manager import save_file
from frappe.utils import add_to_date, get_url, now_datetime
from tecponto_app.tecponto.service_order.inoperative_device import (
	build_inoperative_device_term,
	public_inoperative_device_term,
	requires_inoperative_device_term,
)
from tecponto_app.tecponto.service_order.customer_supplied_part import (
	build_customer_supplied_part_term,
	requires_customer_supplied_part_term,
)


ACCEPTANCE_TYPES = {"Entrada", "Retirada", "Orçamento"}
SIGNER_ROLES = {"Dono", "Terceiro"}
PENDING_STATUS = "Pendente"
TOKEN_TTL_HOURS = 24
MAX_SELFIE_BYTES = 5 * 1024 * 1024
MAX_SIGNATURE_BYTES = 2 * 1024 * 1024
MAX_PHYSICAL_EVIDENCE_BYTES = 10 * 1024 * 1024
LGPD_CONSENT_VERSION = "TECPONTO-ACEITE-1.0"
EVIDENCE_AUDITOR_ROLES = {"System Manager", "Tecponto Gestor", "Tecponto Diretor"}


def issue_acceptance(service_order: str, acceptance_type: str, signer_role: str = "Dono") -> dict:
	"""Issue a one-time public link without ever persisting the raw token."""
	service_order = (service_order or "").strip()
	acceptance_type = (acceptance_type or "").strip()
	signer_role = (signer_role or "Dono").strip()
	if acceptance_type not in ACCEPTANCE_TYPES or signer_role not in SIGNER_ROLES:
		frappe.throw(_("Dados do aceite inválidos."), frappe.ValidationError)

	order = frappe.get_doc("Service Order", service_order)
	order.check_permission("read")
	if signer_role == "Terceiro" and (not order.get("picked_up_by") or not order.get("picked_up_doc") or not order.get("third_party_auth")):
		frappe.throw(_("Registre nome, documento e autorização do terceiro antes de emitir o aceite."), frappe.ValidationError)
	frappe.db.set_value(
		"OS Acceptance",
		{"service_order": order.name, "acceptance_type": acceptance_type, "status": PENDING_STATUS},
		"status",
		"Invalidado",
		update_modified=False,
	)

	token = secrets.token_urlsafe(32)
	term = build_inoperative_device_term(order) if acceptance_type == "Entrada" and requires_inoperative_device_term(order) else None
	customer_part_term = build_customer_supplied_part_term(order) if acceptance_type == "Orçamento" and requires_customer_supplied_part_term(order) else None
	doc = frappe.get_doc(
		{
			"doctype": "OS Acceptance",
			"service_order": order.name,
			"acceptance_type": acceptance_type,
			"acceptance_method": "Digital",
			"signer_role": signer_role,
			"status": PENDING_STATUS,
			"token_hash": _token_hash(token),
			"expires_on": add_to_date(now_datetime(), hours=TOKEN_TTL_HOURS),
			"issued_by": frappe.session.user,
			"signer_name": order.get("picked_up_by") if signer_role == "Terceiro" else "",
			"signer_document": order.get("picked_up_doc") if signer_role == "Terceiro" else "",
			"signer_authorization": order.get("third_party_auth") if signer_role == "Terceiro" else "",
			"inoperative_device_term_version": term["version"] if term else "",
			"inoperative_device_term_text": term["text"] if term else "",
			"customer_part_term_version": customer_part_term["version"] if customer_part_term else "",
			"customer_part_term_text": customer_part_term["text"] if customer_part_term else "",
		}
	)
	doc.insert(ignore_permissions=True)
	link = f"{get_url()}/tecponto/aceite/{token}"
	# Frappe's helper already returns the SVG encoded in base64.
	qr_svg = get_qr_svg_code(link).decode()
	return {
		"acceptance": doc.name,
		"acceptance_type": doc.acceptance_type,
		"expires_on": str(doc.expires_on),
		"link": link,
		"qr_svg": f"data:image/svg+xml;base64,{qr_svg}",
	}


def record_physical_acceptance(
	service_order: str,
	acceptance_type: str,
	file_data: str,
	file_name: str,
	*,
	inoperative_term_consent: int | bool = False,
	customer_part_term_consent: int | bool = False,
) -> dict:
	"""Archive a real signed paper copy as a private, immutable acceptance evidence.

	This deliberately never manufactures digital evidence: no selfie, signature
	canvas or LGPD consent fields are populated for the physical method.
	"""
	service_order = (service_order or "").strip()
	acceptance_type = (acceptance_type or "").strip()
	if acceptance_type not in ACCEPTANCE_TYPES:
		frappe.throw(_("Tipo de aceite inválido."), frappe.ValidationError)
	order = frappe.get_doc("Service Order", service_order)
	order.check_permission("read")
	content, extension = _decode_physical_evidence(file_data, file_name)
	term = build_inoperative_device_term(order) if acceptance_type == "Entrada" and requires_inoperative_device_term(order) else None
	customer_part_term = build_customer_supplied_part_term(order) if acceptance_type == "Orçamento" and requires_customer_supplied_part_term(order) else None
	if term and not frappe.utils.cint(inoperative_term_consent):
		frappe.throw(_("Confirme o termo adicional antes de arquivar o aceite físico."), frappe.ValidationError)
	if customer_part_term and not frappe.utils.cint(customer_part_term_consent):
		frappe.throw(_("Confirme o termo da peça do cliente antes de arquivar o aceite físico."), frappe.ValidationError)

	# A physical copy supersedes only a pending copy of the same legal action.
	frappe.db.set_value(
		"OS Acceptance",
		{"service_order": order.name, "acceptance_type": acceptance_type, "status": PENDING_STATUS},
		"status",
		"Invalidado",
		update_modified=False,
	)
	previous_user = frappe.session.user
	try:
		# The authenticated operator is authorized for this single private file,
		# scoped to the selected OS.  It is not a guest upload path.
		frappe.set_user("Administrator")
		file_doc = save_file(
			f"aceite-fisico-{order.name}-{secrets.token_hex(6)}.{extension}",
			content,
			dt="Service Order",
			dn=order.name,
			is_private=1,
		)
	finally:
		if previous_user:
			frappe.set_user(previous_user)
	_assert_private_evidence_file(file_doc, order.name, "via física assinada")
	accepted_on = now_datetime()
	doc = frappe.get_doc(
		{
			"doctype": "OS Acceptance",
			"service_order": order.name,
			"acceptance_type": acceptance_type,
			"acceptance_method": "Físico",
			"signer_role": "Dono",
			"status": "Concluído",
			"token_hash": _token_hash(secrets.token_urlsafe(32)),
			"expires_on": accepted_on,
			"issued_by": previous_user or "Administrator",
			"physical_evidence_file": file_doc.name,
			"physical_evidence_hash": hashlib.sha256(content).hexdigest(),
			"physical_collected_by": previous_user or "Administrator",
			"physical_collected_on": accepted_on,
			"inoperative_device_term_version": term["version"] if term else "",
			"inoperative_device_term_text": term["text"] if term else "",
			"inoperative_device_term_accepted_on": accepted_on if term else None,
			"customer_part_term_version": customer_part_term["version"] if customer_part_term else "",
			"customer_part_term_text": customer_part_term["text"] if customer_part_term else "",
			"customer_part_term_accepted_on": accepted_on if customer_part_term else None,
			"used_on": accepted_on,
		}
	)
	doc.insert(ignore_permissions=True)
	_assert_acceptance_evidence(doc)
	if acceptance_type == "Entrada":
		from tecponto_app.tecponto.service_order.assignment import advance_auto_assigned_entry

		advance_auto_assigned_entry(order.name)
	return {"completed": True, "acceptance": doc.name, "acceptance_type": acceptance_type, "method": "physical"}


def issue_budget_acceptance_from_tracking(tracking, identity_document: str) -> dict:
	"""Create a one-time budget-approval acceptance after server-side identity proof.

	The tracking token grants public *viewing* access. The customer must additionally
	match the CPF/RG held on the Customer record before we issue the separate selfie
	and signature token for a financially relevant approval.
	"""
	order = frappe.get_doc("Service Order", tracking.service_order)
	if order.get("workflow_state") != "Aguardando aprovação":
		frappe.throw(_("Este orçamento não está mais disponível para decisão."), frappe.ValidationError)
	if order.get("approval_deadline") and order.approval_deadline <= now_datetime():
		frappe.throw(_("O prazo de aprovação deste orçamento expirou."), frappe.ValidationError)

	document_type = _validate_customer_identity(order.customer, identity_document)
	frappe.db.set_value(
		"OS Acceptance",
		{"service_order": order.name, "acceptance_type": "Orçamento", "status": PENDING_STATUS},
		"status",
		"Invalidado",
		update_modified=False,
	)

	token = secrets.token_urlsafe(32)
	customer_part_term = build_customer_supplied_part_term(order) if requires_customer_supplied_part_term(order) else None
	doc = frappe.get_doc(
		{
			"doctype": "OS Acceptance",
			"service_order": order.name,
			"acceptance_type": "Orçamento",
			"acceptance_method": "Digital",
			"signer_role": "Dono",
			"status": PENDING_STATUS,
			"token_hash": _token_hash(token),
			"expires_on": _budget_acceptance_expiry(order, tracking),
			"issued_by": tracking.issued_by,
			"tracking_link": tracking.name,
			"budget_version": int(order.get("budget_version") or 1),
			"identity_document_type": document_type,
			"identity_verified_on": now_datetime(),
			"customer_part_term_version": customer_part_term["version"] if customer_part_term else "",
			"customer_part_term_text": customer_part_term["text"] if customer_part_term else "",
		}
	)
	doc.insert(ignore_permissions=True)
	link = f"{get_url()}/tecponto/aceite/{token}"
	return {
		"acceptance": doc.name,
		"acceptance_type": doc.acceptance_type,
		"expires_on": str(doc.expires_on),
		"link": link,
	}


def issue_portal_acceptance(tracking, acceptance_type: str, identity_document: str) -> dict:
	"""Issue a one-time entry/pickup acceptance from an already validated portal.

	The portal link remains the customer's durable URL. This short token is only
	used to capture the selfie and signature for one legally relevant action.
	"""
	if acceptance_type not in {"Entrada", "Retirada"}:
		frappe.throw(_("Tipo de aceite público inválido."), frappe.ValidationError)
	order = frappe.get_doc("Service Order", tracking.service_order)
	state = order.get("workflow_state") or "Entrada criada"
	if acceptance_type == "Entrada" and state != "Entrada criada":
		frappe.throw(_("O aceite de entrada não está mais disponível."), frappe.ValidationError)
	if acceptance_type == "Retirada" and state != "Pronto para retirada":
		frappe.throw(_("O aceite de retirada não está mais disponível."), frappe.ValidationError)

	document_type = _validate_customer_identity(order.customer, identity_document)
	frappe.db.set_value(
		"OS Acceptance",
		{"service_order": order.name, "acceptance_type": acceptance_type, "status": PENDING_STATUS},
		"status",
		"Invalidado",
		update_modified=False,
	)
	token = secrets.token_urlsafe(32)
	term = build_inoperative_device_term(order) if acceptance_type == "Entrada" and requires_inoperative_device_term(order) else None
	doc = frappe.get_doc(
		{
			"doctype": "OS Acceptance",
			"service_order": order.name,
			"acceptance_type": acceptance_type,
			"acceptance_method": "Digital",
			"signer_role": "Dono",
			"status": PENDING_STATUS,
			"token_hash": _token_hash(token),
			"expires_on": add_to_date(now_datetime(), hours=TOKEN_TTL_HOURS),
			"issued_by": tracking.issued_by,
			"tracking_link": tracking.name,
			"identity_document_type": document_type,
			"identity_verified_on": now_datetime(),
			"inoperative_device_term_version": term["version"] if term else "",
			"inoperative_device_term_text": term["text"] if term else "",
		}
	)
	doc.insert(ignore_permissions=True)
	return {"acceptance": doc.name, "acceptance_type": acceptance_type, "expires_on": str(doc.expires_on), "link": f"{get_url()}/tecponto/aceite/{token}"}


@frappe.whitelist(allow_guest=True)
def get_public_acceptance(token: str) -> dict:
	"""Return the small read-only public projection for a valid acceptance link."""
	doc = _get_valid_acceptance(token)
	if not doc:
		return {"valid": False, "message": "Este link de aceite não está disponível. Peça um novo link à empresa responsável."}

	order = frappe.get_doc("Service Order", doc.service_order)
	from tecponto_app.tecponto.company_identity import get_company_identity

	return {
		"valid": True,
		"acceptance": {
			"type": doc.acceptance_type,
			"signer_role": doc.signer_role,
			"expires_on": str(doc.expires_on),
			"selfie_captured": bool(doc.selfie_file),
			"selfie_exception": bool(doc.selfie_exception),
			"inoperative_device_term": (
				{
					"version": doc.inoperative_device_term_version,
					"text": public_inoperative_device_term(doc.inoperative_device_term_text, order),
				}
				if doc.inoperative_device_term_version
				else None
			),
			"customer_part_term": (
				{"version": doc.customer_part_term_version, "text": doc.customer_part_term_text}
				if doc.customer_part_term_version
				else None
			),
		},
		"service_order": _public_order_summary(order, doc.acceptance_type),
		"identity": get_company_identity(),
		"lgpd_notice": {
			"version": LGPD_CONSENT_VERSION,
			"text": "[MINUTA — revisar com advogado] Autorizo a coleta de selfie e assinatura para comprovar este aceite, prevenir fraudes e resguardar o atendimento. Os registros serão mantidos pelo prazo aplicável ao atendimento, obrigações legais e defesa de direitos.",
		},
	}


@frappe.whitelist(allow_guest=True)
def save_public_acceptance_selfie(token: str, image_data: str) -> dict:
	"""Persist one camera-captured selfie as a private attachment on the Service Order."""
	doc = _get_valid_acceptance(token)
	if not doc:
		frappe.throw(_("Este link de aceite não está disponível. Peça um novo link à empresa responsável."), frappe.PermissionError)
	if doc.selfie_file:
		frappe.throw(_("A selfie deste aceite já foi registrada."), frappe.ValidationError)

	content = _decode_camera_selfie(image_data)
	previous_user = frappe.session.user
	try:
		# The guest token authorizes this narrowly-scoped private attachment.
		# Frappe's File validation requires an internal user for private files.
		frappe.set_user("Administrator")
		file_doc = save_file(
			f"selfie-{doc.name}.jpg",
			content,
			dt="Service Order",
			dn=doc.service_order,
			is_private=1,
		)
	finally:
		# Public requests normally run as Guest; shell calls may have no user context.
		if previous_user:
			frappe.set_user(previous_user)
	_assert_private_evidence_file(file_doc, doc.service_order, "selfie")
	doc.db_set("selfie_file", file_doc.name, update_modified=False)
	return {"saved": True, "acceptance": doc.name}


@frappe.whitelist(allow_guest=True)
def complete_public_acceptance(
	token: str,
	signature_data: str,
	lgpd_consent: int | bool = False,
	inoperative_term_consent: int | bool = False,
	customer_part_term_consent: int | bool = False,
) -> dict:
	"""Complete one acceptance after the live selfie, signature, and explicit consent."""
	doc = _get_valid_acceptance(token)
	if not doc:
		frappe.throw(_("Este link de aceite não está disponível. Peça um novo link à empresa responsável."), frappe.PermissionError)
	if not doc.selfie_file and not doc.selfie_exception:
		frappe.throw(_("Capture a selfie antes de concluir o aceite."), frappe.ValidationError)
	if not doc.selfie_exception:
		_assert_private_evidence_file(doc.selfie_file, doc.service_order, "selfie")
	if not frappe.utils.cint(lgpd_consent):
		frappe.throw(_("Confirme o consentimento LGPD para concluir o aceite."), frappe.ValidationError)
	if doc.inoperative_device_term_version and not frappe.utils.cint(inoperative_term_consent):
		frappe.throw(_("Confirme o termo adicional sobre o aparelho sem funcionamento para concluir o aceite."), frappe.ValidationError)
	if doc.customer_part_term_version and not frappe.utils.cint(customer_part_term_consent):
		frappe.throw(_("Confirme o termo sobre a peça fornecida pelo cliente para concluir o aceite."), frappe.ValidationError)

	# Lock the pending row so a duplicated final click cannot consume the same token twice.
	frappe.db.sql("select name from `tabOS Acceptance` where name=%s for update", doc.name)
	doc.reload()
	if doc.status != PENDING_STATUS or doc.expires_on <= now_datetime():
		if doc.status == PENDING_STATUS:
			doc.db_set("status", "Expirado", update_modified=False)
		frappe.throw(_("Este aceite já foi concluído ou não está mais disponível."), frappe.ValidationError)

	signature = _decode_signature(signature_data)
	previous_user = frappe.session.user
	try:
		# The token was validated above; this is limited to its signature attachment.
		frappe.set_user("Administrator")
		signature_file = save_file(
			f"signature-{doc.name}.png",
			signature["content"],
			dt="Service Order",
			dn=doc.service_order,
			is_private=1,
		)
	finally:
		# Public requests normally run as Guest; shell calls may have no user context.
		if previous_user:
			frappe.set_user(previous_user)
	_assert_private_evidence_file(signature_file, doc.service_order, "assinatura")
	accepted_on = now_datetime()
	try:
		request = frappe.local.request
		client_ip = getattr(request, "remote_addr", "") or ""
		user_agent = frappe.get_request_header("User-Agent") or ""
	except (AttributeError, RuntimeError):
		# Direct bench tests do not bind an HTTP request; production calls always do.
		client_ip = ""
		user_agent = ""

	if doc.acceptance_type in {"Entrada", "Retirada"}:
		order_field = "entry_signature" if doc.acceptance_type == "Entrada" else "customer_signature"
		frappe.db.set_value(
			"Service Order",
			doc.service_order,
			{order_field: signature["data_url"]},
			update_modified=True,
		)
	frappe.db.set_value(
		"OS Acceptance",
		doc.name,
		{
			"signature_file": signature_file.name,
			"consent_version": LGPD_CONSENT_VERSION,
			"consented_on": accepted_on,
			"inoperative_device_term_accepted_on": accepted_on if doc.inoperative_device_term_version else None,
			"customer_part_term_accepted_on": accepted_on if doc.customer_part_term_version else None,
			"accepted_ip": client_ip,
			"accepted_user_agent": user_agent[:500],
			"used_on": accepted_on,
			"status": "Concluído",
		},
		update_modified=False,
	)
	if doc.acceptance_type == "Orçamento":
		# The approval is deliberately executed only after identity, selfie, signature
		# and consent have all been persisted on this one-time acceptance record.
		from tecponto_app.tecponto.tracking import complete_tracking_budget_acceptance

		complete_tracking_budget_acceptance(doc)
	elif doc.acceptance_type == "Entrada":
		from tecponto_app.tecponto.service_order.assignment import advance_auto_assigned_entry

		advance_auto_assigned_entry(doc.service_order)
	return {"completed": True, "acceptance": doc.name, "service_order": doc.service_order, "acceptance_type": doc.acceptance_type}


def assert_completed_acceptance_evidence(service_order: str, acceptance_type: str, *, required: bool = False) -> None:
	"""Fail closed when a completed public acceptance lost its private evidence file."""
	acceptance_name = frappe.db.get_value(
		"OS Acceptance",
		{"service_order": service_order, "acceptance_type": acceptance_type, "status": "Concluído"},
		"name",
		order_by="used_on desc",
	)
	if not acceptance_name:
		if required:
			frappe.throw(
				_("O aceite por link de {0} precisa ser concluído antes de avançar a OS.").format(acceptance_type),
				frappe.ValidationError,
			)
		# OS created before the link-acceptance rollout remain valid legacy records.
		return

	acceptance = frappe.get_doc("OS Acceptance", acceptance_name)
	_assert_acceptance_evidence(acceptance)


def has_completed_physical_acceptance(service_order: str, acceptance_type: str) -> bool:
	"""Return true only for an intact archived paper acceptance."""
	name = frappe.db.get_value(
		"OS Acceptance",
		{
			"service_order": service_order,
			"acceptance_type": acceptance_type,
			"acceptance_method": "Físico",
			"status": "Concluído",
		},
		"name",
		order_by="used_on desc",
	)
	if not name:
		return False
	_assert_acceptance_evidence(frappe.get_doc("OS Acceptance", name))
	return True


def assert_completed_inoperative_device_term(service_order: str) -> None:
	"""Require the extra legal acknowledgement when the entry condition demands it."""
	acceptance_name = frappe.db.get_value(
		"OS Acceptance",
		{"service_order": service_order, "acceptance_type": "Entrada", "status": "Concluído"},
		"name",
		order_by="used_on desc",
	)
	if not acceptance_name:
		frappe.throw(_("O aceite adicional de aparelho sem funcionamento é obrigatório antes de avançar a OS."), frappe.ValidationError)
	acceptance = frappe.get_doc("OS Acceptance", acceptance_name)
	if not (
		acceptance.inoperative_device_term_version
		and acceptance.inoperative_device_term_text
		and acceptance.inoperative_device_term_accepted_on
	):
		frappe.throw(_("O termo adicional de aparelho sem funcionamento ainda não foi aceito."), frappe.ValidationError)


def assert_completed_customer_supplied_part_term(service_order: str) -> None:
	"""A customer-supplied part must be acknowledged on the budget acceptance."""
	acceptance_name = frappe.db.get_value(
		"OS Acceptance",
		{"service_order": service_order, "acceptance_type": "Orçamento", "status": "Concluído"},
		"name",
		order_by="used_on desc",
	)
	if not acceptance_name:
		frappe.throw(_("O termo da peça fornecida pelo cliente é obrigatório antes de aprovar o orçamento."), frappe.ValidationError)
	acceptance = frappe.get_doc("OS Acceptance", acceptance_name)
	if not (
		acceptance.customer_part_term_version
		and acceptance.customer_part_term_text
		and acceptance.customer_part_term_accepted_on
	):
		frappe.throw(_("O termo da peça fornecida pelo cliente ainda não foi aceito."), frappe.ValidationError)


@frappe.whitelist()
def audit_completed_acceptance_evidence(service_order: str | None = None) -> dict:
	"""Read-only integrity audit for completed link acceptances.

	Managers can run this before go-live or after storage maintenance to find legal
	evidence rows whose private File record or physical attachment no longer exists.
	It never exposes the file content or changes acceptance state.
	"""
	_require_evidence_auditor()
	filters = {"status": "Concluído"}
	if service_order:
		filters["service_order"] = service_order.strip()
	rows = frappe.get_all(
		"OS Acceptance",
		filters=filters,
		fields=["name", "service_order", "acceptance_type"],
		order_by="used_on desc",
	)
	issues = []
	for row in rows:
		try:
			_assert_acceptance_evidence(frappe.get_doc("OS Acceptance", row.name))
		except frappe.ValidationError as error:
			issues.append(
				{
					"acceptance": row.name,
					"acceptance_type": row.acceptance_type,
					"reason": str(error),
					"service_order": row.service_order,
				}
			)
	return {"checked": len(rows), "issues": issues, "valid": len(rows) - len(issues)}


def _assert_acceptance_evidence(acceptance) -> None:
	if acceptance.get("acceptance_method") == "Físico":
		file_doc = _assert_private_evidence_file(acceptance.physical_evidence_file, acceptance.service_order, "via física assinada")
		if not acceptance.get("physical_evidence_hash"):
			frappe.throw(_("O hash da via física assinada não está disponível."), frappe.ValidationError)
		with open(file_doc.get_full_path(), "rb") as evidence_file:
			if hashlib.sha256(evidence_file.read()).hexdigest() != acceptance.physical_evidence_hash:
				frappe.throw(_("A integridade da via física assinada não pôde ser confirmada."), frappe.ValidationError)
		return
	_assert_private_evidence_file(acceptance.signature_file, acceptance.service_order, "assinatura")
	if not frappe.utils.cint(acceptance.selfie_exception):
		_assert_private_evidence_file(acceptance.selfie_file, acceptance.service_order, "selfie")


def _require_evidence_auditor() -> None:
	if frappe.session.user == "Administrator" or EVIDENCE_AUDITOR_ROLES & set(frappe.get_roles()):
		return
	frappe.throw(_("Somente Gestor, Diretor ou System Manager pode auditar evidências de aceite."), frappe.PermissionError)


def _assert_private_evidence_file(file_reference, service_order: str, evidence_label: str) -> None:
	"""Prove that a legal-evidence File is private, scoped to its OS and on disk."""
	if not file_reference:
		frappe.throw(
			_("A prova de {0} não está disponível. Gere um novo link de aceite.").format(evidence_label),
			frappe.ValidationError,
		)
	file_doc = file_reference if getattr(file_reference, "doctype", None) == "File" else frappe.get_doc("File", file_reference)
	if (
		not file_doc.is_private
		or file_doc.attached_to_doctype != "Service Order"
		or file_doc.attached_to_name != service_order
		or not os.path.isfile(file_doc.get_full_path())
	):
		frappe.throw(
			_("A prova de {0} não pôde ser validada. Gere um novo link de aceite.").format(evidence_label),
			frappe.ValidationError,
		)
	return file_doc


def _get_valid_acceptance(token: str):
	token = (token or "").strip()
	if len(token) < 24:
		return None
	name = frappe.db.get_value("OS Acceptance", {"token_hash": _token_hash(token)}, "name")
	if not name:
		return None
	doc = frappe.get_doc("OS Acceptance", name)
	if doc.status != PENDING_STATUS:
		return None
	if doc.expires_on <= now_datetime():
		doc.db_set("status", "Expirado", update_modified=False)
		return None
	return doc


def _public_order_summary(order, acceptance_type: str) -> dict:
	device = frappe.db.get_value(
		"Customer Device",
		order.customer_device,
		["brand", "model", "color", "imei_serial"],
		as_dict=True,
	) if order.customer_device else {}
	return {
		"number": order.name,
		"type": acceptance_type,
		"customer": frappe.db.get_value("Customer", order.customer, "customer_name") or "Cliente",
		"device": " ".join(part for part in [device.get("brand"), device.get("model"), device.get("color")] if part) or "Aparelho não informado",
		"imei_suffix": _imei_suffix(device.get("imei_serial")),
		"reported_defect": order.get("reported_defect") or "Não informado",
		"physical_state": order.get("physical_state") or "Não informado",
		"entry_operating_condition": order.get("entry_operating_condition") or "Liga e permite teste",
		"accessories_received": order.get("accessories_received") or "Nenhum acessório informado",
	}


def _imei_suffix(imei: str | None) -> str:
	value = (imei or "").strip()
	return f"•••• {value[-4:]}" if value else "Não informado"


def _budget_acceptance_expiry(order, tracking):
	"""The second-factor link cannot outlive either the quote or tracking link."""
	expires = add_to_date(now_datetime(), hours=TOKEN_TTL_HOURS)
	for candidate in (order.get("approval_deadline"), tracking.get("expires_on")):
		if candidate and candidate < expires:
			expires = candidate
	return expires


def _validate_customer_identity(customer_name: str, identity_document: str) -> str:
	provided_digits = _digits(identity_document)
	provided_rg = _normalise_rg(identity_document)
	customer = frappe.db.get_value(
		"Customer",
		customer_name,
		["custom_cpf", "custom_rg"],
		as_dict=True,
	) or {}
	if provided_digits and provided_digits == _digits(customer.get("custom_cpf")):
		return "CPF"
	if provided_rg and provided_rg == _normalise_rg(customer.get("custom_rg")):
		return "RG"
	# Keep this intentionally neutral: a public link must not disclose which
	# document exists or any fragment of it.
	frappe.throw(_("Não foi possível validar o documento informado. Confira e tente novamente."), frappe.PermissionError)


def _digits(value: str | None) -> str:
	return "".join(character for character in (value or "") if character.isdigit())


def _normalise_rg(value: str | None) -> str:
	return "".join(character for character in (value or "").upper() if character.isalnum())


def _token_hash(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


def _decode_camera_selfie(image_data: str) -> bytes:
	"""Allow only the JPEG data URL produced by the in-page camera canvas."""
	prefix = "data:image/jpeg;base64,"
	if not isinstance(image_data, str) or not image_data.startswith(prefix):
		frappe.throw(_("Envie uma selfie capturada pela câmera."), frappe.ValidationError)
	try:
		content = b64decode(image_data[len(prefix):], validate=True)
	except ValueError:
		frappe.throw(_("A imagem capturada é inválida."), frappe.ValidationError)
	if len(content) < 256 or len(content) > MAX_SELFIE_BYTES or not content.startswith(b"\xff\xd8\xff"):
		frappe.throw(_("A imagem capturada é inválida."), frappe.ValidationError)
	return content


def _decode_signature(signature_data: str) -> dict:
	"""Validate the PNG data URL produced by the in-page signature canvas."""
	prefix = "data:image/png;base64,"
	if not isinstance(signature_data, str) or not signature_data.startswith(prefix):
		frappe.throw(_("Assine no quadro para concluir o aceite."), frappe.ValidationError)
	try:
		content = b64decode(signature_data[len(prefix):], validate=True)
	except ValueError:
		frappe.throw(_("A assinatura capturada é inválida."), frappe.ValidationError)
	if len(content) < 256 or len(content) > MAX_SIGNATURE_BYTES or not content.startswith(b"\x89PNG\r\n\x1a\n"):
		frappe.throw(_("A assinatura capturada é inválida."), frappe.ValidationError)
	return {"content": content, "data_url": signature_data}


def _decode_physical_evidence(file_data: str, file_name: str) -> tuple[bytes, str]:
	"""Allow a scanned physical signature as JPEG, PNG or PDF only."""
	if not isinstance(file_data, str) or ";base64," not in file_data:
		frappe.throw(_("Envie a foto ou PDF da via física assinada."), frappe.ValidationError)
	prefix, encoded = file_data.split(";base64,", 1)
	allowed = {
		"data:image/jpeg": ("jpg", b"\xff\xd8\xff"),
		"data:image/png": ("png", b"\x89PNG\r\n\x1a\n"),
		"data:application/pdf": ("pdf", b"%PDF-"),
	}
	if prefix not in allowed:
		frappe.throw(_("A via física deve ser JPEG, PNG ou PDF."), frappe.ValidationError)
	try:
		content = b64decode(encoded, validate=True)
	except ValueError:
		frappe.throw(_("O arquivo da via física é inválido."), frappe.ValidationError)
	extension, magic = allowed[prefix]
	if len(content) < 128 or len(content) > MAX_PHYSICAL_EVIDENCE_BYTES or not content.startswith(magic):
		frappe.throw(_("O arquivo da via física é inválido."), frappe.ValidationError)
	return content, extension
