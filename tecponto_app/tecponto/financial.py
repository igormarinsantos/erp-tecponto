"""Narrow elevation for ERPNext's native accounting document posting."""

from __future__ import annotations

from contextlib import contextmanager

from tecponto_app.tecponto.permissions import as_user


@contextmanager
def native_financial_posting():
	"""Post a validated native accounting document without granting the caller accounting roles.

	Operational authorization must be checked before entering this context.  ERPNext
	still resolves party accounts while inserting a document even with
	``ignore_permissions=True``; this temporary session is limited to that native
	posting call and always restores the request user.

	Uses ``as_user`` rather than a bare ``frappe.set_user()``/restore, which corrupts
	the caller's session cookie (see ``tecponto_app.tecponto.permissions.as_user``).
	"""
	with as_user("Administrator"):
		yield
