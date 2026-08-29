# Copyright (c) 2026, Tecponto and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ServiceOrder(Document):
	def before_save(self):
		if self.is_new():
			return
		previous = self.get_doc_before_save()
		if previous and previous.workflow_state == "Diagnosticado — aguardando orçamento" and self.workflow_state == "Em diagnóstico":
			self.budget_review_required = 1
