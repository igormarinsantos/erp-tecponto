from __future__ import annotations

import re
import unicodedata

import frappe
from frappe.utils import flt, nowdate

from tecponto_app.tecponto.tradein.buyback import _default_company, ensure_serial_batch_for_used_devices


STATE_COMPRADO = "Comprado"
DESTINATION_PARTS = "pecas"
DESTINATION_REPAIR = "reparo"
DESTINATION_COMMERCIAL = "comercial"
DESTINATION_DISCARD = "descarte"
STOCK_ENTRY_TYPE_REPACK = "Repack"


def canibalizar(doc, method=None) -> None:
	if doc.get("workflow_state") != STATE_COMPRADO:
		return

	if _normalize(doc.get("destination")) != DESTINATION_PARTS:
		return

	if not doc.get("created_item") or not doc.get("harvest_parts"):
		return

	if _existing_repack(doc):
		return

	_validate_canibalization(doc)
	repack = _criar_repack(doc)
	repack.insert(ignore_permissions=True)
	repack.submit()


def _criar_repack(doc):
	ensure_serial_batch_for_used_devices()

	warehouse_used = _used_devices_warehouse()
	repack = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": STOCK_ENTRY_TYPE_REPACK,
			"purpose": STOCK_ENTRY_TYPE_REPACK,
			"company": _default_company(),
			"posting_date": nowdate(),
			"remarks": _repack_reference(doc),
		}
	)
	repack.append(
		"items",
		{
			"item_code": doc.created_item,
			"qty": 1,
			"s_warehouse": warehouse_used,
			"serial_no": doc.imei,
			"basic_rate": _used_device_cost(doc, warehouse_used),
		},
	)

	for part, rate in _ratear_custo(doc):
		batch_no = _ensure_batch(doc, part)
		repack.append(
			"items",
			{
				"item_code": part.item_code,
				"qty": flt(part.qty),
				"t_warehouse": _warehouse_for_part(part),
				"basic_rate": rate,
				"set_basic_rate_manually": 1,
				"batch_no": batch_no,
			},
		)

	return repack


def _validate_canibalization(doc) -> None:
	if not doc.get("imei"):
		frappe.throw("Canibalização exige IMEI do doador.")

	if not frappe.db.exists("Item", doc.get("created_item")):
		frappe.throw("Canibalização exige item usado criado.")

	if not _serial_in_used_stock(doc):
		frappe.throw("Aparelho usado não está disponível no estoque de usados.")

	produced_parts = [part for part in doc.get("harvest_parts") if not _is_discarded(part)]
	if not produced_parts:
		frappe.throw("Canibalização exige ao menos uma peça estocada.")

	total_expected = sum(_expected_total(part) for part in produced_parts)
	if total_expected <= 0:
		frappe.throw("Rateio exige valor esperado maior que zero nas peças estocadas.")

	for part in produced_parts:
		if flt(part.get("qty")) <= 0:
			frappe.throw("Peça colhida exige quantidade maior que zero.")

		if _normalize(part.get("destination")) not in {DESTINATION_REPAIR, DESTINATION_COMMERCIAL}:
			frappe.throw("Destino da peça deve ser Reparo ou Comercial.")

		if not frappe.db.exists("Item", part.get("item_code")):
			frappe.throw("Peça colhida não encontrada: {0}".format(part.get("item_code")))

		if not frappe.get_cached_value("Item", part.item_code, "has_batch_no"):
			frappe.throw("Peça colhida exige controle de lote: {0}".format(part.item_code))


def _ratear_custo(doc) -> list[tuple[object, float]]:
	produced_parts = [part for part in doc.get("harvest_parts") if not _is_discarded(part)]
	total_cost = _used_device_cost(doc, _used_devices_warehouse())
	total_expected = sum(_expected_total(part) for part in produced_parts)
	allocated_total = 0
	rates: list[tuple[object, float]] = []

	for index, part in enumerate(produced_parts):
		qty = flt(part.qty)
		if index == len(produced_parts) - 1:
			part_total = total_cost - allocated_total
		else:
			part_total = flt(total_cost * _expected_total(part) / total_expected, 2)
			allocated_total += part_total

		rates.append((part, flt(part_total / qty, 2)))

	return rates


def _expected_total(part) -> float:
	return flt(part.get("expected_value")) * flt(part.get("qty"))


def _used_device_cost(doc, warehouse: str) -> float:
	valuation_rate = frappe.db.get_value(
		"Bin",
		{"item_code": doc.get("created_item"), "warehouse": warehouse},
		"valuation_rate",
	)
	return flt(valuation_rate) or flt(doc.get("approved_value"))


def _warehouse_for_part(part) -> str:
	destination = _normalize(part.get("destination"))
	if destination == DESTINATION_REPAIR:
		warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
	elif destination == DESTINATION_COMMERCIAL:
		warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	else:
		frappe.throw("Destino da peça deve ser Reparo ou Comercial.")

	if not warehouse:
		frappe.throw("Warehouse de destino da peça não configurado.")

	return warehouse


def _ensure_batch(doc, part) -> str:
	batch_id = _batch_id(doc, part.item_code)
	if frappe.db.exists("Batch", batch_id):
		return batch_id

	batch = frappe.get_doc(
		{
			"doctype": "Batch",
			"batch_id": batch_id,
			"item": part.item_code,
			"manufacturing_date": nowdate(),
		}
	)
	batch.insert(ignore_permissions=True)
	return batch.name


def _batch_id(doc, item_code: str) -> str:
	return "{0}-{1}".format(_clean_code(doc.get("imei")), _clean_code(item_code))[:140]


def _serial_in_used_stock(doc) -> bool:
	serial = frappe.db.get_value("Serial No", doc.get("imei"), ["item_code", "warehouse"], as_dict=True)
	return bool(
		serial
		and serial.item_code == doc.get("created_item")
		and serial.warehouse == _used_devices_warehouse()
	)


def _used_devices_warehouse() -> str:
	warehouse = frappe.db.get_single_value("Tecponto Settings", "used_devices_warehouse")
	if not warehouse:
		frappe.throw("Warehouse de usados não configurado no Tecponto Settings.")
	return warehouse


def _existing_repack(doc) -> str | None:
	return frappe.db.get_value(
		"Stock Entry",
		{"docstatus": 1, "stock_entry_type": STOCK_ENTRY_TYPE_REPACK, "remarks": _repack_reference(doc)},
		"name",
	)


def _repack_reference(doc) -> str:
	return "Tecponto Repack {0}".format(doc.name)


def _is_discarded(part) -> bool:
	return bool(part.get("discard")) or _normalize(part.get("destination")) == DESTINATION_DISCARD


def _clean_code(value: str | None) -> str:
	cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value or "").strip("-").upper()
	return cleaned or frappe.generate_hash(length=8).upper()


def _normalize(value: str | None) -> str:
	normalized = unicodedata.normalize("NFKD", value or "")
	return "".join(char for char in normalized if not unicodedata.combining(char)).strip().lower()
