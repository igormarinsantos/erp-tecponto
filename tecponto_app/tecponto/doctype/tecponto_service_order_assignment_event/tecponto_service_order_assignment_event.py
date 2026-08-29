import frappe
from frappe import _
from frappe.model.document import Document


class TecpontoServiceOrderAssignmentEvent(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(_("O histórico de atribuição é imutável."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("O histórico de atribuição é imutável."), frappe.PermissionError)
