"""Idempotent Tecponto branding for Frappe-rendered pages."""

from __future__ import annotations

import frappe


FAVICON_PATH = "/assets/tecponto_app/branding/favicon.ico"


def ensure_branding_assets() -> None:
	"""Point Frappe's shared Website Settings at the app-owned favicon."""
	if not frappe.db.exists("Website Settings", "Website Settings"):
		return

	frappe.db.set_value(
		"Website Settings",
		"Website Settings",
		"favicon",
		FAVICON_PATH,
		update_modified=False,
	)
	frappe.clear_cache(doctype="Website Settings")
