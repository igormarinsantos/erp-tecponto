from __future__ import annotations

import frappe


REQUIRED_SETTINGS_DEFAULTS = {
	"technician_assignment_mode": "Dispatch",
	"unassigned_technician_alert_hours": 4,
}


def bootstrap_erpnext_foundation(company: str | None = None) -> None:
	"""Create idempotent operational defaults for the selected native Company."""
	company_doc = _resolve_company(company)
	company_name = company_doc.name
	abbr = company_doc.abbr

	frappe.defaults.set_global_default("company", company_name)
	frappe.db.set_single_value("Global Defaults", "default_company", company_name)

	for item_group_name, is_group in (("Peças de Reparo", 1), ("Produtos de Varejo", 1), ("Aparelhos Usados", 0), ("Serviços", 0)):
		if not frappe.db.exists("Item Group", item_group_name):
			frappe.get_doc({"doctype": "Item Group", "item_group_name": item_group_name, "parent_item_group": "All Item Groups", "is_group": is_group}).insert(ignore_permissions=True)

	warehouses = {}
	for warehouse_name in ("Peças", "Acessórios", "Aparelhos Usados", "Sucata"):
		warehouse = f"{warehouse_name} - {abbr}"
		warehouses[warehouse_name] = warehouse
		if not frappe.db.exists("Warehouse", warehouse):
			frappe.get_doc({"doctype": "Warehouse", "warehouse_name": warehouse_name, "company": company_name, "is_group": 0}).insert(ignore_permissions=True)

	if not frappe.db.exists("Item", "MO-REPARO"):
		frappe.get_doc({"doctype": "Item", "item_code": "MO-REPARO", "item_name": "Mão de obra de reparo", "item_group": "Serviços", "stock_uom": "Nos", "is_stock_item": 0, "is_sales_item": 1}).insert(ignore_permissions=True)

	for mode_of_payment in ("Pix", "Dinheiro", "Cartão Débito", "Cartão Crédito"):
		if not frappe.db.exists("Mode of Payment", mode_of_payment):
			frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": mode_of_payment, "type": "Cash" if mode_of_payment == "Dinheiro" else "Bank"}).insert(ignore_permissions=True)

	from tecponto_app.tecponto.payments import _get_card_receivable_parent

	asset_parent = _get_card_receivable_parent(company_name)
	parent_values = frappe.db.get_value("Account", asset_parent, ["root_type", "report_type"], as_dict=True)
	bank_name = f"Banco {abbr}"
	for account_name, account_type in ((bank_name, "Bank"), (f"Caixa {abbr}", "Cash")):
		if not frappe.db.exists("Account", {"company": company_name, "account_name": account_name}):
			frappe.get_doc({"doctype": "Account", "account_name": account_name, "parent_account": asset_parent, "company": company_name, "is_group": 0, "root_type": parent_values.root_type, "report_type": parent_values.report_type, "account_type": account_type}).insert(ignore_permissions=True)

	bank_account = frappe.db.get_value("Account", {"company": company_name, "account_name": bank_name}, "name")
	frappe.db.set_value("Company", company_name, "default_bank_account", bank_account, update_modified=False)
	if frappe.db.exists("DocType", "Tecponto Settings"):
		_configure_settings(company_name, warehouses)


def after_install() -> None:
	"""Finish defaults after the app DocTypes are available."""
	company_doc = _resolve_company(raise_if_missing=False)
	if not company_doc:
		return
	bootstrap_erpnext_foundation(company_doc.name)
	_configure_settings(company_doc.name, {
		"Peças": f"Peças - {company_doc.abbr}",
		"Acessórios": f"Acessórios - {company_doc.abbr}",
		"Aparelhos Usados": f"Aparelhos Usados - {company_doc.abbr}",
	})
	from tecponto_app.tecponto.payments import ensure_card_receivables_setup
	from tecponto_app.tecponto.pos import ensure_pos_profile

	ensure_card_receivables_setup()
	ensure_pos_profile()


def _resolve_company(company: str | None = None, raise_if_missing: bool = True):
	company_name = company or frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if company_name and frappe.db.exists("Company", company_name):
		return frappe.get_doc("Company", company_name)
	if raise_if_missing:
		frappe.throw("Crie ou selecione uma empresa ERPNext antes de inicializar a fundação do aplicativo.")
	return None


def _configure_settings(company_name: str, warehouses: dict[str, str]) -> None:
	settings = frappe.get_single("Tecponto Settings")
	for fieldname, default in REQUIRED_SETTINGS_DEFAULTS.items():
		value = settings.get(fieldname)
		if value is None or (isinstance(value, str) and not value.strip()):
			settings.set(fieldname, default)
	settings.identity_company = company_name
	settings.repair_warehouse = warehouses["Peças"]
	settings.commercial_warehouse = warehouses["Acessórios"]
	settings.used_devices_warehouse = warehouses["Aparelhos Usados"]
	settings.default_labor_item = "MO-REPARO"
	settings.save(ignore_permissions=True)
