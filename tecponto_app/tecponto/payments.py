import frappe


CARD_RECEIVABLE_ACCOUNT_NAME = "Recebíveis de Cartão"
# ERPNext requires party on GL rows for technical Receivable accounts.
CARD_RECEIVABLE_ACCOUNT_TYPE = "Current Asset"
CARD_PAYMENT_MODES = ("Débito", "Crédito à vista", "Crédito parcelado")
EXISTING_CARD_MODE_ALIASES = ("Cartão Débito", "Cartão Crédito", "Credit Card")
CARD_FEES = (
	("Débito", 1.5, 1),
	("Crédito à vista", 3.0, 30),
	("Crédito 2x", 4.5, 30),
	("Crédito 3x+", 5.5, 30),
)


def _get_default_company() -> str | None:
	return frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")


def _get_card_receivable_parent(company: str) -> str:
	for account_name in ("CRÉDITOS", "Accounts Receivable", "Contas a Receber"):
		parent = frappe.db.get_value(
			"Account",
			{"company": company, "account_name": account_name, "is_group": 1},
			"name",
		)
		if parent:
			return parent

	receivable_account = frappe.db.get_value(
		"Account",
		{"company": company, "root_type": "Asset", "account_type": "Receivable", "is_group": 0},
		"parent_account",
	)
	if receivable_account:
		return receivable_account

	for account_name in ("CIRCULANTE 1", "Current Assets", "ATIVO"):
		parent = frappe.db.get_value(
			"Account",
			{"company": company, "account_name": account_name, "is_group": 1},
			"name",
		)
		if parent:
			return parent

	frappe.throw("Nao foi encontrado um grupo de Ativo para criar Recebiveis de Cartao.")


def _ensure_card_receivable_account(company: str) -> str:
	account = frappe.db.get_value(
		"Account",
		{"company": company, "account_name": CARD_RECEIVABLE_ACCOUNT_NAME},
		"name",
	)
	if account:
		frappe.db.set_value(
			"Account",
			account,
			"account_type",
			CARD_RECEIVABLE_ACCOUNT_TYPE,
			update_modified=False,
		)
		return account

	parent_account = _get_card_receivable_parent(company)
	parent_values = frappe.db.get_value(
		"Account",
		parent_account,
		["root_type", "report_type"],
		as_dict=True,
	)

	doc = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": CARD_RECEIVABLE_ACCOUNT_NAME,
			"parent_account": parent_account,
			"company": company,
			"is_group": 0,
			"root_type": parent_values.root_type if parent_values else "Asset",
			"report_type": parent_values.report_type if parent_values else "Balance Sheet",
			"account_type": CARD_RECEIVABLE_ACCOUNT_TYPE,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_mode_of_payment_account(
	mode_of_payment: str,
	company: str,
	clearing_account: str,
	create_if_missing: bool = True,
) -> None:
	if frappe.db.exists("Mode of Payment", mode_of_payment):
		doc = frappe.get_doc("Mode of Payment", mode_of_payment)
	elif create_if_missing:
		doc = frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": mode_of_payment,
				"type": "Bank",
				"enabled": 1,
			}
		)
	else:
		return

	row = None
	for account_row in doc.get("accounts") or []:
		if account_row.get("company") == company:
			row = account_row
			break

	if row:
		row.default_account = clearing_account
	else:
		doc.append("accounts", {"company": company, "default_account": clearing_account})

	doc.save(ignore_permissions=True)


def _set_card_fees(settings) -> None:
	settings.set("card_fees", [])
	for tipo, taxa_pct, settlement_days in CARD_FEES:
		settings.append(
			"card_fees",
			{
				"tipo": tipo,
				"taxa_pct": taxa_pct,
				"settlement_days": settlement_days,
			},
		)


def ensure_card_receivables_setup() -> None:
	if not frappe.db.exists("DocType", "Tecponto Settings"):
		return

	company = _get_default_company()
	if not company:
		return

	clearing_account = _ensure_card_receivable_account(company)

	settings = frappe.get_single("Tecponto Settings")
	settings.acquirer_clearing_account = clearing_account
	_set_card_fees(settings)
	settings.save(ignore_permissions=True)

	for mode_of_payment in CARD_PAYMENT_MODES:
		_ensure_mode_of_payment_account(mode_of_payment, company, clearing_account)

	for mode_of_payment in EXISTING_CARD_MODE_ALIASES:
		_ensure_mode_of_payment_account(
			mode_of_payment,
			company,
			clearing_account,
			create_if_missing=False,
		)
