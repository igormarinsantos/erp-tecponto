from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


PRODUCT_GROUP_ROOT = "Produtos de Varejo"
ACCESSORIES_GROUP = "Acessórios"
DEVICES_GROUP = "Aparelhos"
REPAIR_PARTS_GROUP = "Peças de Reparo"
USED_DEVICES_GROUP = "Aparelhos Usados"
SELL_ONLINE_FIELD = "custom_tecponto_sell_online"
ACTIVE_FIELD = "custom_tecponto_category_active"
SEEDED_FIELD = "custom_tecponto_marketplace_seeded"

CATEGORY_EDITOR_ROLES = {"System Manager", "Tecponto Gestor", "Tecponto Diretor"}

ITEM_GROUP_FIELDS = {
	"Item Group": [
		{
			"fieldname": ACTIVE_FIELD,
			"fieldtype": "Check",
			"label": "Categoria ativa",
			"default": "1",
			"insert_after": "is_group",
			"module": "Tecponto",
		},
		{
			"fieldname": SELL_ONLINE_FIELD,
			"fieldtype": "Check",
			"label": "Vendável online",
			"description": "Permite usar esta categoria em canais de venda online.",
			"insert_after": ACTIVE_FIELD,
			"module": "Tecponto",
		},
		{
			"fieldname": SEEDED_FIELD,
			"fieldtype": "Check",
			"label": "Semente de marketplace aplicada",
			"hidden": 1,
			"read_only": 1,
			"module": "Tecponto",
		},
	]
}


def ensure_product_category_foundation() -> None:
	"""Seed the native Item Group hierarchy without overwriting manager edits."""
	create_custom_fields(ITEM_GROUP_FIELDS, update=True)
	frappe.clear_cache(doctype="Item Group")
	seed_defaults = not frappe.db.get_value("Item Group", PRODUCT_GROUP_ROOT, SEEDED_FIELD)

	_ensure_category(PRODUCT_GROUP_ROOT, parent="All Item Groups", is_group=1, sell_online=1, seed_defaults=seed_defaults)
	_ensure_category(ACCESSORIES_GROUP, parent=PRODUCT_GROUP_ROOT, is_group=1, sell_online=1, seed_defaults=seed_defaults)
	for category in ("Capas", "Películas", "Carregadores", "Cabos", "Fones", "Suportes", "Caixas de som"):
		_ensure_category(category, parent=ACCESSORIES_GROUP, is_group=0, sell_online=1, seed_defaults=seed_defaults)
	_ensure_category(DEVICES_GROUP, parent=PRODUCT_GROUP_ROOT, is_group=1, sell_online=1, seed_defaults=seed_defaults)
	_ensure_category("Novos", parent=DEVICES_GROUP, is_group=0, sell_online=1, seed_defaults=seed_defaults)
	_ensure_category(USED_DEVICES_GROUP, parent=DEVICES_GROUP, is_group=0, sell_online=1, seed_defaults=seed_defaults)
	_ensure_category(REPAIR_PARTS_GROUP, parent="All Item Groups", is_group=1, sell_online=0, seed_defaults=seed_defaults)
	if seed_defaults:
		root = frappe.get_doc("Item Group", PRODUCT_GROUP_ROOT)
		root.set(SEEDED_FIELD, 1)
		root.save(ignore_permissions=True)


def _ensure_category(name: str, *, parent: str, is_group: int, sell_online: int, seed_defaults: bool) -> None:
	if frappe.db.exists("Item Group", name):
		doc = frappe.get_doc("Item Group", name)
		# The default hierarchy is only adjusted for the named seed nodes. All
		# manager-created descendants remain untouched on later migrations.
		if doc.parent_item_group != parent:
			doc.parent_item_group = parent
		if not doc.get(ACTIVE_FIELD):
			doc.set(ACTIVE_FIELD, 1)
		if seed_defaults or doc.get(SELL_ONLINE_FIELD) is None:
			doc.set(SELL_ONLINE_FIELD, sell_online)
		if name == REPAIR_PARTS_GROUP:
			doc.set(SELL_ONLINE_FIELD, 0)
		doc.save(ignore_permissions=True)
		return

	frappe.get_doc(
		{
			"doctype": "Item Group",
			"item_group_name": name,
			"parent_item_group": parent,
			"is_group": is_group,
			ACTIVE_FIELD: 1,
			SELL_ONLINE_FIELD: sell_online,
		}
	).insert(ignore_permissions=True)


def require_category_editor() -> None:
	roles = set(frappe.get_roles(frappe.session.user))
	if roles.intersection(CATEGORY_EDITOR_ROLES):
		return
	frappe.throw(_("Somente Gestor ou Diretor pode editar categorias de produto."), frappe.PermissionError)


def category_tree() -> list[dict[str, Any]]:
	"""Return native Item Groups only, with Tecponto's two operational flags."""
	fields = ["name", "parent_item_group", "is_group", ACTIVE_FIELD, SELL_ONLINE_FIELD, "lft", "rgt"]
	rows = frappe.get_all("Item Group", fields=fields, order_by="lft asc", limit_page_length=0)
	children: dict[str, list[dict[str, Any]]] = {}
	by_name: dict[str, dict[str, Any]] = {}
	for row in rows:
		entry = {
			"name": row.name,
			"parent": row.parent_item_group,
			"is_group": bool(row.is_group),
			"active": bool(row.get(ACTIVE_FIELD)),
			"sell_online": bool(row.get(SELL_ONLINE_FIELD)),
			"children": [],
		}
		by_name[row.name] = entry
		children.setdefault(row.parent_item_group or "", []).append(entry)
	for entry in by_name.values():
		entry["children"] = children.get(entry["name"], [])
	# The ERPNext defaults stay untouched, but the Tecponto screen intentionally
	# presents only the two business branches it operates.
	return [by_name[name] for name in (PRODUCT_GROUP_ROOT, REPAIR_PARTS_GROUP) if name in by_name]


def save_category(
	*,
	name: str,
	parent: str,
	is_group: bool,
	sell_online: bool,
	active: bool,
	original_name: str | None = None,
) -> dict[str, Any]:
	require_category_editor()
	name = (name or "").strip()[:140]
	parent = (parent or "").strip()
	if not name or not parent:
		frappe.throw(_("Nome e categoria pai são obrigatórios."), frappe.ValidationError)
	if parent == name or not frappe.db.exists("Item Group", parent):
		frappe.throw(_("Selecione uma categoria pai válida."), frappe.ValidationError)
	if original_name and frappe.db.exists("Item Group", original_name):
		doc = frappe.get_doc("Item Group", original_name)
		if original_name == "All Item Groups":
			frappe.throw(_("A raiz do catálogo não pode ser alterada."), frappe.PermissionError)
		if name != original_name:
			frappe.rename_doc("Item Group", original_name, name, force=True, ignore_permissions=True)
			doc = frappe.get_doc("Item Group", name)
	else:
		if frappe.db.exists("Item Group", name):
			frappe.throw(_("Já existe uma categoria com este nome."), frappe.ValidationError)
		doc = frappe.new_doc("Item Group")
		doc.item_group_name = name

	# A category cannot be moved below itself or one of its descendants.
	if not doc.is_new() and _is_descendant(parent, doc.name):
		frappe.throw(_("Não é possível mover uma categoria para dentro dela mesma."), frappe.ValidationError)
	if not is_group and frappe.db.exists("Item Group", {"parent_item_group": doc.name}):
		frappe.throw(_("Uma categoria com subcategorias deve continuar sendo um grupo."), frappe.ValidationError)
	doc.parent_item_group = parent
	doc.is_group = int(bool(is_group))
	doc.set(ACTIVE_FIELD, int(bool(active)))
	doc.set(SELL_ONLINE_FIELD, int(bool(sell_online)) if name != REPAIR_PARTS_GROUP else 0)
	doc.save(ignore_permissions=True)
	frappe.clear_cache(doctype="Item Group")
	return next((item for item in _flatten(category_tree()) if item["name"] == doc.name), {"name": doc.name})


def _is_descendant(candidate: str, ancestor: str) -> bool:
	bounds = frappe.db.get_value("Item Group", ancestor, ["lft", "rgt"], as_dict=True)
	candidate_bounds = frappe.db.get_value("Item Group", candidate, ["lft", "rgt"], as_dict=True)
	return bool(bounds and candidate_bounds and bounds.lft <= candidate_bounds.lft <= bounds.rgt)


def _flatten(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
	flat: list[dict[str, Any]] = []
	for item in items:
		flat.append(item)
		flat.extend(_flatten(item["children"]))
	return flat
