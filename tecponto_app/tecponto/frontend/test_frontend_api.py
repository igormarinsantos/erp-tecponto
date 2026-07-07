from __future__ import annotations

import frappe

from tecponto_app.tecponto.frontend.api import (
	contains_sensitive_field,
	get_dashboard_metrics,
	get_boot,
	list_customer_devices,
	list_service_orders,
	list_stock_items,
	list_trade_evaluations,
	resolve_panel,
	search_customers,
)
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
		navigation_check = _check_attendant_navigation_apis(users["Tecponto Atendente"])
		metrics_check = _check_dashboard_metrics(users["Tecponto Atendente"])
		guard_check = _check_sensitive_guard(users["Tecponto Tecnico"])

		return {
			"status": "ok",
			"panel_checks": panel_checks,
			"service_order_api": orders_check,
			"navigation_apis": navigation_check,
			"dashboard_metrics": metrics_check,
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


def _check_attendant_navigation_apis(user: str) -> dict:
	frappe.set_user(user)
	payload = {
		"customers": search_customers(limit=5),
		"devices": list_customer_devices(limit=5),
		"trade_evaluations": list_trade_evaluations(limit=5),
		"stock_items": list_stock_items(limit=5),
	}
	leaks = contains_sensitive_field(payload)
	if leaks:
		raise AssertionError(f"Campos sensíveis vazaram nas APIs de navegação: {', '.join(leaks)}")

	return {
		"user": user,
		"customers": payload["customers"]["count"],
		"devices": payload["devices"]["count"],
		"trade_evaluations": payload["trade_evaluations"]["count"],
		"stock_items": payload["stock_items"]["count"],
	}


def _check_dashboard_metrics(user: str) -> dict:
	frappe.set_user(user)
	payload = get_dashboard_metrics()
	leaks = contains_sensitive_field(payload)
	if leaks:
		raise AssertionError(f"Campos sensíveis vazaram nas métricas do painel: {', '.join(leaks)}")

	service_orders = payload["service_orders"]
	if not {
		"awaiting_approval",
		"ready_for_pickup",
		"waiting_part",
	}.issubset(service_orders):
		raise AssertionError("Métricas de OS não trouxeram os filtros esperados por status.")

	return {
		"user": user,
		"sales_today_total": payload["sales_today_total"],
		"awaiting_approval": service_orders["awaiting_approval"],
		"ready_for_pickup": service_orders["ready_for_pickup"],
		"waiting_part": service_orders["waiting_part"],
	}


def _check_sensitive_guard(user: str) -> dict:
	frappe.set_user(user)
	payload = {
		"boot": get_boot(),
		"metrics": get_dashboard_metrics(),
		"service_orders": list_service_orders(limit=20),
		"customers": search_customers(limit=5),
		"devices": list_customer_devices(limit=5),
		"trade_evaluations": list_trade_evaluations(limit=5),
		"stock_items": list_stock_items(limit=5),
	}
	leaks = contains_sensitive_field(payload)
	if leaks:
		raise AssertionError(f"Campos sensíveis vazaram para Técnico: {', '.join(leaks)}")

	return {
		"user": user,
		"checked_payloads": [
			"get_boot",
			"get_dashboard_metrics",
			"list_service_orders",
			"search_customers",
			"list_customer_devices",
			"list_trade_evaluations",
			"list_stock_items",
		],
		"leaked_fields": leaks,
	}
