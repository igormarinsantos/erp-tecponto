from __future__ import annotations

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.utils import flt, nowdate, nowtime

from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	get_available_qty_to_reserve,
)


DOCTYPE_SERVICE_ORDER = "Service Order"
DOCTYPE_SERVICE_ORDER_PART = "Service Order Part"
DOCTYPE_STOCK_RESERVATION_ENTRY = "Stock Reservation Entry"
DOCTYPE_STOCK_ENTRY = "Stock Entry"
DOCTYPE_ADDITIONAL_SALARY = "Additional Salary"

STATE_AGUARDANDO_APROVACAO = "Aguardando aprova\u00e7\u00e3o"
STATE_APROVADO = "Aprovado"
STATE_REPROVADO = "Reprovado"
STATE_SEM_CONSERTO = "Sem conserto"
STATE_CANCELADO = "Cancelado"
STATES_WITH_RESERVED_PARTS = {
	STATE_APROVADO,
	"Aguardando pe\u00e7a",
	"Em reparo",
	"Teste final",
	"Pronto para retirada",
}
STATES_THAT_RELEASE_RESERVATIONS = {STATE_REPROVADO, STATE_CANCELADO, STATE_SEM_CONSERTO}

APPROVAL_STATUS_APROVADO = "Aprovado"

OUTCOME_USADA = "Usada no reparo"
OUTCOME_PERDIDA = "Perdida"
OUTCOMES_THAT_CONSUME_STOCK = {OUTCOME_USADA, OUTCOME_PERDIDA}

LOSS_LOJA = "Perda da loja"
LOSS_TECNICO = "Responsabilidade do t\u00e9cnico"
LOSS_FORNECEDOR = "Garantia do fornecedor"

SALARY_COMPONENT_PERDA = "D\u00e9bito por perda"
MODULE_TECPONTO = "Tecponto"


def processar_pecas(doc, method=None) -> None:
	reservar_pecas(doc, method=method)

	for part_row in doc.get("parts") or []:
		baixar_peca(part_row, doc)

	liberar_reservas(doc, method=method)


def reservar_pecas(doc, method=None) -> None:
	if not _should_reserve_parts(doc):
		return

	for part_row in doc.get("parts") or []:
		if part_row.get("reservation") or part_row.get("stock_entry"):
			continue

		_validate_stock_part(part_row)
		reservation = _criar_reserva(part_row, doc)
		_set_part_value(part_row, "reservation", reservation)


def baixar_peca(part_row, doc):
	if part_row.get("stock_entry"):
		return part_row.stock_entry

	if part_row.get("outcome") not in OUTCOMES_THAT_CONSUME_STOCK:
		return None

	if part_row.get("outcome") == OUTCOME_PERDIDA and not part_row.get("loss_reason"):
		frappe.throw("Informe o motivo da perda da pe\u00e7a antes de baixar o estoque.")

	_validate_stock_part(part_row)
	_assert_unreserved_part_is_available(part_row)
	_liberar_reserva(part_row.get("reservation"))
	_set_part_value(part_row, "reservation", None)

	stock_entry = _material_issue(part_row, doc)
	_set_part_value(part_row, "stock_entry", stock_entry)

	if not part_row.get("used_date"):
		_set_part_value(part_row, "used_date", nowdate())

	if part_row.get("outcome") == OUTCOME_PERDIDA:
		_rotear_perda(part_row, doc)

	return stock_entry


def liberar_reservas(doc, method=None) -> None:
	if doc.get("workflow_state") not in STATES_THAT_RELEASE_RESERVATIONS:
		return

	for part_row in doc.get("parts") or []:
		if part_row.get("reservation") and not part_row.get("stock_entry"):
			_liberar_reserva(part_row.reservation)
			_set_part_value(part_row, "reservation", None)


def _rotear_perda(part_row, doc) -> None:
	if part_row.get("loss_reason") == LOSS_LOJA:
		return

	if part_row.get("loss_reason") == LOSS_TECNICO:
		_criar_deducao_hr(part_row, doc)
		return

	if part_row.get("loss_reason") == LOSS_FORNECEDOR:
		_marcar_devolucao_fornecedor(part_row, doc)
		return

	frappe.throw("Motivo de perda invalido para a pe\u00e7a.")


def ensure_stock_reservation_for_service_order() -> None:
	if not frappe.db.exists("DocType", DOCTYPE_STOCK_RESERVATION_ENTRY):
		return

	meta = frappe.get_meta(DOCTYPE_STOCK_RESERVATION_ENTRY)
	voucher_type = meta.get_field("voucher_type")
	if not voucher_type:
		return

	options = _append_select_option(voucher_type.options or "", DOCTYPE_SERVICE_ORDER)
	property_setter = make_property_setter(
		DOCTYPE_STOCK_RESERVATION_ENTRY,
		"voucher_type",
		"options",
		options,
		"Text",
		validate_fields_for_doctype=False,
		is_system_generated=False,
	)
	property_setter.module = MODULE_TECPONTO
	property_setter.save(ignore_permissions=True)
	frappe.clear_cache(doctype=DOCTYPE_STOCK_RESERVATION_ENTRY)


def _should_reserve_parts(doc) -> bool:
	return (
		doc.get("workflow_state") in STATES_WITH_RESERVED_PARTS
		or doc.get("approval_status") == APPROVAL_STATUS_APROVADO
	)


def _criar_reserva(part_row, doc) -> str:
	existing_reservation = _get_existing_open_reservation(doc.name, part_row.name)
	if existing_reservation:
		return existing_reservation

	available_qty = flt(get_available_qty_to_reserve(part_row.item_code, part_row.warehouse))
	qty = flt(part_row.qty)
	if available_qty < qty:
		frappe.throw(
			"Estoque disponivel insuficiente para reservar {0}. Disponivel: {1}.".format(
				part_row.item_code,
				frappe.format_value(available_qty, {"fieldtype": "Float"}),
			)
		)

	item_details = _get_item_stock_details(part_row.item_code)
	reservation = frappe.new_doc(DOCTYPE_STOCK_RESERVATION_ENTRY)
	reservation.item_code = part_row.item_code
	reservation.warehouse = part_row.warehouse
	reservation.has_serial_no = item_details.has_serial_no
	reservation.has_batch_no = item_details.has_batch_no
	reservation.voucher_type = DOCTYPE_SERVICE_ORDER
	reservation.voucher_no = doc.name
	reservation.voucher_detail_no = part_row.name
	reservation.available_qty = available_qty
	reservation.voucher_qty = qty
	reservation.reserved_qty = qty
	reservation.company = _get_company(part_row.warehouse)
	reservation.stock_uom = item_details.stock_uom
	reservation.reservation_based_on = "Qty"

	if part_row.get("batch_no"):
		reservation.reservation_based_on = "Serial and Batch"
		reservation.append(
			"sb_entries",
			{
				"batch_no": part_row.batch_no,
				"qty": qty,
				"warehouse": part_row.warehouse,
			},
		)

	reservation.insert(ignore_permissions=True)
	reservation.submit()
	return reservation.name


def _material_issue(part_row, doc) -> str:
	company = _get_company(part_row.warehouse)
	stock_entry = frappe.new_doc(DOCTYPE_STOCK_ENTRY)
	stock_entry.stock_entry_type = _get_stock_entry_type("Material Issue")
	stock_entry.purpose = "Material Issue"
	stock_entry.company = company
	stock_entry.set_posting_time = 1
	stock_entry.posting_date = nowdate()
	stock_entry.posting_time = nowtime()
	stock_entry.remarks = "Baixa de peca da OS {0}, linha {1}.".format(doc.name, part_row.name)

	stock_entry.append(
		"items",
		{
			"item_code": part_row.item_code,
			"qty": flt(part_row.qty),
			"s_warehouse": part_row.warehouse,
			"batch_no": part_row.get("batch_no"),
			"conversion_factor": 1,
			"cost_center": _get_cost_center(company),
			"expense_account": _get_stock_adjustment_account(company),
		},
	)
	stock_entry.insert(ignore_permissions=True)
	stock_entry.submit()
	return stock_entry.name


def _criar_deducao_hr(part_row, doc) -> str | None:
	if not frappe.db.exists("DocType", DOCTYPE_ADDITIONAL_SALARY):
		return None

	if not part_row.get("technician"):
		frappe.throw("Informe o tecnico responsavel pela perda da peca.")

	existing = frappe.db.get_value(
		DOCTYPE_ADDITIONAL_SALARY,
		{
			"ref_doctype": DOCTYPE_SERVICE_ORDER_PART,
			"ref_docname": part_row.name,
			"salary_component": SALARY_COMPONENT_PERDA,
			"docstatus": ["<", 2],
		},
		"name",
	)
	if existing:
		return existing

	employee = frappe.db.get_value("Employee", {"user_id": part_row.technician, "status": "Active"}, "name")
	if not employee:
		frappe.throw("Tecnico {0} nao possui Employee ativo para desconto em folha.".format(part_row.technician))

	additional_salary = frappe.get_doc(
		{
			"doctype": DOCTYPE_ADDITIONAL_SALARY,
			"employee": employee,
			"company": _get_employee_company(employee),
			"salary_component": SALARY_COMPONENT_PERDA,
			"payroll_date": nowdate(),
			"amount": _custo(part_row),
			"overwrite_salary_structure_amount": 0,
			"ref_doctype": DOCTYPE_SERVICE_ORDER_PART,
			"ref_docname": part_row.name,
		}
	)
	additional_salary.insert(ignore_permissions=True)
	additional_salary.submit()
	return additional_salary.name


def _marcar_devolucao_fornecedor(part_row, doc) -> str:
	description = "Abrir devolucao/claim com fornecedor para a peca {0} da OS {1}, linha {2}.".format(
		part_row.item_code,
		doc.name,
		part_row.name,
	)
	existing = frappe.db.get_value(
		"ToDo",
		{
			"reference_type": DOCTYPE_SERVICE_ORDER,
			"reference_name": doc.name,
			"description": description,
			"status": ["!=", "Cancelled"],
		},
		"name",
	)
	if existing:
		return existing

	todo = frappe.get_doc(
		{
			"doctype": "ToDo",
			"description": description,
			"reference_type": DOCTYPE_SERVICE_ORDER,
			"reference_name": doc.name,
			"allocated_to": doc.get("attendant") or frappe.session.user,
			"assigned_by": frappe.session.user,
		}
	)
	todo.insert(ignore_permissions=True)
	return todo.name


def _liberar_reserva(reservation: str | None) -> None:
	if not reservation or not frappe.db.exists(DOCTYPE_STOCK_RESERVATION_ENTRY, reservation):
		return

	reservation_doc = frappe.get_doc(DOCTYPE_STOCK_RESERVATION_ENTRY, reservation)
	if reservation_doc.docstatus != 1:
		return

	reservation_doc.cancel()


def _validate_stock_part(part_row) -> None:
	if not part_row.get("item_code"):
		frappe.throw("Item da peca e obrigatorio.")

	if flt(part_row.get("qty")) <= 0:
		frappe.throw("Quantidade da peca precisa ser maior que zero.")

	if not part_row.get("warehouse"):
		frappe.throw("Deposito da peca e obrigatorio.")

	if not frappe.get_cached_value("Item", part_row.item_code, "is_stock_item"):
		frappe.throw("A peca {0} precisa ser um Item de estoque.".format(part_row.item_code))


def _assert_unreserved_part_is_available(part_row) -> None:
	"""Never issue stock that is already reserved for another Service Order.

	Normal repair flow carries its own SRE and releases it immediately before the
	Material Issue. A manually added line has no such claim, so it can only use
	the remaining free quantity.
	"""
	if part_row.get("reservation"):
		return
	available_qty = flt(get_available_qty_to_reserve(part_row.item_code, part_row.warehouse))
	if available_qty < flt(part_row.qty):
		frappe.throw(
			"Estoque reservado para outra OS. Disponivel para uso: {0}.".format(
				frappe.format_value(available_qty, {"fieldtype": "Float"})
			)
		)


def _get_existing_open_reservation(service_order: str, part_row_name: str) -> str | None:
	return frappe.db.get_value(
		DOCTYPE_STOCK_RESERVATION_ENTRY,
		{
			"voucher_type": DOCTYPE_SERVICE_ORDER,
			"voucher_no": service_order,
			"voucher_detail_no": part_row_name,
			"docstatus": 1,
		},
		"name",
	)


def _get_item_stock_details(item_code: str):
	return frappe.get_cached_value(
		"Item",
		item_code,
		["stock_uom", "has_serial_no", "has_batch_no"],
		as_dict=True,
	)


def _get_company(warehouse: str | None = None) -> str:
	company = None
	if warehouse:
		company = frappe.get_cached_value("Warehouse", warehouse, "company")

	company = company or frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw("Empresa padrao nao configurada para movimentacao de estoque.")

	return company


def _get_employee_company(employee: str) -> str:
	return frappe.db.get_value("Employee", employee, "company") or _get_company()


def _get_stock_entry_type(purpose: str) -> str:
	stock_entry_type = frappe.db.get_value(
		"Stock Entry Type",
		{"purpose": purpose, "is_standard": 1},
		"name",
	)
	if stock_entry_type:
		return stock_entry_type

	if frappe.db.exists("Stock Entry Type", purpose):
		return purpose

	frappe.throw("Stock Entry Type {0} nao encontrado.".format(purpose))


def _get_cost_center(company: str) -> str | None:
	return frappe.get_cached_value("Company", company, "cost_center")


def _get_stock_adjustment_account(company: str) -> str | None:
	return frappe.get_cached_value("Company", company, "stock_adjustment_account")


def _custo(part_row) -> float:
	return flt(part_row.get("valuation_rate")) * flt(part_row.get("qty"))


def _set_part_value(part_row, fieldname: str, value) -> None:
	if part_row.get(fieldname) == value:
		return

	frappe.db.set_value(part_row.doctype, part_row.name, fieldname, value, update_modified=False)
	part_row.set(fieldname, value)


def _append_select_option(options: str, option: str) -> str:
	existing_options = [value for value in options.splitlines() if value]
	if option not in existing_options:
		existing_options.append(option)

	return "\n" + "\n".join(existing_options)
