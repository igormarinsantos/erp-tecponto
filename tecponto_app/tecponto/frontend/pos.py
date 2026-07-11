from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_days, flt, nowdate
from frappe.utils.pdf import get_pdf

from tecponto_app.tecponto.pos import (
	CARD_PAYMENT_MODES,
	POS_PAYMENT_MODES,
	POS_PROFILE_NAME,
	POS_RECEIPT_PRINT_FORMAT,
	_company_currency,
	_cost_center,
	_default_company,
	_expense_account,
	_income_account,
	_selling_price_list,
	get_commercial_item_groups,
)
from tecponto_app.tecponto.pricing import validate_discount_limit, validate_price_floor


POS_SALE_ROLES = {"Tecponto Atendente", "Tecponto Gestor", "System Manager"}
IDEMPOTENCY_DOCTYPE = "Tecponto POS Sale Request"
IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$")


@frappe.whitelist()
def pos_create_sale(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Create one submitted POS sale from server-owned prices, stock and accounts."""
	_require_pos_sale_role()
	data = _parse_payload(payload)
	idempotency_key = _validate_idempotency_key(data.get("idempotency_key"))
	request = _normalize_request(data)
	request_hash = _request_hash(request)

	existing = _get_existing_request(idempotency_key, request_hash)
	if existing:
		return _sale_response(existing.sales_invoice, idempotent_replay=True)

	savepoint = f"tp_pos_{request_hash[:12]}"
	frappe.db.savepoint(savepoint)
	try:
		company = _default_company()
		warehouse = _commercial_warehouse()
		items, gross_total = _resolve_sale_items(request["items"], warehouse)
		discount_amount = _validate_discount(request["discount_amount"], gross_total)
		net_total = flt(gross_total - discount_amount, 2)
		_validate_effective_price_floor(items, gross_total, discount_amount, warehouse)
		payments, payment_metadata = _resolve_payments(request["payments"], net_total, company)

		idempotency_doc = frappe.get_doc(
			{
				"doctype": IDEMPOTENCY_DOCTYPE,
				"idempotency_key": idempotency_key,
				"request_hash": request_hash,
				"status": "Processing",
				"requested_by": frappe.session.user,
				"customer": request["customer"],
				"gross_total": gross_total,
				"discount_amount": discount_amount,
				"net_total": net_total,
				"payment_metadata": frappe.as_json(payment_metadata),
			}
		)
		idempotency_doc.insert(ignore_permissions=True)

		invoice = _create_sales_invoice(
			company=company,
			customer=request["customer"],
			warehouse=warehouse,
			items=items,
			discount_amount=discount_amount,
			payments=payments,
		)

		idempotency_doc.sales_invoice = invoice.name
		idempotency_doc.status = "Completed"
		idempotency_doc.save(ignore_permissions=True)
		return _sale_response(invoice.name, idempotent_replay=False)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


@frappe.whitelist()
def pos_download_receipt(sales_invoice: str) -> None:
	_require_pos_sale_role()
	request = frappe.db.get_value(
		IDEMPOTENCY_DOCTYPE,
		{"sales_invoice": sales_invoice, "status": "Completed"},
		["name", "requested_by"],
		as_dict=True,
	)
	if not request:
		raise frappe.PermissionError(_("Cupom não pertence ao PDV Tecponto."))

	roles = set(frappe.get_roles(frappe.session.user))
	can_audit = frappe.session.user == "Administrator" or bool(roles & {"Tecponto Gestor", "System Manager"})
	if request.requested_by != frappe.session.user and not can_audit:
		raise frappe.PermissionError(_("Você não pode abrir o cupom de outra sessão."))

	doc = frappe.get_doc("Sales Invoice", sales_invoice)
	print_format = frappe.get_doc("Print Format", POS_RECEIPT_PRINT_FORMAT)
	body = frappe.render_template(print_format.html, {"doc": doc, "frappe": frappe})
	pdf = get_pdf(f"<style>{print_format.css or ''}</style>{body}")
	frappe.local.response.filename = f"Cupom-{sales_invoice}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"


def _require_pos_sale_role() -> None:
	user = frappe.session.user
	if not user or user == "Guest":
		raise frappe.AuthenticationError(_("Faça login para finalizar a venda."))
	if user == "Administrator":
		return
	if not set(frappe.get_roles(user)) & POS_SALE_ROLES:
		raise frappe.PermissionError(_("Seu papel não permite finalizar vendas no PDV Tecponto."))


def _parse_payload(payload: str | dict[str, Any] | None) -> dict[str, Any]:
	if isinstance(payload, str):
		try:
			payload = json.loads(payload)
		except (TypeError, ValueError):
			frappe.throw(_("Dados da venda inválidos."), frappe.ValidationError)
	if not isinstance(payload, dict):
		frappe.throw(_("Dados da venda não informados."), frappe.ValidationError)
	return payload


def _validate_idempotency_key(value: Any) -> str:
	key = str(value or "").strip()
	if not IDEMPOTENCY_KEY_PATTERN.fullmatch(key):
		frappe.throw(_("Referência idempotente da venda inválida."), frappe.ValidationError)
	return key


def _normalize_request(data: dict[str, Any]) -> dict[str, Any]:
	customer = str(data.get("customer") or "").strip()
	if not customer or not frappe.db.exists("Customer", customer):
		frappe.throw(_("Selecione um cliente válido para finalizar a venda."), frappe.ValidationError)

	item_totals: dict[tuple[str, str], float] = {}
	for raw_item in data.get("items") or []:
		if not isinstance(raw_item, dict):
			continue
		item_code = str(raw_item.get("item_code") or "").strip()
		serial_no = str(raw_item.get("serial_no") or "").strip()
		qty = flt(raw_item.get("qty"), 3)
		if not item_code or qty <= 0:
			frappe.throw(_("Produto e quantidade são obrigatórios em todas as linhas."), frappe.ValidationError)
		key = (item_code, serial_no)
		item_totals[key] = flt(item_totals.get(key, 0) + qty, 3)
	if not item_totals:
		frappe.throw(_("Adicione ao menos um produto à venda."), frappe.ValidationError)

	payment_totals: dict[tuple[str, int], float] = {}
	for raw_payment in data.get("payments") or []:
		if not isinstance(raw_payment, dict):
			continue
		mode = str(raw_payment.get("mode_of_payment") or "").strip()
		amount = flt(raw_payment.get("amount"), 2)
		installments = max(1, int(raw_payment.get("installments") or 1))
		if not mode or amount <= 0:
			frappe.throw(_("Forma e valor do pagamento são obrigatórios."), frappe.ValidationError)
		key = (mode, installments)
		payment_totals[key] = flt(payment_totals.get(key, 0) + amount, 2)
	if not payment_totals:
		frappe.throw(_("Informe ao menos uma forma de pagamento."), frappe.ValidationError)

	return {
		"customer": customer,
		"discount_amount": flt(data.get("discount_amount"), 2),
		"items": [
			{"item_code": item_code, "qty": qty, "serial_no": serial_no or None}
			for (item_code, serial_no), qty in sorted(item_totals.items())
		],
		"payments": [
			{"mode_of_payment": mode, "amount": amount, "installments": installments}
			for (mode, installments), amount in sorted(payment_totals.items())
		],
	}


def _request_hash(request: dict[str, Any]) -> str:
	canonical = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
	return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _get_existing_request(idempotency_key: str, request_hash: str):
	if not frappe.db.exists(IDEMPOTENCY_DOCTYPE, idempotency_key):
		return None
	doc = frappe.get_doc(IDEMPOTENCY_DOCTYPE, idempotency_key)
	if doc.requested_by != frappe.session.user and frappe.session.user != "Administrator":
		raise frappe.PermissionError(_("Esta referência de venda pertence a outra sessão."))
	if doc.request_hash != request_hash:
		frappe.throw(_("A referência já foi usada com dados diferentes."), frappe.ValidationError)
	if doc.status != "Completed" or not doc.sales_invoice:
		frappe.throw(_("Esta venda ainda está sendo processada. Aguarde antes de reenviar."), frappe.ValidationError)
	if frappe.db.get_value("Sales Invoice", doc.sales_invoice, "docstatus") != 1:
		frappe.throw(_("A venda vinculada a esta referência não está válida."), frappe.ValidationError)
	return doc


def _commercial_warehouse() -> str:
	warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	if not warehouse:
		frappe.throw(_("Depósito Comercial não configurado no Tecponto Settings."), frappe.ValidationError)
	return warehouse


def _resolve_sale_items(raw_items: list[dict[str, Any]], warehouse: str) -> tuple[list[dict[str, Any]], float]:
	allowed_groups = set(get_commercial_item_groups())
	if not allowed_groups:
		frappe.throw(_("Grupos comerciais do PDV não estão configurados."), frappe.ValidationError)

	items: list[dict[str, Any]] = []
	gross_total = 0.0
	for raw in raw_items:
		item = frappe.db.get_value(
			"Item",
			raw["item_code"],
			["name", "item_name", "item_group", "stock_uom", "is_stock_item", "is_sales_item", "disabled", "has_serial_no", "standard_rate"],
			as_dict=True,
		)
		if not item or item.disabled or not item.is_stock_item or not item.is_sales_item:
			frappe.throw(_("O item {0} não está habilitado para venda.").format(raw["item_code"]), frappe.ValidationError)
		if item.item_group not in allowed_groups:
			frappe.throw(_("O item {0} não pertence ao catálogo Comercial.").format(item.name), frappe.ValidationError)

		qty = flt(raw["qty"], 3)
		available_qty = flt(frappe.db.get_value("Bin", {"item_code": item.name, "warehouse": warehouse}, "actual_qty"))
		if available_qty < qty:
			frappe.throw(_("Estoque Comercial insuficiente para {0}.").format(item.item_name or item.name), frappe.ValidationError)

		serial_no = raw.get("serial_no")
		if item.has_serial_no and not serial_no:
			frappe.throw(_("Informe o Serial / IMEI do item {0}.").format(item.item_name or item.name), frappe.ValidationError)
		if item.has_serial_no and qty != 1:
			frappe.throw(_("Cada aparelho serializado deve ser vendido em uma linha unitária."), frappe.ValidationError)

		rate = flt(item.standard_rate, 2)
		if rate <= 0:
			frappe.throw(_("O item {0} está sem preço de venda cadastrado.").format(item.item_name or item.name), frappe.ValidationError)
		amount = flt(rate * qty, 2)
		gross_total = flt(gross_total + amount, 2)
		items.append(
			{
				"item_code": item.name,
				"item_name": item.item_name,
				"qty": qty,
				"uom": item.stock_uom,
				"rate": rate,
				"amount": amount,
				"serial_no": serial_no,
			}
		)
	return items, gross_total


def _validate_discount(discount_amount: float, gross_total: float) -> float:
	discount = flt(discount_amount, 2)
	if discount < 0 or discount >= gross_total:
		frappe.throw(_("O desconto deve ser menor que o subtotal da venda."), frappe.ValidationError)
	validate_discount_limit(discount)
	return discount


def _validate_effective_price_floor(
	items: list[dict[str, Any]], gross_total: float, discount_amount: float, warehouse: str
) -> None:
	factor = (gross_total - discount_amount) / gross_total if gross_total else 0
	for item in items:
		validate_price_floor(flt(item["rate"] * factor, 6), item["item_code"], warehouse)


def _resolve_payments(raw_payments: list[dict[str, Any]], net_total: float, company: str):
	if abs(sum(flt(payment["amount"], 2) for payment in raw_payments) - net_total) > 0.01:
		frappe.throw(_("A soma dos pagamentos deve ser igual ao total da venda."), frappe.ValidationError)

	clearing_account = frappe.db.get_single_value("Tecponto Settings", "acquirer_clearing_account")
	payments: list[dict[str, Any]] = []
	metadata: list[dict[str, Any]] = []
	for payment in raw_payments:
		mode = payment["mode_of_payment"]
		installments = int(payment["installments"])
		if mode not in POS_PAYMENT_MODES:
			frappe.throw(_("Forma de pagamento {0} não permitida no PDV.").format(mode), frappe.ValidationError)
		if mode == "Crédito parcelado" and installments < 2:
			frappe.throw(_("Crédito parcelado exige ao menos 2 parcelas."), frappe.ValidationError)
		if mode != "Crédito parcelado" and installments != 1:
			frappe.throw(_("Número de parcelas inválido para {0}.").format(mode), frappe.ValidationError)

		account = frappe.db.get_value(
			"Mode of Payment Account",
			{"parent": mode, "company": company},
			"default_account",
		)
		if not account:
			frappe.throw(_("Conta contábil não configurada para {0}.").format(mode), frappe.ValidationError)
		if mode in CARD_PAYMENT_MODES and account != clearing_account:
			frappe.throw(_("Pagamento em cartão deve usar a conta transitória configurada."), frappe.ValidationError)

		amount = flt(payment["amount"], 2)
		fee_pct, settlement_days = _card_fee(mode, installments)
		fee_amount = flt(amount * fee_pct / 100, 2)
		payments.append({"mode_of_payment": mode, "amount": amount, "account": account, "type": "Bank" if mode != "Dinheiro" else "Cash"})
		metadata.append(
			{
				"mode_of_payment": mode,
				"amount": amount,
				"installments": installments,
				"account": account,
				"fee_pct": fee_pct,
				"fee_amount": fee_amount,
				"net_settlement": flt(amount - fee_amount, 2),
				"settlement_days": settlement_days,
				"expected_settlement_date": add_days(nowdate(), settlement_days),
			}
		)
	return payments, metadata


def _card_fee(mode: str, installments: int) -> tuple[float, int]:
	if mode not in CARD_PAYMENT_MODES:
		return 0.0, 0
	fee_type = mode
	if mode == "Crédito parcelado":
		fee_type = "Crédito 2x" if installments == 2 else "Crédito 3x+"
	row = frappe.db.get_value(
		"Tecponto Card Fee",
		{"parent": "Tecponto Settings", "parenttype": "Tecponto Settings", "tipo": fee_type},
		["taxa_pct", "settlement_days"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Taxa e prazo de {0} não configurados.").format(fee_type), frappe.ValidationError)
	return flt(row.taxa_pct), int(row.settlement_days or 0)


def _create_sales_invoice(
	*, company: str, customer: str, warehouse: str, items: list[dict[str, Any]], discount_amount: float, payments: list[dict[str, Any]]
):
	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": company,
			"customer": customer,
			"posting_date": nowdate(),
			"due_date": nowdate(),
			"is_pos": 1,
			"update_stock": 1,
			"pos_profile": POS_PROFILE_NAME,
			"set_warehouse": warehouse,
			"selling_price_list": _selling_price_list(),
			"currency": _company_currency(company),
			"apply_discount_on": "Grand Total",
			"discount_amount": discount_amount,
		}
	)
	income_account = _income_account(company)
	expense_account = _expense_account(company)
	cost_center = _cost_center(company)
	for item in items:
		invoice.append(
			"items",
			{
				"item_code": item["item_code"],
				"item_name": item["item_name"],
				"qty": item["qty"],
				"uom": item["uom"],
				"stock_uom": item["uom"],
				"conversion_factor": 1,
				"rate": item["rate"],
				"price_list_rate": item["rate"],
				"warehouse": warehouse,
				"serial_no": item["serial_no"],
				"income_account": income_account,
				"expense_account": expense_account,
				"cost_center": cost_center,
			},
		)
	for payment in payments:
		invoice.append("payments", payment)

	invoice.flags.ignore_permissions = True
	invoice.insert(ignore_permissions=True)
	invoice.submit()
	return invoice


def _sale_response(sales_invoice: str, *, idempotent_replay: bool) -> dict[str, Any]:
	doc = frappe.get_doc("Sales Invoice", sales_invoice)
	return {
		"sale": doc.name,
		"status": "Concluída",
		"posting_date": str(doc.posting_date),
		"customer": doc.customer,
		"customer_name": doc.customer_name,
		"grand_total": flt(doc.grand_total, 2),
		"paid_amount": flt(doc.paid_amount, 2),
		"idempotent_replay": idempotent_replay,
		"items": [
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": flt(row.qty, 3),
				"unit_price": flt(row.rate, 2),
				"amount": flt(row.amount, 2),
			}
			for row in doc.items
		],
		"payments": [
			{"mode_of_payment": row.mode_of_payment, "amount": flt(row.amount, 2)}
			for row in doc.payments
			if flt(row.amount)
		],
		"receipt": {
			"format": POS_RECEIPT_PRINT_FORMAT,
			"url": "/api/method/tecponto_app.tecponto.frontend.pos.pos_download_receipt?sales_invoice={0}".format(
				quote(doc.name)
			),
		},
	}
