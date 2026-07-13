from frappe.model.document import Document

from tecponto_app.tecponto.requests import expire_requests


class TecpontoRequest(Document):
	pass


def expire_pending_requests():
	return expire_requests()
