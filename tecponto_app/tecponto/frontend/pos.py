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

from tecponto_app.tecponto.cashier import CASHIER_OPERATOR_FIELD, identify_cashier_operator, resolve_cashier_operator
from tecponto_app.tecponto.pos import (
	BARCODE_SOURCE_FIELD,
	BARCODE_SOURCE_INTERNAL,
	BARCODE_SOURCE_MANUFACTURER,
	BARCODE_SYMBOLOGY_CODE128,
	BARCODE_SYMBOLOGY_EAN13,
	BARCODE_SYMBOLOGY_FIELD,
	CARD_PAYMENT_MODES,
	POS_PAYMENT_MODES,
	POS_BARCODE_LABEL_PRINT_FORMAT,
	POS_PROFILE_NAME,
	POS_RECEIPT_PRINT_FORMAT,
	_company_currency,
	_cost_center,
	_default_company,
	_expense_account,
	generate_item_barcode,
	get_item_barcode_label_context,
	_income_account,
	_selling_price_list,
	get_commercial_item_groups,
	get_retail_item_groups,
)
from tecponto_app.tecponto.pricing import validate_discount_limit, validate_price_floor
from tecponto_app.tecponto.stock import normalize_barcode


POS_SALE_ROLES = {"Tecponto Atendente", "Tecponto Gestor", "System Manager"}
INVENTORY_RECEIPT_ROLES = {"Tecponto Gestor", "System Manager"}
IDEMPOTENCY_DOCTYPE = "Tecponto POS Sale Request"
IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$")
CONSUMER_FINAL_CUSTOMER = "CONSUMIDOR FINAL"


@frappe.whitelist()
def pos_create_sale(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Create one submitted POS sale from server-owned prices, stock and accounts."""
	_require_pos_sale_role()
	data = _parse_payload(payload)
	idempotency_key = _validate_idempotency_key(data.get("idempotency_key"))
	cashier_operator = resolve_cashier_operator(data.get("cashier_operator_token"))
	request = _normalize_request(data, cashier_operator=cashier_operator)
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
				"cashier_operator": request["cashier_operator"],
				"cashier_identified_via": request["cashier_identified_via"],
				"customer": request["customer"],
				"gross_total": gross_total,
				"discount_amount": discount_amount,
				"net_total": net_total,
				"payment_metadata": frappe.as_json(payment_metadata),
			}
		)
		idempotency_doc.insert(ignore_permissions=True)

		invoice = _create_sales_invoice(
			cashier_operator=request["cashier_operator"],
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
def pos_identify_cashier_operator(badge_code: str = "", pin: str = "") -> dict[str, str]:
	"""Return a sale-attribution token. It never authenticates or changes permissions."""
	_require_pos_sale_role()
	return identify_cashier_operator(badge_code=badge_code, pin=pin)


@frappe.whitelist()
def pos_download_cashier_badge(operator: str) -> None:
	"""Render a small Code-128 badge through the same PDF path used by PDV labels."""
	_require_pos_sale_role()
	operator_doc = frappe.get_doc("Tecponto Cashier Operator", operator)
	roles = set(frappe.get_roles(frappe.session.user))
	can_manage_badges = frappe.session.user == "Administrator" or bool(roles & {"Tecponto Gestor", "System Manager"})
	if operator_doc.user != frappe.session.user and not can_manage_badges:
		raise frappe.PermissionError(_("Somente o proprio operador ou o Gestor pode imprimir este cracha."))
	if not operator_doc.active:
		raise frappe.PermissionError(_("Este cracha esta inativo."))
	user = frappe.db.get_value("User", operator_doc.user, ["full_name", "enabled"], as_dict=True)
	if not user or not user.enabled:
		raise frappe.PermissionError(_("O usuario deste cracha esta inativo."))
	from tecponto_app.tecponto.pos import barcode_svg_data_uri

	body = """
<div class="tp-barcode-label">
  <p class="tp-product">{name}</p>
  <p class="tp-price">CRACHA TEC PONTO</p>
  <img alt="Codigo do cracha" src="{image}">
  <p class="tp-code">{code}</p>
  <p class="tp-sku">Operador de caixa</p>
</div>
""".format(name=frappe.utils.escape_html(user.full_name or operator_doc.user), image=barcode_svg_data_uri(operator_doc.badge_code), code=frappe.utils.escape_html(operator_doc.badge_code))
	from tecponto_app.tecponto.pos import _barcode_label_css

	pdf = _render_barcode_label_pdf(body, _barcode_label_css())
	frappe.local.response.filename = f"Cracha-{operator_doc.user}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"


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


@frappe.whitelist()
def pos_generate_item_barcode(item_code: str) -> dict[str, Any]:
	_require_pos_sale_role()
	# Etiquetas internas servem aos itens de varejo controlados por quantidade.
	# Aparelhos com IMEI/Serial permanecem no fluxo proprio de rastreabilidade.
	item = _get_retail_item(item_code)
	barcode, created = generate_item_barcode(item)
	return {
		"item_code": item.name,
		"item_name": item.item_name or item.name,
		"barcode": barcode,
		"created": created,
		"label": {
			"format": POS_BARCODE_LABEL_PRINT_FORMAT,
			"url": _barcode_label_url(item.name),
		},
	}


@frappe.whitelist()
def pos_download_barcode_label(item_code: str) -> None:
	_require_pos_sale_role()
	item = _get_retail_item(item_code)
	if not any(row.barcode for row in item.get("barcodes") or []):
		frappe.throw(_("Gere o código de barras antes de imprimir a etiqueta."), frappe.ValidationError)

	print_format = frappe.get_doc("Print Format", POS_BARCODE_LABEL_PRINT_FORMAT)
	body = frappe.render_template(
		print_format.html,
		{
			"doc": item,
			"frappe": frappe,
			"get_item_barcode_label_context": get_item_barcode_label_context,
		},
	)
	pdf = _render_barcode_label_pdf(body, print_format.css or "")
	frappe.local.response.filename = f"Etiqueta-{frappe.scrub(item.name)}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline"


@frappe.whitelist()
def pos_lookup_retail_barcode(barcode: str) -> dict[str, Any]:
	"""Resolve a scanned code without creating an item as a side effect."""
	_require_pos_sale_role()
	value = normalize_barcode(barcode)
	if not value:
		frappe.throw(_("Escaneie ou informe um código de barras."), frappe.ValidationError)

	row = frappe.db.get_value(
		"Item Barcode",
		{"barcode": value},
		["parent", BARCODE_SOURCE_FIELD],
		as_dict=True,
	)
	if not row:
		return {"state": "unknown", "barcode": value}

	item = frappe.db.get_value(
		"Item",
		row.parent,
		["name", "item_name", "item_group", "disabled", "has_serial_no", "stock_uom", "standard_rate"],
		as_dict=True,
	)
	if not item:
		return {"state": "unknown", "barcode": value}
	return {
		"state": "disabled" if item.disabled else "found",
		"barcode": value,
		"barcode_source": row.get(BARCODE_SOURCE_FIELD) or None,
		"item": {
			"item_code": item.name,
			"item_name": item.item_name,
			"item_group": item.item_group,
			"has_serial_no": bool(item.has_serial_no),
			"stock_uom": item.stock_uom,
			"standard_rate": flt(item.standard_rate, 2),
		},
	}


@frappe.whitelist()
def pos_list_retail_item_groups() -> dict[str, Any]:
	_require_pos_sale_role()
	return {"items": [{"name": name} for name in get_retail_item_groups()]}


@frappe.whitelist()
def pos_register_retail_product(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Create one quantity-controlled retail item and attach its chosen barcode."""
	_require_pos_sale_role()
	data = _parse_payload(payload)
	item_code = str(data.get("item_code") or "").strip()[:140]
	item_name = str(data.get("item_name") or "").strip()[:140]
	item_group = str(data.get("item_group") or "").strip()
	stock_uom = str(data.get("stock_uom") or "").strip()[:140]
	source = str(data.get("barcode_source") or "").strip()
	barcode = normalize_barcode(data.get("barcode"))
	selling_rate = flt(data.get("selling_rate"), 2)

	if not item_code or not item_name or not item_group or not stock_uom:
		frappe.throw(_("Código do item, nome, grupo e unidade são obrigatórios."), frappe.ValidationError)
	if frappe.db.exists("Item", item_code):
		frappe.throw(_("Já existe um item com o código {0}.").format(item_code), frappe.ValidationError)
	if item_group not in set(get_retail_item_groups()):
		frappe.throw(_("Selecione um grupo de Produtos de Varejo."), frappe.ValidationError)
	if not frappe.db.exists("UOM", stock_uom):
		frappe.throw(_("Unidade de estoque inválida."), frappe.ValidationError)
	if selling_rate < 0:
		frappe.throw(_("Preço de venda não pode ser negativo."), frappe.ValidationError)
	if source not in {BARCODE_SOURCE_MANUFACTURER, BARCODE_SOURCE_INTERNAL}:
		frappe.throw(_("Selecione a origem do código de barras."), frappe.ValidationError)
	if source == BARCODE_SOURCE_MANUFACTURER and not barcode:
		frappe.throw(_("Escaneie o código da embalagem ou escolha código interno."), frappe.ValidationError)
	if source == BARCODE_SOURCE_MANUFACTURER:
		_assert_barcode_available(barcode)

	frappe.db.savepoint("tecponto_register_retail_product")
	try:
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_name,
				"item_group": item_group,
				"stock_uom": stock_uom,
				"is_stock_item": 1,
				"is_sales_item": 1,
				"has_serial_no": 0,
				"standard_rate": selling_rate,
			}
		)
		if source == BARCODE_SOURCE_MANUFACTURER:
			item.append(
				"barcodes",
				{
					"barcode": barcode,
					"barcode_type": _barcode_symbology(barcode),
					BARCODE_SYMBOLOGY_FIELD: _tecponto_symbology(barcode),
					BARCODE_SOURCE_FIELD: BARCODE_SOURCE_MANUFACTURER,
					"uom": stock_uom,
				},
			)
		# ERPNext creates an Item Price from Item.after_insert. Run that native
		# cascade as the system identity, then restore the caller immediately.
		# This does not grant or persist any role for the attendant.
		caller = frappe.session.user
		frappe.set_user("Administrator")
		try:
			item.insert(ignore_permissions=True)
		finally:
			frappe.set_user(caller)

		if source == BARCODE_SOURCE_INTERNAL:
			barcode, _created = generate_item_barcode(item, force_internal=True)
	except Exception:
		frappe.db.rollback(save_point="tecponto_register_retail_product")
		raise

	return {
		"item": {
			"item_code": item.name,
			"item_name": item.item_name,
			"item_group": item.item_group,
			"stock_uom": item.stock_uom,
			"has_serial_no": False,
			"standard_rate": flt(item.standard_rate, 2),
		},
		"barcode": barcode,
		"barcode_source": source,
		"label": {"format": POS_BARCODE_LABEL_PRINT_FORMAT, "url": _barcode_label_url(item.name)},
	}


@frappe.whitelist()
def pos_receive_retail_stock(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Receive quantity through ERPNext's stock ledger; never update Bin directly."""
	_require_inventory_receipt_role()
	data = _parse_payload(payload)
	item = _get_retail_item(str(data.get("item_code") or ""))
	qty = flt(data.get("qty"), 3)
	incoming_rate = flt(data.get("incoming_rate"), 6)
	if qty <= 0:
		frappe.throw(_("Quantidade recebida deve ser maior que zero."), frappe.ValidationError)
	if incoming_rate < 0:
		frappe.throw(_("Custo de entrada não pode ser negativo."), frappe.ValidationError)

	warehouse = _commercial_warehouse()
	before_qty = flt(frappe.db.get_value("Bin", {"item_code": item.name, "warehouse": warehouse}, "actual_qty"), 3)
	entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"purpose": "Material Receipt",
			"company": _default_company(),
			"posting_date": nowdate(),
			"remarks": f"Entrada por leitura de código - {item.name}",
			"items": [
				{
					"item_code": item.name,
					"qty": qty,
					"t_warehouse": warehouse,
					"basic_rate": incoming_rate,
					"set_basic_rate_manually": 1,
				}
			],
		}
	)
	entry.insert(ignore_permissions=True)
	entry.submit()
	after_qty = flt(frappe.db.get_value("Bin", {"item_code": item.name, "warehouse": warehouse}, "actual_qty"), 3)
	return {
		"stock_entry": entry.name,
		"item_code": item.name,
		"warehouse": warehouse,
		"qty_before": before_qty,
		"qty_received": qty,
		"qty_after": after_qty,
	}


def _require_pos_sale_role() -> None:
	user = frappe.session.user
	if not user or user == "Guest":
		raise frappe.AuthenticationError(_("Faça login para finalizar a venda."))
	if user == "Administrator":
		return
	if not set(frappe.get_roles(user)) & POS_SALE_ROLES:
		raise frappe.PermissionError(_("Seu papel não permite finalizar vendas no PDV Tecponto."))


def _require_inventory_receipt_role() -> None:
	_require_pos_sale_role()
	if frappe.session.user == "Administrator" or set(frappe.get_roles(frappe.session.user)) & INVENTORY_RECEIPT_ROLES:
		return
	raise frappe.PermissionError(_("Somente o Gestor pode registrar entrada de estoque com custo."))


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


def _normalize_request(data: dict[str, Any], *, cashier_operator: dict[str, str] | None = None) -> dict[str, Any]:
	customer = str(data.get("customer") or "").strip()
	if not customer:
		customer = _get_or_create_consumer_final_customer()
	elif not frappe.db.exists("Customer", customer):
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
		"cashier_identified_via": cashier_operator["via"] if cashier_operator else None,
		"cashier_operator": cashier_operator["operator"] if cashier_operator else None,
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


def _get_or_create_consumer_final_customer() -> str:
	"""Return the single anonymous counter-sale party, without personal data."""
	if frappe.db.exists("Customer", CONSUMER_FINAL_CUSTOMER):
		return CONSUMER_FINAL_CUSTOMER

	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": "Consumidor Final",
			"customer_type": "Individual",
		}
	)
	customer.flags.tecponto_consumer_final = True
	customer.insert(ignore_permissions=True, set_name=CONSUMER_FINAL_CUSTOMER)
	return customer.name


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


def _get_commercial_item(item_code: str):
	item_code = str(item_code or "").strip()
	if not item_code or not frappe.db.exists("Item", item_code):
		frappe.throw(_("Item não encontrado."), frappe.ValidationError)
	item = frappe.get_doc("Item", item_code)
	if item.disabled or not item.is_stock_item or not item.is_sales_item:
		frappe.throw(_("Item não está habilitado para venda."), frappe.ValidationError)
	if item.item_group not in set(get_commercial_item_groups()):
		frappe.throw(_("Somente itens do catálogo Comercial podem receber etiqueta no PDV."), frappe.ValidationError)
	return item


def _get_retail_item(item_code: str):
	item = _get_commercial_item(item_code)
	if item.item_group not in set(get_retail_item_groups()):
		frappe.throw(_("Entrada por leitura é restrita a Produtos de Varejo."), frappe.ValidationError)
	if item.has_serial_no:
		frappe.throw(_("Aparelhos serializados devem usar o fluxo próprio de IMEI/Serial."), frappe.ValidationError)
	return item


def _barcode_symbology(barcode: str) -> str:
	return "EAN-13" if _is_valid_ean13(barcode) else ""


def _tecponto_symbology(barcode: str) -> str:
	return BARCODE_SYMBOLOGY_EAN13 if _is_valid_ean13(barcode) else BARCODE_SYMBOLOGY_CODE128


def _is_valid_ean13(barcode: str) -> bool:
	"""Use EAN-13 only for a genuine factory EAN; retain other scanned codes as Code-128."""
	if len(barcode) != 13 or not barcode.isdigit():
		return False
	checksum = sum(int(digit) * (1 if index % 2 == 0 else 3) for index, digit in enumerate(barcode[:12]))
	return (10 - checksum % 10) % 10 == int(barcode[12])


def _assert_barcode_available(barcode: str) -> None:
	"""Give a useful conflict while the database index remains the concurrency guard."""
	existing_item = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")
	if not existing_item:
		return
	item_name = frappe.db.get_value("Item", existing_item, "item_name") or existing_item
	frappe.throw(
		_("Código já cadastrado: {0} ({1}). Confira a embalagem ou gere uma etiqueta interna.").format(
			item_name, existing_item
		),
		frappe.ValidationError,
	)


def _barcode_label_url(item_code: str) -> str:
	return "/api/method/tecponto_app.tecponto.frontend.pos.pos_download_barcode_label?item_code={0}".format(
		quote(item_code)
	)


def _render_barcode_label_pdf(body: str, css: str) -> bytes:
	import pdfkit

	html = "<!doctype html><html><head><meta charset='utf-8'><style>{0}</style></head><body>{1}</body></html>".format(
		css,
		body,
	)
	return pdfkit.from_string(
		html,
		False,
		options={
			"page-width": "50mm",
			"page-height": "30mm",
			"margin-top": "0mm",
			"margin-bottom": "0mm",
			"margin-left": "0mm",
			"margin-right": "0mm",
			"encoding": "UTF-8",
			"disable-javascript": "",
			"disable-local-file-access": "",
			"disable-smart-shrinking": "",
			"quiet": "",
		},
	)


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
	*, cashier_operator: str | None, company: str, customer: str, warehouse: str, items: list[dict[str, Any]], discount_amount: float, payments: list[dict[str, Any]]
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
	if cashier_operator:
		invoice.set(CASHIER_OPERATOR_FIELD, cashier_operator)
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
