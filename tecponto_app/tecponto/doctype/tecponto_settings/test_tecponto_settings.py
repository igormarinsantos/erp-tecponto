# Copyright (c) 2026, Tecponto and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from tecponto_app.patches.v16_0.initialize_operation_settings_defaults import (
	OPERATION_DEFAULTS,
	execute as initialize_operation_settings_defaults,
)


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestTecpontoSettings(IntegrationTestCase):
	"""
	Integration tests for TecpontoSettings.
	Use this class for testing interactions between multiple components.
	"""

	def setUp(self):
		super().setUp()
		self.operation_fields = tuple(OPERATION_DEFAULTS)
		self.previous_values = frappe.db.get_singles_dict("Tecponto Settings")

	def tearDown(self):
		frappe.db.delete(
			"Singles",
			filters={"doctype": "Tecponto Settings", "field": ("in", self.operation_fields)},
		)
		restore = {
			fieldname: self.previous_values[fieldname]
			for fieldname in self.operation_fields
			if fieldname in self.previous_values
		}
		if restore:
			frappe.db.set_single_value("Tecponto Settings", restore, update_modified=False)
		super().tearDown()

	def test_operation_defaults_backfill_only_missing_or_blank_legacy_keys(self):
		"""A legacy singleton receives defaults without overwriting explicit store choices."""
		frappe.db.delete(
			"Singles",
			filters={
				"doctype": "Tecponto Settings",
				"field": (
					"in",
					(
						"enable_repair_pillar",
						"enable_buy_pillar",
						"enable_tradein_pillar",
						"payment_advance_enabled",
						"payment_installments_enabled",
						"payment_device_tradein_enabled",
						"default_warranty_days",
					),
				),
			},
		)
		frappe.db.set_single_value(
			"Tecponto Settings",
			{
				"diagnostic_fee_enabled": 0,
				"storage_fee_start_days": 0,
				"use_technician_commission": 0,
			},
			update_modified=False,
		)

		initialize_operation_settings_defaults()
		first_run = frappe.db.get_singles_dict("Tecponto Settings")

		self.assertEqual(first_run["enable_repair_pillar"], "1")
		self.assertEqual(first_run["enable_buy_pillar"], "1")
		self.assertEqual(first_run["enable_tradein_pillar"], "1")
		self.assertEqual(first_run["payment_advance_enabled"], "1")
		self.assertEqual(first_run["payment_installments_enabled"], "1")
		self.assertEqual(first_run["payment_device_tradein_enabled"], "1")
		self.assertEqual(first_run["default_warranty_days"], "90")
		self.assertEqual(first_run["diagnostic_fee_enabled"], "0")
		self.assertEqual(first_run["storage_fee_start_days"], "0")
		self.assertEqual(first_run["use_technician_commission"], "0")

		initialize_operation_settings_defaults()
		self.assertEqual(frappe.db.get_singles_dict("Tecponto Settings"), first_run)
