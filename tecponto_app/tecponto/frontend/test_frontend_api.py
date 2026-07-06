from __future__ import annotations

import frappe

from tecponto_app.tecponto.frontend.api import contains_sensitive_field, get_boot, list_service_orders, resolve_panel
from tecponto_app.tecponto.frontend.setup import FRONTEND_ROLES, ensure_frontend_foundation


TEST_USERS = {
	"Tecponto Atendente": ("front-atendente@tecponto.local", "Atendente Front"),
	"Tecponto Tecnico": ("front-tecnico@tecponto.local", "Técnico Front"),
	"Tecponto Gestor": ("front-gestor@tecponto.local", "Gestor Front"),
	"Tecponto Diretor": ("front-diretor@tecponto.local", "Diretor Front"),
}


def run_foundation_checks() -> dict:
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		users = {role: _find_or_create_user(role) for role in FRONTEND_ROLES}
		panel_checks = _check_role_panels(users)
		orders_check = _check_service_order_api(users["Tecponto Gestor"])
		guard_check = _check_sensitive_guard(users["Tecponto Tecnico"])

		return {
			"status": "ok",
			"panel_checks": panel_checks,
			"service_order_api": orders_check,
			"sensitive_guard": guard_check,
		}
	finally:
		frappe.set_user(previous_user)


def _find_or_create_user(role: str) -> str:
	existing = frappe.get_all(
		"Has Role",
		filters={"role": role, "parenttype": "User"},
		pluck="parent",
		limit_page_length=20,
	)
	for user in existing:
		if user != "Administrator" and frappe.db.get_value("User", user, "enabled"):
			return user

	email, full_name = TEST_USERS[role]
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": full_name.split()[0],
				"last_name": " ".join(full_name.split()[1:]),
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
	user.add_roles(role)
	return user.name


def _check_role_panels(users: dict[str, str]) -> list[dict]:
	results = []
	for role, user in users.items():
		frappe.set_user(user)
		boot = get_boot()
		expected = resolve_panel([role])
		actual = boot["user"]["panel"]
		if actual != expected["panel"]:
			raise AssertionError(f"{user} abriu painel {actual}, esperado {expected['panel']}")
		results.append(
			{
				"user": user,
				"role": role,
				"panel": actual,
				"label": boot["user"]["role_label"],
			}
		)
	return results


def _check_service_order_api(user: str) -> dict:
	frappe.set_user(user)
	total_service_orders = frappe.db.count("Service Order")
	payload = list_service_orders(limit=5)
	if total_service_orders and not payload["items"]:
		raise AssertionError("A API tipada não retornou nenhuma OS apesar de existirem OS no banco.")

	return {
		"user": user,
		"database_count": total_service_orders,
		"returned_count": payload["count"],
		"fields": payload["fields"],
		"first_order": payload["items"][0]["name"] if payload["items"] else None,
	}


def _check_sensitive_guard(user: str) -> dict:
	frappe.set_user(user)
	payload = {
		"boot": get_boot(),
		"service_orders": list_service_orders(limit=20),
	}
	leaks = contains_sensitive_field(payload)
	if leaks:
		raise AssertionError(f"Campos sensíveis vazaram para Técnico: {', '.join(leaks)}")

	return {
		"user": user,
		"checked_payloads": ["get_boot", "list_service_orders"],
		"leaked_fields": leaks,
	}
