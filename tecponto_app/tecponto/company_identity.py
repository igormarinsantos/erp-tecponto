"""Customer-facing company identity resolved from the active ERPNext Company.

The Tecponto app namespace is intentionally fixed. This module is only for
commercial identity shown to customers and operators, so a separate site can
serve another repair business without copying Tecponto's name into its terms.
"""

from __future__ import annotations

import json
import re

import frappe
from frappe.utils import get_url


def get_company_identity(company: str | None = None) -> dict[str, str]:
	"""Return one safe, display-ready identity projection for the active company."""
	settings = frappe.get_single("Tecponto Settings") if frappe.db.exists("DocType", "Tecponto Settings") else None
	company_name = (
		company
		or (settings.get("identity_company") if settings else None)
		or frappe.defaults.get_global_default("company")
		or frappe.db.get_value("Company", {}, "name")
	)
	company_doc = frappe.get_doc("Company", company_name) if company_name and frappe.db.exists("Company", company_name) else None

	legal_name = company_doc.get("company_name") if company_doc else "Empresa"
	display_name = (settings.get("trade_name") if settings else None) or legal_name
	address = (settings.get("public_address") if settings else None) or _company_address(company_doc)
	logo = (settings.get("public_logo") if settings else None) or (company_doc.get("company_logo") if company_doc else "")

	return {
		"company": company_doc.name if company_doc else "",
		"legal_name": legal_name,
		"display_name": display_name,
		"cnpj": company_doc.get("tax_id") if company_doc else "",
		"address": _plain_text(address),
		"phone": (settings.get("public_phone") if settings else None) or (company_doc.get("phone_no") if company_doc else "") or "",
		"email": (settings.get("public_email") if settings else None) or (company_doc.get("email") if company_doc else "") or "",
		"logo_url": _asset_url(logo),
	}


@frappe.whitelist(allow_guest=True)
def get_public_company_identity() -> dict[str, str]:
	"""Guest-safe branding used by the login and public acceptance pages."""
	return get_company_identity()


@frappe.whitelist(allow_guest=True)
def get_pwa_manifest() -> None:
	"""Serve a guest-safe PWA manifest from the same commercial identity source."""
	identity = get_company_identity()
	icon = identity["logo_url"] or "/assets/tecponto_app/branding/android-chrome-192x192.png"
	manifest = {
		"name": identity["display_name"],
		"short_name": identity["display_name"][:24],
		"start_url": "/tecponto",
		"display": "standalone",
		"background_color": "#15181B",
		"theme_color": "#15181B",
		"icons": [
			{"src": icon, "sizes": "192x192", "type": "image/png"},
			{"src": icon, "sizes": "512x512", "type": "image/png"},
		],
	}
	frappe.local.response.filename = "tecponto.webmanifest"
	frappe.local.response.filecontent = json.dumps(manifest)
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"
	frappe.local.response.content_type = "application/manifest+json"


def _asset_url(value: str | None) -> str:
	value = (value or "").strip()
	if not value:
		return ""
	return value if value.startswith(("http://", "https://", "/")) else f"{get_url()}/{value.lstrip('/')}"


def _company_address(company_doc) -> str:
	if not company_doc:
		return ""
	from frappe.contacts.doctype.address.address import get_address_display, get_default_address

	address_name = get_default_address("Company", company_doc.name)
	if not address_name:
		return ""
	return get_address_display(frappe.get_cached_doc("Address", address_name).as_dict()) or ""


def _plain_text(value: str | None) -> str:
	return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()
