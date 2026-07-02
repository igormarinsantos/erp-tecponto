import frappe


PRIVILEGED_SERVICE_ORDER_ROLES = {
	"System Manager",
	"Tecponto Gestor",
	"Tecponto Atendente",
}


def _is_restricted_technician(user: str | None = None) -> bool:
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	return "Tecponto Tecnico" in roles and not roles.intersection(PRIVILEGED_SERVICE_ORDER_ROLES)


def service_order_query(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if user == "Administrator" or not _is_restricted_technician(user):
		return None

	return f"`tabService Order`.`technician` = {frappe.db.escape(user)}"


def service_order_has_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool | None:
	user = user or frappe.session.user
	if user == "Administrator" or not _is_restricted_technician(user):
		return True

	return doc.get("technician") == user
