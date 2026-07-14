from __future__ import annotations

import hmac
import json
import re
from typing import Any

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import now_datetime
from frappe.utils.password import get_decrypted_password

from tecponto_app.tecponto.stock import normalize_barcode


CASHIER_OPERATOR_DOCTYPE = "Tecponto Cashier Operator"
CASHIER_OPERATOR_FIELD = "custom_tecponto_cashier_operator"
CASHIER_TOKEN_PREFIX = "tecponto:cashier-operator:"
CASHIER_TOKEN_TTL_SECONDS = 12 * 60 * 60
POS_OPERATOR_ROLES = {"Tecponto Atendente", "Tecponto Gestor", "System Manager"}


def ensure_cashier_sales_invoice_field() -> None:
	if not frappe.db.exists("DocType", "Sales Invoice"):
		return
	create_custom_fields(
		{
			"Sales Invoice": [
				{
					"fieldname": CASHIER_OPERATOR_FIELD,
					"fieldtype": "Link",
					"label": "Operador do caixa",
					"options": "User",
					"insert_after": "pos_profile",
					"module": "Tecponto",
					"read_only": 1,
					"allow_on_submit": 1,
				}
			]
		},
		update=True,
	)


def identify_cashier_operator(*, badge_code: str = "", pin: str = "") -> dict[str, str]:
	"""Identify a cashier for sale attribution; this never changes session roles."""
	operator = _find_operator(badge_code=badge_code, pin=pin)
	if not operator:
		frappe.throw("Cracha ou PIN do operador nao encontrado.", frappe.PermissionError)

	user = frappe.db.get_value("User", operator.user, ["enabled", "full_name"], as_dict=True)
	if not user or not user.enabled or not _has_pos_operator_role(operator.user):
		frappe.throw("Este operador nao esta habilitado para vendas no caixa.", frappe.PermissionError)

	token = frappe.generate_hash(length=32)
	payload = {
		"identified_at": now_datetime().isoformat(),
		"identified_by": frappe.session.user,
		"method": "badge" if badge_code else "pin",
		"operator": operator.user,
	}
	frappe.cache.set_value(f"{CASHIER_TOKEN_PREFIX}{token}", json.dumps(payload), expires_in_sec=CASHIER_TOKEN_TTL_SECONDS)
	return {
		"operator": operator.user,
		"operator_name": user.full_name or operator.user,
		"token": token,
		"via": payload["method"],
	}


def resolve_cashier_operator(token: Any) -> dict[str, str] | None:
	"""Resolve a token issued for the current signed-in cashier session only."""
	token = str(token or "").strip()
	if not token:
		return None
	raw = frappe.cache.get_value(f"{CASHIER_TOKEN_PREFIX}{token}")
	if not raw:
		frappe.throw("A identificacao do operador expirou. Bipe o cracha novamente.", frappe.PermissionError)
	try:
		payload = frappe.parse_json(raw) if isinstance(raw, str) else raw
	except (TypeError, ValueError):
		frappe.throw("Identificacao do operador invalida.", frappe.PermissionError)
	if not isinstance(payload, dict):
		frappe.throw("Identificacao do operador invalida.", frappe.PermissionError)
	operator = str(payload.get("operator") or "")
	if not operator or not _has_pos_operator_role(operator):
		frappe.throw("Operador de caixa indisponivel.", frappe.PermissionError)
	return {"operator": operator, "via": str(payload.get("method") or "")}


def _find_operator(*, badge_code: str, pin: str):
	badge_code = normalize_barcode(badge_code)
	pin = str(pin or "").strip()
	if badge_code:
		return frappe.db.get_value(
			CASHIER_OPERATOR_DOCTYPE,
			{"active": 1, "badge_code": badge_code},
			["name", "user", "badge_code"],
			as_dict=True,
		)
	if not re.fullmatch(r"\d{4}", pin):
		frappe.throw("Informe um PIN de 4 digitos.", frappe.ValidationError)
	for operator_name in frappe.get_all(CASHIER_OPERATOR_DOCTYPE, filters={"active": 1}, pluck="name"):
		stored_pin = get_decrypted_password(CASHIER_OPERATOR_DOCTYPE, operator_name, "pin", raise_exception=False)
		if stored_pin and hmac.compare_digest(stored_pin, pin):
			return frappe.db.get_value(CASHIER_OPERATOR_DOCTYPE, operator_name, ["name", "user", "badge_code"], as_dict=True)
	return None


def _has_pos_operator_role(user: str) -> bool:
	return bool(set(frappe.get_roles(user)) & POS_OPERATOR_ROLES)
