from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import flt, now_datetime, strip_html, today
from frappe.utils.file_manager import save_file

from tecponto_app.tecponto.customer import (
	CUSTOMER_NO_CPF_FIELD,
	assert_existing_customer_is_complete,
	validate_customer_contact_document,
)
from tecponto_app.tecponto.pos import get_commercial_item_groups, get_retail_item_groups
from tecponto_app.tecponto.pending import action_for_service_order_state
from tecponto_app.tecponto.stock import normalize_barcode
from tecponto_app.tecponto.service_order.print_formats import (
	PF_ETIQUETA_QR,
	PF_OS_ORCAMENTO,
	PF_TERMO_ENTRADA,
	PF_TERMO_RETIRADA,
)
from tecponto_app.tecponto.workflow import _get_service_order_transitions, get_service_order_workflow_state_names


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
CHECKIN_ALLOWED_ROLES = {
	"System Manager",
	"Tecponto Atendente",
	"Tecponto Gestor",
}
ATTENDANT_FLOW_ALLOWED_ROLES = CHECKIN_ALLOWED_ROLES
POS_ALLOWED_ROLES = CHECKIN_ALLOWED_ROLES
APPROVAL_CHANNELS = {"Presencial", "Telefone", "WhatsApp"}
STATE_AGUARDANDO_APROVACAO = "Aguardando aprovação"
STATE_APROVADO = "Aprovado"
STATE_REPROVADO = "Reprovado"
STATE_PRONTO_RETIRADA = "Pronto para retirada"
STATE_ENTREGUE = "Entregue"
APPROVAL_STATUS_APROVADO = "Aprovado"
APPROVAL_STATUS_REPROVADO = "Reprovado"
KANBAN_BLOCKED_TARGETS = {
	STATE_APROVADO: "Use o fluxo de aprovação para registrar canal, atendente e observação.",
	STATE_REPROVADO: "Use o fluxo de reprovação para registrar canal e motivo.",
	STATE_ENTREGUE: "Use o fluxo de retirada para coletar assinatura e validar pagamento.",
}
QUOTE_SEND_CHANNELS = {"WhatsApp", "Telefone", "Presencial", "E-mail"}
QUOTE_SEND_MEDIUM_BY_CHANNEL = {
	"WhatsApp": "Chat",
	"Telefone": "Phone",
	"Presencial": "Visit",
	"E-mail": "Email",
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
	"custom_whatsapp",
	"custom_cpf",
	"custom_rg",
	CUSTOMER_NO_CPF_FIELD,
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
	"photos",
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
	"table_max",
	"approved_value",
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


def _require_checkin_role() -> None:
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(CHECKIN_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem permissão para abrir OS no balcão."), frappe.PermissionError)


def _require_attendant_flow_role() -> None:
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(ATTENDANT_FLOW_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem permissão para registrar aprovação ou retirada no balcão."), frappe.PermissionError)


def _require_pos_role() -> None:
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(POS_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem permissão para operar o PDV do balcão."), frappe.PermissionError)


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


@frappe.whitelist(allow_guest=True)
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


@frappe.whitelist(allow_guest=True)
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
def list_service_orders(
	limit: int = 20,
	query: str | None = None,
	status: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit or 20), 100))
	filters, or_filters = _service_order_search_filters(
		query=query,
		status=status,
		from_date=from_date,
		to_date=to_date,
	)
	items = frappe.get_list(
		"Service Order",
		fields=list(SAFE_SERVICE_ORDER_FIELDS),
		filters=filters,
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=limit,
	)
	count = _count_service_orders(filters=filters, or_filters=or_filters)

	return {
		"items": [_serialize_service_order(item) for item in items],
		"count": count,
		"fields": list(SAFE_SERVICE_ORDER_FIELDS),
	}


@frappe.whitelist()
def get_service_order_kanban(
	limit_per_column: int = 18,
	query: str | None = None,
	status: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit_per_column or 18), 40))
	columns = []
	for state in get_service_order_workflow_state_names():
		if status and status != "all" and status != state:
			items = []
			count = 0
		else:
			filters, or_filters = _service_order_search_filters(
				query=query,
				status=state,
				from_date=from_date,
				to_date=to_date,
			)
			items = frappe.get_list(
				"Service Order",
				fields=list(SAFE_SERVICE_ORDER_FIELDS),
				filters=filters,
				or_filters=or_filters,
				order_by="modified desc",
				limit_page_length=limit,
			)
			count = _count_service_orders(filters=filters, or_filters=or_filters)
		columns.append(
			{
				"state": state,
				"count": count,
				"items": [_serialize_service_order(item) for item in items],
			}
		)

	return {
		"columns": columns,
		"fields": list(SAFE_SERVICE_ORDER_FIELDS),
	}


@frappe.whitelist()
def move_service_order(name: str, target_state: str) -> dict[str, Any]:
	_require_frontend_role()
	name = (name or "").strip()
	target_state = (target_state or "").strip()
	if not name:
		frappe.throw(_("Informe a ordem de serviço."), frappe.ValidationError)
	if target_state not in get_service_order_workflow_state_names():
		frappe.throw(_("Estado de destino inválido para o Kanban."), frappe.ValidationError)

	doc = frappe.get_doc("Service Order", name)
	doc.check_permission("read")
	current_state = doc.get("workflow_state")
	if current_state == target_state:
		return {"item": _serialize_service_order(doc.as_dict()), "changed": False}
	if target_state in KANBAN_BLOCKED_TARGETS:
		frappe.throw(_(KANBAN_BLOCKED_TARGETS[target_state]), frappe.ValidationError)

	action = _get_allowed_kanban_action(current_state, target_state)
	apply_workflow(frappe.as_json({"doctype": doc.doctype, "name": doc.name}), action)
	updated = frappe.db.get_value(
		"Service Order",
		name,
		list(SAFE_SERVICE_ORDER_FIELDS),
		as_dict=True,
	)
	return {
		"item": _serialize_service_order(updated),
		"changed": True,
	}


@frappe.whitelist()
def get_service_order_detail(name: str) -> dict[str, Any]:
	_require_frontend_role()
	name = (name or "").strip()
	if not name:
		frappe.throw(_("Informe a ordem de serviço."), frappe.ValidationError)

	doc = frappe.get_doc("Service Order", name)
	doc.check_permission("read")

	services = [_serialize_service_row(row) for row in (doc.get("services") or [])]
	parts = [_serialize_part_row(row) for row in (doc.get("parts") or [])]
	service_total = sum(row["amount"] for row in services)
	parts_price_total = sum(row["amount"] for row in parts)
	discount = flt(doc.get("discount") or 0)
	grand_total = flt(doc.get("grand_total") or (service_total + parts_price_total - discount))

	return {
		"name": doc.name,
		"workflow_state": doc.get("workflow_state"),
		"approval_status": doc.get("approval_status"),
		"approval_deadline": str(doc.get("approval_deadline") or ""),
		"approval": {
			"channel": doc.get("approval_channel"),
			"approved_by": doc.get("approved_by"),
			"approved_by_attendant": doc.get("approved_by_attendant"),
			"approval_date": str(doc.get("approval_date") or ""),
			"notes": doc.get("approval_notes"),
		},
		"entry_date": str(doc.get("entry_date") or ""),
		"modified": str(doc.get("modified") or ""),
		"attendant": doc.get("attendant"),
		"technician": doc.get("technician"),
		"priority": doc.get("priority"),
		"customer": _get_customer_detail(doc.get("customer")),
		"device": _get_device_detail(doc.get("customer_device")),
		"reported_defect": doc.get("reported_defect"),
		"physical_state": doc.get("physical_state"),
		"accessories_received": doc.get("accessories_received"),
		"diagnosis": {
			"problem_found": doc.get("problem_found"),
			"diagnosis_date": str(doc.get("diagnosis_date") or ""),
			"diagnosis_deadline": str(doc.get("diagnosis_deadline") or ""),
		},
		"services": services,
		"parts": parts,
		"totals": {
			"service_total": service_total,
			"parts_price_total": parts_price_total,
			"discount": discount,
			"grand_total": grand_total,
			"budget_version": int(doc.get("budget_version") or 1),
			"quote_locked": bool(doc.get("quote_locked")),
		},
		"warranty": {
			"is_warranty": bool(doc.get("is_warranty")),
			"original_service_order": doc.get("original_service_order"),
			"warranty_expiry": str(doc.get("warranty_expiry") or ""),
		},
		"pickup": {
			"pickup_by_third_party": bool(doc.get("picked_up_by_third_party")),
			"pickup_person_name": doc.get("picked_up_by"),
			"pickup_person_document": doc.get("picked_up_doc") or doc.get("third_party_doc"),
			"pickup_date": str(doc.get("pickup_date") or ""),
			"pickup_notes": doc.get("pickup_notes"),
			"has_signature": bool(doc.get("customer_signature")),
		},
		"finance": {
			"sales_invoice": doc.get("sales_invoice"),
			"sales_invoice_status": _get_sales_invoice_status(doc.get("sales_invoice")),
		},
		"workflow_actions": _get_visible_workflow_actions(doc),
		"workflow_transitions": _get_service_order_transition_options(doc.get("workflow_state")),
		"timeline": _get_service_order_timeline(doc),
		"print_links": _get_service_order_print_links(doc.name),
	}


@frappe.whitelist()
def search_budget_items(
	query: str = "",
	line_type: str = "service",
	limit: int = 12,
) -> dict[str, Any]:
	_require_attendant_flow_role()
	line_type = _validate_budget_line_type(line_type)
	filters: dict[str, Any] = {"disabled": 0}
	if line_type == "service":
		filters["is_stock_item"] = 0
	else:
		filters["is_stock_item"] = 1

	search = (query or "").strip()
	or_filters = None
	if search:
		like = f"%{search}%"
		or_filters = [
			["Item", "name", "like", like],
			["Item", "item_name", "like", like],
			["Item", "item_group", "like", like],
		]

	items = frappe.get_all(
		"Item",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "item_name", "item_group", "is_stock_item", "standard_rate"],
		order_by="modified desc",
		limit_page_length=max(1, min(int(limit or 12), 30)),
	)
	return {
		"items": [
			{
				"item_code": item.name,
				"item_name": item.item_name,
				"item_group": item.item_group,
				"is_stock_item": bool(item.is_stock_item),
				"standard_rate": flt(item.standard_rate or 0),
				"has_price": flt(item.standard_rate or 0) > 0,
			}
			for item in items
		]
	}


@frappe.whitelist()
def search_pos_items(
	query: str = "",
	barcode: str = "",
	limit: int = 12,
) -> dict[str, Any]:
	_require_pos_role()
	query = (query or "").strip()[:80]
	barcode = normalize_barcode(barcode)[:80]
	limit = max(1, min(int(limit or 12), 30))
	fields = [
		"item_code",
		"item_name",
		"item_group",
		"barcode",
		"description",
		"image",
		"standard_rate",
		"has_price",
		"available_qty",
		"warehouse",
	]
	if not query and not barcode:
		return {"items": [], "count": 0, "fields": fields}

	warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	if not warehouse:
		frappe.throw(_("Depósito Comercial não configurado no Tecponto Settings."), frappe.ValidationError)

	commercial_groups = get_commercial_item_groups()
	if not commercial_groups:
		frappe.throw(_("Grupos comerciais do PDV não estão configurados."), frappe.ValidationError)

	conditions = [
		"item.disabled = 0",
		"item.is_stock_item = 1",
		"item.is_sales_item = 1",
		"item.item_group in %(commercial_groups)s",
	]
	values: dict[str, Any] = {
		"commercial_groups": tuple(commercial_groups),
		"limit": limit,
		"warehouse": warehouse,
	}
	if barcode:
		conditions.append(
			"exists (select 1 from `tabItem Barcode` matched_barcode where matched_barcode.parent = item.name and matched_barcode.barcode = %(barcode)s)"
		)
		values["barcode"] = barcode
		barcode_select = "%(barcode)s"
	else:
		conditions.append(
			"(item.name like %(query)s or item.item_name like %(query)s or item.item_group like %(query)s)"
		)
		values["query"] = f"%{query}%"
		barcode_select = "(select item_barcode.barcode from `tabItem Barcode` item_barcode where item_barcode.parent = item.name order by item_barcode.idx asc limit 1)"

	rows = frappe.db.sql(
		f"""
		select
			item.name as item_code,
			item.item_name,
			item.item_group,
			item.has_serial_no,
			{barcode_select} as barcode,
			item.description,
			item.image,
			item.standard_rate,
			coalesce(bin.actual_qty, 0) as available_qty,
			%(warehouse)s as warehouse
		from `tabItem` item
		left join `tabBin` bin
			on bin.item_code = item.name
			and bin.warehouse = %(warehouse)s
		where {" and ".join(conditions)}
		order by item.item_name asc, item.name asc
		limit %(limit)s
		""",
		values,
		as_dict=True,
	)
	items = [_serialize_pos_item(item) for item in rows]
	return {"items": items, "count": len(items), "fields": fields}


@frappe.whitelist()
def list_budget_warehouses(query: str = "", limit: int = 12) -> dict[str, Any]:
	_require_attendant_flow_role()
	filters: dict[str, Any] = {"is_group": 0, "disabled": 0}
	search = (query or "").strip()
	or_filters = None
	if search:
		like = f"%{search}%"
		or_filters = [
			["Warehouse", "name", "like", like],
			["Warehouse", "warehouse_name", "like", like],
		]

	warehouses = frappe.get_all(
		"Warehouse",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "warehouse_name"],
		order_by="warehouse_name asc",
		limit_page_length=max(1, min(int(limit or 12), 30)),
	)
	return {"items": [dict(warehouse) for warehouse in warehouses]}


@frappe.whitelist()
def add_service_order_budget_line(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_attendant_flow_role()
	data = _parse_payload(payload)
	line_type = _validate_budget_line_type(data.get("type"))
	item_code = (data.get("item_code") or "").strip()
	qty = flt(data.get("qty") or 0)
	rate = flt(data.get("rate") or 0)

	if not item_code:
		frappe.throw(_("Selecione o item do orçamento."), frappe.ValidationError)
	if qty <= 0:
		frappe.throw(_("Quantidade precisa ser maior que zero."), frappe.ValidationError)
	if rate < 0:
		frappe.throw(_("Valor unitário não pode ser negativo."), frappe.ValidationError)

	item = frappe.db.get_value(
		"Item",
		item_code,
		["name", "item_name", "is_stock_item", "disabled"],
		as_dict=True,
	)
	if not item or item.disabled:
		frappe.throw(_("Item do orçamento inválido."), frappe.ValidationError)
	if line_type == "service" and item.is_stock_item:
		frappe.throw(_("Serviço do orçamento deve ser um item não estocável."), frappe.ValidationError)
	if line_type == "part" and not item.is_stock_item:
		frappe.throw(_("Peça do orçamento deve ser um item de estoque."), frappe.ValidationError)

	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("write")
	if line_type == "service":
		doc.append(
			"services",
			{
				"item_code": item.name,
				"description": (data.get("description") or item.item_name or item.name).strip(),
				"qty": qty,
				"rate": rate,
			},
		)
	else:
		warehouse = (data.get("warehouse") or "").strip() or _get_default_repair_warehouse()
		if not warehouse:
			frappe.throw(_("Informe o estoque da peça."), frappe.ValidationError)
		if not frappe.db.exists("Warehouse", {"name": warehouse, "is_group": 0, "disabled": 0}):
			frappe.throw(_("Estoque da peça inválido."), frappe.ValidationError)
		doc.append(
			"parts",
			{
				"item_code": item.name,
				"description": (data.get("description") or item.item_name or item.name).strip(),
				"qty": qty,
				"warehouse": warehouse,
				"rate": rate,
			},
		)

	doc.save(ignore_permissions=True)
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def send_service_order_quote(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_attendant_flow_role()
	data = _parse_payload(payload)
	channel = (data.get("channel") or "").strip()
	notes = (data.get("notes") or "").strip()

	if channel not in QUOTE_SEND_CHANNELS:
		frappe.throw(_("Canal de envio do orçamento inválido."), frappe.ValidationError)

	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("read")
	if doc.get("workflow_state") != STATE_AGUARDANDO_APROVACAO:
		frappe.throw(_("A OS precisa estar em Aguardando aprovação para enviar orçamento."), frappe.ValidationError)
	if not (doc.get("services") or doc.get("parts")):
		frappe.throw(_("Inclua ao menos um serviço ou peça antes de enviar o orçamento."), frappe.ValidationError)

	customer = _get_customer_detail(doc.get("customer")) or {}
	phone = customer.get("custom_whatsapp") or customer.get("mobile_no") or ""
	email = customer.get("email_id") or ""
	communication = frappe.get_doc(
		{
			"doctype": "Communication",
			"subject": f"Orçamento enviado - {doc.name}",
			"communication_medium": QUOTE_SEND_MEDIUM_BY_CHANNEL[channel],
			"communication_type": "Communication",
			"sent_or_received": "Sent",
			"status": "Linked",
			"sender": frappe.session.user,
			"recipients": email if channel == "E-mail" else "",
			"phone_no": phone if channel in {"WhatsApp", "Telefone"} else "",
			"content": _quote_send_content(doc, channel, notes),
			"text_content": _quote_send_text(doc, channel, notes),
			"communication_date": now_datetime(),
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"user": frappe.session.user,
		}
	)
	communication.insert(ignore_permissions=True)
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def create_service_order_checkin(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_checkin_role()
	data = _parse_payload(payload)
	_validate_checkin_payload(data)

	customer_name = _get_or_create_checkin_customer(data["customer"])
	device_name = _get_or_create_checkin_device(data["device"], customer_name)
	order = frappe.new_doc("Service Order")
	order.naming_series = "OS-.YYYY.-.#####"
	order.customer = customer_name
	order.customer_device = device_name
	order.entry_date = now_datetime()
	order.attendant = frappe.session.user
	order.workflow_state = "Entrada criada"
	order.priority = "Normal"
	order.reported_defect = data["service_order"]["reported_defect"].strip()
	order.physical_state = data["service_order"]["physical_state"].strip()
	order.accessories_received = (data["service_order"].get("accessories_received") or "").strip()
	order.entry_signature = data["entry_signature"]
	order.insert(ignore_permissions=True)

	photo_url = _save_checkin_photo(order.name, data["entry_photo"])
	frappe.db.set_value(
		"Service Order",
		order.name,
		{"entry_photos": photo_url},
		update_modified=True,
	)

	return {
		"service_order": {
			"name": order.name,
			"workflow_state": "Entrada criada",
			"customer": _get_customer_detail(customer_name),
			"device": _get_device_detail(device_name),
			"print_links": _get_service_order_print_links(order.name),
		},
		"entry_photo_url": photo_url,
	}


@frappe.whitelist()
def decide_service_order_budget(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_attendant_flow_role()
	data = _parse_payload(payload)
	decision = (data.get("decision") or "").strip()
	channel = (data.get("channel") or "").strip()
	notes = (data.get("notes") or "").strip()

	if decision not in {"approve", "reject"}:
		frappe.throw(_("Informe se o orçamento foi aprovado ou reprovado."), frappe.ValidationError)
	if channel not in APPROVAL_CHANNELS:
		frappe.throw(_("Canal de aprovação inválido."), frappe.ValidationError)
	if decision == "reject" and not notes:
		frappe.throw(_("Informe o motivo da reprovação."), frappe.ValidationError)

	doc = frappe.get_doc("Service Order", name)
	if doc.get("workflow_state") != STATE_AGUARDANDO_APROVACAO:
		frappe.throw(_("A OS precisa estar em Aguardando aprovação."), frappe.ValidationError)

	if decision == "approve":
		approval_status = APPROVAL_STATUS_APROVADO
		approved_by = frappe.session.user
		workflow_action = STATE_APROVADO
	else:
		approval_status = APPROVAL_STATUS_REPROVADO
		approved_by = None
		workflow_action = STATE_REPROVADO

	frappe.db.set_value(
		doc.doctype,
		doc.name,
		{
			"approval_status": approval_status,
			"approved_by": approved_by,
			"approval_channel": channel,
			"approved_by_attendant": frappe.session.user,
			"approval_notes": notes,
			"approval_date": now_datetime(),
		},
		update_modified=False,
	)
	apply_workflow(frappe.as_json({"doctype": doc.doctype, "name": doc.name}), workflow_action)

	return get_service_order_detail(doc.name)


@frappe.whitelist()
def complete_service_order_pickup(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_attendant_flow_role()
	data = _parse_payload(payload)
	signature = data.get("customer_signature")
	if not _is_image_data_url(signature):
		frappe.throw(_("Assinatura de retirada é obrigatória."), frappe.ValidationError)

	doc = frappe.get_doc("Service Order", name)
	if doc.get("workflow_state") != STATE_PRONTO_RETIRADA:
		frappe.throw(_("A OS precisa estar Pronto para retirada."), frappe.ValidationError)

	third_party = bool(data.get("third_party"))
	picked_up_by = (data.get("picked_up_by") or "").strip()
	picked_up_doc = (data.get("picked_up_doc") or "").strip()
	pickup_notes = (data.get("pickup_notes") or "").strip()
	if third_party and not picked_up_by:
		frappe.throw(_("Informe o nome de quem está retirando."), frappe.ValidationError)
	if third_party and not picked_up_doc:
		frappe.throw(_("Informe o documento de quem está retirando."), frappe.ValidationError)

	frappe.db.set_value(
		doc.doctype,
		doc.name,
		{
			"picked_up_by": picked_up_by or _customer_label(doc.get("customer")),
			"picked_up_doc": picked_up_doc,
			"picked_up_by_third_party": 1 if third_party else 0,
			"third_party_doc": picked_up_doc if third_party else None,
			"third_party_auth": (data.get("third_party_auth") or "").strip() if third_party else None,
			"pickup_notes": pickup_notes,
			"customer_signature": signature,
			"pickup_date": now_datetime(),
		},
		update_modified=False,
	)
	apply_workflow(frappe.as_json({"doctype": doc.doctype, "name": doc.name}), STATE_ENTREGUE)

	return get_service_order_detail(doc.name)


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
		("name", "customer_name", "mobile_no", "custom_whatsapp", "custom_cpf", "custom_rg", "email_id"),
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
def create_customer(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Create an individual customer from the counter without opening core Customer."""
	_require_checkin_role()
	data = _parse_payload(payload)
	validate_customer_contact_document(data)

	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": data["customer_name"].strip(),
			"customer_type": "Individual",
			"mobile_no": (data.get("mobile_no") or data.get("custom_whatsapp") or "").strip(),
			"custom_whatsapp": (data.get("custom_whatsapp") or data.get("mobile_no") or "").strip(),
			"custom_cpf": (data.get("custom_cpf") or "").strip(),
			"custom_rg": (data.get("custom_rg") or "").strip(),
			CUSTOMER_NO_CPF_FIELD: 1 if data.get(CUSTOMER_NO_CPF_FIELD) else 0,
			"email_id": (data.get("email_id") or "").strip(),
		}
	)
	customer.insert(ignore_permissions=True)
	item = frappe.db.get_value("Customer", customer.name, list(SAFE_CUSTOMER_FIELDS), as_dict=True)
	return {"item": _serialize_customer(item)}


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
def create_customer_device(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_checkin_role()
	data = _parse_payload(payload)
	customer = (data.get("customer") or "").strip()
	if not customer:
		frappe.throw(_("Selecione o cliente do aparelho."), frappe.ValidationError)
	assert_existing_customer_is_complete(customer)
	_validate_device_payload(data)

	device = frappe.get_doc(
		{
			"doctype": "Customer Device",
			"customer": customer,
			"brand": data["brand"].strip(),
			"model": data["model"].strip(),
			"color": (data.get("color") or "").strip(),
			"imei_serial": data["imei_serial"].strip(),
			"capacity": (data.get("capacity") or "").strip(),
			"general_state": (data.get("general_state") or "").strip(),
			"registration_date": today(),
		}
	)
	device.insert(ignore_permissions=True)

	photo = data.get("photo") or {}
	if _is_image_data_url(photo.get("data_url")):
		photo_url = _save_customer_device_photo(device.name, photo)
		frappe.db.set_value("Customer Device", device.name, "photos", photo_url, update_modified=False)

	item = frappe.db.get_value("Customer Device", device.name, list(SAFE_DEVICE_FIELDS), as_dict=True)
	return {"item": _serialize_customer_device(item)}


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
def set_tradein_approved_value(name: str, approved_value: float) -> dict[str, Any]:
	"""Attempt the normal evaluation save so the trade table guard remains authoritative."""
	_require_frontend_role()
	doc = frappe.get_doc("Device Trade Evaluation", (name or "").strip())
	doc.approved_value = flt(approved_value, 2)
	# This endpoint exposes only the table-governed value. Validation still runs under
	# the caller, while an approved request later saves normally under the Gestor.
	doc.save(ignore_permissions=True)
	item = frappe.db.get_value("Device Trade Evaluation", doc.name, list(SAFE_TRADE_EVALUATION_FIELDS), as_dict=True)
	return {"item": _serialize_trade_evaluation(item)}


@frappe.whitelist()
def list_stock_items(query: str = "", limit: int = 12, scope: str = "parts-stock") -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit or 12), 50))
	query = (query or "").strip()
	scope = (scope or "parts-stock").strip()
	repair_warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
	commercial_warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	if scope == "repair-parts":
		stock_groups = tuple(_descendant_item_groups("Peças de Reparo")) or ("",)
		warehouse = repair_warehouse
	elif scope == "commercial-products":
		stock_groups = tuple(get_retail_item_groups()) or ("",)
		warehouse = commercial_warehouse
	elif scope == "used-devices":
		stock_groups = tuple(_descendant_item_groups("Aparelhos Usados")) or ("",)
		warehouse = commercial_warehouse
	else:
		stock_groups = tuple(get_commercial_item_groups()) or ("",)
		warehouse = None
	conditions = [
		"item.disabled = 0",
		"item.is_stock_item = 1",
		"bin.warehouse is not null",
	]
	values: dict[str, Any] = {"stock_groups": stock_groups, "limit": limit}
	conditions.append("item.item_group in %(stock_groups)s")
	if warehouse:
		conditions.append("bin.warehouse = %(stock_warehouse)s")
		values["stock_warehouse"] = warehouse
	if query:
		conditions.append(
			"""(
				item.name like %(query)s
				or item.item_name like %(query)s
				or item.item_group like %(query)s
				or bin.warehouse like %(query)s
				or exists (
					select 1 from `tabItem Barcode` searched_barcode
					where searched_barcode.parent = item.name and searched_barcode.barcode like %(query)s
				)
			)"""
		)
		values["query"] = f"%{query}%"

	rows = frappe.db.sql(
		f"""
		select
			item.name as item_code,
			item.item_name,
			item.item_group,
			item.has_serial_no,
			(select item_barcode.barcode from `tabItem Barcode` item_barcode where item_barcode.parent = item.name order by item_barcode.idx asc limit 1) as barcode,
			item.item_group in %(stock_groups)s as is_commercial_item,
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
		"fields": ["item_code", "item_name", "item_group", "has_serial_no", "barcode", "is_commercial_item", "warehouse", "available_qty"],
	}


def _service_order_search_filters(
	query: str | None = None,
	status: str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> tuple[dict[str, Any], list[list[str]]]:
	filters: dict[str, Any] = {}
	or_filters: list[list[str]] = []

	status = (status or "").strip()
	if status and status != "all":
		filters["workflow_state"] = status

	from_date = (from_date or "").strip()
	to_date = (to_date or "").strip()
	if from_date and to_date:
		filters["modified"] = ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]
	elif from_date:
		filters["modified"] = [">=", f"{from_date} 00:00:00"]
	elif to_date:
		filters["modified"] = ["<=", f"{to_date} 23:59:59"]

	query = (query or "").strip()[:80]
	if query:
		like = f"%{query}%"
		or_filters = [
			["Service Order", "name", "like", like],
			["Service Order", "customer", "like", like],
			["Service Order", "customer_device", "like", like],
			["Service Order", "reported_defect", "like", like],
			["Service Order", "workflow_state", "like", like],
			["Service Order", "technician", "like", like],
			["Service Order", "attendant", "like", like],
			["Service Order", "priority", "like", like],
		]

	return filters, or_filters


def _count_service_orders(filters: dict[str, Any], or_filters: list[list[str]]) -> int:
	return len(
		frappe.get_all(
			"Service Order",
			filters=filters,
			or_filters=or_filters,
			pluck="name",
			limit_page_length=0,
		)
	)


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
		"workflow_transitions": _get_service_order_transition_options(item.get("workflow_state")),
		"next_action": action_for_service_order_state(item.get("workflow_state")),
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
		"custom_whatsapp": item.get("custom_whatsapp"),
		"custom_cpf": item.get("custom_cpf"),
		"custom_rg": item.get("custom_rg"),
		CUSTOMER_NO_CPF_FIELD: bool(item.get(CUSTOMER_NO_CPF_FIELD)),
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
		"photo_url": item.get("photos"),
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
		"table_max": flt(item.get("table_max") or 0),
		"approved_value": flt(item.get("approved_value") or 0),
		"workflow_state": item.get("workflow_state"),
		"modified": str(item.get("modified") or ""),
	}


def _serialize_stock_item(item: dict[str, Any]) -> dict[str, Any]:
	return {
		"item_code": item.get("item_code"),
		"item_name": item.get("item_name"),
		"item_group": item.get("item_group"),
		"has_serial_no": bool(item.get("has_serial_no")),
		"barcode": item.get("barcode"),
		"is_commercial_item": bool(item.get("is_commercial_item")),
		"warehouse": item.get("warehouse"),
		"available_qty": float(item.get("available_qty") or 0),
	}


def _descendant_item_groups(root: str) -> list[str]:
	bounds = frappe.db.get_value("Item Group", root, ["lft", "rgt"], as_dict=True)
	if not bounds:
		return []
	return frappe.get_all(
		"Item Group",
		filters={"lft": [">=", bounds.lft], "rgt": ["<=", bounds.rgt]},
		pluck="name",
	)


def _serialize_pos_item(item: dict[str, Any]) -> dict[str, Any]:
	standard_rate = flt(item.get("standard_rate") or 0)
	return {
		"item_code": item.get("item_code"),
		"item_name": item.get("item_name"),
		"item_group": item.get("item_group"),
		"barcode": item.get("barcode"),
		"description": strip_html(item.get("description") or "").strip()[:180] or None,
		"image": item.get("image"),
		"standard_rate": standard_rate,
		"has_price": standard_rate > 0,
		"available_qty": flt(item.get("available_qty") or 0),
		"warehouse": item.get("warehouse"),
	}


def _parse_payload(payload: str | dict[str, Any] | None) -> dict[str, Any]:
	if isinstance(payload, dict):
		return payload
	if isinstance(payload, str) and payload.strip():
		return json.loads(payload)
	frappe.throw(_("Dados do check-in não informados."), frappe.ValidationError)


def _validate_budget_line_type(line_type: str | None) -> str:
	value = (line_type or "").strip()
	if value not in {"service", "part"}:
		frappe.throw(_("Tipo de linha de orçamento inválido."), frappe.ValidationError)
	return value


def _get_default_repair_warehouse() -> str | None:
	return (
		frappe.db.get_value("Warehouse", {"warehouse_name": ["like", "%Reparo%"], "is_group": 0, "disabled": 0}, "name")
		or frappe.db.get_value("Warehouse", {"name": ["like", "%Reparo%"], "is_group": 0, "disabled": 0}, "name")
		or frappe.db.get_value("Warehouse", {"warehouse_name": ["like", "%Peças%"], "is_group": 0, "disabled": 0}, "name")
		or frappe.db.get_value("Warehouse", {"name": ["like", "%Peças%"], "is_group": 0, "disabled": 0}, "name")
	)


def _quote_send_text(doc: Any, channel: str, notes: str) -> str:
	customer = _customer_label(doc.get("customer")) or "cliente"
	total = flt(doc.get("grand_total") or 0)
	deadline = doc.get("approval_deadline") or "prazo não definido"
	lines = [
		f"Orçamento {doc.name} enviado para {customer}.",
		f"Canal: {channel}.",
		f"Total: R$ {total:.2f}.",
		f"Validade: {deadline}.",
	]
	if notes:
		lines.append(f"Observação: {notes}")
	return "\n".join(lines)


def _quote_send_content(doc: Any, channel: str, notes: str) -> str:
	return frappe.utils.escape_html(_quote_send_text(doc, channel, notes)).replace("\n", "<br>")


def _validate_checkin_payload(data: dict[str, Any]) -> None:
	customer = data.get("customer") or {}
	device = data.get("device") or {}
	service_order = data.get("service_order") or {}
	entry_photo = data.get("entry_photo") or {}

	if customer.get("existing_name"):
		assert_existing_customer_is_complete(customer["existing_name"])
	else:
		validate_customer_contact_document(customer)

	if not device.get("existing_name"):
		_validate_device_payload(device)

	if not (service_order.get("reported_defect") or "").strip():
		frappe.throw(_("Informe o defeito relatado."), frappe.ValidationError)
	if not (service_order.get("physical_state") or "").strip():
		frappe.throw(_("Informe o estado físico declarado."), frappe.ValidationError)
	if not _is_image_data_url(entry_photo.get("data_url")):
		frappe.throw(_("Anexe ao menos uma foto de entrada."), frappe.ValidationError)
	if not _is_image_data_url(data.get("entry_signature")):
		frappe.throw(_("Assinatura de entrada é obrigatória."), frappe.ValidationError)


def _validate_device_payload(data: dict[str, Any]) -> None:
	if not (data.get("brand") or "").strip():
		frappe.throw(_("Informe a marca do aparelho."), frappe.ValidationError)
	if not (data.get("model") or "").strip():
		frappe.throw(_("Informe o modelo do aparelho."), frappe.ValidationError)
	if not (data.get("imei_serial") or "").strip():
		frappe.throw(_("IMEI/serial é obrigatório para cadastrar aparelho."), frappe.ValidationError)


def _get_or_create_checkin_customer(data: dict[str, Any]) -> str:
	existing_name = (data.get("existing_name") or "").strip()
	if existing_name:
		if not frappe.db.exists("Customer", existing_name):
			frappe.throw(_("Cliente selecionado não existe."), frappe.ValidationError)
		return existing_name

	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": data["customer_name"].strip(),
			"customer_type": "Individual",
			"mobile_no": (data.get("mobile_no") or "").strip(),
			"custom_whatsapp": (data.get("custom_whatsapp") or data.get("mobile_no") or "").strip(),
			"custom_cpf": (data.get("custom_cpf") or "").strip(),
			"custom_rg": (data.get("custom_rg") or "").strip(),
			CUSTOMER_NO_CPF_FIELD: 1 if data.get(CUSTOMER_NO_CPF_FIELD) else 0,
			"email_id": (data.get("email_id") or "").strip(),
		}
	)
	customer.insert(ignore_permissions=True)
	return customer.name


def _get_or_create_checkin_device(data: dict[str, Any], customer_name: str) -> str:
	existing_name = (data.get("existing_name") or "").strip()
	if existing_name:
		device = frappe.db.get_value("Customer Device", existing_name, ["customer", "imei_serial"], as_dict=True)
		customer = device.customer if device else None
		if device and not (device.imei_serial or "").strip():
			frappe.throw(_("Aparelho selecionado não possui IMEI/serial."), frappe.ValidationError)
		if not customer:
			frappe.throw(_("Aparelho selecionado não existe."), frappe.ValidationError)
		if customer != customer_name:
			frappe.throw(_("O aparelho selecionado não pertence ao cliente informado."), frappe.ValidationError)
		return existing_name

	device = frappe.get_doc(
		{
			"doctype": "Customer Device",
			"customer": customer_name,
			"brand": data["brand"].strip(),
			"model": data["model"].strip(),
			"color": (data.get("color") or "").strip(),
			"imei_serial": data["imei_serial"].strip(),
			"capacity": (data.get("capacity") or "").strip(),
			"general_state": (data.get("general_state") or "").strip(),
			"registration_date": today(),
		}
	)
	device.insert(ignore_permissions=True)
	return device.name


def _save_checkin_photo(service_order: str, photo: dict[str, str]) -> str:
	filename = _safe_filename(photo.get("filename") or f"{service_order}-entrada.png")
	if "." not in filename:
		filename = f"{filename}.png"
	file_doc = save_file(
		filename,
		photo["data_url"],
		"Service Order",
		service_order,
		decode=True,
		is_private=0,
		df="entry_photos",
	)
	return file_doc.file_url


def _save_customer_device_photo(customer_device: str, photo: dict[str, str]) -> str:
	filename = _safe_filename(photo.get("filename") or f"{customer_device}-foto.png")
	if "." not in filename:
		filename = f"{filename}.png"
	file_doc = save_file(
		filename,
		photo["data_url"],
		"Customer Device",
		customer_device,
		decode=True,
		is_private=0,
		df="photos",
	)
	return file_doc.file_url


def _is_image_data_url(value: str | None) -> bool:
	return bool(value and isinstance(value, str) and value.startswith("data:image/") and "," in value)


def _safe_filename(value: str) -> str:
	name = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
	return name or "entrada.png"


def _serialize_service_row(row: Any) -> dict[str, Any]:
	qty = flt(row.get("qty") or 0)
	unit_price = flt(row.get("rate") or 0)
	return {
		"item_code": row.get("item_code"),
		"description": row.get("description"),
		"qty": qty,
		"unit_price": unit_price,
		"amount": flt(qty * unit_price),
		"technician": row.get("technician"),
	}


def _serialize_part_row(row: Any) -> dict[str, Any]:
	qty = flt(row.get("qty") or 0)
	unit_price = flt(row.get("rate") or 0)
	return {
		"item_code": row.get("item_code"),
		"description": row.get("description"),
		"qty": qty,
		"unit_price": unit_price,
		"amount": flt(qty * unit_price),
		"warehouse": row.get("warehouse"),
		"outcome": row.get("outcome"),
		"loss_reason": row.get("loss_reason"),
	}


def _get_customer_detail(customer: str | None) -> dict[str, Any] | None:
	if not customer:
		return None
	item = frappe.db.get_value(
		"Customer",
		customer,
		["name", "customer_name", "mobile_no", "custom_whatsapp", "custom_cpf", "custom_rg", CUSTOMER_NO_CPF_FIELD, "email_id"],
		as_dict=True,
	)
	return dict(item) if item else {"name": customer, "customer_name": customer}


def _customer_label(customer: str | None) -> str:
	item = _get_customer_detail(customer)
	if not item:
		return ""
	return item.get("customer_name") or item.get("name") or ""


def _get_device_detail(customer_device: str | None) -> dict[str, Any] | None:
	if not customer_device:
		return None
	item = frappe.db.get_value(
		"Customer Device",
		customer_device,
		["name", "customer", "brand", "model", "color", "imei_serial", "capacity", "photos"],
		as_dict=True,
	)
	return dict(item) if item else {"name": customer_device}


def _get_sales_invoice_status(sales_invoice: str | None) -> str | None:
	if not sales_invoice:
		return None
	return frappe.db.get_value("Sales Invoice", sales_invoice, "status")


def _get_allowed_kanban_action(current_state: str | None, target_state: str) -> str:
	user_roles = set(frappe.get_roles(frappe.session.user))
	matching_transitions = []
	for transition in _get_service_order_transitions():
		state, action, next_state, allowed, *rest = transition
		condition = rest[0] if rest else None
		if state == current_state and next_state == target_state and condition != "False":
			matching_transitions.append((action, allowed))

	if not matching_transitions:
		frappe.throw(
			_("Transição não permitida no Kanban: {0} → {1}.").format(current_state or "Sem status", target_state),
			frappe.ValidationError,
		)

	for action, allowed in matching_transitions:
		if allowed in user_roles or "System Manager" in user_roles:
			return action

	frappe.throw(
		_("Seu papel não permite mover esta OS de {0} para {1}.").format(current_state or "Sem status", target_state),
		frappe.PermissionError,
	)


def _get_visible_workflow_actions(doc: Any) -> list[dict[str, str]]:
	user_roles = set(frappe.get_roles(frappe.session.user))
	actions: list[dict[str, str]] = []
	for transition in _get_service_order_transitions():
		state, action, next_state, allowed, *rest = transition
		condition = rest[0] if rest else None
		if state != doc.get("workflow_state"):
			continue
		if condition == "False":
			continue
		if allowed not in user_roles and "System Manager" not in user_roles:
			continue
		actions.append(
			{
				"action": action,
				"next_state": next_state,
				"role": allowed,
			}
		)
	return actions


def _get_service_order_transition_options(current_state: str | None) -> list[dict[str, str]]:
	"""Expose workflow-valid destinations only; execution permission remains server-side."""
	options: list[dict[str, str]] = []
	seen: set[tuple[str, str]] = set()
	for transition in _get_service_order_transitions():
		state, action, next_state, allowed, *rest = transition
		condition = rest[0] if rest else None
		key = (action, next_state)
		if state != current_state or condition == "False" or key in seen:
			continue
		seen.add(key)
		options.append({"action": action, "next_state": next_state, "role": allowed})
	return options


def _get_service_order_timeline(doc: Any) -> list[dict[str, str]]:
	timeline = [
		{
			"title": "Entrada criada",
			"detail": doc.get("reported_defect") or "Atendimento aberto no balcão",
			"date": str(doc.get("entry_date") or doc.get("creation") or ""),
			"tone": "blue",
		}
	]
	if doc.get("problem_found") or doc.get("diagnosis_date"):
		timeline.append(
			{
				"title": "Diagnóstico",
				"detail": doc.get("problem_found") or "Diagnóstico registrado",
				"date": str(doc.get("diagnosis_date") or ""),
				"tone": "amber",
			}
		)
	timeline.extend(_get_quote_send_timeline_events(doc))
	if doc.get("approval_status") and doc.get("approval_status") != "Pendente":
		timeline.append(
			{
				"title": "Aprovação",
				"detail": doc.get("approval_status"),
				"date": str(doc.get("approval_date") or ""),
				"tone": "green" if doc.get("approval_status") == "Aprovado" else "red",
			}
		)
	timeline.append(
		{
			"title": "Status atual",
			"detail": doc.get("workflow_state") or "Sem status",
			"date": str(doc.get("modified") or ""),
			"tone": "orange",
		}
	)
	if doc.get("pickup_date"):
		timeline.append(
			{
				"title": "Retirada",
				"detail": doc.get("picked_up_by") or "Cliente retirou o aparelho",
				"date": str(doc.get("pickup_date") or ""),
				"tone": "green",
			}
		)
	return timeline


def _get_quote_send_timeline_events(doc: Any) -> list[dict[str, str]]:
	communications = frappe.get_all(
		"Communication",
		filters={
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"subject": ["like", "Orçamento enviado%"],
		},
		fields=["communication_medium", "text_content", "communication_date", "creation"],
		order_by="communication_date asc, creation asc",
		limit_page_length=20,
	)
	events: list[dict[str, str]] = []
	for communication in communications:
		events.append(
			{
				"title": "Orçamento enviado",
				"detail": _quote_send_timeline_detail(communication),
				"date": str(communication.communication_date or communication.creation or ""),
				"tone": "amber",
			}
		)
	return events


def _quote_send_timeline_detail(communication: Any) -> str:
	medium_label = {
		"Chat": "WhatsApp",
		"Phone": "Telefone",
		"Visit": "Presencial",
		"Email": "E-mail",
	}.get(communication.communication_medium, communication.communication_medium or "Canal registrado")
	text = (communication.text_content or "").splitlines()
	note = next((line.replace("Observação:", "").strip() for line in text if line.startswith("Observação:")), "")
	return f"{medium_label}{f' · {note}' if note else ''}"


def _get_service_order_print_links(name: str) -> list[dict[str, str]]:
	return [
		_print_link(name, "Termo de entrada", PF_TERMO_ENTRADA),
		_print_link(name, "Orçamento", PF_OS_ORCAMENTO),
		_print_link(name, "Etiqueta QR", PF_ETIQUETA_QR),
		_print_link(name, "Termo de retirada", PF_TERMO_RETIRADA),
	]


def _print_link(name: str, label: str, print_format: str) -> dict[str, str]:
	return {
		"label": label,
		"format": print_format,
		"url": (
			"/printview?"
			"doctype=Service%20Order"
			f"&name={quote(name)}"
			f"&format={quote(print_format)}"
			"&no_letterhead=0"
		),
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


def contains_sensitive_field(payload: Any, forbidden_values: list[float] | tuple[float, ...] | set[float] | None = None) -> list[str]:
	found: set[str] = set()
	forbidden_amounts = {round(flt(value), 4) for value in (forbidden_values or []) if abs(flt(value)) > 0.0001}

	def matches_forbidden_amount(value: Any) -> bool:
		if not forbidden_amounts or isinstance(value, bool):
			return False
		if isinstance(value, (int, float)):
			return round(flt(value), 4) in forbidden_amounts
		if isinstance(value, str):
			normalized = value.strip().replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
			if not re.fullmatch(r"-?\d+(\.\d+)?", normalized):
				return False
			return round(flt(normalized), 4) in forbidden_amounts
		return False

	def walk(value: Any, path: str = "") -> None:
		if isinstance(value, dict):
			for key, nested in value.items():
				normalized = key.lower()
				if normalized in SENSITIVE_FIELD_NAMES:
					found.add(key)
				if "cost" in normalized or "margin" in normalized or "commission" in normalized:
					found.add(key)
				child_path = f"{path}.{key}" if path else str(key)
				walk(nested, child_path)
		elif isinstance(value, (list, tuple)):
			for index, nested in enumerate(value):
				walk(nested, f"{path}[{index}]")
		elif matches_forbidden_amount(value):
			found.add(path or "<root>")

	walk(payload)
	return sorted(found)
