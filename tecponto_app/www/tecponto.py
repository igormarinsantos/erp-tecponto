from pathlib import Path

import frappe

from tecponto_app.tecponto.company_identity import get_company_identity


def _frontend_asset_version() -> str:
	app_path = Path(frappe.get_app_path("tecponto_app"))
	asset = app_path / "public" / "frontend" / "assets" / "app.js"
	if asset.exists():
		return str(asset.stat().st_mtime_ns)
	return "local"


def get_context(context):
	context.no_cache = 1
	context.no_breadcrumbs = 1
	context.show_sidebar = False
	context.identity = get_company_identity()
	context.title = context.identity["display_name"]
	context.build_version = _frontend_asset_version()
