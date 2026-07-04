from __future__ import annotations

import unicodedata

import frappe
from frappe.utils import flt


MANAGER_ROLES = {"Tecponto Gestor", "System Manager"}
APPROVED_STATES = {
	"Aprovado",
	"Aprovado para compra",
	"Compra aprovada",
	"Comprado",
	"Confirmada",
}

IPHONE_CHECKLIST = (
	("Bateria %", "Informar percentual"),
	("Face ID/Touch ID", "OK"),
	("iCloud limpo", "Sim"),
	("Tela original", "OK"),
	("Chip/eSIM", "OK"),
	("Estetica A/B/C", "Classificar"),
)

ANDROID_CHECKLIST = (
	("Conta Google limpa", "Sim"),
	("Root", "Ausente"),
	("Tela", "OK"),
	("Chip/eSIM", "OK"),
	("Estetica A/B/C", "Classificar"),
)

BLOCKING_ITEM_MARKERS = ("icloud", "conta google")
BLOCKING_RESULTS = {"atencao", "reprovado"}


def validar_avaliacao(doc, method=None) -> None:
	_sync_checklist(doc)
	_validate_blocked_device(doc)
	_validate_approved_value_range(doc)


def _sync_checklist(doc) -> None:
	expected_rows = _expected_checklist(doc.get("device_type"))
	if not expected_rows:
		return

	existing_items = {
		_normalize(row.get("check_item"))
		for row in doc.get("checklist") or []
		if row.get("check_item")
	}

	for check_item, expected_value in expected_rows:
		if _normalize(check_item) in existing_items:
			continue

		doc.append(
			"checklist",
			{
				"check_item": check_item,
				"expected_value": expected_value,
			},
		)


def _expected_checklist(device_type: str | None) -> tuple[tuple[str, str], ...]:
	if device_type == "iPhone":
		return IPHONE_CHECKLIST
	if device_type == "Android":
		return ANDROID_CHECKLIST
	return ()


def _validate_blocked_device(doc) -> None:
	if not _is_approval_attempt(doc):
		return

	if doc.get("icloud_google_lock") or _has_blocking_checklist_result(doc):
		frappe.throw("Aparelho com bloqueio iCloud/Google nao pode ser aprovado para troca.")


def _has_blocking_checklist_result(doc) -> bool:
	for row in doc.get("checklist") or []:
		item = _normalize(row.get("check_item"))
		result = _normalize(row.get("result"))
		if any(marker in item for marker in BLOCKING_ITEM_MARKERS) and result in BLOCKING_RESULTS:
			return True

	return False


def _validate_approved_value_range(doc) -> None:
	approved_value = flt(doc.get("approved_value"))
	if not approved_value:
		return

	table_min = flt(doc.get("table_min"))
	table_max = flt(doc.get("table_max"))

	if table_min and approved_value < table_min:
		frappe.throw("Valor aprovado abaixo do minimo da tabela.")

	if not table_max or approved_value <= table_max:
		return

	if _over_max_requires_manager() and not _user_is_manager():
		frappe.throw("Valor aprovado acima do maximo da tabela exige Gestor.")


def _over_max_requires_manager() -> bool:
	return bool(frappe.db.get_single_value("Tecponto Settings", "tradein_over_max_needs_manager"))


def _is_approval_attempt(doc) -> bool:
	return doc.get("workflow_state") in APPROVED_STATES or bool(doc.get("approved_value"))


def _user_is_manager() -> bool:
	if frappe.session.user == "Administrator":
		return True

	return bool(set(frappe.get_roles()) & MANAGER_ROLES)


def _normalize(value: str | None) -> str:
	normalized = unicodedata.normalize("NFKD", value or "")
	return "".join(char for char in normalized if not unicodedata.combining(char)).strip().lower()
