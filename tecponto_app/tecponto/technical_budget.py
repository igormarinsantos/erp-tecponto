"""Narrow, sale-price-only budgeting surface for assigned technicians."""

from __future__ import annotations

from typing import Any
from io import StringIO
import csv

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import flt

TECHNICIAN_ROLE = "Tecponto Tecnico"
PRICING_STATE = "Diagnosticado — aguardando orçamento"
NEXT_STATE = "Aguardando aprovação"
ALLOWED_SOURCES = {"Loja", "Cliente"}
ALLOWED_DURATION_UNITS = {"Horas", "Dias úteis"}


@frappe.whitelist()
def search_services(query: str = "", limit: int = 20) -> dict[str, Any]:
	_require_technician_role()
	query = (query or "").strip()[:80]
	filters: dict[str, Any] = {"active": 1}
	if query:
		filters["service_name"] = ["like", f"%{query}%"]
	rows = frappe.get_all(
		"Tecponto Service",
		filters=filters,
		fields=["name", "service_name", "category", "default_labor_price", "default_duration", "duration_unit"],
		order_by="service_name asc",
		limit_page_length=max(1, min(int(limit or 20), 50)),
	)
	items = [
		{
			"name": row.name,
			"description": row.service_name,
			"category": row.category,
			"selling_price": flt(row.default_labor_price),
			"duration": flt(row.default_duration),
			"duration_unit": row.duration_unit or "Horas",
		}
		for row in rows
	]
	return {"items": items, "count": len(items)}


@frappe.whitelist()
def search_parts(query: str = "", limit: int = 20) -> dict[str, Any]:
	_require_technician_role()
	query = (query or "").strip()[:80]
	warehouse = _repair_warehouse()
	conditions = ["item.disabled = 0", "item.is_stock_item = 1", "item.is_sales_item = 1"]
	values: dict[str, Any] = {"warehouse": warehouse, "limit": max(1, min(int(limit or 20), 50))}
	if query:
		conditions.append("(item.name like %(query)s or item.item_name like %(query)s or item.item_group like %(query)s)")
		values["query"] = f"%{query}%"
	rows = frappe.db.sql(
		f"""
		select item.name as item_code, item.item_name, item.item_group,
			item.standard_rate as selling_price, coalesce(bin.actual_qty, 0) as available_qty
		from `tabItem` item
		left join `tabBin` bin on bin.item_code = item.name and bin.warehouse = %(warehouse)s
		where {' and '.join(conditions)}
		order by item.item_name asc, item.name asc
		limit %(limit)s
		""",
		values,
		as_dict=True,
	)
	items = [
		{
			"item_code": row.item_code,
			"description": row.item_name,
			"category": row.item_group,
			"selling_price": flt(row.selling_price),
			"available_qty": flt(row.available_qty),
			"warehouse": warehouse,
			"source": "Loja",
		}
		for row in rows
	]
	return {"items": items, "count": len(items), "warehouse": warehouse}


@frappe.whitelist()
def get_budget(name: str) -> dict[str, Any]:
	doc = _get_editable_order(name, require_pricing_state=False)
	return _serialize_budget(doc)


@frappe.whitelist()
def add_line(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	doc = _get_editable_order(name)
	data = _payload(payload)
	_validate_payload_fields(data, {"type", "catalog_service", "item_code", "description", "qty", "selling_price", "duration", "duration_unit", "source", "customer_part_note", "service_row"})
	_append_line(doc, data)
	_save_budget(doc, flt(data.get("selling_price")))
	return _serialize_budget(doc)


@frappe.whitelist()
def update_line(name: str, line_type: str, line_name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	doc = _get_editable_order(name)
	line_type = _line_type(line_type)
	row = _find_line(doc, line_type, line_name)
	data = _payload(payload)
	_validate_payload_fields(data, {"description", "qty", "selling_price", "duration", "duration_unit"})
	qty = flt(data.get("qty") if "qty" in data else row.qty)
	rate = flt(data.get("selling_price") if "selling_price" in data else row.rate)
	if qty <= 0 or rate < 0:
		frappe.throw(_("Quantidade e preço de venda inválidos."), frappe.ValidationError)
	row.qty = qty
	row.rate = 0 if doc.get("is_warranty") or row.get("part_source") == "Cliente" else rate
	if "description" in data:
		row.description = (data.get("description") or "").strip()
	if line_type == "service":
		duration = flt(data.get("duration") if "duration" in data else row.get("service_duration"))
		unit = (data.get("duration_unit") or row.get("duration_unit") or "Horas").strip()
		if duration < 0 or unit not in ALLOWED_DURATION_UNITS:
			frappe.throw(_("Duração inválida."), frappe.ValidationError)
		row.service_duration = duration
		row.duration_unit = unit
	_save_budget(doc, rate)
	return _serialize_budget(doc)


@frappe.whitelist()
def remove_line(name: str, line_type: str, line_name: str) -> dict[str, Any]:
	doc = _get_editable_order(name)
	line_type = _line_type(line_type)
	row = _find_line(doc, line_type, line_name)
	doc.remove(row)
	_save_budget(doc)
	return _serialize_budget(doc)


@frappe.whitelist()
def complete_budget(name: str) -> dict[str, Any]:
	doc = _get_editable_order(name)
	if not any(row.get("item_code") for row in (doc.get("services") or [])) and not any(row.get("item_code") for row in (doc.get("parts") or [])):
		frappe.throw(_("Inclua ao menos um serviço ou peça identificada antes de concluir o orçamento."), frappe.ValidationError)
	apply_workflow(frappe.as_json({"doctype": doc.doctype, "name": doc.name}), NEXT_STATE)
	return get_budget(doc.name)


@frappe.whitelist()
def get_print_html(name: str) -> dict[str, str]:
	budget = get_budget(name)
	rows = "".join(
		f"<tr><td>{frappe.utils.escape_html(line.get('description') or line.get('item_code') or '')}</td><td>{line['qty']:.2f}</td><td>R$ {line['selling_price']:.2f}</td><td>R$ {line['selling_total']:.2f}</td></tr>"
		for line in budget["services"] + budget["parts"]
	)
	html = f"<!doctype html><html><head><meta charset='utf-8'><title>Orçamento {frappe.utils.escape_html(budget['name'])}</title></head><body><h1>Orçamento {frappe.utils.escape_html(budget['name'])}</h1><table><thead><tr><th>Descrição</th><th>Quantidade</th><th>Preço de venda</th><th>Total de venda</th></tr></thead><tbody>{rows}</tbody></table><h2>Total de venda: R$ {budget['selling_total']:.2f}</h2></body></html>"
	return {"html": html}


@frappe.whitelist()
def export_budget(name: str) -> dict[str, str]:
	budget = get_budget(name)
	output = StringIO()
	writer = csv.writer(output)
	writer.writerow(["tipo", "item", "descrição", "categoria", "quantidade", "preço de venda", "total de venda", "origem"])
	for line in budget["services"] + budget["parts"]:
		writer.writerow([line["type"], line.get("item_code") or "", line.get("description") or "", line.get("category") or "", line["qty"], line["selling_price"], line["selling_total"], line.get("source") or "Loja"])
	return {"filename": f"orcamento-{budget['name']}.csv", "content": output.getvalue()}


def _get_editable_order(name: str, require_pricing_state: bool = True):
	_require_technician_role()
	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("read")
	if doc.get("technician") != frappe.session.user:
		frappe.throw(_("Você só pode orçar suas próprias OS."), frappe.PermissionError)
	if require_pricing_state and (doc.get("workflow_state") != PRICING_STATE or doc.get("pricing_responsibility") != "Técnico"):
		frappe.throw(_("Esta OS não está na sua fila de precificação."), frappe.ValidationError)
	return doc


def _append_line(doc, data: dict[str, Any]) -> None:
	line_type = _line_type(data.get("type"))
	qty = flt(data.get("qty") or 1)
	rate = flt(data.get("selling_price") or 0)
	if qty <= 0 or rate < 0:
		frappe.throw(_("Quantidade e preço de venda inválidos."), frappe.ValidationError)
	if line_type == "service":
		catalog_name = (data.get("catalog_service") or "").strip()
		catalog = frappe.db.get_value("Tecponto Service", catalog_name, ["name", "service_name", "category", "default_duration", "duration_unit", "active"], as_dict=True)
		if not catalog or not catalog.active:
			frappe.throw(_("Serviço inválido."), frappe.ValidationError)
		from tecponto_app.tecponto.service_order.billing import _get_labor_item
		duration = flt(data.get("duration") if data.get("duration") is not None else catalog.default_duration)
		unit = (data.get("duration_unit") or catalog.duration_unit or "Horas").strip()
		if duration < 0 or unit not in ALLOWED_DURATION_UNITS:
			frappe.throw(_("Duração inválida."), frappe.ValidationError)
		doc.append("services", {"item_code": _get_labor_item(), "catalog_service": catalog.name, "service_category": catalog.category, "description": (data.get("description") or catalog.service_name).strip(), "qty": qty, "rate": 0 if doc.get("is_warranty") else rate, "service_duration": duration, "duration_unit": unit})
		return
	source = (data.get("source") or "Loja").strip()
	if source not in ALLOWED_SOURCES:
		frappe.throw(_("Origem da peça inválida."), frappe.ValidationError)
	item_code = (data.get("item_code") or "").strip()
	item = frappe.db.get_value("Item", item_code, ["name", "item_name", "is_stock_item", "disabled"], as_dict=True) if item_code else None
	if source == "Loja" and (not item or item.disabled or not item.is_stock_item):
		frappe.throw(_("Peça inválida."), frappe.ValidationError)
	if source == "Cliente" and not (data.get("description") or "").strip():
		frappe.throw(_("Identifique a peça fornecida pelo cliente."), frappe.ValidationError)
	doc.append("parts", {"item_code": item.name if item else None, "description": (data.get("description") or (item.item_name if item else "")).strip(), "qty": qty, "warehouse": _repair_warehouse() if source == "Loja" else None, "rate": rate if source == "Loja" and not doc.get("is_warranty") else 0, "part_source": source, "customer_part_note": (data.get("customer_part_note") or "").strip() or None})
	if source == "Cliente":
		doc.customer_supplied_part_term_required = 1


def _serialize_budget(doc) -> dict[str, Any]:
	services = [_safe_line(row, "service") for row in (doc.get("services") or [])]
	parts = [_safe_line(row, "part") for row in (doc.get("parts") or [])]
	return {"name": doc.name, "workflow_state": doc.get("workflow_state"), "pricing_responsibility": doc.get("pricing_responsibility"), "quote_locked": bool(doc.get("quote_locked")), "budget_version": int(doc.get("budget_version") or 1), "services": services, "parts": parts, "selling_total": sum(row["selling_total"] for row in services + parts)}


def _safe_line(row, line_type: str) -> dict[str, Any]:
	qty, rate = flt(row.get("qty")), flt(row.get("rate"))
	return {"name": row.name, "type": line_type, "item_code": row.get("item_code"), "description": row.get("description"), "category": row.get("service_category") if line_type == "service" else frappe.get_cached_value("Item", row.get("item_code"), "item_group") if row.get("item_code") else None, "qty": qty, "selling_price": rate, "selling_total": qty * rate, "duration": flt(row.get("service_duration")) if line_type == "service" else None, "duration_unit": row.get("duration_unit") if line_type == "service" else None, "available_qty": _available_qty(row.get("item_code"), row.get("warehouse")) if line_type == "part" and row.get("part_source") != "Cliente" else None, "warehouse": row.get("warehouse"), "source": row.get("part_source") or "Loja"}


def _available_qty(item_code: str | None, warehouse: str | None) -> float:
	if not item_code or not warehouse:
		return 0
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"))


def _save_budget(doc, submitted_selling_price: float | None = None) -> None:
	try:
		doc.save(ignore_permissions=True)
	except frappe.ValidationError as error:
		message = str(error)
		if "piso comercial" in message.lower():
			frappe.throw(
				_("Preço de venda informado ({0}) abaixo do piso permitido; solicite aprovação do Gestor.").format(
					frappe.format_value(flt(submitted_selling_price), {"fieldtype": "Currency"}),
				),
				frappe.ValidationError,
			)
		raise


def _find_line(doc, line_type: str, line_name: str):
	for row in doc.get("services" if line_type == "service" else "parts") or []:
		if row.name == (line_name or "").strip():
			return row
	frappe.throw(_("Linha do orçamento não encontrada."), frappe.DoesNotExistError)


def _line_type(value: str | None) -> str:
	value = (value or "").strip()
	if value not in {"service", "part"}:
		frappe.throw(_("Tipo de linha inválido."), frappe.ValidationError)
	return value


def _payload(value: str | dict[str, Any] | None) -> dict[str, Any]:
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if not isinstance(value, dict):
		frappe.throw(_("Dados do orçamento inválidos."), frappe.ValidationError)
	return value


def _validate_payload_fields(payload: dict[str, Any], allowed: set[str]) -> None:
	if set(payload) - allowed:
		frappe.throw(_("O orçamento técnico aceita somente dados operacionais e preço de venda."), frappe.PermissionError)


def _repair_warehouse() -> str:
	warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
	if not warehouse:
		frappe.throw(_("Depósito Reparo não configurado."), frappe.ValidationError)
	return warehouse


def _require_technician_role() -> None:
	if frappe.session.user == "Guest" or TECHNICIAN_ROLE not in frappe.get_roles():
		frappe.throw(_("Acesso exclusivo do técnico."), frappe.PermissionError)
