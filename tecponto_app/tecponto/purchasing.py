import frappe
from frappe.utils import flt


REPAIR_ITEM_GROUP = "Peças de Reparo"
RETAIL_ITEM_GROUP = "Produtos de Varejo"
MANAGER_ROLES = {"Tecponto Gestor", "System Manager"}


def apply_buying_warehouse_defaults(doc, method=None) -> None:
	for item in doc.get("items") or []:
		if item.get("warehouse") or not item.get("item_code"):
			continue

		warehouse = _warehouse_for_item(item.get("item_code"))
		if warehouse:
			item.warehouse = warehouse


def validate_purchase_approval_threshold(doc, method=None) -> None:
	threshold = flt(frappe.db.get_single_value("Tecponto Settings", "purchase_approval_threshold"))
	if threshold <= 0:
		return

	total = flt(doc.get("grand_total"))
	if total <= threshold:
		return

	if frappe.session.user == "Administrator" or set(frappe.get_roles()) & MANAGER_ROLES:
		return

	frappe.throw("Compra acima de {0} exige aprovação do Gestor.".format(threshold))


def _warehouse_for_item(item_code: str) -> str | None:
	item_group = frappe.get_cached_value("Item", item_code, "item_group")
	if _is_descendant_or_same(item_group, REPAIR_ITEM_GROUP):
		return frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
	if _is_descendant_or_same(item_group, RETAIL_ITEM_GROUP):
		return frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	return None


def _is_descendant_or_same(item_group: str | None, root_item_group: str) -> bool:
	if not item_group:
		return False
	if item_group == root_item_group:
		return True

	root = frappe.db.get_value("Item Group", root_item_group, ["lft", "rgt"], as_dict=True)
	current = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=True)
	if not root or not current:
		return False

	return current.lft >= root.lft and current.rgt <= root.rgt
