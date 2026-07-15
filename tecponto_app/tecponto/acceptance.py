from __future__ import annotations

import hashlib
import secrets
from base64 import b64decode

import frappe
from frappe import _
from frappe.twofactor import get_qr_svg_code
from frappe.utils.file_manager import save_file
from frappe.utils import add_to_date, get_url, now_datetime


ACCEPTANCE_TYPES = {"Entrada", "Retirada"}
SIGNER_ROLES = {"Dono", "Terceiro"}
PENDING_STATUS = "Pendente"
TOKEN_TTL_HOURS = 24
MAX_SELFIE_BYTES = 5 * 1024 * 1024
MAX_SIGNATURE_BYTES = 2 * 1024 * 1024
LGPD_CONSENT_VERSION = "TECPONTO-ACEITE-1.0"


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
	doc = frappe.get_doc(
		{
			"doctype": "OS Acceptance",
			"service_order": order.name,
			"acceptance_type": acceptance_type,
			"signer_role": signer_role,
			"status": PENDING_STATUS,
			"token_hash": _token_hash(token),
			"expires_on": add_to_date(now_datetime(), hours=TOKEN_TTL_HOURS),
			"issued_by": frappe.session.user,
			"signer_name": order.get("picked_up_by") if signer_role == "Terceiro" else "",
			"signer_document": order.get("picked_up_doc") if signer_role == "Terceiro" else "",
			"signer_authorization": order.get("third_party_auth") if signer_role == "Terceiro" else "",
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


@frappe.whitelist(allow_guest=True)
def get_public_acceptance(token: str) -> dict:
	"""Return the small read-only public projection for a valid acceptance link."""
	doc = _get_valid_acceptance(token)
	if not doc:
		return {"valid": False, "message": "Este link de aceite não está disponível. Peça um novo link à Tecponto."}

	order = frappe.get_doc("Service Order", doc.service_order)
	return {
		"valid": True,
		"acceptance": {
			"type": doc.acceptance_type,
			"signer_role": doc.signer_role,
			"expires_on": str(doc.expires_on),
			"selfie_captured": bool(doc.selfie_file),
			"selfie_exception": bool(doc.selfie_exception),
		},
		"service_order": _public_order_summary(order, doc.acceptance_type),
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
		frappe.throw(_("Este link de aceite não está disponível. Peça um novo link à Tecponto."), frappe.PermissionError)
	if doc.selfie_file:
		frappe.throw(_("A selfie deste aceite já foi registrada."), frappe.ValidationError)

	content = _decode_camera_selfie(image_data)
	file_doc = save_file(
		f"selfie-{doc.name}.jpg",
		content,
		dt="Service Order",
		dn=doc.service_order,
		is_private=1,
	)
	doc.db_set("selfie_file", file_doc.name, update_modified=False)
	return {"saved": True, "acceptance": doc.name}


@frappe.whitelist(allow_guest=True)
def complete_public_acceptance(token: str, signature_data: str, lgpd_consent: int | bool = False) -> dict:
	"""Complete one acceptance after the live selfie, signature, and explicit consent."""
	doc = _get_valid_acceptance(token)
	if not doc:
		frappe.throw(_("Este link de aceite não está disponível. Peça um novo link à Tecponto."), frappe.PermissionError)
	if not doc.selfie_file and not doc.selfie_exception:
		frappe.throw(_("Capture a selfie antes de concluir o aceite."), frappe.ValidationError)
	if not frappe.utils.cint(lgpd_consent):
		frappe.throw(_("Confirme o consentimento LGPD para concluir o aceite."), frappe.ValidationError)

	# Lock the pending row so a duplicated final click cannot consume the same token twice.
	frappe.db.sql("select name from `tabOS Acceptance` where name=%s for update", doc.name)
	doc.reload()
	if doc.status != PENDING_STATUS or doc.expires_on <= now_datetime():
		if doc.status == PENDING_STATUS:
			doc.db_set("status", "Expirado", update_modified=False)
		frappe.throw(_("Este aceite já foi concluído ou não está mais disponível."), frappe.ValidationError)

	signature = _decode_signature(signature_data)
	signature_file = save_file(
		f"signature-{doc.name}.png",
		signature["content"],
		dt="Service Order",
		dn=doc.service_order,
		is_private=1,
	)
	accepted_on = now_datetime()
	try:
		request = frappe.local.request
		client_ip = getattr(request, "remote_addr", "") or ""
		user_agent = frappe.get_request_header("User-Agent") or ""
	except (AttributeError, RuntimeError):
		# Direct bench tests do not bind an HTTP request; production calls always do.
		client_ip = ""
		user_agent = ""

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
			"accepted_ip": client_ip,
			"accepted_user_agent": user_agent[:500],
			"used_on": accepted_on,
			"status": "Concluído",
		},
		update_modified=False,
	)
	return {"completed": True, "acceptance": doc.name, "service_order": doc.service_order, "acceptance_type": doc.acceptance_type}


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
		"imei": device.get("imei_serial") or "Não informado",
		"reported_defect": order.get("reported_defect") or "Não informado",
		"physical_state": order.get("physical_state") or "Não informado",
		"accessories_received": order.get("accessories_received") or "Nenhum acessório informado",
	}


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
