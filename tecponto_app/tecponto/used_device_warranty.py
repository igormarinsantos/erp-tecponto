from __future__ import annotations

import frappe
from frappe.utils import add_days, flt, getdate, nowdate


ITEM_GROUP_USED_DEVICES = "Aparelhos Usados"
WARRANTY_COVERAGE = "Defeito de fábrica"
DEFAULT_WARRANTY_DAYS = 90
WARRANTY_LOOKUP_ROLES = {"System Manager", "Tecponto Atendente", "Tecponto Gestor"}


def validate_used_device_serials(doc, method=None) -> None:
	if doc.get("is_return"):
		return

	for item in doc.get("items") or []:
		if not _is_used_device_item(item.get("item_code")):
			continue

		serials = _serials_from_row(item)
		if not serials:
			frappe.throw(
				"Venda de aparelho usado exige Serial/IMEI na linha {0}.".format(item.get("idx"))
			)

		qty = abs(flt(item.get("stock_qty")) or flt(item.get("qty")))
		if qty and len(serials) != int(qty):
			frappe.throw(
				"Quantidade de Serial/IMEI nao confere com a quantidade vendida na linha {0}.".format(
					item.get("idx")
				)
			)

		for serial_no in serials:
			_validate_serial_matches_item(serial_no, item.get("item_code"))


def create_used_device_warranties(doc, method=None) -> list[str]:
	if doc.get("is_return") or doc.docstatus != 1:
		return []

	created_or_updated = []
	for item in doc.get("items") or []:
		if not _is_used_device_item(item.get("item_code")):
			continue

		for serial_no in _serials_from_row(item):
			created_or_updated.append(_upsert_warranty(doc, item, serial_no))

	return created_or_updated


@frappe.whitelist()
def consultar_garantia_usado(serial_no: str, reference_date: str | None = None) -> dict:
	"""Internal counter lookup; knowing an IMEI is never sufficient authorization."""
	_require_warranty_lookup_role()
	serial_no = (serial_no or "").strip()
	if not serial_no:
		frappe.throw("Informe o Serial/IMEI.", frappe.ValidationError)
	reference = getdate(reference_date or nowdate())
	warranty_name = frappe.db.get_value(
		"Used Device Warranty",
		{"serial_no": serial_no},
		"name",
		order_by="sale_date desc, creation desc",
	)
	if not warranty_name:
		return {
			"serial_no": serial_no,
			"exists": False,
			"under_warranty": False,
		}

	warranty = frappe.get_doc("Used Device Warranty", warranty_name)
	warranty.check_permission("read")
	expiry = getdate(warranty.warranty_expiry)
	return {
		"name": warranty.name,
		"serial_no": warranty.serial_no,
		"customer": warranty.customer,
		"item_code": warranty.item_code,
		"sales_invoice": warranty.sales_invoice,
		"sale_date": warranty.sale_date,
		"warranty_expiry": warranty.warranty_expiry,
		"coverage": warranty.coverage,
		"exists": True,
		"under_warranty": expiry >= reference,
	}


def _require_warranty_lookup_role() -> None:
	if frappe.session.user == "Guest":
		frappe.throw("Faça login para consultar garantias.", frappe.PermissionError)
	roles = set(frappe.get_roles(frappe.session.user))
	if frappe.session.user == "Administrator" or roles.intersection(WARRANTY_LOOKUP_ROLES):
		return
	frappe.throw("Usuário sem permissão para consultar garantias de aparelhos usados.", frappe.PermissionError)


def _upsert_warranty(doc, item, serial_no: str) -> str:
	sale_date = getdate(doc.get("posting_date") or nowdate())
	warranty_days = _warranty_days()
	warranty_expiry = add_days(sale_date, warranty_days)

	existing = frappe.db.get_value(
		"Used Device Warranty",
		{"serial_no": serial_no, "sales_invoice": doc.name},
		"name",
	)
	if existing:
		warranty = frappe.get_doc("Used Device Warranty", existing)
	else:
		warranty = frappe.new_doc("Used Device Warranty")

	warranty.serial_no = serial_no
	warranty.customer = doc.get("customer")
	warranty.item_code = item.get("item_code")
	warranty.sales_invoice = doc.name
	warranty.sales_invoice_item = item.get("name")
	warranty.sale_date = sale_date
	warranty.warranty_days = warranty_days
	warranty.warranty_expiry = warranty_expiry
	warranty.coverage = WARRANTY_COVERAGE
	warranty.save(ignore_permissions=True)

	if frappe.db.exists("Serial No", serial_no):
		frappe.db.set_value(
			"Serial No",
			serial_no,
			{
				"warranty_expiry_date": warranty_expiry,
			},
			update_modified=False,
		)

	return warranty.name


def _serials_from_row(item) -> list[str]:
	serials = []
	if item.get("serial_no"):
		serials.extend(_split_serials(item.get("serial_no")))

	bundle = item.get("serial_and_batch_bundle")
	if bundle and frappe.db.exists("Serial and Batch Bundle", bundle):
		serials.extend(
			frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": bundle, "serial_no": ["is", "set"]},
				pluck="serial_no",
				order_by="idx asc",
			)
		)

	if not serials and item.get("pos_invoice_item"):
		pos_row = frappe.db.get_value(
			"POS Invoice Item",
			item.get("pos_invoice_item"),
			["serial_no", "serial_and_batch_bundle"],
			as_dict=True,
		)
		if pos_row:
			serials.extend(_split_serials(pos_row.serial_no))
			if pos_row.serial_and_batch_bundle and frappe.db.exists(
				"Serial and Batch Bundle", pos_row.serial_and_batch_bundle
			):
				serials.extend(
					frappe.get_all(
						"Serial and Batch Entry",
						filters={
							"parent": pos_row.serial_and_batch_bundle,
							"serial_no": ["is", "set"],
						},
						pluck="serial_no",
						order_by="idx asc",
					)
				)

	return list(dict.fromkeys(serials))


def _split_serials(serials: str | list[str] | tuple[str, ...] | None) -> list[str]:
	if not serials:
		return []
	if isinstance(serials, (list, tuple)):
		return [serial.strip() for serial in serials if serial and serial.strip()]
	return [
		serial.strip()
		for serial in str(serials).replace(",", "\n").split("\n")
		if serial.strip()
	]


def _validate_serial_matches_item(serial_no: str, item_code: str | None) -> None:
	serial_item = frappe.db.get_value("Serial No", serial_no, "item_code")
	if serial_item and serial_item != item_code:
		frappe.throw("Serial/IMEI {0} nao pertence ao item {1}.".format(serial_no, item_code))


def _is_used_device_item(item_code: str | None) -> bool:
	if not item_code:
		return False

	item_group = frappe.get_cached_value("Item", item_code, "item_group")
	if not item_group:
		return False
	if item_group == ITEM_GROUP_USED_DEVICES:
		return True

	root = frappe.db.get_value(
		"Item Group",
		ITEM_GROUP_USED_DEVICES,
		["lft", "rgt"],
		as_dict=True,
	)
	current = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=True)
	if not root or not current:
		return False

	return current.lft >= root.lft and current.rgt <= root.rgt


def _warranty_days() -> int:
	days = frappe.db.get_single_value("Tecponto Settings", "used_device_warranty_days")
	return int(days or DEFAULT_WARRANTY_DAYS)
