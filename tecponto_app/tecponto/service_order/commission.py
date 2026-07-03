from __future__ import annotations

import frappe
from frappe.utils import flt, nowdate


DOCTYPE_ADDITIONAL_SALARY = "Additional Salary"
DOCTYPE_SERVICE_ORDER_SERVICE = "Service Order Service"

STATE_PRONTO_RETIRADA = "Pronto para retirada"
SALARY_COMPONENT_COMISSAO = "Comiss\u00e3o"
DEFAULT_COMMISSION_PCT = 20


def gerar_comissao(doc, method=None) -> list[str]:
	if doc.get("is_warranty"):
		return []

	if doc.get("workflow_state") != STATE_PRONTO_RETIRADA:
		return []

	if not doc.get("sales_invoice"):
		return []

	commission_pct = _get_commission_pct()
	commissions = []
	for service_row in doc.get("services") or []:
		commission = _criar_comissao(service_row, doc, commission_pct)
		if commission:
			commissions.append(commission)

	return commissions


def _criar_comissao(service_row, doc, commission_pct: float) -> str | None:
	if not service_row.get("technician"):
		return None

	if flt(service_row.get("qty")) <= 0:
		return None

	amount = flt(service_row.get("rate")) * flt(service_row.get("qty")) * commission_pct / 100
	if amount <= 0:
		return None

	existing = frappe.db.get_value(
		DOCTYPE_ADDITIONAL_SALARY,
		{
			"ref_doctype": DOCTYPE_SERVICE_ORDER_SERVICE,
			"ref_docname": service_row.name,
			"salary_component": SALARY_COMPONENT_COMISSAO,
			"docstatus": ["<", 2],
		},
		"name",
	)
	if existing:
		return existing

	employee = _get_employee(service_row.technician)
	company = _get_employee_company(employee, doc)

	additional_salary = frappe.get_doc(
		{
			"doctype": DOCTYPE_ADDITIONAL_SALARY,
			"employee": employee,
			"company": company,
			"salary_component": SALARY_COMPONENT_COMISSAO,
			"type": "Earning",
			"payroll_date": nowdate(),
			"currency": _get_currency(company),
			"amount": amount,
			"overwrite_salary_structure_amount": 0,
			"ref_doctype": DOCTYPE_SERVICE_ORDER_SERVICE,
			"ref_docname": service_row.name,
		}
	)
	additional_salary.insert(ignore_permissions=True)
	additional_salary.submit()
	return additional_salary.name


def _get_commission_pct() -> float:
	return flt(frappe.db.get_single_value("Tecponto Settings", "commission_pct")) or DEFAULT_COMMISSION_PCT


def _get_employee(technician: str) -> str:
	if frappe.db.exists("Employee", technician):
		return technician

	employee = frappe.db.get_value("Employee", {"user_id": technician, "status": "Active"}, "name")
	if employee:
		return employee

	frappe.throw("Tecnico {0} nao possui Employee ativo para comissao.".format(technician))


def _get_employee_company(employee: str, doc) -> str:
	return (
		frappe.db.get_value("Employee", employee, "company")
		or doc.get("company")
		or frappe.defaults.get_global_default("company")
		or frappe.db.get_value("Company", {}, "name")
	)


def _get_currency(company: str) -> str:
	return (
		frappe.get_cached_value("Company", company, "default_currency")
		or frappe.defaults.get_global_default("currency")
		or "BRL"
	)
