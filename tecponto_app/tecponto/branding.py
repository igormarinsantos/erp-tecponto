"""Idempotent Tecponto branding for Frappe-rendered pages."""

from __future__ import annotations

import frappe

from tecponto_app.tecponto.company_identity import get_company_identity


FAVICON_PATH = "/assets/tecponto_app/branding/favicon.ico"


def ensure_branding_assets() -> None:
	"""Point Frappe's shared Website Settings at the configured commercial logo."""
	if not frappe.db.exists("Website Settings", "Website Settings"):
		return

	identity = get_company_identity()
	frappe.db.set_value(
		"Website Settings",
		"Website Settings",
		"favicon",
		identity["logo_url"] or FAVICON_PATH,
		update_modified=False,
	)
	frappe.clear_cache(doctype="Website Settings")
