import frappe

from tecponto_app.tecponto.company_identity import get_company_identity


def get_context(context):
	context.no_cache = 1
	context.no_breadcrumbs = 1
	context.show_sidebar = False
	context.identity = get_company_identity()
	context.title = f"Portal do cliente | {context.identity['display_name']}"
	context.token = frappe.form_dict.get("token", "")
