import re

import frappe

from tecponto_app.tecponto.pos import (
	BARCODE_SOURCE_FIELD,
	BARCODE_SOURCE_INTERNAL,
	BARCODE_SOURCE_MANUFACTURER,
	BARCODE_SYMBOLOGY_CODE128,
	BARCODE_SYMBOLOGY_FIELD,
)


MOVING_AVERAGE = "Moving Average"
VALUATION_ROOT_ITEM_GROUPS = ("Peças de Reparo", "Produtos de Varejo", "Aparelhos Usados")


def _get_settings_warehouse(fieldname: str) -> str | None:
	return frappe.db.get_single_value("Tecponto Settings", fieldname)


def _get_repair_warehouse() -> str | None:
	return _get_settings_warehouse("repair_warehouse")


def _get_commercial_warehouse() -> str | None:
	return _get_settings_warehouse("commercial_warehouse")


def _get_operational_warehouses() -> set[str]:
	return {warehouse for warehouse in (_get_repair_warehouse(), _get_commercial_warehouse()) if warehouse}


def _user_has_any_role(roles: set[str]) -> bool:
	return bool(set(frappe.get_roles()).intersection(roles))


def _get_valuation_item_groups() -> set[str]:
	item_groups = set()

	for item_group in VALUATION_ROOT_ITEM_GROUPS:
		bounds = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=True)
		if not bounds:
			continue

		item_groups.update(
			frappe.get_all(
				"Item Group",
				filters={
					"lft": [">=", bounds.lft],
					"rgt": ["<=", bounds.rgt],
				},
				pluck="name",
			)
		)

	return item_groups


def _item_group_uses_moving_average(item_group: str | None = None) -> bool:
	return bool(item_group and item_group in _get_valuation_item_groups())


def _stock_entry_warehouses(doc) -> set[str]:
	warehouses = {doc.get("from_warehouse"), doc.get("to_warehouse")}

	for item in doc.get("items") or []:
		warehouses.add(item.get("s_warehouse"))
		warehouses.add(item.get("t_warehouse"))

	return {warehouse for warehouse in warehouses if warehouse}


def apply_service_order_stock_defaults(doc, method=None) -> None:
	repair_warehouse = _get_repair_warehouse()
	if not repair_warehouse:
		return

	for part in doc.get("parts") or []:
		if not part.get("warehouse"):
			part.warehouse = repair_warehouse


def apply_sales_stock_defaults(doc, method=None) -> None:
	commercial_warehouse = _get_commercial_warehouse()
	if not commercial_warehouse:
		return

	if doc.meta.has_field("set_warehouse") and not doc.get("set_warehouse"):
		doc.set_warehouse = commercial_warehouse

	for item in doc.get("items") or []:
		if item.get("warehouse") or not item.get("item_code"):
			continue

		if frappe.get_cached_value("Item", item.item_code, "is_stock_item"):
			item.warehouse = commercial_warehouse


def apply_item_valuation_defaults(doc, method=None) -> None:
	if doc.get("is_stock_item") and _item_group_uses_moving_average(doc.get("item_group")):
		doc.valuation_method = MOVING_AVERAGE


def normalize_barcode(value: str | None) -> str:
	"""Scanners may append whitespace; never coerce a barcode to a number."""
	return re.sub(r"\s+", "", str(value or ""))[:140]


def validate_item_barcodes(doc, method=None) -> None:
	"""Give the operator a useful conflict before the native unique index rejects it."""
	seen: set[str] = set()
	for row in doc.get("barcodes") or []:
		barcode = normalize_barcode(row.get("barcode"))
		if not barcode:
			continue
		row.barcode = barcode
		if barcode in seen:
			frappe.throw("O mesmo código foi informado duas vezes neste item.")
		seen.add(barcode)

		source = row.get(BARCODE_SOURCE_FIELD)
		if source and source not in {BARCODE_SOURCE_MANUFACTURER, BARCODE_SOURCE_INTERNAL}:
			frappe.throw("Origem do código de barras inválida.")
		if source == BARCODE_SOURCE_INTERNAL and row.get(BARCODE_SYMBOLOGY_FIELD) != BARCODE_SYMBOLOGY_CODE128:
			frappe.throw("Código interno Tecponto deve usar a simbologia Code-128.")

		conflict = frappe.db.get_value(
			"Item Barcode",
			{"barcode": barcode, "parent": ["!=", doc.name or ""]},
			"parent",
		)
		if conflict:
			item_name = frappe.db.get_value("Item", conflict, "item_name") or conflict
			frappe.throw(
				"Código já cadastrado: {0} ({1}). Confira a embalagem ou gere uma etiqueta interna.".format(
					item_name, conflict
				)
			)


def validate_transfer_role(doc, method=None) -> None:
	is_material_transfer = (
		doc.get("stock_entry_type") == "Material Transfer" or doc.get("purpose") == "Material Transfer"
	)
	if not is_material_transfer:
		return
	# Operational staff may prepare a draft. The approval gate protects the
	# stock movement itself, which only exists after submission.
	if int(doc.get("docstatus") or 0) != 1:
		return

	operational_warehouses = _get_operational_warehouses()
	if not operational_warehouses:
		return

	if not (_stock_entry_warehouses(doc) & operational_warehouses):
		return

	if (
		frappe.session.user == "Administrator"
		or _user_has_any_role({"Tecponto Gestor", "System Manager"})
	):
		return

	frappe.throw("Transferencia entre estoques exige o Gestor.")


def ensure_moving_average_valuation() -> None:
	if frappe.db.exists("DocType", "Tecponto Settings"):
		frappe.db.set_single_value("Tecponto Settings", "valuation_method", MOVING_AVERAGE)

	item_groups = _get_valuation_item_groups()
	if not item_groups:
		return

	if frappe.get_meta("Item Group").has_field("valuation_method"):
		for item_group in item_groups:
			frappe.db.set_value(
				"Item Group",
				item_group,
				"valuation_method",
				MOVING_AVERAGE,
				update_modified=False,
			)

	for item in frappe.get_all(
		"Item",
		filters={
			"is_stock_item": 1,
			"item_group": ["in", list(item_groups)],
		},
		fields=["name", "valuation_method"],
	):
		if item.valuation_method != MOVING_AVERAGE:
			frappe.db.set_value(
				"Item",
				item.name,
				"valuation_method",
				MOVING_AVERAGE,
				update_modified=False,
			)
