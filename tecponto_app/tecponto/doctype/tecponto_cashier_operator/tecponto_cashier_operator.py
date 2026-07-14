from __future__ import annotations

import re

import frappe
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password

from tecponto_app.tecponto.stock import normalize_barcode


class TecpontoCashierOperator(Document):
	def validate(self) -> None:
		self.badge_code = normalize_barcode(self.badge_code)
		if not self.badge_code:
			frappe.throw("O codigo do cracha e obrigatorio.")
		if not frappe.db.get_value("User", self.user, "enabled"):
			frappe.throw("Selecione um usuario ativo para o operador de caixa.")

		pin = self.get_password("pin", raise_exception=False)
		if not re.fullmatch(r"\d{4}", pin or ""):
			frappe.throw("O PIN do operador deve ter exatamente 4 digitos.")

		for operator_name in frappe.get_all(
			"Tecponto Cashier Operator",
			filters={"active": 1, "name": ["!=", self.name or ""]},
			pluck="name",
		):
			other_pin = get_decrypted_password("Tecponto Cashier Operator", operator_name, "pin", raise_exception=False)
			if other_pin == pin:
				frappe.throw("Este PIN ja pertence a outro operador ativo.")
