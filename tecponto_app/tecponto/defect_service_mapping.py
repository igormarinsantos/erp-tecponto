from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import flt


MAPPING_DOCTYPE = "Tecponto Defect Service Mapping"
SERVICE_DOCTYPE = "Tecponto Service"

# These are deliberately suggestions, never a diagnosis. A defect without a
# clear repair path stays unmapped and cannot prevent the check-in from opening.
DEFAULT_MAPPINGS = (
	("N\u00e3o liga", "N\u00e3o liga / curto"),
	("N\u00e3o carrega", "Troca de conector de carga"),
	("Carrega intermitente", "Troca de conector de carga"),
	("Aquece", "Reparo de placa (micro-solda)"),
	("Tela quebrada", "Troca de tela"),
	("Tela sem imagem", "Troca de tela"),
	("Touch falhando", "Troca de tela"),
	("Sem audio", "Troca de alto-falante/auricular"),
	("C\u00e2mera falhando", "Troca de c\u00e2mera"),
	("Molhou", "Aparelho molhado (oxida\u00e7\u00e3o)"),
	("Bateria descarregando r\u00e1pido", "Troca de bateria"),
	("Conector com mau contato", "Troca de conector de carga"),
	("Lentid\u00e3o/travamento", "Formata\u00e7\u00e3o/atualiza\u00e7\u00e3o/desbloqueio"),
)


def ensure_defect_service_mappings() -> None:
	"""Seed editable defaults only when the matching catalog service exists."""
	for defect, service_name in DEFAULT_MAPPINGS:
		if frappe.db.exists(MAPPING_DOCTYPE, {"defect": defect}):
			continue
		service = frappe.db.get_value(
			SERVICE_DOCTYPE,
			{"service_name": service_name, "device_type": "Celular", "active": 1},
			"name",
		)
		if not service:
			continue
		frappe.get_doc(
			{
				"doctype": MAPPING_DOCTYPE,
				"defect": defect,
				"catalog_service": service,
				"active": 1,
			}
		).insert(ignore_permissions=True)


def list_mappings(include_inactive: bool = True) -> dict[str, Any]:
	ensure_defect_service_mappings()
	filters = {} if include_inactive else {"active": 1}
	rows = frappe.get_all(
		MAPPING_DOCTYPE,
		filters=filters,
		fields=["name", "defect", "catalog_service", "active", "modified"],
		order_by="defect asc",
	)
	return {"items": [_serialize_mapping(row) for row in rows]}


def save_mapping(payload: dict[str, Any]) -> dict[str, Any]:
	name = (payload.get("name") or "").strip()
	defect = (payload.get("defect") or "").strip()
	catalog_service = (payload.get("catalog_service") or "").strip()
	if not defect or not catalog_service:
		frappe.throw(_("Informe o defeito e o servico do catalogo."), frappe.ValidationError)
	service = frappe.db.get_value(
		SERVICE_DOCTYPE,
		catalog_service,
		["name", "active"],
		as_dict=True,
	)
	if not service:
		frappe.throw(_("Servico do catalogo nao encontrado."), frappe.ValidationError)
	if name:
		doc = frappe.get_doc(MAPPING_DOCTYPE, name)
	else:
		existing = frappe.db.get_value(MAPPING_DOCTYPE, {"defect": defect}, "name")
		doc = frappe.get_doc(MAPPING_DOCTYPE, existing) if existing else frappe.new_doc(MAPPING_DOCTYPE)
	doc.update(
		{
			"defect": defect,
			"catalog_service": service.name,
			"active": 1 if payload.get("active", True) else 0,
		}
	)
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)
	return _serialize_mapping(doc.as_dict())


def resolve_services(defects: list[str] | tuple[str, ...] | None) -> list[dict[str, Any]]:
	"""Resolve unique, active catalog services in selected-defect order."""
	clean_defects = _clean_defects(defects)
	if not clean_defects:
		return []
	ensure_defect_service_mappings()
	mappings = frappe.get_all(
		MAPPING_DOCTYPE,
		filters={"defect": ["in", clean_defects], "active": 1},
		fields=["defect", "catalog_service"],
	)
	by_defect = {row.defect: row.catalog_service for row in mappings}
	service_names = list(dict.fromkeys(by_defect.get(defect) for defect in clean_defects if by_defect.get(defect)))
	if not service_names:
		return []
	services = frappe.get_all(
		SERVICE_DOCTYPE,
		filters={"name": ["in", service_names], "active": 1},
		fields=["name", "service_name", "default_labor_price", "default_duration", "duration_unit", "active"],
	)
	by_name = {row.name: row for row in services}
	return [_serialize_service(by_name[name]) for name in service_names if name in by_name]


def calculate_delivery_suggestion(
	defects: list[str] | tuple[str, ...] | None,
	start_datetime=None,
	lead_time_business_hours: float = 0,
) -> dict[str, Any]:
	"""Return no date until a mapped service gives the estimate a real basis."""
	from tecponto_app.tecponto.service_order import stage_sla

	services = resolve_services(defects)
	if not services:
		return {
			"suggested_delivery_date": "",
			"total_business_hours": 0,
			"stage_business_hours": 0,
			"service_business_hours": 0,
			"lead_time_business_hours": max(0, flt(lead_time_business_hours)),
			"mapped_services": [],
			"has_estimate": False,
		}
	service_hours = sum(
		stage_sla._duration_as_business_hours(service["default_duration"], service["duration_unit"])
		for service in services
	)
	result = stage_sla.calculate_suggested_delivery(
		start_datetime=start_datetime,
		service_duration=service_hours,
		service_duration_unit="Horas",
		lead_time_business_hours=lead_time_business_hours,
	)
	return {**result, "mapped_services": services, "has_estimate": bool(result["suggested_delivery_date"])}


def _clean_defects(defects: list[str] | tuple[str, ...] | None) -> list[str]:
	return list(dict.fromkeys((value or "").strip() for value in (defects or []) if (value or "").strip()))


def _serialize_mapping(row: dict[str, Any]) -> dict[str, Any]:
	service = frappe.db.get_value(SERVICE_DOCTYPE, row.get("catalog_service"), "service_name")
	return {
		"name": row.get("name"),
		"defect": row.get("defect"),
		"catalog_service": row.get("catalog_service"),
		"catalog_service_label": service or row.get("catalog_service"),
		"active": bool(row.get("active")),
		"modified": str(row.get("modified") or ""),
	}


def _serialize_service(row: Any) -> dict[str, Any]:
	return {
		"name": row.get("name"),
		"service_name": row.get("service_name"),
		"default_labor_price": flt(row.get("default_labor_price")),
		"default_duration": flt(row.get("default_duration")),
		"duration_unit": row.get("duration_unit") or "Horas",
	}
