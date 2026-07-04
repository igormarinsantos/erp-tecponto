import json

import frappe


SERVICE_ORDER_DOCTYPE = "Service Order"
SERVICE_ORDER_KANBAN_NAME = "OS - Operacao"

KANBAN_CARD_FIELDS = [
	"name",
	"customer",
	"customer_device",
	"approval_deadline",
	"estimated_deadline",
]

KANBAN_COLUMNS = (
	("Entrada criada", "Active", "Gray"),
	("Em diagnóstico", "Active", "Light Blue"),
	("Aguardando aprovação", "Active", "Orange"),
	("Aguardando peça", "Active", "Purple"),
	("Em reparo", "Active", "Blue"),
	("Teste final", "Active", "Cyan"),
	("Pronto para retirada", "Active", "Green"),
	("Orçamento expirado", "Archived", "Red"),
	("Entregue", "Archived", "Green"),
	("Cancelado", "Archived", "Gray"),
	("Sem conserto", "Archived", "Red"),
)


def ensure_service_order_kanban() -> str:
	if frappe.db.exists("Kanban Board", SERVICE_ORDER_KANBAN_NAME):
		board = frappe.get_doc("Kanban Board", SERVICE_ORDER_KANBAN_NAME)
	else:
		board = frappe.new_doc("Kanban Board")
		board.kanban_board_name = SERVICE_ORDER_KANBAN_NAME

	changed = _set_if_changed(board, "reference_doctype", SERVICE_ORDER_DOCTYPE)
	changed |= _set_if_changed(board, "field_name", "workflow_state")
	changed |= _set_if_changed(board, "private", 0)
	changed |= _set_if_changed(board, "show_labels", 1)
	changed |= _set_if_changed(board, "fields", json.dumps(KANBAN_CARD_FIELDS))
	changed |= _sync_columns(board)

	if not board.is_new() and not changed:
		return board.name

	board.save(ignore_permissions=True)
	frappe.clear_cache(doctype=SERVICE_ORDER_DOCTYPE)
	return board.name


def _sync_columns(board) -> bool:
	existing_orders = {row.column_name: row.order or "[]" for row in board.get("columns") or []}
	current_columns = [
		(row.column_name, row.status, row.indicator)
		for row in board.get("columns") or []
	]

	if current_columns == list(KANBAN_COLUMNS):
		return False

	board.set("columns", [])
	for column_name, status, indicator in KANBAN_COLUMNS:
		board.append(
			"columns",
			{
				"column_name": column_name,
				"status": status,
				"indicator": indicator,
				"order": existing_orders.get(column_name, "[]"),
			},
		)

	return True


def _set_if_changed(doc, fieldname: str, value) -> bool:
	if doc.get(fieldname) == value:
		return False

	doc.set(fieldname, value)
	return True
