from __future__ import annotations

from typing import Any

import frappe
from frappe import _


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
