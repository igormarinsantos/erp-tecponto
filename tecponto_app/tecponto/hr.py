import frappe
from frappe.utils import getdate, today


DEFAULT_EMPLOYEE_DATE_OF_BIRTH = "1990-01-01"
DEFAULT_GENDER = "Not Specified"
TECHNICIAN_ROLE = "Tecponto Tecnico"
SALARY_COMPONENTS = (
	{
		"salary_component": "Comissão",
		"salary_component_abbr": "COM",
		"type": "Earning",
		"is_tax_applicable": 1,
		"description": "Comissao de mao de obra Tecponto via Additional Salary.",
	},
	{
		"salary_component": "Débito por perda",
		"salary_component_abbr": "PERDA",
		"type": "Deduction",
		"description": "Debito por perda do tecnico via Additional Salary.",
	},
)


def _get_default_company() -> str | None:
	return frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")


def _ensure_default_gender() -> str:
	if frappe.db.exists("Gender", DEFAULT_GENDER):
		return DEFAULT_GENDER

	existing_gender = frappe.db.get_value("Gender", {}, "name")
	if existing_gender:
		return existing_gender

	gender = frappe.get_doc({"doctype": "Gender", "gender": DEFAULT_GENDER})
	gender.insert(ignore_permissions=True)
	return gender.name


def _get_technician_users() -> list[str]:
	return frappe.get_all(
		"Has Role",
		filters={"role": TECHNICIAN_ROLE, "parenttype": "User"},
		pluck="parent",
	)


def _employee_name_from_user(user_doc) -> str:
	return user_doc.get("full_name") or user_doc.get("first_name") or user_doc.name.split("@")[0]


def _ensure_employee_for_user(user: str, company: str, gender: str) -> str:
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if employee:
		return employee

	user_doc = frappe.get_cached_doc("User", user)
	first_name = user_doc.get("first_name") or _employee_name_from_user(user_doc)

	employee_doc = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": first_name,
			"last_name": user_doc.get("last_name"),
			"gender": gender,
			"date_of_birth": DEFAULT_EMPLOYEE_DATE_OF_BIRTH,
			"date_of_joining": getdate(user_doc.get("creation")) or today(),
			"company": company,
			"status": "Active",
			"user_id": user,
			"create_user_permission": 0,
		}
	)
	employee_doc.insert(ignore_permissions=True)
	return employee_doc.name


def _ensure_salary_component(component: dict) -> str:
	name = component["salary_component"]
	doc = frappe.get_doc("Salary Component", name) if frappe.db.exists("Salary Component", name) else None

	if not doc:
		doc = frappe.get_doc({"doctype": "Salary Component", "salary_component": name})

	doc.salary_component_abbr = component["salary_component_abbr"]
	doc.type = component["type"]
	doc.description = component["description"]
	doc.depends_on_payment_days = 0
	doc.remove_if_zero_valued = 1
	doc.disabled = 0

	if component["type"] == "Earning":
		doc.is_tax_applicable = component.get("is_tax_applicable", 1)
	else:
		doc.variable_based_on_taxable_salary = 0
		doc.is_income_tax_component = 0

	doc.save(ignore_permissions=True)
	return doc.name


def ensure_hr_foundation() -> None:
	if not all(frappe.db.exists("DocType", doctype) for doctype in ("Employee", "Salary Component")):
		return

	company = _get_default_company()
	if not company:
		return

	for component in SALARY_COMPONENTS:
		_ensure_salary_component(component)

	gender = _ensure_default_gender()
	for user in _get_technician_users():
		_ensure_employee_for_user(user, company, gender)
