from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import flt


SERVICE_DOCTYPE = "Tecponto Service"
DEVICE_TYPE_DOCTYPE = "Tecponto Device Type"
CATEGORY_DOCTYPE = "Tecponto Service Category"

DEVICE_TYPES = ("Celular", "Tablet", "Notebook", "Smartwatch", "Outros")
CATEGORIES = ("Tela", "Bateria", "Carga", "Áudio", "Câmera", "Botões", "Placa", "Software", "Danos", "Diagnóstico")

# Prices deliberately begin unset. The catalog suggests information; no seed can
# turn a missing commercial decision into a blocker for a service order.
SERVICE_SEED = (
	("Tela", "Troca de tela", "Celular", 8, "Horas", "Baixa", 1),
	("Tela", "Troca de vidro (laminação)", "Celular", 2, "Dias úteis", "Média", 1),
	("Bateria", "Troca de bateria", "Celular", 8, "Horas", "Baixa", 1),
	("Carga", "Troca de conector de carga", "Celular", 1, "Dias úteis", "Baixa", 1),
	("Áudio", "Troca de alto-falante/auricular", "Celular", 8, "Horas", "Baixa", 1),
	("Câmera", "Troca de câmera", "Celular", 1, "Dias úteis", "Média", 1),
	("Botões", "Botão power/volume", "Celular", 1, "Dias úteis", "Média", 1),
	("Placa", "Reparo de placa (micro-solda)", "Celular", 7, "Dias úteis", "Alta", 1),
	("Placa", "Não liga / curto", "Celular", 7, "Dias úteis", "Alta", 1),
	("Software", "Formatação/atualização/desbloqueio", "Celular", 8, "Horas", "Baixa", 0),
	("Software", "Recuperação de dados", "Celular", 5, "Dias úteis", "Alta", 0),
	("Danos", "Aparelho molhado (oxidação)", "Celular", 5, "Dias úteis", "Alta", 1),
	("Diagnóstico", "Diagnóstico", "Celular", 48, "Horas", "", 0),
	("Tela", "Troca de tela", "Tablet", 1, "Dias úteis", "Média", 1),
	("Bateria", "Troca de bateria", "Tablet", 1, "Dias úteis", "Baixa", 1),
	("Carga", "Troca de conector de carga", "Tablet", 2, "Dias úteis", "Média", 1),
	("Software", "Formatação/atualização", "Tablet", 1, "Dias úteis", "Baixa", 0),
	("Diagnóstico", "Diagnóstico", "Tablet", 48, "Horas", "", 0),
	("Tela", "Troca de tela", "Notebook", 3, "Dias úteis", "Alta", 1),
	("Bateria", "Troca de bateria", "Notebook", 2, "Dias úteis", "Média", 1),
	("Carga", "Reparo de conector de carga", "Notebook", 3, "Dias úteis", "Alta", 1),
	("Software", "Formatação/atualização", "Notebook", 1, "Dias úteis", "Baixa", 0),
	("Diagnóstico", "Diagnóstico", "Notebook", 48, "Horas", "", 0),
)


def ensure_service_catalog() -> None:
	"""Idempotently install a useful, editable service catalog."""
	for name in DEVICE_TYPES:
		_ensure_reference(DEVICE_TYPE_DOCTYPE, "type_name", name)
	for name in CATEGORIES:
		_ensure_reference(CATEGORY_DOCTYPE, "category_name", name)
	for category, service_name, device_type, duration, duration_unit, complexity, requires_part in SERVICE_SEED:
		if frappe.db.exists(SERVICE_DOCTYPE, {"service_name": service_name, "device_type": device_type}):
			continue
		frappe.get_doc(
			{
				"doctype": SERVICE_DOCTYPE,
				"service_name": service_name,
				"device_type": device_type,
				"category": category,
				"default_labor_price": 0,
				"default_duration": duration,
				"duration_unit": duration_unit,
				"requires_part": requires_part,
				"complexity": complexity,
				"active": 1,
			}
		).insert(ignore_permissions=True)


def list_services(query: str = "", device_type: str = "", category: str = "", include_inactive: bool = False) -> dict[str, Any]:
	filters: dict[str, Any] = {}
	if not include_inactive:
		filters["active"] = 1
	if device_type:
		filters["device_type"] = device_type
	if category:
		filters["category"] = category
	if query:
		filters["service_name"] = ["like", f"%{query.strip()}%"]
	rows = frappe.get_all(
		SERVICE_DOCTYPE,
		filters=filters,
		fields=["name", "service_name", "device_type", "category", "default_labor_price", "default_duration", "duration_unit", "requires_part", "complexity", "active", "modified"],
		order_by="active desc, service_name asc",
		limit_page_length=200,
	)
	return {"items": [_serialize_service(row) for row in rows], "count": len(rows)}


def list_references(include_inactive: bool = True) -> dict[str, list[dict[str, Any]]]:
	return {
		"device_types": _list_reference(DEVICE_TYPE_DOCTYPE, "type_name", include_inactive),
		"categories": _list_reference(CATEGORY_DOCTYPE, "category_name", include_inactive),
	}


def save_service(payload: dict[str, Any]) -> dict[str, Any]:
	name = (payload.get("name") or "").strip()
	service_name = (payload.get("service_name") or "").strip()
	device_type = (payload.get("device_type") or "").strip()
	category = (payload.get("category") or "").strip()
	if not service_name or not device_type or not category:
		frappe.throw(_("Informe serviço, tipo de aparelho e categoria."), frappe.ValidationError)
	_validate_active_reference(DEVICE_TYPE_DOCTYPE, device_type, "tipo de aparelho")
	_validate_active_reference(CATEGORY_DOCTYPE, category, "categoria")
	doc = frappe.get_doc(SERVICE_DOCTYPE, name) if name else frappe.new_doc(SERVICE_DOCTYPE)
	doc.update(
		{
			"service_name": service_name,
			"device_type": device_type,
			"category": category,
			"default_labor_price": max(0, flt(payload.get("default_labor_price"))),
			"default_duration": max(0, flt(payload.get("default_duration"))),
			"duration_unit": (payload.get("duration_unit") or "Horas").strip(),
			"requires_part": 1 if payload.get("requires_part") else 0,
			"complexity": (payload.get("complexity") or "").strip(),
			"active": 1 if payload.get("active", True) else 0,
		}
	)
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	return _serialize_service(doc.as_dict())


def save_reference(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
	doctype, fieldname = _reference_definition(kind)
	name = (payload.get("name") or "").strip()
	value = (payload.get("value") or "").strip()
	if not value:
		frappe.throw(_("Informe um nome."), frappe.ValidationError)
	if name and name != value:
		# These references intentionally use their label as the document name. Use
		# Frappe's rename flow so every Link (including existing catalog services)
		# follows the edited label instead of silently keeping a stale identifier.
		frappe.rename_doc(doctype, name, value, force=True)
		name = value
	doc = frappe.get_doc(doctype, name) if name else frappe.new_doc(doctype)
	doc.update({fieldname: value, "active": 1 if payload.get("active", True) else 0})
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	return _serialize_reference(doc.as_dict(), fieldname)


def _ensure_reference(doctype: str, fieldname: str, value: str) -> None:
	if not frappe.db.exists(doctype, {fieldname: value}):
		frappe.get_doc({"doctype": doctype, fieldname: value, "active": 1}).insert(ignore_permissions=True)


def _list_reference(doctype: str, fieldname: str, include_inactive: bool) -> list[dict[str, Any]]:
	filters = {} if include_inactive else {"active": 1}
	rows = frappe.get_all(doctype, filters=filters, fields=["name", fieldname, "active", "modified"], order_by=f"active desc, {fieldname} asc")
	return [_serialize_reference(row, fieldname) for row in rows]


def _reference_definition(kind: str) -> tuple[str, str]:
	if kind == "device_type":
		return DEVICE_TYPE_DOCTYPE, "type_name"
	if kind == "category":
		return CATEGORY_DOCTYPE, "category_name"
	frappe.throw(_("Referência de catálogo inválida."), frappe.ValidationError)


def _validate_active_reference(doctype: str, name: str, label: str) -> None:
	if not frappe.db.exists(doctype, {"name": name, "active": 1}):
		frappe.throw(_("Selecione uma {0} ativa.").format(label), frappe.ValidationError)


def _serialize_service(row: dict[str, Any]) -> dict[str, Any]:
	device_type = row.get("device_type")
	category = row.get("category")
	return {
		"name": row.get("name"),
		"service_name": row.get("service_name"),
		"device_type": device_type,
		"device_type_label": frappe.db.get_value(DEVICE_TYPE_DOCTYPE, device_type, "type_name") or device_type,
		"category": category,
		"category_label": frappe.db.get_value(CATEGORY_DOCTYPE, category, "category_name") or category,
		"default_labor_price": flt(row.get("default_labor_price")),
		"default_duration": flt(row.get("default_duration")),
		"duration_unit": row.get("duration_unit"),
		"requires_part": bool(row.get("requires_part")),
		"complexity": row.get("complexity") or None,
		"active": bool(row.get("active")),
		"modified": str(row.get("modified") or ""),
	}


def _serialize_reference(row: dict[str, Any], fieldname: str) -> dict[str, Any]:
	return {"name": row.get("name"), "value": row.get(fieldname), "active": bool(row.get("active")), "modified": str(row.get("modified") or "")}
