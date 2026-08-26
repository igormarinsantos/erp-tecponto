"""Narrow elevation for ERPNext's native accounting document posting."""

from __future__ import annotations

from contextlib import contextmanager

import frappe


@contextmanager
def native_financial_posting():
	"""Post a validated native accounting document without granting the caller accounting roles.

	Operational authorization must be checked before entering this context.  ERPNext
	still resolves party accounts while inserting a document even with
	``ignore_permissions=True``; this temporary session is limited to that native
	posting call and always restores the request user.
	"""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		yield
	finally:
		# A shell/worker call can lack a request session. It must fall back to
		# Guest rather than leave the temporary Administrator context behind.
		frappe.set_user(previous_user or "Guest")
