import frappe
from frappe import _
from frappe.model.document import Document


class TecpontoCashMovement(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(_("Movimentos de caixa são imutáveis; registre um novo movimento de reversão."))

	def on_trash(self):
		frappe.throw(_("Movimentos de caixa são imutáveis e não podem ser excluídos."))
