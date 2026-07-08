from __future__ import annotations

from typing import Any

import frappe
from frappe import _


CUSTOMER_NO_CPF_FIELD = "custom_nao_possui_cpf"


def validate_customer_registration(doc: Any, method: str | None = None) -> None:
	if doc.get("customer_type") and doc.get("customer_type") != "Individual":
		return
	validate_customer_contact_document(doc)


def validate_customer_contact_document(data: Any) -> None:
	customer_name = _value(data, "customer_name")
	phone = _value(data, "mobile_no") or _value(data, "custom_whatsapp")
	cpf = _digits(_value(data, "custom_cpf"))
	rg = _value(data, "custom_rg")
	without_cpf = bool(_value(data, CUSTOMER_NO_CPF_FIELD))

	if not customer_name:
		frappe.throw(_("Nome do cliente é obrigatório."), frappe.ValidationError)
	if not phone:
		frappe.throw(_("Telefone/WhatsApp do cliente é obrigatório."), frappe.ValidationError)
	if _digits(phone) and len(_digits(phone)) < 8:
		frappe.throw(_("Telefone/WhatsApp do cliente deve ter ao menos 8 dígitos."), frappe.ValidationError)
	if without_cpf:
		if not rg:
			frappe.throw(_("Informe o RG quando o cliente não possui CPF."), frappe.ValidationError)
		return
	if not cpf:
		frappe.throw(_("CPF do cliente é obrigatório. Se o cliente não possuir CPF, marque 'Não possui CPF' e informe o RG."), frappe.ValidationError)
	if len(cpf) != 11:
		frappe.throw(_("CPF do cliente deve ter 11 dígitos."), frappe.ValidationError)


def assert_existing_customer_is_complete(customer_name: str) -> None:
	customer = frappe.db.get_value(
		"Customer",
		customer_name,
		["customer_name", "customer_type", "mobile_no", "custom_whatsapp", "custom_cpf", "custom_rg", CUSTOMER_NO_CPF_FIELD],
		as_dict=True,
	)
	if not customer:
		frappe.throw(_("Cliente selecionado não existe."), frappe.ValidationError)
	if customer.get("customer_type") and customer.get("customer_type") != "Individual":
		return
	validate_customer_contact_document(customer)


def _value(data: Any, key: str) -> Any:
	if isinstance(data, dict):
		return (data.get(key) or "").strip() if isinstance(data.get(key), str) else data.get(key)
	value = data.get(key) if hasattr(data, "get") else getattr(data, key, None)
	return (value or "").strip() if isinstance(value, str) else value


def _digits(value: str | None) -> str:
	return "".join(ch for ch in (value or "") if ch.isdigit())
