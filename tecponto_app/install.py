from __future__ import annotations

import frappe


COMPANY_NAME = "Tecponto"


def bootstrap_erpnext_foundation() -> None:
	"""Create the Tecponto stock and catalog foundation on a new ERPNext site.

	This runs before installing tecponto_app in production. Its records are the
	links referenced by the app fixtures, so a completely empty ERPNext site can
	be provisioned without relying on local development data.
	"""
	if not frappe.db.exists("Company", COMPANY_NAME):
		frappe.throw("A empresa Tecponto deve existir antes da fundacao do aplicativo.")

	frappe.defaults.set_global_default("company", COMPANY_NAME)
	frappe.db.set_single_value("Global Defaults", "default_company", COMPANY_NAME)

	for item_group_name, is_group in (
		("Peças de Reparo", 1),
		("Produtos de Varejo", 1),
		("Aparelhos Usados", 0),
		("Serviços", 0),
	):
		if frappe.db.exists("Item Group", item_group_name):
			continue
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": item_group_name,
				"parent_item_group": "All Item Groups",
				"is_group": is_group,
			}
		).insert(ignore_permissions=True)

	for warehouse_name in ("Peças", "Acessórios", "Aparelhos Usados", "Sucata"):
		warehouse = f"{warehouse_name} - TEC"
		if frappe.db.exists("Warehouse", warehouse):
			continue
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": warehouse_name,
				"company": COMPANY_NAME,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)

	if not frappe.db.exists("Item", "MO-REPARO"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "MO-REPARO",
				"item_name": "Mão de obra de reparo",
				"item_group": "Serviços",
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"is_sales_item": 1,
			}
		).insert(ignore_permissions=True)

	for mode_of_payment in ("Pix", "Dinheiro", "Cartão Débito", "Cartão Crédito"):
		if frappe.db.exists("Mode of Payment", mode_of_payment):
			continue
		frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": mode_of_payment,
				"type": "Cash" if mode_of_payment == "Dinheiro" else "Bank",
			}
		).insert(ignore_permissions=True)

	from tecponto_app.tecponto.payments import _get_card_receivable_parent

	asset_parent = _get_card_receivable_parent(COMPANY_NAME)
	parent_values = frappe.db.get_value(
		"Account", asset_parent, ["root_type", "report_type"], as_dict=True
	)
	for account_name, account_type in (("Banco Tecponto", "Bank"), ("Caixa Tecponto", "Cash")):
		if frappe.db.exists("Account", {"company": COMPANY_NAME, "account_name": account_name}):
			continue
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": asset_parent,
				"company": COMPANY_NAME,
				"is_group": 0,
				"root_type": parent_values.root_type,
				"report_type": parent_values.report_type,
				"account_type": account_type,
			}
		).insert(ignore_permissions=True)

	bank_account = frappe.db.get_value(
		"Account", {"company": COMPANY_NAME, "account_name": "Banco Tecponto"}, "name"
	)
	frappe.db.set_value("Company", COMPANY_NAME, "default_bank_account", bank_account, update_modified=False)


def after_install() -> None:
	"""Finish Tecponto defaults after the app DocTypes are available."""
	bootstrap_erpnext_foundation()

	settings = frappe.get_single("Tecponto Settings")
	settings.repair_warehouse = "Peças - TEC"
	settings.commercial_warehouse = "Acessórios - TEC"
	settings.used_devices_warehouse = "Aparelhos Usados - TEC"
	settings.default_labor_item = "MO-REPARO"
	settings.save(ignore_permissions=True)

	from tecponto_app.tecponto.payments import ensure_card_receivables_setup
	from tecponto_app.tecponto.pos import ensure_pos_profile

	ensure_card_receivables_setup()
	ensure_pos_profile()
