from pathlib import Path

import frappe


def _frontend_asset_version() -> str:
	app_path = Path(frappe.get_app_path("tecponto_app"))
	asset = app_path / "public" / "frontend" / "assets" / "app.js"
	if asset.exists():
		return str(asset.stat().st_mtime_ns)
	return "local"


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/tecponto"
		raise frappe.Redirect

	context.no_cache = 1
	context.no_breadcrumbs = 1
	context.show_sidebar = False
	context.title = "Tecponto"
	context.build_version = _frontend_asset_version()
