from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint, flt

from tecponto_app.tecponto.pos import get_retail_item_groups
from tecponto_app.tecponto.product_categories import USED_DEVICES_GROUP, require_category_editor
from tecponto_app.tecponto.product_variants import _save_variant_sale_price


LISTING_TITLE_FIELD = "custom_tecponto_listing_title"
LISTING_DESCRIPTION_FIELD = "custom_tecponto_listing_description"
LISTING_ONLINE_FIELD = "custom_tecponto_online_sellable"
LISTING_CONDITION_FIELD = "custom_tecponto_listing_condition"
LISTING_GRADE_FIELD = "custom_tecponto_listing_grade"
LISTING_LENGTH_FIELD = "custom_tecponto_package_length_cm"
LISTING_WIDTH_FIELD = "custom_tecponto_package_width_cm"
LISTING_HEIGHT_FIELD = "custom_tecponto_package_height_cm"
LISTING_IMAGES_FIELD = "custom_tecponto_listing_images"

ITEM_LISTING_FIELDS = {
	"Item": [
		{"fieldname": LISTING_ONLINE_FIELD, "fieldtype": "Check", "label": "Vendável online", "insert_after": "is_sales_item", "module": "Tecponto"},
		{"fieldname": LISTING_TITLE_FIELD, "fieldtype": "Data", "label": "Título de anúncio", "insert_after": LISTING_ONLINE_FIELD, "module": "Tecponto"},
		{"fieldname": LISTING_DESCRIPTION_FIELD, "fieldtype": "Text", "label": "Descrição de anúncio", "insert_after": LISTING_TITLE_FIELD, "module": "Tecponto"},
		{"fieldname": LISTING_CONDITION_FIELD, "fieldtype": "Select", "label": "Condição", "options": "\nNovo\nUsado", "insert_after": LISTING_DESCRIPTION_FIELD, "module": "Tecponto"},
		{"fieldname": LISTING_GRADE_FIELD, "fieldtype": "Select", "label": "Grade", "options": "\nA\nB\nC", "insert_after": LISTING_CONDITION_FIELD, "module": "Tecponto"},
		{"fieldname": LISTING_LENGTH_FIELD, "fieldtype": "Float", "label": "Comprimento da embalagem (cm)", "insert_after": LISTING_GRADE_FIELD, "module": "Tecponto"},
		{"fieldname": LISTING_WIDTH_FIELD, "fieldtype": "Float", "label": "Largura da embalagem (cm)", "insert_after": LISTING_LENGTH_FIELD, "module": "Tecponto"},
		{"fieldname": LISTING_HEIGHT_FIELD, "fieldtype": "Float", "label": "Altura da embalagem (cm)", "insert_after": LISTING_WIDTH_FIELD, "module": "Tecponto"},
		{"fieldname": LISTING_IMAGES_FIELD, "fieldtype": "Table", "label": "Fotos do anúncio", "options": "Tecponto Listing Image", "insert_after": LISTING_HEIGHT_FIELD, "module": "Tecponto"},
	]
}


def ensure_listing_metadata_fields() -> None:
	create_custom_fields(ITEM_LISTING_FIELDS, update=True)
	frappe.clear_cache(doctype="Item")


def save_listing_metadata(item_code: str, payload: dict[str, Any]) -> dict[str, Any]:
	require_category_editor()
	ensure_listing_metadata_fields()
	item = _get_sellable_item(item_code)
	data = payload or {}
	online_sellable = bool(cint(data.get("online_sellable")))
	listing_title = _text(data.get("listing_title"), 140)
	listing_description = _text(data.get("listing_description"), 4000)
	condition = _choice(data.get("condition"), {"", "Novo", "Usado"}, "Condição")
	grade = _choice(data.get("grade"), {"", "A", "B", "C"}, "Grade")
	weight = flt(data.get("weight_per_unit"), 3)
	public_price = flt(data.get("public_price"), 2)
	dimensions = {
		LISTING_LENGTH_FIELD: flt(data.get("package_length_cm"), 2),
		LISTING_WIDTH_FIELD: flt(data.get("package_width_cm"), 2),
		LISTING_HEIGHT_FIELD: flt(data.get("package_height_cm"), 2),
	}
	images = _normalize_images(data.get("images"))
	if online_sellable:
		if not listing_title or not listing_description or not condition:
			frappe.throw(_("Título, descrição e condição são obrigatórios para venda online."), frappe.ValidationError)
		if weight <= 0 or any(value <= 0 for value in dimensions.values()):
			frappe.throw(_("Informe peso e todas as dimensões da embalagem para venda online."), frappe.ValidationError)
		if not images:
			frappe.throw(_("Adicione ao menos uma foto para venda online."), frappe.ValidationError)
	item.set(LISTING_ONLINE_FIELD, cint(online_sellable))
	item.set(LISTING_TITLE_FIELD, listing_title)
	item.set(LISTING_DESCRIPTION_FIELD, listing_description)
	item.set(LISTING_CONDITION_FIELD, condition)
	item.set(LISTING_GRADE_FIELD, grade)
	item.weight_per_unit = weight
	item.weight_uom = "Kg" if weight else item.weight_uom
	for fieldname, value in dimensions.items():
		item.set(fieldname, value)
	item.set(LISTING_IMAGES_FIELD, [])
	for image in images:
		item.append(LISTING_IMAGES_FIELD, image)
	item.save(ignore_permissions=True)
	if "public_price" in data and public_price >= 0:
		_save_variant_sale_price(item, public_price)
	return serialize_listing_item(item)


def list_commercial_catalog(kind: str = "all", limit: int = 100) -> list[dict[str, Any]]:
	ensure_listing_metadata_fields()
	kind = (kind or "all").strip()
	if kind not in {"all", "shelf", "unique"}:
		frappe.throw(_("Tipo de catálogo inválido."), frappe.ValidationError)
	limit = max(1, min(cint(limit or 100), 200))
	retail_groups = set(get_retail_item_groups())
	used_groups = set(_descendant_groups(USED_DEVICES_GROUP))
	rows = frappe.get_all("Item", filters={"disabled": 0, "is_sales_item": 1}, fields=["name", "item_group", "variant_of", "has_serial_no"], order_by="modified desc", limit_page_length=0)
	commercial_warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	items = []
	for row in rows:
		is_shelf = bool(row.variant_of) and row.item_group in retail_groups
		is_unique_used = bool(row.has_serial_no) and row.item_group in used_groups
		if kind == "shelf" and not is_shelf:
			continue
		if kind == "unique" and not is_unique_used:
			continue
		if not (is_shelf or is_unique_used):
			continue
		quantity = flt(frappe.db.get_value("Bin", {"item_code": row.name, "warehouse": commercial_warehouse}, "actual_qty"), 3)
		if is_unique_used and quantity <= 0:
			continue
		item = frappe.get_doc("Item", row.name)
		items.append(serialize_listing_item(item, catalog_kind="shelf" if is_shelf else "unique", available_qty=quantity))
	return items[:limit]


def serialize_listing_item(item: Any, *, catalog_kind: str | None = None, available_qty: float | None = None) -> dict[str, Any]:
	images = [{"image": row.image, "caption": row.caption or ""} for row in (item.get(LISTING_IMAGES_FIELD) or []) if row.image]
	barcode = next((row.barcode for row in item.get("barcodes") or [] if row.barcode), None)
	serial_suffix = None
	if item.has_serial_no:
		serial = frappe.db.get_value("Serial No", {"item_code": item.name, "status": ["!=", "Delivered"]}, "name")
		if serial:
			serial_suffix = str(serial)[-4:]
	return {"item_code": item.name, "item_name": item.item_name, "catalog_kind": catalog_kind, "variant_of": item.variant_of or None, "sku": item.name, "gtin": barcode, "public_price": flt(item.standard_rate, 2), "available_qty": available_qty, "serial_suffix": serial_suffix, "online_sellable": bool(item.get(LISTING_ONLINE_FIELD)), "listing_title": item.get(LISTING_TITLE_FIELD) or "", "listing_description": item.get(LISTING_DESCRIPTION_FIELD) or "", "condition": item.get(LISTING_CONDITION_FIELD) or "", "grade": item.get(LISTING_GRADE_FIELD) or "", "weight_per_unit": flt(item.weight_per_unit, 3), "package_length_cm": flt(item.get(LISTING_LENGTH_FIELD), 2), "package_width_cm": flt(item.get(LISTING_WIDTH_FIELD), 2), "package_height_cm": flt(item.get(LISTING_HEIGHT_FIELD), 2), "images": images}


def _get_sellable_item(item_code: str):
	item_code = _text(item_code, 140)
	if not frappe.db.exists("Item", item_code):
		frappe.throw(_("Item não encontrado."), frappe.DoesNotExistError)
	item = frappe.get_doc("Item", item_code)
	retail_groups = set(get_retail_item_groups())
	used_groups = set(_descendant_groups(USED_DEVICES_GROUP))
	if not item.is_sales_item or not ((item.variant_of and item.item_group in retail_groups) or (item.has_serial_no and item.item_group in used_groups)):
		frappe.throw(_("Somente variações de varejo ou aparelhos usados únicos podem receber dados de anúncio."), frappe.ValidationError)
	return item


def _descendant_groups(parent: str) -> list[str]:
	doc = frappe.get_doc("Item Group", parent)
	return frappe.get_all("Item Group", filters={"lft": [">=", doc.lft], "rgt": ["<=", doc.rgt]}, pluck="name")


def _normalize_images(value: Any) -> list[dict[str, str]]:
	if not isinstance(value, list):
		return []
	items = []
	for raw in value:
		if isinstance(raw, dict):
			image = _text(raw.get("image"), 255)
			if image:
				items.append({"image": image, "caption": _text(raw.get("caption"), 140)})
	return items


def _choice(value: Any, allowed: set[str], label: str) -> str:
	text = _text(value, 20)
	if text not in allowed:
		frappe.throw(_("{0} inválida.").format(label), frappe.ValidationError)
	return text


def _text(value: Any, length: int) -> str:
	return str(value or "").strip()[:length]
