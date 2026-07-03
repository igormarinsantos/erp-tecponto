from datetime import datetime, time, timedelta

import frappe
from frappe.utils import get_datetime, getdate, now, now_datetime, today


APPROVAL_BUSINESS_HOURS = 48
GUARULHOS_HOLIDAY_LIST = "Guarulhos-SP"
STATE_AGUARDANDO_APROVACAO = "Aguardando aprova\u00e7\u00e3o"
STATE_ORCAMENTO_EXPIRADO = "Or\u00e7amento expirado"


def ensure_guarulhos_holiday_list() -> str:
	from dateutil.easter import easter
	from holidays import country_holidays

	current_year = getdate(today()).year
	from_date = getdate(f"{current_year - 1}-01-01")
	to_date = getdate(f"{current_year + 5}-12-31")

	if frappe.db.exists("Holiday List", GUARULHOS_HOLIDAY_LIST):
		holiday_list = frappe.get_doc("Holiday List", GUARULHOS_HOLIDAY_LIST)
		holiday_list.from_date = min(getdate(holiday_list.from_date), from_date)
		holiday_list.to_date = max(getdate(holiday_list.to_date), to_date)
	else:
		holiday_list = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": GUARULHOS_HOLIDAY_LIST,
				"from_date": from_date,
				"to_date": to_date,
				"country": "BR",
				"subdivision": "SP",
			}
		)

	existing_dates = {getdate(row.holiday_date) for row in holiday_list.get("holidays")}
	holidays_by_date = {}

	for holiday_date, description in country_holidays(
		"BR",
		subdiv="SP",
		years=range(from_date.year, to_date.year + 1),
		language="pt_BR",
	).items():
		holidays_by_date[getdate(holiday_date)] = description

	for year in range(from_date.year, to_date.year + 1):
		easter_date = easter(year)
		holidays_by_date.setdefault(easter_date - timedelta(days=2), "Sexta-feira da Paixao")
		holidays_by_date[easter_date + timedelta(days=60)] = "Corpus Christi"
		holidays_by_date[getdate(f"{year}-12-08")] = (
			"Nossa Senhora da Conceicao e Fundacao da Cidade"
		)

	cursor = from_date
	while cursor <= to_date:
		if cursor.weekday() == 5:
			holidays_by_date.setdefault(cursor, "Saturday")
		elif cursor.weekday() == 6:
			holidays_by_date.setdefault(cursor, "Sunday")
		cursor += timedelta(days=1)

	for holiday_date, description in sorted(holidays_by_date.items()):
		if holiday_date in existing_dates:
			continue

		holiday_list.append(
			"holidays",
			{
				"holiday_date": holiday_date,
				"description": description,
				"weekly_off": 1 if holiday_date.weekday() in (5, 6) else 0,
			},
		)

	holiday_list.save(ignore_permissions=True)
	_set_company_default_holiday_list_if_empty(holiday_list.name)
	return holiday_list.name


def set_approval_deadline(doc, method=None) -> None:
	if doc.get("workflow_state") != STATE_AGUARDANDO_APROVACAO:
		return

	if doc.get("approval_deadline"):
		return

	doc.approval_deadline = add_business_hours(now_datetime(), APPROVAL_BUSINESS_HOURS)


def expirar_orcamentos() -> None:
	for row in frappe.get_all(
		"Service Order",
		filters={
			"workflow_state": STATE_AGUARDANDO_APROVACAO,
			"approval_deadline": ["<", now()],
		},
		pluck="name",
	):
		frappe.db.set_value(
			"Service Order",
			row,
			"workflow_state",
			STATE_ORCAMENTO_EXPIRADO,
			update_modified=True,
		)


def add_business_hours(start_datetime, hours: int, holiday_list: str | None = None) -> datetime:
	holiday_list = holiday_list or ensure_guarulhos_holiday_list()
	current = get_datetime(start_datetime)
	remaining_seconds = hours * 60 * 60
	holiday_dates = _get_holiday_dates(holiday_list)

	while remaining_seconds > 0:
		if not _is_business_day(current, holiday_dates):
			current = _next_business_day_start(current, holiday_dates)
			continue

		end_of_day = datetime.combine(getdate(current) + timedelta(days=1), time.min)
		seconds_available = max((end_of_day - current).total_seconds(), 0)
		if seconds_available <= 0:
			current = _next_business_day_start(current, holiday_dates)
			continue

		seconds_to_consume = min(remaining_seconds, seconds_available)
		current += timedelta(seconds=seconds_to_consume)
		remaining_seconds -= seconds_to_consume

	return current


def _get_holiday_dates(holiday_list: str) -> set:
	return {
		getdate(row.holiday_date)
		for row in frappe.get_all(
			"Holiday",
			filters={"parent": holiday_list, "is_half_day": 0},
			fields=["holiday_date"],
		)
	}


def _is_business_day(value, holiday_dates: set) -> bool:
	return getdate(value) not in holiday_dates


def _next_business_day_start(current: datetime, holiday_dates: set) -> datetime:
	next_day = getdate(current) + timedelta(days=1)

	while next_day in holiday_dates:
		next_day += timedelta(days=1)

	return datetime.combine(next_day, time.min)


def _set_company_default_holiday_list_if_empty(holiday_list: str) -> None:
	if not frappe.db.exists("DocType", "Company"):
		return

	for company in frappe.get_all("Company", fields=["name", "default_holiday_list"]):
		if not company.default_holiday_list:
			frappe.db.set_value(
				"Company",
				company.name,
				"default_holiday_list",
				holiday_list,
				update_modified=False,
			)
