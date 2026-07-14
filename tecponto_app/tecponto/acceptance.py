from __future__ import annotations

import hashlib
import secrets
import frappe
from frappe import _
from frappe.twofactor import get_qr_svg_code
from frappe.utils import add_to_date, get_url, now_datetime


ACCEPTANCE_TYPES = {"Entrada", "Retirada"}
SIGNER_ROLES = {"Dono", "Terceiro"}
PENDING_STATUS = "Pendente"
TOKEN_TTL_HOURS = 24


def issue_acceptance(service_order: str, acceptance_type: str, signer_role: str = "Dono") -> dict:
	"""Issue a one-time public link without ever persisting the raw token."""
	service_order = (service_order or "").strip()
	acceptance_type = (acceptance_type or "").strip()
	signer_role = (signer_role or "Dono").strip()
	if acceptance_type not in ACCEPTANCE_TYPES or signer_role not in SIGNER_ROLES:
		frappe.throw(_("Dados do aceite inválidos."), frappe.ValidationError)

	order = frappe.get_doc("Service Order", service_order)
	order.check_permission("read")
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
		},
		"service_order": _public_order_summary(order, doc.acceptance_type),
		"lgpd_notice": {
			"version": "MINUTA-3.6-1",
			"text": "[MINUTA — revisar com advogado] No próximo passo, a Tecponto solicitará seu consentimento para coletar selfie e assinatura exclusivamente para registrar este aceite e prevenir fraudes. A coleta ocorrerá somente após sua confirmação expressa.",
		},
	}


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
