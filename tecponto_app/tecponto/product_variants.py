from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.controllers.item_variant import create_variant

from tecponto_app.tecponto.pos import (
	BARCODE_SOURCE_FIELD,
	BARCODE_SOURCE_MANUFACTURER,
	BARCODE_SYMBOLOGY_CODE128,
	BARCODE_SYMBOLOGY_FIELD,
	get_retail_item_groups,
)
from tecponto_app.tecponto.product_categories import require_category_editor


VARIANT_ATTRIBUTES = ("Cor", "Modelo compatível", "Capacidade", "Tamanho")
ATTRIBUTE_SEEDS = {
	"Cor": (("Preto", "PT"), ("Branco", "BR"), ("Azul", "AZ")),
	"Modelo compatível": (("iPhone 13", "IP13"), ("iPhone 14", "IP14")),
	"Capacidade": (("64GB", "64"), ("128GB", "128")),
	"Tamanho": (("P", "P"), ("M", "M"), ("G", "G")),
}


def ensure_product_variant_attributes() -> None:
	"""Seed only native Item Attribute documents; existing manager values are preserved."""
	for attribute, values in ATTRIBUTE_SEEDS.items():
		if frappe.db.exists("Item Attribute", attribute):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Item Attribute",
				"attribute_name": attribute,
				"numeric_values": 0,
				"item_attribute_values": [
					{"attribute_value": value, "abbr": abbreviation} for value, abbreviation in values
				],
			}
		)
		doc.insert(ignore_permissions=True)
	frappe.clear_cache(doctype="Item Attribute")


def list_product_variant_attributes() -> list[dict[str, Any]]:
	ensure_product_variant_attributes()
	result = []
	for name in VARIANT_ATTRIBUTES:
		doc = frappe.get_doc("Item Attribute", name)
		result.append(
			{
				"name": doc.name,
				"disabled": bool(doc.disabled),
				"values": [
					{"value": row.attribute_value, "abbreviation": row.abbr}
					for row in doc.item_attribute_values
				],
			}
		)
	return result


def save_product_variant_attribute(name: str, values: Iterable[dict[str, Any]], disabled: bool = False) -> dict[str, Any]:
	"""Append/maintain native values without deleting values used by existing variants."""
	require_category_editor()
	name = (name or "").strip()
	if name not in VARIANT_ATTRIBUTES:
		frappe.throw(_("Atributo de variação inválido."), frappe.ValidationError)
	ensure_product_variant_attributes()
	doc = frappe.get_doc("Item Attribute", name)
	existing = {row.attribute_value for row in doc.item_attribute_values}
	for raw in values or []:
		value = str(raw.get("value") or "").strip()[:140]
		if not value or value in existing:
			continue
		abbreviation = str(raw.get("abbreviation") or frappe.scrub(value).upper()[:20]).strip()[:140]
		if not abbreviation:
			frappe.throw(_("Informe uma abreviação para cada valor."), frappe.ValidationError)
		doc.append("item_attribute_values", {"attribute_value": value, "abbr": abbreviation})
		existing.add(value)
	doc.disabled = cint(disabled)
	doc.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Item Attribute")
	return next(item for item in list_product_variant_attributes() if item["name"] == name)


def create_product_with_variants(payload: dict[str, Any]) -> dict[str, Any]:
	"""Create a native non-stock template and its independently sellable variants."""
	require_category_editor()
	ensure_product_variant_attributes()
	data = payload or {}
	template_code = _text(data.get("template_code"), "Código do produto pai")
	template_name = _text(data.get("template_name"), "Nome do produto pai")
	item_group = _text(data.get("item_group"), "Categoria")
	stock_uom = _text(data.get("stock_uom") or "Nos", "Unidade de estoque")
	attributes = _normalize_template_attributes(data.get("attributes"))
	variants = _normalize_variants(data.get("variants"), attributes)

	if frappe.db.exists("Item", template_code):
		frappe.throw(_("Já existe um Item com este código de produto pai."), frappe.ValidationError)
	if item_group not in set(get_retail_item_groups()):
		frappe.throw(_("Selecione uma categoria de varejo ativa e sem subcategorias."), frappe.ValidationError)
	if not frappe.db.exists("UOM", stock_uom):
		frappe.throw(_("Unidade de estoque inválida."), frappe.ValidationError)

	frappe.db.savepoint("tecponto_product_variants")
	try:
		template = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": template_code,
				"item_name": template_name,
				"item_group": item_group,
				"stock_uom": stock_uom,
				"has_variants": 1,
				"variant_based_on": "Item Attribute",
				"is_stock_item": 0,
				"is_sales_item": 0,
				"attributes": [{"attribute": name} for name in attributes],
			}
		)
		template.insert(ignore_permissions=True)

		created = []
		for variant_data in variants:
			variant = create_variant(template.name, variant_data["attributes"])
			variant.item_code = variant_data["sku"]
			variant.item_name = _variant_name(template_name, variant_data["attributes"])
			variant.item_group = item_group
			variant.stock_uom = stock_uom
			variant.is_stock_item = 1
			variant.is_sales_item = 1
			variant.disabled = 0
			# Item.after_insert creates Item Price without propagating the endpoint's
			# controlled context. Persist the public selling price after insertion.
			variant.standard_rate = 0
			variant.append(
				"barcodes",
				{
					"barcode": variant_data["gtin"],
					"barcode_type": "",
					BARCODE_SYMBOLOGY_FIELD: BARCODE_SYMBOLOGY_CODE128,
					BARCODE_SOURCE_FIELD: BARCODE_SOURCE_MANUFACTURER,
					"uom": stock_uom,
				},
			)
			variant.insert(ignore_permissions=True)
			_save_variant_sale_price(variant, variant_data["price"])
			created.append(_serialize_variant(variant))
	except Exception:
		frappe.db.rollback(save_point="tecponto_product_variants")
		raise

	return {"template": _serialize_template(template), "variants": created}


def list_variant_products(limit: int = 50) -> list[dict[str, Any]]:
	ensure_product_variant_attributes()
	rows = frappe.get_all(
		"Item",
		filters={"has_variants": 1, "item_group": ["in", get_retail_item_groups()]},
		fields=["name", "item_name", "item_group", "disabled"],
		order_by="modified desc",
		limit_page_length=max(1, min(int(limit or 50), 100)),
	)
	return [_serialize_template(frappe.get_doc("Item", row.name), include_variants=True) for row in rows]


def _normalize_template_attributes(raw_attributes: Any) -> list[str]:
	if not isinstance(raw_attributes, list):
		frappe.throw(_("Selecione ao menos um atributo de variação."), frappe.ValidationError)
	attributes = []
	for raw in raw_attributes:
		name = str(raw.get("name") if isinstance(raw, dict) else raw or "").strip()
		if name and name not in attributes:
			attributes.append(name)
	if not attributes or any(name not in VARIANT_ATTRIBUTES for name in attributes):
		frappe.throw(_("Selecione atributos de variação válidos."), frappe.ValidationError)
	return attributes


def _normalize_variants(raw_variants: Any, attributes: list[str]) -> list[dict[str, Any]]:
	if not isinstance(raw_variants, list) or not raw_variants:
		frappe.throw(_("Gere ao menos uma variação."), frappe.ValidationError)
	result = []
	seen_combinations: set[tuple[tuple[str, str], ...]] = set()
	seen_skus: set[str] = set()
	seen_gtins: set[str] = set()
	for raw in raw_variants:
		if not isinstance(raw, dict):
			continue
		values = raw.get("attributes") or {}
		if not isinstance(values, dict):
			frappe.throw(_("Valores de variação inválidos."), frappe.ValidationError)
		combination = {name: str(values.get(name) or "").strip()[:140] for name in attributes}
		if any(not value for value in combination.values()):
			frappe.throw(_("Preencha todos os atributos de cada variação."), frappe.ValidationError)
		for name, value in combination.items():
			if not frappe.db.exists("Item Attribute Value", {"parent": name, "attribute_value": value}):
				frappe.throw(_("{0} não é um valor válido para {1}.").format(value, name), frappe.ValidationError)
		sku = _text(raw.get("sku"), "SKU da variação")
		gtin = _text(raw.get("gtin"), "GTIN/EAN da variação")
		if frappe.db.exists("Item", sku) or sku in seen_skus:
			frappe.throw(_("SKU de variação já existe: {0}.").format(sku), frappe.ValidationError)
		if frappe.db.exists("Item Barcode", {"barcode": gtin}) or gtin in seen_gtins:
			frappe.throw(_("GTIN/EAN já existe: {0}.").format(gtin), frappe.ValidationError)
		price = flt(raw.get("price"), 2)
		if price < 0:
			frappe.throw(_("Preço da variação não pode ser negativo."), frappe.ValidationError)
		key = tuple(sorted(combination.items()))
		if key in seen_combinations:
			frappe.throw(_("Há combinações de atributos duplicadas."), frappe.ValidationError)
		seen_combinations.add(key)
		seen_skus.add(sku)
		seen_gtins.add(gtin)
		result.append({"attributes": combination, "sku": sku, "gtin": gtin, "price": price})
	if not result:
		frappe.throw(_("Gere ao menos uma variação válida."), frappe.ValidationError)
	return result


def _serialize_template(item, include_variants: bool = False) -> dict[str, Any]:
	result = {
		"item_code": item.name,
		"item_name": item.item_name,
		"item_group": item.item_group,
		"disabled": bool(item.disabled),
		"attributes": [row.attribute for row in item.get("attributes") or []],
	}
	if include_variants:
		variants = frappe.get_all("Item", filters={"variant_of": item.name}, pluck="name", order_by="item_name asc")
		result["variants"] = [_serialize_variant(frappe.get_doc("Item", name)) for name in variants]
	return result


def _serialize_variant(item) -> dict[str, Any]:
	warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	quantity = flt(frappe.db.get_value("Bin", {"item_code": item.name, "warehouse": warehouse}, "actual_qty"), 3)
	barcode = next((row.barcode for row in item.get("barcodes") or [] if row.barcode), None)
	return {
		"item_code": item.name,
		"item_name": item.item_name,
		"sku": item.name,
		"gtin": barcode,
		"price": flt(item.standard_rate, 2),
		"available_qty": quantity,
		"attributes": {row.attribute: row.attribute_value for row in item.get("attributes") or []},
	}


def _save_variant_sale_price(item, price: float) -> None:
	"""Save only the variant's public selling price and native Item Price."""
	price = flt(price, 2)
	frappe.db.set_value("Item", item.name, "standard_rate", price, update_modified=False)
	item.standard_rate = price
	price_list = frappe.get_single_value("Selling Settings", "selling_price_list") or frappe.db.get_value(
		"Price List", {"selling": 1}, "name"
	)
	if not price_list:
		return
	filters = {"price_list": price_list, "item_code": item.name, "uom": item.stock_uom}
	if frappe.db.exists("Item Price", filters):
		frappe.db.set_value("Item Price", filters, "price_list_rate", price, update_modified=False)
		return
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"price_list": price_list,
			"item_code": item.name,
			"uom": item.stock_uom,
			"currency": frappe.defaults.get_global_default("currency"),
			"price_list_rate": price,
		}
	).insert(ignore_permissions=True)


def _variant_name(template_name: str, attributes: dict[str, str]) -> str:
	return "{} - {}".format(template_name, " / ".join(attributes.values()))[:140]


def _text(value: Any, label: str) -> str:
	text = str(value or "").strip()[:140]
	if not text:
		frappe.throw(_("{0} é obrigatório.").format(label), frappe.ValidationError)
	return text
