from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from typing import Any
from urllib.parse import quote

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import add_days, add_to_date, cint, flt, getdate, get_datetime, now_datetime, strip_html, today
from frappe.utils.file_manager import save_file

from tecponto_app.tecponto.customer import (
	CUSTOMER_NO_CPF_FIELD,
	assert_existing_customer_is_complete,
	validate_customer_contact_document,
)
from tecponto_app.tecponto.pos import get_commercial_item_groups, get_retail_item_groups
from tecponto_app.tecponto import pending
from tecponto_app.tecponto.pending import action_for_service_order
from tecponto_app.tecponto.stock import normalize_barcode
from tecponto_app.tecponto.service_order.print_formats import (
	PF_ETIQUETA_INTERNA,
	PF_ETIQUETA_QR,
	PF_LAUDO_TECNICO,
	PF_OS_ORCAMENTO,
	PF_OS_ORCAMENTO_DISCRIMINADO,
	PF_TERMO_APARELHO_PAGAMENTO,
	PF_TERMO_ENTRADA,
	PF_TERMO_GARANTIA,
	PF_TERMO_PECA_CLIENTE,
	PF_TERMO_RETIRADA,
)
from tecponto_app.tecponto.workflow import _get_service_order_transitions, get_service_order_workflow_state_names
from tecponto_app.tecponto import service_catalog
from tecponto_app.tecponto import defect_service_mapping
from tecponto_app.tecponto import part_requests
from tecponto_app.tecponto.lean_operations import operation_shape, technician_commissions_enabled
from tecponto_app.tecponto.operation_config import get_operation_config
from tecponto_app.tecponto import user_access
from tecponto_app.tecponto.cashier import CASHIER_OPERATOR_DOCTYPE, POS_OPERATOR_ROLES
from tecponto_app.tecponto.cash import (
	close_cash_session,
	get_cash_statement,
	get_cash_session_history,
	get_open_cash_session,
	open_cash_session,
	record_drawer_adjustment,
	record_sales_invoice_cash_movements,
	require_open_cash_session,
)
from tecponto_app.tecponto.permissions import is_restricted_technician, service_order_scope_filters
from tecponto_app.tecponto.service_order import stage_clock, stage_sla
from tecponto_app.tecponto.service_order import payments as service_order_payments
from tecponto_app.tecponto.service_order.parts import (
	LOSS_FORNECEDOR,
	LOSS_LOJA,
	LOSS_TECNICO,
	OUTCOME_PERDIDA,
	OUTCOME_USADA,
)
from tecponto_app.tecponto.service_order.inoperative_device import (
	ENTRY_OPERATING_CONDITION_OK,
	ENTRY_OPERATING_CONDITIONS,
)


ROLE_PANELS = (
	{
		"role": "Tecponto Diretor",
		"panel": "diretor",
		"label": "Diretor",
		"subtitle": "Visão executiva",
	},
	{
		"role": "Tecponto Gestor",
		"panel": "gestor",
		"label": "Gestor",
		"subtitle": "Painel do gestor",
	},
	{
		"role": "Tecponto Tecnico",
		"panel": "tecnico",
		"label": "Técnico",
		"subtitle": "Operação técnica",
	},
	{
		"role": "Tecponto Atendente",
		"panel": "atendente",
		"label": "Atendente",
		"subtitle": "Balcão 01",
	},
)
FRONTEND_ALLOWED_ROLES = {
	"System Manager",
	"Tecponto Atendente",
	"Tecponto Tecnico",
	"Tecponto Gestor",
	"Tecponto Diretor",
}
CHECKIN_ALLOWED_ROLES = {
	"System Manager",
	"Tecponto Atendente",
	"Tecponto Gestor",
}
ATTENDANT_FLOW_ALLOWED_ROLES = CHECKIN_ALLOWED_ROLES
BUDGET_ALLOWED_ROLES = CHECKIN_ALLOWED_ROLES | {"Tecponto Tecnico"}
POS_ALLOWED_ROLES = CHECKIN_ALLOWED_ROLES
POST_SALE_ALLOWED_ROLES = CHECKIN_ALLOWED_ROLES
POST_SALE_IDEMPOTENCY_DOCTYPE = "Tecponto Post Sale Request"
TRADEIN_ALLOWED_ROLES = CHECKIN_ALLOWED_ROLES | {"Tecponto Diretor"}
SERVICE_CATALOG_EDITOR_ROLES = {"System Manager", "Tecponto Gestor", "Tecponto Diretor"}
STORE_OPERATION_MANAGER_ROLES = {"System Manager", "Tecponto Gestor", "Tecponto Diretor"}
TECHNICIAN_COMMISSION_ROLES = {"System Manager", "Tecponto Tecnico"}
DIRECTOR_FINANCIAL_ROLES = {"Tecponto Diretor"}
APPROVAL_CHANNELS = {"Presencial", "Telefone", "WhatsApp", "E-mail", "Link"}
STATE_ENTRADA_CRIADA = "Entrada criada"
STATE_AGUARDANDO_APROVACAO = "Aguardando aprovação"
STATE_EM_DIAGNOSTICO = "Em diagnóstico"
STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO = "Diagnosticado — aguardando orçamento"
STATE_APROVADO = "Aprovado"
STATE_REPROVADO = "Reprovado"
STATE_PRONTO_RETIRADA = "Pronto para retirada"
STATE_ENTREGUE = "Entregue"
APPROVAL_STATUS_APROVADO = "Aprovado"
PART_EXECUTION_STATES = {"Aprovado", "Aguardando peça", "Em reparo", "Teste final"}
APPROVAL_STATUS_REPROVADO = "Reprovado"
KANBAN_BLOCKED_TARGETS = {
	STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO: "Use Concluir diagnóstico para escolher quem fará a precificação.",
	STATE_APROVADO: "Use o fluxo de aprovação para registrar canal, atendente e observação.",
	STATE_REPROVADO: "Use o fluxo de reprovação para registrar canal e motivo.",
	STATE_ENTREGUE: "Use o fluxo de retirada para coletar assinatura e validar pagamento.",
}
QUOTE_SEND_CHANNELS = {"WhatsApp", "Telefone", "Presencial", "E-mail"}
QUOTE_SEND_MEDIUM_BY_CHANNEL = {
	"WhatsApp": "Chat",
	"Telefone": "Phone",
	"Presencial": "Visit",
	"E-mail": "Email",
}

SAFE_SERVICE_ORDER_FIELDS = (
	"name",
	"customer",
	"customer_device",
	"entry_date",
	"attendant",
	"technician",
	"pricing_responsibility",
	"budget_review_required",
	"labor_total",
	"parts_total",
	"priority",
	"workflow_state",
	"stage_entered_at",
	"reported_defect",
	"approval_status",
	"approval_deadline",
	"pickup_date",
	"sales_invoice",
	"modified",
)
SAFE_CUSTOMER_FIELDS = (
	"name",
	"customer_name",
	"mobile_no",
	"custom_whatsapp",
	"custom_cpf",
	"custom_rg",
	CUSTOMER_NO_CPF_FIELD,
	"email_id",
	"modified",
)
SAFE_TECHNICIAN_CUSTOMER_FIELDS = (
	"name",
	"customer_name",
	"mobile_no",
	"custom_whatsapp",
	"modified",
)
SAFE_DEVICE_FIELDS = (
	"name",
	"customer",
	"brand",
	"model",
	"color",
	"imei_serial",
	"capacity",
	"photos",
	"registration_date",
	"modified",
)
REGISTRY_KINDS = {"customer", "device", "repair_part", "product"}
CUSTOMER_REGISTRY_FIELDS = {
	"customer_name",
	"mobile_no",
	"custom_whatsapp",
	"custom_cpf",
	"custom_rg",
	CUSTOMER_NO_CPF_FIELD,
	"email_id",
	"address",
}
DEVICE_REGISTRY_FIELDS = {"brand", "model", "color", "imei_serial", "capacity", "general_state"}
ITEM_REGISTRY_FIELDS = {"item_name", "description", "custom_compatible_models", "custom_part_type", "standard_rate"}
SAFE_TRADE_EVALUATION_FIELDS = (
	"name",
	"customer",
	"device_type",
	"evaluated_device_desc",
	"model",
	"imei",
	"physical_state",
	"destination",
	"table_max",
	"suggested_value",
	"approved_value",
	"workflow_state",
	"created_item",
	"trade_category",
	"modified",
)
SAFE_SALES_INVOICE_FIELDS = (
	"name",
	"customer",
	"posting_date",
	"grand_total",
	"status",
	"modified",
)

SENSITIVE_FIELD_NAMES = {
	"actual_qty",
	"base_rate",
	"buying_rate",
	"commission",
	"commission_amount",
	"commission_pct",
	"cost",
	"discount_amount",
	"gross_profit",
	"gross_profit_percent",
	"incoming_rate",
	"labor_total",
	"margin",
	"parts_total",
	"purchase_rate",
	"rate",
	"stock_value",
	"valuation_rate",
}


def _require_login() -> None:
	if frappe.session.user == "Guest":
		frappe.throw(_("Faça login para acessar o sistema."), frappe.PermissionError)


def _require_frontend_role() -> None:
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(FRONTEND_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem papel operacional."), frappe.PermissionError)


def _require_checkin_role() -> None:
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(CHECKIN_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem permissão para abrir OS no balcão."), frappe.PermissionError)


def _require_attendant_flow_role() -> None:
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(ATTENDANT_FLOW_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem permissão para registrar aprovação ou retirada no balcão."), frappe.PermissionError)


def _require_budget_edit_role() -> None:
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(BUDGET_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem permissão para compor orçamento na OS."), frappe.PermissionError)


def _require_pos_role() -> None:
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(POS_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem permissão para operar o PDV do balcão."), frappe.PermissionError)


@frappe.whitelist()
def open_store_cash_session(opening_amount: float = 0, idempotency_key: str = "") -> dict[str, Any]:
	"""Open the single physical drawer; sales integration arrives in cash phase 4.2."""
	_require_pos_role()
	return open_cash_session(
		opening_amount=opening_amount,
		idempotency_key=idempotency_key,
		opened_by=frappe.session.user,
	)


@frappe.whitelist()
def get_store_cash_session() -> dict[str, Any]:
	_require_pos_role()
	return {"session": get_open_cash_session()}


@frappe.whitelist()
def get_store_cash_statement(cash_session: str = "") -> dict[str, Any]:
	_require_pos_role()
	return get_cash_statement(cash_session=cash_session or None)


@frappe.whitelist()
def get_store_cash_session_history(limit: int = 31) -> dict[str, Any]:
	_require_pos_role()
	return {"sessions": get_cash_session_history(limit=limit)}


@frappe.whitelist()
def register_store_drawer_movement(
	movement_type: str = "",
	amount: float = 0,
	reason: str = "",
	idempotency_key: str = "",
) -> dict[str, Any]:
	_require_pos_role()
	return record_drawer_adjustment(
		movement_type=movement_type,
		amount=amount,
		reason=reason,
		idempotency_key=idempotency_key,
		registered_by=frappe.session.user,
	)


@frappe.whitelist()
def close_store_cash_session(
	counted_amounts: Any = None,
	reason: str = "",
	idempotency_key: str = "",
	cash_session: str = "",
) -> dict[str, Any]:
	_require_pos_role()
	return close_cash_session(
		counted_amounts=counted_amounts or {},
		reason=reason,
		idempotency_key=idempotency_key,
		closed_by=frappe.session.user,
		cash_session=cash_session or None,
	)


def _require_post_sale_role() -> None:
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(POST_SALE_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem permissão para registrar devoluções."), frappe.PermissionError)


def _require_tradein_role() -> None:
	"""Trade-in is a counter/management flow; technicians cannot access it."""
	_require_login()
	if set(frappe.get_roles(frappe.session.user)).intersection(TRADEIN_ALLOWED_ROLES):
		return
	frappe.throw(_("Usuário sem permissão para operar avaliações de troca."), frappe.PermissionError)


@contextmanager
def _run_tradein_stock_mutation():
	"""Temporarily run only the already-authorized trade-in stock/payment hook as Administrator."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		yield
	finally:
		if previous_user:
			frappe.set_user(previous_user)


def _require_service_catalog_editor() -> None:
	_require_frontend_role()
	if set(frappe.get_roles(frappe.session.user)).intersection(SERVICE_CATALOG_EDITOR_ROLES):
		return
	frappe.throw(_("Somente Gestor ou Diretor pode editar o catálogo de serviços."), frappe.PermissionError)


def _require_store_operation_manager() -> None:
	"""Store-wide queues are visible only to management roles."""
	_require_frontend_role()
	if set(frappe.get_roles(frappe.session.user)).intersection(STORE_OPERATION_MANAGER_ROLES):
		return
	frappe.throw(_("Somente Gestor ou Diretor pode consultar a carga da loja."), frappe.PermissionError)


def _require_technician_commission_role() -> None:
	"""Allow commission history only for the technician who owns it."""
	_require_frontend_role()
	if not technician_commissions_enabled():
		frappe.throw(_("A comissão de técnico está desativada nesta operação."), frappe.PermissionError)
	if set(frappe.get_roles(frappe.session.user)).intersection(TECHNICIAN_COMMISSION_ROLES):
		return
	frappe.throw(_("Only technicians can consult their own commissions."), frappe.PermissionError)


def _require_director_financial_role() -> None:
	"""Financial cost and profit data is exclusive to the Director role."""
	_require_frontend_role()
	if set(frappe.get_roles(frappe.session.user)).intersection(DIRECTOR_FINANCIAL_ROLES):
		return
	frappe.throw(_("Somente o Diretor pode consultar indicadores financeiros detalhados."), frappe.PermissionError)


def _initials(full_name: str, fallback: str) -> str:
	parts = [part for part in (full_name or "").strip().split() if part]
	if not parts:
		return fallback[:2].upper()
	if len(parts) == 1:
		return parts[0][:2].upper()
	return f"{parts[0][0]}{parts[-1][0]}".upper()


def resolve_panel(roles: list[str] | tuple[str, ...] | None = None) -> dict[str, str]:
	roles = set(roles or frappe.get_roles(frappe.session.user))
	for entry in ROLE_PANELS:
		if entry["role"] in roles:
			return entry

	if "System Manager" in roles:
		return {
			"role": "System Manager",
			"panel": "gestor",
			"label": "Gestor",
			"subtitle": "Sala de máquinas",
		}

	return {
		"role": "Guest",
		"panel": "sem_papel",
		"label": "Sem papel operacional",
		"subtitle": "Solicite acesso ao gestor",
	}


@frappe.whitelist(allow_guest=True)
def get_logged_user() -> dict[str, Any]:
	_require_login()
	user = frappe.session.user
	full_name = frappe.db.get_value("User", user, "full_name") or user
	roles = frappe.get_roles(user)
	panel = resolve_panel(roles)

	return {
		"name": user,
		"full_name": full_name,
		"initials": _initials(full_name, user),
		"roles": roles,
		"panel": panel["panel"],
		"role_label": panel["label"],
		"role_name": panel["role"],
		"subtitle": panel["subtitle"],
		"can_manage_users": user == user_access.get_owner_user() or user_access.SYSTEM_MANAGER_ROLE in set(roles),
	}


@frappe.whitelist(allow_guest=True)
def get_boot() -> dict[str, Any]:
	from tecponto_app.tecponto.company_identity import get_company_identity

	identity = get_company_identity()
	operation = get_operation_config()
	return {
		"user": get_logged_user(),
		"app": {
			"name": identity["display_name"],
			"route": "/tecponto",
			"version": "3.0",
		},
		"identity": identity,
		"features": {
			**operation,
			**operation_shape(),
		},
		"panels": [
			{
				"panel": entry["panel"],
				"role": entry["role"],
				"label": entry["label"],
				"subtitle": entry["subtitle"],
			}
			for entry in ROLE_PANELS
		],
	}


@frappe.whitelist()
def list_user_accounts(query: str = "", include_inactive: bool = True) -> dict[str, Any]:
	"""Return native users for account administration, never credentials or PINs."""
	_require_user_management_role()
	user_access.ensure_user_access_fields()
	query = (query or "").strip()
	filters: dict[str, Any] = {"name": ["!=", "Guest"]}
	if not cint(include_inactive):
		filters["enabled"] = 1
	if query:
		filters["name"] = ["like", f"%{query}%"]
	users = frappe.get_all(
		"User",
		filters=filters,
		fields=["name", "full_name", "email", "enabled", "last_login", user_access.INDIVIDUAL_DISCOUNT_LIMIT_FIELD],
		order_by="enabled desc, full_name asc",
		limit_page_length=500,
	)
	operator_rows = frappe.get_all(
		CASHIER_OPERATOR_DOCTYPE,
		fields=["user", "active", "badge_code"],
		limit_page_length=500,
	)
	operators = {row.user: row for row in operator_rows}
	items = [_serialize_user_account(row, operators.get(row.name)) for row in users]
	return {
		"items": items,
		"stats": {
			"total": len(items),
			"active": sum(1 for item in items if item["enabled"]),
			"administrators": sum(1 for item in items if item["account_level"] == "Administrador do Sistema"),
			"operational": sum(1 for item in items if item["business_roles"]),
		},
		"role_options": _user_role_options(),
		"actor": {
			"name": frappe.session.user,
			"account_level": user_access.get_account_level(frappe.session.user),
		},
	}


@frappe.whitelist()
def save_user_account(payload: dict[str, Any] | str) -> dict[str, Any]:
	"""Create or update a User through the same native hooks used by Desk."""
	_require_user_management_role()
	user_access.ensure_user_access_fields()
	payload = _parse_user_account_payload(payload)
	name = str(payload.get("name") or "").strip()
	roles = _normalize_managed_roles(payload.get("roles"))
	creating = not name
	if creating:
		email = str(payload.get("email") or "").strip().lower()
		if not email or "@" not in email:
			frappe.throw("Informe um e-mail válido para a nova pessoa.", frappe.ValidationError)
		if frappe.db.exists("User", email):
			frappe.throw("Já existe uma pessoa cadastrada com este e-mail.", frappe.ValidationError)
		doc = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": str(payload.get("full_name") or "").strip() or email.split("@", 1)[0],
				"enabled": cint(payload.get("enabled", 1)),
				"send_welcome_email": 0,
			}
		)
	else:
		if not frappe.db.exists("User", name):
			frappe.throw("Pessoa não encontrada.", frappe.DoesNotExistError)
		doc = frappe.get_doc("User", name)
		if "full_name" in payload:
			doc.first_name = str(payload.get("full_name") or "").strip() or doc.first_name
		if "enabled" in payload:
			doc.enabled = cint(payload.get("enabled"))

	current_roles = {row.role for row in (doc.get("roles") or []) if row.role}
	unmanaged_roles = current_roles - user_access.MANAGED_ROLES
	doc.set("roles", [{"role": role} for role in sorted(unmanaged_roles | roles)])
	if frappe.db.has_column("User", user_access.INDIVIDUAL_DISCOUNT_LIMIT_FIELD):
		doc.set(user_access.INDIVIDUAL_DISCOUNT_LIMIT_FIELD, flt(payload.get("discount_limit") or 0))
	if creating:
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	password = str(payload.get("password") or "")
	if password:
		_set_user_password(doc.name, password, creating=creating)

	_save_cashier_operator(doc.name, roles, payload.get("cashier"))
	frappe.clear_cache(user=doc.name)
	operator = frappe.db.get_value(CASHIER_OPERATOR_DOCTYPE, doc.name, ["active", "badge_code"], as_dict=True)
	return {"item": _serialize_user_account(frappe.db.get_value("User", doc.name, ["name", "full_name", "email", "enabled", "last_login", user_access.INDIVIDUAL_DISCOUNT_LIMIT_FIELD], as_dict=True), operator)}


@frappe.whitelist()
def set_user_password(user: str, new_password: str) -> dict[str, bool]:
	"""Set another user's password locally; deliberately sends no email."""
	_require_user_management_role()
	_set_user_password((user or "").strip(), new_password or "", creating=False)
	return {"changed": True}


def _set_user_password(user: str, new_password: str, *, creating: bool) -> None:
	_require_user_management_role()
	if not user or not frappe.db.exists("User", user):
		frappe.throw("Pessoa não encontrada.", frappe.DoesNotExistError)
	actor = frappe.session.user
	owner = user_access.get_owner_user()
	if user == owner and actor != owner:
		frappe.throw("A senha da conta Proprietário só pode ser alterada pelo próprio Proprietário.", frappe.PermissionError)
	if len(new_password) < 8:
		frappe.throw("A senha precisa ter pelo menos 8 caracteres.", frappe.ValidationError)
	from frappe.utils.password import update_password

	update_password(user, new_password)
	user_access.audit_password_change(user, creating=creating)
	frappe.clear_cache(user=user)


@frappe.whitelist()
def send_user_password_reset(user: str) -> dict[str, bool]:
	"""Delegate reset delivery to Frappe; no password ever reaches Tecponto."""
	_require_user_management_role()
	user = (user or "").strip()
	if not frappe.db.exists("User", user):
		frappe.throw("Pessoa não encontrada.", frappe.DoesNotExistError)
	from frappe.core.doctype.user.user import reset_password

	reset_password(user)
	return {"sent": True}


def _require_user_management_role() -> None:
	_require_login()
	actor = frappe.session.user
	if actor == user_access.get_owner_user() or user_access.SYSTEM_MANAGER_ROLE in set(frappe.get_roles(actor)):
		return
	frappe.throw("A gestão de pessoas é restrita ao Proprietário e Administradores do Sistema.", frappe.PermissionError)


@frappe.whitelist()
def get_administrative_sales_report(period: str = "month") -> dict[str, Any]:
	"""Read-only sales view for account administration, without cost projections."""
	_require_user_management_role()
	period = (period or "month").strip()
	if period == "today":
		from_date = today()
		label = _("Hoje")
	elif period == "7d":
		from_date = add_days(today(), -6)
		label = _("Últimos 7 dias")
	elif period == "month":
		from_date = getdate(today()).replace(day=1)
		label = _("Este mês")
	else:
		frappe.throw(_("Período de vendas inválido."), frappe.ValidationError)

	values = {"from_date": from_date, "to_date": today()}
	invoice_totals = frappe.db.sql(
		"""
		select
			coalesce(sum(case when is_return = 0 then 1 else 0 end), 0) as invoices,
			coalesce(sum(case when is_return = 0 then grand_total else 0 end), 0) as gross_sales,
			coalesce(sum(case when is_return = 1 then abs(grand_total) else 0 end), 0) as returns,
			coalesce(sum(case when is_return = 1 then -abs(grand_total) else grand_total end), 0) as net_sales
		from `tabSales Invoice`
		where docstatus = 1 and posting_date between %(from_date)s and %(to_date)s
		""",
		values,
		as_dict=True,
	)[0]
	category_rows = frappe.db.sql(
		"""
		select
			coalesce(nullif(item.item_group, ''), 'Sem categoria') as category,
			coalesce(sum(case when invoice.is_return = 1 then -abs(item.base_net_amount) else item.base_net_amount end), 0) as revenue,
			coalesce(sum(case when invoice.is_return = 1 then -abs(item.qty) else item.qty end), 0) as quantity
		from `tabSales Invoice Item` item
		inner join `tabSales Invoice` invoice on invoice.name = item.parent
		where invoice.docstatus = 1 and invoice.posting_date between %(from_date)s and %(to_date)s
		group by item.item_group
		order by revenue desc
		limit 12
		""",
		values,
		as_dict=True,
	)
	movement_rows = frappe.db.sql(
		"""
		select
			payment_mode,
			max(affects_drawer) as affects_drawer,
			count(*) as movement_count,
			coalesce(sum(case when direction = 'Entrada' then amount else -amount end), 0) as amount
		from `tabTecponto Cash Movement`
		where date(occurred_on) between %(from_date)s and %(to_date)s
			and movement_type in ('Recebimento de venda', 'Recebimento de OS', 'Estorno')
		group by payment_mode
		order by amount desc, payment_mode asc
		""",
		values,
		as_dict=True,
	)
	payment_entries = frappe.db.sql(
		"""
		select count(distinct entry.name)
		from `tabPayment Entry Reference` reference
		inner join `tabPayment Entry` entry on entry.name = reference.parent
		where entry.docstatus = 1
			and entry.posting_date between %(from_date)s and %(to_date)s
			and reference.reference_doctype = 'Sales Invoice'
		""",
		values,
	)[0][0]

	return {
		"period": {"key": period, "label": label, "from_date": str(from_date), "to_date": str(today())},
		"totals": {
			"invoices": int(invoice_totals.invoices or 0),
			"gross_sales": float(flt(invoice_totals.gross_sales)),
			"returns": float(flt(invoice_totals.returns)),
			"net_sales": float(flt(invoice_totals.net_sales)),
			"payment_entries": int(payment_entries or 0),
			"cash_movements": int(sum(row.movement_count or 0 for row in movement_rows)),
		},
		"categories": [
			{"category": row.category, "revenue": float(flt(row.revenue)), "quantity": float(flt(row.quantity))}
			for row in category_rows
		],
		"payment_methods": [
			{"payment_mode": row.payment_mode, "amount": float(flt(row.amount)), "affects_drawer": bool(row.affects_drawer)}
			for row in movement_rows
		],
	}


ADMINISTRATION_SETTING_FIELDS = {
	"identity_company", "trade_name", "public_phone", "public_email", "public_address", "public_logo",
	"enable_repair_pillar", "enable_buy_pillar", "enable_tradein_pillar",
	"diagnostic_fee_enabled", "diagnostic_fee_amount", "storage_fee_enabled", "storage_fee_amount",
	"storage_fee_start_days", "storage_fee_abandonment_days", "diagnosis_only_enabled",
	"payment_advance_enabled", "payment_installments_enabled", "payment_device_tradein_enabled",
	"default_warranty_days", "use_technician_commission", "commission_pct", "commission_labor_only",
	"technician_assignment_mode", "unassigned_technician_alert_hours",
}


def _administration_settings_payload() -> dict[str, Any]:
	from tecponto_app.tecponto.company_identity import get_company_identity

	settings = frappe.get_single("Tecponto Settings")
	resolved_identity = get_company_identity()
	company_name = settings.identity_company or resolved_identity.get("company")
	company = frappe.get_doc("Company", company_name) if company_name else None
	return {
		"identity": {
			**resolved_identity,
			"company_name": company.company_name if company else "",
			"tax_id": company.tax_id if company else "",
			"trade_name": settings.trade_name or "",
			"public_phone": settings.public_phone or "",
			"public_email": settings.public_email or "",
			"public_address": settings.public_address or "",
			"public_logo": settings.public_logo or "",
		},
		"operation": {field: settings.get(field) for field in ADMINISTRATION_SETTING_FIELDS if field not in {"identity_company", "trade_name", "public_phone", "public_email", "public_address", "public_logo"}},
		"card_fees": [{"tipo": row.tipo, "taxa_pct": flt(row.taxa_pct), "settlement_days": cint(row.settlement_days)} for row in settings.get("card_fees") or []],
		"stage_slas": [stage_sla._serialize_sla(row) for row in stage_sla.get_stage_slas()],
	}


@frappe.whitelist()
def get_administration_settings() -> dict[str, Any]:
	"""Read the administration-safe configuration projection for the React UI."""
	_require_user_management_role()
	return _administration_settings_payload()


@frappe.whitelist()
def save_administration_settings(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Persist only the explicit operational/identity allowlist from Administration."""
	_require_user_management_role()
	data = _parse_payload(payload)
	operation, identity, card_fees = data.get("operation") or {}, data.get("identity") or {}, data.get("card_fees") or []
	if not isinstance(operation, dict) or not isinstance(identity, dict) or not isinstance(card_fees, list):
		frappe.throw(_("Configuração inválida."), frappe.ValidationError)

	settings = frappe.get_single("Tecponto Settings")
	for field, value in operation.items():
		if field not in ADMINISTRATION_SETTING_FIELDS:
			frappe.throw(_("Campo de configuração não permitido: {0}").format(field), frappe.PermissionError)
		if field.endswith(("_amount", "_pct")):
			value = max(0, flt(value))
		elif field.endswith("_days"):
			value = max(0, cint(value))
		elif field == "unassigned_technician_alert_hours":
			value = max(0, flt(value))
		elif field == "technician_assignment_mode":
			value = str(value or "").strip()
			if value not in {"Pull", "Dispatch"}:
				frappe.throw(_("Modo de atribuição inválido."), frappe.ValidationError)
		elif field.startswith(("enable_", "payment_", "use_", "diagnosis_", "commission_")):
			value = cint(value)
		settings.set(field, value)

	if settings.storage_fee_abandonment_days and settings.storage_fee_start_days and cint(settings.storage_fee_abandonment_days) < cint(settings.storage_fee_start_days):
		frappe.throw(_("O prazo de abandono não pode ser menor que o início da armazenagem."), frappe.ValidationError)
	if cint(settings.default_warranty_days) < 1:
		frappe.throw(_("Informe ao menos um dia para a garantia."), frappe.ValidationError)

	from tecponto_app.tecponto.company_identity import get_company_identity

	company_name = str(identity.get("company") or settings.identity_company or get_company_identity().get("company") or "").strip()
	if company_name and not frappe.db.exists("Company", company_name):
		frappe.throw(_("Empresa não encontrada."), frappe.DoesNotExistError)
	if company_name:
		company = frappe.get_doc("Company", company_name)
		for field, key in (("company_name", "company_name"), ("tax_id", "tax_id"), ("phone_no", "phone"), ("email", "email"), ("company_logo", "logo_url")):
			if key in identity:
				company.set(field, str(identity.get(key) or "").strip())
		company.save(ignore_permissions=True)
		settings.identity_company = company.name
	for field in ("trade_name", "public_phone", "public_email", "public_address", "public_logo"):
		if field in identity:
			settings.set(field, str(identity.get(field) or "").strip())

	validated_fees = []
	for row in card_fees:
		if not isinstance(row, dict) or not str(row.get("tipo") or "").strip():
			frappe.throw(_("Informe o tipo de cada taxa de cartão."), frappe.ValidationError)
		fee = flt(row.get("taxa_pct"))
		if fee < 0 or fee > 100:
			frappe.throw(_("A taxa de cartão deve ficar entre 0% e 100%."), frappe.ValidationError)
		validated_fees.append({"tipo": str(row["tipo"]).strip(), "taxa_pct": fee, "settlement_days": max(0, cint(row.get("settlement_days")))})
	settings.set("card_fees", validated_fees)
	settings.save(ignore_permissions=True)
	frappe.clear_cache()
	return _administration_settings_payload()


def _parse_user_account_payload(payload: dict[str, Any] | str) -> dict[str, Any]:
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	if not isinstance(payload, dict):
		frappe.throw("Dados de pessoa inválidos.", frappe.ValidationError)
	return payload


def _normalize_managed_roles(value: Any) -> set[str]:
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if not isinstance(value, list):
		frappe.throw("Informe os papéis da pessoa.", frappe.ValidationError)
	roles = {str(role).strip() for role in value if str(role).strip()}
	unknown = roles - user_access.MANAGED_ROLES
	if unknown:
		frappe.throw("Papel inválido: {0}.".format(", ".join(sorted(unknown))), frappe.ValidationError)
	return roles


def _user_role_options() -> list[dict[str, Any]]:
	actor = frappe.session.user
	actor_roles = set(frappe.get_roles(actor))
	is_owner = actor == user_access.get_owner_user()
	options = []
	for role in sorted(user_access.MANAGED_ROLES):
		allowed = is_owner or (role not in {user_access.SYSTEM_MANAGER_ROLE, "Tecponto Diretor"} and role in actor_roles)
		reason = ""
		if not allowed:
			reason = (
				"Somente o Proprietário pode conceder Administrador do Sistema."
				if role == user_access.SYSTEM_MANAGER_ROLE
				else "Somente o Proprietário pode conceder o papel Diretor."
				if role == "Tecponto Diretor"
				else "Você só pode conceder papéis que já possui."
			)
		options.append({"role": role, "allowed": allowed, "reason": reason})
	return options


def _serialize_user_account(user: Any, operator: Any) -> dict[str, Any]:
	roles = user_access._user_roles(user.name)
	managed_roles = sorted(roles & user_access.MANAGED_ROLES)
	return {
		"name": user.name,
		"full_name": user.full_name or user.name,
		"email": user.email or user.name,
		"enabled": bool(user.enabled),
		"last_login": str(user.last_login or ""),
		"roles": managed_roles,
		"business_roles": sorted(roles & user_access.BUSINESS_ROLES),
		"account_level": user_access.get_account_level(user.name),
		"discount_limit": flt(user.get(user_access.INDIVIDUAL_DISCOUNT_LIMIT_FIELD) or 0),
		"cashier": {
			"enabled": bool(operator and operator.active),
			"badge_code": operator.badge_code if operator else "",
			"has_pin": bool(operator),
		},
	}


def _save_cashier_operator(user: str, roles: set[str], cashier: Any) -> None:
	if cashier is None:
		return
	if isinstance(cashier, str):
		cashier = frappe.parse_json(cashier)
	if not isinstance(cashier, dict):
		frappe.throw("Dados de crachá inválidos.", frappe.ValidationError)
	existing = frappe.db.exists(CASHIER_OPERATOR_DOCTYPE, user)
	enabled = bool(cint(cashier.get("enabled")))
	if not enabled and existing:
		doc = frappe.get_doc(CASHIER_OPERATOR_DOCTYPE, user)
		doc.active = 0
		doc.save(ignore_permissions=True)
		return
	if not enabled:
		return
	if not (roles & POS_OPERATOR_ROLES):
		frappe.throw("Crachá/PIN só pode ser ativado para quem possui papel de operação do PDV.", frappe.ValidationError)
	badge_code = str(cashier.get("badge_code") or "").strip()
	pin = str(cashier.get("pin") or "").strip()
	if not existing and (not badge_code or not pin):
		frappe.throw("Informe crachá e PIN de 4 dígitos para ativar o modo caixa.", frappe.ValidationError)
	doc = frappe.get_doc(CASHIER_OPERATOR_DOCTYPE, user) if existing else frappe.get_doc({"doctype": CASHIER_OPERATOR_DOCTYPE, "user": user})
	doc.active = 1
	if badge_code:
		doc.badge_code = badge_code
	if pin:
		doc.pin = pin
	doc.save(ignore_permissions=True) if existing else doc.insert(ignore_permissions=True)


@frappe.whitelist()
def list_service_orders(
	limit: int = 20,
	query: str | None = None,
	status: str | None = None,
	in_progress: int | bool | str | None = True,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit or 20), 100))
	filters, or_filters = _service_order_search_filters(
		query=query,
		status=status,
		in_progress=in_progress,
		from_date=from_date,
		to_date=to_date,
	)
	filters = _with_service_order_scope(filters)
	items = frappe.get_list(
		"Service Order",
		fields=list(SAFE_SERVICE_ORDER_FIELDS),
		filters=filters,
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=limit,
	)
	count = _count_service_orders(filters=filters, or_filters=or_filters)

	return {
		"items": [_serialize_service_order(item) for item in items],
		"count": count,
		"fields": list(SAFE_SERVICE_ORDER_FIELDS),
	}


@frappe.whitelist()
def list_unassigned_service_orders(limit: int = 1000) -> dict[str, Any]:
	"""Dedicated safe queue; technicians only receive it while Pull is enabled."""
	from tecponto_app.tecponto.service_order.assignment import list_unassigned

	_require_frontend_role()
	result = list_unassigned(frappe.session.user, limit=limit)
	result["items"] = [
		{
			**_serialize_service_order(row),
			"unassigned_waiting_hours": row.get("unassigned_waiting_hours"),
			"unassigned_overdue": row.get("unassigned_overdue"),
		}
		for row in result["items"]
	]
	return result


@frappe.whitelist()
def claim_service_order(name: str) -> dict[str, Any]:
	from tecponto_app.tecponto.service_order.assignment import claim

	_require_frontend_role()
	return claim(name, frappe.session.user)


@frappe.whitelist()
def assign_service_order(name: str, technician: str, observation: str = "") -> dict[str, Any]:
	from tecponto_app.tecponto.service_order.assignment import assign

	_require_frontend_role()
	return assign(name, technician, frappe.session.user, observation=observation)


@frappe.whitelist()
def transfer_service_order(name: str, technician: str, observation: str = "") -> dict[str, Any]:
	from tecponto_app.tecponto.service_order.assignment import transfer

	_require_frontend_role()
	return transfer(name, technician, frappe.session.user, observation=observation)


@frappe.whitelist()
def get_service_order_statbar() -> dict[str, Any]:
	"""Operational workflow counts only; deliberately excludes all financial fields."""
	_require_frontend_role()
	technical_view = is_restricted_technician()
	states = (
		["Em diagnóstico", STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO, "Aguardando peça", "Teste final"]
		if technical_view
		else ["Entrada criada", "Em diagnóstico", STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO, "Aguardando aprovação", "Aguardando peça", "Em reparo", "Pronto para retirada"]
	)
	scope = service_order_scope_filters()
	items = []
	if technical_view:
		items.append({"key": "total", "label": "Minhas OS", "value": frappe.db.count("Service Order", scope)})
	items.append({"key": "overdue", "label": "Atrasadas", "value": len(stage_clock.list_overdue_service_order_names(filters=scope))})
	for state in states:
		filters = {**scope, "workflow_state": state}
		items.append({"key": state, "label": state, "value": frappe.db.count("Service Order", filters)})
	return {"items": items}


@frappe.whitelist()
def get_list_statbar(scope: str) -> dict[str, Any]:
	"""Safe list summaries. This intentionally never selects stock cost, margins, or profit."""
	_require_frontend_role()
	scope = (scope or "").strip()
	if is_restricted_technician() and scope in {"sales", "trades"}:
		frappe.throw(_("Este resumo não está disponível para o perfil técnico."), frappe.PermissionError)
	if scope == "customers":
		month_start = getdate(today()).replace(day=1)
		service_scope = service_order_scope_filters()
		active_filters = {**service_scope, "workflow_state": ["not in", ["Entregue", "Cancelado", "Reprovado", "Orçamento expirado"]]}
		active = len(set(frappe.get_all("Service Order", filters=active_filters, pluck="customer", limit_page_length=0)))
		if service_scope:
			customer_names = list(set(frappe.get_all("Service Order", filters=service_scope, pluck="customer", limit_page_length=0))) or [""]
			customer_filters: dict[str, Any] = {"name": ["in", customer_names]}
			items = [
				("active", "Com OS em andamento", active),
				("all", "Total", frappe.db.count("Customer", customer_filters)),
				("new", "Novos no mês", frappe.db.count("Customer", {**customer_filters, "creation": [">=", month_start]})),
			]
		else:
			items = [("active", "Com OS em andamento", active), ("all", "Total", frappe.db.count("Customer")), ("new", "Novos no mês", frappe.db.count("Customer", {"creation": [">=", month_start]}))]
	elif scope.startswith("stock:"):
		stock_scope = scope.split(":", 1)[1]
		if is_restricted_technician() and stock_scope != "repair-parts":
			frappe.throw(_("O perfil técnico consulta somente o estoque de Reparo."), frappe.PermissionError)
		repair = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
		commercial = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
		warehouse = repair if stock_scope == "repair-parts" else commercial
		group = "Peças de Reparo" if stock_scope == "repair-parts" else "Aparelhos Usados" if stock_scope == "used-devices" else None
		conditions = ["item.disabled = 0", "item.is_stock_item = 1", "bin.warehouse = %(warehouse)s"]
		values = {"warehouse": warehouse}
		if group:
			groups = _descendant_item_groups(group)
			conditions.append("item.item_group in %(groups)s")
			values["groups"] = groups
		where = " and ".join(conditions)
		rows = frappe.db.sql(f"select count(distinct item.name), coalesce(sum(bin.actual_qty <= 0), 0), coalesce(sum(bin.actual_qty between 0.001 and 2), 0) from `tabItem` item inner join `tabBin` bin on bin.item_code=item.name where {where}", values)[0]
		items = [("all", "Itens", rows[0]), ("empty", "Sem estoque", rows[1]), ("low", "Baixo estoque", rows[2])]
	elif scope == "trades":
		items = [("open", "Avaliações abertas", frappe.db.count("Device Trade Evaluation", {"workflow_state": ["not in", ["Comprado", "Descartado"]]})), ("approval", "Aguardando aprovação", frappe.db.count("Device Trade Evaluation", {"workflow_state": "Aguardando aprovação"})), ("closed", "Fechadas no mês", frappe.db.count("Device Trade Evaluation", {"workflow_state": "Comprado", "modified": [">=", getdate(today()).replace(day=1)]}))]
	elif scope == "sales":
		count, total = frappe.db.sql("select count(*), coalesce(sum(grand_total),0) from `tabSales Invoice` where docstatus=1 and is_return=0 and posting_date=%(date)s", {"date": today()})[0]
		return {"items": [
			{"key": "today", "label": "Vendas hoje", "value": int(count or 0)},
			{"key": "amount", "label": "Valor vendido", "value": float(total or 0), "amount": float(total or 0)},
		]}
	elif scope == "catalog":
		items = [
			("active", "Servicos ativos", frappe.db.count("Tecponto Service", {"active": 1})),
			("all", "Total cadastrado", frappe.db.count("Tecponto Service")),
			("categories", "Categorias ativas", frappe.db.count("Tecponto Service Category", {"active": 1})),
		]
	else:
		frappe.throw(_("Resumo não disponível."), frappe.ValidationError)
	return {"items": [{"key": key, "label": label, "value": int(value or 0)} for key, label, value in items]}


@frappe.whitelist()
def list_sales(query: str = "", limit: int = 50, period: str = "today") -> dict[str, Any]:
	"""Counter sales projection. It deliberately contains no inventory cost or profitability data."""
	_require_frontend_role()
	if is_restricted_technician():
		frappe.throw(_("O perfil técnico não consulta vendas."), frappe.PermissionError)
	limit = max(1, min(int(limit or 50), 100))
	period = (period or "today").strip()
	filters: dict[str, Any] = {"docstatus": 1, "is_return": 0}
	if period == "today":
		filters["posting_date"] = today()
	elif period == "7d":
		filters["posting_date"] = [">=", add_days(today(), -6)]
	elif period != "all":
		frappe.throw(_("Período de vendas inválido."), frappe.ValidationError)
	term = (query or "").strip()
	or_filters = _like_filters(term, ("name", "customer")) if term else None
	items = frappe.get_all(
		"Sales Invoice",
		fields=list(SAFE_SALES_INVOICE_FIELDS),
		filters=filters,
		or_filters=or_filters,
		order_by="posting_date desc, modified desc",
		limit_page_length=limit,
	)
	return {"items": items, "count": len(items), "fields": list(SAFE_SALES_INVOICE_FIELDS)}


@frappe.whitelist()
def get_sale_post_sale_detail(name: str) -> dict[str, Any]:
	"""Safe sales projection used to decide a native invoice return."""
	_require_post_sale_role()
	invoice = frappe.get_doc("Sales Invoice", (name or "").strip())
	if invoice.docstatus != 1 or invoice.is_return:
		frappe.throw(_("Selecione uma venda concluída para o pós-venda."), frappe.ValidationError)
	returned = frappe.db.sql(
		"""
		select item_code, abs(sum(qty)) as qty
		from `tabSales Invoice Item`
		where parenttype = 'Sales Invoice' and docstatus = 1
		and parent in (select name from `tabSales Invoice` where return_against = %(invoice)s and is_return = 1)
		group by item_code
		""",
		{"invoice": invoice.name},
		as_dict=True,
	)
	returned_by_item = {row.item_code: flt(row.qty) for row in returned}
	return {
		"name": invoice.name,
		"customer": invoice.customer,
		"posting_date": str(invoice.posting_date),
		"grand_total": flt(invoice.grand_total),
		"payments": [{"mode_of_payment": row.mode_of_payment, "amount": flt(row.amount)} for row in invoice.payments],
		"items": [
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": flt(row.qty),
				"returned_qty": returned_by_item.get(row.item_code, 0),
				"available_qty": max(flt(row.qty) - returned_by_item.get(row.item_code, 0), 0),
				"unit_price": flt(row.rate),
			}
			for row in invoice.items
		],
	}


@frappe.whitelist()
def create_sales_return(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Submit ERPNext's native Sales Invoice Return for selected, still-returnable lines."""
	_require_post_sale_role()
	data = _parse_payload(payload)
	return_doc, replay = _create_sales_return_with_cash(data)
	return {
		"return_invoice": return_doc.name,
		"return_against": return_doc.return_against,
		"grand_total": flt(return_doc.grand_total),
		"idempotent_replay": replay,
	}


@frappe.whitelist()
def exchange_sales_product(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Atomically compose a native return and the existing server-owned POS sale."""
	_require_post_sale_role()
	data = _parse_payload(payload)
	from tecponto_app.tecponto.frontend.pos import pos_create_sale

	exchange_key = _validate_post_sale_idempotency_key(data.get("idempotency_key"))
	savepoint = f"frontend_product_exchange_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	try:
		return_doc, _return_replay = _create_sales_return_with_cash({**data, "idempotency_key": f"{exchange_key}:return"})
		new_sale = pos_create_sale(data.get("new_sale"))
		return_doc.db_set("remarks", f"Troca Tecponto: venda nova {new_sale['sale']}", update_modified=False)
		frappe.db.set_value("Sales Invoice", new_sale["sale"], "remarks", f"Troca Tecponto: devolucao {return_doc.name}", update_modified=False)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise
	return {"return_invoice": return_doc.name, "new_sale": new_sale}


@frappe.whitelist()
def list_my_commissions(
	period: str = "month",
	from_date: str = "",
	to_date: str = "",
	limit: int = 100,
) -> dict[str, Any]:
	"""Read submitted commissions already generated in Additional Salary.

	The projection is deliberately limited to the logged technician's Employee
	and Service Orders assigned to that same user. It never recalculates values
	or joins any item cost, margin, or other employee's payroll information.
	"""
	_require_technician_commission_role()
	limit = max(1, min(int(limit or 100), 200))
	period = (period or "month").strip()
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, "name")
	if not employee:
		return {"items": [], "count": 0, "total": 0.0, "period": period}

	conditions = [
		"additional_salary.employee = %(employee)s",
		"additional_salary.salary_component = %(salary_component)s",
		"additional_salary.type = 'Earning'",
		"additional_salary.docstatus = 1",
		"additional_salary.ref_doctype = 'Service Order Service'",
		"service_order.technician = %(user)s",
	]
	values: dict[str, Any] = {
		"employee": employee,
		"salary_component": "Comiss\u00e3o",
		"user": frappe.session.user,
		"limit": limit,
	}
	if period == "7d":
		conditions.append("additional_salary.payroll_date >= %(from_date)s")
		values["from_date"] = add_days(today(), -6)
	elif period == "month":
		conditions.append("additional_salary.payroll_date >= %(from_date)s")
		values["from_date"] = getdate(today()).replace(day=1)
	elif period == "custom":
		start = (from_date or "").strip()
		end = (to_date or "").strip()
		if not start or not end:
			frappe.throw(_("Informe as duas datas do periodo personalizado."), frappe.ValidationError)
		conditions.append("additional_salary.payroll_date between %(from_date)s and %(to_date)s")
		values.update({"from_date": start, "to_date": end})
	elif period != "all":
		frappe.throw(_("Periodo de comissoes invalido."), frappe.ValidationError)

	rows = []
	if frappe.db.table_exists("Additional Salary"):
		payroll_entry_field = "additional_salary.payroll_entry" if frappe.get_meta("Additional Salary").has_field("payroll_entry") else "''"
		rows = frappe.db.sql(
			f"""
			select
				service_order.name as service_order,
				service_row.description as service_name,
				additional_salary.amount as value,
				additional_salary.payroll_date as date,
				{payroll_entry_field} as payroll_entry
			from `tabAdditional Salary` additional_salary
			inner join `tabService Order Service` service_row on service_row.name = additional_salary.ref_docname
			inner join `tabService Order` service_order on service_order.name = service_row.parent
			where {' and '.join(conditions)}
			order by additional_salary.payroll_date desc, additional_salary.creation desc
			limit %(limit)s
			""",
			values,
			as_dict=True,
		)
	items = [
		{
			"service_order": row.service_order,
			"service_name": row.service_name or "Mao de obra",
			"value": float(flt(row.value)),
			"date": str(row.date or ""),
			"payment_status": "Em folha" if row.payroll_entry else "Lançada",
		}
		for row in rows
	]
	return {
		"items": items,
		"count": len(items),
		"total": float(sum(item["value"] for item in items)),
		"period": period,
	}


@frappe.whitelist()
def create_technical_part_request(
	service_order: str,
	item: str = "",
	free_description: str = "",
	qty: float = 1,
	notes: str = "",
) -> dict[str, Any]:
	"""Create a technical need; later buying/receiving flows own the cost fields."""
	_require_frontend_role()
	return part_requests.create_part_request(
		service_order=service_order,
		item=item,
		free_description=free_description,
		qty=qty,
		notes=notes,
	)


@frappe.whitelist()
def list_my_technical_part_requests(limit: int = 100) -> dict[str, Any]:
	_require_frontend_role()
	return part_requests.list_my_part_requests(limit=limit)


@frappe.whitelist()
def search_repair_part_options(query: str = "", limit: int = 20) -> dict[str, Any]:
	_require_frontend_role()
	return part_requests.list_repair_part_options(query=query, limit=limit)


@frappe.whitelist()
def list_purchase_part_requests(status: str = "open", query: str = "", limit: int = 100) -> dict[str, Any]:
	_require_frontend_role()
	return part_requests.list_purchase_part_requests(status=status, query=query, limit=limit)


@frappe.whitelist()
def mark_part_request_ordered(
	name: str,
	supplier: str,
	expected_arrival: str,
	estimated_cost: float | None = None,
) -> dict[str, Any]:
	_require_frontend_role()
	return part_requests.mark_part_request_ordered(name, supplier=supplier, expected_arrival=expected_arrival, estimated_cost=estimated_cost)


@frappe.whitelist()
def mark_part_request_received(name: str, item: str = "") -> dict[str, Any]:
	_require_frontend_role()
	return part_requests.mark_part_request_received(name, item=item)


@frappe.whitelist()
def cancel_part_request(name: str, reason: str) -> dict[str, Any]:
	_require_frontend_role()
	return part_requests.cancel_part_request(name, reason)


@frappe.whitelist()
def get_service_order_kanban(
	limit_per_column: int = 18,
	query: str | None = None,
	status: str | None = None,
	in_progress: int | bool | str | None = True,
	from_date: str | None = None,
	to_date: str | None = None,
) -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit_per_column or 18), 40))
	columns = []
	legacy_in_progress = status == "in_progress"
	selected_status = "all" if legacy_in_progress else status
	in_progress_only = legacy_in_progress if in_progress is None else str(in_progress).strip().lower() in {"1", "true", "yes"}
	for state in get_service_order_workflow_state_names():
		if selected_status and selected_status != "all" and selected_status != state:
			items = []
			count = 0
		else:
			filters, or_filters = _service_order_search_filters(
				query=query,
				status=state,
				from_date=from_date,
				to_date=to_date,
			)
			if in_progress_only:
				filters["pickup_date"] = ["is", "not set"]
			filters = _with_service_order_scope(filters)
			items = frappe.get_list(
				"Service Order",
				fields=list(SAFE_SERVICE_ORDER_FIELDS),
				filters=filters,
				or_filters=or_filters,
				order_by="modified desc",
				limit_page_length=limit,
			)
			count = _count_service_orders(filters=filters, or_filters=or_filters)
		columns.append(
			{
				"state": state,
				"count": count,
				"items": [_serialize_service_order(item) for item in items],
			}
		)

	return {
		"columns": columns,
		"fields": list(SAFE_SERVICE_ORDER_FIELDS),
	}


@frappe.whitelist()
def move_service_order(name: str, target_state: str) -> dict[str, Any]:
	_require_frontend_role()
	name = (name or "").strip()
	target_state = (target_state or "").strip()
	if not name:
		frappe.throw(_("Informe a ordem de serviço."), frappe.ValidationError)
	if target_state not in get_service_order_workflow_state_names():
		frappe.throw(_("Estado de destino inválido para o Kanban."), frappe.ValidationError)

	doc = frappe.get_doc("Service Order", name)
	doc.check_permission("read")
	current_state = doc.get("workflow_state")
	if current_state == target_state:
		return {"item": _serialize_service_order(doc.as_dict()), "changed": False}
	if target_state in KANBAN_BLOCKED_TARGETS:
		frappe.throw(_(KANBAN_BLOCKED_TARGETS[target_state]), frappe.ValidationError)
	# Surface the billed-cancellation gate before the workflow-role message so the
	# user receives the correct approval path. The Service Order policy validates
	# the same rule again when the Gestor executes the transition.
	if target_state == "Cancelado" and doc.get("sales_invoice") and not _current_user_is_manager():
		frappe.throw(_("OS faturada so pode ser cancelada pelo Gestor."), frappe.PermissionError)

	action = _get_allowed_kanban_action(current_state, target_state)
	apply_workflow(frappe.as_json({"doctype": doc.doctype, "name": doc.name}), action)
	updated = frappe.db.get_value(
		"Service Order",
		name,
		list(SAFE_SERVICE_ORDER_FIELDS),
		as_dict=True,
	)
	return {
		"item": _serialize_service_order(updated),
		"changed": True,
	}


@frappe.whitelist()
def issue_os_acceptance(service_order: str, acceptance_type: str, signer_role: str = "Dono") -> dict[str, Any]:
	"""Issue a public, read-only acceptance link for the authenticated operator."""
	_require_checkin_role()
	from tecponto_app.tecponto.acceptance import issue_acceptance
	return issue_acceptance(service_order, acceptance_type, signer_role)


@frappe.whitelist()
def record_os_physical_acceptance(
	service_order: str,
	acceptance_type: str,
	file_data: str,
	file_name: str = "aceite-fisico.jpg",
	term_confirmed: int | bool = False,
) -> dict[str, Any]:
	"""Archive an authenticated attendant's real signed paper copy."""
	_require_attendant_flow_role()
	from tecponto_app.tecponto.acceptance import record_physical_acceptance

	return record_physical_acceptance(
		service_order,
		acceptance_type,
		file_data,
		file_name,
		inoperative_term_consent=term_confirmed,
		customer_part_term_consent=term_confirmed,
	)


@frappe.whitelist()
def get_service_order_detail(name: str) -> dict[str, Any]:
	_require_frontend_role()
	name = (name or "").strip()
	if not name:
		frappe.throw(_("Informe a ordem de serviço."), frappe.ValidationError)

	doc = frappe.get_doc("Service Order", name)
	doc.check_permission("read")

	technical_view = is_restricted_technician()
	services = [_serialize_service_row(row) for row in (doc.get("services") or [])]
	parts = [_serialize_part_row(row) for row in (doc.get("parts") or [])]
	service_total = sum(row["amount"] for row in services)
	parts_price_total = sum(row["amount"] for row in parts)
	discount = flt(doc.get("discount") or 0)
	grand_total = flt(doc.get("grand_total") or (service_total + parts_price_total - discount))
	closed_lines = _build_closed_budget_lines(services, parts)

	finance = _service_order_finance_payload(doc, technical_view=technical_view, fallback_total=grand_total)
	pricing_available = bool(set(frappe.get_roles(frappe.session.user)).intersection(ATTENDANT_FLOW_ALLOWED_ROLES | {"Tecponto Tecnico"}))
	pricing_default = "Técnico" if operation_shape()["single_operator"] and pricing_available else "Balcão"
	return {
		"name": doc.name,
		"workflow_state": doc.get("workflow_state"),
		"approval_status": doc.get("approval_status"),
		"approval_deadline": str(doc.get("approval_deadline") or ""),
		"approval": {
			"channel": doc.get("approval_channel"),
			"approved_by": doc.get("approved_by"),
			"approved_by_attendant": doc.get("approved_by_attendant"),
			"approval_date": str(doc.get("approval_date") or ""),
			"notes": doc.get("approval_notes"),
			"expired": bool(
				doc.get("approval_deadline")
				and doc.get("workflow_state") == "Aguardando aprovação"
				and doc.get("approval_deadline") < now_datetime()
			),
		},
		"entry_date": str(doc.get("entry_date") or ""),
		"modified": str(doc.get("modified") or ""),
		"attendant": doc.get("attendant"),
		"technician": doc.get("technician"),
		"technical_view": technical_view,
		"priority": doc.get("priority"),
		"customer": _get_customer_detail(doc.get("customer"), include_fiscal=not is_restricted_technician()),
		"device": _get_device_detail(doc.get("customer_device")),
		"reported_defect": doc.get("reported_defect"),
		"physical_state": doc.get("physical_state"),
		"entry_operating_condition": doc.get("entry_operating_condition"),
		"accessories_received": doc.get("accessories_received"),
		"os_contact_name": doc.get("os_contact_name"),
		"os_contact_phone": doc.get("os_contact_phone"),
		"device_access_type": doc.get("device_access_type"),
		"diagnosis": {
			"problem_found": doc.get("problem_found"),
			"diagnosis_date": str(doc.get("diagnosis_date") or ""),
			"diagnosis_deadline": str(doc.get("diagnosis_deadline") or ""),
			"completed_at": str(doc.get("diagnosis_completed_at") or ""),
			"completed_by": doc.get("diagnosis_completed_by"),
			"pricing_responsibility": doc.get("pricing_responsibility"),
			"budget_review_required": bool(doc.get("budget_review_required")),
			"technician_pricing_available": pricing_available,
			"default_pricing_responsibility": pricing_default,
		},
		"services": services,
		"parts": parts,
		"budget": {
			"presentation": doc.get("budget_presentation") or "Fechado",
			"closed_lines": closed_lines,
			"customer_supplied_part_term_required": bool(doc.get("customer_supplied_part_term_required")),
		},
		"totals": {
			"service_total": service_total,
			"parts_price_total": parts_price_total,
			"discount": discount if not technical_view else 0,
			"grand_total": grand_total if not technical_view else service_total + parts_price_total,
			"budget_version": int(doc.get("budget_version") or 1),
			"quote_locked": bool(doc.get("quote_locked")),
		},
		"warranty": {
			"is_warranty": bool(doc.get("is_warranty")),
			"original_service_order": doc.get("original_service_order"),
			"warranty_expiry": str(doc.get("warranty_expiry") or ""),
		},
		"pickup": {
			"without_repair": bool(doc.get("pickup_without_repair")),
			"pickup_by_third_party": bool(doc.get("picked_up_by_third_party")),
			"pickup_person_name": doc.get("picked_up_by"),
			"pickup_person_document": doc.get("picked_up_doc") or doc.get("third_party_doc"),
			"pickup_date": str(doc.get("pickup_date") or ""),
			"pickup_notes": doc.get("pickup_notes"),
			"has_signature": bool(doc.get("customer_signature")),
		},
		"finance": {
			**finance,
		},
		"workflow_actions": _get_visible_workflow_actions(doc),
		"workflow_transitions": _get_service_order_transition_options(doc.get("workflow_state")),
		"workflow_blockers": _get_workflow_blockers(doc),
		"workflow_requestable_transitions": _get_workflow_requestable_transitions(doc),
		"next_action": action_for_service_order(doc),
		"timeline": _get_service_order_timeline(doc),
		"print_links": _get_service_order_print_links(doc.name) if not technical_view else [],
	}


@frappe.whitelist()
def receive_service_order_payment(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Receive one OS amount through the native payment ledger and active cash session."""
	_require_attendant_flow_role()
	order = frappe.get_doc("Service Order", (name or "").strip())
	order.check_permission("write")
	result = service_order_payments.collect_service_order_payment(order.name, _parse_payload(payload))
	return {"payment": result, "detail": get_service_order_detail(order.name)}


@frappe.whitelist()
def list_service_order_tradein_candidates(name: str) -> dict[str, Any]:
	_require_attendant_flow_role()
	order = frappe.get_doc("Service Order", (name or "").strip())
	order.check_permission("read")
	if not get_operation_config()["payments"]["device_tradein_enabled"]:
		return {"items": []}
	items = frappe.get_all(
		"Device Trade Evaluation",
		filters={"customer": order.customer, "approved_value": [">", 0]},
		fields=["name", "evaluated_device_desc", "model", "imei", "approved_value", "workflow_state"],
		order_by="modified desc",
		limit_page_length=30,
	)
	return {
		"items": [
			{
				"name": item.name,
				"label": " ".join(part for part in [item.evaluated_device_desc, item.model] if part) or item.name,
				"amount": flt(item.approved_value, 2),
				"status": item.workflow_state,
			}
			for item in items
		]
	}


@frappe.whitelist()
def save_technical_diagnosis(name: str, problem_found: str) -> dict[str, Any]:
	"""Save a technical diagnosis without granting access to commercial or desk flows."""
	_require_frontend_role()
	roles = set(frappe.get_roles(frappe.session.user))
	if not roles.intersection({"Tecponto Tecnico", "Tecponto Gestor", "Tecponto Diretor", "System Manager"}):
		frappe.throw(_("Somente a equipe técnica pode registrar o diagnóstico."), frappe.PermissionError)

	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("write")
	if is_restricted_technician() and doc.get("technician") != frappe.session.user:
		frappe.throw(_("Você só pode registrar diagnóstico nas suas OS."), frappe.PermissionError)

	clean_problem = strip_html(problem_found or "").strip()
	if not clean_problem:
		frappe.throw(_("Informe o diagnóstico encontrado."), frappe.ValidationError)

	doc.problem_found = clean_problem
	doc.diagnosis_date = now_datetime().date()
	doc.save()
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def complete_technical_diagnosis(name: str, problem_found: str, pricing_responsibility: str) -> dict[str, Any]:
	"""Complete diagnosis and make the pricing hand-off explicit in one transaction."""
	_require_frontend_role()
	roles = set(frappe.get_roles(frappe.session.user))
	if not roles.intersection({"Tecponto Tecnico", "Tecponto Gestor", "System Manager"}):
		frappe.throw(_("Somente a equipe técnica pode concluir o diagnóstico."), frappe.PermissionError)
	clean_problem = strip_html(problem_found or "").strip()
	if not clean_problem:
		frappe.throw(_("Informe o diagnóstico encontrado."), frappe.ValidationError)
	responsibility = (pricing_responsibility or "").strip()
	if responsibility not in {"Técnico", "Balcão"}:
		frappe.throw(_("Escolha quem fará a precificação."), frappe.ValidationError)
	if responsibility == "Técnico" and "Tecponto Tecnico" not in roles and not roles.intersection(ATTENDANT_FLOW_ALLOWED_ROLES):
		frappe.throw(_("Este usuário não possui capacidade para montar o orçamento."), frappe.PermissionError)

	savepoint = f"complete_diagnosis_{frappe.generate_hash(length=8)}"
	frappe.db.savepoint(savepoint)
	try:
		clean_name = (name or "").strip()
		frappe.db.sql("SELECT name FROM `tabService Order` WHERE name=%s FOR UPDATE", (clean_name,))
		doc = frappe.get_doc("Service Order", clean_name)
		doc.check_permission("write")
		if doc.workflow_state != STATE_EM_DIAGNOSTICO:
			frappe.throw(_("A OS precisa estar Em diagnóstico para concluir esta etapa."), frappe.ValidationError)
		if is_restricted_technician() and doc.technician != frappe.session.user:
			frappe.throw(_("Você só pode concluir diagnóstico nas suas OS."), frappe.PermissionError)
		doc.problem_found = clean_problem
		doc.diagnosis_date = now_datetime().date()
		doc.diagnosis_completed_at = now_datetime()
		doc.diagnosis_completed_by = frappe.session.user
		doc.pricing_responsibility = responsibility
		doc.budget_review_required = 0
		doc.save()
		action = _get_allowed_kanban_action(STATE_EM_DIAGNOSTICO, STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO)
		apply_workflow(frappe.as_json({"doctype": doc.doctype, "name": doc.name}), action)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def set_service_order_part_outcome(
	name: str,
	part_name: str,
	outcome: str,
	loss_reason: str = "",
) -> dict[str, Any]:
	"""Record technical part usage and let the existing part engine issue stock once."""
	_require_frontend_role()
	roles = set(frappe.get_roles(frappe.session.user))
	if not roles.intersection({"Tecponto Tecnico", "Tecponto Gestor", "Tecponto Diretor", "System Manager"}):
		frappe.throw(_("Somente a equipe técnica pode registrar o uso de peças."), frappe.PermissionError)

	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("write")
	if is_restricted_technician() and doc.get("technician") != frappe.session.user:
		frappe.throw(_("Você só pode registrar peças nas suas OS."), frappe.PermissionError)
	if doc.get("workflow_state") not in PART_EXECUTION_STATES:
		frappe.throw(_("Registre peças somente após a aprovação do orçamento."), frappe.ValidationError)

	part = next((row for row in doc.get("parts") or [] if row.name == (part_name or "").strip()), None)
	if not part:
		frappe.throw(_("Peça não encontrada nesta ordem de serviço."), frappe.ValidationError)

	outcome = (outcome or "").strip()
	loss_reason = (loss_reason or "").strip()
	if outcome not in {OUTCOME_USADA, OUTCOME_PERDIDA}:
		frappe.throw(_("Desfecho de peça inválido."), frappe.ValidationError)
	if outcome == OUTCOME_PERDIDA and loss_reason not in {LOSS_LOJA, LOSS_TECNICO, LOSS_FORNECEDOR}:
		frappe.throw(_("Informe um motivo válido para a perda da peça."), frappe.ValidationError)
	if outcome == OUTCOME_USADA:
		loss_reason = ""

	if part.get("stock_entry"):
		if part.get("outcome") == outcome and (outcome != OUTCOME_PERDIDA or part.get("loss_reason") == loss_reason):
			return get_service_order_detail(doc.name)
		frappe.throw(_("Esta peça já teve estoque baixado e não pode ter o desfecho alterado."), frappe.ValidationError)

	part.outcome = outcome
	part.loss_reason = loss_reason
	# The technical role intentionally has no generic Desk permission on the child
	# table. This narrowly-scoped endpoint has already validated role, OS scope,
	# workflow stage, part ownership and allowed values; Frappe validations and
	# Service Order on_update hooks still run and own the actual stock issue.
	doc.save(ignore_permissions=True)
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def search_budget_items(
	query: str = "",
	line_type: str = "service",
	limit: int = 12,
) -> dict[str, Any]:
	_require_attendant_flow_role()
	line_type = _validate_budget_line_type(line_type)
	filters: dict[str, Any] = {"disabled": 0}
	if line_type == "service":
		filters["is_stock_item"] = 0
	else:
		filters["is_stock_item"] = 1

	search = (query or "").strip()
	or_filters = None
	if search:
		like = f"%{search}%"
		or_filters = [
			["Item", "name", "like", like],
			["Item", "item_name", "like", like],
			["Item", "item_group", "like", like],
		]

	items = frappe.get_all(
		"Item",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "item_name", "item_group", "is_stock_item", "standard_rate"],
		order_by="modified desc",
		limit_page_length=max(1, min(int(limit or 12), 30)),
	)
	return {
		"items": [
			{
				"item_code": item.name,
				"item_name": item.item_name,
				"item_group": item.item_group,
				"is_stock_item": bool(item.is_stock_item),
				"standard_rate": flt(item.standard_rate or 0),
				"has_price": flt(item.standard_rate or 0) > 0,
			}
			for item in items
		]
	}


@frappe.whitelist()
def search_pos_items(
	query: str = "",
	barcode: str = "",
	limit: int = 12,
) -> dict[str, Any]:
	_require_pos_role()
	query = (query or "").strip()[:80]
	barcode = normalize_barcode(barcode)[:80]
	limit = max(1, min(int(limit or 12), 30))
	fields = [
		"item_code",
		"item_name",
		"item_group",
		"barcode",
		"description",
		"image",
		"standard_rate",
		"has_price",
		"available_qty",
		"warehouse",
	]
	if not query and not barcode:
		return {"items": [], "count": 0, "fields": fields}

	warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	if not warehouse:
		frappe.throw(_("Depósito Comercial não configurado no Tecponto Settings."), frappe.ValidationError)

	commercial_groups = get_commercial_item_groups()
	if not commercial_groups:
		frappe.throw(_("Grupos comerciais do PDV não estão configurados."), frappe.ValidationError)

	conditions = [
		"item.disabled = 0",
		"item.is_stock_item = 1",
		"item.is_sales_item = 1",
		"item.item_group in %(commercial_groups)s",
	]
	values: dict[str, Any] = {
		"commercial_groups": tuple(commercial_groups),
		"limit": limit,
		"warehouse": warehouse,
	}
	if barcode:
		conditions.append(
			"exists (select 1 from `tabItem Barcode` matched_barcode where matched_barcode.parent = item.name and matched_barcode.barcode = %(barcode)s)"
		)
		values["barcode"] = barcode
		barcode_select = "%(barcode)s"
	else:
		conditions.append(
			"(item.name like %(query)s or item.item_name like %(query)s or item.item_group like %(query)s)"
		)
		values["query"] = f"%{query}%"
		barcode_select = "(select item_barcode.barcode from `tabItem Barcode` item_barcode where item_barcode.parent = item.name order by item_barcode.idx asc limit 1)"

	rows = frappe.db.sql(
		f"""
		select
			item.name as item_code,
			item.item_name,
			item.item_group,
			item.has_serial_no,
			{barcode_select} as barcode,
			item.description,
			item.image,
			item.standard_rate,
			coalesce(bin.actual_qty, 0) as available_qty,
			%(warehouse)s as warehouse
		from `tabItem` item
		left join `tabBin` bin
			on bin.item_code = item.name
			and bin.warehouse = %(warehouse)s
		where {" and ".join(conditions)}
		order by item.item_name asc, item.name asc
		limit %(limit)s
		""",
		values,
		as_dict=True,
	)
	items = [_serialize_pos_item(item) for item in rows]
	return {"items": items, "count": len(items), "fields": fields}


@frappe.whitelist()
def list_budget_warehouses(query: str = "", limit: int = 12) -> dict[str, Any]:
	_require_attendant_flow_role()
	filters: dict[str, Any] = {"is_group": 0, "disabled": 0}
	search = (query or "").strip()
	or_filters = None
	if search:
		like = f"%{search}%"
		or_filters = [
			["Warehouse", "name", "like", like],
			["Warehouse", "warehouse_name", "like", like],
		]

	warehouses = frappe.get_all(
		"Warehouse",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "warehouse_name"],
		order_by="warehouse_name asc",
		limit_page_length=max(1, min(int(limit or 12), 30)),
	)
	return {"items": [dict(warehouse) for warehouse in warehouses]}


@frappe.whitelist()
def add_service_order_budget_line(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_budget_edit_role()
	data = _parse_payload(payload)
	line_type = _validate_budget_line_type(data.get("type") or data.get("line_type"))
	item_code = (data.get("item_code") or "").strip()
	part_source = (data.get("part_source") or "Loja").strip()
	qty = flt(data.get("qty") or 0)
	rate = flt(data.get("rate") or 0)

	if part_source not in {"Loja", "Cliente"}:
		frappe.throw(_("Origem da peça inválida."), frappe.ValidationError)
	if line_type == "service" and part_source != "Loja":
		frappe.throw(_("Origem de peça só se aplica a linhas de peça."), frappe.ValidationError)
	if line_type == "service" and not item_code:
		from tecponto_app.tecponto.service_order.billing import _get_labor_item
		item_code = _get_labor_item()
	if not item_code and not (line_type == "part" and part_source == "Cliente"):
		frappe.throw(_("Selecione o item do orçamento."), frappe.ValidationError)
	if qty <= 0:
		frappe.throw(_("Quantidade precisa ser maior que zero."), frappe.ValidationError)
	if rate < 0:
		frappe.throw(_("Valor unitário não pode ser negativo."), frappe.ValidationError)

	item = None
	if item_code:
		item = frappe.db.get_value(
			"Item", item_code, ["name", "item_name", "is_stock_item", "disabled"], as_dict=True
		)
		if not item or item.disabled:
			frappe.throw(_("Item do orçamento inválido."), frappe.ValidationError)
		if line_type == "service" and item.is_stock_item:
			frappe.throw(_("Serviço do orçamento deve ser um item não estocável."), frappe.ValidationError)
		if line_type == "part" and not item.is_stock_item:
			frappe.throw(_("Peça do orçamento deve ser um item de estoque."), frappe.ValidationError)

	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("write")
	if line_type == "service":
		# Warranty labor is recorded for traceability, but never billed to the customer.
		if doc.get("is_warranty"):
			rate = 0
		doc.append(
			"services",
			{
				"item_code": item.name,
				"description": (data.get("description") or item.item_name or item.name).strip(),
				"qty": qty,
				"rate": rate,
			},
		)
	else:
		service_row = (data.get("service_row") or "").strip()
		if service_row and service_row not in {row.name for row in (doc.get("services") or [])}:
			frappe.throw(_("Serviço vinculado inválido para esta OS."), frappe.ValidationError)
		warehouse = None
		if part_source == "Loja":
			warehouse = (data.get("warehouse") or "").strip() or _get_default_repair_warehouse()
			if not warehouse:
				frappe.throw(_("Informe o estoque da peça."), frappe.ValidationError)
			if not frappe.db.exists("Warehouse", {"name": warehouse, "is_group": 0, "disabled": 0}):
				frappe.throw(_("Estoque da peça inválido."), frappe.ValidationError)
		else:
			rate = 0
			if not (data.get("description") or "").strip():
				frappe.throw(_("Identifique a peça fornecida pelo cliente."), frappe.ValidationError)
		doc.append(
			"parts",
			{
				"item_code": item.name if item else None,
				"description": (data.get("description") or (item.item_name if item else "") or (item.name if item else "")).strip(),
				"qty": qty,
				"warehouse": warehouse,
				"rate": rate,
				"part_source": part_source,
				"service_row": service_row or None,
				"customer_part_note": (data.get("customer_part_note") or "").strip() or None,
			},
		)
		if part_source == "Cliente":
			doc.customer_supplied_part_term_required = 1

	doc.save(ignore_permissions=True)
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def add_catalog_service_to_service_order(name: str, catalog_service: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Add a catalog suggestion while preserving the ability to adjust it per OS."""
	_require_budget_edit_role()
	data = _parse_payload(payload)
	catalog = frappe.db.get_value(
		"Tecponto Service",
		(catalog_service or "").strip(),
		["name", "service_name", "category", "default_labor_price", "default_duration", "duration_unit", "active"],
		as_dict=True,
	)
	if not catalog or not catalog.active:
		frappe.throw(_("Selecione um serviço ativo do catálogo."), frappe.ValidationError)

	qty = flt(data.get("qty") or 1)
	rate = flt(data["rate"]) if "rate" in data and data.get("rate") not in (None, "") else flt(catalog.default_labor_price)
	duration = flt(data["duration"]) if "duration" in data and data.get("duration") not in (None, "") else flt(catalog.default_duration)
	duration_unit = (data.get("duration_unit") or catalog.duration_unit or "Horas").strip()
	if qty <= 0:
		frappe.throw(_("Quantidade precisa ser maior que zero."), frappe.ValidationError)
	if rate < 0 or duration < 0:
		frappe.throw(_("Preço e prazo não podem ser negativos."), frappe.ValidationError)
	if duration_unit not in {"Horas", "Dias úteis"}:
		frappe.throw(_("Unidade do prazo inválida."), frappe.ValidationError)

	from tecponto_app.tecponto.service_order.billing import _get_labor_item

	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("write")
	# The catalog remains useful for quality/rework reporting in warranty jobs. Its
	# suggestion is deliberately kept, but labor is always zero on the OS.
	if doc.get("is_warranty"):
		rate = 0
	doc.append(
		"services",
		{
			"item_code": _get_labor_item(),
			"catalog_service": catalog.name,
			"service_category": catalog.category,
			"description": (data.get("description") or catalog.service_name).strip(),
			"qty": qty,
			"rate": rate,
			"service_duration": duration,
			"duration_unit": duration_unit,
		},
	)
	doc.save(ignore_permissions=True)
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def remove_service_order_budget_line(name: str, line_name: str, line_type: str = "service") -> dict[str, Any]:
	_require_budget_edit_role()
	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("write")
	if doc.get("workflow_state") in {"Entregue", "Cancelado"}:
		frappe.throw(_("O orçamento não pode ser alterado após o encerramento da OS."), frappe.ValidationError)
	if doc.get("quote_locked"):
		frappe.throw(_("O orçamento está travado e não permite remoção de itens."), frappe.ValidationError)
	table_name = "services" if line_type == "service" else "parts"
	table = doc.get(table_name) or []
	filtered = [row for row in table if row.name != (line_name or "").strip()]
	if len(filtered) == len(table):
		frappe.throw(_("Item do orçamento não encontrado."), frappe.ValidationError)
	doc.set(table_name, filtered)
	if line_type == "part" and not any(row.part_source == "Cliente" for row in (doc.get("parts") or [])):
		doc.customer_supplied_part_term_required = 0
	doc.save(ignore_permissions=True)
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def update_service_order_budget_presentation(name: str, presentation: str = "Discriminado") -> dict[str, Any]:
	_require_budget_edit_role()
	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("write")
	if presentation not in {"Discriminado", "Fechado"}:
		frappe.throw(_("Formato de apresentação inválido."), frappe.ValidationError)
	doc.budget_presentation = presentation
	doc.save(ignore_permissions=True)
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def list_warranty_candidates(customer: str = "", customer_device: str = "") -> dict[str, Any]:
	"""Return only active, readable warranty originals for the selected check-in context."""
	_require_checkin_role()
	filters: dict[str, Any] = {
		"workflow_state": STATE_ENTREGUE,
		"is_warranty": 0,
		"warranty_expiry": [">=", today()],
	}
	if (customer_device or "").strip():
		filters["customer_device"] = customer_device.strip()
	elif (customer or "").strip():
		filters["customer"] = customer.strip()
	else:
		return {"items": []}

	rows = frappe.get_list(
		"Service Order",
		filters=filters,
		fields=["name", "customer", "customer_device", "reported_defect", "pickup_date", "warranty_expiry"],
		order_by="pickup_date desc, modified desc",
		limit_page_length=12,
	)
	return {
		"items": [
			{
				"name": row.name,
				"reported_defect": row.reported_defect,
				"pickup_date": row.pickup_date,
				"warranty_expiry": row.warranty_expiry,
			}
			for row in rows
		]
	}


@frappe.whitelist()
def search_service_order_warranties(query: str, search_by: str = "os", limit: int = 30) -> dict[str, Any]:
	"""Safe warranty desk projection; the Service Order policy remains authoritative."""
	_require_frontend_role()
	query = (query or "").strip()[:100]
	search_by = (search_by or "os").strip().lower()
	if search_by not in {"os", "imei", "customer"}:
		frappe.throw(_("Tipo de consulta de garantia inválido."), frappe.ValidationError)
	if not query:
		return {"items": [], "count": 0, "can_start_service": _can_start_warranty_service()}
	filters: dict[str, Any] = {"workflow_state": STATE_ENTREGUE, "is_warranty": 0, "warranty_expiry": ["is", "set"]}
	if search_by == "os":
		filters["name"] = ["like", f"%{query}%"]
	elif search_by == "imei":
		devices = frappe.get_all("Customer Device", filters={"imei_serial": ["like", f"%{query}%"]}, pluck="name", limit_page_length=100)
		filters["customer_device"] = ["in", devices or [""]]
	else:
		customers = list(set(
			frappe.get_all("Customer", filters={"name": ["like", f"%{query}%"]}, pluck="name", limit_page_length=100)
			+ frappe.get_all("Customer", filters={"customer_name": ["like", f"%{query}%"]}, pluck="name", limit_page_length=100)
		))
		filters["customer"] = ["in", customers or [""]]
	filters = _with_service_order_scope(filters)
	rows = frappe.get_list(
		"Service Order",
		filters=filters,
		fields=["name", "customer", "customer_device", "reported_defect", "pickup_date", "warranty_expiry"],
		order_by="pickup_date desc, modified desc",
		limit_page_length=max(1, min(int(limit or 30), 50)),
	)
	services_by_order: dict[str, list[str]] = {row.name: [] for row in rows}
	if rows:
		for service in frappe.get_all(
			"Service Order Service",
			filters={"parent": ["in", list(services_by_order)]},
			fields=["parent", "description"],
			order_by="idx asc",
			limit_page_length=500,
		):
			if service.description:
				services_by_order[service.parent].append(service.description)
	items = []
	for row in rows:
		expires = getdate(row.warranty_expiry)
		remaining_days = (expires - getdate(today())).days
		device = frappe.db.get_value("Customer Device", row.customer_device, ["brand", "model", "imei_serial"], as_dict=True) or {}
		items.append({
			"service_order": row.name,
			"customer": row.customer,
			"customer_device": row.customer_device,
			"device_label": " ".join(value for value in (device.get("brand"), device.get("model")) if value) or row.customer_device,
			"imei_serial": device.get("imei_serial"),
			"reported_defect": row.reported_defect,
			"delivery_date": str(row.pickup_date or ""),
			"warranty_expiry": str(row.warranty_expiry or ""),
			"warranty_days": max(0, (expires - getdate(row.pickup_date)).days) if row.pickup_date else 0,
			"remaining_days": max(0, remaining_days),
			"status": "vigente" if remaining_days >= 0 else "expirada",
			"covered_services": services_by_order[row.name] or [row.reported_defect or "Serviço executado na OS"],
			"coverage": "Mão de obra e serviço executado nesta OS; não cobre dano posterior, mau uso, intervenção de terceiros, falha diferente nem peça fornecida pelo cliente.",
		})
	return {"items": items, "count": len(items), "can_start_service": _can_start_warranty_service()}


def _can_start_warranty_service() -> bool:
	return bool(set(frappe.get_roles(frappe.session.user)).intersection(CHECKIN_ALLOWED_ROLES))


@frappe.whitelist()
def send_service_order_quote(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_attendant_flow_role()
	data = _parse_payload(payload)
	channel = (data.get("channel") or "").strip()
	notes = (data.get("notes") or "").strip()

	if channel not in QUOTE_SEND_CHANNELS:
		frappe.throw(_("Canal de envio do orçamento inválido."), frappe.ValidationError)

	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("read")

	if not (doc.get("services") or doc.get("parts")):
		frappe.throw(_("Inclua ao menos um serviço ou peça antes de enviar o orçamento."), frappe.ValidationError)

	if doc.get("workflow_state") != STATE_AGUARDANDO_APROVACAO:
		if doc.get("workflow_state") in {STATE_ENTRADA_CRIADA, STATE_EM_DIAGNOSTICO, STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO}:
			doc.workflow_state = STATE_AGUARDANDO_APROVACAO
			doc.approval_status = "Pendente"
			doc.quote_locked = 1
			doc.save(ignore_permissions=True)
		else:
			frappe.throw(_("A OS precisa estar em diagnóstico ou aguardando aprovação para enviar orçamento."), frappe.ValidationError)

	customer = _get_customer_detail(doc.get("customer")) or {}
	phone = customer.get("custom_whatsapp") or customer.get("mobile_no") or ""
	email = customer.get("email_id") or ""
	communication = frappe.get_doc(
		{
			"doctype": "Communication",
			"subject": f"Orçamento enviado - {doc.name}",
			"communication_medium": QUOTE_SEND_MEDIUM_BY_CHANNEL[channel],
			"communication_type": "Communication",
			"sent_or_received": "Sent",
			"status": "Linked",
			"sender": frappe.session.user,
			"recipients": email if channel == "E-mail" else "",
			"phone_no": phone if channel in {"WhatsApp", "Telefone"} else "",
			"content": _quote_send_content(doc, channel, notes),
			"text_content": _quote_send_text(doc, channel, notes),
			"communication_date": now_datetime(),
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"user": frappe.session.user,
		}
	)
	communication.insert(ignore_permissions=True)
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def create_service_order_checkin(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_checkin_role()
	data = _parse_payload(payload)
	_validate_checkin_payload(data)

	customer_name = _get_or_create_checkin_customer(data["customer"])
	device_name = _get_or_create_checkin_device(data["device"], customer_name)
	order = frappe.new_doc("Service Order")
	order.naming_series = "OS-.YYYY.-.#####"
	order.customer = customer_name
	order.os_contact_name = (data["service_order"].get("contact_name") or "").strip()
	order.os_contact_phone = (data["service_order"].get("contact_phone") or "").strip()
	order.customer_device = device_name
	order.entry_date = now_datetime()
	order.attendant = frappe.session.user
	order.workflow_state = "Entrada criada"
	order.link_acceptance_required = 1
	order.priority = "Normal"
	order.reported_defect = data["service_order"]["reported_defect"].strip()
	order.physical_state = data["service_order"]["physical_state"].strip()
	order.attendance_notes = (data["service_order"].get("attendance_notes") or "").strip()
	order.entry_operating_condition = (data["service_order"].get("entry_operating_condition") or ENTRY_OPERATING_CONDITION_OK).strip()
	order.accessories_received = (data["service_order"].get("accessories_received") or "").strip()
	order.device_access_type = (data["service_order"].get("device_access_type") or "").strip()
	order.device_access_credential = (data["service_order"].get("device_access_credential") or "").strip()
	order.is_warranty = cint(data["service_order"].get("is_warranty"))
	order.original_service_order = (data["service_order"].get("original_service_order") or "").strip() or None
	selected_defects = _checkin_defects(data["service_order"].get("defects"))
	suggested_services = defect_service_mapping.resolve_services(selected_defects)
	initial_budget_lines = data.get("initial_budget_lines") or []
	if not isinstance(initial_budget_lines, list):
		frappe.throw(_("Composição do orçamento inicial inválida."), frappe.ValidationError)
	# Prazo pertence ao diagnóstico/orçamento, não à Entrada.
	order.estimated_deadline = None
	if cint(data["service_order"].get("include_initial_budget")) and not initial_budget_lines:
		_append_checkin_service_suggestions(order, suggested_services)
	order.insert(ignore_permissions=True)
	if cint(data["service_order"].get("include_initial_budget")):
		from tecponto_app.tecponto.service_order.billing import _get_labor_item
		for line in initial_budget_lines:
			if not isinstance(line, dict):
				frappe.throw(_("Linha do orçamento inicial inválida."), frappe.ValidationError)
			line_payload = dict(line)
			if line_payload.get("type") == "service" and not (line_payload.get("item_code") or "").strip():
				line_payload["item_code"] = _get_labor_item()
			add_service_order_budget_line(order.name, line_payload)

	photo_url = _save_checkin_photo(order.name, data["entry_photo"])
	frappe.db.set_value(
		"Service Order",
		order.name,
		{"entry_photos": photo_url},
		update_modified=True,
	)
	from tecponto_app.tecponto.service_order.assignment import auto_assign_single_technician

	auto_assignment = auto_assign_single_technician(order.name, frappe.session.user)
	from tecponto_app.tecponto.tracking import issue_tracking_link

	tracking = issue_tracking_link(order.name)
	workflow_state, technician = frappe.db.get_value(
		"Service Order", order.name, ["workflow_state", "technician"]
	)

	return {
		"service_order": {
			"name": order.name,
			"workflow_state": workflow_state,
			"technician": technician,
			"customer": _get_customer_detail(customer_name),
			"device": _get_device_detail(device_name),
			"print_links": _get_service_order_print_links(order.name),
		},
		"entry_photo_url": photo_url,
		"tracking": tracking,
		"auto_assignment": auto_assignment,
	}


@frappe.whitelist()
def update_service_order_entry(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Edit only check-in facts; workflow, gates and budget stay under their own motors."""
	_require_checkin_role()
	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("write")
	if doc.get("workflow_state") in {"Entregue", "Cancelado"}:
		frappe.throw(_("A entrada não pode ser editada após o encerramento da OS."), frappe.ValidationError)
	data = _parse_payload(payload)
	text_fields = {
		"reported_defect", "physical_state", "attendance_notes", "entry_operating_condition",
		"accessories_received", "os_contact_name", "os_contact_phone", "device_access_type",
	}
	for fieldname in text_fields:
		if fieldname in data:
			doc.set(fieldname, (data.get(fieldname) or "").strip())
	if "device_access_credential" in data and (data.get("device_access_credential") or "").strip():
		doc.device_access_credential = data["device_access_credential"].strip()
	if not (doc.reported_defect or "").strip() or not (doc.physical_state or "").strip():
		frappe.throw(_("Defeito relatado e estado físico são obrigatórios na Entrada."), frappe.ValidationError)
	if doc.entry_operating_condition not in ENTRY_OPERATING_CONDITIONS:
		frappe.throw(_("Condição de funcionamento inválida."), frappe.ValidationError)
	# The endpoint allowlist is the authority here; permlevel 1 keeps the secret
	# out of generic forms while the check-in operator may rotate it explicitly.
	doc.save(ignore_permissions=True)
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def get_checkin_delivery_suggestion(
	payload: str | dict[str, Any] | None = None,
	defects: str | list[str] | tuple[str, ...] | None = None,
	lead_time_business_hours: float = 0,
) -> dict[str, Any]:
	_require_checkin_role()
	data = _parse_payload(payload)
	# Keep the transition safe for a browser that still has the previous bundle
	# cached: it posted defects directly instead of under `payload`.
	if not data:
		data = {"defects": defects or [], "lead_time_business_hours": lead_time_business_hours}
	return defect_service_mapping.calculate_delivery_suggestion(
		_checkin_defects(data.get("defects")),
		lead_time_business_hours=data.get("lead_time_business_hours") or 0,
	)


@frappe.whitelist()
def list_defect_service_mappings(include_inactive: bool = True) -> dict[str, Any]:
	_require_frontend_role()
	return defect_service_mapping.list_mappings(include_inactive=bool(cint(include_inactive)))


@frappe.whitelist()
def save_defect_service_mapping(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_service_catalog_editor()
	return {"item": defect_service_mapping.save_mapping(_parse_payload(payload))}


@frappe.whitelist()
def list_stage_slas() -> dict[str, Any]:
	_require_frontend_role()
	return {"items": [stage_sla._serialize_sla(row) for row in stage_sla.get_stage_slas()]}


@frappe.whitelist()
def save_stage_sla(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_user_management_role()
	return {"item": stage_sla.save_stage_sla(_parse_payload(payload))}


@frappe.whitelist()
def decide_service_order_budget(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_attendant_flow_role()
	data = _parse_payload(payload)
	decision = (data.get("decision") or "").strip()
	channel = (data.get("channel") or "").strip()
	notes = (data.get("notes") or "").strip()

	if decision not in {"approve", "reject"}:
		frappe.throw(_("Informe se o orçamento foi aprovado ou reprovado."), frappe.ValidationError)
	if channel not in APPROVAL_CHANNELS:
		frappe.throw(_("Canal de aprovação inválido."), frappe.ValidationError)
	if decision == "reject" and not notes:
		frappe.throw(_("Informe o motivo da reprovação."), frappe.ValidationError)
	approval_evidence = None
	if decision == "approve" and channel != "Link":
		approval_evidence = _decode_private_approval_evidence(data.get("attachment"))

	doc = frappe.get_doc("Service Order", name)
	if doc.get("workflow_state") != STATE_AGUARDANDO_APROVACAO:
		frappe.throw(_("A OS precisa estar em Aguardando aprovação."), frappe.ValidationError)
	if decision == "approve":
		from tecponto_app.tecponto.service_order.deadline import assert_budget_approval_within_deadline

		assert_budget_approval_within_deadline(doc)
	elif get_operation_config()["diagnostic_fee"]["enabled"]:
		# The fee is configured by the store, not typed by the attendant. Billing
		# will add it to the native invoice when the rejection workflow is applied.
		frappe.db.set_value(
			doc.doctype,
			doc.name,
			{
				"diagnosis_fee_enabled": 1,
				"diagnosis_fee_value": flt(get_operation_config()["diagnostic_fee"]["amount"], 2),
			},
			update_modified=False,
		)
		doc.diagnosis_fee_enabled = 1
		doc.diagnosis_fee_value = flt(get_operation_config()["diagnostic_fee"]["amount"], 2)

	if decision == "approve":
		approval_status = APPROVAL_STATUS_APROVADO
		approved_by = frappe.session.user
		workflow_action = STATE_APROVADO
	else:
		approval_status = APPROVAL_STATUS_REPROVADO
		approved_by = None
		workflow_action = STATE_REPROVADO

	frappe.db.set_value(
		doc.doctype,
		doc.name,
		{
			"approval_status": approval_status,
			"approved_by": approved_by,
			"approval_channel": channel,
			"approved_by_attendant": frappe.session.user,
			"approval_notes": notes,
			"approval_date": now_datetime(),
		},
		update_modified=False,
	)

	if decision == "approve" and channel != "Link":
		if approval_evidence:
			from frappe.utils.file_manager import save_file
			content, extension = approval_evidence
			save_file(f"comprovante_{doc.name}.{extension}", content, doc.doctype, doc.name, is_private=1)

	apply_workflow(frappe.as_json({"doctype": doc.doctype, "name": doc.name}), workflow_action)

	return get_service_order_detail(doc.name)


def _decode_private_approval_evidence(attachment: Any) -> tuple[bytes, str]:
	from base64 import b64decode
	from binascii import Error as Base64Error

	allowed = {
		"data:image/jpeg;base64": "jpg",
		"data:image/png;base64": "png",
		"data:image/webp;base64": "webp",
		"data:application/pdf;base64": "pdf",
	}
	if not isinstance(attachment, str) or "," not in attachment:
		frappe.throw(_("Anexe uma foto, imagem ou PDF real como comprovante da aprovação."), frappe.ValidationError)
	header, encoded = attachment.split(",", 1)
	if header not in allowed:
		frappe.throw(_("Formato do comprovante inválido. Use JPG, PNG, WEBP ou PDF."), frappe.ValidationError)
	try:
		content = b64decode(encoded, validate=True)
	except (Base64Error, ValueError):
		frappe.throw(_("O arquivo do comprovante está corrompido."), frappe.ValidationError)
	if not content or len(content) > 8 * 1024 * 1024:
		frappe.throw(_("O comprovante deve ter entre 1 byte e 8 MB."), frappe.ValidationError)
	return content, allowed[header]


@frappe.whitelist()
def record_quote_follow_up(
	name: str,
	channel: str = "WhatsApp",
	result: str = "Sem resposta",
	notes: str = "",
) -> dict[str, Any]:
	"""Record an operational follow-up contact attempt for an in-flight quote."""
	_require_attendant_flow_role()
	doc = frappe.get_doc("Service Order", (name or "").strip())
	doc.check_permission("write")
	channel = (channel or "WhatsApp").strip()
	result = (result or "Sem resposta").strip()
	notes = (notes or "").strip()

	content = f"Follow-up de Orçamento via {channel} · Resultado: {result}"
	if notes:
		content += f"\nObservação: {notes}"

	doc.add_comment(
		comment_type="Comment",
		text=content,
		comment_by=frappe.session.user,
	)
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def get_quotes_crm_panel(
	status: str = "all",
	channel: str = "all",
	query: str = "",
	limit: int = 50,
	in_progress: int | bool | str | None = True,
	from_date: str = "",
	to_date: str = "",
) -> dict[str, Any]:
	"""CRM pipeline projection for service order quotes without leaking costs."""
	_require_frontend_role()
	limit = max(1, min(int(limit or 50), 100))

	status = (status or "all").strip()
	legacy_in_progress = status == "in_progress"
	in_progress_only = legacy_in_progress if in_progress is None else str(in_progress).strip().lower() in {"1", "true", "yes"}
	if legacy_in_progress:
		status = "all"

	filters: dict[str, Any] = {
		"workflow_state": [
			"in",
			[
				STATE_AGUARDANDO_APROVACAO,
				STATE_APROVADO,
				STATE_REPROVADO,
				"Orçamento expirado",
				"Aguardando peça",
				"Em reparo",
				"Teste final",
				STATE_PRONTO_RETIRADA,
				STATE_ENTREGUE,
			],
		],
	}
	if in_progress_only:
		filters["pickup_date"] = ["is", "not set"]
	if status == "pending":
		filters["workflow_state"] = STATE_AGUARDANDO_APROVACAO
	elif status == "approved":
		filters["approval_status"] = APPROVAL_STATUS_APROVADO
	elif status == "rejected":
		filters["approval_status"] = APPROVAL_STATUS_REPROVADO
	elif status == "expired":
		filters["workflow_state"] = "Orçamento expirado"

	from_date = (from_date or "").strip()
	to_date = (to_date or "").strip()
	if from_date and to_date:
		filters["modified"] = ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]
	elif from_date:
		filters["modified"] = [">=", f"{from_date} 00:00:00"]
	elif to_date:
		filters["modified"] = ["<=", f"{to_date} 23:59:59"]

	if channel and channel != "all":
		filters["approval_channel"] = channel

	fields = [
		"name",
		"customer",
		"customer_device",
		"reported_defect",
		"problem_found",
		"workflow_state",
		"approval_status",
		"approval_channel",
		"approval_date",
		"approved_by_attendant",
		"approval_notes",
		"budget_version",
		"os_contact_name",
		"os_contact_phone",
		"modified",
		"creation",
		"pickup_date",
	]

	or_filters = None
	if (query or "").strip():
		q = f"%{query.strip()}%"
		or_filters = [
			["name", "like", q],
			["customer", "like", q],
			["customer_device", "like", q],
			["reported_defect", "like", q],
			["problem_found", "like", q],
			["os_contact_name", "like", q],
		]

	orders = frappe.get_list(
		"Service Order",
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by="modified desc",
		limit_page_length=limit,
	)

	all_quotes = frappe.get_list(
		"Service Order",
		filters={"workflow_state": ["in", [STATE_AGUARDANDO_APROVACAO, STATE_APROVADO, STATE_REPROVADO, "Orçamento expirado"]]},
		fields=["name", "workflow_state", "approval_status", "modified"],
		limit_page_length=500,
	)

	pending_count = sum(1 for q in all_quotes if q.workflow_state == STATE_AGUARDANDO_APROVACAO or q.approval_status == "Pendente")
	approved_count = sum(1 for q in all_quotes if q.approval_status == APPROVAL_STATUS_APROVADO or q.workflow_state == STATE_APROVADO)
	rejected_count = sum(1 for q in all_quotes if q.approval_status == APPROVAL_STATUS_REPROVADO or q.workflow_state == STATE_REPROVADO)
	expired_count = sum(1 for q in all_quotes if q.workflow_state == "Orçamento expirado")
	total_decided = approved_count + rejected_count
	conversion_rate = round((approved_count / total_decided * 100), 1) if total_decided > 0 else 0.0

	items = []
	now_time = now_datetime()
	for row in orders:
		services = frappe.db.sql(
			"SELECT SUM(rate * qty) as total FROM `tabService Order Service` WHERE parent = %s",
			row.name,
			as_dict=True,
		)
		parts = frappe.db.sql(
			"SELECT SUM(rate * qty) as total FROM `tabService Order Part` WHERE parent = %s",
			row.name,
			as_dict=True,
		)
		service_total = flt(services[0].total) if services and services[0].total else 0.0
		parts_total = flt(parts[0].total) if parts and parts[0].total else 0.0
		grand_total = service_total + parts_total

		days_pending = 0
		if row.modified:
			mod_dt = get_datetime(row.modified)
			days_pending = max(0, (now_time - mod_dt).days)
		elif row.creation:
			create_dt = get_datetime(row.creation)
			days_pending = max(0, (now_time - create_dt).days)

		device_info = frappe.db.get_value("Customer Device", row.customer_device, ["brand", "model"], as_dict=True) if row.customer_device else None
		device_label = f"{device_info.brand} {device_info.model}".strip() if device_info else (row.customer_device or "Aparelho não identificado")

		items.append(
			{
				"name": row.name,
				"customer": row.customer,
				"phone": row.os_contact_phone or frappe.db.get_value("Customer", row.customer, "custom_whatsapp") or frappe.db.get_value("Customer", row.customer, "mobile_no") or "",
				"contact_name": row.os_contact_name or row.customer,
				"device_label": device_label,
				"reported_defect": row.reported_defect,
				"problem_found": row.problem_found,
				"workflow_state": row.workflow_state,
				"approval_status": row.approval_status or ("Pendente" if row.workflow_state == STATE_AGUARDANDO_APROVACAO else "Não enviado"),
				"approval_channel": row.approval_channel,
				"approval_date": row.approval_date,
				"approved_by_attendant": row.approved_by_attendant,
				"approval_notes": row.approval_notes,
				"budget_version": row.budget_version or 1,
				"grand_total": grand_total,
				"days_pending": days_pending,
				"follow_ups": _get_quote_follow_ups(row.name),
			}
		)

	return {
		"summary": {
			"pending_count": pending_count,
			"approved_count": approved_count,
			"rejected_count": rejected_count,
			"expired_count": expired_count,
			"conversion_rate": conversion_rate,
		},
		"items": items,
	}


def _get_quote_follow_ups(service_order: str) -> list[dict[str, str]]:
	rows = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "Service Order",
			"reference_name": service_order,
			"comment_type": "Comment",
			"content": ["like", "Follow-up de Orçamento via%"],
		},
		fields=["content", "comment_by", "comment_email", "creation"],
		order_by="creation desc",
		limit_page_length=20,
	)
	events = []
	for row in rows:
		text = strip_html(row.content or "")
		first_line, _, note = text.partition("\n")
		prefix = "Follow-up de Orçamento via "
		channel_result = first_line[len(prefix):] if first_line.startswith(prefix) else first_line
		channel, _, result = channel_result.partition(" · Resultado: ")
		events.append(
			{
				"channel": channel.strip(),
				"result": result.strip(),
				"notes": note.replace("Observação:", "", 1).strip(),
				"date": str(row.creation or ""),
				"user": _get_user_display_name(row.comment_email or row.comment_by),
			}
		)
	return events


@frappe.whitelist()
def prepare_service_order_pickup(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_attendant_flow_role()
	data = _parse_payload(payload)
	doc = frappe.get_doc("Service Order", name)
	if doc.get("workflow_state") != STATE_PRONTO_RETIRADA:
		frappe.throw(_("A OS precisa estar Pronto para retirada."), frappe.ValidationError)

	third_party = bool(data.get("third_party"))
	picked_up_by = (data.get("picked_up_by") or "").strip()
	picked_up_doc = (data.get("picked_up_doc") or "").strip()
	pickup_notes = (data.get("pickup_notes") or "").strip()
	if third_party and not picked_up_by:
		frappe.throw(_("Informe o nome de quem está retirando."), frappe.ValidationError)
	if third_party and not picked_up_doc:
		frappe.throw(_("Informe o documento de quem está retirando."), frappe.ValidationError)

	frappe.db.set_value(
		doc.doctype,
		doc.name,
		{
			"picked_up_by": picked_up_by or _customer_label(doc.get("customer")),
			"picked_up_doc": picked_up_doc,
			"picked_up_by_third_party": 1 if third_party else 0,
			"third_party_doc": picked_up_doc if third_party else None,
			"third_party_auth": (data.get("third_party_auth") or "").strip() if third_party else None,
			"pickup_notes": pickup_notes,
		},
		update_modified=False,
	)
	return get_service_order_detail(doc.name)


@frappe.whitelist()
def complete_service_order_pickup(name: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_attendant_flow_role()
	data = _parse_payload(payload)
	doc = frappe.get_doc("Service Order", name)
	if doc.get("workflow_state") != STATE_PRONTO_RETIRADA:
		frappe.throw(_("A OS precisa estar Pronto para retirada."), frappe.ValidationError)

	acceptance_name = (data.get("acceptance_name") or "").strip()
	if not acceptance_name:
		frappe.throw(_("Gere e conclua o aceite por link antes de entregar."), frappe.ValidationError)
	acceptance = frappe.get_doc("OS Acceptance", acceptance_name)
	if acceptance.service_order != doc.name or acceptance.acceptance_type != "Retirada" or acceptance.status != "Concluído":
		frappe.throw(_("O aceite de retirada ainda não foi concluído pelo cliente."), frappe.ValidationError)
	from tecponto_app.tecponto.acceptance import has_completed_physical_acceptance
	if not doc.get("customer_signature") and not has_completed_physical_acceptance(doc.name, "Retirada"):
		frappe.throw(_("A assinatura de retirada ou via física arquivada ainda não foi registrada."), frappe.ValidationError)

	frappe.db.set_value(doc.doctype, doc.name, "pickup_date", now_datetime(), update_modified=False)
	apply_workflow(frappe.as_json({"doctype": doc.doctype, "name": doc.name}), STATE_ENTREGUE)

	return get_service_order_detail(doc.name)


@frappe.whitelist()
def get_dashboard_metrics() -> dict[str, Any]:
	_require_frontend_role()
	service_scope = service_order_scope_filters()
	service_orders = {
		"total": frappe.db.count("Service Order", service_scope),
		"in_diagnosis": frappe.db.count("Service Order", {**service_scope, "workflow_state": "Em diagnóstico"}),
		"awaiting_approval": frappe.db.count("Service Order", {**service_scope, "workflow_state": "Aguardando aprovação"}),
		"ready_for_pickup": frappe.db.count("Service Order", {**service_scope, "workflow_state": "Pronto para retirada"}),
		"waiting_part": frappe.db.count("Service Order", {**service_scope, "workflow_state": "Aguardando peça"}),
		"ready_for_test": frappe.db.count("Service Order", {**service_scope, "workflow_state": "Teste final"}),
		"new_today": frappe.db.count("Service Order", {**service_scope, "creation": [">=", today()]}),
		"overdue": _count_overdue_service_orders(service_scope),
	}
	sales_visible = not is_restricted_technician()
	sales_today_total = 0
	if sales_visible:
		sales_today_total = frappe.db.sql(
			"""
			select coalesce(sum(grand_total), 0)
			from `tabSales Invoice`
			where docstatus = 1
				and is_return = 0
				and posting_date = %(posting_date)s
			""",
			{"posting_date": today()},
		)[0][0]

	sales_tickets = {
		"retail": {"count": 0, "total": 0.0, "average": None},
		"service_order": {"count": 0, "total": 0.0, "average": None},
	}
	if sales_visible:
		for row in frappe.db.sql(
			"""
			select is_pos, count(*) as sales_count, coalesce(sum(grand_total), 0) as sales_total
			from `tabSales Invoice`
			where docstatus = 1 and is_return = 0 and posting_date = %(posting_date)s
			group by is_pos
			""",
			{"posting_date": today()},
			as_dict=True,
		):
			key = "retail" if cint(row.is_pos) else "service_order"
			count = int(row.sales_count or 0)
			total = float(row.sales_total or 0)
			sales_tickets[key] = {"count": count, "total": total, "average": total / count if count else None}

	return {
		"sales_today_total": float(sales_today_total or 0),
		"sales_visible": sales_visible,
		"sales_tickets": sales_tickets,
		"service_orders": service_orders,
	}


@frappe.whitelist()
def get_director_financial_summary() -> dict[str, Any]:
	"""Today\'s operational gross result, intentionally separate from net profit.

	Fixed expenses and taxes do not yet have Tecponto postings, so this endpoint
	never labels the result as net profit. It only uses submitted sales, the
	actual item/part cost tied to those sales, and submitted commission entries.
	"""
	_require_director_financial_role()
	date = today()
	revenue = frappe.db.sql(
		"""
		select coalesce(sum(case when is_return = 1 then -abs(grand_total) else grand_total end), 0)
		from `tabSales Invoice`
		where docstatus = 1 and posting_date = %(posting_date)s
		""",
		{"posting_date": date},
	)[0][0]
	retail_cost = frappe.db.sql(
		"""
		select coalesce(sum(
			case when invoice.is_return = 1 then -1 else 1 end
			* coalesce(item.incoming_rate, 0) * abs(coalesce(item.stock_qty, item.qty, 0))
		), 0)
		from `tabSales Invoice Item` item
		inner join `tabSales Invoice` invoice on invoice.name = item.parent
		where invoice.docstatus = 1 and invoice.is_pos = 1 and invoice.posting_date = %(posting_date)s
		""",
		{"posting_date": date},
	)[0][0]
	service_part_cost = frappe.db.sql(
		"""
		select coalesce(sum(coalesce(part.valuation_rate, 0) * coalesce(part.qty, 0)), 0)
		from `tabService Order` service_order
		inner join `tabSales Invoice` invoice on invoice.name = service_order.sales_invoice
		inner join `tabService Order Part` part on part.parent = service_order.name
		where invoice.docstatus = 1
			and invoice.is_return = 0
			and invoice.posting_date = %(posting_date)s
			and part.outcome = 'Usada no reparo'
		""",
		{"posting_date": date},
	)[0][0]
	commissions_enabled = technician_commissions_enabled()
	commissions = 0
	if commissions_enabled and frappe.db.table_exists("Additional Salary"):
		commissions = frappe.db.sql(
			"""
			select coalesce(sum(amount), 0)
			from `tabAdditional Salary`
			where docstatus = 1
				and salary_component = 'Comissão'
				and type = 'Earning'
				and payroll_date = %(payroll_date)s
			""",
			{"payroll_date": date},
		)[0][0]
	cost = flt(retail_cost) + flt(service_part_cost)
	gross_profit = flt(revenue) - cost
	return {
		"period": {"key": "today", "label": _("Hoje"), "date": str(date)},
		"revenue": float(flt(revenue)),
		"operational_cost": float(cost),
		"retail_cost": float(flt(retail_cost)),
		"service_part_cost": float(flt(service_part_cost)),
		"gross_operating_profit": float(gross_profit),
		"gross_margin_pct": float((gross_profit / flt(revenue) * 100) if flt(revenue) else 0),
		"team_earnings_accrued": float(flt(commissions)),
		"technician_commissions_enabled": commissions_enabled,
		"net_profit_available": False,
	}


@frappe.whitelist()
def get_director_strategic_report(period: str = "month") -> dict[str, Any]:
	"""Director-only commercial, service and cost projections for one period."""
	_require_director_financial_role()
	period = (period or "month").strip()
	if period == "7d":
		from_date = add_days(today(), -6)
		label = _("Ultimos 7 dias")
	elif period == "month":
		from_date = getdate(today()).replace(day=1)
		label = _("Este mes")
	else:
		frappe.throw(_("Periodo estrategico invalido."), frappe.ValidationError)
	values = {"from_date": from_date, "to_date": today()}

	category_rows = frappe.db.sql(
		"""
		select
			coalesce(nullif(item.item_group, ''), 'Sem categoria') as category,
			sum(case when invoice.is_return = 1 then -abs(item.base_net_amount) else item.base_net_amount end) as revenue
		from `tabSales Invoice Item` item
		inner join `tabSales Invoice` invoice on invoice.name = item.parent
		where invoice.docstatus = 1 and invoice.posting_date between %(from_date)s and %(to_date)s
		group by item.item_group
		order by revenue desc
		limit 8
		""",
		values,
		as_dict=True,
	)
	technician_rows = frappe.db.sql(
		"""
		select
			service_row.technician as employee,
			coalesce(employee.employee_name, service_row.technician, 'Nao atribuido') as technician,
			count(distinct service_order.name) as service_orders,
			coalesce(sum(service_row.qty * service_row.rate), 0) as labor_revenue
		from `tabService Order Service` service_row
		inner join `tabService Order` service_order on service_order.name = service_row.parent
		inner join `tabSales Invoice` invoice on invoice.name = service_order.sales_invoice
		left join `tabEmployee` employee on employee.name = service_row.technician
		where invoice.docstatus = 1
			and invoice.is_return = 0
			and invoice.posting_date between %(from_date)s and %(to_date)s
		group by service_row.technician, employee.employee_name
		order by labor_revenue desc
		limit 8
		""",
		values,
		as_dict=True,
	)
	commissions_enabled = technician_commissions_enabled()
	commission_rows = (
		frappe.db.sql(
			"""
			select additional_salary.employee, coalesce(sum(additional_salary.amount), 0) as amount
			from `tabAdditional Salary` additional_salary
			where additional_salary.docstatus = 1
				and additional_salary.salary_component = 'Comissão'
				and additional_salary.type = 'Earning'
				and additional_salary.payroll_date between %(from_date)s and %(to_date)s
			group by additional_salary.employee
			""",
			values,
			as_dict=True,
		)
		if commissions_enabled and frappe.db.table_exists("Additional Salary")
		else []
	)
	commissions = {row.employee: flt(row.amount) for row in commission_rows}
	technicians = [
		{
			"technician": row.technician,
			"service_orders": int(row.service_orders or 0),
			"labor_revenue": float(flt(row.labor_revenue)),
			"team_earnings": float(commissions.get(row.get("employee"), 0)),
		}
		for row in technician_rows
	]
	item_costs = frappe.db.sql(
		"""
		select
			item.item_code,
			coalesce(max(item.item_name), item.item_code) as item_name,
			coalesce(sum(
				case when invoice.is_return = 1 then -1 else 1 end
				* coalesce(item.incoming_rate, 0) * abs(coalesce(item.stock_qty, item.qty, 0))
			), 0) as cost
		from `tabSales Invoice Item` item
		inner join `tabSales Invoice` invoice on invoice.name = item.parent
		where invoice.docstatus = 1 and invoice.posting_date between %(from_date)s and %(to_date)s
		group by item.item_code
		having cost > 0
		order by cost desc
		limit 8
		""",
		values,
		as_dict=True,
	)
	service_order_costs = frappe.db.sql(
		"""
		select
			service_order.name as service_order,
			coalesce(sum(part.valuation_rate * part.qty), 0) as cost
		from `tabService Order` service_order
		inner join `tabSales Invoice` invoice on invoice.name = service_order.sales_invoice
		inner join `tabService Order Part` part on part.parent = service_order.name
		where invoice.docstatus = 1
			and invoice.is_return = 0
			and invoice.posting_date between %(from_date)s and %(to_date)s
			and part.outcome = 'Usada no reparo'
		group by service_order.name
		order by cost desc
		limit 8
		""",
		values,
		as_dict=True,
	)
	trend_rows = frappe.db.sql(
		"""
		select
			invoice.posting_date as date,
			coalesce(sum(case when invoice.is_return = 1 then -abs(invoice.grand_total) else invoice.grand_total end), 0) as revenue
		from `tabSales Invoice` invoice
		where invoice.docstatus = 1 and invoice.posting_date between %(from_date)s and %(to_date)s
		group by invoice.posting_date
		order by invoice.posting_date asc
		""",
		values,
		as_dict=True,
	)
	return {
		"period": {"key": period, "label": label, "from_date": str(from_date), "to_date": str(today())},
		"technician_commissions_enabled": commissions_enabled,
		"categories": [{"category": row.category, "revenue": float(flt(row.revenue))} for row in category_rows],
		"technicians": technicians,
		"item_costs": [{"item_code": row.item_code, "item_name": row.item_name, "cost": float(flt(row.cost))} for row in item_costs],
		"service_order_costs": [{"service_order": row.service_order, "cost": float(flt(row.cost))} for row in service_order_costs],
		"trend": [{"date": str(row.date), "revenue": float(flt(row.revenue))} for row in trend_rows],
	}


@frappe.whitelist()
def get_director_risk_agenda() -> dict[str, Any]:
	"""Director-only agenda combining operational actions with derived executive risks."""
	_require_director_financial_role()
	base = pending.list_daily_actions(panel="diretor")
	items = [*base["items"], *_director_risk_actions()]
	items = _sort_director_risk_actions(items)
	return {"items": items, "count": len(items), "risk_count": len(items) - len(base["items"])}


def _director_risk_actions() -> list[dict[str, Any]]:
	"""Read-only risk projection. All alerts disappear when their source state is resolved."""
	items: list[dict[str, Any]] = []
	repair_warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
	commercial_warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	reorder_level = flt(frappe.db.get_single_value("Tecponto Settings", "reorder_level") or 0)
	warehouses = [warehouse for warehouse in (repair_warehouse, commercial_warehouse) if warehouse]
	if warehouses:
		for row in frappe.db.sql(
			"""
			select bin.item_code, coalesce(item.item_name, bin.item_code) as item_name,
				bin.warehouse, coalesce(bin.actual_qty, 0) as actual_qty
			from `tabBin` bin
			inner join `tabItem` item on item.name = bin.item_code
			where item.disabled = 0
				and item.is_stock_item = 1
				and bin.warehouse in %(warehouses)s
				and coalesce(bin.actual_qty, 0) <= %(reorder_level)s
			order by coalesce(bin.actual_qty, 0) asc, item.item_name asc
			limit 40
			""",
			{"warehouses": warehouses, "reorder_level": reorder_level},
			as_dict=True,
		):
			warehouse_label = "Reparo" if row.warehouse == repair_warehouse else "Comercial"
			items.append(
				_director_risk_action(
					key=f"critical-stock:{row.warehouse}:{row.item_code}",
					title="Estoque critico",
					description=f"{row.item_name} - {warehouse_label}: {flt(row.actual_qty)} disponivel(is)",
					urgency="overdue" if flt(row.actual_qty) <= 0 else "due_today",
					urgency_sort_at=f"{flt(row.actual_qty):012.3f}",
					link="/tecponto?view=parts-stock" if warehouse_label == "Reparo" else "/tecponto?view=products",
					reference_doctype="Item",
					reference_name=row.item_code,
					group_key=f"critical-stock:{warehouse_label}",
					group_label=f"Estoque critico - {warehouse_label}",
				),
			)

	for row in frappe.get_all(
		"Tecponto Part Request",
		filters={"status": "Pedida", "expected_arrival": ["<", today()]},
		fields=["name", "service_order", "item", "free_description", "expected_arrival"],
		order_by="expected_arrival asc",
		limit_page_length=50,
	):
		part_label = row.item or row.free_description or "Peca sem descricao"
		items.append(
			_director_risk_action(
				key=f"late-part-request:{row.name}",
				title="Peca pedida atrasada",
				description=f"{part_label} - OS {row.service_order or 'nao vinculada'} - prevista para {row.expected_arrival}",
				urgency="overdue",
				urgency_sort_at=str(row.expected_arrival),
				link="/tecponto?view=part-requests",
				reference_doctype="Tecponto Part Request",
				reference_name=row.name,
				group_key="late-part-request",
				group_label="Pecas pedidas atrasadas",
			),
		)

	now = now_datetime()
	for row in frappe.get_all(
		"Tecponto Request",
		filters={"status": "Pendente", "expires_on": ["between", [now, add_to_date(now, hours=12)]]},
		fields=["name", "request_type", "expires_on"],
		order_by="expires_on asc",
		limit_page_length=50,
	):
		items.append(
			_director_risk_action(
				key=f"request-expiring:{row.name}",
				title="Aprovacao perto de expirar",
				description=f"{row.request_type or 'Solicitacao'} expira em {row.expires_on}",
				urgency="due_today",
				urgency_sort_at=str(row.expires_on),
				link="/tecponto?view=approval-requests",
				reference_doctype="Tecponto Request",
				reference_name=row.name,
				group_key="request-expiring",
				group_label="Aprovacoes perto de expirar",
			),
		)

	ready_before = add_days(now, -7)
	for row in frappe.get_all(
		"Service Order",
		filters={"workflow_state": STATE_PRONTO_RETIRADA, "stage_entered_at": ["<", ready_before]},
		fields=["name", "customer", "stage_entered_at"],
		order_by="stage_entered_at asc",
		limit_page_length=50,
	):
		items.append(
			_director_risk_action(
				key=f"pickup-overdue:{row.name}",
				title="OS pronta sem retirada",
				description=f"{row.name} - {row.customer or 'Cliente nao informado'} - pronta desde {row.stage_entered_at}",
				urgency="overdue",
				urgency_sort_at=str(row.stage_entered_at),
				link=f"/tecponto?view=service-order-detail&id={quote(row.name)}",
				reference_doctype="Service Order",
				reference_name=row.name,
				group_key="pickup-overdue",
				group_label="OS prontas sem retirada ha mais de 7 dias",
			),
		)
	return items


def _director_risk_action(**values: Any) -> dict[str, Any]:
	return {"kind": "derived", "tone": "red", **values}


def _sort_director_risk_actions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
	priority = {"overdue": 0, "high": 0, "due_today": 1, "normal": 1, "scheduled": 2, "low": 2}
	return sorted(
		items,
		key=lambda item: (
			priority.get(item.get("urgency"), 1),
			item.get("urgency_sort_at") or "9999-12-31 23:59:59",
			item.get("title") or "",
		),
	)


@frappe.whitelist()
def get_technician_workload() -> dict[str, Any]:
	"""Safe store-wide workload projection for management, without financial data."""
	_require_store_operation_manager()
	terminal_states = ("Entregue", "Cancelado", "Reprovado", "Orçamento expirado", "Sem conserto")
	rows = frappe.get_all(
		"Service Order",
		filters={"workflow_state": ["not in", terminal_states], "technician": ["is", "set"]},
		fields=["name", "technician", "workflow_state"],
		limit_page_length=0,
	)
	overdue_names = set(stage_clock.list_overdue_service_order_names())
	by_technician: dict[str, dict[str, Any]] = {}
	for row in rows:
		technician = row.technician
		entry = by_technician.setdefault(
			technician,
			{"technician": technician, "active_orders": 0, "in_diagnosis": 0, "waiting_part": 0, "overdue": 0},
		)
		entry["active_orders"] += 1
		if row.workflow_state == "Em diagnóstico":
			entry["in_diagnosis"] += 1
		if row.workflow_state == "Aguardando peça":
			entry["waiting_part"] += 1
		if row.name in overdue_names:
			entry["overdue"] += 1

	full_names = (
		{
			row.name: row.full_name
			for row in frappe.get_all("User", filters={"name": ["in", list(by_technician)]}, fields=["name", "full_name"])
		}
		if by_technician
		else {}
	)
	items = [
		{**entry, "technician_name": full_names.get(entry["technician"]) or entry["technician"]}
		for entry in by_technician.values()
	]
	items.sort(key=lambda item: (-item["overdue"], -item["active_orders"], item["technician_name"]))
	return {"items": items, "count": len(items)}


@frappe.whitelist()
def list_catalog_services(
	query: str = "",
	device_type: str = "",
	category: str = "",
	include_inactive: bool = False,
) -> dict[str, Any]:
	"""Read-only labor catalog. No stock cost is joined or exposed here."""
	_require_frontend_role()
	return service_catalog.list_services(
		query=(query or "").strip(),
		device_type=(device_type or "").strip(),
		category=(category or "").strip(),
		include_inactive=bool(cint(include_inactive)),
	)


@frappe.whitelist()
def list_catalog_references(include_inactive: bool = True) -> dict[str, Any]:
	_require_frontend_role()
	return service_catalog.list_references(include_inactive=bool(cint(include_inactive)))


@frappe.whitelist()
def save_catalog_service(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_service_catalog_editor()
	return {"item": service_catalog.save_service(_parse_payload(payload))}


@frappe.whitelist()
def save_catalog_reference(kind: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_service_catalog_editor()
	return {"item": service_catalog.save_reference((kind or "").strip(), _parse_payload(payload))}


@frappe.whitelist()
def search_customers(query: str = "", limit: int = 12) -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit or 12), 50))
	query = (query or "").strip()
	restricted_technician = is_restricted_technician()
	allowed_customers = _technician_customer_names() if restricted_technician else None
	if restricted_technician and not allowed_customers:
		return {"items": [], "count": 0, "fields": list(SAFE_TECHNICIAN_CUSTOMER_FIELDS)}
	fields = SAFE_TECHNICIAN_CUSTOMER_FIELDS if restricted_technician else SAFE_CUSTOMER_FIELDS
	search_fields = (
		("name", "customer_name", "mobile_no", "custom_whatsapp")
		if restricted_technician
		else ("name", "customer_name", "mobile_no", "custom_whatsapp", "custom_cpf", "custom_rg", "email_id")
	)
	or_filters = _like_filters(query, search_fields)
	items = frappe.get_all(
		"Customer",
		fields=list(fields),
		filters={"name": ["in", allowed_customers]} if allowed_customers is not None else None,
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=limit,
	)
	return {
		"items": [_serialize_customer(item, include_fiscal=not restricted_technician) for item in items],
		"count": len(items),
		"fields": list(fields),
	}


@frappe.whitelist()
def create_customer(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Create an individual customer from the counter without opening core Customer."""
	_require_checkin_role()
	data = _parse_payload(payload)
	validate_customer_contact_document(data)

	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": data["customer_name"].strip(),
			"customer_type": "Individual",
			"mobile_no": (data.get("mobile_no") or data.get("custom_whatsapp") or "").strip(),
			"custom_whatsapp": (data.get("custom_whatsapp") or data.get("mobile_no") or "").strip(),
			"custom_cpf": (data.get("custom_cpf") or "").strip(),
			"custom_rg": (data.get("custom_rg") or "").strip(),
			CUSTOMER_NO_CPF_FIELD: 1 if data.get(CUSTOMER_NO_CPF_FIELD) else 0,
			"email_id": (data.get("email_id") or "").strip(),
		}
	)
	customer.insert(ignore_permissions=True)
	item = frappe.db.get_value("Customer", customer.name, list(SAFE_CUSTOMER_FIELDS), as_dict=True)
	return {"item": _serialize_customer(item)}


@frappe.whitelist()
def list_customer_devices(query: str = "", limit: int = 12, customer: str = "") -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit or 12), 50))
	query = (query or "").strip()
	customer = (customer or "").strip()
	allowed_customers = _technician_customer_names() if is_restricted_technician() else None
	if allowed_customers is not None and customer and customer not in allowed_customers:
		return {"items": [], "count": 0, "fields": list(SAFE_DEVICE_FIELDS)}
	if allowed_customers is not None and not allowed_customers:
		return {"items": [], "count": 0, "fields": list(SAFE_DEVICE_FIELDS)}
	or_filters = _like_filters(
		query,
		("name", "customer", "brand", "model", "imei_serial"),
	)
	filters = (
		{"customer": customer}
		if customer
		else {"customer": ["in", allowed_customers]}
		if allowed_customers is not None
		else None
	)
	items = frappe.get_all(
		"Customer Device",
		fields=list(SAFE_DEVICE_FIELDS),
		filters=filters,
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=limit,
	)
	return {
		"items": [_serialize_customer_device(item) for item in items],
		"count": len(items),
		"fields": list(SAFE_DEVICE_FIELDS),
	}


@frappe.whitelist()
def create_customer_device(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_checkin_role()
	data = _parse_payload(payload)
	customer = (data.get("customer") or "").strip()
	if not customer:
		frappe.throw(_("Selecione o cliente do aparelho."), frappe.ValidationError)
	assert_existing_customer_is_complete(customer)
	_validate_device_payload(data)

	device = frappe.get_doc(
		{
			"doctype": "Customer Device",
			"customer": customer,
			"brand": data["brand"].strip(),
			"model": data["model"].strip(),
			"color": (data.get("color") or "").strip(),
			"imei_serial": data["imei_serial"].strip(),
			"capacity": (data.get("capacity") or "").strip(),
			"general_state": (data.get("general_state") or "").strip(),
			"registration_date": today(),
		}
	)
	device.insert(ignore_permissions=True)

	photo = data.get("photo") or {}
	if _is_image_data_url(photo.get("data_url")):
		photo_url = _save_customer_device_photo(device.name, photo)
		frappe.db.set_value("Customer Device", device.name, "photos", photo_url, update_modified=False)

	item = frappe.db.get_value("Customer Device", device.name, list(SAFE_DEVICE_FIELDS), as_dict=True)
	return {"item": _serialize_customer_device(item)}


def _require_registry_editor(kind: str) -> None:
	"""Keep registry writes on the server, with a distinct boundary per registry."""
	if kind not in REGISTRY_KINDS:
		frappe.throw(_("Cadastro inválido."), frappe.ValidationError)
	if kind in {"customer", "device", "repair_part"}:
		_require_frontend_role()
		roles = set(frappe.get_roles(frappe.session.user))
		if frappe.session.user == "Administrator" or roles & {"Tecponto Atendente", "Tecponto Gestor", "Tecponto Diretor", "System Manager"}:
			return
		frappe.throw(_("Seu papel não permite editar este cadastro operacional."), frappe.PermissionError)
		return
	_require_product_category_editor()


def _require_registry_reader(kind: str) -> None:
	"""Technicians retain their scoped operational reads, never global registry editing."""
	if kind not in REGISTRY_KINDS:
		frappe.throw(_("Cadastro inválido."), frappe.ValidationError)
	if is_restricted_technician():
		frappe.throw(_("O perfil técnico não abre cadastros globais."), frappe.PermissionError)
	_require_registry_editor(kind)


def _assert_registry_payload_fields(data: dict[str, Any], allowed_fields: set[str]) -> None:
	unknown = sorted(set(data) - allowed_fields)
	if unknown:
		frappe.throw(
			_("Campo não permitido nesta edição: {0}.").format(", ".join(unknown)),
			frappe.PermissionError,
		)


def _customer_address(customer_name: str) -> dict[str, str]:
	address_name = frappe.db.get_value(
		"Dynamic Link",
		{"link_doctype": "Customer", "link_name": customer_name, "parenttype": "Address"},
		"parent",
	)
	if not address_name or not frappe.db.exists("Address", address_name):
		return {}
	address = frappe.db.get_value(
		"Address",
		address_name,
		["address_line1", "address_line2", "city", "state", "pincode"],
		as_dict=True,
	)
	return {field: str(address.get(field) or "") for field in ("address_line1", "address_line2", "city", "state", "pincode")}


def _save_customer_address(customer_name: str, value: Any) -> None:
	if not isinstance(value, dict):
		frappe.throw(_("Endereço inválido."), frappe.ValidationError)
	allowed = {"address_line1", "address_line2", "city", "state", "pincode"}
	_assert_registry_payload_fields(value, allowed)
	clean = {field: str(value.get(field) or "").strip() for field in allowed}
	address_name = frappe.db.get_value(
		"Dynamic Link",
		{"link_doctype": "Customer", "link_name": customer_name, "parenttype": "Address"},
		"parent",
	)
	if address_name and frappe.db.exists("Address", address_name):
		address = frappe.get_doc("Address", address_name)
		address.update(clean)
		address.save(ignore_permissions=True)
		return
	if not any(clean.values()):
		return
	address = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": frappe.db.get_value("Customer", customer_name, "customer_name") or customer_name,
			"address_type": "Billing",
			**clean,
			"links": [{"link_doctype": "Customer", "link_name": customer_name}],
		}
	)
	address.insert(ignore_permissions=True)


def _registry_item_scope(kind: str) -> set[str]:
	return set(_descendant_item_groups("Peças de Reparo")) if kind == "repair_part" else set(get_retail_item_groups())


def _registry_item_projection(item: Any, kind: str, warehouse: str | None = None) -> dict[str, Any]:
	result = {
		"item_code": item.get("name") or item.get("item_code"),
		"item_name": item.get("item_name"),
		"item_group": item.get("item_group"),
		"model": item.get("description") or "",
		"compatible_models": item.get("custom_compatible_models") or "",
		"part_type": item.get("custom_part_type") or "",
		"selling_rate": flt(item.get("standard_rate"), 2),
		"barcode": next((row.barcode for row in item.get("barcodes") or [] if row.barcode), None),
		"kind": kind,
	}
	if _current_user_is_director():
		result["valuation_rate"] = flt(
			frappe.db.get_value("Bin", {"item_code": result["item_code"], "warehouse": warehouse}, "valuation_rate")
			if warehouse
			else item.get("valuation_rate"),
			2,
		)
	return result


@frappe.whitelist()
def get_registry_record(kind: str, name: str) -> dict[str, Any]:
	"""Return one role-scoped registry record; Item cost exists only for Diretor."""
	kind = (kind or "").strip()
	name = (name or "").strip()
	_require_registry_reader(kind)
	if not name:
		frappe.throw(_("Cadastro não informado."), frappe.ValidationError)
	if kind == "customer":
		row = frappe.db.get_value("Customer", name, list(SAFE_CUSTOMER_FIELDS), as_dict=True)
		if not row:
			frappe.throw(_("Cliente não encontrado."), frappe.DoesNotExistError)
		return {"item": {**_serialize_customer(row), "address": _customer_address(name)}, "can_edit": True}
	if kind == "device":
		row = frappe.db.get_value("Customer Device", name, list(SAFE_DEVICE_FIELDS) + ["general_state"], as_dict=True)
		if not row:
			frappe.throw(_("Aparelho não encontrado."), frappe.DoesNotExistError)
		return {"item": {**_serialize_customer_device(row), "general_state": row.get("general_state") or ""}, "can_edit": True}

	item = frappe.get_doc("Item", name)
	if item.item_group not in _registry_item_scope(kind):
		frappe.throw(_("Item não pertence a este cadastro."), frappe.PermissionError)
	warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse" if kind == "repair_part" else "commercial_warehouse")
	return {"item": _registry_item_projection(item, kind, warehouse), "can_edit": True}


@frappe.whitelist()
def save_registry_record(kind: str, name: str = "", payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Create/update only registry fields explicitly allowed for the caller's workflow."""
	kind = (kind or "").strip()
	name = (name or "").strip()
	_require_registry_editor(kind)
	data = _parse_payload(payload)
	if kind == "customer":
		if not name or not frappe.db.exists("Customer", name):
			frappe.throw(_("Cliente não encontrado."), frappe.DoesNotExistError)
		_assert_registry_payload_fields(data, CUSTOMER_REGISTRY_FIELDS)
		customer = frappe.get_doc("Customer", name)
		for field in CUSTOMER_REGISTRY_FIELDS - {"address"}:
			if field in data:
				customer.set(field, data[field])
		customer.mobile_no = (customer.mobile_no or customer.custom_whatsapp or "").strip()
		customer.custom_whatsapp = (customer.custom_whatsapp or customer.mobile_no or "").strip()
		validate_customer_contact_document(customer)
		customer.save(ignore_permissions=True)
		if "address" in data:
			_save_customer_address(customer.name, data["address"])
		row = frappe.db.get_value("Customer", customer.name, list(SAFE_CUSTOMER_FIELDS), as_dict=True)
		return {"item": {**_serialize_customer(row), "address": _customer_address(customer.name)}}
	if kind == "device":
		if not name or not frappe.db.exists("Customer Device", name):
			frappe.throw(_("Aparelho não encontrado."), frappe.DoesNotExistError)
		_assert_registry_payload_fields(data, DEVICE_REGISTRY_FIELDS)
		device = frappe.get_doc("Customer Device", name)
		for field, value in data.items():
			device.set(field, value)
		_validate_device_payload(device)
		device.save(ignore_permissions=True)
		row = frappe.db.get_value("Customer Device", device.name, list(SAFE_DEVICE_FIELDS) + ["general_state"], as_dict=True)
		return {"item": {**_serialize_customer_device(row), "general_state": row.get("general_state") or ""}}

	_assert_registry_payload_fields(data, ITEM_REGISTRY_FIELDS | ({"item_code", "item_group"} if kind == "repair_part" and not name else set()))
	allowed_groups = _registry_item_scope(kind)
	if name:
		item = frappe.get_doc("Item", name)
		if item.item_group not in allowed_groups:
			frappe.throw(_("Item não pertence a este cadastro."), frappe.PermissionError)
	else:
		if kind != "repair_part":
			frappe.throw(_("Use o cadastro por código de barras para criar produtos comerciais."), frappe.ValidationError)
		item_code = str(data.get("item_code") or "").strip()
		item_group = str(data.get("item_group") or "Peças de Reparo").strip()
		if not item_code or not data.get("item_name"):
			frappe.throw(_("Código e nome da peça são obrigatórios."), frappe.ValidationError)
		if item_group not in allowed_groups:
			frappe.throw(_("Selecione um grupo de Peças de Reparo."), frappe.ValidationError)
		if frappe.db.exists("Item", item_code):
			frappe.throw(_("Já existe uma peça com este código."), frappe.ValidationError)
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": data["item_name"].strip(),
				"item_group": item_group,
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"is_purchase_item": 1,
			}
		)
	for field in ITEM_REGISTRY_FIELDS:
		if field in data:
			item.set(field, data[field])
	item.save(ignore_permissions=True)
	warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse" if kind == "repair_part" else "commercial_warehouse")
	return {"item": _registry_item_projection(item, kind, warehouse)}


@frappe.whitelist()
def list_trade_evaluations(query: str = "", limit: int = 12) -> dict[str, Any]:
	_require_tradein_role()
	limit = max(1, min(int(limit or 12), 50))
	query = (query or "").strip()
	or_filters = _like_filters(
		query,
		("name", "customer", "evaluated_device_desc", "model", "imei"),
	)
	items = frappe.get_all(
		"Device Trade Evaluation",
		fields=list(SAFE_TRADE_EVALUATION_FIELDS),
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=limit,
	)
	return {
		"items": [_serialize_trade_evaluation(item) for item in items],
		"count": len(items),
		"fields": list(SAFE_TRADE_EVALUATION_FIELDS),
	}


@frappe.whitelist()
def create_trade_evaluation(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Create the evaluation document; table validation remains in the trade-in engine."""
	_require_tradein_role()
	data = _parse_payload(payload)
	customer = (data.get("customer") or "").strip()
	if not customer or not frappe.db.exists("Customer", customer):
		frappe.throw(_("Selecione um cliente válido para a avaliação."), frappe.ValidationError)

	device_type = (data.get("device_type") or "").strip()
	if device_type not in {"iPhone", "Android"}:
		frappe.throw(_("Selecione o tipo do aparelho."), frappe.ValidationError)

	model = (data.get("model") or "").strip()
	imei = (data.get("imei") or "").strip()
	physical_state = (data.get("physical_state") or "").strip()
	destination = (data.get("destination") or "").strip()
	if not model or not imei or physical_state not in {"A", "B", "C", "Sucata"}:
		frappe.throw(_("Informe modelo, IMEI/serial e estado físico."), frappe.ValidationError)
	if destination not in {"Venda", "Peças", "Descarte"}:
		frappe.throw(_("Selecione o destino do aparelho avaliado."), frappe.ValidationError)

	suggested_value = flt(data.get("suggested_value"), 2)
	if suggested_value <= 0:
		frappe.throw(_("Informe o valor avaliado maior que zero."), frappe.ValidationError)

	doc = frappe.get_doc(
		{
			"doctype": "Device Trade Evaluation",
			"customer": customer,
			"device_type": device_type,
			"evaluated_device_desc": (data.get("evaluated_device_desc") or model).strip(),
			"model": model,
			"imei": imei,
			"capacity": (data.get("capacity") or "").strip(),
			"physical_state": physical_state,
			"icloud_google_lock": cint(bool(data.get("icloud_google_lock"))),
			"has_invoice": cint(bool(data.get("has_invoice"))),
			"defects": (data.get("defects") or "").strip(),
			"table_min": flt(data.get("table_min"), 2),
			"table_max": flt(data.get("table_max"), 2),
			"suggested_value": suggested_value,
			"destination": destination,
			"workflow_state": STATE_AGUARDANDO_APROVACAO,
		}
	)
	doc.insert(ignore_permissions=True)
	item = frappe.db.get_value("Device Trade Evaluation", doc.name, list(SAFE_TRADE_EVALUATION_FIELDS), as_dict=True)
	return {"item": _serialize_trade_evaluation(item)}


@frappe.whitelist()
def set_tradein_approved_value(name: str, approved_value: float) -> dict[str, Any]:
	"""Attempt the normal evaluation save so the trade table guard remains authoritative."""
	_require_tradein_role()
	doc = frappe.get_doc("Device Trade Evaluation", (name or "").strip())
	doc.approved_value = flt(approved_value, 2)
	# This endpoint exposes only the table-governed value. Validation still runs under
	# the caller, while an approved request later saves normally under the Gestor.
	doc.save(ignore_permissions=True)
	item = frappe.db.get_value("Device Trade Evaluation", doc.name, list(SAFE_TRADE_EVALUATION_FIELDS), as_dict=True)
	return {"item": _serialize_trade_evaluation(item)}


@frappe.whitelist()
def complete_trade_buyback(name: str) -> dict[str, Any]:
	"""Conclude a pure buyback through the existing Device Trade Evaluation hook."""
	_require_tradein_role()
	doc = frappe.get_doc("Device Trade Evaluation", (name or "").strip())
	if not doc.created_item:
		frappe.db.savepoint("frontend_trade_buyback")
		try:
			with _run_tradein_stock_mutation():
				doc.workflow_state = "Comprado"
				doc.save(ignore_permissions=True)
		except Exception:
			frappe.db.rollback(save_point="frontend_trade_buyback")
			raise

	item = frappe.db.get_value("Device Trade Evaluation", doc.name, list(SAFE_TRADE_EVALUATION_FIELDS), as_dict=True)
	return {"item": _serialize_trade_evaluation(item), "created_item": doc.created_item or None}


@frappe.whitelist()
def list_tradein_output_devices(query: str = "", limit: int = 20) -> dict[str, Any]:
	"""Expose only serials currently held in Comercial; costs never leave this endpoint."""
	_require_tradein_role()
	warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	if not warehouse:
		frappe.throw(_("Depósito Comercial não configurado."), frappe.ValidationError)
	limit = max(1, min(int(limit or 20), 50))
	query = (query or "").strip()
	filters: dict[str, Any] = {"warehouse": warehouse}
	or_filters = _like_filters(query, ("name", "serial_no", "item_code"))
	serials = frappe.get_all(
		"Serial No",
		fields=["name", "serial_no", "item_code"],
		filters=filters,
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=limit,
	)
	items = []
	for serial in serials:
		items.append(
			{
				"name": serial.name,
				"serial_no": serial.serial_no,
				"item_code": serial.item_code,
				"item_name": frappe.db.get_value("Item", serial.item_code, "item_name") or serial.item_code,
			}
		)
	return {"items": items, "count": len(items)}


@frappe.whitelist()
def confirm_tradein_operation(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	"""Create and confirm the existing atomic Trade-In Operation without duplicating its rules."""
	_require_tradein_role()
	data = _parse_payload(payload)
	evaluation_name = (data.get("evaluation") or "").strip()
	device_out = (data.get("device_out") or "").strip()
	if not evaluation_name or not device_out:
		frappe.throw(_("Selecione a avaliação e o aparelho que sairá da loja."), frappe.ValidationError)

	evaluation = frappe.get_doc("Device Trade Evaluation", evaluation_name)
	if not evaluation.get("approved_value"):
		frappe.throw(_("Registre o valor aprovado antes de confirmar a troca."), frappe.ValidationError)

	existing_name = frappe.db.get_value(
		"Trade-In Operation",
		{"evaluation": evaluation.name, "device_out": device_out, "atomic_status": ["in", ["Confirmada", "Concluída"]]},
		"name",
	)
	if existing_name:
		existing = frappe.get_doc("Trade-In Operation", existing_name)
		return {"operation": _serialize_tradein_operation(existing), "evaluation": _serialize_trade_evaluation(evaluation)}

	difference = flt(data.get("difference"), 2)
	if difference < 0:
		frappe.throw(_("A diferença da troca não pode ser negativa."), frappe.ValidationError)
	# The stock hook needs a narrow elevation to create native serial/batch records,
	# but the caller's margin entitlement must be checked before that elevation.
	from tecponto_app.tecponto.tradein.operation import _get_available_output_serial, _validar_margem_troca

	preflight = frappe.get_doc(
		{
			"doctype": "Trade-In Operation",
			"evaluation": evaluation.name,
			"device_out": device_out,
			"difference": difference,
		}
	)
	_get_available_output_serial(preflight)
	_validar_margem_troca(preflight, evaluation)

	frappe.db.savepoint("frontend_tradein_operation")
	try:
		with _run_tradein_stock_mutation():
			operation = frappe.get_doc(
				{
					"doctype": "Trade-In Operation",
					"customer": evaluation.customer,
					"evaluation": evaluation.name,
					"device_out": device_out,
					"difference": difference,
					"payment_mode": (data.get("payment_mode") or "").strip(),
					"notes": (data.get("notes") or "").strip(),
					"atomic_status": "Rascunho",
				}
			)
			operation.insert(ignore_permissions=True)
			operation.atomic_status = "Pendente"
			operation.save(ignore_permissions=True)
	except Exception:
		frappe.db.rollback(save_point="frontend_tradein_operation")
		raise

	updated_evaluation = frappe.get_doc("Device Trade Evaluation", evaluation.name)
	return {
		"operation": _serialize_tradein_operation(operation),
		"evaluation": _serialize_trade_evaluation(updated_evaluation),
	}


@frappe.whitelist()
def create_stock_transfer(item_code: str, qty: float, source_warehouse: str, target_warehouse: str) -> dict[str, Any]:
	"""Prepare a constrained transfer draft; submission remains role-gated."""
	_require_frontend_role()
	item_code = (item_code or "").strip()
	source_warehouse = (source_warehouse or "").strip()
	target_warehouse = (target_warehouse or "").strip()
	qty = flt(qty, 3)
	repair, commercial = _operational_warehouse_pair()
	if not target_warehouse:
		target_warehouse = commercial if source_warehouse == repair else repair
	if {source_warehouse, target_warehouse} != {repair, commercial}:
		frappe.throw(_("A transferência deve ocorrer somente entre Reparo e Comercial."), frappe.PermissionError)
	if source_warehouse == target_warehouse or qty <= 0:
		frappe.throw(_("Informe depósitos diferentes e uma quantidade maior que zero."), frappe.ValidationError)
	if not frappe.db.exists("Item", item_code):
		frappe.throw(_("Item não encontrado."), frappe.DoesNotExistError)
	available = flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": source_warehouse}, "actual_qty") or 0)
	if available < qty:
		frappe.throw(_("Saldo insuficiente no depósito de origem."), frappe.ValidationError)

	doc = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Transfer",
			"purpose": "Material Transfer",
			"from_warehouse": source_warehouse,
			"to_warehouse": target_warehouse,
			"items": [
				{
					"item_code": item_code,
					"qty": qty,
					"s_warehouse": source_warehouse,
					"t_warehouse": target_warehouse,
				}
			],
		}
	)
	# Only the fixed pair, item, and quantity above are persisted. Submission
	# continues through the regular Stock Entry validator under the real actor.
	doc.insert(ignore_permissions=True)
	return {"item": _serialize_stock_transfer(doc)}


@frappe.whitelist()
def submit_stock_transfer(name: str) -> dict[str, Any]:
	_require_frontend_role()
	doc = frappe.get_doc("Stock Entry", (name or "").strip())
	if doc.owner != frappe.session.user:
		frappe.throw(_("Somente quem preparou esta transferência pode enviá-la."), frappe.PermissionError)
	if not _current_user_is_manager():
		frappe.throw(_("Transferencia entre estoques exige o Gestor."), frappe.PermissionError)
	return _submit_operational_transfer(doc)


def submit_approved_stock_transfer(name: str) -> dict[str, Any]:
	"""Execute a pending operational transfer for the real approving Gestor."""
	_require_frontend_role()
	if not _current_user_is_manager():
		frappe.throw(_("Transferencia entre estoques exige o Gestor."), frappe.PermissionError)
	doc = frappe.get_doc("Stock Entry", (name or "").strip())
	return _submit_operational_transfer(doc)


def _submit_operational_transfer(doc) -> dict[str, Any]:
	if doc.docstatus != 0:
		frappe.throw(_("Esta transferência não está pendente."), frappe.ValidationError)
	repair, commercial = _operational_warehouse_pair()
	if doc.stock_entry_type != "Material Transfer" or {doc.from_warehouse, doc.to_warehouse} != {repair, commercial}:
		frappe.throw(_("Transferência inválida."), frappe.ValidationError)
	# The endpoint deliberately bypasses only DocType ACLs: the prepared draft,
	# warehouses, manager role, and native Stock Entry validations remain enforced.
	doc.flags.ignore_permissions = True
	doc.submit()
	return {"item": _serialize_stock_transfer(doc)}


@frappe.whitelist()
def list_stock_items(query: str = "", limit: int = 12, scope: str = "parts-stock", category: str = "") -> dict[str, Any]:
	_require_frontend_role()
	limit = max(1, min(int(limit or 12), 50))
	query = (query or "").strip()
	scope = (scope or "parts-stock").strip()
	if is_restricted_technician() and scope != "repair-parts":
		frappe.throw(_("O perfil técnico consulta somente o estoque de Reparo."), frappe.PermissionError)
	repair_warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
	commercial_warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	if scope == "repair-parts":
		stock_groups = tuple(_descendant_item_groups("Peças de Reparo")) or ("",)
		warehouse = repair_warehouse
	elif scope == "commercial-products":
		stock_groups = tuple(get_retail_item_groups()) or ("",)
		warehouse = commercial_warehouse
	elif scope == "used-devices":
		stock_groups = tuple(_descendant_item_groups("Aparelhos Usados")) or ("",)
		warehouse = commercial_warehouse
	else:
		stock_groups = tuple(get_commercial_item_groups()) or ("",)
		warehouse = None
	category = (category or "").strip()
	if category:
		if not frappe.db.exists("Item Group", category):
			frappe.throw(_("Categoria de produto inválida."), frappe.ValidationError)
		category_groups = set(_descendant_item_groups(category))
		stock_groups = tuple(group for group in stock_groups if group in category_groups)
		if not stock_groups:
			return {
				"items": [],
				"count": 0,
				"fields": ["item_code", "item_name", "item_group", "has_serial_no", "barcode", "is_commercial_item", "warehouse", "available_qty"],
			}
	conditions = [
		"item.disabled = 0",
		"item.is_stock_item = 1",
		"bin.warehouse is not null",
	]
	values: dict[str, Any] = {"stock_groups": stock_groups, "limit": limit}
	conditions.append("item.item_group in %(stock_groups)s")
	if warehouse:
		conditions.append("bin.warehouse = %(stock_warehouse)s")
		values["stock_warehouse"] = warehouse
	if query:
		conditions.append(
			"""(
				item.name like %(query)s
				or item.item_name like %(query)s
				or item.item_group like %(query)s
				or bin.warehouse like %(query)s
				or exists (
					select 1 from `tabItem Barcode` searched_barcode
					where searched_barcode.parent = item.name and searched_barcode.barcode like %(query)s
				)
			)"""
		)
		values["query"] = f"%{query}%"

	rows = frappe.db.sql(
		f"""
		select
			item.name as item_code,
			item.item_name,
			item.item_group,
			item.has_serial_no,
			(select item_barcode.barcode from `tabItem Barcode` item_barcode where item_barcode.parent = item.name order by item_barcode.idx asc limit 1) as barcode,
			item.item_group in %(stock_groups)s as is_commercial_item,
			bin.warehouse,
			bin.actual_qty as available_qty
		from `tabItem` item
		inner join `tabBin` bin on bin.item_code = item.name
		where {" and ".join(conditions)}
		order by item.modified desc
		limit %(limit)s
		""",
		values,
		as_dict=True,
	)
	return {
		"items": [_serialize_stock_item(item) for item in rows],
		"count": len(rows),
		"fields": ["item_code", "item_name", "item_group", "has_serial_no", "barcode", "is_commercial_item", "warehouse", "available_qty"],
	}


def _service_order_search_filters(
	query: str | None = None,
	status: str | None = None,
	in_progress: int | bool | str | None = None,
	from_date: str | None = None,
	to_date: str | None = None,
) -> tuple[dict[str, Any], list[list[str]]]:
	filters: dict[str, Any] = {}
	or_filters: list[list[str]] = []

	status = (status or "").strip()
	legacy_in_progress = status == "in_progress"
	in_progress_only = (not status or legacy_in_progress) if in_progress is None else str(in_progress).strip().lower() in {"1", "true", "yes"}
	if in_progress_only:
		filters["pickup_date"] = ["is", "not set"]
	if status and status not in {"all", "in_progress"}:
		filters["workflow_state"] = status

	from_date = (from_date or "").strip()
	to_date = (to_date or "").strip()
	if from_date and to_date:
		filters["modified"] = ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]
	elif from_date:
		filters["modified"] = [">=", f"{from_date} 00:00:00"]
	elif to_date:
		filters["modified"] = ["<=", f"{to_date} 23:59:59"]

	query = (query or "").strip()[:80]
	if query:
		like = f"%{query}%"
		or_filters = [
			["Service Order", "name", "like", like],
			["Service Order", "customer", "like", like],
			["Service Order", "customer_device", "like", like],
			["Service Order", "reported_defect", "like", like],
			["Service Order", "workflow_state", "like", like],
			["Service Order", "technician", "like", like],
			["Service Order", "attendant", "like", like],
			["Service Order", "priority", "like", like],
		]

	return filters, or_filters


def _count_service_orders(filters: dict[str, Any], or_filters: list[list[str]]) -> int:
	return len(
		frappe.get_all(
			"Service Order",
			filters=filters,
			or_filters=or_filters,
			pluck="name",
			limit_page_length=0,
		)
	)


def _serialize_service_order(item: dict[str, Any]) -> dict[str, Any]:
	clock = stage_clock.get_stage_clock(item)
	return {
		"name": item.get("name"),
		"customer": item.get("customer"),
		"customer_device": item.get("customer_device"),
		"entry_date": str(item.get("entry_date") or ""),
		"attendant": item.get("attendant"),
		"technician": item.get("technician"),
		"pricing_responsibility": item.get("pricing_responsibility"),
		"budget_review_required": bool(item.get("budget_review_required")),
		"selling_total": flt(item.get("labor_total")) + flt(item.get("parts_total")),
		"priority": item.get("priority"),
		"workflow_state": item.get("workflow_state"),
		"stage_clock": clock,
		"workflow_transitions": _get_service_order_transition_options(item.get("workflow_state")),
		"workflow_blockers": _get_workflow_blockers(item),
		"workflow_requestable_transitions": _get_workflow_requestable_transitions(item),
		"has_sales_invoice": bool(item.get("sales_invoice")),
		"next_action": action_for_service_order(item),
		"reported_defect": item.get("reported_defect"),
		"approval_status": item.get("approval_status"),
		"approval_deadline": str(item.get("approval_deadline") or ""),
		"modified": str(item.get("modified") or ""),
	}


def _get_workflow_blockers(order: Any) -> dict[str, str]:
	"""Expose safe, actionable preflight guidance for workflow controls."""
	blockers = _get_workflow_role_blockers(order)
	if order.get("workflow_state") not in {STATE_EM_DIAGNOSTICO, STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO}:
		return blockers

	name = order.get("name")
	if order.get("workflow_state") == STATE_EM_DIAGNOSTICO:
		if not order.get("diagnosis_completed_at") or not order.get("pricing_responsibility"):
			blockers[STATE_DIAGNOSTICADO_AGUARDANDO_ORCAMENTO] = "Registre o diagnóstico técnico antes de concluir esta etapa."
		return blockers

	if not (
		frappe.db.count("Service Order Service", {"parent": name})
		or frappe.db.count("Service Order Part", {"parent": name})
	):
		blockers[STATE_AGUARDANDO_APROVACAO] = "Inclua ao menos um serviço ou peça no orçamento antes de enviar ao cliente."
	return blockers


def _get_workflow_role_blockers(order: Any) -> dict[str, str]:
	"""Describe role-only workflow gates without granting any front-end authority."""
	user_roles = set(frappe.get_roles(frappe.session.user))
	blockers: dict[str, str] = {}
	for transition in _get_service_order_transitions():
		state, _action, next_state, allowed, *rest = transition
		condition = rest[0] if rest else None
		if state != order.get("workflow_state") or condition == "False":
			continue
		if allowed in user_roles or "System Manager" in user_roles:
			continue
		blockers.setdefault(
			next_state,
			_("Seu papel não permite mover esta OS para {0}. Solicite aprovação do Gestor.").format(next_state),
		)
	return blockers


def _get_workflow_requestable_transitions(order: Any) -> list[str]:
	"""Only role gates are requestable; data-completeness gates must be resolved first."""
	role_blockers = _get_workflow_role_blockers(order)
	hard_blockers = _get_workflow_blockers(order)
	return [target for target in role_blockers if hard_blockers.get(target) == role_blockers[target]]


def _serialize_customer(item: dict[str, Any], include_fiscal: bool = True) -> dict[str, Any]:
	return {
		"name": item.get("name"),
		"customer_name": item.get("customer_name"),
		"mobile_no": item.get("mobile_no"),
		"custom_whatsapp": item.get("custom_whatsapp"),
		"custom_cpf": item.get("custom_cpf") if include_fiscal else None,
		"custom_rg": item.get("custom_rg") if include_fiscal else None,
		CUSTOMER_NO_CPF_FIELD: bool(item.get(CUSTOMER_NO_CPF_FIELD)) if include_fiscal else False,
		"email_id": item.get("email_id") if include_fiscal else None,
		"modified": str(item.get("modified") or ""),
	}


def _serialize_customer_device(item: dict[str, Any]) -> dict[str, Any]:
	return {
		"name": item.get("name"),
		"customer": item.get("customer"),
		"brand": item.get("brand"),
		"model": item.get("model"),
		"color": item.get("color"),
		"imei_serial": item.get("imei_serial"),
		"capacity": item.get("capacity"),
		"photo_url": item.get("photos"),
		"registration_date": str(item.get("registration_date") or ""),
		"modified": str(item.get("modified") or ""),
	}


def _serialize_trade_evaluation(item: dict[str, Any]) -> dict[str, Any]:
	return {
		"name": item.get("name"),
		"customer": item.get("customer"),
		"device_type": item.get("device_type"),
		"evaluated_device_desc": item.get("evaluated_device_desc"),
		"model": item.get("model"),
		"imei": item.get("imei"),
		"physical_state": item.get("physical_state"),
		"destination": item.get("destination"),
		"suggested_value": flt(item.get("suggested_value") or 0),
		"table_max": flt(item.get("table_max") or 0),
		"approved_value": flt(item.get("approved_value") or 0),
		"created_item": item.get("created_item") or None,
		"trade_category": item.get("trade_category") or None,
		"workflow_state": item.get("workflow_state"),
		"modified": str(item.get("modified") or ""),
	}


def _serialize_tradein_operation(doc: Any) -> dict[str, Any]:
	return {
		"name": doc.name,
		"evaluation": doc.get("evaluation"),
		"device_out": doc.get("device_out"),
		"difference": flt(doc.get("difference") or 0),
		"atomic_status": doc.get("atomic_status"),
		"used_device_fiscal_ref": doc.get("used_device_fiscal_ref") or None,
		"sale_fiscal_ref": doc.get("sale_fiscal_ref") or None,
	}


@contextmanager
def _run_post_sale_mutation():
	"""Scoped elevation for ERPNext's own stock and payment-ledger return posting."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		yield
	finally:
		if previous_user:
			frappe.set_user(previous_user)


def _create_sales_return_with_cash(data: dict[str, Any]):
	"""Create one native return and its operational movements as one database unit."""
	key = _validate_post_sale_idempotency_key(data.get("idempotency_key"))
	request_hash = _post_sale_request_hash(data)
	existing = _get_existing_post_sale_request(key, request_hash)
	if existing:
		return frappe.get_doc("Sales Invoice", existing.return_invoice), True

	savepoint = f"tp_post_sale_{frappe.generate_hash(length=12)}"
	frappe.db.savepoint(savepoint)
	try:
		original = frappe.get_doc("Sales Invoice", (data.get("invoice") or "").strip())
		require_open_cash_session(company=original.company)
		request = frappe.get_doc(
			{
				"doctype": POST_SALE_IDEMPOTENCY_DOCTYPE,
				"idempotency_key": key,
				"request_hash": request_hash,
				"status": "Processando",
				"requested_by": frappe.session.user,
				"original_invoice": original.name,
			}
		)
		request.insert(ignore_permissions=True)
		with _run_post_sale_mutation():
			return_doc = _build_sales_return(data)
			return_doc.insert(ignore_permissions=True)
			return_doc.submit()
		record_sales_invoice_cash_movements(invoice=return_doc, idempotency_prefix=f"return:{key}")
		request.return_invoice = return_doc.name
		request.status = "Concluída"
		request.save(ignore_permissions=True)
		return return_doc, False
	except frappe.UniqueValidationError:
		frappe.db.rollback(save_point=savepoint)
		existing = _get_existing_post_sale_request(key, request_hash)
		if existing:
			return frappe.get_doc("Sales Invoice", existing.return_invoice), True
		raise
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise


def _validate_post_sale_idempotency_key(value: Any) -> str:
	key = str(value or "").strip()
	if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,95}", key):
		frappe.throw(_("Referência idempotente da devolução inválida."), frappe.ValidationError)
	return key


def _post_sale_request_hash(data: dict[str, Any]) -> str:
	items = sorted(
		[
			{"item_code": str(row.get("item_code") or "").strip(), "qty": flt(row.get("qty"), 3)}
			for row in (data.get("items") or [])
			if isinstance(row, dict)
		],
		key=lambda row: row["item_code"],
	)
	canonical = json.dumps({"invoice": str(data.get("invoice") or "").strip(), "items": items}, sort_keys=True, separators=(",", ":"))
	return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _get_existing_post_sale_request(key: str, request_hash: str):
	if not frappe.db.exists(POST_SALE_IDEMPOTENCY_DOCTYPE, key):
		return None
	request = frappe.get_doc(POST_SALE_IDEMPOTENCY_DOCTYPE, key)
	if request.requested_by != frappe.session.user and frappe.session.user != "Administrator":
		raise frappe.PermissionError(_("Esta referência de devolução pertence a outra sessão."))
	if request.request_hash != request_hash:
		frappe.throw(_("Esta referência de devolução já foi usada com dados diferentes."), frappe.ValidationError)
	if request.status != "Concluída" or not request.return_invoice:
		frappe.throw(_("Esta devolução ainda está sendo processada. Aguarde antes de reenviar."), frappe.ValidationError)
	if frappe.db.get_value("Sales Invoice", request.return_invoice, "docstatus") != 1:
		frappe.throw(_("A devolução vinculada a esta referência não está válida."), frappe.ValidationError)
	return request


def _build_sales_return(data: dict[str, Any]):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	invoice_name = (data.get("invoice") or "").strip()
	if not invoice_name:
		frappe.throw(_("Selecione a venda original."), frappe.ValidationError)
	original = frappe.get_doc("Sales Invoice", invoice_name)
	if original.docstatus != 1 or original.is_return:
		frappe.throw(_("A venda original não está disponível para devolução."), frappe.ValidationError)
	requested = {str(row.get("item_code")): flt(row.get("qty")) for row in (data.get("items") or []) if row.get("item_code")}
	if not requested or any(qty <= 0 for qty in requested.values()):
		frappe.throw(_("Selecione ao menos um item e quantidade válida para devolver."), frappe.ValidationError)
	returned_rows = frappe.db.sql(
		"""select item_code, abs(sum(qty)) as qty from `tabSales Invoice Item`
		where parent in (select name from `tabSales Invoice` where return_against = %(invoice)s and is_return = 1)
		and docstatus = 1 group by item_code""",
		{"invoice": original.name}, as_dict=True,
	)
	previously_returned = {row.item_code: flt(row.qty) for row in returned_rows}
	original_by_item = {row.item_code: row for row in original.items}
	for item_code, qty in requested.items():
		row = original_by_item.get(item_code)
		if not row or qty > flt(row.qty) - previously_returned.get(item_code, 0):
			frappe.throw(_("Quantidade de devolução maior que a vendida."), frappe.ValidationError)
	return_doc = make_return_doc("Sales Invoice", original.name)
	return_doc.items = [row for row in return_doc.items if row.item_code in requested]
	for row in return_doc.items:
		row.qty = -abs(requested[row.item_code])
		row.stock_qty = -abs(requested[row.item_code] * flt(row.conversion_factor or 1))
	return_doc.set_missing_values()
	return_doc.calculate_taxes_and_totals()
	# ERPNext intentionally omits POS payments from make_return_doc. Rebuild the
	# original split with negative values so its native payment ledger reverses
	# each payment method instead of creating an unrelated customer credit.
	if cint(original.is_pos):
		payments = [row for row in original.payments if flt(row.amount)]
		total_paid = sum(flt(row.amount) for row in payments)
		if payments and total_paid:
			return_doc.set("payments", [])
			remaining = abs(flt(return_doc.grand_total))
			for index, payment in enumerate(payments):
				amount = remaining if index == len(payments) - 1 else flt(
					abs(flt(return_doc.grand_total)) * flt(payment.amount) / total_paid,
					2,
				)
				remaining = flt(remaining - amount, 2)
				return_doc.append(
					"payments",
					{"mode_of_payment": payment.mode_of_payment, "account": payment.account, "amount": -abs(amount)},
				)
	return return_doc


def _serialize_stock_item(item: dict[str, Any]) -> dict[str, Any]:
	return {
		"item_code": item.get("item_code"),
		"item_name": item.get("item_name"),
		"item_group": item.get("item_group"),
		"has_serial_no": bool(item.get("has_serial_no")),
		"barcode": item.get("barcode"),
		"is_commercial_item": bool(item.get("is_commercial_item")),
		"warehouse": item.get("warehouse"),
		"available_qty": float(item.get("available_qty") or 0),
	}


def _operational_warehouse_pair() -> tuple[str, str]:
	repair = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
	commercial = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	if not repair or not commercial:
		frappe.throw(_("Configure os depósitos de Reparo e Comercial antes de transferir."), frappe.ValidationError)
	return repair, commercial


def _current_user_is_manager() -> bool:
	roles = set(frappe.get_roles(frappe.session.user))
	return frappe.session.user == "Administrator" or bool({"Tecponto Gestor", "System Manager"} & roles)


def _current_user_is_director() -> bool:
	roles = set(frappe.get_roles(frappe.session.user))
	return frappe.session.user == "Administrator" or "Tecponto Diretor" in roles


def _serialize_stock_transfer(doc) -> dict[str, Any]:
	row = (doc.get("items") or [None])[0]
	return {
		"name": doc.name,
		"item_code": row.item_code if row else None,
		"qty": flt(row.qty if row else 0),
		"source_warehouse": doc.from_warehouse,
		"target_warehouse": doc.to_warehouse,
		"docstatus": int(doc.docstatus or 0),
	}


def _descendant_item_groups(root: str) -> list[str]:
	bounds = frappe.db.get_value("Item Group", root, ["lft", "rgt"], as_dict=True)
	if not bounds:
		return []
	return frappe.get_all(
		"Item Group",
		filters={"lft": [">=", bounds.lft], "rgt": ["<=", bounds.rgt]},
		pluck="name",
	)


def _serialize_pos_item(item: dict[str, Any]) -> dict[str, Any]:
	standard_rate = flt(item.get("standard_rate") or 0)
	return {
		"item_code": item.get("item_code"),
		"item_name": item.get("item_name"),
		"item_group": item.get("item_group"),
		"barcode": item.get("barcode"),
		"description": strip_html(item.get("description") or "").strip()[:180] or None,
		"image": item.get("image"),
		"standard_rate": standard_rate,
		"has_price": standard_rate > 0,
		"available_qty": flt(item.get("available_qty") or 0),
		"warehouse": item.get("warehouse"),
	}


def _parse_payload(payload: str | dict[str, Any] | None) -> dict[str, Any]:
	if isinstance(payload, dict):
		return payload
	if isinstance(payload, str) and payload.strip():
		return json.loads(payload)
	frappe.throw(_("Dados do check-in não informados."), frappe.ValidationError)


def _validate_budget_line_type(line_type: str | None) -> str:
	value = (line_type or "").strip()
	if value not in {"service", "part"}:
		frappe.throw(_("Tipo de linha de orçamento inválido."), frappe.ValidationError)
	return value


def _get_default_repair_warehouse() -> str | None:
	return (
		frappe.db.get_value("Warehouse", {"warehouse_name": ["like", "%Reparo%"], "is_group": 0, "disabled": 0}, "name")
		or frappe.db.get_value("Warehouse", {"name": ["like", "%Reparo%"], "is_group": 0, "disabled": 0}, "name")
		or frappe.db.get_value("Warehouse", {"warehouse_name": ["like", "%Peças%"], "is_group": 0, "disabled": 0}, "name")
		or frappe.db.get_value("Warehouse", {"name": ["like", "%Peças%"], "is_group": 0, "disabled": 0}, "name")
	)


def _quote_send_text(doc: Any, channel: str, notes: str) -> str:
	customer = _customer_label(doc.get("customer")) or "cliente"
	total = flt(doc.get("grand_total") or 0)
	deadline = doc.get("approval_deadline") or "prazo não definido"
	lines = [
		f"Orçamento {doc.name} enviado para {customer}.",
		f"Canal: {channel}.",
		f"Total: R$ {total:.2f}.",
		f"Validade: {deadline}.",
	]
	if notes:
		lines.append(f"Observação: {notes}")
	return "\n".join(lines)


def _quote_send_content(doc: Any, channel: str, notes: str) -> str:
	return frappe.utils.escape_html(_quote_send_text(doc, channel, notes)).replace("\n", "<br>")


def _validate_checkin_payload(data: dict[str, Any]) -> None:
	customer = data.get("customer") or {}
	device = data.get("device") or {}
	service_order = data.get("service_order") or {}
	entry_photo = data.get("entry_photo") or {}

	if customer.get("existing_name"):
		assert_existing_customer_is_complete(customer["existing_name"])
	else:
		validate_customer_contact_document(customer)

	if not device.get("existing_name"):
		_validate_device_payload(device)

	if not (service_order.get("physical_state") or "").strip():
		frappe.throw(_("Informe o estado físico declarado."), frappe.ValidationError)
	entry_operating_condition = (service_order.get("entry_operating_condition") or ENTRY_OPERATING_CONDITION_OK).strip()
	if entry_operating_condition not in ENTRY_OPERATING_CONDITIONS:
		frappe.throw(_("Informe uma condição de funcionamento válida na entrada."), frappe.ValidationError)
	access_type = (service_order.get("device_access_type") or "").strip()
	if access_type and access_type not in {"PIN", "Padrão de desenho", "Alfanumérica"}:
		frappe.throw(_("Tipo de acesso do aparelho inválido."), frappe.ValidationError)
	if not _is_image_data_url(entry_photo.get("data_url")):
		frappe.throw(_("Anexe ao menos uma foto de entrada."), frappe.ValidationError)


def _validate_device_payload(data: dict[str, Any]) -> None:
	if not (data.get("brand") or "").strip():
		frappe.throw(_("Informe a marca do aparelho."), frappe.ValidationError)
	if not (data.get("model") or "").strip():
		frappe.throw(_("Informe o modelo do aparelho."), frappe.ValidationError)
	if not (data.get("imei_serial") or "").strip():
		frappe.throw(_("IMEI/serial é obrigatório para cadastrar aparelho."), frappe.ValidationError)


def _get_or_create_checkin_customer(data: dict[str, Any]) -> str:
	existing_name = (data.get("existing_name") or "").strip()
	if existing_name:
		if not frappe.db.exists("Customer", existing_name):
			frappe.throw(_("Cliente selecionado não existe."), frappe.ValidationError)
		return existing_name

	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": data["customer_name"].strip(),
			"customer_type": "Individual",
			"mobile_no": (data.get("mobile_no") or "").strip(),
			"custom_whatsapp": (data.get("custom_whatsapp") or data.get("mobile_no") or "").strip(),
			"custom_cpf": (data.get("custom_cpf") or "").strip(),
			"custom_rg": (data.get("custom_rg") or "").strip(),
			CUSTOMER_NO_CPF_FIELD: 1 if data.get(CUSTOMER_NO_CPF_FIELD) else 0,
			"email_id": (data.get("email_id") or "").strip(),
		}
	)
	customer.insert(ignore_permissions=True)
	return customer.name


def _get_or_create_checkin_device(data: dict[str, Any], customer_name: str) -> str:
	existing_name = (data.get("existing_name") or "").strip()
	if existing_name:
		device = frappe.db.get_value("Customer Device", existing_name, ["customer", "imei_serial"], as_dict=True)
		customer = device.customer if device else None
		if device and not (device.imei_serial or "").strip():
			frappe.throw(_("Aparelho selecionado não possui IMEI/serial."), frappe.ValidationError)
		if not customer:
			frappe.throw(_("Aparelho selecionado não existe."), frappe.ValidationError)
		if customer != customer_name:
			frappe.throw(_("O aparelho selecionado não pertence ao cliente informado."), frappe.ValidationError)
		return existing_name

	device = frappe.get_doc(
		{
			"doctype": "Customer Device",
			"customer": customer_name,
			"brand": data["brand"].strip(),
			"model": data["model"].strip(),
			"color": (data.get("color") or "").strip(),
			"imei_serial": data["imei_serial"].strip(),
			"capacity": (data.get("capacity") or "").strip(),
			"general_state": (data.get("general_state") or "").strip(),
			"registration_date": today(),
		}
	)
	device.insert(ignore_permissions=True)
	return device.name


def _checkin_defects(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
	if isinstance(value, str):
		try:
			value = json.loads(value)
		except (TypeError, ValueError):
			value = []
	if not isinstance(value, (list, tuple)):
		return []
	return list(dict.fromkeys((item or "").strip() for item in value if isinstance(item, str) and item.strip()))


def _append_checkin_service_suggestions(order: Any, services: list[dict[str, Any]]) -> None:
	"""Pre-populate the editable budget from active, server-resolved catalog rows."""
	if not services:
		return
	from tecponto_app.tecponto.service_order.billing import _get_labor_item

	for service in services:
		order.append(
			"services",
			{
				"item_code": _get_labor_item(),
			"catalog_service": service["name"],
			"service_category": service.get("category"),
				"description": service["service_name"],
				"qty": 1,
				"rate": 0 if order.get("is_warranty") else flt(service["default_labor_price"]),
				"service_duration": flt(service["default_duration"]),
				"duration_unit": service["duration_unit"],
			},
		)


def _save_checkin_photo(service_order: str, photo: dict[str, str]) -> str:
	filename = _safe_filename(photo.get("filename") or f"{service_order}-entrada.png")
	if "." not in filename:
		filename = f"{filename}.png"
	file_doc = save_file(
		filename,
		photo["data_url"],
		"Service Order",
		service_order,
		decode=True,
		is_private=0,
		df="entry_photos",
	)
	return file_doc.file_url


def _save_customer_device_photo(customer_device: str, photo: dict[str, str]) -> str:
	filename = _safe_filename(photo.get("filename") or f"{customer_device}-foto.png")
	if "." not in filename:
		filename = f"{filename}.png"
	file_doc = save_file(
		filename,
		photo["data_url"],
		"Customer Device",
		customer_device,
		decode=True,
		is_private=0,
		df="photos",
	)
	return file_doc.file_url


def _is_image_data_url(value: str | None) -> bool:
	return bool(value and isinstance(value, str) and value.startswith("data:image/") and "," in value)


def _safe_filename(value: str) -> str:
	name = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
	return name or "entrada.png"


def _serialize_service_row(row: Any) -> dict[str, Any]:
	qty = flt(row.get("qty") or 0)
	unit_price = flt(row.get("rate") or 0)
	return {
		"name": row.get("name"),
		"item_code": row.get("item_code"),
		"description": row.get("description"),
		"qty": qty,
		"unit_price": unit_price,
		"amount": flt(qty * unit_price),
		"catalog_service": row.get("catalog_service"),
		"service_category": row.get("service_category"),
		"service_duration": flt(row.get("service_duration") or 0),
		"duration_unit": row.get("duration_unit") or "Horas",
		"technician": row.get("technician"),
	}


def _serialize_part_row(row: Any) -> dict[str, Any]:
	qty = flt(row.get("qty") or 0)
	unit_price = flt(row.get("rate") or 0)
	return {
		"name": row.get("name"),
		"item_code": row.get("item_code"),
		"description": row.get("description"),
		"qty": qty,
		"unit_price": unit_price,
		"amount": flt(qty * unit_price),
		"warehouse": row.get("warehouse"),
		"outcome": row.get("outcome"),
		"loss_reason": row.get("loss_reason"),
		"reservation": row.get("reservation"),
		"stock_entry": row.get("stock_entry"),
		"used_date": str(row.get("used_date") or ""),
		"part_source": row.get("part_source") or "Loja",
		"service_row": row.get("service_row"),
		"customer_part_note": row.get("customer_part_note"),
	}


def _build_closed_budget_lines(services: list[dict[str, Any]], parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Customer-facing aggregate; it deliberately contains sale prices only."""
	parts_by_service: dict[str, float] = {}
	unlinked_parts: list[dict[str, Any]] = []
	for part in parts:
		if part.get("part_source") == "Cliente":
			continue
		if part.get("service_row"):
			parts_by_service[part["service_row"]] = parts_by_service.get(part["service_row"], 0) + flt(part.get("amount"))
		else:
			unlinked_parts.append(part)
	lines = [
		{
			"description": service.get("description") or service.get("item_code") or "Serviço",
			"amount": flt(service.get("amount")) + parts_by_service.get(service.get("name") or "", 0),
		}
		for service in services
	]
	lines.extend({"description": part.get("description") or part.get("item_code") or "Peça", "amount": flt(part.get("amount"))} for part in unlinked_parts)
	return lines


def _get_customer_detail(customer: str | None, include_fiscal: bool = True) -> dict[str, Any] | None:
	if not customer:
		return None
	fields = ["name", "customer_name", "mobile_no", "custom_whatsapp"]
	if include_fiscal:
		fields.extend(["custom_cpf", "custom_rg", CUSTOMER_NO_CPF_FIELD, "email_id"])
	item = frappe.db.get_value(
		"Customer",
		customer,
		fields,
		as_dict=True,
	)
	if not item:
		return {"name": customer, "customer_name": customer}
	result = dict(item)
	if not include_fiscal:
		result.update({"custom_cpf": None, "custom_rg": None, CUSTOMER_NO_CPF_FIELD: False, "email_id": None})
	return result


def _technician_customer_names() -> list[str] | None:
	"""Return a technical-only user's customer portfolio, or None for broader roles."""
	service_scope = service_order_scope_filters()
	if not service_scope:
		return None
	return sorted(
		{
			customer
			for customer in frappe.get_all("Service Order", filters=service_scope, pluck="customer", limit_page_length=0)
			if customer
		}
	)


def _customer_label(customer: str | None) -> str:
	item = _get_customer_detail(customer)
	if not item:
		return ""
	return item.get("customer_name") or item.get("name") or ""


def _get_device_detail(customer_device: str | None) -> dict[str, Any] | None:
	if not customer_device:
		return None
	item = frappe.db.get_value(
		"Customer Device",
		customer_device,
		["name", "customer", "brand", "model", "color", "imei_serial", "capacity", "photos"],
		as_dict=True,
	)
	return dict(item) if item else {"name": customer_device}


def _get_sales_invoice_status(sales_invoice: str | None) -> str | None:
	if not sales_invoice:
		return None
	return frappe.db.get_value("Sales Invoice", sales_invoice, "status")


def _service_order_finance_payload(doc, *, technical_view: bool, fallback_total: float) -> dict[str, Any]:
	if technical_view:
		return {
			"sales_invoice": None,
			"sales_invoice_status": None,
			"total_due": 0.0,
			"paid_total": 0.0,
			"remaining_total": 0.0,
			"payments": [],
			"options": {"advance": False, "installments": False, "tradein": False, "diagnostic_fee": False, "storage_fee": False},
		}
	invoice = frappe.get_doc("Sales Invoice", doc.sales_invoice) if doc.get("sales_invoice") else None
	total_due = flt(invoice.grand_total, 2) if invoice else flt(fallback_total, 2)
	summary = service_order_payments.payment_summary(doc.name, total_due)
	config = get_operation_config()
	return {
		"sales_invoice": doc.get("sales_invoice") or None,
		"sales_invoice_status": invoice.status if invoice else None,
		"total_due": total_due,
		"paid_total": summary["paid_total"],
		"remaining_total": summary["remaining_total"],
		"payments": summary["items"],
		"options": {
			"advance": bool(config["payments"]["advance_enabled"]),
			"installments": bool(config["payments"]["installments_enabled"]),
			"tradein": bool(config["payments"]["device_tradein_enabled"]),
			"diagnostic_fee": bool(config["diagnostic_fee"]["enabled"]),
			"storage_fee": bool(config["storage_fee"]["enabled"]),
		},
	}


@frappe.whitelist()
def get_service_order_director_financial_summary(name: str) -> dict[str, Any]:
	"""Return the per-OS confidential cost projection for the Director only.

	The normal detail payload intentionally never receives these fields. Cost is
	derived from parts actually used in the repair and labor cost only from
	already-provisioned Additional Salary commission entries; it does not invent
	a payroll or a parallel financial balance.
	"""
	_require_director_financial_role()
	name = (name or "").strip()
	if not name:
		frappe.throw(_("Informe a ordem de serviço."), frappe.ValidationError)

	doc = frappe.get_doc("Service Order", name)
	doc.check_permission("read")
	commercial = _service_order_finance_payload(
		doc,
		technical_view=False,
		fallback_total=flt(doc.get("grand_total") or 0),
	)
	part_cost = frappe.db.sql(
		"""
		select coalesce(sum(coalesce(valuation_rate, 0) * coalesce(qty, 0)), 0)
		from `tabService Order Part`
		where parent = %(service_order)s
			and outcome = %(outcome)s
		""",
		{"service_order": doc.name, "outcome": OUTCOME_USADA},
	)[0][0]
	labor_cost = 0
	if frappe.db.table_exists("Additional Salary"):
		labor_cost = frappe.db.sql(
			"""
			select coalesce(sum(additional_salary.amount), 0)
			from `tabAdditional Salary` additional_salary
			inner join `tabService Order Service` service_row
				on service_row.name = additional_salary.ref_docname
			where additional_salary.docstatus = 1
				and additional_salary.salary_component = 'Comissão'
				and additional_salary.type = 'Earning'
				and additional_salary.ref_doctype = 'Service Order Service'
				and service_row.parent = %(service_order)s
			""",
			{"service_order": doc.name},
		)[0][0]
	total_cost = flt(part_cost) + flt(labor_cost)
	revenue = flt(commercial["total_due"])
	gross_profit = revenue - total_cost
	return {
		"service_order": doc.name,
		"revenue": float(revenue),
		"part_cost": float(flt(part_cost)),
		"labor_cost_provisioned": float(flt(labor_cost)),
		"total_cost": float(total_cost),
		"gross_profit": float(gross_profit),
		"gross_margin_pct": float((gross_profit / revenue * 100) if revenue else 0),
		"net_profit_available": False,
	}


def _get_allowed_kanban_action(current_state: str | None, target_state: str) -> str:
	user_roles = set(frappe.get_roles(frappe.session.user))
	matching_transitions = []
	for transition in _get_service_order_transitions():
		state, action, next_state, allowed, *rest = transition
		condition = rest[0] if rest else None
		if state == current_state and next_state == target_state and condition != "False":
			matching_transitions.append((action, allowed))

	if not matching_transitions:
		frappe.throw(
			_("Transição não permitida no Kanban: {0} → {1}.").format(current_state or "Sem status", target_state),
			frappe.ValidationError,
		)

	for action, allowed in matching_transitions:
		if allowed in user_roles or "System Manager" in user_roles:
			return action

	frappe.throw(
		_("Seu papel não permite mover esta OS de {0} para {1}.").format(current_state or "Sem status", target_state),
		frappe.PermissionError,
	)


def _get_visible_workflow_actions(doc: Any) -> list[dict[str, str]]:
	user_roles = set(frappe.get_roles(frappe.session.user))
	actions: list[dict[str, str]] = []
	for transition in _get_service_order_transitions():
		state, action, next_state, allowed, *rest = transition
		condition = rest[0] if rest else None
		if state != doc.get("workflow_state"):
			continue
		if condition == "False":
			continue
		if allowed not in user_roles and "System Manager" not in user_roles:
			continue
		actions.append(
			{
				"action": action,
				"next_state": next_state,
				"role": allowed,
			}
		)
	return actions


def _get_service_order_transition_options(current_state: str | None) -> list[dict[str, str]]:
	"""Expose workflow-valid destinations only; execution permission remains server-side."""
	options: list[dict[str, str]] = []
	seen: set[tuple[str, str]] = set()
	for transition in _get_service_order_transitions():
		state, action, next_state, allowed, *rest = transition
		condition = rest[0] if rest else None
		key = (action, next_state)
		if state != current_state or condition == "False" or key in seen:
			continue
		seen.add(key)
		options.append({"action": action, "next_state": next_state, "role": allowed})
	return options


def _get_user_display_name(username: str | None) -> str:
	if not username:
		return "sistema"
	full_name = frappe.db.get_value("User", username, "full_name")
	return full_name or username


def _get_service_order_timeline(doc: Any) -> list[dict[str, str]]:
	timeline = [
		{
			"title": "Entrada criada",
			"detail": f"{doc.get('reported_defect') or 'Atendimento aberto no balcão'} · por {_get_user_display_name(doc.get('attendant') or doc.get('owner'))}",
			"date": str(doc.get("entry_date") or doc.get("creation") or ""),
			"tone": "blue",
		}
	]
	if frappe.db.exists("DocType", "Tecponto Service Order Assignment Event"):
		assignment_events = frappe.get_all(
			"Tecponto Service Order Assignment Event",
			filters={"service_order": doc.name},
			fields=["event_type", "previous_technician", "new_technician", "performed_by", "observation", "occurred_at"],
			order_by="occurred_at asc, creation asc",
			limit_page_length=100,
		)
		for event in assignment_events:
			labels = {"Claim": "OS assumida", "Assign": "Técnico atribuído", "Transfer": "OS transferida"}
			if event.event_type == "Transfer":
				detail = f"{event.previous_technician or 'Sem técnico'} → {event.new_technician}"
			else:
				detail = f"Técnico: {event.new_technician}"
			if event.observation:
				detail += f" · {event.observation}"
			detail += f" · por {_get_user_display_name(event.performed_by)}"
			timeline.append({"title": labels.get(event.event_type, "Atribuição"), "detail": detail, "date": str(event.occurred_at or ""), "tone": "blue"})
	if doc.get("problem_found") or doc.get("diagnosis_date"):
		timeline.append(
			{
				"title": "Diagnóstico",
				"detail": f"{doc.get('problem_found') or 'Diagnóstico registrado'} · por {_get_user_display_name(doc.get('technician') or doc.get('diagnosis_completed_by'))}",
				"date": str(doc.get("diagnosis_date") or ""),
				"tone": "amber",
			}
		)
	if doc.get("diagnosis_completed_at") and doc.get("pricing_responsibility"):
		timeline.append(
			{
				"title": "Diagnóstico concluído e repassado",
				"detail": f"Precificação: {doc.get('pricing_responsibility')} · por {_get_user_display_name(doc.get('diagnosis_completed_by'))}",
				"date": str(doc.get("diagnosis_completed_at") or ""),
				"tone": "amber",
			}
		)
	timeline.extend(_get_quote_send_timeline_events(doc))
	if doc.get("approval_status") and doc.get("approval_status") != "Pendente":
		detail = f"{doc.get('approval_status')} via {doc.get('approval_channel') or 'Canal não informado'}"
		if doc.get("approval_notes"):
			detail += f" · {doc.get('approval_notes')}"
		detail += f" · por {_get_user_display_name(doc.get('approved_by_attendant') or doc.get('approved_by'))}"
		timeline.append(
			{
				"title": "Aprovação",
				"detail": detail,
				"date": str(doc.get("approval_date") or ""),
				"tone": "green" if doc.get("approval_status") == "Aprovado" else "red",
			}
		)
	if frappe.db.exists("DocType", "Comment"):
		comments = frappe.get_all(
			"Comment",
			filters={"reference_doctype": doc.doctype, "reference_name": doc.name, "comment_type": "Comment"},
			fields=["content", "comment_by", "comment_email", "creation"],
			order_by="creation asc",
			limit_page_length=50,
		)
		for comment in comments:
			user_label = _get_user_display_name(comment.comment_email or comment.comment_by)
			timeline.append(
				{
					"title": "Acompanhamento / Nota",
					"detail": f"{strip_html(comment.content or '')} · por {user_label}",
					"date": str(comment.creation or ""),
					"tone": "blue",
				}
			)
	timeline.append(
		{
			"title": "Status atual",
			"detail": doc.get("workflow_state") or "Sem status",
			"date": str(doc.get("modified") or ""),
			"tone": "orange",
		}
	)
	if doc.get("pickup_date"):
		timeline.append(
			{
				"title": "Retirada",
				"detail": f"{doc.get('picked_up_by') or 'Cliente retirou o aparelho'} · por {_get_user_display_name(doc.get('delivered_by') or doc.get('modified_by'))}",
				"date": str(doc.get("pickup_date") or ""),
				"tone": "green",
			}
		)
	return sorted(timeline, key=lambda event: event.get("date") or "")


def _get_quote_send_timeline_events(doc: Any) -> list[dict[str, str]]:
	communications = frappe.get_all(
		"Communication",
		filters={
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"subject": ["like", "Orçamento enviado%"],
		},
		fields=["communication_medium", "text_content", "communication_date", "creation", "sender", "user"],
		order_by="communication_date asc, creation asc",
		limit_page_length=20,
	)
	events: list[dict[str, str]] = []
	for communication in communications:
		sender_name = _get_user_display_name(communication.user or communication.sender)
		events.append(
			{
				"title": "Orçamento enviado",
				"detail": f"{_quote_send_timeline_detail(communication)} · por {sender_name}",
				"date": str(communication.communication_date or communication.creation or ""),
				"tone": "amber",
			}
		)
	return events


def _quote_send_timeline_detail(communication: Any) -> str:
	medium_label = {
		"Chat": "WhatsApp",
		"Phone": "Telefone",
		"Visit": "Presencial",
		"Email": "E-mail",
	}.get(communication.communication_medium, communication.communication_medium or "Canal registrado")
	text = (communication.text_content or "").splitlines()
	note = next((line.replace("Observação:", "").strip() for line in text if line.startswith("Observação:")), "")
	return f"{medium_label}{f' · {note}' if note else ''}"


def _get_service_order_print_links(name: str) -> list[dict[str, str]]:
	order = frappe.get_doc("Service Order", name)
	links = [
		_print_link(name, "Termo de entrada", PF_TERMO_ENTRADA),
		_print_link(name, "Orçamento fechado", PF_OS_ORCAMENTO),
		_print_link(name, "Orçamento discriminado", PF_OS_ORCAMENTO_DISCRIMINADO),
		_print_link(name, "Laudo técnico", PF_LAUDO_TECNICO),
		_print_link(name, "Termo de garantia", PF_TERMO_GARANTIA),
		_print_link(name, "Etiqueta QR", PF_ETIQUETA_QR),
		_print_link(name, "Etiqueta interna (senha)", PF_ETIQUETA_INTERNA),
		_print_link(name, "Termo de retirada", PF_TERMO_RETIRADA),
	]
	if order.get("customer_supplied_part_term_required"):
		links.append(_print_link(name, "Termo de peça do cliente", PF_TERMO_PECA_CLIENTE))
	trade_payment = frappe.db.get_value(
		"Tecponto Service Order Payment",
		{"service_order": name, "payment_kind": "Aparelho como pagamento"},
		"name",
		order_by="creation desc",
	)
	if trade_payment:
		links.append(
			_print_link(
				trade_payment,
				"Termo aparelho como pagamento",
				PF_TERMO_APARELHO_PAGAMENTO,
				doctype="Tecponto Service Order Payment",
			)
		)
	return links


def _print_link(name: str, label: str, print_format: str, *, doctype: str = "Service Order") -> dict[str, str]:
	return {
		"label": label,
		"format": print_format,
		"url": (
			"/printview?"
			f"doctype={quote(doctype)}"
			f"&name={quote(name)}"
			f"&format={quote(print_format)}"
			"&no_letterhead=0"
		),
	}


def _like_filters(query: str, fields: tuple[str, ...]) -> list[list[str]]:
	if not query:
		return []
	return [[field, "like", f"%{query}%"] for field in fields]


def _count_overdue_service_orders(filters: dict[str, Any] | None = None) -> int:
	return len(stage_clock.list_overdue_service_order_names(filters=filters))


def _with_service_order_scope(filters: dict[str, Any] | None = None) -> dict[str, Any]:
	"""Apply explicit scope before aggregate queries bypass Frappe's query hook."""
	return {**(filters or {}), **service_order_scope_filters()}


def contains_sensitive_field(payload: Any, forbidden_values: list[float] | tuple[float, ...] | set[float] | None = None) -> list[str]:
	found: set[str] = set()
	# Feature switches are not payroll values. Keep this list deliberately tiny:
	# every amount or record containing commission remains sensitive.
	non_sensitive_feature_flags = {"technician_commissions_enabled"}
	forbidden_amounts = {round(flt(value), 4) for value in (forbidden_values or []) if abs(flt(value)) > 0.0001}

	def matches_forbidden_amount(value: Any) -> bool:
		if not forbidden_amounts or isinstance(value, bool):
			return False
		if isinstance(value, (int, float)):
			return round(flt(value), 4) in forbidden_amounts
		if isinstance(value, str):
			candidates = re.findall(r"-?(?:\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)", value)
			for candidate in candidates:
				normalized = candidate.replace(".", "").replace(",", ".") if "," in candidate else candidate
				if round(flt(normalized), 4) in forbidden_amounts:
					return True
			return False
		return False

	def walk(value: Any, path: str = "") -> None:
		if isinstance(value, dict):
			for key, nested in value.items():
				normalized = key.lower()
				if normalized in non_sensitive_feature_flags and isinstance(nested, bool):
					continue
				if normalized in SENSITIVE_FIELD_NAMES:
					found.add(key)
				if "cost" in normalized or "margin" in normalized or "commission" in normalized:
					found.add(key)
				child_path = f"{path}.{key}" if path else str(key)
				walk(nested, child_path)
		elif isinstance(value, (list, tuple)):
			for index, nested in enumerate(value):
				walk(nested, f"{path}[{index}]")
		elif matches_forbidden_amount(value):
			found.add(path or "<root>")

	walk(payload)
	return sorted(found)
from tecponto_app.tecponto import product_categories
from tecponto_app.tecponto import product_variants
from tecponto_app.tecponto import listing_metadata


def _require_product_category_editor() -> None:
	_require_frontend_role()
	product_categories.require_category_editor()


@frappe.whitelist()
def list_product_categories() -> dict[str, Any]:
	"""Native Item Group hierarchy, projected without stock cost or margin data."""
	_require_frontend_role()
	return {"items": product_categories.category_tree()}


@frappe.whitelist()
def save_product_category(
	name: str,
	parent: str,
	is_group: int | bool = 0,
	sell_online: int | bool = 0,
	active: int | bool = 1,
	original_name: str | None = None,
) -> dict[str, Any]:
	"""Create, rename, move or inactivate an Item Group after role validation."""
	_require_product_category_editor()
	return {
		"item": product_categories.save_category(
			name=name,
			parent=parent,
			is_group=bool(cint(is_group)),
			sell_online=bool(cint(sell_online)),
			active=bool(cint(active)),
			original_name=original_name,
		)
	}


@frappe.whitelist()
def list_product_variant_attributes() -> dict[str, Any]:
	_require_frontend_role()
	return {"items": product_variants.list_product_variant_attributes()}


@frappe.whitelist()
def save_product_variant_attribute(name: str, values: str | list[dict[str, Any]] | None = None, disabled: int | bool = 0, replace_values: int | bool = 0) -> dict[str, Any]:
	_require_product_category_editor()
	parsed_values = frappe.parse_json(values) if isinstance(values, str) else values
	return {"item": product_variants.save_product_variant_attribute(name, parsed_values or [], bool(cint(disabled)), bool(cint(replace_values)))}


@frappe.whitelist()
def create_product_with_variants(payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_product_category_editor()
	data = frappe.parse_json(payload) if isinstance(payload, str) else payload
	if not isinstance(data, dict):
		frappe.throw(_("Dados do produto com variações não informados."), frappe.ValidationError)
	return product_variants.create_product_with_variants(data)


@frappe.whitelist()
def list_variant_products(limit: int = 50) -> dict[str, Any]:
	_require_frontend_role()
	return {"items": product_variants.list_variant_products(limit)}


@frappe.whitelist()
def list_commercial_catalog(kind: str = "all", limit: int = 100) -> dict[str, Any]:
	"""Public-sale catalogue only; never serializes cost, margin or valuation."""
	_require_frontend_role()
	return {"items": listing_metadata.list_commercial_catalog(kind, limit)}


@frappe.whitelist()
def save_listing_metadata(item_code: str, payload: str | dict[str, Any] | None = None) -> dict[str, Any]:
	_require_product_category_editor()
	data = frappe.parse_json(payload) if isinstance(payload, str) else payload
	if not isinstance(data, dict):
		frappe.throw(_("Dados de anúncio não informados."), frappe.ValidationError)
	return {"item": listing_metadata.save_listing_metadata(item_code, data)}
