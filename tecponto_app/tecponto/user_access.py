"""Account-level security for native Frappe users.

Business roles remain native Frappe roles.  This module adds only the narrow
account-administration guardrail required by Tecponto: one protected owner,
System Managers as account administrators, and an immutable access audit.
"""

from __future__ import annotations

import json
from contextlib import contextmanager

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import now_datetime


OWNER_FIELD = "access_owner_user"
SYSTEM_MANAGER_ROLE = "System Manager"
BUSINESS_ROLES = {
	"Tecponto Atendente",
	"Tecponto Tecnico",
	"Tecponto Gestor",
	"Tecponto Diretor",
}
MANAGED_ROLES = BUSINESS_ROLES | {SYSTEM_MANAGER_ROLE}
AUDIT_DOCTYPE = "Tecponto Access Audit"
INDIVIDUAL_DISCOUNT_LIMIT_FIELD = "custom_tecponto_discount_limit"


def ensure_access_control() -> str:
	"""Assign the one initial owner once, then ensure its required roles.

	Fresh installations use Administrator as the accountable bootstrap account.
	Existing installations with a configured owner are never silently reassigned.
	A later ownership transfer is an explicit, audited 3.15-3 action.
	"""
	ensure_user_access_fields()
	if not frappe.db.exists("DocType", "Tecponto Settings"):
		return ""

	settings = frappe.get_single("Tecponto Settings")
	owner = settings.get(OWNER_FIELD)
	if not owner:
		owner = "Administrator" if frappe.db.exists("User", "Administrator") else _first_enabled_admin()
		if not owner:
			frappe.throw("Defina um Administrador do Sistema antes de inicializar o controle de acessos.")
		set_initial_owner(owner)

	with _bootstrap_context():
		owner_doc = frappe.get_doc("User", owner)
		owner_doc.add_roles(*sorted(MANAGED_ROLES))
	frappe.clear_cache(user=owner)

	return owner


def ensure_user_access_fields() -> None:
	"""Keep the per-person commercial limit on the native User record."""
	if not frappe.db.exists("DocType", "User"):
		return
	create_custom_fields(
		{
			"User": [
				{
					"fieldname": INDIVIDUAL_DISCOUNT_LIMIT_FIELD,
					"fieldtype": "Currency",
					"label": "Limite individual de desconto",
					"description": "Quando preenchido, substitui o limite geral para este usuário.",
					"insert_after": "mobile_no",
					"module": "Tecponto",
				}
			]
		},
		update=True,
	)


def set_initial_owner(user: str) -> str:
	"""Set the first owner once; this is not a transfer mechanism."""
	user = (user or "").strip()
	if not user or not frappe.db.exists("User", user):
		frappe.throw("Informe uma conta existente para o Proprietário.")
	settings = frappe.get_single("Tecponto Settings")
	existing = (settings.get(OWNER_FIELD) or "").strip()
	if existing:
		frappe.throw("Já existe uma conta Proprietário. Use o fluxo auditado de transferência.", frappe.ValidationError)
	with _bootstrap_context():
		settings.set(OWNER_FIELD, user)
		settings.save(ignore_permissions=True)
	_write_audit(
		affected_user=user,
		change_type="Proprietário inicial definido",
		before={"account_level": ""},
		after={"account_level": "Proprietário"},
	)
	return user


def get_owner_user() -> str:
	if not frappe.db.exists("DocType", "Tecponto Settings"):
		return ""
	return (frappe.db.get_single_value("Tecponto Settings", OWNER_FIELD) or "").strip()


def get_account_level(user: str) -> str:
	if user and user == get_owner_user():
		return "Proprietário"
	if user and SYSTEM_MANAGER_ROLE in _user_roles(user):
		return "Administrador do Sistema"
	return "Usuário comum"


def validate_user_access(doc, method=None) -> None:
	"""Validate every native User write before Frappe persists it."""
	if _is_bootstrap_context() or _is_employee_user_sync(doc.name):
		return

	actor = frappe.session.user
	if actor == "Guest":
		frappe.throw("Faça login para alterar acessos.", frappe.PermissionError)

	previous = None if doc.is_new() else doc.get_doc_before_save()
	before_roles = _roles(previous)
	after_roles = _roles(doc)
	added_roles = (after_roles - before_roles) & MANAGED_ROLES
	removed_roles = (before_roles - after_roles) & MANAGED_ROLES
	target_is_owner = doc.name == get_owner_user()

	if target_is_owner:
		if actor != doc.name:
			frappe.throw("A conta Proprietário só pode ser editada pelo próprio Proprietário.", frappe.PermissionError)
		if previous and previous.enabled and not doc.enabled:
			frappe.throw("A conta Proprietário não pode ser desativada.", frappe.PermissionError)
		if removed_roles:
			frappe.throw("Os papéis da conta Proprietário não podem ser removidos.", frappe.PermissionError)

	if previous and actor == doc.name and previous.enabled and not doc.enabled:
		frappe.throw("Você não pode desativar a própria conta.", frappe.PermissionError)

	if SYSTEM_MANAGER_ROLE in added_roles and actor != get_owner_user():
		frappe.throw("Somente o Proprietário pode criar Administradores do Sistema.", frappe.PermissionError)
	if "Tecponto Diretor" in added_roles and actor != get_owner_user():
		frappe.throw("Somente o Proprietário pode conceder o papel Diretor.", frappe.PermissionError)

	# Do not rely on Frappe's per-request role cache here. A user can receive a
	# role and immediately use the management screen in the same request flow.
	actor_roles = _user_roles(actor)
	for role in added_roles - {SYSTEM_MANAGER_ROLE, "Tecponto Diretor"}:
		if role not in actor_roles:
			frappe.throw(f"Você não pode conceder o papel {role} porque não o possui.", frappe.PermissionError)

	if previous and _would_remove_last_administrator(doc, previous):
		frappe.throw("Não é possível remover ou desativar o último Administrador do Sistema.", frappe.PermissionError)


def validate_user_deletion(doc, method=None) -> None:
	if _is_bootstrap_context():
		return
	if doc.name == get_owner_user():
		frappe.throw("A conta Proprietário não pode ser excluída.", frappe.PermissionError)
	if _is_active_administrator(doc) and _active_administrator_count() <= 1:
		frappe.throw("Não é possível excluir o último Administrador do Sistema.", frappe.PermissionError)


def validate_owner_setting(doc, method=None) -> None:
	if _is_bootstrap_context() or doc.is_new():
		return
	previous = doc.get_doc_before_save()
	if previous and previous.get(OWNER_FIELD) != doc.get(OWNER_FIELD):
		frappe.throw("A propriedade só pode ser alterada pelo fluxo auditado de transferência.", frappe.PermissionError)


def audit_user_access_change(doc, method=None) -> None:
	if _is_bootstrap_context():
		return
	previous = doc.get_doc_before_save()
	before = _access_snapshot(previous)
	after = _access_snapshot(doc)
	if before == after:
		return
	_write_audit(
		affected_user=doc.name,
		change_type=_change_type(before, after),
		before=before,
		after=after,
	)


def audit_user_creation(doc, method=None) -> None:
	if _is_bootstrap_context():
		return
	_write_audit(
		affected_user=doc.name,
		change_type="Usuário criado",
		before={},
		after=_access_snapshot(doc),
	)


def audit_password_change(affected_user: str, *, creating: bool = False) -> None:
	"""Record credential rotation without ever persisting the credential itself."""
	_write_audit(
		affected_user=affected_user,
		change_type="Senha definida na criação" if creating else "Senha redefinida manualmente",
		before={"credential": "withheld"},
		after={"credential": "changed"},
	)


def validate_access_audit_immutable(doc, method=None) -> None:
	if not doc.is_new():
		frappe.throw("A trilha de auditoria de acesso é imutável.", frappe.PermissionError)


def prevent_access_audit_deletion(doc, method=None) -> None:
	frappe.throw("A trilha de auditoria de acesso não pode ser excluída.", frappe.PermissionError)


def _roles(doc) -> set[str]:
	if not doc:
		return set()
	return {row.role for row in (doc.get("roles") or []) if row.role}


def _access_snapshot(doc) -> dict:
	if not doc:
		return {}
	return {
		"enabled": bool(doc.enabled),
		"roles": sorted(_roles(doc) & MANAGED_ROLES),
		"account_level": get_account_level(doc.name),
	}


def _change_type(before: dict, after: dict) -> str:
	if before.get("enabled") != after.get("enabled"):
		return "Conta ativada" if after.get("enabled") else "Conta desativada"
	if before.get("roles") != after.get("roles"):
		return "Papéis alterados"
	return "Acesso alterado"


def _is_active_administrator(doc) -> bool:
	return bool(doc.enabled and SYSTEM_MANAGER_ROLE in _roles(doc))


def _would_remove_last_administrator(doc, previous) -> bool:
	return _is_active_administrator(previous) and not _is_active_administrator(doc) and _active_administrator_count() <= 1


def _active_administrator_count() -> int:
	return sum(
		1
		for user in frappe.get_all("User", filters={"enabled": 1}, fields=["name"])
		if SYSTEM_MANAGER_ROLE in _user_roles(user.name)
	)


def _first_enabled_admin() -> str:
	for user in frappe.get_all("User", filters={"enabled": 1}, fields=["name"], order_by="creation asc"):
		if SYSTEM_MANAGER_ROLE in _user_roles(user.name):
			return user.name
	return ""


def _write_audit(*, affected_user: str, change_type: str, before: dict, after: dict) -> None:
	if not frappe.db.exists("DocType", AUDIT_DOCTYPE):
		return
	frappe.get_doc(
		{
			"doctype": AUDIT_DOCTYPE,
			"actor": frappe.session.user,
			"affected_user": affected_user,
			"change_type": change_type,
			"before_state": json.dumps(before, ensure_ascii=True, sort_keys=True),
			"after_state": json.dumps(after, ensure_ascii=True, sort_keys=True),
			"occurred_on": now_datetime(),
		}
	).insert(ignore_permissions=True)


def audit_accumulated_role_action(*, role: str, action_type: str, reference_doctype: str, reference_name: str, result: dict) -> None:
	"""Record a direct action executed under an authority the actor truly holds.

	The audit does not grant access and is written only after the ordinary action
	has revalidated every business rule under the real session user.
	"""
	_write_audit(
		affected_user=frappe.session.user,
		change_type="Ação sob papel acumulado",
		before={
			"action_type": action_type,
			"authority_role": role,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
		},
		after={"result": result},
	)


def _user_roles(user: str) -> set[str]:
	"""Read persisted roles so access guards cannot lag behind a cache refresh."""
	if not user:
		return set()
	return {
		row.role
		for row in frappe.get_all(
			"Has Role",
			filters={"parent": user, "parenttype": "User", "parentfield": "roles"},
			fields=["role"],
		)
		if row.role
	}


@contextmanager
def _bootstrap_context():
	previous = frappe.flags.get("tecponto_access_control_bootstrap")
	frappe.flags.tecponto_access_control_bootstrap = True
	try:
		yield
	finally:
		frappe.flags.tecponto_access_control_bootstrap = previous


def _is_bootstrap_context() -> bool:
	return bool(frappe.flags.get("tecponto_access_control_bootstrap"))


@contextmanager
def employee_user_sync_context(user: str):
	"""Allow ERPNext's Employee hook to update only its linked User.

	ERPNext persists a User while creating an Employee. This is not an account
	administration action and must not make bootstrap or HR provisioning fail,
	but it must also never become a broad bypass for native User edits.
	"""
	previous = frappe.flags.get("tecponto_employee_user_sync")
	frappe.flags.tecponto_employee_user_sync = user
	try:
		yield
	finally:
		frappe.flags.tecponto_employee_user_sync = previous


def _is_employee_user_sync(user: str) -> bool:
	return bool(user and frappe.flags.get("tecponto_employee_user_sync") == user)
