import frappe
from frappe.utils import flt

from tecponto_app.tecponto.user_access import INDIVIDUAL_DISCOUNT_LIMIT_FIELD


MANAGER_ROLES = {"Tecponto Gestor", "System Manager"}


def _user_can_override_pricing() -> bool:
	return frappe.session.user == "Administrator" or bool(set(frappe.get_roles()) & MANAGER_ROLES)


def _get_discount_limit() -> float:
	if frappe.db.has_column("User", INDIVIDUAL_DISCOUNT_LIMIT_FIELD):
		individual_limit = flt(frappe.db.get_value("User", frappe.session.user, INDIVIDUAL_DISCOUNT_LIMIT_FIELD) or 0)
		if individual_limit > 0:
			return individual_limit
	return flt(frappe.db.get_single_value("Tecponto Settings", "discount_limit"))


def _is_price_floor_enabled() -> bool:
	return bool(frappe.db.get_single_value("Tecponto Settings", "price_floor_block"))


def _is_stock_item(item_code: str | None) -> bool:
	return bool(item_code and frappe.get_cached_value("Item", item_code, "is_stock_item"))


def _get_valuation_rate(item_code: str | None, warehouse: str | None = None) -> float:
	if not item_code:
		return 0

	if warehouse:
		valuation_rate = frappe.db.get_value(
			"Bin",
			{"item_code": item_code, "warehouse": warehouse},
			"valuation_rate",
		)
		if valuation_rate is not None:
			return flt(valuation_rate)

	return flt(frappe.get_cached_value("Item", item_code, "valuation_rate"))


def _throw_price_floor() -> None:
	frappe.throw("Este preco fica abaixo do piso comercial permitido e exige aprovacao do Gestor.")


def _throw_discount_limit(discount_total: float, discount_limit: float) -> None:
	frappe.throw(
		"Desconto acima do limite ({0}) exige aprovacao do Gestor.".format(
			frappe.format_value(discount_limit, {"fieldtype": "Currency"})
		)
	)


def validate_price_floor(rate, item_code, warehouse=None) -> None:
	if not _is_price_floor_enabled() or not _is_stock_item(item_code):
		return

	cost = _get_valuation_rate(item_code, warehouse)
	if cost and flt(rate) < cost and not _user_can_override_pricing():
		_throw_price_floor()


def validate_discount_limit(discount_total) -> None:
	discount_limit = _get_discount_limit()
	if discount_limit <= 0:
		return

	if flt(discount_total) > discount_limit and not _user_can_override_pricing():
		_throw_discount_limit(flt(discount_total), discount_limit)


def _row_amount(row) -> float:
	return flt(row.get("qty")) * flt(row.get("rate"))


def _invoice_item_discount(row) -> float:
	qty = flt(row.get("qty"))
	discount_amount = flt(row.get("discount_amount"))
	if discount_amount:
		return discount_amount * qty

	discount_percentage = flt(row.get("discount_percentage"))
	if not discount_percentage:
		return 0

	base_rate = flt(row.get("price_list_rate")) or flt(row.get("rate_with_margin")) or flt(row.get("rate"))
	return base_rate * qty * discount_percentage / 100


def _invoice_discount_total(doc) -> float:
	item_discounts = sum(_invoice_item_discount(row) for row in doc.get("items") or [])
	return item_discounts + flt(doc.get("discount_amount"))


def validate_service_order_pricing(doc, method=None) -> None:
	labor_total = sum(_row_amount(row) for row in doc.get("services") or [])
	parts_total = 0

	for part in doc.get("parts") or []:
		rate = flt(part.get("rate"))
		qty = flt(part.get("qty"))
		cost = _get_valuation_rate(part.get("item_code"), part.get("warehouse"))
		part.valuation_rate = cost
		parts_total += qty * rate
		# Warranty parts carry real valuation and stock movement, but are not a
		# customer sale. A zero customer rate must therefore not be treated as a
		# below-cost discount request.
		if not doc.get("is_warranty"):
			validate_price_floor(rate, part.get("item_code"), part.get("warehouse"))

	discount = flt(doc.get("discount"))
	doc.labor_total = labor_total
	doc.parts_total = parts_total
	doc.grand_total = max(labor_total + parts_total - discount, 0)

	validate_discount_limit(discount)


def validate_sales_pricing(doc, method=None) -> None:
	for item in doc.get("items") or []:
		validate_price_floor(
			item.get("rate"),
			item.get("item_code"),
			item.get("warehouse") or doc.get("set_warehouse"),
		)

	validate_discount_limit(_invoice_discount_total(doc))
