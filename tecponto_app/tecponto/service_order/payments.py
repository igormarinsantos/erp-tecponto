"""Native, idempotent OS receipts mirrored into the operational cash ledger."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import frappe
from erpnext.accounts.party import get_party_account
from frappe import _
from frappe.utils import flt, nowdate

from tecponto_app.tecponto.cash import (
	DIRECTION_IN,
	DIRECTION_OUT,
	get_default_company,
	record_cash_movement,
	require_open_cash_session,
)
from tecponto_app.tecponto.financial import native_financial_posting
from tecponto_app.tecponto.operation_config import get_operation_config


PAYMENT_DOCTYPE = "Tecponto Service Order Payment"
PAYMENT_KINDS = {
	"regular": "Pagamento da OS",
	"advance": "Sinal",
	"installment": "Parcela",
	"diagnostic_fee": "Taxa de diagnóstico",
	"storage_fee": "Taxa de armazenamento",
	"tradein": "Aparelho como pagamento",
	"cancellation_adjustment": "Ajuste de cancelamento",
}
FEE_KINDS = {"diagnostic_fee", "storage_fee"}
INVOICE_REQUIRED_KINDS = {"regular", "installment", "diagnostic_fee", "storage_fee"}


def collect_service_order_payment(service_order: str, payload: dict[str, Any]) -> dict[str, Any]:
	"""Register one real receipt/refund in native finance and the cash statement.

	The idempotency record is operational metadata, not a second accounting ledger:
	monetary collection remains a native Payment Entry, while Cash Movement mirrors
	only its operational impact on the active drawer.
	"""
	order = frappe.get_doc("Service Order", (service_order or "").strip())
	order.check_permission("write")
	data = _normalize_payload(order, payload)
	existing = _existing_payment(data["idempotency_key"], data["request_hash"])
	if existing:
		return _payment_response(existing, idempotent_replay=True)

	savepoint = f"tp_os_payment_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	try:
		payment = frappe.get_doc(
			{
				"doctype": PAYMENT_DOCTYPE,
				"service_order": order.name,
				"payment_kind": PAYMENT_KINDS[data["kind"]],
				"direction": data["direction"],
				"amount": data["amount"],
				"payment_mode": data["payment_mode"],
				"affects_drawer": 1 if data["affects_drawer"] else 0,
				"reason": data["reason"] or None,
				"idempotency_key": data["idempotency_key"],
				"request_hash": data["request_hash"],
			}
		)
		payment.insert(ignore_permissions=True)

		if data["kind"] == "tradein":
			payment.source_doctype = "Device Trade Evaluation"
			payment.source_name = data["trade_evaluation"]
			payment.save(ignore_permissions=True)
			return _payment_response(payment, idempotent_replay=False)

		native_payment = _create_native_payment_entry(order, data)
		payment.payment_entry = native_payment.name
		movement = record_cash_movement(
			cash_session=data["cash_session"],
			movement_type="Ajuste" if data["kind"] == "cancellation_adjustment" else "Recebimento de OS",
			direction=data["direction"],
			amount=data["amount"],
			payment_mode=data["payment_mode"],
			affects_drawer=data["affects_drawer"],
			idempotency_key=f"os-payment:{data['idempotency_key']}",
			registered_by=frappe.session.user,
			reference_doctype="Payment Entry",
			reference_name=native_payment.name,
			reason=data["reason"] or PAYMENT_KINDS[data["kind"]],
		)
		payment.cash_movement = movement["movement"]
		payment.save(ignore_permissions=True)
		return _payment_response(payment, idempotent_replay=False)
	except frappe.UniqueValidationError:
		frappe.db.rollback(save_point=savepoint)
		existing = _existing_payment(data["idempotency_key"], data["request_hash"])
		if existing:
			return _payment_response(existing, idempotent_replay=True)
		raise
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def list_service_order_payments(service_order: str) -> list[dict[str, Any]]:
	rows = frappe.get_all(
		PAYMENT_DOCTYPE,
		filters={"service_order": service_order},
		fields=["name", "payment_kind", "direction", "amount", "payment_mode", "affects_drawer", "payment_entry", "cash_movement", "source_doctype", "source_name", "reason", "creation"],
		order_by="creation asc",
	)
	return [_payment_row(row) for row in rows]


def payment_summary(service_order: str, total_due: Any) -> dict[str, Any]:
	items = list_service_order_payments(service_order)
	paid = sum(row["amount"] if row["direction"] == DIRECTION_IN else -row["amount"] for row in items)
	return {"items": items, "paid_total": flt(paid, 2), "remaining_total": max(flt(total_due, 2) - flt(paid, 2), 0)}


def pending_advance_payment_entries(service_order: str) -> list[str]:
	"""Return submitted advance entries not yet allocated when the OS invoice is made."""
	return [
		row.payment_entry
		for row in frappe.get_all(
			PAYMENT_DOCTYPE,
			filters={"service_order": service_order, "payment_kind": ["in", [PAYMENT_KINDS["advance"], PAYMENT_KINDS["installment"]]], "direction": DIRECTION_IN},
			fields=["payment_entry"],
		)
		if row.payment_entry and frappe.db.get_value("Payment Entry", row.payment_entry, "docstatus") == 1
	]


def _normalize_payload(order, payload: dict[str, Any]) -> dict[str, Any]:
	data = payload if isinstance(payload, dict) else {}
	kind = str(data.get("kind") or "regular").strip()
	if kind not in PAYMENT_KINDS:
		frappe.throw(_("Tipo de pagamento da OS inválido."), frappe.ValidationError)
	key = str(data.get("idempotency_key") or "").strip()
	if len(key) < 8 or len(key) > 120:
		frappe.throw(_("Referência idempotente do pagamento inválida."), frappe.ValidationError)
	amount = flt(data.get("amount"), 2)
	if amount <= 0:
		frappe.throw(_("Informe um valor maior que zero."), frappe.ValidationError)
	mode = str(data.get("mode_of_payment") or "").strip()
	direction = str(data.get("direction") or DIRECTION_IN).strip()
	reason = str(data.get("reason") or "").strip()
	config = get_operation_config()
	if kind == "advance" and not config["payments"]["advance_enabled"]:
		frappe.throw(_("Pagamento antecipado está desativado nesta loja."), frappe.ValidationError)
	if kind == "installment" and not config["payments"]["installments_enabled"]:
		frappe.throw(_("Pagamento parcelado está desativado nesta loja."), frappe.ValidationError)
	if kind == "diagnostic_fee":
		if not config["diagnostic_fee"]["enabled"]:
			frappe.throw(_("Taxa de diagnóstico está desativada nesta loja."), frappe.ValidationError)
		if abs(amount - flt(config["diagnostic_fee"]["amount"], 2)) > 0.01:
			frappe.throw(_("A taxa de diagnóstico deve usar o valor configurado."), frappe.ValidationError)
	if kind == "storage_fee":
		if not config["storage_fee"]["enabled"]:
			frappe.throw(_("Taxa de armazenamento está desativada nesta loja."), frappe.ValidationError)
		if abs(amount - flt(config["storage_fee"]["amount"], 2)) > 0.01:
			frappe.throw(_("A taxa de armazenamento deve usar o valor configurado."), frappe.ValidationError)
	if kind == "tradein":
		if not config["payments"]["device_tradein_enabled"]:
			frappe.throw(_("Aparelho como pagamento está desativado nesta loja."), frappe.ValidationError)
		evaluation = str(data.get("trade_evaluation") or "").strip()
		if not evaluation:
			frappe.throw(_("Selecione a avaliação do aparelho entregue como pagamento."), frappe.ValidationError)
		trade = frappe.get_doc("Device Trade Evaluation", evaluation)
		if trade.customer != order.customer or flt(trade.approved_value, 2) != amount:
			frappe.throw(_("A avaliação informada não corresponde ao cliente e valor desta OS."), frappe.ValidationError)
		mode = "Aparelho usado"
	elif kind == "cancellation_adjustment":
		if direction not in {DIRECTION_IN, DIRECTION_OUT} or not reason:
			frappe.throw(_("Ajuste de cancelamento exige direção e observação."), frappe.ValidationError)
	else:
		if direction != DIRECTION_IN:
			frappe.throw(_("Recebimentos de OS devem ter direção de entrada."), frappe.ValidationError)
	if kind in INVOICE_REQUIRED_KINDS and kind != "advance" and not order.get("sales_invoice"):
		frappe.throw(_("Gere a nota da OS antes de registrar este pagamento."), frappe.ValidationError)
	if kind != "tradein" and not mode:
		frappe.throw(_("Informe a forma de pagamento."), frappe.ValidationError)
	if kind != "tradein" and not frappe.db.exists("Mode of Payment", mode):
		frappe.throw(_("Forma de pagamento não encontrada."), frappe.ValidationError)
	if kind != "tradein":
		session = require_open_cash_session(company=order.get("company") or get_default_company())
	else:
		session = None
	request = {
		"service_order": order.name,
		"kind": kind,
		"amount": amount,
		"mode": mode,
		"direction": direction,
		"reason": reason,
		"trade_evaluation": str(data.get("trade_evaluation") or "").strip(),
	}
	return {
		**request,
		"idempotency_key": key,
		"request_hash": hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
		"cash_session": session["session"] if session else None,
		"payment_mode": mode,
		"affects_drawer": mode == "Dinheiro",
	}


def _create_native_payment_entry(order, data: dict[str, Any]):
	company = order.get("company") or get_default_company()
	invoice = frappe.get_doc("Sales Invoice", order.sales_invoice) if order.get("sales_invoice") and data["kind"] != "cancellation_adjustment" else None
	if invoice and data["direction"] == DIRECTION_IN and data["amount"] > flt(invoice.outstanding_amount, 2) + 0.01:
		frappe.throw(_("O pagamento não pode superar o saldo restante da OS."), frappe.ValidationError)
	from tecponto_app.tecponto.service_order.advance import _get_account_currency, _get_payment_account, _get_receivable_account, _get_currency
	paid_from = _get_receivable_account(company) if data["direction"] == DIRECTION_IN else _get_payment_account(data["payment_mode"], company)
	paid_to = _get_payment_account(data["payment_mode"], company) if data["direction"] == DIRECTION_IN else _get_receivable_account(company)
	payment = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive" if data["direction"] == DIRECTION_IN else "Pay",
			"company": company,
			"posting_date": nowdate(),
			"mode_of_payment": data["payment_mode"],
			"party_type": "Customer",
			"party": order.customer,
			"paid_from": paid_from,
			"paid_from_account_currency": _get_account_currency(paid_from, _get_currency(company)),
			"paid_to": paid_to,
			"paid_to_account_currency": _get_account_currency(paid_to, _get_currency(company)),
			"paid_amount": data["amount"],
			"received_amount": data["amount"],
			"base_paid_amount": data["amount"],
			"base_received_amount": data["amount"],
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"reference_no": f"OSPAY-{order.name}-{data['idempotency_key']}",
			"reference_date": nowdate(),
			"remarks": f"{PAYMENT_KINDS[data['kind']]} da OS {order.name}.{f' {data["reason"]}' if data['reason'] else ''}",
		}
	)
	if invoice:
		payment.append(
			"references",
			{
				"reference_doctype": "Sales Invoice",
				"reference_name": invoice.name,
				"allocated_amount": data["amount"],
			},
		)
	# The caller has already passed the OS write gate and all payment validation.
	# ERPNext needs account visibility solely while it posts this native entry.
	with native_financial_posting():
		payment.insert(ignore_permissions=True)
		payment.submit()
	return payment


def _existing_payment(key: str, request_hash: str):
	name = frappe.db.get_value(PAYMENT_DOCTYPE, {"idempotency_key": key}, "name")
	if not name:
		return None
	payment = frappe.get_doc(PAYMENT_DOCTYPE, name)
	if payment.request_hash != request_hash:
		frappe.throw(_("Esta referência já foi usada com dados diferentes."), frappe.ValidationError)
	return payment


def _payment_response(payment, *, idempotent_replay: bool) -> dict[str, Any]:
	return {**_payment_row(payment), "idempotent_replay": idempotent_replay}


def _payment_row(row) -> dict[str, Any]:
	return {
		"name": row.name,
		"kind": row.payment_kind,
		"direction": row.direction,
		"amount": flt(row.amount, 2),
		"payment_mode": row.payment_mode or None,
		"affects_drawer": bool(row.affects_drawer),
		"payment_entry": row.payment_entry or None,
		"cash_movement": row.cash_movement or None,
		"source_doctype": row.source_doctype or None,
		"source_name": row.source_name or None,
		"reason": row.reason or None,
		"created_at": str(row.creation or ""),
	}
