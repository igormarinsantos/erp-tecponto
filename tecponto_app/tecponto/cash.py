from __future__ import annotations

import hashlib
import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, nowdate


CASH_SESSION_DOCTYPE = "Tecponto Cash Session"
CASH_MOVEMENT_DOCTYPE = "Tecponto Cash Movement"
DEFAULT_CASH_POINT = "Balcão principal"
SESSION_OPEN = "Aberto"
SESSION_CLOSED = "Fechado"
DIRECTION_IN = "Entrada"
DIRECTION_OUT = "Saída"
MOVEMENT_OPENING = "Abertura"
MOVEMENT_WITHDRAWAL = "Sangria"
MOVEMENT_SUPPLY = "Suprimento"


def get_default_company() -> str:
	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw(_("Empresa padrão não configurada para operar o caixa."), frappe.ValidationError)
	return company


def open_cash_session(*, opening_amount: Any, idempotency_key: str, opened_by: str | None = None, cash_point: str = DEFAULT_CASH_POINT) -> dict[str, Any]:
	"""Open the store drawer exactly once and record its immutable opening line."""
	amount = flt(opening_amount, 2)
	if amount < 0:
		frappe.throw(_("O valor inicial do caixa não pode ser negativo."), frappe.ValidationError)
	key = _validate_idempotency_key(idempotency_key)
	operator = opened_by or frappe.session.user
	if not operator or operator == "Guest":
		frappe.throw(_("Informe um operador autenticado para abrir o caixa."), frappe.PermissionError)
	point = (cash_point or DEFAULT_CASH_POINT).strip() or DEFAULT_CASH_POINT
	business_date = nowdate()
	company = get_default_company()
	session_key = _session_key(company=company, cash_point=point, business_date=business_date)

	existing = frappe.db.get_value(
		CASH_SESSION_DOCTYPE,
		{"opening_idempotency_key": key},
		["name", "opening_amount", "cash_point", "opened_by", "status"],
		as_dict=True,
	)
	if existing:
		if flt(existing.opening_amount, 2) != amount or existing.cash_point != point or existing.opened_by != operator:
			frappe.throw(_("Esta referência de abertura já foi usada com dados diferentes."), frappe.ValidationError)
		return get_cash_session_summary(existing.name, idempotent_replay=True)

	existing_session = frappe.db.get_value(
		CASH_SESSION_DOCTYPE,
		{"session_key": session_key},
		["name", "status"],
		as_dict=True,
	)
	if existing_session:
		message = _("Já existe um caixa aberto no ponto {0}.").format(point) if existing_session.status == SESSION_OPEN else _("O caixa deste ponto já foi fechado hoje.").format(point)
		frappe.throw(message, frappe.ValidationError)

	savepoint = f"tp_cash_open_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	try:
		session = frappe.get_doc(
			{
				"doctype": CASH_SESSION_DOCTYPE,
				"company": company,
				"cash_point": point,
				"business_date": business_date,
				"session_key": session_key,
				"status": SESSION_OPEN,
				"opened_by": operator,
				"opened_at": now_datetime(),
				"opening_amount": amount,
				"opening_idempotency_key": key,
			}
		)
		session.insert(ignore_permissions=True)
		record_cash_movement(
			cash_session=session.name,
			movement_type=MOVEMENT_OPENING,
			direction=DIRECTION_IN,
			amount=amount,
			idempotency_key=f"opening:{key}",
			registered_by=operator,
			reference_doctype=CASH_SESSION_DOCTYPE,
			reference_name=session.name,
			reason="Abertura de caixa",
		)
		return get_cash_session_summary(session.name, idempotent_replay=False)
	except frappe.UniqueValidationError:
		frappe.db.rollback(save_point=savepoint)
		return _resolve_opening_collision(
			idempotency_key=key,
			amount=amount,
			cash_point=point,
			opened_by=operator,
			session_key=session_key,
		)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def record_cash_movement(
	*,
	cash_session: str,
	movement_type: str,
	direction: str,
	amount: Any,
	idempotency_key: str,
	registered_by: str | None = None,
	payment_mode: str = "Dinheiro",
	affects_drawer: bool = True,
	reference_doctype: str = "",
	reference_name: str = "",
	reason: str = "",
) -> dict[str, Any]:
	"""Internal append-only ledger. Payment and refund flows use it in later phases."""
	value = flt(amount, 2)
	if value < 0:
		frappe.throw(_("O valor do movimento não pode ser negativo."), frappe.ValidationError)
	if direction not in {DIRECTION_IN, DIRECTION_OUT}:
		frappe.throw(_("Direção de movimento de caixa inválida."), frappe.ValidationError)
	if movement_type not in {MOVEMENT_OPENING, "Recebimento de venda", "Recebimento de OS", "Sangria", "Suprimento", "Estorno", "Ajuste"}:
		frappe.throw(_("Tipo de movimento de caixa inválido."), frappe.ValidationError)
	key = _validate_idempotency_key(idempotency_key)

	existing = frappe.db.get_value(
		CASH_MOVEMENT_DOCTYPE,
		{"idempotency_key": key},
		["name", "cash_session", "movement_type", "direction", "amount", "payment_mode", "affects_drawer", "reference_doctype", "reference_name", "reason"],
		as_dict=True,
	)
	if existing:
		if not _same_movement_request(
			existing,
			cash_session=cash_session,
			movement_type=movement_type,
			direction=direction,
			amount=value,
			payment_mode=payment_mode,
			affects_drawer=affects_drawer,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
			reason=reason,
		):
			frappe.throw(_("Esta referência de movimento já foi usada com dados diferentes."), frappe.ValidationError)
		return _movement_payload(frappe.get_doc(CASH_MOVEMENT_DOCTYPE, existing.name), idempotent_replay=True)

	session = frappe.db.get_value(CASH_SESSION_DOCTYPE, cash_session, ["name", "status"], as_dict=True)
	if not session or session.status != SESSION_OPEN:
		frappe.throw(_("O movimento exige um caixa aberto."), frappe.ValidationError)

	movement = frappe.get_doc(
		{
			"doctype": CASH_MOVEMENT_DOCTYPE,
			"cash_session": cash_session,
			"movement_type": movement_type,
			"direction": direction,
			"amount": value,
			"payment_mode": payment_mode or "Dinheiro",
			"affects_drawer": 1 if affects_drawer else 0,
			"occurred_on": now_datetime(),
			"registered_by": registered_by or frappe.session.user,
			"reason": (reason or "").strip() or None,
			"reference_doctype": reference_doctype or None,
			"reference_name": reference_name or None,
			"idempotency_key": key,
		}
	)
	try:
		movement.insert(ignore_permissions=True)
	except frappe.UniqueValidationError:
		existing = frappe.db.get_value(
			CASH_MOVEMENT_DOCTYPE,
			{"idempotency_key": key},
			["name", "cash_session", "movement_type", "direction", "amount", "payment_mode", "affects_drawer", "reference_doctype", "reference_name", "reason"],
			as_dict=True,
		)
		if existing and _same_movement_request(
			existing,
			cash_session=cash_session,
			movement_type=movement_type,
			direction=direction,
				amount=value,
				payment_mode=payment_mode,
				affects_drawer=affects_drawer,
			reference_doctype=reference_doctype,
			reference_name=reference_name,
			reason=reason,
		):
			return _movement_payload(frappe.get_doc(CASH_MOVEMENT_DOCTYPE, existing.name), idempotent_replay=True)
		raise
	return _movement_payload(movement, idempotent_replay=False)


def get_open_cash_session(*, company: str | None = None, cash_point: str = DEFAULT_CASH_POINT) -> dict[str, Any] | None:
	name = frappe.db.get_value(
		CASH_SESSION_DOCTYPE,
		{"company": company or get_default_company(), "cash_point": (cash_point or DEFAULT_CASH_POINT).strip() or DEFAULT_CASH_POINT, "status": SESSION_OPEN},
		"name",
	)
	return get_cash_session_summary(name) if name else None


def get_cash_session_summary(cash_session: str, *, idempotent_replay: bool = False) -> dict[str, Any]:
	session = frappe.get_doc(CASH_SESSION_DOCTYPE, cash_session)
	movements = frappe.get_all(
		CASH_MOVEMENT_DOCTYPE,
		filters={"cash_session": session.name},
		fields=["name", "movement_type", "direction", "amount", "payment_mode", "affects_drawer", "occurred_on", "registered_by", "reason", "reference_doctype", "reference_name"],
		order_by="occurred_on asc, creation asc",
	)
	balance = sum(
		flt(row.amount) if row.direction == DIRECTION_IN else -flt(row.amount)
		for row in movements
		if row.affects_drawer
	)
	return {
		"session": session.name,
		"company": session.company,
		"cash_point": session.cash_point,
		"business_date": str(session.business_date),
		"status": session.status,
		"opened_by": session.opened_by,
		"opened_at": str(session.opened_at),
		"opening_amount": flt(session.opening_amount, 2),
		"closed_by": session.closed_by or None,
		"closed_at": str(session.closed_at) if session.closed_at else None,
		"closing_reason": session.closing_reason or None,
		"closing_expected_drawer": flt(session.closing_expected_drawer, 2),
		"closing_counted_drawer": flt(session.closing_counted_drawer, 2),
		"closing_drawer_difference": flt(session.closing_drawer_difference, 2),
		"drawer_balance": flt(balance, 2),
		"movement_count": len(movements),
		"drawer_movement_count": sum(1 for row in movements if row.affects_drawer),
		"idempotent_replay": bool(idempotent_replay),
	}


def get_cash_statement(*, cash_session: str | None = None) -> dict[str, Any]:
	"""Return a read-only operational statement; accounting remains in native invoices/payments."""
	session_name = cash_session or frappe.db.get_value(
		CASH_SESSION_DOCTYPE,
		{"company": get_default_company(), "cash_point": DEFAULT_CASH_POINT, "status": SESSION_OPEN},
		"name",
	)
	if not session_name:
		session_name = frappe.db.get_value(
			CASH_SESSION_DOCTYPE,
			{"company": get_default_company(), "cash_point": DEFAULT_CASH_POINT},
			"name",
			order_by="opened_at desc",
		)
	if not session_name:
		return {"session": None, "movements": [], "payment_totals": [], "drawer_balance": 0.0}

	summary = get_cash_session_summary(session_name)
	movements = frappe.get_all(
		CASH_MOVEMENT_DOCTYPE,
		filters={"cash_session": session_name},
		fields=["name", "movement_type", "direction", "amount", "payment_mode", "affects_drawer", "occurred_on", "registered_by", "reason", "reference_doctype", "reference_name"],
		order_by="occurred_on desc, creation desc",
	)
	expected = _expected_totals(movements)
	return {
		"session": summary,
		"drawer_balance": summary["drawer_balance"],
		"payment_totals": [
			{"payment_mode": mode, "expected_amount": flt(amount, 2), "affects_drawer": mode == "Dinheiro"}
			for mode, amount in expected.items()
		],
		"movements": [_statement_movement_payload(row) for row in movements],
	}


def close_cash_session(*, counted_amounts: Any, reason: str, idempotency_key: str, closed_by: str | None = None, cash_session: str | None = None) -> dict[str, Any]:
	"""Close a drawer once, recording counted totals and any explained discrepancy."""
	key = _validate_idempotency_key(idempotency_key)
	operator = closed_by or frappe.session.user
	if not operator or operator == "Guest":
		frappe.throw(_("Informe um operador autenticado para fechar o caixa."), frappe.PermissionError)
	counts = _normalize_counted_amounts(counted_amounts)
	open_session = get_cash_session_summary(cash_session) if cash_session else get_open_cash_session()
	if open_session and open_session["status"] != SESSION_OPEN:
		open_session = None
	if not open_session:
		existing_name = frappe.db.get_value(CASH_SESSION_DOCTYPE, {"closing_idempotency_key": key}, "name")
		if existing_name:
			existing = frappe.get_doc(CASH_SESSION_DOCTYPE, existing_name)
			if existing.closing_request_hash == _closing_request_hash(counts, reason):
				return {**get_cash_session_summary(existing.name, idempotent_replay=True), "closing": _closing_payload(existing)}
		frappe.throw(_("Não existe um caixa aberto para fechar."), frappe.ValidationError)
	statement = get_cash_statement(cash_session=open_session["session"])
	expected = {row["payment_mode"]: flt(row["expected_amount"], 2) for row in statement["payment_totals"]}
	missing = [mode for mode in expected if mode not in counts]
	if missing:
		frappe.throw(_("Informe o valor contado para: {0}.").format(", ".join(missing)), frappe.ValidationError)
	unknown = sorted(set(counts) - set(expected))
	if unknown:
		frappe.throw(_("Forma de pagamento sem movimento nesta sessão: {0}.").format(", ".join(unknown)), frappe.ValidationError)
	request_hash = _closing_request_hash(counts, reason)
	doc = frappe.get_doc(CASH_SESSION_DOCTYPE, open_session["session"])
	if doc.status == SESSION_CLOSED:
		if doc.closing_idempotency_key == key and doc.closing_request_hash == request_hash:
			return {**get_cash_session_summary(doc.name, idempotent_replay=True), "closing": _closing_payload(doc)}
		frappe.throw(_("Este caixa já foi fechado."), frappe.ValidationError)

	rows = []
	for mode, expected_amount in expected.items():
		counted = counts[mode]
		difference = flt(counted - expected_amount, 2)
		rows.append({"payment_mode": mode, "expected_amount": expected_amount, "counted_amount": counted, "difference": difference})
	if any(row["difference"] for row in rows) and not (reason or "").strip():
		frappe.throw(_("Informe o motivo da divergência antes de fechar o caixa."), frappe.ValidationError)

	savepoint = f"tp_cash_close_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	try:
		doc.status = SESSION_CLOSED
		doc.closed_by = operator
		doc.closed_at = now_datetime()
		doc.closing_reason = (reason or "").strip() or None
		doc.closing_idempotency_key = key
		doc.closing_request_hash = request_hash
		drawer_row = next((row for row in rows if row["payment_mode"] == "Dinheiro"), {"expected_amount": 0, "counted_amount": 0, "difference": 0})
		doc.closing_expected_drawer = drawer_row["expected_amount"]
		doc.closing_counted_drawer = drawer_row["counted_amount"]
		doc.closing_drawer_difference = drawer_row["difference"]
		doc.set("closing_counts", [])
		for row in rows:
			doc.append("closing_counts", row)
		doc.save(ignore_permissions=True)
		return {**get_cash_session_summary(doc.name, idempotent_replay=False), "closing": _closing_payload(doc)}
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def record_drawer_adjustment(*, movement_type: str, amount: Any, reason: str, idempotency_key: str, registered_by: str | None = None, cash_session: str | None = None) -> dict[str, Any]:
	"""Register physical drawer movement with a mandatory reason, never by editing balances."""
	if movement_type not in {MOVEMENT_WITHDRAWAL, MOVEMENT_SUPPLY}:
		frappe.throw(_("Use Sangria ou Suprimento para movimentar a gaveta."), frappe.ValidationError)
	if not (reason or "").strip():
		frappe.throw(_("Informe o motivo da sangria ou suprimento."), frappe.ValidationError)
	session = get_cash_session_summary(cash_session) if cash_session else require_open_cash_session()
	if session["status"] != SESSION_OPEN:
		frappe.throw(_("O movimento exige um caixa aberto."), frappe.ValidationError)
	value = flt(amount, 2)
	if value <= 0:
		frappe.throw(_("Informe um valor maior que zero."), frappe.ValidationError)
	if movement_type == MOVEMENT_WITHDRAWAL and value > flt(session["drawer_balance"], 2):
		frappe.throw(_("A sangria não pode ser maior que o saldo físico derivado da gaveta."), frappe.ValidationError)
	return record_cash_movement(
		cash_session=session["session"],
		movement_type=movement_type,
		direction=DIRECTION_OUT if movement_type == MOVEMENT_WITHDRAWAL else DIRECTION_IN,
		amount=value,
		idempotency_key=idempotency_key,
		registered_by=registered_by or frappe.session.user,
		payment_mode="Dinheiro",
		affects_drawer=True,
		reference_doctype=CASH_SESSION_DOCTYPE,
		reference_name=session["session"],
		reason=(reason or "").strip(),
	)


def _movement_payload(movement, *, idempotent_replay: bool) -> dict[str, Any]:
	return {
		"movement": movement.name,
		"cash_session": movement.cash_session,
		"movement_type": movement.movement_type,
		"direction": movement.direction,
		"amount": flt(movement.amount, 2),
		"affects_drawer": bool(movement.affects_drawer),
		"idempotent_replay": bool(idempotent_replay),
	}


def _expected_totals(movements: list[Any]) -> dict[str, float]:
	totals: dict[str, float] = {"Dinheiro": 0.0}
	for row in movements:
		mode = row.payment_mode or "Dinheiro"
		totals.setdefault(mode, 0.0)
		totals[mode] += flt(row.amount) if row.direction == DIRECTION_IN else -flt(row.amount)
	return {mode: flt(amount, 2) for mode, amount in totals.items()}


def _normalize_counted_amounts(value: Any) -> dict[str, float]:
	if isinstance(value, str):
		try:
			value = json.loads(value)
		except ValueError:
			frappe.throw(_("Conferência de fechamento inválida."), frappe.ValidationError)
	if not isinstance(value, dict):
		frappe.throw(_("Informe os valores contados por forma de pagamento."), frappe.ValidationError)
	return {str(mode).strip(): flt(amount, 2) for mode, amount in value.items() if str(mode).strip()}


def _closing_request_hash(counts: dict[str, float], reason: str) -> str:
	payload = {"counts": {mode: counts[mode] for mode in sorted(counts)}, "reason": (reason or "").strip()}
	return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _closing_payload(session) -> dict[str, Any]:
	return {
		"closed_by": session.closed_by,
		"closed_at": str(session.closed_at) if session.closed_at else None,
		"reason": session.closing_reason or None,
		"counts": [
			{
				"payment_mode": row.payment_mode,
				"expected_amount": flt(row.expected_amount, 2),
				"counted_amount": flt(row.counted_amount, 2),
				"difference": flt(row.difference, 2),
			}
			for row in session.get("closing_counts")
		],
	}


def _statement_movement_payload(row) -> dict[str, Any]:
	return {
		"movement": row.name,
		"movement_type": row.movement_type,
		"direction": row.direction,
		"amount": flt(row.amount, 2),
		"payment_mode": row.payment_mode or "Dinheiro",
		"affects_drawer": bool(row.affects_drawer),
		"occurred_on": str(row.occurred_on),
		"registered_by": row.registered_by,
		"reason": row.reason or None,
		"reference_doctype": row.reference_doctype or None,
		"reference_name": row.reference_name or None,
	}


def _validate_idempotency_key(value: Any) -> str:
	key = str(value or "").strip()
	if len(key) < 8 or len(key) > 120:
		frappe.throw(_("Referência idempotente do caixa inválida."), frappe.ValidationError)
	return key


def _session_key(*, company: str, cash_point: str, business_date: str) -> str:
	return f"{company}::{cash_point}::{business_date}"


def _resolve_opening_collision(
	*,
	idempotency_key: str,
	amount: float,
	cash_point: str,
	opened_by: str,
	session_key: str,
) -> dict[str, Any]:
	"""Turn a simultaneous open into either the same replay or a clear one-drawer error."""
	existing = frappe.db.get_value(
		CASH_SESSION_DOCTYPE,
		{"opening_idempotency_key": idempotency_key},
		["name", "opening_amount", "cash_point", "opened_by"],
		as_dict=True,
	)
	if existing and flt(existing.opening_amount, 2) == amount and existing.cash_point == cash_point and existing.opened_by == opened_by:
		return get_cash_session_summary(existing.name, idempotent_replay=True)
	if frappe.db.exists(CASH_SESSION_DOCTYPE, {"session_key": session_key}):
		frappe.throw(_("Já existe uma sessão de caixa para este ponto hoje."), frappe.ValidationError)
	frappe.throw(_("Não foi possível confirmar a abertura idempotente do caixa. Tente novamente."), frappe.ValidationError)


def _same_movement_request(existing, **request: Any) -> bool:
	return (
		existing.cash_session == request["cash_session"]
		and existing.movement_type == request["movement_type"]
		and existing.direction == request["direction"]
		and flt(existing.amount, 2) == flt(request["amount"], 2)
		and (existing.payment_mode or "") == (request["payment_mode"] or "Dinheiro")
		and bool(existing.affects_drawer) == bool(request["affects_drawer"])
		and (existing.reference_doctype or "") == (request["reference_doctype"] or "")
		and (existing.reference_name or "") == (request["reference_name"] or "")
		and (existing.reason or "") == (request["reason"] or "").strip()
	)


def require_open_cash_session(*, company: str | None = None, cash_point: str = DEFAULT_CASH_POINT) -> dict[str, Any]:
	"""All payments need an open operational session, even when not paid in cash."""
	session = get_open_cash_session(company=company, cash_point=cash_point)
	if not session:
		frappe.throw(_("Abra o caixa antes de registrar pagamentos ou devoluções."), frappe.ValidationError)
	return session


def record_sales_invoice_cash_movements(*, invoice, idempotency_prefix: str) -> list[dict[str, Any]]:
	"""Mirror native POS payment rows without creating another accounting document."""
	session = require_open_cash_session(company=invoice.company)
	movements: list[dict[str, Any]] = []
	for index, payment in enumerate(invoice.get("payments") or [], start=1):
		amount = abs(flt(payment.amount, 2))
		if not amount:
			continue
		mode = payment.mode_of_payment or ""
		movements.append(
			record_cash_movement(
				cash_session=session["session"],
				movement_type="Estorno" if invoice.is_return else "Recebimento de venda",
				direction=DIRECTION_OUT if invoice.is_return else DIRECTION_IN,
				amount=amount,
				payment_mode=mode,
				affects_drawer=mode == "Dinheiro",
				idempotency_key=f"{idempotency_prefix}:payment:{index}",
				registered_by=frappe.session.user,
				reference_doctype="Sales Invoice",
				reference_name=invoice.name,
				reason="Estorno de venda" if invoice.is_return else "Recebimento de venda",
			)
		)
	return movements
