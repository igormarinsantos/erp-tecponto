from __future__ import annotations

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
