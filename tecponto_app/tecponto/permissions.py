from contextlib import contextmanager

import frappe


PRIVILEGED_SERVICE_ORDER_ROLES = {
	"System Manager",
	"Tecponto Gestor",
	"Tecponto Diretor",
	"Tecponto Atendente",
}


def is_restricted_technician(user: str | None = None) -> bool:
	"""Return whether a user has only the restricted technical scope.

	A person may accumulate Tecponto roles. In that case the broader real role
	wins; the frontend's unified view must never reduce or fabricate permissions.
	"""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	return "Tecponto Tecnico" in roles and not roles.intersection(PRIVILEGED_SERVICE_ORDER_ROLES)


# Kept as a compatibility alias for any installed custom hooks that imported it
# before the scope helper was made public.
_is_restricted_technician = is_restricted_technician


def service_order_scope_filters(user: str | None = None) -> dict[str, str]:
	"""Explicit query scope for APIs that intentionally use get_all/db.count.

	Frappe's ``get_all`` bypasses permission query conditions, so aggregate APIs
	must carry this scope themselves instead of relying on list permissions.
	"""
	user = user or frappe.session.user
	if user == "Administrator" or not is_restricted_technician(user):
		return {}
	return {"technician": user}


def service_order_query(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	if user == "Administrator" or not is_restricted_technician(user):
		return None

	return f"`tabService Order`.`technician` = {frappe.db.escape(user)}"


def service_order_has_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool | None:
	user = user or frappe.session.user
	if user == "Administrator" or not is_restricted_technician(user):
		return True

	return doc.get("technician") == user


def part_request_query(user: str | None = None) -> str | None:
	"""Technicians may see only the needs they personally registered."""
	user = user or frappe.session.user
	if user == "Administrator" or not is_restricted_technician(user):
		return None
	return f"`tabTecponto Part Request`.`requested_by` = {frappe.db.escape(user)}"


def part_request_has_permission(doc, user: str | None = None, permission_type: str | None = None) -> bool | None:
	user = user or frappe.session.user
	if user == "Administrator" or not is_restricted_technician(user):
		return True
	return doc.get("requested_by") == user


@contextmanager
def as_user(username: str):
	"""Temporarily act as another user for a permission check, without corrupting the session.

	``frappe.set_user()`` is NOT safe to call mid-request and restore afterwards: besides
	swapping ``frappe.session.user``, it also overwrites ``frappe.session.sid`` with the
	plain username and wipes ``frappe.session.data`` (frappe/__init__.py, ``set_user``).
	``frappe.session.sid`` is exactly the value ``frappe/auth.py`` writes into the outgoing
	``Set-Cookie: sid=...`` header at the end of the request — so even a perfectly restored
	``frappe.session.user`` still ships a cookie that no longer matches any real session.
	The browser's next request is rejected with "User None not found" (403). This corrupts
	every one of the caller's requests from that point on, not just this one.

	This helper only ever touches ``frappe.session.user`` (plus the per-request permission
	caches that must be recomputed for the new identity) — never ``.sid`` or ``.data``.
	"""
	session = frappe.session
	saved_user = session.user
	try:
		session.user = username
		frappe.local.role_permissions = {}
		frappe.local.user_perms = None
		frappe.local.cache = {}
		yield
	finally:
		session.user = saved_user
		frappe.local.role_permissions = {}
		frappe.local.user_perms = None
		frappe.local.cache = {}
