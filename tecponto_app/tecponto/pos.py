import frappe

from tecponto_app.tecponto.payments import ensure_card_receivables_setup


POS_PROFILE_NAME = "Tecponto Balcão"
POS_PAYMENT_MODES = ("Pix", "Dinheiro", "Débito", "Crédito à vista")
CARD_PAYMENT_MODES = ("Débito", "Crédito à vista")


def ensure_pos_profile() -> None:
	if not frappe.db.exists("DocType", "POS Profile"):
		return

	ensure_card_receivables_setup()

	company = _default_company()
	commercial_warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	if not commercial_warehouse:
		frappe.throw("Warehouse Comercial nao configurado no Tecponto Settings.")

	_ensure_pos_payment_modes(company)

	if frappe.db.exists("POS Profile", POS_PROFILE_NAME):
		profile = frappe.get_doc("POS Profile", POS_PROFILE_NAME)
	else:
		profile = frappe.new_doc("POS Profile")
		profile.name = POS_PROFILE_NAME

	profile.company = company
	profile.disabled = 0
	profile.warehouse = commercial_warehouse
	profile.currency = _company_currency(company)
	profile.selling_price_list = _selling_price_list()
	profile.write_off_account = _write_off_account(company)
	profile.write_off_cost_center = _cost_center(company)

	if profile.meta.has_field("income_account"):
		profile.income_account = _income_account(company)
	if profile.meta.has_field("expense_account"):
		profile.expense_account = _expense_account(company)

	profile.set("payments", [])
	for mode_of_payment in POS_PAYMENT_MODES:
		profile.append(
			"payments",
			{
				"mode_of_payment": mode_of_payment,
				"default": 1 if mode_of_payment == "Dinheiro" else 0,
			},
		)

	profile.save(ignore_permissions=True)


def validate_pos_warehouse(doc, method=None) -> None:
	if doc.get("pos_profile") != POS_PROFILE_NAME:
		return

	commercial_warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	if not commercial_warehouse:
		return

	if doc.get("set_warehouse") and doc.get("set_warehouse") != commercial_warehouse:
		frappe.throw("POS Tecponto Balcao deve baixar apenas do estoque Comercial.")

	for item in doc.get("items") or []:
		if not item.get("item_code"):
			continue
		if not frappe.get_cached_value("Item", item.item_code, "is_stock_item"):
			continue
		if item.get("warehouse") and item.get("warehouse") != commercial_warehouse:
			frappe.throw("POS Tecponto Balcao deve baixar apenas do estoque Comercial.")


def _ensure_pos_payment_modes(company: str) -> None:
	clearing_account = frappe.db.get_single_value("Tecponto Settings", "acquirer_clearing_account")
	if not clearing_account:
		frappe.throw("Conta de recebiveis de cartao nao configurada no Tecponto Settings.")

	for mode_of_payment in POS_PAYMENT_MODES:
		if mode_of_payment in CARD_PAYMENT_MODES:
			_ensure_mode_account(mode_of_payment, company, "Bank", clearing_account)
		elif mode_of_payment == "Pix":
			_ensure_mode_account(mode_of_payment, company, "Bank", _bank_account(company))
		else:
			_ensure_mode_account(mode_of_payment, company, "Cash", _cash_account(company))


def _ensure_mode_account(mode_of_payment: str, company: str, mode_type: str, account: str) -> None:
	if frappe.db.exists("Mode of Payment", mode_of_payment):
		doc = frappe.get_doc("Mode of Payment", mode_of_payment)
	else:
		doc = frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": mode_of_payment,
				"type": mode_type,
				"enabled": 1,
			}
		)

	doc.type = doc.type or mode_type
	doc.enabled = 1

	row = None
	for account_row in doc.get("accounts") or []:
		if account_row.get("company") == company:
			row = account_row
			break

	if row:
		row.default_account = account
	else:
		doc.append("accounts", {"company": company, "default_account": account})

	doc.save(ignore_permissions=True)


def _default_company() -> str:
	company = frappe.defaults.get_user_default("Company")
	company = company or frappe.db.get_single_value("Global Defaults", "default_company")
	company = company or frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw("Empresa padrao nao encontrada.")
	return company


def _company_currency(company: str) -> str:
	currency = frappe.db.get_value("Company", company, "default_currency")
	if not currency:
		frappe.throw("Moeda padrao da empresa nao encontrada.")
	return currency


def _selling_price_list() -> str:
	price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
	price_list = price_list or frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
	if not price_list:
		frappe.throw("Price List de venda nao encontrada.")
	return price_list


def _write_off_account(company: str) -> str:
	account = frappe.db.get_value("Company", company, "default_expense_account")
	account = account or frappe.db.get_value(
		"Account",
		{"company": company, "is_group": 0, "root_type": "Expense"},
		"name",
	)
	if not account:
		frappe.throw("Conta de write-off para POS nao encontrada.")
	return account


def _cost_center(company: str) -> str:
	cost_center = frappe.db.get_value("Company", company, "cost_center")
	cost_center = cost_center or frappe.db.get_value(
		"Cost Center",
		{"company": company, "is_group": 0},
		"name",
	)
	if not cost_center:
		frappe.throw("Centro de custo para POS nao encontrado.")
	return cost_center


def _income_account(company: str) -> str | None:
	return frappe.db.get_value("Company", company, "default_income_account") or frappe.db.get_value(
		"Account",
		{"company": company, "is_group": 0, "root_type": "Income"},
		"name",
	)


def _expense_account(company: str) -> str | None:
	return frappe.db.get_value("Company", company, "default_expense_account") or frappe.db.get_value(
		"Account",
		{"company": company, "is_group": 0, "root_type": "Expense"},
		"name",
	)


def _bank_account(company: str) -> str:
	account = frappe.db.get_value(
		"Mode of Payment Account",
		{"parent": "Pix", "company": company},
		"default_account",
	)
	account = account or frappe.db.get_value("Company", company, "default_bank_account")
	account = account or frappe.db.get_value(
		"Account",
		{"company": company, "is_group": 0, "account_type": "Bank"},
		"name",
	)
	if not account:
		frappe.throw("Conta bancaria para Pix no POS nao encontrada.")
	return account


def _cash_account(company: str) -> str:
	account = frappe.db.get_value(
		"Mode of Payment Account",
		{"parent": ["in", ["Dinheiro", "Cash"]], "company": company},
		"default_account",
	)
	account = account or frappe.db.get_value(
		"Account",
		{"company": company, "is_group": 0, "account_type": "Cash"},
		"name",
	)
	if not account:
		frappe.throw("Conta caixa para Dinheiro no POS nao encontrada.")
	return account
