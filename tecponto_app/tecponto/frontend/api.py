from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime, today


ROLE_PANELS = (
	{
		"role": "Tecponto Diretor",
		"panel": "diretor",
		"label": "Diretor",
		"subtitle": "Visão executiva",
	},
	{
		"role": "Tecponto Gestor",
		"panel": "gestor",
		"label": "Gestor",
		"subtitle": "Painel do gestor",
	},
	{
		"role": "Tecponto Tecnico",
		"panel": "tecnico",
		"label": "Técnico",
		"subtitle": "Operação técnica",
	},
	{
		"role": "Tecponto Atendente",
		"panel": "atendente",
		"label": "Atendente",
		"subtitle": "Balcão 01",
	},
)
FRONTEND_ALLOWED_ROLES = {
	"System Manager",
	"Tecponto Atendente",
	"Tecponto Tecnico",
	"Tecponto Gestor",
	"Tecponto Diretor",
}

SAFE_SERVICE_ORDER_FIELDS = (
	"name",
	"customer",
	"customer_device",
	"entry_date",
	"attendant",
	"technician",
	"priority",
	"workflow_state",
	"reported_defect",
	"approval_status",
	"approval_deadline",
	"modified",
)
SAFE_CUSTOMER_FIELDS = (
	"name",
	"customer_name",
	"mobile_no",
	"email_id",
	"modified",
)
SAFE_DEVICE_FIELDS = (
	"name",
	"customer",
	"brand",
	"model",
	"color",
	"imei_serial",
	"capacity",
	"registration_date",
	"modified",
)
SAFE_TRADE_EVALUATION_FIELDS = (
	"name",
	"customer",
	"device_type",
	"evaluated_device_desc",
	"model",
	"imei",
	"physical_state",
	"destination",
	"workflow_state",
	"modified",
)

SENSITIVE_FIELD_NAMES = {
	"actual_qty",
	"base_rate",
	"buying_rate",
	"commission",
	"commission_amount",
	"commission_pct",
	"cost",
	"discount_amount",
	"gross_profit",
	"gross_profit_percent",
	"incoming_rate",
	"labor_total",
	"margin",
	"parts_total",
	"purchase_rate",
	"rate",
	"stock_value",
	"valuation_rate",
}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Faça login para acessar o front da Tecponto."), frappe.PermissionError)


def _require_frontend_role() -> None:
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(FRONTEND_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem papel operacional Tecponto."), frappe.PermissionError)


def _initials(full_name: str, fallback: str) -> str:
	parts = [part for part in (full_name or "").strip().split() if part]
	if not parts:
		return fallback[:2].upper()
	if len(parts) == 1:
		return parts[0][:2].upper()
	return f"{parts[0][0]}{parts[-1][0]}".upper()


def resolve_panel(roles: list[str] | tuple[str, ...] | None = None) -> dict[str, str]:
	roles = set(roles or frappe.get_roles(frappe.session.user))
	for entry in ROLE_PANELS:
		if entry["role"] in roles:
			return entry

	if "System Manager" in roles:
		return {
			"role": "System Manager",
			"panel": "gestor",
			"label": "Gestor",
			"subtitle": "Sala de máquinas",
		}

	return {
		"role": "Guest",
		"panel": "sem_papel",
		"label": "Sem papel Tecponto",
		"subtitle": "Solicite acesso ao gestor",
	}


@frappe.whitelist()
def get_logged_user() -> dict[str, Any]:
	_require_login()
	user = frappe.session.user
	full_name = frappe.db.get_value("User", user, "full_name") or user
	roles = frappe.get_roles(user)
	panel = resolve_panel(roles)

	return {
		"name": user,
		"full_name": full_name,
		"initials": _initials(full_name, user),
		"roles": roles,
		"panel": panel["panel"],
		"role_label": panel["label"],
		"role_name": panel["role"],
		"subtitle": panel["subtitle"],
	}


@frappe.whitelist()
def get_boot() -> dict[str, Any]:
	return {
		"user": get_logged_user(),
		"app": {
			"name": "Tecponto",
			"route": "/tecponto",
			"version": "3.0",
		},
		"panels": [
			{
				"panel": entry["panel"],
				"role": entry["role"],
				"label": entry["label"],
				"subtitle": entry["subtitle"],
			}
			for entry in ROLE_PANELS
		],
	}


@frappe.whitelist()
def list_service_orders(limit: int = 20) -> dict[str, Any]:
	_require_login()
	limit = max(1, min(int(limit or 20), 100))
	items = frappe.get_list(
		"Service Order",
		fields=list(SAFE_SERVICE_ORDER_FIELDS),
		order_by="modified desc",
		limit_page_length=limit,
	)

	return {
		"items": [_serialize_service_order(item) for item in items],
		"count": len(items),
		"fields": list(SAFE_SERVICE_ORDER_FIELDS),
	}


@frappe.whitelist()
def get_dashboard_metrics() -> dict[str, Any]:
	_require_frontend_role()
	service_orders = {
		"total": frappe.db.count("Service Order"),
		"awaiting_approval": frappe.db.count("Service Order", {"workflow_state": "Aguardando aprovação"}),
		"ready_for_pickup": frappe.db.count("Service Order", {"workflow_state": "Pronto para retirada"}),
		"waiting_part": frappe.db.count("Service Order", {"workflow_state": "Aguardando peça"}),
		"new_today": frappe.db.count("Service Order", {"creation": [">=", today()]}),
		"overdue": _count_overdue_service_orders(),
	}
	sales_today_total = frappe.db.sql(
		"""
		select coalesce(sum(grand_total), 0)
		from `tabSales Invoice`
		where docstatus = 1
			and is_return = 0
			and posting_date = %(posting_date)s
		""",
		{"posting_date": today()},
	)[0][0]

	return {
		"sales_today_total": float(sales_today_total or 0),
		"service_orders": service_orders,
	}


@frappe.whitelist()
def search_customers(query: str = "", limit: int = 12) -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit or 12), 50))
	query = (query or "").strip()
	or_filters = _like_filters(
		query,
		("name", "customer_name", "mobile_no", "email_id"),
	)
	items = frappe.get_all(
		"Customer",
		fields=list(SAFE_CUSTOMER_FIELDS),
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=limit,
	)
	return {
		"items": [_serialize_customer(item) for item in items],
		"count": len(items),
		"fields": list(SAFE_CUSTOMER_FIELDS),
	}


@frappe.whitelist()
def list_customer_devices(query: str = "", limit: int = 12) -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit or 12), 50))
	query = (query or "").strip()
	or_filters = _like_filters(
		query,
		("name", "customer", "brand", "model", "imei_serial"),
	)
	items = frappe.get_all(
		"Customer Device",
		fields=list(SAFE_DEVICE_FIELDS),
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=limit,
	)
	return {
		"items": [_serialize_customer_device(item) for item in items],
		"count": len(items),
		"fields": list(SAFE_DEVICE_FIELDS),
	}


@frappe.whitelist()
def list_trade_evaluations(query: str = "", limit: int = 12) -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit or 12), 50))
	query = (query or "").strip()
	or_filters = _like_filters(
		query,
		("name", "customer", "evaluated_device_desc", "model", "imei"),
	)
	items = frappe.get_all(
		"Device Trade Evaluation",
		fields=list(SAFE_TRADE_EVALUATION_FIELDS),
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=limit,
	)
	return {
		"items": [_serialize_trade_evaluation(item) for item in items],
		"count": len(items),
		"fields": list(SAFE_TRADE_EVALUATION_FIELDS),
	}


@frappe.whitelist()
def list_stock_items(query: str = "", limit: int = 12) -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit or 12), 50))
	query = (query or "").strip()
	conditions = [
		"item.disabled = 0",
		"item.is_stock_item = 1",
		"bin.warehouse is not null",
	]
	values: dict[str, Any] = {"limit": limit}
	if query:
		conditions.append(
			"""(
				item.name like %(query)s
				or item.item_name like %(query)s
				or item.item_group like %(query)s
				or bin.warehouse like %(query)s
			)"""
		)
		values["query"] = f"%{query}%"

	rows = frappe.db.sql(
		f"""
		select
			item.name as item_code,
			item.item_name,
			item.item_group,
			bin.warehouse,
			bin.actual_qty as available_qty
		from `tabItem` item
		inner join `tabBin` bin on bin.item_code = item.name
		where {" and ".join(conditions)}
		order by item.modified desc
		limit %(limit)s
		""",
		values,
		as_dict=True,
	)
	return {
		"items": [_serialize_stock_item(item) for item in rows],
		"count": len(rows),
		"fields": ["item_code", "item_name", "item_group", "warehouse", "available_qty"],
	}


def _serialize_service_order(item: dict[str, Any]) -> dict[str, Any]:
	return {
		"name": item.get("name"),
		"customer": item.get("customer"),
		"customer_device": item.get("customer_device"),
		"entry_date": str(item.get("entry_date") or ""),
		"attendant": item.get("attendant"),
		"technician": item.get("technician"),
		"priority": item.get("priority"),
		"workflow_state": item.get("workflow_state"),
		"reported_defect": item.get("reported_defect"),
		"approval_status": item.get("approval_status"),
		"approval_deadline": str(item.get("approval_deadline") or ""),
		"modified": str(item.get("modified") or ""),
	}


def _serialize_customer(item: dict[str, Any]) -> dict[str, Any]:
	return {
		"name": item.get("name"),
		"customer_name": item.get("customer_name"),
		"mobile_no": item.get("mobile_no"),
		"email_id": item.get("email_id"),
		"modified": str(item.get("modified") or ""),
	}


def _serialize_customer_device(item: dict[str, Any]) -> dict[str, Any]:
	return {
		"name": item.get("name"),
		"customer": item.get("customer"),
		"brand": item.get("brand"),
		"model": item.get("model"),
		"color": item.get("color"),
		"imei_serial": item.get("imei_serial"),
		"capacity": item.get("capacity"),
		"registration_date": str(item.get("registration_date") or ""),
		"modified": str(item.get("modified") or ""),
	}


def _serialize_trade_evaluation(item: dict[str, Any]) -> dict[str, Any]:
	return {
		"name": item.get("name"),
		"customer": item.get("customer"),
		"device_type": item.get("device_type"),
		"evaluated_device_desc": item.get("evaluated_device_desc"),
		"model": item.get("model"),
		"imei": item.get("imei"),
		"physical_state": item.get("physical_state"),
		"destination": item.get("destination"),
		"workflow_state": item.get("workflow_state"),
		"modified": str(item.get("modified") or ""),
	}


def _serialize_stock_item(item: dict[str, Any]) -> dict[str, Any]:
	return {
		"item_code": item.get("item_code"),
		"item_name": item.get("item_name"),
		"item_group": item.get("item_group"),
		"warehouse": item.get("warehouse"),
		"available_qty": float(item.get("available_qty") or 0),
	}


def _like_filters(query: str, fields: tuple[str, ...]) -> list[list[str]]:
	if not query:
		return []
	return [[field, "like", f"%{query}%"] for field in fields]


def _count_overdue_service_orders() -> int:
	return frappe.db.count(
		"Service Order",
		{
			"approval_deadline": ["<", now_datetime()],
			"workflow_state": ["not in", ["Entregue", "Cancelada", "Orçamento expirado"]],
		},
	)


def contains_sensitive_field(payload: Any) -> list[str]:
	found: set[str] = set()

	def walk(value: Any) -> None:
		if isinstance(value, dict):
			for key, nested in value.items():
				normalized = key.lower()
				if normalized in SENSITIVE_FIELD_NAMES:
					found.add(key)
				if "cost" in normalized or "margin" in normalized or "commission" in normalized:
					found.add(key)
				walk(nested)
		elif isinstance(value, (list, tuple)):
			for nested in value:
				walk(nested)

	walk(payload)
	return sorted(found)
