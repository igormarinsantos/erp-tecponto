import frappe


def migrate_device_credentials() -> None:
	"""Move legacy OS/device plaintext credentials to the encrypted device record."""
	if not frappe.db.table_exists("Customer Device") or not frappe.db.has_column("Customer Device", "device_access_credential"):
		return
	legacy_device_field = frappe.db.has_column("Customer Device", "device_password")
	for name in frappe.get_all("Customer Device", pluck="name"):
		device = frappe.get_doc("Customer Device", name)
		try:
			current = device.get_password("device_access_credential")
		except Exception:
			current = ""
		if current:
			continue
		credential = frappe.db.get_value("Customer Device", name, "device_password") if legacy_device_field else ""
		access_type = "Alfanumérica" if credential else ""
		if not credential:
			orders = frappe.get_all("Service Order", filters={"customer_device": name}, fields=["name", "device_access_type"], order_by="creation desc")
			for row in orders:
				order = frappe.get_doc("Service Order", row.name)
				try:
					credential = order.get_password("device_access_credential")
				except Exception:
					credential = ""
				if credential:
					access_type = row.device_access_type or "Alfanumérica"
					break
		if credential:
			device.device_access_type = access_type
			device.device_access_credential = credential
			device.save(ignore_permissions=True)
