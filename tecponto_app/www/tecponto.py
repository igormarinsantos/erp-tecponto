import frappe


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/tecponto"
		raise frappe.Redirect

	context.no_cache = 1
	context.no_breadcrumbs = 1
	context.show_sidebar = False
	context.title = "Tecponto"
