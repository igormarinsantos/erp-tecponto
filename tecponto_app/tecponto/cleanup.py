from __future__ import annotations

from pathlib import Path
from typing import Any

import frappe


def cleanup_orphan_tracking_links(dry_run: bool = True) -> dict[str, Any]:
	"""Delete revoked/expired tracking links whose Service Order no longer exists."""
	rows = frappe.db.sql(
		"""
		select name, service_order, status
		from `tabService Order Tracking` t
		where t.service_order is not null and t.service_order != ''
			and t.status in ('Revogado', 'Expirado')
			and not exists (
				select 1 from `tabService Order` so where so.name = t.service_order
			)
		order by modified desc
		""",
		as_dict=True,
	)
	if not dry_run:
		for row in rows:
			frappe.delete_doc("Service Order Tracking", row.name, force=True, ignore_permissions=True)
		frappe.db.commit()
	return {
		"dry_run": bool(dry_run),
		"deleted": 0 if dry_run else len(rows),
		"matched": len(rows),
		"sample": rows[:10],
	}


def scan_orphans() -> dict[str, Any]:
	"""Read-only orphan report used after test-data cleanup."""
	return {
		"orphan_tracking_links": _count_orphan_tracking_links(),
		"missing_public_file_records": {
			"count": len(_missing_public_file_rows()),
			"sample": _missing_public_file_rows()[:10],
		},
		"missing_private_file_records": {
			"count": len(_missing_private_file_rows()),
			"sample": _missing_private_file_rows()[:10],
		},
	}


def _count_orphan_tracking_links() -> dict[str, int]:
	rows = frappe.db.sql(
		"""
		select status, count(*) as qty
		from `tabService Order Tracking` t
		where t.service_order is not null and t.service_order != ''
			and not exists (
				select 1 from `tabService Order` so where so.name = t.service_order
			)
		group by status
		""",
		as_dict=True,
	)
	return {row.status or "Sem status": int(row.qty) for row in rows}


def cleanup_missing_public_file_records(dry_run: bool = True) -> dict[str, Any]:
	"""Delete public File rows whose physical file is gone.

	Private files are excluded because they may be legal evidence. Acceptance
	evidence has its own fail-closed audit in tecponto.acceptance.
	"""
	rows = _missing_public_file_rows()
	if not dry_run:
		names = [row.name for row in rows]
		if names:
			frappe.db.sql("delete from `tabFile` where name in %(names)s", {"names": tuple(names)})
		frappe.db.commit()
	return {
		"dry_run": bool(dry_run),
		"deleted": 0 if dry_run else len(rows),
		"matched": len(rows),
		"sample": rows[:10],
	}


def _missing_public_file_rows() -> list[dict[str, Any]]:
	return _missing_file_rows(is_private=0)


def _missing_private_file_rows() -> list[dict[str, Any]]:
	return _missing_file_rows(is_private=1)


def _missing_file_rows(is_private: int) -> list[dict[str, Any]]:
	rows = frappe.db.sql(
		"""
		select name, file_name, file_url, attached_to_doctype, attached_to_name, is_private
		from `tabFile`
		where is_folder = 0
			and is_private = %(is_private)s
			and (file_url like '/files/%%' or file_url like '/private/files/%%')
		""",
		{"is_private": is_private},
		as_dict=True,
	)
	site_path = Path(frappe.get_site_path())
	missing: list[dict[str, Any]] = []
	for row in rows:
		relative = (row.file_url or "").lstrip("/")
		if relative and not (site_path / relative).exists():
			missing.append(row)
	return missing
