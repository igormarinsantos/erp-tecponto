from __future__ import annotations

import json
import os
from base64 import b64encode
from datetime import datetime
from io import BytesIO
from threading import Event, Thread
from time import monotonic, sleep
from typing import Any
from unittest.mock import patch
from pathlib import Path

import frappe
from frappe.utils import today
from frappe.utils import add_days, add_to_date, flt, now_datetime, nowdate
from pypdf import PdfReader
from PIL import Image, ImageDraw
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	get_available_qty_to_reserve,
)

from tecponto_app.tecponto.customer import CUSTOMER_NO_CPF_FIELD
from tecponto_app.tecponto.financial import native_financial_posting
from tecponto_app.tecponto.pending import action_for_service_order
from tecponto_app.tecponto.company_identity import (
	get_company_identity,
	get_public_company_identity,
	get_pwa_manifest,
)
from tecponto_app.www import aceite as acceptance_page
from tecponto_app.www import rastreio as tracking_page
from tecponto_app.www import tecponto as frontend_page
from tecponto_app.tecponto.frontend.api import (
	contains_sensitive_field,
	get_dashboard_metrics,
	get_administrative_sales_report,
	get_administration_settings,
	save_administration_settings,
	get_director_financial_summary,
	get_service_order_director_financial_summary,
	get_director_risk_agenda,
	get_director_strategic_report,
	get_technician_workload,
	get_boot,
	get_store_cash_session,
	get_store_cash_statement,
	get_store_cash_session_history,
	close_store_cash_session,
	get_list_statbar,
	get_service_order_statbar,
	get_service_order_detail,
	save_technical_diagnosis,
	complete_technical_diagnosis,
	set_service_order_part_outcome,
	get_service_order_kanban,
	issue_os_acceptance,
	add_service_order_budget_line,
	remove_service_order_budget_line,
	update_service_order_budget_presentation,
	record_quote_follow_up,
	get_quotes_crm_panel,
	send_service_order_quote,
	add_catalog_service_to_service_order,
	create_service_order_checkin,
	decide_service_order_budget,
	get_checkin_delivery_suggestion,
	list_defect_service_mappings,
	list_warranty_candidates,
	search_service_order_warranties,
	open_store_cash_session,
	create_customer,
	create_customer_device,
	get_registry_record,
	list_catalog_references,
	list_catalog_services,
	list_customer_devices,
	list_my_commissions,
	list_service_orders,
	list_unassigned_service_orders,
	claim_service_order,
	assign_service_order,
	transfer_service_order,
	list_stock_items,
	list_sales,
	list_trade_evaluations,
	create_trade_evaluation,
	complete_trade_buyback,
	receive_service_order_payment,
	list_service_order_tradein_candidates,
	list_tradein_output_devices,
	confirm_tradein_operation,
	move_service_order,
	create_stock_transfer,
	resolve_panel,
	search_budget_items,
	search_customers,
	save_registry_record,
	search_pos_items,
	set_tradein_approved_value,
	list_product_categories,
	save_product_category,
	create_product_with_variants,
	list_product_variant_attributes,
	list_variant_products,
	save_product_variant_attribute,
	list_commercial_catalog,
	save_listing_metadata,
	save_catalog_reference,
	save_catalog_service,
	save_stage_sla,
	save_defect_service_mapping,
	list_user_accounts,
	save_user_account,
	set_user_password,
	submit_stock_transfer,
	create_technical_part_request,
	cancel_part_request,
	list_purchase_part_requests,
	list_my_technical_part_requests,
	mark_part_request_ordered,
	mark_part_request_received,
	search_repair_part_options,
	get_sale_post_sale_detail,
	create_sales_return,
	exchange_sales_product,
	_quote_send_text,
)
from tecponto_app.tecponto.acceptance import (
	audit_completed_acceptance_evidence,
	assert_completed_acceptance_evidence,
	assert_completed_inoperative_device_term,
	complete_public_acceptance,
	get_public_acceptance,
	has_completed_physical_acceptance,
	record_physical_acceptance,
	save_public_acceptance_selfie,
)
from tecponto_app.tecponto.tracking import (
	INVALID_LINK_MESSAGE,
	TRACKING_STAGES,
	decide_public_tracking_budget,
	get_public_tracking,
	get_public_portal,
	issue_tracking_link,
	issue_service_order_tracking_link,
	on_service_order_updated,
	revoke_service_order_tracking_link,
	start_public_tracking_budget_acceptance,
	lookup_public_portal,
	start_public_portal_action,
)
from tecponto_app.tecponto.frontend.setup import FRONTEND_ROLES, ensure_frontend_foundation
from tecponto_app.tecponto import technical_budget
from tecponto_app.tecponto.hr import ensure_hr_foundation
from tecponto_app.tecponto.product_categories import ensure_product_category_foundation
from tecponto_app.tecponto.product_variants import ensure_product_variant_attributes
from tecponto_app.tecponto.listing_metadata import ensure_listing_metadata_fields
from tecponto_app.tecponto.requests import (
	approve_request,
	create_request,
	expire_requests,
	list_my_requests,
	list_pending_approvals,
	reject_request,
)
from tecponto_app.tecponto.frontend.pos import (
	pos_create_sale,
	pos_download_cashier_badge,
	pos_download_barcode_label,
	pos_download_receipt,
	pos_generate_item_barcode,
	pos_identify_cashier_operator,
	pos_lookup_retail_barcode,
	pos_receive_retail_stock,
	pos_register_retail_product,
)
from tecponto_app.tecponto.pos import (
	BARCODE_SOURCE_FIELD,
	BARCODE_SOURCE_INTERNAL,
	BARCODE_SOURCE_MANUFACTURER,
	BARCODE_SYMBOLOGY_CODE128,
	BARCODE_SYMBOLOGY_FIELD,
	POS_BARCODE_LABEL_PRINT_FORMAT,
	POS_RECEIPT_PRINT_FORMAT,
	POS_RECEIPT_58_PRINT_FORMAT,
	_receipt_css,
	ensure_item_barcode_source_field,
	ensure_pos_barcode_label_print_format,
	ensure_pos_receipt_print_format,
	get_retail_item_groups,
)
from tecponto_app.tecponto import notify
from tecponto_app.tecponto.cashier import CASHIER_OPERATOR_FIELD
from tecponto_app.tecponto.cash import (
	CASH_SESSION_DOCTYPE,
	CASH_MOVEMENT_DOCTYPE,
	close_cash_session,
	get_cash_statement,
	get_open_cash_session,
	get_cash_session_summary,
	open_cash_session,
	record_drawer_adjustment,
	record_cash_movement,
)
from tecponto_app.tecponto.pending import complete_manual_task, create_manual_task, list_agenda_calendar, list_daily_actions
from tecponto_app.tecponto.used_device_warranty import consultar_garantia_usado
from tecponto_app.tecponto.service_order.stage_clock import get_stage_clock
from tecponto_app.tecponto.service_order.stage_sla import add_commercial_business_hours, get_stage_slas
from tecponto_app.tecponto.service_order.parts import processar_pecas
from tecponto_app.tecponto.service_order.aceites import validate_aceites
from tecponto_app.tecponto.service_order.inoperative_device import (
	INOPERATIVE_DEVICE_TERM_VERSION,
	ENTRY_OPERATING_CONDITION_OK,
	ENTRY_OPERATING_CONDITION_PARTIAL,
	ENTRY_OPERATING_CONDITION_INOPERATIVE,
)
from tecponto_app.tecponto.service_order.print_formats import (
	PF_ETIQUETA_INTERNA,
	PF_ETIQUETA_QR,
	PF_LAUDO_TECNICO,
	PF_OS_ORCAMENTO,
	PF_OS_ORCAMENTO_DISCRIMINADO,
	PF_TERMO_APARELHO_PAGAMENTO,
	PF_TERMO_ENTRADA,
	PF_TERMO_GARANTIA,
	PF_TERMO_PECA_CLIENTE,
	PF_TERMO_RETIRADA,
	_etiqueta_interna_html,
	_etiqueta_qr_html,
	_laudo_tecnico_html,
	_os_orcamento_html,
	_os_orcamento_discriminado_html,
	_termo_aparelho_pagamento_html,
	_termo_entrada_html,
	_termo_garantia_html,
	_termo_peca_cliente_html,
	_termo_retirada_html,
	ensure_service_order_print_formats,
	get_service_order_payment_print_context,
	get_service_order_print_context,
)
from tecponto_app.tecponto.pos import _receipt_html


TEST_USERS = {
	"Tecponto Atendente": ("front-atendente@tecponto.local", "Atendente Front"),
	"Tecponto Tecnico": ("front-tecnico@tecponto.local", "Técnico Front"),
	"Tecponto Gestor": ("front-gestor@tecponto.local", "Gestor Front"),
	"Tecponto Diretor": ("front-diretor@tecponto.local", "Diretor Front"),
}

DETAIL_DEMO_MARKER = "Fase 3.1b demo detail"
BUDGET_COST_GUARD_ITEM = "TP-FRONT-COST-GUARD"
BUDGET_COST_GUARD_VALUATION = 9876.54
POS_BARCODE_ITEM = "TP-PDV-BIPE"
POS_BARCODE_VALUE = "7891234567890"
POS_NAME_ITEM = "TP-PDV-NOME"
POS_DEMO_ITEMS = (
	(POS_BARCODE_ITEM, "Cabo USB-C PDV", "Cabos", 79.90, 11.11, POS_BARCODE_VALUE),
	(POS_NAME_ITEM, "Película 3D PDV", "Películas", 35.50, 7.77, None),
)


def run_foundation_checks() -> dict:
	previous_user = frappe.session.user
	previous_in_test = frappe.flags.in_test
	try:
		frappe.flags.in_test = True
		# Foundation provisions native ERPNext records; keep this independent from
		# whatever role a preceding integration scenario left in the session.
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		# Access control must initialize after the Tecponto roles themselves exist.
		# Running this first also makes later fixture users subject to the same
		# server-side anti-escalation rules as production users.
		user_access_checks = run_user_access_control_checks()
		user_management_checks = run_user_management_api_checks()
		administrative_center_checks = run_administrative_center_checks()
		users = {role: _find_or_create_user(role) for role in FRONTEND_ROLES}
		_ensure_default_test_cash_session(users["Tecponto Atendente"])
		company_identity_check = _check_company_identity(users["Tecponto Atendente"])
		panel_checks = _check_role_panels(users)
		orders_check = _check_service_order_api(users["Tecponto Gestor"])
		detail_check = _check_service_order_detail_api(users["Tecponto Atendente"])
		navigation_check = _check_attendant_navigation_apis(users["Tecponto Atendente"])
		metrics_check = _check_dashboard_metrics(users["Tecponto Atendente"])
		device_search_check = _check_customer_device_search(users["Tecponto Atendente"])
		statbar_guard = _check_statbar_guard(users["Tecponto Atendente"])
		manager_home_guard = _check_manager_home_guard(users["Tecponto Gestor"])
		director_financial_guard = _check_director_financial_guard(
			users["Tecponto Diretor"],
			users["Tecponto Gestor"],
			users["Tecponto Tecnico"],
			users["Tecponto Atendente"],
		)
		director_report_guard = _check_director_strategic_report_guard(
			users["Tecponto Diretor"],
			users["Tecponto Gestor"],
			users["Tecponto Tecnico"],
			users["Tecponto Atendente"],
		)
		director_risk_agenda_guard = _check_director_risk_agenda_guard(
			users["Tecponto Diretor"],
			users["Tecponto Gestor"],
			users["Tecponto Tecnico"],
			users["Tecponto Atendente"],
		)
		manager_operation_check = _check_manager_operation_scope(users["Tecponto Gestor"], users["Tecponto Atendente"])
		guard_check = _check_sensitive_guard(users["Tecponto Tecnico"])
		technician_scope_check = run_technician_scope_checks()
		technician_part_execution_check = run_technician_part_execution_checks()
		technician_commission_check = run_technician_commission_checks()
		lean_operation_check = run_lean_operation_checks()
		operation_config_check = run_operation_config_checks()
		technician_assignment_check = run_technician_assignment_checks(
			users["Tecponto Gestor"], users["Tecponto Atendente"], users["Tecponto Tecnico"]
		)
		diagnosis_handoff_check = run_diagnosis_handoff_checks(
			users["Tecponto Gestor"], users["Tecponto Atendente"], users["Tecponto Tecnico"]
		)
		technician_budget_leak_check = run_technician_budget_leak_checks(
			users["Tecponto Diretor"], users["Tecponto Atendente"], users["Tecponto Tecnico"]
		)
		k4_flow_check = run_k4_flow_projection_checks()
		cash_session_check = run_cash_session_checks()
		pos_cash_integration_check = run_pos_cash_integration_checks()
		cash_closing_check = run_cash_closing_checks()
		service_order_cash_check = run_service_order_cash_checks()
		per_order_finance_check = run_per_order_financial_summary_checks()
		technician_part_request_check = run_technician_part_request_checks()
		part_purchase_cycle_check = run_part_purchase_cycle_checks()
		part_receipt_check = run_part_receipt_reservation_checks()
		management_stock_scope_routing = _check_management_stock_scope_routing(
			users["Tecponto Gestor"],
			users["Tecponto Diretor"],
		)
		tradein_frontend_check = run_tradein_frontend_checks()
		post_sale_checks = run_post_sale_checks()
		used_device_warranty_lookup = run_used_device_warranty_lookup_checks()
		warranty_delivery_check = run_warranty_delivery_checks()
		budget_presentation_check = run_budget_presentation_checks()
		print_document_checks = run_print_document_checks()
		device_credential_guard = run_device_credential_non_leak_checks()
		os2_checkin_choices = run_os2_checkin_choice_checks()
		os3_cohesive_diagnosis = run_os3_cohesive_diagnosis_and_budget_checks()
		os4_approval_crm = run_os4_approval_and_quotes_crm_checks()
		os5_workflow_automations = run_os5_workflow_automations_checks()
		budget_cost_guard = _check_budget_item_cost_guard(users["Tecponto Atendente"])
		pos_cost_guard = _check_pos_item_cost_guard(
			users["Tecponto Atendente"],
			users["Tecponto Tecnico"],
		)
		cashier_mode_checks = run_cashier_mode_checks()
		multi_role_context = _check_multi_role_union(users["Tecponto Atendente"])
		# Each group intentionally creates documents with naming series. Commit the
		# completed fixtures before the approval suite starts a fresh transaction.
		frappe.db.commit()
		action_request_checks = run_action_request_checks()
		frappe.db.commit()
		notification_checks = run_notification_checks()
		daily_action_checks = run_daily_action_checks()
		quick_stage_checks = run_quick_stage_move_checks()
		customer_registration_checks = run_customer_registration_checks()
		registry_crud_checks = run_registry_crud_checks()
		service_catalog_checks = run_service_catalog_checks()
		product_category_checks = run_product_category_checks()
		product_variant_checks = run_product_variant_checks()
		marketplace_listing_checks = run_marketplace_listing_checks()
		marketplace_reporting_checks = run_marketplace_reporting_checks()
		defect_service_mapping_checks = run_defect_service_mapping_checks()
		stage_sla_checks = run_stage_sla_checks()
		stage_clock_checks = run_stage_clock_checks()
		public_acceptance_checks = run_public_acceptance_checks()
		workflow_metadata_gate_checks = run_workflow_metadata_gate_checks()
		link_acceptance_gate_checks = run_link_acceptance_gate_checks()
		no_repair_pickup_checks = run_no_repair_pickup_checks()
		inoperative_entry_term_checks = run_inoperative_entry_term_checks()
		tracking_checks = run_public_tracking_checks()
		unified_portal_checks = run_unified_portal_checks()
		tracking_budget_checks = run_public_tracking_budget_checks()
		tracking_lifecycle_checks = run_tracking_lifecycle_checks()
		return {
			"status": "ok",
			"panel_checks": panel_checks,
			"company_identity": company_identity_check,
			"service_order_api": orders_check,
			"service_order_detail_api": detail_check,
			"navigation_apis": navigation_check,
			"dashboard_metrics": metrics_check,
			"customer_device_search": device_search_check,
			"statbar_guard": statbar_guard,
			"manager_home_guard": manager_home_guard,
			"director_financial_guard": director_financial_guard,
			"director_report_guard": director_report_guard,
			"director_risk_agenda_guard": director_risk_agenda_guard,
			"manager_operation_scope": manager_operation_check,
			"diagnosis_handoff": diagnosis_handoff_check,
			"technician_budget_leak": technician_budget_leak_check,
			"k4_flow_projection": k4_flow_check,
			"sensitive_guard": guard_check,
			"technician_scope": technician_scope_check,
			"technician_part_execution": technician_part_execution_check,
			"technician_commissions": technician_commission_check,
			"lean_operation": lean_operation_check,
			"operation_config": operation_config_check,
			"technician_assignment": technician_assignment_check,
			"cash_session": cash_session_check,
			"pos_cash_integration": pos_cash_integration_check,
			"cash_closing": cash_closing_check,
			"service_order_cash": service_order_cash_check,
			"per_order_finance": per_order_finance_check,
			"technician_part_requests": technician_part_request_check,
			"part_purchase_cycle": part_purchase_cycle_check,
			"part_receipt_reservation": part_receipt_check,
			"management_stock_scope_routing": management_stock_scope_routing,
			"tradein_frontend": tradein_frontend_check,
			"post_sale": post_sale_checks,
			"used_device_warranty_lookup": used_device_warranty_lookup,
			"warranty_delivery": warranty_delivery_check,
			"budget_presentation": budget_presentation_check,
			"print_documents": print_document_checks,
			"device_credential_guard": device_credential_guard,
			"os2_checkin_choices": os2_checkin_choices,
			"os3_cohesive_diagnosis": os3_cohesive_diagnosis,
			"os4_approval_crm": os4_approval_crm,
			"os5_workflow_automations": os5_workflow_automations,
			"budget_cost_guard": budget_cost_guard,
			"pos_cost_guard": pos_cost_guard,
			"cashier_mode_checks": cashier_mode_checks,
			"multi_role_union": multi_role_context,
			"action_request_checks": action_request_checks,
			"notification_checks": notification_checks,
			"daily_action_checks": daily_action_checks,
			"quick_stage_checks": quick_stage_checks,
			"inoperative_entry_term": inoperative_entry_term_checks,
			"customer_registration_checks": customer_registration_checks,
			"registry_crud_checks": registry_crud_checks,
			"service_catalog_checks": service_catalog_checks,
			"product_category_checks": product_category_checks,
			"product_variant_checks": product_variant_checks,
			"marketplace_listing_checks": marketplace_listing_checks,
			"marketplace_reporting_checks": marketplace_reporting_checks,
			"defect_service_mapping_checks": defect_service_mapping_checks,
			"stage_sla_checks": stage_sla_checks,
			"stage_clock_checks": stage_clock_checks,
			"public_acceptance_checks": public_acceptance_checks,
			"workflow_metadata_gate_checks": workflow_metadata_gate_checks,
			"link_acceptance_gate_checks": link_acceptance_gate_checks,
			"no_repair_pickup_checks": no_repair_pickup_checks,
			"tracking_checks": tracking_checks,
			"unified_portal_checks": unified_portal_checks,
			"tracking_budget_checks": tracking_budget_checks,
			"tracking_lifecycle_checks": tracking_lifecycle_checks,
			"user_access_checks": user_access_checks,
			"user_management_checks": user_management_checks,
			"administrative_center": administrative_center_checks,
		}
	finally:
		frappe.flags.in_test = previous_in_test
		frappe.set_user(previous_user)


def run_k4_flow_projection_checks() -> dict:
	cases = [
		(frappe._dict(name="K4-EMPTY", workflow_state="Em diagnóstico", problem_found="", diagnosis_date=None), "Registrar diagnóstico"),
		(frappe._dict(name="K4-SAVED", workflow_state="Em diagnóstico", problem_found="Conector oxidado", diagnosis_date=today()), "Concluir diagnóstico e definir repasse"),
		(frappe._dict(name="K4-PRICE", workflow_state="Diagnosticado — aguardando orçamento", pricing_responsibility="Balcão", has_budget_lines=False), "Montar orçamento · Balcão"),
		(frappe._dict(name="K4-READY", workflow_state="Diagnosticado — aguardando orçamento", pricing_responsibility="Técnico", has_budget_lines=True), "Concluir orçamento · Técnico"),
		(frappe._dict(name="K4-NOT-SENT", workflow_state="Aguardando aprovação", quote_sent=False), "Enviar orçamento ao cliente"),
		(frappe._dict(name="K4-SENT", workflow_state="Aguardando aprovação", quote_sent=True), "Acompanhar aceite"),
	]
	# Synthetic names deliberately avoid database records; patch exists/count so the
	# projection is tested deterministically without coupling each substate to fixtures.
	with patch.object(frappe.db, "get_value", return_value=None), patch.object(frappe.db, "exists", return_value=False):
		for order, expected in cases:
			actual = action_for_service_order(order)
			if actual["label"] != expected:
				raise AssertionError(f"K.4 projetou '{actual['label']}' em vez de '{expected}'.")

	frontend_source = (Path(__file__).parents[3] / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
	for marker in ("detail.next_action", "Precificação com:", "Recebido por:", 'mode="transfer"'):
		if marker not in frontend_source:
			raise AssertionError(f"A amarra visual da K.4 não usa {marker!r}.")
	return {"status": "ok", "substates": len(cases), "shared_projection": True}


def run_technician_assignment_checks(manager: str, attendant: str, technician: str) -> dict:
	"""Exercise Pull/Dispatch, stale claims, transfer audit and the safe queue contract."""
	previous_user = frappe.session.user
	settings = frappe.get_single("Tecponto Settings")
	previous_mode = settings.technician_assignment_mode or "Dispatch"
	previous_alert = settings.unassigned_technician_alert_hours or 4
	second_technician = "front-tecnico-k1@tecponto.local"
	try:
		frappe.set_user("Administrator")
		if not frappe.db.exists("User", second_technician):
			user = frappe.get_doc({
				"doctype": "User", "email": second_technician, "first_name": "Técnico", "last_name": "K1",
				"enabled": 1, "user_type": "System User", "send_welcome_email": 0,
				"roles": [{"role": "Tecponto Tecnico"}],
			})
			user.insert(ignore_permissions=True)
		elif "Tecponto Tecnico" not in frappe.get_roles(second_technician):
			user = frappe.get_doc("User", second_technician)
			user.append("roles", {"role": "Tecponto Tecnico"})
			user.save(ignore_permissions=True)

		order = _create_action_request_service_order(attendant)
		frappe.db.set_value("Service Order", order, "technician", None, update_modified=False)
		frappe.db.set_single_value("Tecponto Settings", "technician_assignment_mode", "Pull")
		frappe.db.set_single_value("Tecponto Settings", "unassigned_technician_alert_hours", 4)
		frappe.clear_cache(doctype="Tecponto Settings")
		frappe.set_user(technician)
		available = list_unassigned_service_orders(limit=1000)
		if order not in {item["name"] for item in available["items"]} or contains_sensitive_field(available):
			raise AssertionError("Fila Pull não trouxe a OS segura e sem técnico.")
		# The two workers need independent MariaDB sessions. Commit only the fixture
		# setup so both connections can see the same unassigned row.
		frappe.db.commit()
		claim = _run_concurrent_claim_check(order, technician, second_technician)
		# MariaDB REPEATABLE READ keeps the fixture connection's earlier snapshot;
		# start a fresh read transaction before validating the workers' commits.
		frappe.db.rollback()
		if frappe.db.get_value("Service Order", order, "technician") != technician:
			raise AssertionError("A reivindicação atômica não preservou o primeiro técnico.")
		if frappe.db.count("Tecponto Service Order Assignment Event", {"service_order": order, "event_type": "Claim"}) != 1:
			raise AssertionError("A reivindicação não gerou exatamente um evento de auditoria.")

		frappe.set_user(manager)
		try:
			transfer_service_order(order, second_technician, "")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("Transferência sem observação foi aceita.")
		transfer = transfer_service_order(order, second_technician, "Redistribuição de bancada")
		transfer_event = frappe.get_doc("Tecponto Service Order Assignment Event", transfer["event"])
		if (
			transfer_event.event_type != "Transfer"
			or transfer_event.previous_technician != technician
			or transfer_event.new_technician != second_technician
			or transfer_event.performed_by != manager
			or transfer_event.observation != "Redistribuição de bancada"
			or not transfer_event.occurred_at
		):
			raise AssertionError("A transferência não preservou ator, origem, destino, data e motivo na auditoria.")
		if frappe.db.get_value("Service Order", order, "workflow_state") != "Em diagnóstico":
			raise AssertionError("O Pull não levou a OS assumida para Em diagnóstico.")

		dispatch_order = _create_action_request_service_order(attendant)
		frappe.db.set_value("Service Order", dispatch_order, "technician", None, update_modified=False)
		frappe.db.set_single_value("Tecponto Settings", "technician_assignment_mode", "Dispatch")
		frappe.clear_cache(doctype="Tecponto Settings")
		assigned = assign_service_order(dispatch_order, technician, "Distribuição do gestor")
		frappe.set_user(second_technician)
		try:
			claim_service_order(dispatch_order)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("Técnico reivindicou OS enquanto a operação estava em Dispatch.")

		intervention_order = _create_action_request_service_order(attendant)
		frappe.db.set_value("Service Order", intervention_order, "technician", None, update_modified=False)
		frappe.db.set_single_value("Tecponto Settings", "technician_assignment_mode", "Pull")
		frappe.clear_cache(doctype="Tecponto Settings")
		frappe.set_user(manager)
		try:
			assign_service_order(intervention_order, technician, "")
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("Intervenção no Pull sem justificativa foi aceita.")
		intervention = assign_service_order(intervention_order, technician, "Urgência: técnico ausente")
		intervention_event = frappe.get_doc("Tecponto Service Order Assignment Event", intervention["event"])
		if (
			intervention_event.event_type != "Intervention"
			or intervention_event.assignment_mode != "Pull"
			or intervention_event.observation != "Urgência: técnico ausente"
			or intervention_event.performed_by != manager
		):
			raise AssertionError("A intervenção no Pull não foi auditada como exceção.")

		frappe.set_user("Administrator")
		event = frappe.get_doc("Tecponto Service Order Assignment Event", transfer["event"])
		event.observation = "tentativa de adulteração"
		try:
			event.save(ignore_permissions=True)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("Evento de atribuição imutável pôde ser editado.")
		return {"status": "ok", "claim": claim["event"], "transfer": transfer["event"], "assign": assigned["event"], "intervention": intervention["event"]}
	finally:
		frappe.set_user("Administrator")
		frappe.db.set_single_value("Tecponto Settings", "technician_assignment_mode", previous_mode)
		frappe.db.set_single_value("Tecponto Settings", "unassigned_technician_alert_hours", previous_alert)
		frappe.clear_cache(doctype="Tecponto Settings")
		frappe.set_user(previous_user)


def _run_concurrent_claim_check(service_order: str, first_technician: str, second_technician: str) -> dict:
	"""Force real DB lock contention instead of hoping two threads collide by chance."""
	site = frappe.local.site
	sites_path = frappe.local.sites_path
	first_locked = Event()
	second_at_lock = Event()
	allow_second_sql = Event()
	second_sql_started = Event()
	second_sql_returned = Event()
	results: dict[str, Any] = {}

	def connect_worker(user: str) -> None:
		frappe.init(site=site, sites_path=sites_path)
		frappe.connect()
		frappe.set_user(user)

	def first_worker() -> None:
		try:
			connect_worker(first_technician)
			# Hold the exact row lock used by production before the second claim starts.
			frappe.db.sql(
				"SELECT name FROM `tabService Order` WHERE name=%s FOR UPDATE",
				(service_order,),
			)
			first_locked.set()
			if not second_at_lock.wait(10):
				raise AssertionError("A segunda transação não alcançou o SELECT FOR UPDATE.")
			allow_second_sql.set()
			if not second_sql_started.wait(10):
				raise AssertionError("A consulta concorrente não iniciou no MariaDB.")
			# Keep the first transaction's row lock long enough to prove that the
			# independently connected query cannot return before commit. The elapsed
			# time is also asserted after both workers finish.
			sleep(2)
			if second_sql_returned.is_set():
				raise AssertionError("A segunda transação atravessou um row lock ainda ativo.")
			results["winner"] = claim_service_order(service_order)
			frappe.db.commit()
		except Exception as error:
			results["first_error"] = error
			frappe.db.rollback()
		finally:
			allow_second_sql.set()
			frappe.destroy()

	def second_worker() -> None:
		try:
			connect_worker(second_technician)
			if not first_locked.wait(10):
				raise AssertionError("A primeira transação não adquiriu o row lock.")
			original_sql = frappe.db.sql

			def controlled_sql(query, *args, **kwargs):
				if "FOR UPDATE" not in str(query).upper():
					return original_sql(query, *args, **kwargs)
				second_at_lock.set()
				if not allow_second_sql.wait(10):
					raise AssertionError("O teste não liberou a tentativa concorrente.")
				started_at = monotonic()
				second_sql_started.set()
				try:
					return original_sql(query, *args, **kwargs)
				finally:
					results["loser_blocked_seconds"] = monotonic() - started_at
					second_sql_returned.set()

			frappe.db.sql = controlled_sql
			try:
				claim_service_order(service_order)
			except frappe.ValidationError as error:
				results["loser_error"] = str(error)
				frappe.db.rollback()
			else:
				results["second_winner"] = True
				frappe.db.commit()
		except Exception as error:
			results["second_error"] = error
			frappe.db.rollback()
		finally:
			frappe.destroy()

	first = Thread(target=first_worker, name="k1-first-claim")
	second = Thread(target=second_worker, name="k1-second-claim")
	first.start()
	second.start()
	first.join(20)
	second.join(20)
	if first.is_alive() or second.is_alive():
		raise AssertionError("As transações concorrentes não terminaram; possível deadlock.")
	if results.get("first_error"):
		raise results["first_error"]
	if results.get("second_error"):
		raise results["second_error"]
	if results.get("second_winner") or not results.get("winner"):
		raise AssertionError(f"A disputa não produziu exatamente um vencedor: {results}")
	if "já foi assumida" not in results.get("loser_error", ""):
		raise AssertionError(f"O perdedor não recebeu o conflito esperado: {results}")
	if results.get("loser_blocked_seconds", 0) < 1.5:
		raise AssertionError(f"A consulta perdedora não ficou bloqueada pelo row lock: {results}")
	return results["winner"]


def run_diagnosis_handoff_checks(manager: str, attendant: str, technician: str) -> dict:
	"""Prove the K.2 hand-off, including the safe K.2/K.3 capability boundary."""
	from frappe.model.workflow import apply_workflow

	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		restricted_order = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order", restricted_order,
			{"workflow_state": "Em diagnóstico", "technician": technician},
			update_modified=False,
		)
		frappe.set_user(technician)
		handoff = complete_technical_diagnosis(restricted_order, "Falha confirmada na alimentação.", "Balcão")
		if handoff["workflow_state"] != "Diagnosticado — aguardando orçamento":
			raise AssertionError("Conclusão não criou a etapa intermediária de precificação.")
		if handoff["diagnosis"]["pricing_responsibility"] != "Balcão" or not handoff["diagnosis"]["completed_by"]:
			raise AssertionError("Repasse não registrou responsável e autoria explicitamente.")
		if contains_sensitive_field(handoff):
			raise AssertionError("Repasse K.2 vazou campo sensível para o técnico.")

		frappe.set_user("Administrator")
		multi_role_order = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order", multi_role_order,
			{"workflow_state": "Em diagnóstico", "technician": technician},
			update_modified=False,
		)
		frappe.set_user(manager)
		continued = complete_technical_diagnosis(multi_role_order, "Conector danificado; substituição indicada.", "Técnico")
		if continued["diagnosis"]["pricing_responsibility"] != "Técnico":
			raise AssertionError("Usuário multipapel perdeu o caminho de orçamento já autorizado.")

		service_item = _get_demo_item(is_stock_item=0)
		add_service_order_budget_line(
			multi_role_order,
			{"type": "service", "item_code": service_item, "description": "Substituição do conector", "qty": 1, "rate": 180},
		)
		apply_workflow(
			frappe.as_json({"doctype": "Service Order", "name": multi_role_order}),
			"Aguardando aprovação",
		)
		if frappe.db.get_value("Service Order", multi_role_order, "workflow_state") != "Aguardando aprovação":
			raise AssertionError("OS precificada não avançou para aprovação.")

		frappe.set_user(technician)
		apply_workflow(
			frappe.as_json({"doctype": "Service Order", "name": restricted_order}),
			"Em diagnóstico",
		)
		reopened = frappe.get_doc("Service Order", restricted_order)
		if not reopened.budget_review_required:
			raise AssertionError("Reabrir diagnóstico não marcou a revisão do orçamento.")
		if reopened.pricing_responsibility != "Balcão":
			raise AssertionError("Reabertura apagou o histórico do repasse anterior.")
		return {"separate_operation": "Balcão", "multi_role": "Técnico", "review_warning": True}
	finally:
		frappe.set_user(previous_user)


def run_technician_budget_leak_checks(director: str, attendant: str, technician: str) -> dict:
	"""Prove all ten K.3 technician channels carry sale values and no cost sentinel."""
	previous_user = frappe.session.user
	settings = frappe.get_single("Tecponto Settings")
	previous_floor = settings.get("price_floor_block")
	cost_sentinels = {113.37, 127.41, 139.53}
	service_sale = 287.65
	part_sale = 431.29
	low_sale = 17.29
	forbidden_names = {
		"valuation_rate", "incoming_rate", "purchase_rate", "last_purchase_rate", "cost", "cost_price",
		"margin", "markup", "profit", "gross_profit", "supplier_rate",
	}
	part_item = None
	catalog_name = None
	warehouse = None
	original_item_rates = None
	original_catalog_price = None
	original_bin_valuation = None
	try:
		frappe.set_user("Administrator")
		order_name = _create_action_request_service_order(attendant)
		part_item = _get_demo_item(is_stock_item=1)
		warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
		original_item_rates = frappe.db.get_value("Item", part_item, ["standard_rate", "valuation_rate"], as_dict=True)
		original_bin_valuation = frappe.db.get_value("Bin", {"item_code": part_item, "warehouse": warehouse}, "valuation_rate")
		_ensure_pos_demo_stock(part_item, warehouse, valuation_rate=113.37)
		frappe.db.set_value("Item", part_item, {"standard_rate": part_sale, "valuation_rate": 127.41}, update_modified=False)
		frappe.db.set_value("Bin", {"item_code": part_item, "warehouse": warehouse}, "valuation_rate", 139.53, update_modified=False)
		catalog = frappe.db.get_value("Tecponto Service", {"active": 1}, ["name", "service_name"], as_dict=True)
		if not catalog:
			raise AssertionError("Catálogo técnico não possui serviço ativo para a prova K.3.")
		catalog_name = catalog.name
		original_catalog_price = frappe.db.get_value("Tecponto Service", catalog.name, "default_labor_price")
		frappe.db.set_value("Tecponto Service", catalog.name, "default_labor_price", service_sale, update_modified=False)
		order = frappe.get_doc("Service Order", order_name)
		order.set("services", [])
		order.set("parts", [])
		order.workflow_state = "Em diagnóstico"
		order.technician = technician
		order.save(ignore_permissions=True)

		frappe.set_user(technician)
		complete_technical_diagnosis(order_name, "Falha de placa confirmada para orçamento técnico.", "Técnico")

		channels: dict[str, Any] = {}
		channels["1_service_search"] = technical_budget.search_services(catalog.service_name, 10)
		_assert_technician_sale_safe("busca de serviços", channels["1_service_search"], {service_sale}, cost_sentinels, forbidden_names)
		channels["2_part_search"] = technical_budget.search_parts(part_item, 10)
		_assert_technician_sale_safe("busca de peças", channels["2_part_search"], {part_sale}, cost_sentinels, forbidden_names)

		created_service = technical_budget.add_line(order_name, {"type": "service", "catalog_service": catalog.name, "description": catalog.service_name, "qty": 1, "selling_price": service_sale, "duration": 2, "duration_unit": "Horas"})
		created_part = technical_budget.add_line(order_name, {"type": "part", "item_code": part_item, "description": "Peça segura K.3", "qty": 1, "selling_price": part_sale, "source": "Loja"})
		part_line = created_part["parts"][-1]
		channels["4_create_edit"] = technical_budget.update_line(order_name, "part", part_line["name"], {"qty": 1, "selling_price": part_sale})
		_assert_technician_sale_safe("criação e edição", channels["4_create_edit"], {service_sale, part_sale}, cost_sentinels, forbidden_names)
		channels["5_saved_response"] = technical_budget.get_budget(order_name)
		_assert_technician_sale_safe("resposta após salvar", channels["5_saved_response"], {service_sale, part_sale}, cost_sentinels, forbidden_names)

		channels["3_order_detail"] = get_service_order_detail(order_name)
		_assert_technician_sale_safe("detalhe da OS", channels["3_order_detail"], {service_sale, part_sale}, cost_sentinels, forbidden_names)
		channels["6_mesa"] = list_service_orders(limit=100)
		_assert_technician_sale_safe("Mesa", channels["6_mesa"], {service_sale + part_sale}, cost_sentinels, forbidden_names)
		channels["7_agenda"] = list_daily_actions("tecnico")
		_assert_technician_sale_safe("agenda", channels["7_agenda"], {service_sale + part_sale}, cost_sentinels, forbidden_names)

		frappe.db.set_single_value("Tecponto Settings", "price_floor_block", 1)
		frappe.clear_cache(doctype="Tecponto Settings")
		try:
			technical_budget.update_line(order_name, "part", part_line["name"], {"qty": 1, "selling_price": low_sale})
		except frappe.ValidationError as error:
			channels["8_validation_error"] = str(error)
		else:
			raise AssertionError("Preço técnico abaixo do piso não foi bloqueado pelo motor.")
		_assert_technician_sale_safe("erro de validação", channels["8_validation_error"], {low_sale}, cost_sentinels, forbidden_names)
		frappe.db.set_single_value("Tecponto Settings", "price_floor_block", 0)
		frappe.clear_cache(doctype="Tecponto Settings")

		channels["9_print"] = technical_budget.get_print_html(order_name)
		_assert_technician_sale_safe("impressão", channels["9_print"], {service_sale, part_sale}, cost_sentinels, forbidden_names)
		channels["10_export_list"] = {"export": technical_budget.export_budget(order_name), "list": list_service_orders(limit=100, query=order_name)}
		_assert_technician_sale_safe("exportação/listagem", channels["10_export_list"], {service_sale + part_sale}, cost_sentinels, forbidden_names)

		financial_blocked = False
		try:
			get_service_order_director_financial_summary(order_name)
		except frappe.PermissionError:
			financial_blocked = True
		if not financial_blocked:
			raise AssertionError("Técnico acessou o endpoint financeiro exclusivo do Diretor.")

		frontend_source = (Path(__file__).resolve().parents[3] / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
		technical_state = frontend_source.split("function TechnicalBudgetEditor", 1)[1].split("function TechnicalFinanceStageCard", 1)[0] if "function TechnicalFinanceStageCard" in frontend_source.split("function TechnicalBudgetEditor", 1)[1] else frontend_source.split("function TechnicalBudgetEditor", 1)[1].split("function TechnicalLineList", 1)[0]
		lower_state = technical_state.lower()
		if any(name in lower_state for name in forbidden_names) or any(str(value) in lower_state for value in cost_sentinels):
			raise AssertionError("Estado React do orçamento técnico referencia campo interno de custo.")

		technical_budget.complete_budget(order_name)
		if frappe.db.get_value("Service Order", order_name, "workflow_state") != "Aguardando aprovação":
			raise AssertionError("Conclusão técnica não encaminhou o orçamento para aprovação.")
		return {"status": "ok", "channels": sorted(channels), "sentinels": sorted(cost_sentinels), "director_endpoint_blocked": True, "react_state_safe": True}
	finally:
		frappe.set_user("Administrator")
		frappe.db.set_single_value("Tecponto Settings", "price_floor_block", previous_floor or 0)
		if part_item and original_item_rates:
			frappe.db.set_value("Item", part_item, dict(original_item_rates), update_modified=False)
		if part_item and warehouse and frappe.db.exists("Bin", {"item_code": part_item, "warehouse": warehouse}):
			frappe.db.set_value("Bin", {"item_code": part_item, "warehouse": warehouse}, "valuation_rate", original_bin_valuation or 0, update_modified=False)
		if catalog_name and original_catalog_price is not None:
			frappe.db.set_value("Tecponto Service", catalog_name, "default_labor_price", original_catalog_price, update_modified=False)
		frappe.clear_cache(doctype="Tecponto Settings")
		frappe.set_user(previous_user)


def _assert_technician_sale_safe(label: str, payload: Any, sale_values: set[float], cost_sentinels: set[float], forbidden_names: set[str]) -> None:
	serialized = frappe.as_json(payload).lower()
	for value in sale_values:
		variants = {str(value).lower(), f"{value:.2f}".lower(), f"{value:.2f}".replace(".", ",").lower()}
		if not any(variant in serialized for variant in variants):
			raise AssertionError(f"{label} não expôs o preço de venda esperado {value:.2f}.")
	leaks = contains_sensitive_field(payload, forbidden_values=cost_sentinels)
	if leaks or any(name in serialized for name in forbidden_names):
		raise AssertionError(f"{label} vazou custo/sensível: {leaks or 'nome de campo proibido'}")


def run_budget_presentation_checks() -> dict:
	"""Prove closed/discriminated quotes never expose part cost outside Director."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		director = _find_or_create_user("Tecponto Diretor")
		order_name = _create_action_request_service_order(attendant)
		repair_warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
		frappe.set_user("Administrator")
		part_item = _ensure_part_request_repair_item()
		_ensure_pos_demo_stock(part_item, repair_warehouse, valuation_rate=41.23)
		service_item = frappe.db.get_value("Item", {"item_code": "MO-REPARO", "disabled": 0}, "name")
		if not service_item:
			raise AssertionError("Item MO-REPARO não encontrado para a prova do orçamento.")

		frappe.set_user(attendant)
		with_service = add_service_order_budget_line(order_name, {"type": "service", "item_code": service_item, "description": "Troca de tela", "qty": 1, "rate": 180})
		service_row = with_service["services"][-1]["name"]
		add_service_order_budget_line(order_name, {"type": "part", "item_code": part_item, "description": "Tela compatível", "qty": 1, "rate": 320, "warehouse": repair_warehouse, "service_row": service_row})
		add_service_order_budget_line(order_name, {"type": "part", "description": "Tela fornecida pelo cliente", "qty": 1, "rate": 999, "part_source": "Cliente", "service_row": service_row, "customer_part_note": "Tela do cliente"})
		attendant_detail = get_service_order_detail(order_name)
		leaks = contains_sensitive_field(attendant_detail, forbidden_values={41.23})
		if leaks or attendant_detail.get("budget", {}).get("internal") is not None:
			raise AssertionError("Orçamento do atendente expôs custo ou composição interna.")
		closed = attendant_detail["budget"]["closed_lines"]
		if not any(flt(line["amount"]) == 500 for line in closed):
			raise AssertionError("Orçamento fechado não agregou preço de venda da peça ao serviço.")
		customer_part = next(row for row in attendant_detail["parts"] if row.get("part_source") == "Cliente")
		if flt(customer_part.get("amount")) != 0 or not attendant_detail["budget"]["customer_supplied_part_term_required"]:
			raise AssertionError("Peça do cliente não ficou sem preço/estoque e sem termo obrigatório.")

		frappe.set_user(director)
		director_financial = get_director_financial_summary()
		if "operational_cost" not in director_financial or "gross_operating_profit" not in director_financial:
			raise AssertionError("Diretor não recebeu a visão financeira exclusiva de custo e lucro bruto.")
		return {"closed_total": 500, "customer_part_stock": False, "attendant_leaked_fields": [], "director_financial": True}
	finally:
		frappe.set_user(previous_user)


def run_print_document_checks() -> dict:
	"""Exercise every customer/internal print projection without exposing internal cost."""
	previous_user = frappe.session.user
	settings = frappe.get_single("Tecponto Settings")
	original_trade_name = settings.get("trade_name")
	original_public_logo = settings.get("public_logo")
	try:
		ensure_frontend_foundation()
		ensure_service_order_print_formats()
		ensure_pos_receipt_print_format()
		ensure_pos_barcode_label_print_format()
		attendant = _find_or_create_user("Tecponto Atendente")
		order_name = _create_action_request_service_order(attendant)
		order = frappe.get_doc("Service Order", order_name)
		brand_name = f"Oficina Impressão {frappe.generate_hash(length=6)}"
		settings.trade_name = brand_name
		settings.public_logo = "/assets/tecponto_app/branding/logo-dark.svg"
		settings.save(ignore_permissions=True)

		frappe.db.set_value(
			"Customer Device",
			order.customer_device,
			"device_password",
			"SENHA-INTERNA-NAO-IMPRIMIR-CLIENTE",
			update_modified=False,
		)
		frappe.db.set_value(
			"Service Order",
			order.name,
			{
				"problem_found": "Falha confirmada no conjunto de tela.",
				"probable_cause": "Impacto físico anterior.",
				"recommended_solution": "Substituir o conjunto de tela.",
				"diagnosis_notes": "Teste funcional documentado.",
				"pickup_date": add_days(now_datetime(), -2),
				"warranty_expiry": add_days(nowdate(), 88),
			},
			update_modified=False,
		)
		order.reload()

		frappe.set_user("Administrator")
		repair_warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
		part_item = _ensure_part_request_repair_item()
		_ensure_pos_demo_stock(part_item, repair_warehouse, valuation_rate=BUDGET_COST_GUARD_VALUATION)
		frappe.set_user(attendant)
		add_service_order_budget_line(
			order.name,
			{
				"type": "part",
				"item_code": part_item,
				"description": "Componente comercial discriminado",
				"warehouse": repair_warehouse,
				"qty": 1,
				"rate": 320,
			},
		)
		add_service_order_budget_line(
			order.name,
			{
				"type": "part",
				"part_source": "Cliente",
				"description": "Componente fornecido pelo cliente",
				"customer_part_note": "Cliente confirmou a origem da peça.",
				"qty": 1,
				"rate": 999,
			},
		)
		order.reload()
		frappe.db.set_value(
			"Service Order Part",
			next(row.name for row in order.parts if row.part_source != "Cliente"),
			"valuation_rate",
			BUDGET_COST_GUARD_VALUATION,
			update_modified=False,
		)
		order.reload()

		from tecponto_app.tecponto.service_order.customer_supplied_part import build_customer_supplied_part_term

		term = build_customer_supplied_part_term(order)
		frappe.get_doc(
			{
				"doctype": "OS Acceptance",
				"service_order": order.name,
				"acceptance_type": "Orçamento",
				"signer_role": "Dono",
				"status": "Concluído",
				"token_hash": frappe.generate_hash(length=32),
				"expires_on": add_days(now_datetime(), 1),
				"issued_by": attendant,
				"customer_part_term_version": term["version"],
				"customer_part_term_text": term["text"],
				"customer_part_term_accepted_on": now_datetime(),
			}
		).insert(ignore_permissions=True)

		payment = frappe.get_doc(
			{
				"doctype": "Tecponto Service Order Payment",
				"service_order": order.name,
				"payment_kind": "Aparelho como pagamento",
				"direction": "Entrada",
				"amount": 350,
				"payment_mode": "Aparelho como pagamento",
				"affects_drawer": 0,
				"reason": "Compensação por aparelho usado.",
				"idempotency_key": f"print-payment-{frappe.generate_hash(length=16)}",
				"request_hash": frappe.generate_hash(length=32),
			}
		)
		payment.insert(ignore_permissions=True)

		service_templates = {
			PF_TERMO_ENTRADA: _termo_entrada_html(),
			PF_TERMO_RETIRADA: _termo_retirada_html(),
			PF_OS_ORCAMENTO: _os_orcamento_html(),
			PF_OS_ORCAMENTO_DISCRIMINADO: _os_orcamento_discriminado_html(),
			PF_LAUDO_TECNICO: _laudo_tecnico_html(),
			PF_TERMO_GARANTIA: _termo_garantia_html(),
			PF_TERMO_PECA_CLIENTE: _termo_peca_cliente_html(),
			PF_ETIQUETA_QR: _etiqueta_qr_html(),
			PF_ETIQUETA_INTERNA: _etiqueta_interna_html(),
		}
		rendered = {name: frappe.render_template(template, {"doc": order}) for name, template in service_templates.items()}
		rendered[PF_TERMO_APARELHO_PAGAMENTO] = frappe.render_template(
			_termo_aparelho_pagamento_html(), {"doc": payment}
		)

		internal_password = "SENHA-INTERNA-NAO-IMPRIMIR-CLIENTE"
		a4_documents = set(rendered) - {PF_ETIQUETA_QR, PF_ETIQUETA_INTERNA}
		for name, html in rendered.items():
			if brand_name not in html:
				raise AssertionError(f"{name} não refletiu a identidade comercial configurada.")
			if name in a4_documents and settings.public_logo not in html:
				raise AssertionError(f"{name} não refletiu o logo comercial configurado.")
			if name != PF_ETIQUETA_INTERNA and internal_password in html:
				raise AssertionError(f"{name} imprimiu senha de aparelho em documento não interno.")
			if any(marker in html for marker in ("valuation_rate", str(BUDGET_COST_GUARD_VALUATION), "gross_margin")):
				raise AssertionError(f"{name} expôs custo, margem ou valuation interno.")
		if internal_password not in rendered[PF_ETIQUETA_INTERNA] or "USO INTERNO" not in rendered[PF_ETIQUETA_INTERNA]:
			raise AssertionError("Etiqueta interna não restringiu claramente a senha ao uso interno.")

		closed = rendered[PF_OS_ORCAMENTO]
		itemized = rendered[PF_OS_ORCAMENTO_DISCRIMINADO]
		store_part = "Componente comercial discriminado"
		if store_part in closed or store_part not in itemized:
			raise AssertionError("Orçamento fechado/discriminado não separou corretamente a composição de venda.")
		if "Componente fornecido pelo cliente" not in rendered[PF_TERMO_PECA_CLIENTE]:
			raise AssertionError("Termo de peça do cliente não imprimiu a identificação registrada.")

		context = get_service_order_print_context(order)
		if context["pickup_date"] not in rendered[PF_TERMO_GARANTIA] or context["warranty_expiry"] not in rendered[PF_TERMO_GARANTIA]:
			raise AssertionError("Termo de garantia não imprimiu retirada real e validade configurada.")
		payment_context = get_service_order_payment_print_context(payment)
		if payment_context["payment"]["amount_fmt"] not in rendered[PF_TERMO_APARELHO_PAGAMENTO]:
			raise AssertionError("Termo de aparelho como pagamento não imprimiu o abatimento registrado.")

		for name in (PF_TERMO_ENTRADA, PF_TERMO_RETIRADA, PF_OS_ORCAMENTO, PF_OS_ORCAMENTO_DISCRIMINADO, PF_LAUDO_TECNICO, PF_TERMO_GARANTIA, PF_TERMO_PECA_CLIENTE, PF_ETIQUETA_QR, PF_ETIQUETA_INTERNA, PF_TERMO_APARELHO_PAGAMENTO):
			if not frappe.db.exists("Print Format", name):
				raise AssertionError(f"Formato de impressão {name} não foi provisionado.")
			print_format = frappe.get_doc("Print Format", name)
			if name not in {PF_ETIQUETA_QR, PF_ETIQUETA_INTERNA} and (
				"tp.qr_code" not in print_format.html or "Acompanhe sua OS" not in print_format.html
			):
				raise AssertionError(f"{name} não recebeu o QR comum de acompanhamento da OS.")
			if 'font-family: "Space Grotesk"' not in print_format.css:
				raise AssertionError(f"{name} não recebeu a base visual configurada da marca.")
		for name in (POS_RECEIPT_PRINT_FORMAT, POS_RECEIPT_58_PRINT_FORMAT, POS_BARCODE_LABEL_PRINT_FORMAT):
			if not frappe.db.exists("Print Format", name):
				raise AssertionError(f"Formato de etiqueta/cupom {name} não foi provisionado.")
		if "size: 58mm" not in _receipt_css(58) or "size: 80mm" not in _receipt_css(80):
			raise AssertionError("CSS térmico não aplicou as larguras 58mm e 80mm.")
		return {
			"identity_reflected": True,
			"customer_documents_without_password": True,
			"internal_password_label_only": True,
			"closed_quote": True,
			"itemized_quote_sale_prices_only": True,
			"warranty_from_pickup": True,
			"portal_qr_on_all_documents": True,
			"formats_provisioned": len(rendered) + 3,
		}
	finally:
		settings.trade_name = original_trade_name
		settings.public_logo = original_public_logo
		settings.save(ignore_permissions=True)
		frappe.set_user(previous_user)


def run_device_credential_non_leak_checks() -> dict:
	"""OS.2 sentinel: the device credential never crosses a customer/public/restricted channel."""
	previous_user = frappe.session.user
	sentinel = f"OS2-CREDENCIAL-SENTINELA-{frappe.generate_hash(length=18)}"
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		order_name = _create_action_request_service_order(attendant)
		frappe.set_user("Administrator")
		order = frappe.get_doc("Service Order", order_name)
		order.device_access_type = "Alfanumérica"
		order.device_access_credential = sentinel
		order.save(ignore_permissions=True)
		order.reload()
		if order.get_password("device_access_credential") != sentinel:
			raise AssertionError("Credencial da OS não foi persistida pelo armazenamento protegido de Password.")

		customer_templates = {
			PF_TERMO_ENTRADA: _termo_entrada_html(),
			PF_TERMO_RETIRADA: _termo_retirada_html(),
			PF_OS_ORCAMENTO: _os_orcamento_html(),
			PF_OS_ORCAMENTO_DISCRIMINADO: _os_orcamento_discriminado_html(),
			PF_LAUDO_TECNICO: _laudo_tecnico_html(),
			PF_TERMO_GARANTIA: _termo_garantia_html(),
			PF_TERMO_PECA_CLIENTE: _termo_peca_cliente_html(),
			PF_ETIQUETA_QR: _etiqueta_qr_html(),
		}
		channels: dict[str, Any] = {
			"customer_documents": {
				name: frappe.render_template(template, {"doc": order, "tp": get_service_order_print_context(order)})
				for name, template in customer_templates.items()
			},
			"communication": _quote_send_text(order, "WhatsApp", "Orçamento disponível"),
		}
		frappe.set_user(attendant)
		channels["budget"] = get_service_order_detail(order.name).get("budget")
		tracking = issue_tracking_link(order.name)
		frappe.set_user("Guest")
		channels["public_link"] = get_public_tracking(tracking["link"].rstrip("/").rsplit("/", 1)[-1])
		frappe.set_user(technician)
		unauthorized_blocked = False
		try:
			channels["unauthorized_technician"] = get_service_order_detail(order.name)
		except frappe.PermissionError:
			unauthorized_blocked = True

		for channel, payload in channels.items():
			if sentinel in frappe.as_json(payload):
				raise AssertionError(f"Credencial-sentinela da OS vazou no canal {channel}.")
		return {
			"status": "ok",
			"sentinel_not_leaked": True,
			"channels": sorted(channels),
			"unauthorized_technician_blocked": unauthorized_blocked,
		}
	finally:
		frappe.set_user(previous_user)


def run_os2_checkin_choice_checks() -> dict:
	"""Persist all credential controls and the optional budget through the real check-in API."""
	previous_user = frappe.session.user
	try:
		attendant = _find_or_create_user("Tecponto Atendente")
		frappe.set_user(attendant)
		suffix = frappe.generate_hash(length=10).upper()
		photo = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAghX7JQAAAABJRU5ErkJggg=="
		credentials = {
			"PIN": "5937",
			"Padrão de desenho": "1-2-5-8-9",
			"Alfanumérica": "OS2-Ab9#sentinela",
		}
		orders: dict[str, str] = {}
		for index, (access_type, credential) in enumerate(credentials.items(), start=1):
			response = create_service_order_checkin(
				{
					"customer": {"customer_name": f"Cliente OS2 {suffix}-{index}", "mobile_no": "11999998888", "custom_whatsapp": "11999998888", "custom_nao_possui_cpf": 1, "custom_rg": f"RG-{suffix}-{index}"},
					"device": {"brand": "Teste", "model": f"OS2-{index}", "imei_serial": f"OS2-{suffix}-{index}"},
					"service_order": {
						"reported_defect": "Teste funcional OS.2",
						"physical_state": "Sem avarias adicionais",
						"entry_operating_condition": ENTRY_OPERATING_CONDITION_OK,
						"device_access_type": access_type,
						"device_access_credential": credential,
						"include_initial_budget": index == 1,
					},
					"initial_budget_lines": ([{"type": "service", "description": "Serviço inicial OS.2", "qty": 2, "rate": 75}] if index == 1 else []),
					"entry_photo": {"data_url": photo, "filename": f"os2-{index}.png"},
				}
			)
			order_name = response["service_order"]["name"]
			order = frappe.get_doc("Service Order", order_name)
			if order.device_access_type != access_type or order.get_password("device_access_credential") != credential:
				raise AssertionError(f"Credencial do tipo {access_type} não persistiu na OS.")
			orders[access_type] = order_name

		budget_order = frappe.get_doc("Service Order", orders["PIN"])
		line = next((row for row in budget_order.services if row.description == "Serviço inicial OS.2"), None)
		if not line or flt(line.qty) != 2 or flt(line.rate) != 75:
			raise AssertionError("Composição do orçamento inicial não persistiu no orçamento real da OS.")
		return {"status": "ok", "credential_types": sorted(orders), "initial_budget_persisted": True}
	finally:
		frappe.set_user(previous_user)


def run_os3_cohesive_diagnosis_and_budget_checks() -> dict:
	"""Prove cohesive diagnosis and budget stage: technical handoff, budget mutation and presentation."""
	previous_user = frappe.session.user
	try:
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		suffix = frappe.generate_hash(length=8).upper()

		# 1. Create OS and assign technician in Em diagnóstico
		frappe.set_user(attendant)
		order_name = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order",
			order_name,
			{"technician": technician, "workflow_state": "Em diagnóstico"},
			update_modified=False,
		)

		# 2. Save technical diagnosis draft as technician
		frappe.set_user(technician)
		saved_detail = save_technical_diagnosis(order_name, "Laudo técnico inicial: placa sem curto primário, conector de carga oxidado.")
		if saved_detail["diagnosis"]["problem_found"] != "Laudo técnico inicial: placa sem curto primário, conector de carga oxidado.":
			raise AssertionError("Rascunho de laudo técnico não persistiu na OS.")

		# 3. Conclude diagnosis with technician pricing responsibility
		completed_detail = complete_technical_diagnosis(order_name, "Laudo técnico final: desoxidação do conector e substituição da bateria.", "Técnico")
		if completed_detail["diagnosis"]["pricing_responsibility"] != "Técnico":
			raise AssertionError("Repasse da precificação ao técnico não foi registrado.")

		# 4. Add service and part lines
		added_service = add_service_order_budget_line(
			order_name,
			{
				"line_type": "service",
				"description": "Desoxidação de conector e limpeza química",
				"qty": 1,
				"rate": 150.0,
				"duration": 2,
				"duration_unit": "Horas",
			},
		)
		part_item = _get_demo_item(is_stock_item=1)
		warehouse = _get_demo_warehouse()
		added_part = add_service_order_budget_line(
			order_name,
			{
				"line_type": "part",
				"item_code": part_item,
				"description": "Bateria Original iPhone 13",
				"qty": 1,
				"rate": 280.0,
				"part_source": "Loja",
				"warehouse": warehouse,
			},
		)

		order_doc = frappe.get_doc("Service Order", order_name)
		service_row = next((row for row in order_doc.services if row.description == "Desoxidação de conector e limpeza química"), None)
		part_row = next((row for row in order_doc.parts if row.description == "Bateria Original iPhone 13"), None)
		if not service_row or not part_row:
			raise AssertionError("Linhas de mão de obra e peças não foram salvas na OS.")

		service_row_name = service_row.name
		part_row_name = part_row.name

		# 5. Update presentation toggle
		presentation_closed = update_service_order_budget_presentation(order_name, "Fechado")
		if presentation_closed["budget"]["presentation"] != "Fechado":
			raise AssertionError("Formato do orçamento não alternou para Fechado.")

		presentation_disc = update_service_order_budget_presentation(order_name, "Discriminado")
		if presentation_disc["budget"]["presentation"] != "Discriminado":
			raise AssertionError("Formato do orçamento não alternou para Discriminado.")

		# 6. Remove a budget line
		after_remove = remove_service_order_budget_line(order_name, part_row_name, "part")
		order_doc = frappe.get_doc("Service Order", order_name)
		if any(row.name == part_row_name for row in order_doc.parts):
			raise AssertionError("Item de peça não foi removido do orçamento da OS.")

		# 7. Check sensitive fields guard (cost/margin/profit) for technician
		leaks = contains_sensitive_field(after_remove)
		if leaks:
			raise AssertionError(f"Técnico recebeu campos confidenciais de custo na etapa de diagnóstico/orçamento: {leaks}")

		return {
			"status": "ok",
			"diagnosis_persisted": True,
			"budget_mutations_tested": True,
			"cost_guard_verified": True,
		}
	finally:
		frappe.set_user(previous_user)


def run_os4_approval_and_quotes_crm_checks() -> dict:
	"""Prove approval decision stage, follow-ups persistence and CRM quote funnel."""
	previous_user = frappe.session.user
	try:
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		suffix = frappe.generate_hash(length=8).upper()

		# 1. Create OS in Aguardando aprovação
		frappe.set_user(attendant)
		order_name = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order",
			order_name,
			{
				"technician": technician,
				"workflow_state": "Aguardando aprovação",
				"approval_status": "Pendente",
				"quote_locked": 1,
				"os_contact_name": f"Contato OS4 {suffix}",
				"os_contact_phone": "11988887777",
			},
			update_modified=False,
		)
		send_service_order_quote(order_name, {"channel": "WhatsApp", "notes": "Proposta enviada pelo atendente."})

		# 2. Record follow-up contact attempt
		after_followup = record_quote_follow_up(
			order_name,
			channel="WhatsApp",
			result="Pediu mais tempo",
			notes="Cliente solicitou retorno amanhã às 14h após aprovar com o sócio.",
		)
		# Verify comment on document
		comments = frappe.get_all(
			"Comment",
			filters={"reference_doctype": "Service Order", "reference_name": order_name},
			fields=["content", "comment_by"],
		)
		if not any("Pediu mais tempo" in (c.get("content") or "") for c in comments):
			raise AssertionError("Follow-up de orçamento não persistiu nos comentários da OS.")

		# 3. Test CRM panel projection and sensitive fields guard
		crm_panel = get_quotes_crm_panel(status="pending", query=suffix)
		if not any(item["name"] == order_name for item in crm_panel["items"]):
			raise AssertionError("OS aguardando aprovação não apareceu no CRM de orçamentos.")
		crm_item = next(item for item in crm_panel["items"] if item["name"] == order_name)
		if crm_item["approval_status"] != "Pendente":
			raise AssertionError("Status no CRM de orçamentos incorreto.")
		if crm_item["grand_total"] <= 0:
			raise AssertionError("Total comercial da OS no CRM de orçamentos deve ser maior que zero.")
		if not crm_item.get("follow_ups") or crm_item["follow_ups"][0]["result"] != "Pediu mais tempo":
			raise AssertionError("Histórico de follow-ups não apareceu no card/projeção do CRM.")

		# Check cost guard on CRM panel for attendant
		leaks = contains_sensitive_field(crm_panel)
		if leaks:
			raise AssertionError(f"Campos confidenciais vazados no painel CRM de orçamentos: {leaks}")

		# 4. Test approval decision
		approved_detail = decide_service_order_budget(
			order_name,
			payload={
				"decision": "approve",
				"channel": "WhatsApp",
				"notes": "Cliente aprovou troca completa via WhatsApp.",
				"attachment": "data:image/png;base64," + b64encode(b"crm-private-proof").decode(),
			},
		)
		if approved_detail["approval_status"] != "Aprovado" or approved_detail["workflow_state"] != "Aprovado":
			raise AssertionError("Decisão de aprovação não moveu o estado da OS para Aprovado.")
		if approved_detail["approval"]["channel"] != "WhatsApp":
			raise AssertionError("Canal de aprovação não foi persistido.")
		proof = frappe.db.get_value(
			"File",
			{"attached_to_doctype": "Service Order", "attached_to_name": order_name},
			["name", "is_private"],
			as_dict=True,
			order_by="creation desc",
		)
		if not proof or not proof.is_private:
			raise AssertionError("Comprovante real não foi anexado privadamente à OS.")

		# 5. Test rejection decision on a second OS
		order_name_2 = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order",
			order_name_2,
			{
				"technician": technician,
				"workflow_state": "Aguardando aprovação",
				"approval_status": "Pendente",
				"quote_locked": 1,
			},
			update_modified=False,
		)

		rejected_detail = decide_service_order_budget(
			order_name_2,
			payload={
				"decision": "reject",
				"channel": "Presencial",
				"notes": "Preço elevado — cliente achou caro e desistiu do reparo.",
			},
		)
		if rejected_detail["approval_status"] != "Reprovado" or rejected_detail["workflow_state"] != "Reprovado":
			raise AssertionError("Decisão de reprovação não moveu o estado da OS para Reprovado.")

		# Em andamento é definido exclusivamente pela retirada física.
		crm_in_progress = get_quotes_crm_panel(status="rejected", in_progress=True)
		if not any(item["name"] == order_name_2 for item in crm_in_progress["items"]):
			raise AssertionError("OS recusada sem retirada saiu indevidamente de Em andamento no CRM.")
		list_in_progress = list_service_orders(status="Reprovado", in_progress=True, limit=100)
		if not any(item["name"] == order_name_2 for item in list_in_progress["items"]):
			raise AssertionError("OS recusada sem retirada saiu indevidamente da lista Em andamento.")
		kanban_in_progress = get_service_order_kanban(status="Reprovado", in_progress=True, limit_per_column=40)
		if not any(item["name"] == order_name_2 for column in kanban_in_progress["columns"] for item in column["items"]):
			raise AssertionError("OS recusada sem retirada saiu indevidamente da Mesa Em andamento.")
		frappe.db.set_value("Service Order", order_name_2, "pickup_date", now_datetime(), update_modified=False)
		if any(item["name"] == order_name_2 for item in get_quotes_crm_panel(status="rejected", in_progress=True)["items"]):
			raise AssertionError("OS retirada continuou indevidamente em andamento no CRM.")
		if any(item["name"] == order_name_2 for item in list_service_orders(status="Reprovado", in_progress=True, limit=100)["items"]):
			raise AssertionError("OS retirada continuou indevidamente na lista Em andamento.")
		if any(item["name"] == order_name_2 for column in get_service_order_kanban(status="Reprovado", in_progress=True, limit_per_column=40)["columns"] for item in column["items"]):
			raise AssertionError("OS retirada continuou indevidamente na Mesa Em andamento.")
		if not any(item["name"] == order_name_2 for item in get_quotes_crm_panel(status="rejected", in_progress=False)["items"]):
			raise AssertionError("Período/histórico do CRM não incluiu a OS retirada com o status combinado.")
		if not any(item["name"] == order_name_2 for item in list_service_orders(status="Reprovado", in_progress=False, limit=100)["items"]):
			raise AssertionError("Período/histórico da lista não incluiu a OS retirada com o status combinado.")

		return {
			"status": "ok",
			"followup_persisted": True,
			"crm_panel_verified": True,
			"approval_decision_tested": True,
			"rejection_decision_tested": True,
			"physical_pickup_filter_verified": True,
			"cost_guard_verified": True,
		}
	finally:
		frappe.set_user(previous_user)


def run_os5_workflow_automations_checks() -> dict:
	"""Prove the 6 end-to-end workflow automations:

	1. Enviar orçamento moves automatically to 'Aguardando aprovação'.
	2. Customer approval via link moves automatically to execution ('Em reparo') and notifies technician.
	3. Manual approval without attached evidence is blocked; with attached evidence succeeds.
	4. OS timeline logs include the employee name on each action.
	5. Laudo técnico is optional (does not block OS lifecycle or quote send).
	6. Direct pricing: line added with custom selling price without cost leakage.
	"""
	previous_user = frappe.session.user
	try:
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		suffix = frappe.generate_hash(length=8).upper()

		# --- 1 & 5 & 6. Enviar orçamento auto-transition + Laudo opcional + Preço direto ---
		frappe.set_user(attendant)
		order_1 = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order",
			order_1,
			{
				"technician": technician,
				"workflow_state": "Em diagnóstico",
				"problem_found": "",
				"os_contact_name": f"Cliente Auto1 {suffix}",
				"os_contact_phone": "11988889999",
			},
			update_modified=False,
		)
		service_res = add_service_order_budget_line(
			order_1,
			{
				"type": "service",
				"description": "Troca de Tela Direta",
				"rate": 280.0,
				"qty": 1,
			},
		)
		services = service_res.get("services") or []
		if not services or services[-1].get("amount") != 280.0:
			raise AssertionError("Preço direto não foi respeitado na montagem da linha de orçamento.")

		sent_detail = send_service_order_quote(order_1, {"channel": "WhatsApp", "notes": "Proposta direta enviada."})
		if sent_detail["workflow_state"] != "Aguardando aprovação" or sent_detail["approval_status"] != "Pendente":
			raise AssertionError("Envio do orçamento não moveu automaticamente para Aguardando aprovação.")
		if not sent_detail.get("totals", {}).get("quote_locked"):
			raise AssertionError("Envio do orçamento não travou a proposta para aprovação.")

		# --- 3. Exigência de comprovante na aprovação manual ---
		manual_blocked = False
		try:
			decide_service_order_budget(
				order_1,
				payload={
					"decision": "approve",
					"channel": "WhatsApp",
					"notes": "Tentativa sem comprovante",
				},
			)
		except frappe.ValidationError as error:
			manual_blocked = True
			if "comprovante" not in str(error):
				raise AssertionError(f"Erro inesperado no bloqueio de aprovação manual: {error}")
		if not manual_blocked:
			raise AssertionError("Aprovação manual sem comprovante/documento anexado não foi bloqueada.")

		manual_approved = decide_service_order_budget(
			order_1,
			payload={
				"decision": "approve",
				"channel": "WhatsApp",
				"notes": "Autorizado com print de conversa",
				"attachment": "data:image/png;base64," + b64encode(b"manual-private-proof").decode(),
			},
		)
		if manual_approved["workflow_state"] != "Aprovado" or manual_approved["approval_status"] != "Aprovado":
			raise AssertionError("Aprovação manual com comprovante não moveu para Aprovado.")

		# --- 4. Log da OS com nome do funcionário em cada ação ---
		detail_with_timeline = get_service_order_detail(order_1)
		timeline = detail_with_timeline.get("timeline") or []
		if not timeline:
			raise AssertionError("Timeline da OS está vazia.")
		has_employee_name = any("· por " in (event.get("detail") or "") for event in timeline)
		if not has_employee_name:
			raise AssertionError("Timeline da OS não contém o nome do funcionário responsável nas ações.")

		# --- 2. Cliente aprova pelo link -> Transição automática para Execução + Notifica Técnico ---
		order_2 = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order",
			order_2,
			{
				"technician": technician,
				"workflow_state": "Aguardando aprovação",
				"approval_status": "Pendente",
				"quote_locked": 1,
				"os_contact_name": f"Cliente Link {suffix}",
				"os_contact_phone": "11977776666",
			},
			update_modified=False,
		)
		add_service_order_budget_line(
			order_2,
			{"type": "service", "description": "Reparo de Placa Link", "rate": 350.0, "qty": 1},
		)
		send_service_order_quote(order_2, {"channel": "WhatsApp", "notes": "Enviado link para aprovação"})

		customer = frappe.db.get_value("Service Order", order_2, "customer")
		frappe.db.set_value("Customer", customer, {"custom_cpf": "12345678909", "mobile_no": "11977776666"}, update_modified=False)

		tracking_res = issue_tracking_link(order_2)
		token = tracking_res["link"].rstrip("/").rsplit("/", 1)[-1]
		frappe.set_user("Guest")
		budget_info = start_public_tracking_budget_acceptance(token, "12345678909")
		budget_token = budget_info["link"].rstrip("/").rsplit("/", 1)[-1]

		camera_image = BytesIO()
		camera_seed = int(frappe.generate_hash(length=8), 16)
		Image.new(
			"RGB",
			(24, 24),
			color=(camera_seed & 0xFF, (camera_seed >> 8) & 0xFF, (camera_seed >> 16) & 0xFF),
		).save(camera_image, format="JPEG")
		camera_selfie = "data:image/jpeg;base64," + b64encode(camera_image.getvalue()).decode()
		signature_image = BytesIO()
		signature_canvas = Image.new("RGB", (640, 180), color=(250, 250, 250))
		signature_draw = ImageDraw.Draw(signature_canvas)
		signature_draw.line([(40, 120), (180, 50), (300, 135), (430, 45), (580, 110)], fill=(32, 36, 40), width=5)
		signature_canvas.save(signature_image, format="PNG")
		signature_data = "data:image/png;base64," + b64encode(signature_image.getvalue()).decode()

		save_public_acceptance_selfie(budget_token, camera_selfie)
		complete_public_acceptance(budget_token, signature_data, 1)

		approved_link_order = frappe.get_doc("Service Order", order_2)
		if approved_link_order.workflow_state != "Em reparo":
			raise AssertionError(f"Aprovação pelo link não moveu automaticamente para Em reparo (estado atual: {approved_link_order.workflow_state}).")
		if approved_link_order.approval_status != "Aprovado":
			raise AssertionError("Status de aprovação não foi gravado como Aprovado.")

		comments = frappe.get_all("Comment", filters={"reference_doctype": "Service Order", "reference_name": order_2}, fields=["content"])
		if not any("Avanço automático" in (c.get("content") or "") for c in comments):
			raise AssertionError("Comentário de avanço automático e notificação do técnico não foi gravado.")

		return {
			"status": "ok",
			"auto_transition_on_quote_send": True,
			"auto_transition_on_link_approval": True,
			"manual_approval_evidence_enforced": True,
			"timeline_employee_names_verified": True,
			"optional_laudo_verified": True,
			"direct_pricing_verified": True,
		}
	finally:
		frappe.set_user(previous_user)


def _check_company_identity(user: str) -> dict:
	"""Company + Settings must drive every customer-facing commercial label."""
	settings = frappe.get_single("Tecponto Settings")
	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		raise AssertionError("Nenhuma Company nativa está disponível para a identidade comercial.")
	original = {field: settings.get(field) for field in ("identity_company", "trade_name", "public_phone", "public_email", "public_address", "public_logo")}
	brand_name = f"Oficina Identidade {frappe.generate_hash(length=6)}"
	try:
		settings.update(
			{
				"identity_company": company,
				"trade_name": brand_name,
				"public_phone": "(11) 99999-0000",
				"public_email": "contato@identidade.test",
				"public_address": "Rua de Teste, 100 - Centro",
			}
		)
		settings.save(ignore_permissions=True)
		identity = get_company_identity()
		public_identity = get_public_company_identity()
		previous_response = frappe._dict(frappe.local.response)
		try:
			get_pwa_manifest()
			manifest = json.loads(frappe.local.response.filecontent)
			if (
				manifest["name"] != brand_name
				or manifest["start_url"] != "/tecponto"
				or frappe.local.response.content_type != "application/manifest+json"
			):
				raise AssertionError("O manifesto PWA não usou a identidade comercial configurada.")
		finally:
			frappe.local.response.clear()
			frappe.local.response.update(previous_response)
		frappe.set_user(user)
		boot = get_boot()
		if identity != public_identity or boot["identity"] != identity:
			raise AssertionError("Login, páginas públicas e bootstrap não compartilharam a mesma identidade comercial.")
		if identity["display_name"] != brand_name or identity["company"] != company:
			raise AssertionError("Tecponto Settings não prevaleceu sobre o nome técnico do aplicativo.")
		if {"valuation_rate", "cost", "margin", "commission", "profit"} & set(identity):
			raise AssertionError("A projeção pública de identidade contém dado financeiro proibido.")
		# The base template is rendered for /tecponto and public pages. Its identity
		# helper must be registered in Frappe's supported Jinja hook surface.
		identity_method = frappe.get_jenv().globals.get("get_company_identity")
		if not identity_method or identity_method()["display_name"] != brand_name:
			raise AssertionError("O template base não recebeu a identidade comercial pelo hook Jinja.")
		for page in (acceptance_page, tracking_page, frontend_page):
			context = frappe._dict()
			page.get_context(context)
			if context.identity["display_name"] != brand_name:
				raise AssertionError("Uma página pública não recebeu a identidade comercial configurada.")
		for template in (_termo_entrada_html(), _termo_retirada_html(), _os_orcamento_html(), _receipt_html()):
			if not any(reference in template for reference in ("company.display_name", "company.legal_name", "tp_company.display_name", "tp_company.legal_name")):
				raise AssertionError("Um documento comercial não resolve a marca pela camada única de identidade.")
		return {"company": identity["company"], "display_name": identity["display_name"], "public_fields": sorted(identity)}
	finally:
		settings.update(original)
		settings.save(ignore_permissions=True)


def run_public_tracking_checks() -> dict:
	"""Prove the guest tracking projection is opaque, minimal, and state-driven."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		frappe.set_user(attendant)
		service_order = _create_action_request_service_order(attendant)
		issued = issue_tracking_link(service_order)
		raw_token = issued["link"].rstrip("/").rsplit("/", 1)[-1]
		if raw_token == service_order or len(raw_token) < 24 or service_order in raw_token:
			raise AssertionError("Link público de rastreio não recebeu token opaco não-adivinhável.")
		tracking_doc = frappe.get_doc("Service Order Tracking", issued["tracking"])
		if raw_token in frappe.as_json(tracking_doc.as_dict()) or tracking_doc.token_hash == raw_token:
			raise AssertionError("Token bruto de rastreio foi persistido no banco.")

		device = frappe.db.get_value("Service Order", service_order, "customer_device")
		full_imei = frappe.db.get_value("Customer Device", device, "imei_serial") or ""
		state_results = []
		for state in TRACKING_STAGES:
			values = {"workflow_state": state}
			if state == "Aguardando aprovação":
				values["approval_deadline"] = add_days(now_datetime(), 2)
			frappe.db.set_value("Service Order", service_order, values, update_modified=True)
			frappe.set_user("Guest")
			public = get_public_tracking(raw_token)
			if not public.get("valid") or public["service_order"]["workflow_state"] != state:
				raise AssertionError(f"Rastreio público não refletiu o estado {state}.")
			current = [step for step in public["timeline"] if step["state"] == "current"]
			if len(current) != 1 or current[0]["stage"] != state:
				raise AssertionError(f"Linha do tempo não destacou corretamente {state}.")
			state_results.append(state)

		if full_imei and full_imei in frappe.as_json(public):
			raise AssertionError("Rastreio público expôs o IMEI completo.")
		if full_imei and not public["service_order"]["imei_suffix"].endswith(full_imei[-4:]):
			raise AssertionError("Rastreio público não exibiu apenas os últimos dígitos do IMEI.")
		leaks = contains_sensitive_field(public)
		if leaks:
			raise AssertionError(f"Rastreio público expôs campos sensíveis: {', '.join(leaks)}")
		if {"customer", "password", "internal_notes", "sales_invoice", "services", "parts"} & set(public["service_order"]):
			raise AssertionError("Rastreio público expôs campos fora da projeção mínima.")

		tampered = raw_token[:-1] + ("A" if raw_token[-1] != "A" else "B")
		invalid = get_public_tracking(tampered)
		if invalid.get("valid") or invalid.get("message") != INVALID_LINK_MESSAGE or "service_order" in invalid:
			raise AssertionError("Token adulterado vazou a existência ou os dados da OS.")

		frappe.set_user(attendant)
		expiring = issue_tracking_link(service_order)
		expiring_token = expiring["link"].rstrip("/").rsplit("/", 1)[-1]
		frappe.db.set_value("Service Order Tracking", expiring["tracking"], "expires_on", add_to_date(now_datetime(), hours=-1))
		frappe.set_user("Guest")
		expired = get_public_tracking(expiring_token)
		if expired.get("valid") or frappe.db.get_value("Service Order Tracking", expiring["tracking"], "status") != "Expirado":
			raise AssertionError("Token expirado continuou disponível para o público.")

		return {
			"status": "ok",
			"guest_read_only": True,
			"states_checked": state_results,
			"imei_partial": public["service_order"]["imei_suffix"],
			"tampered_token_blocked": True,
			"expired_token_blocked": True,
			"sensitive_guard": {"leaked_fields": leaks},
		}
	finally:
		frappe.set_user(previous_user)


def run_unified_portal_checks() -> dict:
	"""Prove one evolving portal link, secure lookup and non-public evidence history."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		frappe.set_user(attendant)
		service_order = _create_action_request_service_order(attendant)
		frappe.db.set_value("Service Order", service_order, "link_acceptance_required", 1, update_modified=False)
		order = frappe.get_doc("Service Order", service_order)
		frappe.db.set_value("Customer", order.customer, {"custom_cpf": "12345678909", "mobile_no": "11999998888", "custom_whatsapp": "11999998888"}, update_modified=False)
		legacy_tracking = issue_tracking_link(service_order)
		token = legacy_tracking["link"].rstrip("/").rsplit("/", 1)[-1]
		tracking = issue_tracking_link(service_order)
		if frappe.db.get_value("Service Order Tracking", legacy_tracking["tracking"], "status") != "Substituído":
			raise AssertionError("Reemissão do portal não preservou o link anterior como substituído.")

		frappe.set_user("Guest")
		entry_portal = get_public_portal(token)
		if not entry_portal.get("valid") or [action["key"] for action in entry_portal["portal_actions"]] != ["entry"]:
			raise AssertionError("Portal não exibiu a ação de aceite de entrada no estado real da OS.")
		entry_acceptance = start_public_portal_action(token, "entry", "123.456.789-09")
		acceptance_token = entry_acceptance["link"].rstrip("/").rsplit("/", 1)[-1]
		camera = BytesIO(); Image.new("RGB", (24, 24), color=(10, 20, 30)).save(camera, format="JPEG")
		signature = BytesIO()
		signature_canvas = Image.new("RGB", (640, 180), color=(250, 250, 250))
		ImageDraw.Draw(signature_canvas).line([(40, 120), (180, 50), (300, 135), (430, 45), (580, 110)], fill=(20, 30, 40), width=5)
		signature_canvas.save(signature, format="PNG")
		save_public_acceptance_selfie(acceptance_token, "data:image/jpeg;base64," + b64encode(camera.getvalue()).decode())
		complete_public_acceptance(acceptance_token, "data:image/png;base64," + b64encode(signature.getvalue()).decode(), 1)
		entry_after = get_public_portal(token)
		if any(action["key"] == "entry" for action in entry_after["portal_actions"]):
			raise AssertionError("Ação de entrada permaneceu no portal após aceite concluído.")
		if not entry_after["acceptance_history"] or "selfie_file" in frappe.as_json(entry_after) or "signature_file" in frappe.as_json(entry_after):
			raise AssertionError("Histórico público expôs evidência privada ou não registrou o aceite.")

		frappe.db.set_value("Service Order", service_order, "workflow_state", "Aguardando aprovação", update_modified=True)
		budget_portal = get_public_portal(token)
		if not any(action["key"] == "budget" for action in budget_portal["portal_actions"]):
			raise AssertionError("Portal não evoluiu para a ação de orçamento.")

		lookup = lookup_public_portal(service_order, "11999998888")
		if not lookup.get("valid") or token in frappe.as_json(lookup):
			raise AssertionError("Busca pública não criou sessão opaca ou vazou o token permanente.")
		lookup_token = lookup["portal_url"].rstrip("/").rsplit("/", 1)[-1]
		lookup_portal = get_public_portal(lookup_token)
		if not lookup_portal.get("valid") or lookup_portal["service_order"]["number"] != service_order:
			raise AssertionError("Sessão opaca da busca não abriu o mesmo portal.")
		wrong = lookup_public_portal(service_order, "00000000000")
		if wrong.get("valid") or wrong.get("message") != "Não foi possível localizar um atendimento com esses dados." or "service_order" in wrong:
			raise AssertionError("Busca com identidade errada vazou a existência da OS.")
		# The public lookup must remain neutral while rate limiting repeated probes.
		lookup_rate_key = "tecponto:portal-lookup-attempts:test"
		frappe.cache().delete_value(lookup_rate_key)
		for _ in range(5):
			attempt = lookup_public_portal(service_order, "00000000000")
			if attempt.get("valid") or attempt.get("message") != "Não foi possível localizar um atendimento com esses dados.":
				raise AssertionError("Tentativa pública inválida deixou de retornar erro neutro.")
		rate_limited = False
		try:
			lookup_public_portal(service_order, "00000000000")
		except frappe.PermissionError:
			rate_limited = True
		if not rate_limited:
			raise AssertionError("Busca pública não limitou tentativas repetidas do mesmo IP.")
		frappe.cache().delete_value(lookup_rate_key)
		leaks = contains_sensitive_field({"portal": lookup_portal, "lookup": lookup})
		if leaks:
			raise AssertionError(f"Portal público vazou dado sensível: {', '.join(leaks)}")
		return {"status": "ok", "single_link_evolves": True, "legacy_link_redirects": True, "entry_action_clears": True, "history_private": True, "lookup_session_opaque": True, "lookup_mismatch_neutral": True, "lookup_rate_limited": True, "leaked_fields": leaks}
	finally:
		frappe.cache().delete_value("tecponto:portal-lookup-attempts:test")
		frappe.set_user(previous_user)


def run_public_tracking_budget_checks() -> dict:
	"""Prove a guest decision reuses the motor and cannot bypass deadline or reason rules."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")

		def prepare_order() -> str:
			frappe.set_user(attendant)
			order_name = _create_action_request_service_order(attendant)
			frappe.db.set_value(
				"Service Order",
				order_name,
				{
					"workflow_state": "Aguardando aprovação",
					"approval_status": "Pendente",
					"approval_deadline": add_days(now_datetime(), 2),
					"entry_photos": "/private/files/tracking-entry.jpg",
					"entry_signature": "data:image/png;base64,tracking-entry-signature",
				},
				update_modified=True,
			)
			part = (frappe.get_doc("Service Order", order_name).get("parts") or [None])[0]
			if not part:
				raise AssertionError("OS de rastreio não possui a peça necessária ao teste de aprovação.")
			valuation_rate = flt(frappe.db.get_value("Item", part.item_code, "valuation_rate") or 10)
			_ensure_pos_demo_stock(part.item_code, part.warehouse, valuation_rate)
			frappe.db.set_value(
				"Customer",
				frappe.db.get_value("Service Order", order_name, "customer"),
				{"custom_cpf": "12345678909", "custom_rg": "MG-12.345.678", "custom_nao_possui_cpf": 0},
				update_modified=False,
			)
			return order_name

		approve_order = prepare_order()
		approve_link = issue_tracking_link(approve_order)
		approve_token = approve_link["link"].rstrip("/").rsplit("/", 1)[-1]
		frappe.set_user("Guest")
		public_budget = get_public_tracking(approve_token)
		budget = public_budget.get("budget") or {}
		if not budget.get("services") or not budget.get("parts") or not budget.get("total"):
			raise AssertionError("Rastreio em aprovação não exibiu orçamento de serviço, peça e total.")
		for line in [*budget["services"], *budget["parts"]]:
			if set(line) != {"description", "quantity", "unit_price", "line_total"}:
				raise AssertionError("Linha pública do orçamento contém campo interno.")
		leaks = contains_sensitive_field(public_budget)
		if leaks:
			raise AssertionError(f"Orçamento público expôs campo sensível: {', '.join(leaks)}")
		identity_mismatch_blocked = False
		try:
			start_public_tracking_budget_acceptance(approve_token, "000.000.000-00")
		except frappe.PermissionError:
			identity_mismatch_blocked = True
		if not identity_mismatch_blocked:
			raise AssertionError("Aprovação pública aceitou CPF/RG que não pertence ao titular da OS.")
		rg_order = prepare_order()
		frappe.db.set_value(
			"Customer",
			frappe.db.get_value("Service Order", rg_order, "customer"),
			{"custom_cpf": "", "custom_rg": "MG-12.345.678", "custom_nao_possui_cpf": 1},
			update_modified=False,
		)
		rg_link = issue_tracking_link(rg_order)
		rg_token = rg_link["link"].rstrip("/").rsplit("/", 1)[-1]
		rg_acceptance = start_public_tracking_budget_acceptance(rg_token, "mg 12.345.678")
		if frappe.db.get_value("OS Acceptance", rg_acceptance["acceptance"], "identity_document_type") != "RG":
			raise AssertionError("Aceite de orçamento não aceitou RG do titular quando CPF não está disponível.")
		# Restore the fixture's CPF path for the remaining deadline scenario.
		frappe.db.set_value(
			"Customer",
			frappe.db.get_value("Service Order", rg_order, "customer"),
			{"custom_cpf": "12345678909", "custom_nao_possui_cpf": 0},
			update_modified=False,
		)

		budget_acceptance = start_public_tracking_budget_acceptance(approve_token, "123.456.789-09")
		budget_token = budget_acceptance["link"].rstrip("/").rsplit("/", 1)[-1]
		budget_acceptance_doc = frappe.get_doc("OS Acceptance", budget_acceptance["acceptance"])
		if budget_token in frappe.as_json(budget_acceptance_doc.as_dict()) or budget_acceptance_doc.identity_document_type != "CPF":
			raise AssertionError("Aceite de orçamento não protegeu o token ou não auditou o tipo de documento validado.")
		camera_image = BytesIO()
		camera_seed = int(frappe.generate_hash(length=8), 16)
		Image.new(
			"RGB",
			(24, 24),
			color=(camera_seed & 0xFF, (camera_seed >> 8) & 0xFF, (camera_seed >> 16) & 0xFF),
		).save(camera_image, format="JPEG")
		camera_selfie = "data:image/jpeg;base64," + b64encode(camera_image.getvalue()).decode()
		signature_image = BytesIO()
		signature_canvas = Image.new("RGB", (640, 180), color=(250, 250, 250))
		signature_draw = ImageDraw.Draw(signature_canvas)
		signature_draw.line([(40, 120), (180, 50), (300, 135), (430, 45), (580, 110)], fill=(32, 36, 40), width=5)
		signature_draw.rectangle((620, 160, 635, 175), fill=(camera_seed % 255, 36, 40))
		signature_canvas.save(signature_image, format="PNG")
		signature_data = "data:image/png;base64," + b64encode(signature_image.getvalue()).decode()
		save_public_acceptance_selfie(budget_token, camera_selfie)
		approval = complete_public_acceptance(budget_token, signature_data, 1)
		budget_acceptance_doc.reload()
		approved_doc = frappe.get_doc("Service Order", approve_order)
		if (
			not approval.get("completed")
			or approved_doc.workflow_state not in {"Aprovado", "Em reparo", "Aguardando peça"}
			or approved_doc.approval_status != "Aprovado"
			or approved_doc.approval_channel != "Link"
			or not approved_doc.approval_date
			or not approved_doc.quote_locked
			or budget_acceptance_doc.status != "Concluído"
		):
			raise AssertionError("Aprovação pelo link não reexecutou o motor com canal Link e timestamp.")
		decision_repeat_blocked = False
		try:
			start_public_tracking_budget_acceptance(approve_token, "12345678909")
		except frappe.ValidationError:
			decision_repeat_blocked = True
		if not decision_repeat_blocked:
			raise AssertionError("Link permitiu decidir duas vezes o mesmo orçamento.")

		reject_order = prepare_order()
		reject_link = issue_tracking_link(reject_order)
		reject_token = reject_link["link"].rstrip("/").rsplit("/", 1)[-1]
		frappe.set_user("Guest")
		rejection_reason_required = False
		try:
			decide_public_tracking_budget(reject_token, "reject")
		except frappe.ValidationError:
			rejection_reason_required = True
		if not rejection_reason_required:
			raise AssertionError("Reprovação por link aceitou motivo vazio.")
		rejection = decide_public_tracking_budget(reject_token, "reject", "Prefiro não autorizar o reparo neste momento.")
		rejected_doc = frappe.get_doc("Service Order", reject_order)
		if not rejection.get("completed") or rejected_doc.workflow_state != "Reprovado" or rejected_doc.approval_channel != "Link":
			raise AssertionError("Reprovação por link não reexecutou o motor com rastreio Link.")

		expired_order = prepare_order()
		expired_link = issue_tracking_link(expired_order)
		expired_token = expired_link["link"].rstrip("/").rsplit("/", 1)[-1]
		frappe.db.set_value("Service Order", expired_order, "approval_deadline", add_to_date(now_datetime(), hours=-1), update_modified=False)
		frappe.set_user("Guest")
		expired_blocked = False
		try:
			start_public_tracking_budget_acceptance(expired_token, "12345678909")
		except frappe.ValidationError:
			expired_blocked = True
		if not expired_blocked or frappe.db.get_value("Service Order", expired_order, "workflow_state") != "Aguardando aprovação":
			raise AssertionError("Orçamento com prazo expirado foi decidido pelo link.")
		return {
			"status": "ok",
			"budget_visible": True,
			"approval_channel": approved_doc.approval_channel,
			"approved_state": approved_doc.workflow_state,
			"rejected_state": rejected_doc.workflow_state,
			"rejection_reason_required": rejection_reason_required,
			"decision_repeat_blocked": decision_repeat_blocked,
			"identity_mismatch_blocked": identity_mismatch_blocked,
			"rg_identity_accepted": True,
			"budget_acceptance": budget_acceptance_doc.name,
			"expired_blocked": expired_blocked,
			"sensitive_guard": {"leaked_fields": leaks},
		}
	finally:
		frappe.set_user(previous_user)


def run_tracking_lifecycle_checks() -> dict:
	"""Prove check-in issuance, delivery retention, expiry, revocation, and internal API access."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		suffix = frappe.generate_hash(length=8).upper()
		photo = BytesIO()
		Image.new("RGB", (24, 24), color=(20, 40, 60)).save(photo, format="JPEG")
		photo_data = "data:image/jpeg;base64," + b64encode(photo.getvalue()).decode()

		frappe.set_user(attendant)
		checkin = create_service_order_checkin(
			{
				"customer": {
					"customer_name": f"Cliente Rastreio {suffix}",
					"mobile_no": "11999998888",
					"custom_whatsapp": "11999998888",
					"custom_nao_possui_cpf": 1,
					"custom_rg": f"RG-{suffix}",
				},
				"device": {
					"brand": "Apple",
					"model": "iPhone Rastreio",
					"imei_serial": f"35{int(suffix, 16) % 10**13:013d}",
				},
				"service_order": {
					"reported_defect": "Teste do ciclo de vida do link de rastreio.",
					"physical_state": "Sem danos aparentes.",
				},
				"entry_photo": {"data_url": photo_data, "filename": f"tracking-{suffix}.jpg"},
			}
		)
		order_name = checkin["service_order"]["name"]
		issued = checkin.get("tracking") or {}
		raw_token = (issued.get("link") or "").rstrip("/").rsplit("/", 1)[-1]
		if len(raw_token) < 24 or not issued.get("qr_svg", "").startswith("data:image/svg+xml;base64,"):
			raise AssertionError("Check-in não retornou link de rastreio opaco com QR Code.")
		tracking_doc = frappe.get_doc("Service Order Tracking", issued["tracking"])
		if tracking_doc.expires_on or raw_token in frappe.as_json(tracking_doc.as_dict()):
			raise AssertionError("Link de rastreio não ficou ativo durante o reparo sem persistir o token bruto.")

		pickup_inside_retention = add_days(now_datetime(), -89)
		warranty_expiry = add_days(nowdate(), 1)
		frappe.db.set_value(
			"Service Order",
			order_name,
			{"workflow_state": "Entregue", "pickup_date": pickup_inside_retention, "warranty_expiry": warranty_expiry},
			update_modified=False,
		)
		on_service_order_updated(frappe.get_doc("Service Order", order_name))
		tracking_doc.reload()
		if not tracking_doc.expires_on or tracking_doc.expires_on <= now_datetime():
			raise AssertionError("Entrega não definiu a retenção de 90 dias do link de rastreio.")
		frappe.set_user("Guest")
		within_retention = get_public_tracking(raw_token)
		if not within_retention.get("valid") or not within_retention["service_order"].get("warranty_expiry"):
			raise AssertionError("Rastreio entregue dentro de 90 dias não exibiu a garantia.")

		frappe.db.set_value("Service Order", order_name, "pickup_date", add_days(now_datetime(), -91), update_modified=False)
		on_service_order_updated(frappe.get_doc("Service Order", order_name))
		expired = get_public_tracking(raw_token)
		if expired.get("valid") or frappe.db.get_value("Service Order Tracking", issued["tracking"], "status") != "Expirado":
			raise AssertionError("Link não expirou após 90 dias da retirada.")

		frappe.set_user(attendant)
		integration_link = issue_service_order_tracking_link(order_name)
		if not integration_link.get("link") or not integration_link.get("qr_svg"):
			raise AssertionError("API interna não disponibilizou um link de rastreio para integrações futuras.")
		frappe.set_user(manager)
		revoked = revoke_service_order_tracking_link(integration_link["tracking"])
		if revoked.get("status") != "Revogado":
			raise AssertionError("Gestor não conseguiu revogar o link de rastreio.")
		frappe.set_user("Guest")
		if get_public_tracking(integration_link["link"].rstrip("/").rsplit("/", 1)[-1]).get("valid"):
			raise AssertionError("Link revogado continuou acessível publicamente.")

		leaks = contains_sensitive_field(within_retention)
		if leaks:
			raise AssertionError(f"Ciclo de vida do rastreio expôs campos sensíveis: {', '.join(leaks)}")
		return {
			"status": "ok",
			"generated_at_checkin": True,
			"delivered_within_retention": True,
			"expired_after_90_days": True,
			"revoked_by_manager": True,
			"integration_api": True,
			"sensitive_guard": {"leaked_fields": leaks},
		}
	finally:
		frappe.set_user(previous_user)


def run_defect_service_mapping_checks() -> dict:
	"""Prove defects drive editable service suggestions and never block check-in."""
	previous_user = frappe.session.user
	created_mapping = None
	created_order = None
	try:
		ensure_frontend_foundation()
		manager = _find_or_create_user("Tecponto Gestor")
		attendant = _find_or_create_user("Tecponto Atendente")
		frappe.set_user(manager)
		mappings = list_defect_service_mappings(include_inactive=True)["items"]
		screen_mapping = next((item for item in mappings if item["defect"] == "Tela quebrada" and item["active"]), None)
		battery_mapping = next((item for item in mappings if item["defect"] == "Bateria descarregando r\u00e1pido" and item["active"]), None)
		if not screen_mapping or not battery_mapping:
			raise AssertionError("Semente de mapeamento defeito -> servico nao foi criada.")

		suffix = frappe.generate_hash(length=8).upper()
		created_mapping = save_defect_service_mapping(
			{
				"defect": f"Defeito teste {suffix}",
				"catalog_service": screen_mapping["catalog_service"],
				"active": True,
			}
		)["item"]["name"]
		if not created_mapping:
			raise AssertionError("Gestor nao conseguiu editar/criar o mapeamento.")

		frappe.set_user(attendant)
		attendant_mappings = list_defect_service_mappings(include_inactive=True)["items"]
		attendant_leaks = contains_sensitive_field(attendant_mappings)
		if attendant_leaks:
			raise AssertionError(f"Consulta de mapeamentos vazou campo sensível: {', '.join(attendant_leaks)}")
		no_defect = get_checkin_delivery_suggestion({"defects": [], "lead_time_business_hours": 0})
		if no_defect["suggested_delivery_date"] or no_defect["mapped_services"]:
			raise AssertionError("Previsao foi calculada sem defeito/servico mapeado.")
		single = get_checkin_delivery_suggestion({"defects": ["Tela quebrada"], "lead_time_business_hours": 0})
		multiple = get_checkin_delivery_suggestion(
			{"defects": ["Tela quebrada", "Bateria descarregando r\u00e1pido"], "lead_time_business_hours": 0}
		)
		if (
			not single["suggested_delivery_date"]
			or [service["name"] for service in single["mapped_services"]] != [screen_mapping["catalog_service"]]
			or multiple["service_business_hours"] <= single["service_business_hours"]
		):
			raise AssertionError("Defeitos mapeados nao sugeriram servicos/prazos distintos.")

		write_blocked = False
		try:
			save_defect_service_mapping({"name": created_mapping, "defect": f"Defeito teste {suffix}", "catalog_service": battery_mapping["catalog_service"], "active": True})
		except frappe.PermissionError:
			write_blocked = True
		if not write_blocked:
			raise AssertionError("Atendente alterou mapeamento defeito -> servico.")

		photo = BytesIO()
		Image.new("RGB", (24, 24), color=(20, 40, 60)).save(photo, format="JPEG")
		photo_data = "data:image/jpeg;base64," + b64encode(photo.getvalue()).decode()
		checkin = create_service_order_checkin(
			{
				"customer": {
					"customer_name": f"Cliente mapa {suffix}",
					"mobile_no": "11999998888",
					"custom_whatsapp": "11999998888",
					"custom_nao_possui_cpf": 1,
					"custom_rg": f"RG-MAP-{suffix}",
				},
				"device": {"brand": "Apple", "model": "iPhone mapa", "imei_serial": f"35{int(suffix, 16) % 10**13:013d}"},
				"service_order": {
					"reported_defect": "Tela quebrada e bateria descarregando rapido.",
					"defects": ["Tela quebrada", "Bateria descarregando r\u00e1pido"],
					"physical_state": "Sem danos adicionais aparentes.",
					"include_initial_budget": True,
				},
				"entry_photo": {"data_url": photo_data, "filename": f"mapping-{suffix}.jpg"},
			}
		)
		created_order = checkin["service_order"]["name"]
		services = frappe.get_doc("Service Order", created_order).get("services") or []
		if {row.catalog_service for row in services} != {screen_mapping["catalog_service"], battery_mapping["catalog_service"]}:
			raise AssertionError("Check-in nao preencheu o orcamento com os servicos sugeridos.")

		return {
			"status": "ok",
			"no_defect_has_no_estimate": True,
			"mapped_defect_suggests_service": True,
			"multiple_distinct_defects_sum_durations": True,
			"catalog_lines_suggested_on_checkin": True,
			"manager_mapping_editable": True,
			"attendant_mapping_write_blocked": write_blocked,
			"attendant_mapping_consultation": bool(attendant_mappings),
			"leaked_fields": attendant_leaks,
		}
	finally:
		if created_mapping and frappe.db.exists("Tecponto Defect Service Mapping", created_mapping):
			frappe.delete_doc("Tecponto Defect Service Mapping", created_mapping, ignore_permissions=True, force=True)
		frappe.set_user(previous_user)


def run_stage_sla_checks() -> dict:
	"""Prove SLA defaults, commercial hours, editable suggestion, and non-blocking check-in."""
	previous_user = frappe.session.user
	original_entry_sla = None
	created_order = None
	try:
		ensure_frontend_foundation()
		manager = _find_or_create_user("Tecponto Gestor")
		attendant = _find_or_create_user("Tecponto Atendente")
		frappe.set_user("Administrator")
		slas = get_stage_slas()
		entry_sla = next((row for row in slas if row["workflow_state"] == "Entrada criada"), None)
		if not entry_sla or entry_sla["business_hours"] != 4:
			raise AssertionError("SLA default de Entrada criada não foi carregado.")
		original_entry_sla = dict(entry_sla)

		friday = datetime(2026, 7, 17, 17, 0)
		monday = add_commercial_business_hours(friday, 4)
		if monday != datetime(2026, 7, 20, 12, 0):
			raise AssertionError(f"Cálculo comercial não pulou fim de semana/expediente: {monday!s}")

		before = get_checkin_delivery_suggestion({"defects": ["Tela quebrada"], "lead_time_business_hours": 9})
		updated = save_stage_sla(
			{
				"workflow_state": "Entrada criada",
				"business_hours": 10,
				"description": "Teste temporário de SLA.",
				"active": True,
			}
		)["item"]
		after = get_checkin_delivery_suggestion({"defects": ["Tela quebrada"], "lead_time_business_hours": 9})
		if updated["business_hours"] != 10 or after["total_business_hours"] != before["total_business_hours"] + 6:
			raise AssertionError("Edição do SLA não alterou a sugestão de entrega.")

		photo = BytesIO()
		Image.new("RGB", (24, 24), color=(20, 40, 60)).save(photo, format="JPEG")
		photo_data = "data:image/jpeg;base64," + b64encode(photo.getvalue()).decode()
		suffix = frappe.generate_hash(length=8).upper()
		frappe.set_user(attendant)
		checkin = create_service_order_checkin(
			{
				"customer": {
					"customer_name": f"Cliente SLA {suffix}",
					"mobile_no": "11999998888",
					"custom_whatsapp": "11999998888",
					"custom_nao_possui_cpf": 1,
					"custom_rg": f"RG-SLA-{suffix}",
				},
				"device": {
					"brand": "Apple",
					"model": "iPhone SLA",
					"imei_serial": f"35{int(suffix, 16) % 10**13:013d}",
				},
				"service_order": {
					"reported_defect": "",
					"physical_state": "Sem danos aparentes.",
					"estimated_deadline": "",
				},
				"entry_photo": {"data_url": photo_data, "filename": f"sla-{suffix}.jpg"},
			}
		)
		created_order = checkin["service_order"]["name"]
		if frappe.db.get_value("Service Order", created_order, "estimated_deadline"):
			raise AssertionError("OS com prazo em branco foi preenchida à força ou bloqueada.")
		return {
			"status": "ok",
			"commercial_hours_skip_weekend": str(monday),
			"sla_edit_changes_suggestion": True,
			"suggested_date_editable_and_blank_allowed": True,
			"checkin_without_defect_does_not_block": True,
		}
	finally:
		if original_entry_sla:
			frappe.set_user("Administrator")
			save_stage_sla(original_entry_sla)
		frappe.set_user(previous_user)


def run_stage_clock_checks() -> dict:
	"""A delay is derived from stage timestamps and clears by moving forward."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		manager = _find_or_create_user("Tecponto Gestor")
		frappe.set_user(manager)
		order = frappe.get_doc("Service Order", _create_action_request_service_order(manager))
		# Keep this independent from a manager-edited SLA left by earlier checks.
		# Thirty calendar days is deliberately beyond every seeded operational SLA.
		old = add_to_date(now_datetime(), days=-30)
		frappe.db.set_value(
			"Service Order",
			order.name,
			{"workflow_state": "Entrada criada", "stage_entered_at": old, "estimated_deadline": add_days(now_datetime().date(), -30)},
			update_modified=False,
		)
		order.reload()
		overdue = get_stage_clock(order)
		if not overdue["is_stage_overdue"] or not overdue["is_total_overdue"] or not overdue["is_overdue"]:
			raise AssertionError("OS parada além do SLA/data prometida não foi marcada como atrasada.")
		listed = list_service_orders(query=order.name, limit=1)["items"]
		if not listed or not listed[0].get("stage_clock", {}).get("is_overdue"):
			raise AssertionError("Lista de OS não recebeu a flag derivada de atraso.")
		statbar = get_service_order_statbar()["items"]
		if not next((item for item in statbar if item["key"] == "overdue" and item["value"] >= 1), None):
			raise AssertionError("StatBar não recebeu o contador derivado de atrasadas.")
		frappe.db.set_value("Service Order", order.name, {"workflow_state": "Em reparo", "stage_entered_at": now_datetime(), "estimated_deadline": add_days(now_datetime().date(), 2)}, update_modified=False)
		order.reload()
		cleared = get_stage_clock(order)
		if cleared["is_overdue"]:
			raise AssertionError("Avançar a OS não limpou o alerta derivado.")
		return {"status": "ok", "stage_overdue": True, "total_overdue": True, "list_and_statbar_fed": True, "clears_after_stage_change": True}
	finally:
		frappe.set_user(previous_user)


def run_service_catalog_checks() -> dict:
	"""Prove catalog CRUD, inactive history, role write gate, and safe projection."""
	previous_user = frappe.session.user
	created_service = None
	created_device_type = None
	created_category = None
	try:
		ensure_frontend_foundation()
		manager = _find_or_create_user("Tecponto Gestor")
		attendant = _find_or_create_user("Tecponto Atendente")
		frappe.set_user(manager)
		references = list_catalog_references(include_inactive=True)
		if not {"Celular", "Tablet", "Notebook", "Smartwatch", "Outros"}.issubset({row["value"] for row in references["device_types"]}):
			raise AssertionError("Semente de tipos de aparelho não foi criada.")
		if not {"Tela", "Bateria", "Carga", "Áudio", "Câmera", "Botões", "Placa", "Software", "Danos", "Diagnóstico"}.issubset({row["value"] for row in references["categories"]}):
			raise AssertionError("Semente de categorias não foi criada.")

		suffix = frappe.generate_hash(length=8).upper()
		device_type = save_catalog_reference("device_type", {"value": f"Teste {suffix}", "active": True})["item"]
		category = save_catalog_reference("category", {"value": f"Teste {suffix}", "active": True})["item"]
		created_device_type = device_type["name"]
		created_category = category["name"]
		category = save_catalog_reference(
			"category", {"name": category["name"], "value": f"Categoria editada {suffix}", "active": True}
		)["item"]
		created_category = category["name"]
		if category["value"] != f"Categoria editada {suffix}":
			raise AssertionError("Edição de categoria de serviço não persistiu.")
		device_type = save_catalog_reference(
			"device_type", {"name": device_type["name"], "value": f"Teste editado {suffix}", "active": True}
		)["item"]
		created_device_type = device_type["name"]
		if device_type["value"] != f"Teste editado {suffix}":
			raise AssertionError("Edição de tipo de aparelho não persistiu.")
		created = save_catalog_service(
			{
				"service_name": f"Serviço teste {suffix}",
				"device_type": device_type["name"],
				"category": category["name"],
				"default_labor_price": 149.9,
				"default_duration": 2,
				"duration_unit": "Dias úteis",
				"requires_part": True,
				"complexity": "Média",
				"active": True,
			}
		)["item"]
		created_service = created["name"]
		order_name = _create_action_request_service_order(attendant)
		integrated = add_catalog_service_to_service_order(
			order_name,
			created["name"],
			{"qty": 1, "rate": 123.45, "duration": 3, "duration_unit": "Dias úteis"},
		)
		catalog_line = integrated["services"][-1]
		if (
			catalog_line.get("catalog_service") != created["name"]
			or catalog_line.get("unit_price") != 123.45
			or catalog_line.get("service_duration") != 3
			or catalog_line.get("duration_unit") != "Dias úteis"
		):
			raise AssertionError("Serviço do catálogo não aplicou nem preservou os ajustes da OS.")
		updated = save_catalog_service({**created, "default_labor_price": 179.9, "active": False})["item"]
		inactive_category = save_catalog_reference(
			"category", {"name": category["name"], "value": category["value"], "active": False}
		)["item"]
		if inactive_category["active"]:
			raise AssertionError("Inativação de categoria de serviço não persistiu.")
		active_rows = list_catalog_services(query=suffix, include_inactive="0")["items"]
		all_rows = list_catalog_services(query=suffix, include_inactive=True)["items"]
		if active_rows or not any(row["name"] == created["name"] and not row["active"] for row in all_rows):
			raise AssertionError("Inativação do serviço não preservou o histórico corretamente.")

		frappe.set_user(attendant)
		readable = list_catalog_services(query="Troca de tela")
		write_blocked = False
		try:
			save_catalog_service({**created, "default_labor_price": 1})
		except frappe.PermissionError:
			write_blocked = True
		category_write_blocked = False
		try:
			save_catalog_reference("category", {"name": category["name"], "value": category["value"], "active": True})
		except frappe.PermissionError:
			category_write_blocked = True
		if not write_blocked:
			raise AssertionError("Atendente alterou preço base do catálogo.")
		if not category_write_blocked:
			raise AssertionError("Atendente alterou categoria de serviço.")
		leaks = contains_sensitive_field(readable)
		if leaks:
			raise AssertionError(f"Catálogo expôs campo sensível: {', '.join(leaks)}")
		return {
			"status": "ok",
			"seeded_types": len(references["device_types"]),
			"seeded_categories": len(references["categories"]),
			"created": created["name"],
			"updated_price": updated["default_labor_price"],
			"catalog_suggestion_adjusted_in_os": True,
			"inactive_preserves_history": True,
			"category_rename_and_inactivation": True,
			"attendant_write_blocked": write_blocked,
			"attendant_category_write_blocked": category_write_blocked,
			"sensitive_guard": {"leaked_fields": leaks},
		}
	finally:
		if created_service and frappe.db.exists("Tecponto Service", created_service):
			frappe.delete_doc("Tecponto Service", created_service, ignore_permissions=True, force=True)
		if created_device_type and frappe.db.exists("Tecponto Device Type", created_device_type):
			frappe.delete_doc("Tecponto Device Type", created_device_type, ignore_permissions=True, force=True)
		if created_category and frappe.db.exists("Tecponto Service Category", created_category):
			frappe.delete_doc("Tecponto Service Category", created_category, ignore_permissions=True, force=True)
		# Remove any residue from interrupted catalog-edit test runs as well. These
		# deterministic test labels are never valid catalog seed data.
		for reference_name in frappe.get_all("Tecponto Device Type", filters={"type_name": ["like", "Teste editado %"]}, pluck="name"):
			frappe.delete_doc("Tecponto Device Type", reference_name, ignore_permissions=True, force=True)
		frappe.set_user(previous_user)


def run_warranty_mode_checks() -> dict:
	"""Prove warranty check-in links the original, records free labor, and still consumes parts."""
	previous_user = frappe.session.user
	created_catalog_service = None
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		original_name = _create_action_request_service_order(attendant)
		original = frappe.get_doc("Service Order", original_name)
		# The visual demo customer predates the counter-registration rules. Complete
		# it here because a real warranty check-in must pass those same motor rules.
		frappe.db.set_value(
			"Customer",
			original.customer,
			{"mobile_no": "11999998888", "custom_whatsapp": "11999998888", "custom_cpf": "12345678909"},
			update_modified=False,
		)
		frappe.db.set_value(
			"Service Order",
			original.name,
			{
				"workflow_state": "Entregue",
				"pickup_date": now_datetime(),
				"warranty_expiry": add_days(nowdate(), 90),
			},
			update_modified=False,
		)

		frappe.set_user(manager)
		catalog_references = list_catalog_references()
		created_catalog_service = save_catalog_service(
			{
				"service_name": f"Garantia teste {frappe.generate_hash(length=7).upper()}",
				"device_type": catalog_references["device_types"][0]["name"],
				"category": catalog_references["categories"][0]["name"],
				"default_labor_price": 199.9,
				"default_duration": 2,
				"duration_unit": "Horas",
				"active": True,
			}
		)["item"]["name"]

		photo = BytesIO()
		Image.new("RGB", (24, 24), color=(20, 40, 60)).save(photo, format="JPEG")
		photo_data = "data:image/jpeg;base64," + b64encode(photo.getvalue()).decode()
		frappe.set_user(attendant)
		candidates = list_warranty_candidates(original.customer, original.customer_device)["items"]
		if not any(item["name"] == original.name for item in candidates):
			raise AssertionError("Aviso proativo nÃ£o encontrou a OS entregue dentro da garantia.")

		checkin = create_service_order_checkin(
			{
				"customer": {"existing_name": original.customer},
				"device": {"existing_name": original.customer_device},
				"service_order": {
					"reported_defect": "Retorno em garantia para validar retrabalho.",
					"physical_state": "Sem danos adicionais aparentes.",
					"is_warranty": 1,
					"original_service_order": original.name,
				},
				"entry_photo": {"data_url": photo_data, "filename": "warranty-entry.jpg"},
			}
		)
		warranty_name = checkin["service_order"]["name"]
		warranty_doc = frappe.get_doc("Service Order", warranty_name)
		if not warranty_doc.is_warranty or warranty_doc.original_service_order != original.name:
			raise AssertionError("Check-in em garantia nÃ£o reteve o vÃ­nculo com a OS original.")

		with_catalog = add_catalog_service_to_service_order(
			warranty_name,
			created_catalog_service,
			{"qty": 1, "rate": 199.9, "duration": 2, "duration_unit": "Horas"},
		)
		service_line = with_catalog["services"][-1]
		if service_line.get("unit_price") != 0 or service_line.get("catalog_service") != created_catalog_service:
			raise AssertionError("ServiÃ§o em garantia cobrou mÃ£o de obra ou perdeu o vÃ­nculo do catÃ¡logo.")

		part_template = (original.get("parts") or [None])[0]
		if not part_template or not part_template.warehouse:
			raise AssertionError("OS de teste nÃ£o possui peÃ§a/estoque para validar baixa em garantia.")
		valuation_rate = flt(frappe.db.get_value("Item", part_template.item_code, "valuation_rate") or 10)
		_ensure_pos_demo_stock(part_template.item_code, part_template.warehouse, valuation_rate)
		qty_before = _bin_qty(part_template.item_code, part_template.warehouse)
		warranty_doc.reload()
		warranty_doc.append(
			"parts",
			{
				"item_code": part_template.item_code,
				"description": "PeÃ§a usada no retrabalho de garantia",
				"qty": 1,
				"warehouse": part_template.warehouse,
				"rate": 0,
				"outcome": "Usada no reparo",
			},
		)
		warranty_doc.save(ignore_permissions=True)
		warranty_doc.reload()
		used_part = warranty_doc.parts[-1]
		qty_after = _bin_qty(part_template.item_code, part_template.warehouse)
		stock_entry = frappe.get_doc("Stock Entry", used_part.stock_entry) if used_part.stock_entry else None
		issue_rate = flt(stock_entry.items[0].basic_rate) if stock_entry else 0
		if not used_part.stock_entry or not stock_entry or stock_entry.docstatus != 1 or qty_after >= qty_before or issue_rate <= 0:
			raise AssertionError("PeÃ§a de garantia nÃ£o baixou estoque com custo real registrado.")

		leaks = contains_sensitive_field(
			{"checkin": checkin, "candidates": candidates, "service_order": with_catalog},
			forbidden_values={valuation_rate, issue_rate},
		)
		if leaks:
			raise AssertionError("Modo garantia exp\u00f4s custo em resposta do frontend: {0}".format(", ".join(leaks)))

		return {
			"status": "ok",
			"proactive_warranty_candidate": original.name,
			"warranty_order": warranty_name,
			"original_service_order": warranty_doc.original_service_order,
			"labor_price": service_line.get("unit_price"),
			"catalog_service": service_line.get("catalog_service"),
			"part_stock_entry": used_part.stock_entry,
			"part_qty_before": qty_before,
			"part_qty_after": qty_after,
			"part_cost_recorded": True,
			"sensitive_guard": {"leaked_fields": leaks},
		}
	finally:
		if created_catalog_service and frappe.db.exists("Tecponto Service", created_catalog_service):
			frappe.delete_doc("Tecponto Service", created_catalog_service, ignore_permissions=True, force=True)
		frappe.set_user(previous_user)


def run_warranty_delivery_checks() -> dict:
	"""Prove warranty starts on delivery and a rework cannot extend it."""
	previous_user = frappe.session.user
	settings = frappe.get_single("Tecponto Settings")
	previous_days = settings.get("default_warranty_days")
	created_catalog_service = None
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		frappe.db.set_single_value("Tecponto Settings", "default_warranty_days", 90)

		original_name = _create_action_request_service_order(attendant)
		original = frappe.get_doc("Service Order", original_name)
		frappe.db.set_value(
			"Customer",
			original.customer,
			{"mobile_no": "11999998888", "custom_whatsapp": "11999998888", "custom_cpf": "12345678909"},
			update_modified=False,
		)
		frappe.db.set_value("Service Order", original.name, "entry_date", add_days(nowdate(), -7), update_modified=False)
		original.reload()
		_deliver_warranty_test_order(original)
		original.db_set(
			{"workflow_state": "Entregue", "pickup_date": original.pickup_date, "warranty_expiry": original.warranty_expiry},
			update_modified=False,
		)

		expected_original_expiry = add_days(nowdate(), 90)
		if str(original.pickup_date) != nowdate() or str(original.warranty_expiry) != expected_original_expiry:
			raise AssertionError("Garantia normal não foi calculada a partir da data de entrega configurada.")
		if str(original.warranty_expiry) == str(add_days(original.entry_date, 90)):
			raise AssertionError("Garantia foi calculada a partir da criação, e não da entrega.")
		device_imei = f"K5{frappe.generate_hash(length=12)}"
		frappe.db.set_value("Customer Device", original.customer_device, "imei_serial", device_imei, update_modified=False)
		frappe.set_user(attendant)
		queries = {
			"os": search_service_order_warranties(original.name, "os"),
			"imei": search_service_order_warranties(device_imei, "imei"),
			"customer": search_service_order_warranties(original.customer, "customer"),
		}
		for mode, result in queries.items():
			candidate = next((item for item in result["items"] if item["service_order"] == original.name), None)
			if not candidate:
				raise AssertionError(f"Tela de garantia não encontrou a OS por {mode}.")
			if candidate["status"] != "vigente" or candidate["remaining_days"] != 90 or not candidate["covered_services"]:
				raise AssertionError("Consulta vigente não mostrou prazo restante, status e cobertura.")
			leaks = contains_sensitive_field(result, forbidden_values={BUDGET_COST_GUARD_VALUATION})
			if leaks:
				raise AssertionError(f"Consulta de garantia vazou custo/margem: {', '.join(leaks)}")

		frappe.set_user(manager)
		catalog_references = list_catalog_references()
		created_catalog_service = save_catalog_service(
			{
				"service_name": f"Garantia entrega {frappe.generate_hash(length=7).upper()}",
				"device_type": catalog_references["device_types"][0]["name"],
				"category": catalog_references["categories"][0]["name"],
				"default_labor_price": 199.9,
				"default_duration": 2,
				"duration_unit": "Horas",
				"active": True,
			}
		)["item"]["name"]

		photo = BytesIO()
		Image.new("RGB", (24, 24), color=(20, 40, 60)).save(photo, format="JPEG")
		photo_data = "data:image/jpeg;base64," + b64encode(photo.getvalue()).decode()
		frappe.set_user(attendant)
		warranty = create_service_order_checkin(
			{
				"customer": {"existing_name": original.customer},
				"device": {"existing_name": original.customer_device},
				"service_order": {
					"reported_defect": original.reported_defect,
					"physical_state": "Sem danos adicionais aparentes.",
					"is_warranty": 1,
					"original_service_order": original.name,
				},
				"entry_photo": {"data_url": photo_data, "filename": "warranty-delivery-entry.jpg"},
			}
		)
		warranty_doc = frappe.get_doc("Service Order", warranty["service_order"]["name"])
		if str(warranty_doc.warranty_expiry) != expected_original_expiry:
			raise AssertionError("Retrabalho não herdou a validade imutável da OS original.")
		_deliver_warranty_test_order(warranty_doc)
		if str(warranty_doc.warranty_expiry) != expected_original_expiry:
			raise AssertionError("A entrega do retrabalho reiniciou a garantia original.")

		with_service = add_catalog_service_to_service_order(
			warranty_doc.name,
			created_catalog_service,
			{"qty": 1, "rate": 199.9, "duration": 2, "duration_unit": "Horas"},
		)
		if with_service["services"][-1].get("unit_price") != 0:
			raise AssertionError("Retrabalho em garantia cobrou mão de obra.")
		customer_part = add_service_order_budget_line(
			warranty_doc.name,
			{
				"type": "part",
				"part_source": "Cliente",
				"description": "Peça trazida pelo cliente",
				"customer_part_note": "Cliente forneceu a peça para o retrabalho.",
				"qty": 1,
				"rate": 999,
			},
		)
		customer_part_row = customer_part["parts"][-1]
		if customer_part_row.get("part_source") != "Cliente" or customer_part_row.get("unit_price") != 0:
			raise AssertionError("Peça do cliente foi cobrada ou tratada como peça da loja na garantia.")
		if not frappe.db.get_value("Service Order", warranty_doc.name, "customer_supplied_part_term_required"):
			raise AssertionError("Peça do cliente não exigiu o termo que exclui cobertura da peça fornecida.")

		different_defect_blocked = False
		try:
			create_service_order_checkin(
				{
					"customer": {"existing_name": original.customer},
					"device": {"existing_name": original.customer_device},
					"service_order": {
						"reported_defect": "Defeito diferente, fora da garantia.",
						"physical_state": "Sem danos adicionais aparentes.",
						"is_warranty": 1,
						"original_service_order": original.name,
					},
					"entry_photo": {"data_url": photo_data, "filename": "different-defect.jpg"},
				}
			)
		except frappe.ValidationError:
			different_defect_blocked = True
		if not different_defect_blocked:
			raise AssertionError("Defeito diferente foi aceito indevidamente como retrabalho em garantia.")

		normal_order = create_service_order_checkin(
			{
				"customer": {"existing_name": original.customer},
				"device": {"existing_name": original.customer_device},
				"service_order": {"reported_defect": "Defeito diferente, fora da garantia.", "physical_state": "Sem danos adicionais aparentes."},
				"entry_photo": {"data_url": photo_data, "filename": "normal-different-defect.jpg"},
			}
		)
		normal_quote = add_catalog_service_to_service_order(
			normal_order["service_order"]["name"],
			created_catalog_service,
			{"qty": 1, "rate": 199.9, "duration": 2, "duration_unit": "Horas"},
		)
		if normal_quote["services"][-1].get("unit_price") != 199.9:
			raise AssertionError("Defeito diferente não abriu OS normal com cobrança regular.")

		expired_name = _create_action_request_service_order(attendant)
		expired = frappe.get_doc("Service Order", expired_name)
		expired.db_set({"workflow_state": "Entregue", "pickup_date": add_days(nowdate(), -100), "warranty_expiry": add_days(nowdate(), -10)}, update_modified=False)
		expired_result = search_service_order_warranties(expired.name, "os")
		expired_item = next((item for item in expired_result["items"] if item["service_order"] == expired.name), None)
		if not expired_item or expired_item["status"] != "expirada" or expired_item["remaining_days"] != 0:
			raise AssertionError("Tela não mostrou claramente a garantia expirada.")
		expired_warranty_blocked = False
		try:
			create_service_order_checkin({"customer": {"existing_name": expired.customer}, "device": {"existing_name": expired.customer_device}, "service_order": {"reported_defect": expired.reported_defect, "physical_state": "Sem danos adicionais.", "is_warranty": 1, "original_service_order": expired.name}, "entry_photo": {"data_url": photo_data, "filename": "expired-warranty.jpg"}})
		except frappe.ValidationError:
			expired_warranty_blocked = True
		if not expired_warranty_blocked:
			raise AssertionError("Motor aceitou retrabalho com garantia expirada.")
		expired_normal = create_service_order_checkin({"customer": {"existing_name": expired.customer}, "device": {"existing_name": expired.customer_device}, "service_order": {"reported_defect": expired.reported_defect, "physical_state": "Sem danos adicionais."}, "entry_photo": {"data_url": photo_data, "filename": "expired-normal.jpg"}})
		expired_quote = add_catalog_service_to_service_order(expired_normal["service_order"]["name"], created_catalog_service, {"qty": 1, "rate": 199.9, "duration": 2, "duration_unit": "Horas"})
		if expired_quote["services"][-1].get("unit_price") != 199.9:
			raise AssertionError("Garantia expirada não seguiu como OS normal com cobrança.")

		frappe.db.set_single_value("Tecponto Settings", "default_warranty_days", 30)
		if str(frappe.db.get_value("Service Order", original.name, "warranty_expiry")) != expected_original_expiry:
			raise AssertionError("Alterar a configuração reescreveu a garantia de uma OS já entregue.")
		second_name = _create_action_request_service_order(attendant)
		second = frappe.get_doc("Service Order", second_name)
		frappe.db.set_value("Service Order", second.name, "entry_date", add_days(nowdate(), -3), update_modified=False)
		second.reload()
		_deliver_warranty_test_order(second)
		if str(second.warranty_expiry) != add_days(nowdate(), 30):
			raise AssertionError("Nova OS não respeitou o prazo de garantia configurável.")
		warranty_screen_source = (Path(__file__).parents[3] / "frontend" / "src" / "WarrantyScreen.tsx").read_text(encoding="utf-8")
		for marker in ('const active = item.status === "vigente";', 'active ? "Vigente" : "Expirada"', "Prazo encerrado: o novo atendimento será uma OS normal.", "Abrir nova OS normal", 'item.status === "vigente" ? item.service_order : ""'):
			if marker not in warranty_screen_source:
				raise AssertionError(f"Tela dedicada de garantia perdeu a amarra visual {marker!r}.")

		return {
			"status": "ok",
			"pickup_date": str(original.pickup_date),
			"original_warranty_expiry": expected_original_expiry,
			"rework_inherits_original_expiry": True,
			"different_defect_blocked": different_defect_blocked,
			"customer_part_excluded_from_warranty": True,
			"new_configured_warranty_expiry": str(second.warranty_expiry),
			"screen_queries": sorted(queries),
			"expired_opens_normal_charged": expired_warranty_blocked,
		}
	finally:
		frappe.db.set_single_value("Tecponto Settings", "default_warranty_days", previous_days or 90)
		if created_catalog_service and frappe.db.exists("Tecponto Service", created_catalog_service):
			frappe.delete_doc("Tecponto Service", created_catalog_service, ignore_permissions=True, force=True)
		frappe.set_user(previous_user)


def _deliver_warranty_test_order(doc) -> None:
	"""Exercise the same delivery hooks without needing a financial fixture."""
	from tecponto_app.tecponto.service_order.aceites import validate_aceites
	from tecponto_app.tecponto.service_order.policies import validate_repare_rules

	doc.workflow_state = "Entregue"
	doc.pickup_without_repair = 1
	doc.entry_signature = doc.entry_signature or "Assinatura de entrada de teste"
	doc.customer_signature = "Assinatura de retirada de teste"
	doc.link_acceptance_required = 0
	validate_aceites(doc)
	validate_repare_rules(doc)


def run_customer_registration_checks() -> dict:
	"""Prove counter customer registration is validated by the backend and searchable by the OS wizard."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		frappe.set_user(attendant)
		suffix = frappe.generate_hash(length=10).upper()
		base = {
			"customer_name": f"Cliente Cadastro 3.9-3 {suffix}",
			"mobile_no": "11999998888",
		}

		missing_identity_blocked = False
		try:
			create_customer(base)
		except frappe.ValidationError:
			missing_identity_blocked = True
		if not missing_identity_blocked:
			raise AssertionError("Motor aceitou cliente sem CPF e sem RG.")

		rg_required_blocked = False
		try:
			create_customer({**base, "custom_nao_possui_cpf": 1})
		except frappe.ValidationError:
			rg_required_blocked = True
		if not rg_required_blocked:
			raise AssertionError("Motor aceitou 'não possui CPF' sem exigir RG.")

		created = create_customer({**base, "custom_cpf": "12345678909", "email_id": "cliente.393@tecponto.local"})["item"]
		searchable = any(item["name"] == created["name"] for item in search_customers(created["name"], limit=12)["items"])
		if not searchable:
			raise AssertionError("Cliente cadastrado não ficou disponível na busca usada pelo wizard de OS.")

		without_cpf = create_customer(
			{
				"customer_name": f"Cliente RG 3.9-3 {suffix}",
				"mobile_no": "11999997777",
				"custom_nao_possui_cpf": 1,
				"custom_rg": "MG-12.345.678",
			}
		)["item"]
		if not without_cpf["custom_nao_possui_cpf"] or not without_cpf["custom_rg"]:
			raise AssertionError("Cadastro com RG não reteve a opção 'não possui CPF'.")

		return {
			"status": "ok",
			"created_customer": created["name"],
			"searchable_in_checkin": searchable,
			"missing_identity_blocked": missing_identity_blocked,
			"rg_required_when_no_cpf": rg_required_blocked,
			"rg_customer": without_cpf["name"],
		}
	finally:
		frappe.set_user(previous_user)


def run_registry_crud_checks() -> dict:
	"""Prove registry writes are allowlisted and Item cost remains a Director-only projection."""
	previous_user = frappe.session.user
	created_part = None
	created_customer = None
	created_device = None
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		director = _find_or_create_user("Tecponto Diretor")
		technician = _find_or_create_user("Tecponto Tecnico")
		suffix = frappe.generate_hash(length=8).upper()

		frappe.set_user(attendant)
		created_customer = create_customer(
			{
				"customer_name": f"Cliente CRUD {suffix}",
				"mobile_no": "11999998888",
				"custom_cpf": "12345678909",
			}
		)["item"]
		updated_customer = save_registry_record(
			"customer",
			created_customer["name"],
			{
				"customer_name": f"Cliente CRUD editado {suffix}",
				"mobile_no": "11999997777",
				"custom_whatsapp": "11999997777",
				"custom_cpf": "12345678909",
				"custom_rg": "",
				"custom_nao_possui_cpf": 0,
				"email_id": "crud@tecponto.local",
				"address": {"address_line1": "Rua do Teste, 100", "city": "Guarulhos", "state": "SP", "pincode": "07000-000"},
			},
		)["item"]
		if updated_customer.get("address", {}).get("city") != "Guarulhos":
			raise AssertionError("Edição de endereço do cliente não foi persistida no cadastro nativo.")

		created_device = create_customer_device(
			{
				"customer": created_customer["name"],
				"brand": "Apple",
				"model": "iPhone CRUD",
				"color": "Preto",
				"imei_serial": f"CRUD-{suffix}",
			}
		)["item"]
		updated_device = save_registry_record(
			"device",
			created_device["name"],
			{"brand": "Apple", "model": "iPhone CRUD editado", "color": "Azul", "imei_serial": f"CRUD-{suffix}", "capacity": "128GB", "general_state": "Sem danos aparentes."},
		)["item"]
		if updated_device.get("model") != "iPhone CRUD editado":
			raise AssertionError("Atendente não conseguiu editar aparelho próprio do cadastro.")

		part = save_registry_record(
			"repair_part",
			"",
			{
				"item_code": f"TP-CRUD-PART-{suffix}",
				"item_name": "Peça CRUD",
				"item_group": "Peças de Reparo",
				"description": "iPhone 13",
				"custom_compatible_models": "iPhone 13 / 13 Pro",
				"custom_part_type": "Tela",
			},
		)["item"]
		created_part = part["item_code"]
		attendant_part = get_registry_record("repair_part", created_part)["item"]
		for forbidden in ("valuation_rate", "cost", "margin", "purchase_rate", "incoming_rate"):
			if forbidden in attendant_part:
				raise AssertionError(f"Payload da peça para Atendente vazou {forbidden}.")
		leaks = contains_sensitive_field(attendant_part)
		if leaks:
			raise AssertionError(f"Payload da peça para Atendente vazou campos sensíveis: {', '.join(leaks)}")

		allowlist_blocked = False
		try:
			save_registry_record("repair_part", created_part, {"valuation_rate": 1})
		except frappe.PermissionError:
			allowlist_blocked = True
		if not allowlist_blocked:
			raise AssertionError("Allowlist aceitou valuation_rate enviado pelo Atendente.")

		retail_item = frappe.db.get_value("Item", {"item_group": ["in", get_retail_item_groups()]}, "name")
		catalog_edit_blocked = False
		try:
			save_registry_record("product", retail_item, {"item_name": "Tentativa bloqueada"})
		except frappe.PermissionError:
			catalog_edit_blocked = True
		if not catalog_edit_blocked:
			raise AssertionError("Atendente alterou catálogo comercial/estoque fora do seu papel.")

		frappe.set_user(director)
		director_part = get_registry_record("repair_part", created_part)["item"]
		if "valuation_rate" not in director_part:
			raise AssertionError("Diretor não recebeu o custo interno da peça no cadastro.")

		frappe.set_user(technician)
		technician_blocked = False
		try:
			get_registry_record("customer", created_customer["name"])
		except frappe.PermissionError:
			technician_blocked = True
		if not technician_blocked:
			raise AssertionError("Técnico abriu cadastro global de cliente fora da própria carteira.")

		return {
			"status": "ok",
			"customer_and_device_updated": True,
			"attendant_part_leaked_fields": leaks,
			"director_sees_valuation": True,
			"catalog_edit_blocked": catalog_edit_blocked,
			"allowlist_blocked": allowlist_blocked,
			"technician_blocked": technician_blocked,
		}
	finally:
		# Test data is created under role-scoped sessions; native Customer cleanup also
		# removes linked Address records, which requires an administrative session.
		frappe.set_user("Administrator")
		if created_device and frappe.db.exists("Customer Device", created_device["name"]):
			frappe.delete_doc("Customer Device", created_device["name"], ignore_permissions=True, force=True)
		if created_part and frappe.db.exists("Item", created_part):
			frappe.delete_doc("Item", created_part, ignore_permissions=True, force=True)
		if created_customer and frappe.db.exists("Customer", created_customer["name"]):
			frappe.delete_doc("Customer", created_customer["name"], ignore_permissions=True, force=True)
		frappe.set_user(previous_user)


def run_product_category_checks() -> dict:
	"""Prove native Item Group categories are editable only by management roles."""
	previous_user = frappe.session.user
	try:
		ensure_product_category_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		director = _find_or_create_user("Tecponto Diretor")
		frappe.set_user(attendant)
		initial_tree = list_product_categories()
		if _find_category(initial_tree["items"], "Peças de Reparo").get("sell_online"):
			raise AssertionError("Peças de Reparo não pode ser vendável online.")

		blocked = False
		try:
			save_product_category(
				name="TP Categoria Bloqueada",
				parent="Acessórios",
				is_group=0,
				sell_online=1,
				active=1,
			)
		except frappe.PermissionError:
			blocked = True
		if not blocked:
			raise AssertionError("Atendente não pode editar categorias de produto.")

		frappe.set_user(manager)
		test_category_name = "TP Marketplace Categoria"
		created = save_product_category(
			name=test_category_name,
			original_name=test_category_name if frappe.db.exists("Item Group", test_category_name) else None,
			parent="Acessórios",
			is_group=0,
			sell_online=1,
			active=1,
		)["item"]
		moved = save_product_category(
			name=test_category_name,
			original_name=test_category_name,
			parent="Produtos de Varejo",
			is_group=0,
			sell_online=1,
			active=1,
		)["item"]
		inactive = save_product_category(
			name=test_category_name,
			original_name=test_category_name,
			parent="Produtos de Varejo",
			is_group=0,
			sell_online=1,
			active=0,
		)["item"]
		if created.get("parent") != "Acessórios" or moved.get("parent") != "Produtos de Varejo" or inactive.get("active"):
			raise AssertionError("Criar, mover ou inativar categoria não refletiu na árvore nativa.")
		frappe.set_user(director)
		director_edit = save_product_category(
			name=test_category_name,
			original_name=test_category_name,
			parent="Produtos de Varejo",
			is_group=0,
			sell_online=1,
			active=0,
		)["item"]
		if director_edit.get("active"):
			raise AssertionError("Diretor não conseguiu editar categoria de produto.")
		final_tree = list_product_categories()
		leaks = contains_sensitive_field(final_tree)
		if leaks:
			raise AssertionError(f"Árvore de categorias vazou campo sensível: {', '.join(leaks)}")
		return {
			"created": created["name"],
			"moved_parent": moved["parent"],
			"inactive": not inactive["active"],
			"director_allowed": director_edit["name"] == test_category_name,
			"attendant_blocked": blocked,
			"repair_parts_online": _find_category(final_tree["items"], "Peças de Reparo").get("sell_online"),
			"leaked_fields": leaks,
		}
	finally:
		frappe.set_user(previous_user)


def _find_category(items: list[dict], name: str) -> dict:
	for item in items:
		if item.get("name") == name:
			return item
		found = _find_category(item.get("children") or [], name)
		if found:
			return found
	return {}


def run_product_variant_checks() -> dict:
	"""Prove native variants keep barcode lookup and stock strictly per child SKU."""
	previous_user = frappe.session.user
	created_attribute = None
	try:
		ensure_frontend_foundation()
		ensure_product_variant_attributes()
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		frappe.set_user(manager)

		attribute = save_product_variant_attribute("Cor", [{"value": "Verde TP", "abbreviation": "VTP"}])["item"]
		if not any(row["value"] == "Verde TP" for row in attribute["values"]):
			raise AssertionError("Gestor não conseguiu manter um valor de Item Attribute nativo.")
		created_attribute = f"TP Material {frappe.generate_hash(length=6).upper()}"
		custom_attribute = save_product_variant_attribute(
			created_attribute,
			[{"value": "Silicone", "abbreviation": "SIL"}, {"value": "Couro", "abbreviation": "COU"}],
		)["item"]
		if {row["value"] for row in custom_attribute["values"]} != {"Silicone", "Couro"}:
			raise AssertionError("Gestor não conseguiu criar Item Attribute nativo.")
		custom_attribute = save_product_variant_attribute(
			created_attribute,
			[{"value": "Silicone", "abbreviation": "SI"}],
			disabled=True,
			replace_values=True,
		)["item"]
		if not custom_attribute["disabled"] or custom_attribute["values"] != [{"value": "Silicone", "abbreviation": "SI"}]:
			raise AssertionError("Edição, remoção ou inativação de Item Attribute não foi persistida.")

		suffix = frappe.generate_hash(length=7).upper()
		template_code = f"TPV-CAPA-{suffix}"
		payload = {
			"template_code": template_code,
			"template_name": f"Capa teste {suffix}",
			"item_group": "Capas",
			"stock_uom": "Nos",
			"attributes": [{"name": "Cor"}, {"name": "Modelo compatível"}],
			"variants": [
				{"attributes": {"Cor": "Preto", "Modelo compatível": "iPhone 13"}, "sku": f"{template_code}-PT-IP13", "gtin": f"TPV{suffix}01", "price": 49.90},
				{"attributes": {"Cor": "Azul", "Modelo compatível": "iPhone 13"}, "sku": f"{template_code}-AZ-IP13", "gtin": f"TPV{suffix}02", "price": 49.90},
				{"attributes": {"Cor": "Preto", "Modelo compatível": "iPhone 14"}, "sku": f"{template_code}-PT-IP14", "gtin": f"TPV{suffix}03", "price": 54.90},
				{"attributes": {"Cor": "Azul", "Modelo compatível": "iPhone 14"}, "sku": f"{template_code}-AZ-IP14", "gtin": f"TPV{suffix}04", "price": 54.90},
			],
		}
		created = create_product_with_variants(payload)
		if created["template"]["item_code"] != template_code or len(created["variants"]) != 4:
			raise AssertionError("Produto pai ou combinações nativas não foram criados.")
		if frappe.get_doc("Item", template_code).is_stock_item:
			raise AssertionError("Produto pai de variações não pode manter estoque.")

		target = created["variants"][0]
		other = created["variants"][1]
		pos_receive_retail_stock({"item_code": target["item_code"], "qty": 3, "incoming_rate": 12})
		pos_receive_retail_stock({"item_code": other["item_code"], "qty": 4, "incoming_rate": 12})
		lookup = pos_lookup_retail_barcode(target["gtin"])
		if lookup.get("item", {}).get("item_code") != target["item_code"]:
			raise AssertionError("Bipe não resolveu a variação exata do código de barras.")

		commercial_warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
		before_target = flt(frappe.db.get_value("Bin", {"item_code": target["item_code"], "warehouse": commercial_warehouse}, "actual_qty"), 3)
		before_other = flt(frappe.db.get_value("Bin", {"item_code": other["item_code"], "warehouse": commercial_warehouse}, "actual_qty"), 3)
		sale = pos_create_sale(
			{
				"idempotency_key": f"tpv-sale-{suffix}",
				"discount_amount": 0,
				"items": [{"item_code": target["item_code"], "qty": 1}],
				"payments": [{"mode_of_payment": "Pix", "amount": target["price"]}],
			}
		)
		after_target = flt(frappe.db.get_value("Bin", {"item_code": target["item_code"], "warehouse": commercial_warehouse}, "actual_qty"), 3)
		after_other = flt(frappe.db.get_value("Bin", {"item_code": other["item_code"], "warehouse": commercial_warehouse}, "actual_qty"), 3)
		if after_target != before_target - 1 or after_other != before_other:
			raise AssertionError("Venda de uma variação alterou estoque de SKU incorreto.")

		visible = list_variant_products()
		leaks = contains_sensitive_field({"attributes": list_product_variant_attributes(), "products": visible})
		if leaks:
			raise AssertionError(f"Produto com variação vazou campo sensível: {', '.join(leaks)}")
		frappe.set_user(attendant)
		blocked = False
		try:
			create_product_with_variants({})
		except frappe.PermissionError:
			blocked = True
		if not blocked:
			raise AssertionError("Atendente não pode cadastrar produto com variações.")
		attribute_write_blocked = False
		try:
			save_product_variant_attribute(created_attribute, [{"value": "Bloqueado", "abbreviation": "BLQ"}])
		except frappe.PermissionError:
			attribute_write_blocked = True
		if not attribute_write_blocked:
			raise AssertionError("Atendente não pode alterar atributos de variação.")
		return {
			"template": template_code,
			"variants": len(created["variants"]),
			"barcode_resolves_exact_sku": lookup["item"]["item_code"],
			"sale": sale["sale"],
			"target_stock": [before_target, after_target],
			"other_stock": [before_other, after_other],
			"attendant_blocked": blocked,
			"attendant_attribute_write_blocked": attribute_write_blocked,
			"custom_attribute_crud": True,
			"leaked_fields": leaks,
		}
	finally:
		if created_attribute and frappe.db.exists("Item Attribute", created_attribute):
			frappe.delete_doc("Item Attribute", created_attribute, ignore_permissions=True, force=True)
		frappe.set_user(previous_user)


def run_marketplace_listing_checks() -> dict:
	"""Marketplace data lives on native Item children; used trade-ins stay unique serial Items."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		ensure_product_variant_attributes()
		ensure_listing_metadata_fields()
		manager = _find_or_create_user("Tecponto Gestor")
		attendant = _find_or_create_user("Tecponto Atendente")
		frappe.set_user(manager)
		suffix = frappe.generate_hash(length=7).upper()
		variant = create_product_with_variants({"template_code": f"TPM-CAPA-{suffix}", "template_name": f"Capa marketplace {suffix}", "item_group": "Capas", "attributes": [{"name": "Cor"}], "variants": [{"attributes": {"Cor": "Preto"}, "sku": f"TPM-CAPA-{suffix}-PT", "gtin": f"TPM{suffix}01", "price": 59.90}]})["variants"][0]
		listing = save_listing_metadata(variant["item_code"], {"online_sellable": 1, "listing_title": f"Capa premium {suffix}", "listing_description": "Descrição pública do anúncio, sem dados internos.", "condition": "Novo", "grade": "A", "public_price": 59.90, "weight_per_unit": 0.12, "package_length_cm": 18, "package_width_cm": 10, "package_height_cm": 2, "images": [{"image": "/files/tecponto-listing-cover.png", "caption": "Capa"}, {"image": "/files/tecponto-listing-side.png", "caption": "Lateral"}]})["item"]
		if not listing["online_sellable"] or listing["images"][0]["image"] != "/files/tecponto-listing-cover.png":
			raise AssertionError("Dados ordenados de anúncio não foram persistidos.")
		customer = _get_or_create_demo_customer()
		imei = f"356{frappe.generate_hash(length=12).upper()}"[:15]
		frappe.set_user("Administrator")
		tradein = frappe.get_doc({"doctype": "Device Trade Evaluation", "customer": customer, "device_type": "iPhone", "model": "iPhone usado marketplace", "capacity": "128GB", "imei": imei, "approved_value": 300, "destination": "Venda", "workflow_state": "Comprado"})
		tradein.insert(ignore_permissions=True)
		used_item = tradein.created_item
		if not used_item:
			raise AssertionError("Trade-in não criou Item único serializado.")
		frappe.set_user(manager)
		save_listing_metadata(used_item, {"online_sellable": 1, "listing_title": "iPhone usado revisado", "listing_description": "Aparelho usado, revisado e pronto para venda.", "condition": "Usado", "grade": "B", "public_price": 499.90, "weight_per_unit": 0.24, "package_length_cm": 19, "package_width_cm": 11, "package_height_cm": 4, "images": [{"image": "/files/tecponto-used-cover.png", "caption": "Frente"}]})
		unique_before = next((item for item in list_commercial_catalog("unique")["items"] if item["item_code"] == used_item), None)
		if not unique_before or unique_before["available_qty"] != 1 or unique_before["serial_suffix"] != imei[-4:]:
			raise AssertionError("Trade-in não apareceu como único com estoque 1.")
		frappe.set_user("Administrator")
		sale = pos_create_sale({"idempotency_key": f"marketplace-used-{suffix}", "items": [{"item_code": used_item, "qty": 1, "serial_no": imei}], "payments": [{"mode_of_payment": "Pix", "amount": 499.90}]})
		frappe.set_user(manager)
		removed = not any(item["item_code"] == used_item for item in list_commercial_catalog("unique")["items"])
		if not removed or not any(item["item_code"] == variant["item_code"] for item in list_commercial_catalog("shelf")["items"]):
			raise AssertionError("Catálogo não separou variação de prateleira e usado único vendido.")
		frappe.set_user(attendant)
		blocked = False
		try: save_listing_metadata(variant["item_code"], {"online_sellable": 0})
		except frappe.PermissionError: blocked = True
		payload = {"listing": listing, "shelf": list_commercial_catalog("shelf")["items"]}
		leaks = contains_sensitive_field(payload, forbidden_values=[BUDGET_COST_GUARD_VALUATION])
		if not blocked or leaks:
			raise AssertionError("Permissão ou guard de custo falhou no catálogo marketplace.")
		return {"variant": variant["item_code"], "listing_cover": listing["images"][0]["image"], "used_item": used_item, "unique_stock_before_sale": unique_before["available_qty"], "used_sale": sale["sale"], "removed_after_sale": removed, "attendant_blocked": blocked, "leaked_fields": leaks}
	finally:
		frappe.set_user(previous_user)


def run_marketplace_reporting_checks() -> dict:
	"""Operational documents retain their native category dimension for future reports."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		ensure_product_category_foundation()
		manager = _find_or_create_user("Tecponto Gestor")
		frappe.set_user(manager)
		suffix = frappe.generate_hash(length=7).upper()
		variant = create_product_with_variants(
			{
				"template_code": f"TPR-CAPA-{suffix}",
				"template_name": f"Capa relatório {suffix}",
				"item_group": "Capas",
				"attributes": [{"name": "Cor"}],
				"variants": [{"attributes": {"Cor": "Preto"}, "sku": f"TPR-CAPA-{suffix}-PT", "gtin": f"TPR{suffix}01", "price": 39.90}],
			}
		)["variants"][0]
		pos_receive_retail_stock({"item_code": variant["item_code"], "qty": 2, "incoming_rate": 10})
		parent_filtered = list_stock_items(scope="commercial-products", category="Acessórios", limit=50)
		if variant["item_code"] not in {row["item_code"] for row in parent_filtered["items"]}:
			raise AssertionError("Filtro pela categoria pai não retornou a subcategoria Capas.")
		sale = pos_create_sale(
			{
				"idempotency_key": f"reporting-sale-{suffix}",
				"items": [{"item_code": variant["item_code"], "qty": 1}],
				"payments": [{"mode_of_payment": "Pix", "amount": 39.90}],
			}
		)
		sale_category = frappe.db.get_value("Sales Invoice Item", {"parent": sale["sale"], "item_code": variant["item_code"]}, "item_group")
		if sale_category != "Capas":
			raise AssertionError("Venda não preservou a categoria nativa do Item na linha da nota.")

		service = frappe.db.get_value("Tecponto Service", {"service_name": "Troca de tela", "device_type": "Celular", "active": 1}, ["name", "category"], as_dict=True)
		order_name = _create_action_request_service_order(manager)
		order_detail = add_catalog_service_to_service_order(order_name, service.name, {})
		service_category = order_detail["services"][-1].get("service_category")
		if service_category != service.category:
			raise AssertionError("OS não preservou a categoria do serviço do catálogo.")

		customer = _get_or_create_demo_customer()
		imei = f"358{frappe.generate_hash(length=12).upper()}"[:15]
		frappe.set_user("Administrator")
		trade = frappe.get_doc({"doctype": "Device Trade Evaluation", "customer": customer, "device_type": "iPhone", "model": f"Usado relatório {suffix}", "capacity": "128GB", "imei": imei, "approved_value": 250, "destination": "Venda", "workflow_state": "Comprado"})
		trade.insert(ignore_permissions=True)
		if trade.trade_category != "Aparelhos Usados" or frappe.db.get_value("Item", trade.created_item, "item_group") != trade.trade_category:
			raise AssertionError("Troca não manteve a categoria do Item único criado no trade-in.")

		frappe.set_user(manager)
		payload = {"stock": parent_filtered, "service": order_detail["services"][-1], "trade": {"category": trade.trade_category, "item": trade.created_item}}
		leaks = contains_sensitive_field(payload, forbidden_values=[BUDGET_COST_GUARD_VALUATION])
		if leaks:
			raise AssertionError("Categorias de relatório expuseram dados sensíveis.")
		return {
			"parent_category": "Acessórios",
			"child_category": "Capas",
			"sale_category": sale_category,
			"service_category": service_category,
			"trade_category": trade.trade_category,
			"leaked_fields": leaks,
		}
	finally:
		frappe.set_user(previous_user)


def run_quick_stage_move_checks() -> dict:
	"""Keep the three quick controls tied to workflow metadata and server permission checks."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")

		request_order = _create_action_request_service_order(attendant)
		frappe.set_user(attendant)
		detail = get_service_order_detail(request_order)
		destinations = {item["next_state"] for item in detail["workflow_transitions"]}
		expected = {"Em diagnóstico", "Sem conserto", "Cancelado", "Aguardando aprovação"}
		if destinations != expected:
			raise AssertionError(f"Opções rápidas não batem com o workflow: {destinations}")
		if "Em diagnóstico" not in detail["workflow_blockers"]:
			raise AssertionError("A interface não recebeu o motivo para a transição fora do papel.")
		if "Em diagnóstico" not in detail["workflow_requestable_transitions"]:
			raise AssertionError("A interface não recebeu a indicação de solicitar aprovação para a transição fora do papel.")
		listed = next((row for row in list_service_orders(limit=100)["items"] if row["name"] == request_order), None)
		kanban = get_service_order_kanban(limit_per_column=40)
		kanban_item = next((row for column in kanban["columns"] for row in column["items"] if row["name"] == request_order), None)
		if not listed or not kanban_item or listed["workflow_transitions"] != detail["workflow_transitions"] or kanban_item["workflow_transitions"] != detail["workflow_transitions"]:
			raise AssertionError("Lista, Kanban e detalhe não receberam as mesmas transições do motor.")

		permission_blocked = False
		try:
			move_service_order(request_order, "Em diagnóstico")
		except frappe.PermissionError:
			permission_blocked = True
		if not permission_blocked:
			raise AssertionError("Atendente moveu OS técnica sem passar pela autorização do motor.")
		request = create_request("service_order_move", request_order, "Encaminhar para diagnóstico técnico.", {"target_state": "Em diagnóstico"})
		workflow_approver = _find_or_create_user(request["approver_role"])
		# A technical approver can re-execute only inside the assigned OS scope.
		# Mirror that production prerequisite before proving the approved request.
		frappe.db.set_value("Service Order", request_order, "technician", workflow_approver, update_modified=False)
		frappe.set_user(workflow_approver)
		if request["name"] not in {row["name"] for row in list_pending_approvals()}:
			raise AssertionError("A role exigida pelo workflow não recebeu a solicitação do controle rápido.")
		approved_request = approve_request(request["name"])
		if approved_request["status"] != "Aprovada" or frappe.db.get_value("Service Order", request_order, "workflow_state") != "Em diagnóstico":
			raise AssertionError("A aprovação da mudança não reexecutou a transição no motor.")

		direct_order = _create_action_request_service_order(attendant)
		frappe.set_user(manager)
		moved = move_service_order(direct_order, "Em diagnóstico")
		if not moved["changed"] or moved["item"]["workflow_state"] != "Em diagnóstico":
			raise AssertionError("Gestor não conseguiu mover a OS diretamente pelo workflow.")

		return {
			"status": "ok",
			"destinations": sorted(destinations),
			"three_surfaces": ["detail", "list", "kanban"],
			"permission_request": request["name"],
			"approval_reexecution": approved_request["status"],
			"direct_move": moved["item"]["name"],
		}
	finally:
		frappe.set_user(previous_user)


def run_cashier_mode_checks() -> dict:
	"""Prove badge/PIN attribution without allowing the badge to elevate a session."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		manager = _find_or_create_user("Tecponto Gestor")
		manager = _find_or_create_user("Tecponto Gestor")
		customer = _get_or_create_demo_customer()
		demo = _ensure_pos_demo_records()
		operator = _ensure_cashier_operator(attendant, badge_code="TP-CAIXA-ATENDENTE", pin="2468")
		manager_operator = _ensure_cashier_operator(manager, badge_code="TP-CAIXA-GESTOR", pin="1357")
		frappe.db.commit()

		frappe.set_user(attendant)
		roles_before = sorted(frappe.get_roles(attendant))
		badge_identity = pos_identify_cashier_operator(badge_code=operator.badge_code)
		if badge_identity["operator"] != attendant or badge_identity["via"] != "badge":
			raise AssertionError("Bipe do cracha nao identificou o operador correto.")
		pin_identity = pos_identify_cashier_operator(pin="2468")
		if pin_identity["operator"] != attendant or pin_identity["via"] != "pin":
			raise AssertionError("PIN de fallback nao identificou o operador correto.")
		if roles_before != sorted(frappe.get_roles(attendant)) or frappe.session.user != attendant:
			raise AssertionError("Cracha alterou a sessao ou as roles do usuario logado.")

		qty_before = _bin_qty(POS_NAME_ITEM, demo["commercial_warehouse"])
		sale = pos_create_sale(
			{
				"idempotency_key": f"tp-cashier-{frappe.generate_hash(length=20)}",
				"cashier_operator_token": badge_identity["token"],
				"customer": customer,
				"items": [{"item_code": POS_NAME_ITEM, "qty": 1}],
				"discount_amount": 0,
				"payments": [{"mode_of_payment": "Pix", "amount": 35.50, "installments": 1}],
			}
		)
		frappe.db.commit()
		invoice = frappe.get_doc("Sales Invoice", sale["sale"])
		if invoice.get(CASHIER_OPERATOR_FIELD) != attendant:
			raise AssertionError("Venda do caixa nao gravou o operador na Sales Invoice.")
		request = frappe.db.get_value(
			"Tecponto POS Sale Request",
			{"sales_invoice": sale["sale"]},
			["cashier_operator", "cashier_identified_via"],
			as_dict=True,
		)
		if not request or request.cashier_operator != attendant or request.cashier_identified_via != "badge":
			raise AssertionError("Requisicao idempotente nao reteve a autoria do operador.")
		if flt(qty_before - _bin_qty(POS_NAME_ITEM, demo["commercial_warehouse"]), 3) != 1:
			raise AssertionError("Venda identificada nao baixou uma unidade do Comercial.")

		pos_download_cashier_badge(operator.name)
		badge_pdf = frappe.local.response.get("filecontent") or b""
		if not badge_pdf.startswith(b"%PDF"):
			raise AssertionError("Etiqueta do cracha nao renderizou como PDF.")
		other_badge_blocked = False
		try:
			pos_download_cashier_badge(manager_operator.name)
		except frappe.PermissionError:
			other_badge_blocked = True
		if not other_badge_blocked:
			raise AssertionError("Atendente conseguiu imprimir o cracha de outro operador.")

		anonymous_qty_before = _bin_qty(POS_BARCODE_ITEM, demo["commercial_warehouse"])
		anonymous_result = pos_create_sale(
			{
				"idempotency_key": f"tp-pos-anonymous-{frappe.generate_hash(length=20)}",
				"items": [{"item_code": POS_BARCODE_ITEM, "qty": 1}],
				"discount_amount": 0,
				"payments": [{"mode_of_payment": "Pix", "amount":  79.90, "installments": 1}],
			}
		)
		frappe.db.commit()
		if anonymous_result["customer"] != "CONSUMIDOR FINAL":
			raise AssertionError("Venda avulsa deveria usar somente o cadastro Consumidor Final.")
		if _bin_qty(POS_BARCODE_ITEM, demo["commercial_warehouse"]) != anonymous_qty_before - 1:
			raise AssertionError("Venda avulsa deveria baixar uma unidade do Comercial.")
		anonymous_customer = frappe.db.get_value(
			"Customer",
			"CONSUMIDOR FINAL",
			["customer_name", "mobile_no", "email_id", "custom_cpf", "custom_rg"],
			as_dict=True,
		)
		if not anonymous_customer or any(anonymous_customer.get(field) for field in ("mobile_no", "email_id", "custom_cpf", "custom_rg")):
			raise AssertionError("Consumidor Final nao pode carregar dados pessoais.")

		frappe.set_user(technician)
		badge_blocked = False
		try:
			pos_identify_cashier_operator(badge_code=operator.badge_code)
		except frappe.PermissionError:
			badge_blocked = True
		if not badge_blocked:
			raise AssertionError("Tecnico conseguiu usar o endpoint de identificacao do caixa.")

		frappe.set_user(attendant)
		inventory_blocked = False
		try:
			pos_receive_retail_stock({"items": [], "cashier_operator_token": badge_identity["token"]})
		except frappe.PermissionError:
			inventory_blocked = True
		if not inventory_blocked:
			raise AssertionError("Token do cracha elevou o atendente para registrar estoque.")

		return {
			"status": "ok",
			"badge": {"operator": badge_identity["operator"], "via": badge_identity["via"]},
			"pin": {"operator": pin_identity["operator"], "via": pin_identity["via"]},
			"sale": {"name": sale["sale"], "operator": invoice.get(CASHIER_OPERATOR_FIELD)},
			"badge_pdf": badge_pdf.startswith(b"%PDF"),
			"security": {"session_roles_unchanged": True, "technician_blocked": badge_blocked, "inventory_blocked": inventory_blocked, "other_badge_blocked": other_badge_blocked},
		}
	finally:
		frappe.set_user(previous_user)


def ensure_service_order_detail_demo_data() -> dict:
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		customer = _get_or_create_demo_customer()
		device = _get_or_create_demo_device(customer)
		service_item = _get_demo_item(is_stock_item=0)
		part_item = _get_demo_item(is_stock_item=1)
		warehouse = _get_demo_warehouse()

		demos = [
			{
				"slug": "entrada",
				"state": "Entrada criada",
				"approval_status": "Pendente",
				"reported_defect": "Demo 3.1b: aparelho chegou com tela piscando.",
				"problem_found": None,
			},
			{
				"slug": "aprovacao",
				"state": "Aguardando aprovação",
				"approval_status": "Pendente",
				"reported_defect": "Demo 3.1b: orçamento aguardando aceite do cliente.",
				"problem_found": "Tela OLED danificada; troca recomendada.",
			},
			{
				"slug": "retirada",
				"state": "Pronto para retirada",
				"approval_status": "Aprovado",
				"reported_defect": "Demo 3.1b: reparo concluído e aguardando retirada.",
				"problem_found": "Tela substituída e teste final aprovado.",
			},
		]
		result = {}
		for demo in demos:
			order_name = _upsert_demo_service_order(
				demo=demo,
				customer=customer,
				device=device,
				service_item=service_item,
				part_item=part_item,
				warehouse=warehouse,
				attendant=attendant,
			)
			result[demo["slug"]] = {
				"name": order_name,
				"state": demo["state"],
			}

		frappe.db.commit()
		frappe.set_user(attendant)
		for demo in result.values():
			detail = get_service_order_detail(demo["name"])
			demo["actions"] = [action["action"] for action in detail["workflow_actions"]]
			demo["prints"] = [link["label"] for link in detail["print_links"]]

		return {"status": "ok", "attendant_user": attendant, "orders": result}
	finally:
		frappe.set_user(previous_user)


def run_daily_action_checks() -> dict:
	"""Pendencias derivadas disappear with the source document; manual tasks are explicit."""
	previous_user = frappe.session.user
	original_orders = {}
	order_name = None
	try:
		demo = ensure_service_order_detail_demo_data()
		attendant = demo["attendant_user"]
		order_name = demo["orders"]["aprovacao"]["name"]
		due_today_name = demo["orders"]["retirada"]["name"]
		scheduled_name = demo["orders"]["entrada"]["name"]
		for name in (order_name, due_today_name, scheduled_name):
			original_orders[name] = frappe.db.get_value(
				"Service Order",
				name,
				["workflow_state", "stage_entered_at", "estimated_deadline", "pickup_date"],
				as_dict=True,
			)

		frappe.set_user(attendant)
		frappe.db.set_value(
			"Service Order",
			order_name,
			{"workflow_state": "Aguardando aprovação", "stage_entered_at": add_to_date(now_datetime(), hours=-72), "estimated_deadline": add_days(nowdate(), -1)},
			update_modified=False,
		)
		frappe.db.set_value(
			"Service Order",
			due_today_name,
			{"workflow_state": "Pronto para retirada", "stage_entered_at": now_datetime(), "estimated_deadline": nowdate(), "pickup_date": nowdate()},
			update_modified=False,
		)
		frappe.db.set_value(
			"Service Order",
			scheduled_name,
			{"workflow_state": "Pronto para retirada", "stage_entered_at": now_datetime(), "estimated_deadline": add_days(nowdate(), 3)},
			update_modified=False,
		)
		# A promised delivery for today becomes overdue after business hours. A dated
		# manual task keeps the due-today agenda lane deterministic at any test time.
		task = create_manual_task("Retornar para cliente da pendencia diaria", str(today()))
		before = list_daily_actions("atendente")
		if not any(item["reference_name"] == order_name for item in before["derived"]):
			raise AssertionError("OS aguardando aprovacao nao apareceu nas pendencias do Atendente.")
		if not before.get("items"):
			raise AssertionError("Agenda não retornou a lista unificada por urgência.")

		overdue_items = [item for item in before["items"] if item.get("urgency") == "overdue"]
		if overdue_items != sorted(overdue_items, key=lambda item: item.get("urgency_sort_at") or "9999-12-31 23:59:59"):
			raise AssertionError("Itens atrasados nao estao ordenados pelo prazo mais antigo primeiro.")
		if any(item.get("reference_doctype") == "Service Order" and not item.get("group_key") for item in before["items"]):
			raise AssertionError("Pendencias de OS nao receberam grupo expansivel.")
		if not {"overdue", "due_today", "scheduled"}.issubset({item.get("urgency") for item in before["items"]}):
			raise AssertionError("Agenda nao retornou as secoes atrasado, vence hoje e programado.")
		calendar = list_agenda_calendar("atendente", str(add_days(nowdate(), -1)), str(add_days(nowdate(), 7)))
		calendar_keys = {item["key"] for item in calendar["items"]}
		if not {f"delivery:{order_name}", f"delivery:{due_today_name}", f"delivery:{scheduled_name}", f"pickup:{due_today_name}:{nowdate()}", f"task:{task['name']}"}.issubset(calendar_keys):
			raise AssertionError("Agenda de calendario nao retornou entregas prometidas e retirada do Atendente.")

		frappe.db.set_value("Service Order", order_name, "workflow_state", "Entregue", update_modified=False)
		after = list_daily_actions("atendente")
		if any(item["reference_name"] == order_name for item in after["derived"]):
			raise AssertionError("Pendencia derivada continuou apos a OS ser resolvida.")

		calendar_with_task = list_agenda_calendar("atendente", str(add_days(nowdate(), -1)), str(add_days(nowdate(), 7)))
		if f"task:{task['name']}" not in {item["key"] for item in calendar_with_task["items"]}:
			raise AssertionError("Tarefa manual datada nao apareceu no calendario.")
		with_task = list_daily_actions("atendente")
		if not any(item["name"] == task["name"] for item in with_task["manual"]):
			raise AssertionError("Tarefa manual criada nao apareceu para o proprio usuario.")
		if not any(item.get("name") == task["name"] for item in with_task["items"]):
			raise AssertionError("Tarefa manual não entrou na agenda unificada.")
		complete_manual_task(task["name"])
		after_task = list_daily_actions("atendente")
		if any(item["name"] == task["name"] for item in after_task["manual"]):
			raise AssertionError("Tarefa manual concluida continuou na lista aberta.")

		technician = _find_or_create_user("Tecponto Tecnico")
		frappe.set_user(technician)
		technical = list_daily_actions("tecnico")
		if any(item.get("reference_name") == order_name for item in technical["derived"]):
			raise AssertionError("Tecnico recebeu pendencia de OS atribuida ao Atendente.")
		technical_calendar = list_agenda_calendar("tecnico", str(add_days(nowdate(), -1)), str(add_days(nowdate(), 7)))
		if any(item.get("reference_name") == order_name for item in technical_calendar["items"]):
			raise AssertionError("Tecnico recebeu item de calendario de OS atribuida ao Atendente.")

		multi_role_user = _find_or_create_multi_role_user()
		frappe.set_user(multi_role_user)
		unified = list_daily_actions("unified")
		if not unified.get("items"):
			raise AssertionError("Agenda unificada do usuario multipapel nao retornou itens.")
		return {
			"status": "ok",
			"derived_disappears": True,
			"manual_task_lifecycle": True,
			"unified_urgency_agenda": True,
			"multi_role_agenda": True,
			"calendar_projection": True,
			"role_scoped": True,
		}
	finally:
		for name, values in original_orders.items():
			frappe.db.set_value("Service Order", name, values, update_modified=False)
		frappe.set_user(previous_user)


def run_notification_checks() -> dict:
	"""Covers delivery, ownership, read state and the non-blocking enqueue boundary."""
	previous_user = frappe.session.user
	previous_in_test = frappe.flags.in_test
	original_enqueue = frappe.enqueue
	try:
		# This test explicitly covers the production enqueue boundary with a stub.
		frappe.flags.in_test = False
		frappe.set_user("Administrator")
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		order_name = _create_action_request_service_order(attendant)
		frappe.db.delete("Tecponto Notification", {"recipient": ["in", [attendant, manager]], "reference_name": ["in", [order_name]]})

		# Execute queued jobs inline here only so the assertion is deterministic.
		def deliver_inline(method, **kwargs):
			return notify.send(kwargs["user"], kwargs["template_key"], kwargs["context"])
		frappe.enqueue = deliver_inline

		frappe.set_user(attendant)
		request = create_request("service_order_discount", order_name, "Teste de notificacao.", {"discount": 1})
		frappe.set_user(manager)
		manager_notifications = notify.list_notifications()
		manager_request_notification = next((item for item in manager_notifications["items"] if item["reference_name"] == request["name"]), None)
		if not manager_request_notification:
			raise AssertionError(f"Solicitacao criada nao notificou o aprovador. Destinatarios resolvidos: {notify._users_with_role('Tecponto Gestor')}")
		manager_history = notify.list_notification_history(notification_type="approval", read_state="unread", period="today", limit=1)
		if not manager_history["items"] or manager_history["items"][0]["type"] != "approval" or manager_history["total"] < 1:
			raise AssertionError("Histórico filtrado do aprovador não retornou a solicitação pendente.")
		if manager_history["has_more"] and len(manager_history["items"]) != 1:
			raise AssertionError("Paginação do histórico de notificações não respeitou o limite solicitado.")

		approve_request(request["name"])
		frappe.set_user(attendant)
		attendant_notifications = notify.list_notifications()
		if any(item["name"] == manager_request_notification["name"] for item in attendant_notifications["items"]):
			raise AssertionError("Usuário conseguiu listar uma notificação destinada ao aprovador.")
		foreign_mark_blocked = False
		try:
			notify.mark_notification_read(manager_request_notification["name"])
		except frappe.PermissionError:
			foreign_mark_blocked = True
		if not foreign_mark_blocked:
			raise AssertionError("Usuário conseguiu marcar como lida uma notificação de outro destinatário.")
		decision = next((item for item in attendant_notifications["items"] if item["reference_name"] == request["name"]), None)
		if not decision:
			raise AssertionError("Decisao nao notificou o solicitante.")
		before_read = attendant_notifications["unread_count"]
		notify.mark_notification_read(decision["name"])
		after_read = notify.list_notifications()["unread_count"]
		if after_read != max(0, before_read - 1):
			raise AssertionError("Contagem de nao lidas divergiu do banco.")

		frappe.set_user("Administrator")
		notify.send(attendant, "service_order_state_changed", {"service_order": order_name, "state": "Em diagnostico", "reference_doctype": "Service Order", "reference_name": order_name})
		frappe.set_user(attendant)
		service_order_notification = next((item for item in notify.list_notifications()["items"] if item["reference_name"] == order_name), None)
		if not service_order_notification or "service-orders" not in service_order_notification["link"]:
			raise AssertionError("Notificacao da OS nao trouxe link seguro para o documento.")

		frappe.enqueue = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("queue offline"))
		if notify.enqueue(attendant, "service_order_state_changed", {"reference_name": order_name}) is not False:
			raise AssertionError("Falha de fila nao foi isolada da operacao.")
		return {"status": "ok", "request": request["name"], "decision_notified": True, "history_filters": True, "history_recipient_scoped": True, "unread_before": before_read, "unread_after": after_read, "service_order_link": service_order_notification["link"], "async_failure_isolated": True}
	finally:
		frappe.enqueue = original_enqueue
		frappe.flags.in_test = previous_in_test
		frappe.set_user(previous_user)


def run_inoperative_entry_term_checks() -> dict:
	"""The extra entry term is required only after an inoperant-device check-in advances."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		service_order = _create_action_request_service_order(attendant)
		order = frappe.get_doc("Service Order", service_order)
		order.entry_operating_condition = ENTRY_OPERATING_CONDITION_INOPERATIVE
		order.entry_photos = "/private/files/inoperative-entry-photo-test.jpg"
		order.save(ignore_permissions=True)

		# Opening the OS is never prevented. Only a subsequent technical transition needs
		# an evidenced additional acknowledgement.
		term_required_before_acceptance = False
		try:
			assert_completed_inoperative_device_term(service_order)
		except frappe.ValidationError:
			term_required_before_acceptance = True
		if not term_required_before_acceptance:
			raise AssertionError("OS inoperante avançou sem o termo adicional concluído.")

		frappe.set_user(attendant)
		issued = issue_os_acceptance(service_order, "Entrada")
		raw_token = issued["link"].rstrip("/").rsplit("/", 1)[-1]
		acceptance = frappe.get_doc("OS Acceptance", issued["acceptance"])
		if (
			acceptance.inoperative_device_term_version != INOPERATIVE_DEVICE_TERM_VERSION
			or "[PENDENTE REVISÃO JURÍDICA]" not in acceptance.inoperative_device_term_text
		):
			raise AssertionError("Termo adicional não foi versionado e registrado no aceite de entrada.")

		frappe.set_user("Guest")
		public = get_public_acceptance(raw_token)
		public_term = public.get("acceptance", {}).get("inoperative_device_term") or {}
		full_imei = frappe.db.get_value(
			"Customer Device", order.customer_device, "imei_serial"
		) or ""
		customer_facts = frappe.db.get_value(
			"Customer",
			order.customer,
			["customer_name", "custom_cpf", "custom_rg", "mobile_no", "custom_whatsapp"],
			as_dict=True,
		) or {}
		full_document = customer_facts.get("custom_cpf") or customer_facts.get("custom_rg") or ""
		full_phone = customer_facts.get("custom_whatsapp") or customer_facts.get("mobile_no") or ""
		full_name = customer_facts.get("customer_name") or ""
		if not public_term or public_term.get("version") != INOPERATIVE_DEVICE_TERM_VERSION:
			raise AssertionError("Página pública não exibiu o termo adicional aplicável.")
		if full_imei and full_imei in public_term.get("text", ""):
			raise AssertionError("Termo público expôs IMEI completo em vez da versão mascarada.")
		if any(value and value in public_term.get("text", "") for value in (full_document, full_phone, full_name)):
			raise AssertionError("Termo público expôs dado pessoal completo do cliente.")

		camera_image = BytesIO()
		Image.new("RGB", (24, 24), color=(32, 80, 120)).save(camera_image, format="JPEG")
		camera_selfie = "data:image/jpeg;base64," + b64encode(camera_image.getvalue()).decode()
		save_public_acceptance_selfie(raw_token, camera_selfie)

		signature_image = BytesIO()
		signature_canvas = Image.new("RGB", (640, 180), color=(250, 250, 250))
		signature_draw = ImageDraw.Draw(signature_canvas)
		signature_draw.line([(40, 120), (180, 50), (300, 135), (430, 45), (580, 110)], fill=(32, 36, 40), width=5)
		signature_canvas.save(signature_image, format="PNG")
		signature_data = "data:image/png;base64," + b64encode(signature_image.getvalue()).decode()
		missing_term_consent_blocked = False
		try:
			complete_public_acceptance(raw_token, signature_data, 1, 0)
		except frappe.ValidationError:
			missing_term_consent_blocked = True
		if not missing_term_consent_blocked:
			raise AssertionError("Aceite inoperante concluiu sem consentimento do termo adicional.")

		complete_public_acceptance(raw_token, signature_data, 1, 1)
		acceptance.reload()
		if (
			acceptance.status != "Concluído"
			or not acceptance.inoperative_device_term_accepted_on
			or acceptance.inoperative_device_term_version != INOPERATIVE_DEVICE_TERM_VERSION
		):
			raise AssertionError("Aceite não gravou o timestamp e a versão do termo adicional.")

		frappe.set_user("Administrator")
		order.reload()
		order.workflow_state = "Em diagnóstico"
		validate_aceites(order)
		entry_print_html = frappe.render_template(
			_termo_entrada_html(),
			{"doc": order, "tp": get_service_order_print_context(order)},
		)
		if (
			"APARELHO RECEBIDO SEM FUNCIONAMENTO" not in entry_print_html
			or ENTRY_OPERATING_CONDITION_INOPERATIVE not in entry_print_html
		):
			raise AssertionError("Termo de Entrada não imprimiu a condição e a cláusula adicional aceita.")

		# The entry form must preserve one free operational note in every path. The
		# extra term is conditional, but opening the OS is never conditional.
		suffix = frappe.generate_hash(length=8).upper()
		conditions = (
			(ENTRY_OPERATING_CONDITION_OK, False),
			(ENTRY_OPERATING_CONDITION_PARTIAL, True),
			(ENTRY_OPERATING_CONDITION_INOPERATIVE, True),
		)
		conditional_paths: dict[str, dict] = {}
		for index, (condition, expects_term) in enumerate(conditions, start=1):
			checkin = create_service_order_checkin(
				{
					"customer": {
						"customer_name": f"Cliente condição {suffix}-{index}",
						"mobile_no": "11999998888",
						"custom_whatsapp": "11999998888",
						"custom_nao_possui_cpf": 1,
						"custom_rg": f"RG-COND-{suffix}-{index}",
					},
					"device": {
						"brand": "Apple",
						"model": "iPhone condição",
						"imei_serial": f"35{int(suffix, 16) % 10**12:012d}{index}",
					},
					"service_order": {
						"reported_defect": "Falha relatada durante a entrada.",
						"physical_state": "Sem danos aparentes.",
						"attendance_notes": f"Observação livre {condition}.",
						"entry_operating_condition": condition,
					},
					"entry_photo": {"data_url": camera_selfie, "filename": f"condition-{suffix}-{index}.jpg"},
				}
			)
			created_order = frappe.get_doc("Service Order", checkin["service_order"]["name"])
			if (
				created_order.entry_operating_condition != condition
				or created_order.attendance_notes != f"Observação livre {condition}."
			):
				raise AssertionError("Check-in não persistiu condição e observação livre.")
			issued_condition = issue_os_acceptance(created_order.name, "Entrada")
			condition_acceptance = frappe.get_doc("OS Acceptance", issued_condition["acceptance"])
			if bool(condition_acceptance.inoperative_device_term_version) != expects_term:
				raise AssertionError("Termo de aparelho inoperante foi aplicado fora da condição correta.")
			conditional_paths[condition] = {
				"opens": True,
				"observation_saved": True,
				"inoperative_term_required": expects_term,
			}

		return {
			"status": "ok",
			"service_order": service_order,
			"opens_without_block": True,
			"term_required_before_advance": term_required_before_acceptance,
			"term_version": acceptance.inoperative_device_term_version,
			"public_imei_masked": bool(full_imei),
			"public_customer_facts_masked": True,
			"term_consent_required": missing_term_consent_blocked,
			"accepted_on": str(acceptance.inoperative_device_term_accepted_on),
			"entry_print_rendered": True,
			"conditional_entry_paths": conditional_paths,
		}
	finally:
		frappe.set_user(previous_user)


def run_administrative_center_checks() -> dict:
	"""Administrative reporting is account-gated and never transports cost fields."""
	from tecponto_app.tecponto import user_access

	previous_user = frappe.session.user
	try:
		owner = user_access.ensure_access_control()
		frappe.set_user(owner)
		admin = save_user_account(
			{
				"full_name": "Administração sem Diretor",
				"email": f"admin-center-{frappe.generate_hash(length=8)}@tecponto.local",
				"enabled": True,
				"roles": [user_access.SYSTEM_MANAGER_ROLE],
				"discount_limit": 0,
			}
		)["item"]
		frappe.set_user(admin["name"])
		payload = get_administrative_sales_report("month")
		expected = {"period", "totals", "categories", "payment_methods"}
		if set(payload) != expected:
			raise AssertionError("Relatório administrativo retornou uma projeção inesperada.")
		if set(payload["totals"]) != {"invoices", "gross_sales", "returns", "net_sales", "payment_entries", "cash_movements"}:
			raise AssertionError("Resumo administrativo retornou campos inesperados.")
		leaks = contains_sensitive_field(payload, forbidden_values={BUDGET_COST_GUARD_VALUATION})
		if leaks:
			raise AssertionError(f"Administrador sem Diretor recebeu dado financeiro sensível: {', '.join(leaks)}")
		director_blocked = False
		try:
			get_director_financial_summary()
		except frappe.PermissionError:
			director_blocked = True
		if not director_blocked:
			raise AssertionError("Administrador sem Diretor acessou indicadores de custo/lucro.")
		settings_payload = get_administration_settings()
		if set(settings_payload) != {"identity", "operation", "card_fees", "stage_slas"}:
			raise AssertionError("Tela administrativa recebeu uma projeção de configuração inesperada.")
		settings_without_commission_policy = {
			**settings_payload,
			"operation": {key: value for key, value in settings_payload["operation"].items() if "commission" not in key},
		}
		if contains_sensitive_field(settings_without_commission_policy, forbidden_values={BUDGET_COST_GUARD_VALUATION}):
			raise AssertionError("Configurações administrativas vazaram custo ou valuation para Administrador sem Diretor.")
		original_diagnosis_only = settings_payload["operation"].get("diagnosis_only_enabled")
		saved_settings = save_administration_settings(
			{
				"identity": {},
				"operation": {"diagnosis_only_enabled": not bool(original_diagnosis_only)},
				"card_fees": settings_payload["card_fees"],
			}
		)
		if bool(saved_settings["operation"].get("diagnosis_only_enabled")) == bool(original_diagnosis_only):
			raise AssertionError("Administrador não conseguiu salvar configuração operacional permitida.")
		save_administration_settings(
			{"identity": {}, "operation": {"diagnosis_only_enabled": original_diagnosis_only}, "card_fees": settings_payload["card_fees"]}
		)
		if not settings_payload["stage_slas"]:
			raise AssertionError("Configurações não retornaram os SLAs de etapa.")
		save_stage_sla(settings_payload["stage_slas"][0])
		allowlist_blocked = False
		try:
			save_administration_settings({"identity": {}, "operation": {"purchase_approval_threshold": 1}, "card_fees": []})
		except frappe.PermissionError:
			allowlist_blocked = True
		if not allowlist_blocked:
			raise AssertionError("Endpoint administrativo aceitou campo financeiro fora da allowlist.")

		frappe.set_user(owner)
		director_admin = save_user_account(
			{
				"full_name": "Administração Diretora",
				"email": f"admin-director-{frappe.generate_hash(length=8)}@tecponto.local",
				"enabled": True,
				"roles": [user_access.SYSTEM_MANAGER_ROLE, "Tecponto Diretor"],
				"discount_limit": 0,
			}
		)["item"]
		frappe.set_user(director_admin["name"])
		director_report = get_administrative_sales_report("7d")
		if contains_sensitive_field(director_report, forbidden_values={BUDGET_COST_GUARD_VALUATION}):
			raise AssertionError("Relatório comercial incluiu custo mesmo para Diretor.")
		director_financial = get_director_financial_summary()
		if "operational_cost" not in director_financial or "gross_operating_profit" not in director_financial:
			raise AssertionError("Diretor acumulado não acessou seu endpoint financeiro exclusivo.")

		# Only the owner may create a test user with a business role it does not hold.
		frappe.set_user(owner)
		attendant = _find_or_create_user("Tecponto Atendente")
		frappe.set_user(attendant)
		operational_blocked = False
		try:
			get_administrative_sales_report("today")
		except frappe.PermissionError:
			operational_blocked = True
		if not operational_blocked:
			raise AssertionError("Papel operacional acessou o relatório administrativo.")
		settings_blocked = False
		try:
			get_administration_settings()
		except frappe.PermissionError:
			settings_blocked = True
		if not settings_blocked:
			raise AssertionError("Papel operacional acessou configurações administrativas.")
		return {
			"admin_report_safe": True,
			"director_financial_blocked_for_admin": director_blocked,
			"director_accumulated_financial": True,
			"operational_blocked": operational_blocked,
			"settings_allowlist_and_gate": allowlist_blocked and settings_blocked,
		}
	finally:
		frappe.set_user(previous_user)


def run_user_management_api_checks() -> dict:
	"""Prove the React-facing account API cannot bypass the native User guards."""
	from tecponto_app.tecponto import user_access
	from frappe.utils.password import get_decrypted_password
	from tecponto_app.tecponto.pricing import _get_discount_limit

	previous_user = frappe.session.user
	try:
		owner = user_access.ensure_access_control()
		frappe.set_user(owner)
		used_pins = {
			get_decrypted_password("Tecponto Cashier Operator", operator, "pin", raise_exception=False)
			for operator in frappe.get_all("Tecponto Cashier Operator", filters={"active": 1}, pluck="name")
		}
		cashier_pin = next(f"{number:04d}" for number in range(1000, 10000) if f"{number:04d}" not in used_pins)
		initial_password = f"Tp!{frappe.generate_hash(length=14)}"
		with patch.object(frappe, "sendmail", side_effect=AssertionError("SMTP não pode ser acionado")):
			created = save_user_account({
				"full_name": "Operador Multipapel 3.15",
				"email": f"user-management-{frappe.generate_hash(length=8)}@tecponto.local",
				"enabled": True,
				"roles": ["Tecponto Atendente", "Tecponto Tecnico"],
				"discount_limit": 27.5,
				"cashier": {"enabled": True, "badge_code": f"TP-USER-{frappe.generate_hash(length=6)}", "pin": cashier_pin},
				"password": initial_password,
			})["item"]
		from frappe.utils.password import check_password
		if check_password(created["name"], initial_password) != created["name"]:
			raise AssertionError("A senha inicial definida sem SMTP não autenticou o usuário.")
		if "password" in frappe.as_json(created).lower() or initial_password in frappe.as_json(created):
			raise AssertionError("A criação de usuário devolveu a senha no payload.")
		if set(created["business_roles"]) != {"Tecponto Atendente", "Tecponto Tecnico"}:
			raise AssertionError("A tela/API não persistiu os múltiplos papéis da pessoa.")
		if created["cashier"]["badge_code"] == "" or created["cashier"].get("pin"):
			raise AssertionError("A API de pessoas expôs PIN ou não registrou o crachá.")
		frappe.set_user(created["name"])
		if _get_discount_limit() != 27.5:
			raise AssertionError("O limite individual de desconto não foi aplicado pelo motor.")

		frappe.set_user(owner)
		# The persistent runner intentionally retains historical fixtures. Querying
		# the account under test avoids a pagination-dependent assertion.
		listed = list_user_accounts(query=created["name"])
		listed_item = next((item for item in listed["items"] if item["name"] == created["name"]), None)
		listed_json = frappe.as_json(listed_item).lower() if listed_item else ""
		if not listed_item or listed_item["discount_limit"] != 27.5 or '"pin":' in listed_json or '"password":' in listed_json:
			raise AssertionError("A listagem de pessoas expôs credencial ou perdeu configuração individual.")
		reset_password = f"Tp!{frappe.generate_hash(length=15)}"
		roles_before_reset = set(frappe.get_roles(created["name"]))
		with patch.object(frappe, "sendmail", side_effect=AssertionError("SMTP não pode ser acionado")):
			reset_result = set_user_password(created["name"], reset_password)
		if not reset_result["changed"] or check_password(created["name"], reset_password) != created["name"]:
			raise AssertionError("A redefinição manual não atualizou a credencial nativa.")
		if set(frappe.get_roles(created["name"])) != roles_before_reset:
			raise AssertionError("Redefinir senha alterou papéis ou escalou privilégios.")
		access_event = frappe.get_all(
			"Tecponto Access Audit",
			filters={"affected_user": created["name"], "change_type": "Senha redefinida manualmente"},
			fields=["before_state", "after_state"],
			order_by="creation desc",
			limit_page_length=1,
		)
		if not access_event or reset_password in frappe.as_json(access_event):
			raise AssertionError("A redefinição não foi auditada com a credencial retida.")

		admin = save_user_account(
			{
				"full_name": "Administrador 3.15",
				"email": f"user-admin-{frappe.generate_hash(length=8)}@tecponto.local",
				"enabled": True,
				"roles": [user_access.SYSTEM_MANAGER_ROLE],
				"discount_limit": 0,
			}
		)["item"]
		frappe.set_user(admin["name"])
		owner_password_blocked = False
		try:
			set_user_password(owner, f"Tp!{frappe.generate_hash(length=15)}")
		except frappe.PermissionError:
			owner_password_blocked = True
		if not owner_password_blocked:
			raise AssertionError("Administrador redefiniu a senha da conta Proprietário.")
		director_blocked = False
		try:
			save_user_account(
				{
					"name": created["name"],
					"full_name": created["full_name"],
					"enabled": True,
					"roles": ["Tecponto Atendente", "Tecponto Tecnico", "Tecponto Diretor"],
					"discount_limit": 27.5,
				}
			)
		except frappe.PermissionError:
			director_blocked = True
		if not director_blocked:
			raise AssertionError("Administrador concedeu Diretor pela API de pessoas.")

		frappe.set_user(created["name"])
		attendant_blocked = False
		try:
			list_user_accounts()
		except frappe.PermissionError:
			attendant_blocked = True
		if not attendant_blocked:
			raise AssertionError("Usuário operacional acessou a lista de pessoas.")
		password_reset_blocked = False
		try:
			set_user_password(admin["name"], f"Tp!{frappe.generate_hash(length=15)}")
		except frappe.PermissionError:
			password_reset_blocked = True
		if not password_reset_blocked:
			raise AssertionError("Usuário operacional redefiniu senha de terceiro.")
		return {
			"status": "ok",
			"multi_role_user": created["name"],
			"individual_discount_limit": 27.5,
			"cashier_pin_withheld": True,
			"director_grant_blocked_for_admin": director_blocked,
			"operational_user_blocked": attendant_blocked,
			"manual_password_without_smtp": True,
			"password_does_not_change_roles": True,
			"owner_password_protected": owner_password_blocked,
			"operational_password_reset_blocked": password_reset_blocked,
		}
	finally:
		frappe.set_user(previous_user)


def run_user_access_control_checks() -> dict:
	"""Exercise every 3.15-1 anti-escalation rule through native User writes."""
	from tecponto_app.tecponto import user_access

	previous_user = frappe.session.user
	created_users: list[str] = []
	administrator_role_parents: list[str] = []
	owner = ""
	owner_setting_before_delete_test = ""
	owner_setting_before_employee_sync_test = ""
	commission_setting_before_employee_sync_test = None
	try:
		frappe.set_user("Administrator")
		owner = user_access.ensure_access_control()
		if not owner or user_access.get_account_level(owner) != "Proprietário":
			raise AssertionError("A conta Proprietário única não foi inicializada.")
		owner_roles = set(frappe.get_roles(owner))
		if not user_access.MANAGED_ROLES.issubset(owner_roles):
			raise AssertionError("O Proprietário precisa acumular administração e todos os papéis de negócio.")

		def create_user(label: str, roles: list[str]) -> str:
			email = f"access-{label}-{frappe.generate_hash(length=8)}@tecponto.local"
			doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": f"Access {label}",
					"enabled": 1,
					"send_welcome_email": 0,
					"roles": [{"role": role} for role in roles],
				}
			)
			doc.insert(ignore_permissions=True)
			created_users.append(doc.name)
			return doc.name

		frappe.set_user(owner)
		admin = create_user("admin", [user_access.SYSTEM_MANAGER_ROLE])
		operator = create_user("operator", ["Tecponto Atendente", "Tecponto Tecnico"])
		role_target = create_user("target", ["Tecponto Atendente"])

		second_owner_blocked = False
		try:
			user_access.set_initial_owner(operator)
		except frappe.ValidationError:
			second_owner_blocked = True
		if not second_owner_blocked:
			raise AssertionError("Foi possível criar um segundo Proprietário.")

		frappe.set_user(admin)
		owner_edit_blocked = False
		try:
			owner_doc = frappe.get_doc("User", owner)
			owner_doc.first_name = "Alteração indevida"
			owner_doc.save(ignore_permissions=True)
		except frappe.PermissionError:
			owner_edit_blocked = True
		if not owner_edit_blocked:
			raise AssertionError("Administrador editou a conta Proprietário.")

		# ERPNext updates the linked User while inserting an Employee. That
		# internal synchronization must not weaken the native owner guard.
		frappe.set_user(owner)
		owner_employee_sync_target = create_user("owner-employee-sync", ["Tecponto Tecnico"])
		owner_setting_before_employee_sync_test = owner
		commission_setting_before_employee_sync_test = frappe.db.get_single_value(
			"Tecponto Settings", "use_technician_commission"
		)
		frappe.db.set_single_value(
			"Tecponto Settings",
			user_access.OWNER_FIELD,
			owner_employee_sync_target,
			update_modified=False,
		)
		frappe.clear_cache()
		from tecponto_app.tecponto.hr import (
			_ensure_default_gender,
			_ensure_employee_for_user,
			_get_default_company,
		)

		# Employee synchronization is a commission-mode concern. The production
		# default remains lean/off; this fixture enables it only to prove the hook.
		frappe.db.set_single_value("Tecponto Settings", "use_technician_commission", 1)
		frappe.clear_cache()
		# Exercise the exact Employee -> User synchronization in isolation. The
		# commission feature switch has its own coverage and must not decide
		# whether this owner-guard regression test actually reaches the hook.
		company = _get_default_company()
		if not company:
			raise AssertionError("Empresa padrão ausente para o fixture de Employee.")
		_ensure_employee_for_user(owner_employee_sync_target, company, _ensure_default_gender())
		if not frappe.db.exists("Employee", {"user_id": owner_employee_sync_target}):
			raise AssertionError("Sincronização interna Employee → Proprietário foi bloqueada.")
		direct_owner_edit_still_blocked = False
		try:
			sync_target_doc = frappe.get_doc("User", owner_employee_sync_target)
			sync_target_doc.first_name = "Edição direta proibida"
			sync_target_doc.save(ignore_permissions=True)
		except frappe.PermissionError:
			direct_owner_edit_still_blocked = True
		finally:
			frappe.db.set_single_value(
				"Tecponto Settings",
				"use_technician_commission",
				commission_setting_before_employee_sync_test,
				update_modified=False,
			)
			frappe.db.set_single_value(
				"Tecponto Settings",
				user_access.OWNER_FIELD,
				owner_setting_before_employee_sync_test,
				update_modified=False,
			)
			frappe.clear_cache()
		if not direct_owner_edit_still_blocked:
			raise AssertionError("Sincronização de Employee abriu edição direta da conta Proprietário.")

		# Administrator has native Frappe deletion restrictions of its own. Point the
		# protected-owner setting at a disposable ordinary user and delete it through
		# frappe.delete_doc so this specifically proves our on_trash hook is invoked.
		frappe.set_user(owner)
		owner_delete_target = create_user("owner-delete-target", ["Tecponto Atendente"])
		owner_setting_before_delete_test = owner
		frappe.db.set_single_value("Tecponto Settings", user_access.OWNER_FIELD, owner_delete_target, update_modified=False)
		frappe.clear_cache()
		owner_delete_blocked = False
		try:
			frappe.delete_doc("User", owner_delete_target, ignore_permissions=True)
		except frappe.PermissionError:
			owner_delete_blocked = True
		finally:
			frappe.db.set_single_value(
				"Tecponto Settings",
				user_access.OWNER_FIELD,
				owner_setting_before_delete_test,
				update_modified=False,
			)
			frappe.clear_cache()
		if not owner_delete_blocked:
			raise AssertionError("Foi possível excluir a conta Proprietário pelo caminho nativo.")
		frappe.set_user(admin)

		director_grant_blocked = False
		try:
			target_doc = frappe.get_doc("User", role_target)
			target_doc.append("roles", {"role": "Tecponto Diretor"})
			target_doc.save(ignore_permissions=True)
		except frappe.PermissionError:
			director_grant_blocked = True
		if not director_grant_blocked:
			raise AssertionError("Administrador concedeu Diretor sem ser Proprietário.")

		administrator_creation_blocked = False
		try:
			create_user("forbidden-admin", [user_access.SYSTEM_MANAGER_ROLE])
		except frappe.PermissionError:
			administrator_creation_blocked = True
		if not administrator_creation_blocked:
			raise AssertionError("Administrador criou outro Administrador.")

		role_not_possessed_blocked = False
		try:
			target_doc = frappe.get_doc("User", role_target)
			target_doc.append("roles", {"role": "Tecponto Gestor"})
			target_doc.save(ignore_permissions=True)
		except frappe.PermissionError:
			role_not_possessed_blocked = True
		if not role_not_possessed_blocked:
			raise AssertionError("Administrador concedeu papel operacional que não possui.")

		frappe.set_user(operator)
		self_deactivation_blocked = False
		try:
			operator_doc = frappe.get_doc("User", operator)
			operator_doc.enabled = 0
			operator_doc.save(ignore_permissions=True)
		except frappe.PermissionError:
			self_deactivation_blocked = True
		if not self_deactivation_blocked:
			raise AssertionError("Usuário conseguiu desativar a própria conta.")

		# Direct database setup isolates the last-admin guard without ever weakening
		# a production account through a normal workflow. The persistent test site
		# can contain pre-existing System Managers, so save and restore every one.
		administrator_role_parents = [
			row.parent
			for row in frappe.get_all(
				"Has Role",
				filters={"parenttype": "User", "parentfield": "roles", "role": user_access.SYSTEM_MANAGER_ROLE},
				fields=["parent"],
			)
		]
		frappe.db.delete(
			"Has Role",
			{"parenttype": "User", "parentfield": "roles", "role": user_access.SYSTEM_MANAGER_ROLE},
		)
		frappe.get_doc(
			{
				"doctype": "Has Role",
				"parent": admin,
				"parenttype": "User",
				"parentfield": "roles",
				"idx": 99,
				"role": user_access.SYSTEM_MANAGER_ROLE,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache()
		frappe.set_user(admin)
		last_administrator_blocked = False
		try:
			admin_doc = frappe.get_doc("User", admin)
			admin_doc.set("roles", [row for row in admin_doc.roles if row.role != user_access.SYSTEM_MANAGER_ROLE])
			admin_doc.save(ignore_permissions=True)
		except frappe.PermissionError:
			last_administrator_blocked = True
		if not last_administrator_blocked:
			raise AssertionError("Foi possível remover o último Administrador do Sistema.")

		audits = frappe.get_all(
			user_access.AUDIT_DOCTYPE,
			filters={"affected_user": operator},
			fields=["name", "change_type", "actor", "before_state", "after_state"],
		)
		if not any(row.change_type == "Usuário criado" and row.actor == owner for row in audits):
			raise AssertionError("Criação de usuário não gerou trilha de auditoria.")
		audit = frappe.get_doc(user_access.AUDIT_DOCTYPE, audits[0].name)
		audit_update_blocked = False
		try:
			audit.change_type = "Alteração indevida"
			audit.save(ignore_permissions=True)
		except frappe.PermissionError:
			audit_update_blocked = True
		if not audit_update_blocked:
			raise AssertionError("Foi possível alterar uma trilha de auditoria de acesso.")
		audit_delete_blocked = False
		try:
			frappe.delete_doc(user_access.AUDIT_DOCTYPE, audit.name, ignore_permissions=True)
		except frappe.PermissionError:
			audit_delete_blocked = True
		if not audit_delete_blocked:
			raise AssertionError("Foi possível excluir uma trilha de auditoria de acesso.")

		return {
			"status": "ok",
			"owner": owner,
			"multi_role_user": operator,
			"second_owner_blocked": second_owner_blocked,
			"owner_edit_blocked": owner_edit_blocked,
			"employee_owner_sync_allowed": True,
			"employee_sync_does_not_bypass_owner_guard": direct_owner_edit_still_blocked,
			"owner_delete_blocked": owner_delete_blocked,
			"director_grant_blocked": director_grant_blocked,
			"administrator_creation_blocked": administrator_creation_blocked,
			"last_administrator_blocked": last_administrator_blocked,
			"self_deactivation_blocked": self_deactivation_blocked,
			"role_not_possessed_blocked": role_not_possessed_blocked,
			"audit_recorded": True,
			"audit_update_blocked": audit_update_blocked,
			"audit_delete_blocked": audit_delete_blocked,
		}
	finally:
		if administrator_role_parents:
			frappe.db.delete(
				"Has Role",
				{"parenttype": "User", "parentfield": "roles", "role": user_access.SYSTEM_MANAGER_ROLE},
			)
			for user in administrator_role_parents:
				frappe.get_doc(
					{
						"doctype": "Has Role",
						"parent": user,
						"parenttype": "User",
						"parentfield": "roles",
						"idx": 99,
						"role": user_access.SYSTEM_MANAGER_ROLE,
					}
				).insert(ignore_permissions=True)
			frappe.clear_cache()
		frappe.set_user(previous_user)


def run_workflow_metadata_gate_checks() -> dict:
	"""Native Desk workflow actions cannot bypass budget decision evidence."""
	from frappe.model.workflow import apply_workflow

	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		results = {}
		for decision, workflow_action, expected_status, notes in (
			("approve", "Aprovado", "Aprovado", "Aprovação de teste pelo balcão."),
			("reject", "Reprovado", "Reprovado", "Cliente recusou o orçamento de teste."),
		):
			service_order = _create_action_request_service_order(attendant)
			frappe.db.set_value(
				"Service Order",
				service_order,
				{
					"workflow_state": "Aguardando aprovação",
					"approval_status": "Pendente",
					"approval_channel": None,
					"approved_by": None,
					"approved_by_attendant": None,
					"approval_date": None,
					"approval_notes": None,
				},
				update_modified=False,
			)
			frappe.set_user(attendant)
			desk_bypassed_blocked = False
			try:
				apply_workflow(
					frappe.as_json({"doctype": "Service Order", "name": service_order}),
					workflow_action,
				)
			except frappe.ValidationError:
				desk_bypassed_blocked = True
			if not desk_bypassed_blocked:
				raise AssertionError(f"Desk aprovou/reprovou a OS sem os metadados obrigatórios: {decision}.")
			if frappe.db.get_value("Service Order", service_order, "workflow_state") != "Aguardando aprovação":
				raise AssertionError("Transição nativa inválida persistiu apesar do bloqueio de metadados.")

			decide_service_order_budget(
				service_order,
				{"decision": decision, "channel": "Presencial", "notes": notes, "attachment": "data:image/png;base64," + b64encode(b"desk-private-proof").decode()},
			)
			order = frappe.get_doc("Service Order", service_order)
			if (
				order.workflow_state != workflow_action
				or order.approval_status != expected_status
				or order.approval_channel != "Presencial"
				or order.approved_by_attendant != attendant
				or not order.approval_date
				or (decision == "reject" and order.approval_notes != notes)
			):
				raise AssertionError(f"Fluxo rastreável de orçamento não persistiu os metadados: {decision}.")
			results[decision] = {"desk_bypass_blocked": True, "recorded_by_flow": True}

		# The expiration check lives in both the internal flow and document validator.
		expired_order = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order",
			expired_order,
			{"workflow_state": "Aguardando aprovação", "approval_deadline": add_to_date(now_datetime(), hours=-1)},
			update_modified=False,
		)
		frappe.set_user(attendant)
		expired_detail = get_service_order_detail(expired_order)
		if not expired_detail["approval"]["expired"]:
			raise AssertionError("Detalhe da OS não sinalizou orçamento expirado para a interface.")
		internal_expiration_blocked = False
		try:
			decide_service_order_budget(expired_order, {"decision": "approve", "channel": "Presencial", "notes": ""})
		except frappe.ValidationError:
			internal_expiration_blocked = True
		if not internal_expiration_blocked or frappe.db.get_value("Service Order", expired_order, "approval_status") != "Pendente":
			raise AssertionError("Fluxo interno aprovou orçamento expirado ou gravou decisão parcial.")

		frappe.db.set_value(
			"Service Order",
			expired_order,
			{
				"approval_status": "Aprovado",
				"approval_channel": "Presencial",
				"approved_by_attendant": attendant,
				"approval_date": now_datetime(),
			},
			update_modified=False,
		)
		native_expiration_blocked = False
		try:
			apply_workflow(
				frappe.as_json({"doctype": "Service Order", "name": expired_order}),
				"Aprovado",
			)
		except frappe.ValidationError:
			native_expiration_blocked = True
		if not native_expiration_blocked:
			raise AssertionError("Desk aprovou orçamento expirado apesar do deadline.")
		results["expired"] = {"internal_blocked": internal_expiration_blocked, "desk_blocked": native_expiration_blocked}

		# The native workflow must not turn a blank technical assessment into a
		# customer approval request. Exercise both missing prerequisites directly
		# through Desk's workflow path.
		manager = _find_or_create_user("Tecponto Gestor")
		submission_order = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order",
			submission_order,
			{"workflow_state": "Em diagnóstico", "problem_found": None, "diagnosis_date": None},
			update_modified=False,
		)
		frappe.set_user(manager)
		missing_diagnosis_frontend = get_service_order_detail(submission_order)
		if "Diagnosticado — aguardando orçamento" not in missing_diagnosis_frontend["workflow_blockers"]:
			raise AssertionError("A interface não recebeu a orientação de diagnóstico pendente.")
		missing_diagnosis_blocked = False
		try:
			apply_workflow(
				frappe.as_json({"doctype": "Service Order", "name": submission_order}),
				"Diagnosticado — aguardando orçamento",
			)
		except frappe.ValidationError:
			missing_diagnosis_blocked = True
		if not missing_diagnosis_blocked:
			raise AssertionError("Desk enviou OS sem diagnóstico para aprovação.")

		submission_doc = frappe.get_doc("Service Order", submission_order)
		submission_doc.problem_found = "Diagnóstico preenchido para a trava de orçamento."
		submission_doc.diagnosis_date = now_datetime().date()
		submission_doc.set("services", [])
		submission_doc.set("parts", [])
		submission_doc.save(ignore_permissions=True)
		complete_technical_diagnosis(
			submission_order,
			"Diagnóstico preenchido para a trava de orçamento.",
			"Balcão",
		)
		missing_budget_frontend = get_service_order_detail(submission_order)
		if "Aguardando aprovação" not in missing_budget_frontend["workflow_blockers"]:
			raise AssertionError("A interface não recebeu a orientação de orçamento pendente.")
		missing_budget_blocked = False
		try:
			apply_workflow(
				frappe.as_json({"doctype": "Service Order", "name": submission_order}),
				"Aguardando aprovação",
			)
		except frappe.ValidationError:
			missing_budget_blocked = True
		if not missing_budget_blocked:
			raise AssertionError("Desk enviou OS sem linhas de orçamento para aprovação.")

		submission_doc = frappe.get_doc("Service Order", submission_order)
		submission_doc.append(
			"services",
			{
				"item_code": _get_demo_item(is_stock_item=0),
				"description": "Serviço de garantia sem cobrança",
				"qty": 1,
				"rate": 0,
			},
		)
		submission_doc.save(ignore_permissions=True)
		completed_submission_frontend = get_service_order_detail(submission_order)
		if (
			"Aguardando aprovação" in completed_submission_frontend["workflow_blockers"]
			and "Aguardando aprovação" not in completed_submission_frontend["workflow_requestable_transitions"]
		):
			raise AssertionError("A interface manteve a trava de completude após diagnóstico e orçamento completos.")
		apply_workflow(
			frappe.as_json({"doctype": "Service Order", "name": submission_order}),
			"Aguardando aprovação",
		)
		if frappe.db.get_value("Service Order", submission_order, "workflow_state") != "Aguardando aprovação":
			raise AssertionError("OS válida não entrou em Aguardando aprovação.")
		results["submission"] = {
			"missing_diagnosis_blocked": missing_diagnosis_blocked,
			"missing_budget_blocked": missing_budget_blocked,
			"zero_price_warranty_line_allowed": True,
		}

		# Remote channels need an auditable dispatch record; a Desk user cannot
		# merely type WhatsApp or Link into metadata to emulate customer evidence.
		remote_order = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order",
			remote_order,
			{
				"workflow_state": "Aguardando aprovação",
				"approval_status": "Aprovado",
				"approval_channel": "WhatsApp",
				"approved_by_attendant": attendant,
				"approval_date": now_datetime(),
			},
			update_modified=False,
		)
		remote_dispatch_blocked = False
		try:
			apply_workflow(
				frappe.as_json({"doctype": "Service Order", "name": remote_order}),
				"Aprovado",
			)
		except frappe.ValidationError:
			remote_dispatch_blocked = True
		if not remote_dispatch_blocked:
			raise AssertionError("Desk aprovou decisão por WhatsApp sem comprovante de envio.")
		frappe.get_doc(
			{
				"doctype": "Communication",
				"subject": f"Orçamento enviado - {remote_order}",
				"communication_medium": "Chat",
				"communication_type": "Communication",
				"sent_or_received": "Sent",
				"status": "Linked",
				"sender": attendant,
				"content": "Orçamento enviado para validação de fluxo.",
				"reference_doctype": "Service Order",
				"reference_name": remote_order,
			}
		).insert(ignore_permissions=True)
		from frappe.utils.file_manager import save_file
		save_file("comprovante_autorizacao.txt", b"autorizacao", "Service Order", remote_order, is_private=1)
		apply_workflow(
			frappe.as_json({"doctype": "Service Order", "name": remote_order}),
			"Aprovado",
		)
		if frappe.db.get_value("Service Order", remote_order, "workflow_state") != "Aprovado":
			raise AssertionError("Decisão remota com comprovante de envio não avançou a OS.")
		results["remote_dispatch"] = {
			"missing_dispatch_blocked": remote_dispatch_blocked,
			"documented_dispatch_allowed": True,
		}

		return {"status": "ok", "native_workflow": results}
	finally:
		frappe.set_user(previous_user)


def run_link_acceptance_gate_checks() -> dict:
	"""New OS cannot use legacy Desk fields to bypass link acceptance evidence."""
	from frappe.model.workflow import apply_workflow

	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		customer = _get_or_create_demo_customer()
		device = _get_or_create_demo_device(customer)
		service_order = _upsert_demo_service_order(
			demo={
				"slug": f"link-required-{frappe.generate_hash(length=8)}",
				"state": "Entrada criada",
				"approval_status": "Pendente",
				"reported_defect": "OS criada para validar aceite obrigatório por link.",
				"problem_found": None,
			},
			customer=customer,
			device=device,
			service_item=_get_demo_item(is_stock_item=0),
			part_item=_get_demo_item(is_stock_item=1),
			warehouse=_get_demo_warehouse(),
			attendant=attendant,
			legacy_fixture=False,
		)
		if not frappe.db.get_value("Service Order", service_order, "link_acceptance_required"):
			raise AssertionError("OS nova não foi marcada para exigir aceite por link no motor.")
		frappe.db.set_value("Service Order", service_order, "technician", technician, update_modified=False)

		frappe.set_user(technician)
		desk_bypass_blocked = False
		try:
			apply_workflow(
				frappe.as_json({"doctype": "Service Order", "name": service_order}),
				"Em diagnóstico",
			)
		except frappe.ValidationError:
			desk_bypass_blocked = True
		if not desk_bypass_blocked:
			raise AssertionError("Desk avançou uma OS nova sem aceite por link concluído.")

		frappe.set_user(attendant)
		issued = issue_os_acceptance(service_order, "Entrada")
		raw_token = issued["link"].rstrip("/").rsplit("/", 1)[-1]
		camera = BytesIO()
		Image.new("RGB", (24, 24), color=(24, 40, 60)).save(camera, format="JPEG")
		selfie = "data:image/jpeg;base64," + b64encode(camera.getvalue()).decode()
		signature = BytesIO()
		signature_canvas = Image.new("RGB", (180, 70), color=(250, 250, 250))
		ImageDraw.Draw(signature_canvas).line([(16, 52), (56, 18), (94, 50), (150, 20)], fill=(32, 36, 40), width=4)
		signature_canvas.save(signature, format="PNG")
		signature_data = "data:image/png;base64," + b64encode(signature.getvalue()).decode()
		frappe.set_user("Guest")
		save_public_acceptance_selfie(raw_token, selfie)
		complete_public_acceptance(raw_token, signature_data, 1)

		frappe.set_user(technician)
		apply_workflow(
			frappe.as_json({"doctype": "Service Order", "name": service_order}),
			"Em diagnóstico",
		)
		if frappe.db.get_value("Service Order", service_order, "workflow_state") != "Em diagnóstico":
			raise AssertionError("OS não avançou após o aceite por link íntegro.")

		legacy_order = _create_action_request_service_order(attendant)
		frappe.db.set_value("Service Order", legacy_order, "technician", technician, update_modified=False)
		frappe.set_user(technician)
		apply_workflow(
			frappe.as_json({"doctype": "Service Order", "name": legacy_order}),
			"Em diagnóstico",
		)
		if frappe.db.get_value("Service Order", legacy_order, "workflow_state") != "Em diagnóstico":
			raise AssertionError("OS histórica perdeu a compatibilidade do aceite presencial legado.")

		return {
			"status": "ok",
			"new_orders_require_link_acceptance": True,
			"desk_bypass_blocked": desk_bypass_blocked,
			"legacy_orders_compatible": True,
		}
	finally:
		frappe.set_user(previous_user)


def run_no_repair_pickup_checks() -> dict:
	"""Terminal no-repair outcomes retain an auditable, deliverable pickup route."""
	from frappe.model.workflow import apply_workflow

	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		results = {}
		for source_state in ("Reprovado", "Orçamento expirado", "Sem conserto"):
			service_order = _create_action_request_service_order(attendant)
			frappe.db.set_value(
				"Service Order",
				service_order,
				{
					"workflow_state": source_state,
					"approval_status": "Reprovado" if source_state == "Reprovado" else "Pendente",
					"approval_channel": "Presencial" if source_state == "Reprovado" else None,
					"approved_by_attendant": attendant if source_state == "Reprovado" else None,
					"approval_date": now_datetime() if source_state == "Reprovado" else None,
					"approval_notes": "Cliente recusou o orçamento." if source_state == "Reprovado" else None,
					"pickup_without_repair": 0,
					"sales_invoice": None,
					"customer_signature": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAghX7JQAAAABJRU5ErkJggg==",
				},
				update_modified=False,
			)
			frappe.set_user(manager)
			apply_workflow(
				frappe.as_json({"doctype": "Service Order", "name": service_order}),
				"Liberar para retirada",
			)
			ready = frappe.get_doc("Service Order", service_order)
			if ready.workflow_state != "Pronto para retirada" or not ready.pickup_without_repair or ready.sales_invoice:
				raise AssertionError(f"{source_state} não foi liberada para retirada sem reparo corretamente.")
			frontend_ready = get_service_order_detail(service_order)
			if not frontend_ready["pickup"]["without_repair"]:
				raise AssertionError("A interface não recebeu o indicador de retirada sem reparo.")
			apply_workflow(
				frappe.as_json({"doctype": "Service Order", "name": service_order}),
				"Entregue",
			)
			completed = frappe.get_doc("Service Order", service_order)
			if completed.workflow_state != "Entregue" or not completed.pickup_without_repair:
				raise AssertionError(f"{source_state} não concluiu a retirada sem reparo.")
			results[source_state] = {"released": True, "delivered": True}
		return {"status": "ok", "states": results, "no_unearned_invoice": True}
	finally:
		frappe.set_user(previous_user)


def run_public_acceptance_checks() -> dict:
	"""Public acceptance is read-only, guest-safe and token-limited."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		service_order = _create_action_request_service_order(attendant)

		frappe.set_user(attendant)
		issued = issue_os_acceptance(service_order, "Entrada")
		raw_token = issued["link"].rstrip("/").rsplit("/", 1)[-1]
		acceptance = frappe.get_doc("OS Acceptance", issued["acceptance"])
		if raw_token in frappe.as_json(acceptance.as_dict()) or not acceptance.token_hash:
			raise AssertionError("Token bruto não pode ser persistido no OS Acceptance.")
		if not issued["qr_svg"].startswith("data:image/svg+xml;base64,"):
			raise AssertionError("Emissão não retornou QR SVG local.")

		frappe.set_user("Guest")
		public = get_public_acceptance(raw_token)
		if not public.get("valid") or public["service_order"].get("number") != service_order:
			raise AssertionError("Guest não recebeu a projeção pública read-only esperada.")
		forbidden_keys = {"services", "parts", "rate", "cost", "valuation_rate", "sales_invoice", "customer_email", "imei", "imei_serial"}
		if forbidden_keys & set(public["service_order"]):
			raise AssertionError("Projeção pública expôs dado interno da OS.")
		full_imei = frappe.db.get_value("Customer Device", frappe.db.get_value("Service Order", service_order, "customer_device"), "imei_serial") or ""
		public_imei = public["service_order"].get("imei_suffix") or ""
		if full_imei and (full_imei in frappe.as_json(public) or public_imei != f"•••• {full_imei[-4:]}"):
			raise AssertionError("Projeção pública de aceite expôs o IMEI completo em vez de somente os quatro últimos dígitos.")
		if frappe.db.get_value("OS Acceptance", acceptance.name, "status") != "Pendente":
			raise AssertionError("Consulta pública não pode consumir ou alterar um aceite pendente.")
		camera_image = BytesIO()
		camera_seed = int(frappe.generate_hash(length=4), 16)
		Image.new("RGB", (24, 24), color=(camera_seed % 255, 40, 60)).save(camera_image, format="JPEG")
		camera_selfie = "data:image/jpeg;base64," + b64encode(camera_image.getvalue()).decode()
		saved = save_public_acceptance_selfie(raw_token, camera_selfie)
		acceptance.reload()
		selfie_file = frappe.get_doc("File", acceptance.selfie_file)
		if (
			not saved.get("saved")
			or selfie_file.attached_to_doctype != "Service Order"
			or selfie_file.attached_to_name != service_order
			or not selfie_file.is_private
			or not os.path.isfile(selfie_file.get_full_path())
		):
			raise AssertionError("Selfie pública não foi salva como anexo privado da OS.")
		public_after_selfie = get_public_acceptance(raw_token)
		if not public_after_selfie["acceptance"].get("selfie_captured") or "selfie_file" in public_after_selfie["acceptance"]:
			raise AssertionError("Projeção pública da selfie expôs arquivo interno ou não refletiu a captura.")
		duplicate_blocked = False
		try:
			save_public_acceptance_selfie(raw_token, camera_selfie)
		except frappe.ValidationError:
			duplicate_blocked = True
		if not duplicate_blocked:
			raise AssertionError("Endpoint público aceitou uma segunda selfie para o mesmo aceite.")
		file_picker_payload_blocked = False
		try:
			save_public_acceptance_selfie(raw_token, "data:image/png;base64,aGVsbG8=")
		except frappe.ValidationError:
			file_picker_payload_blocked = True
		if not file_picker_payload_blocked:
			raise AssertionError("Endpoint público aceitou formato fora da captura JPEG da câmera.")
		signature_image = BytesIO()
		signature_canvas = Image.new("RGB", (640, 180), color=(250, 250, 250))
		signature_draw = ImageDraw.Draw(signature_canvas)
		signature_draw.line([(40, 120), (180, 50), (300, 135), (430, 45), (580, 110)], fill=(32, 36, 40), width=5)
		signature_draw.rectangle((620, 160, 635, 175), fill=(camera_seed % 255, 36, 40))
		signature_canvas.save(signature_image, format="PNG")
		signature_data = "data:image/png;base64," + b64encode(signature_image.getvalue()).decode()
		missing_selfie_completion_blocked = False
		selfie_path = selfie_file.get_full_path()
		quarantined_selfie_path = f"{selfie_path}.integrity-check"
		os.replace(selfie_path, quarantined_selfie_path)
		try:
			try:
				complete_public_acceptance(raw_token, signature_data, 1)
			except frappe.ValidationError:
				missing_selfie_completion_blocked = True
		finally:
			os.replace(quarantined_selfie_path, selfie_path)
		if not missing_selfie_completion_blocked:
			raise AssertionError("Aceite público concluiu mesmo com a selfie privada ausente no disco.")
		consent_required = False
		try:
			complete_public_acceptance(raw_token, signature_data, 0)
		except frappe.ValidationError:
			consent_required = True
		if not consent_required:
			raise AssertionError("Aceite público foi concluído sem consentimento LGPD explícito.")
		completed = complete_public_acceptance(raw_token, signature_data, 1)
		acceptance.reload()
		signature_file = frappe.get_doc("File", acceptance.signature_file)
		entry_signature = frappe.db.get_value("Service Order", service_order, "entry_signature")
		if not completed.get("completed") or acceptance.status != "Concluído" or not acceptance.consent_version or not acceptance.consented_on or not acceptance.used_on:
			raise AssertionError("Aceite de entrada não foi consumido com consentimento e timestamp.")
		if (
			not signature_file.is_private
			or signature_file.attached_to_name != service_order
			or not os.path.isfile(signature_file.get_full_path())
			or entry_signature != signature_data
		):
			raise AssertionError("Assinatura de entrada não foi vinculada de forma privada à OS.")
		missing_signature_blocked = False
		signature_path = signature_file.get_full_path()
		quarantined_signature_path = f"{signature_path}.integrity-check"
		os.replace(signature_path, quarantined_signature_path)
		missing_evidence_detected_by_audit = False
		try:
			try:
				assert_completed_acceptance_evidence(service_order, "Entrada")
			except frappe.ValidationError:
				missing_signature_blocked = True
			frappe.set_user("Administrator")
			missing_evidence_detected_by_audit = bool(audit_completed_acceptance_evidence(service_order)["issues"])
		finally:
			os.replace(quarantined_signature_path, signature_path)
		if not missing_signature_blocked or not missing_evidence_detected_by_audit:
			raise AssertionError("Aceite concluído não bloqueou quando o arquivo privado da assinatura desapareceu.")
		frappe.set_user(attendant)
		audit_permission_blocked = False
		try:
			audit_completed_acceptance_evidence(service_order)
		except frappe.PermissionError:
			audit_permission_blocked = True
		if not audit_permission_blocked:
			raise AssertionError("Atendente acessou a auditoria administrativa de evidências.")
		frappe.set_user("Administrator")
		evidence_audit = audit_completed_acceptance_evidence(service_order)
		if evidence_audit["issues"] or evidence_audit["checked"] != 1:
			raise AssertionError("Auditoria de evidências não confirmou o aceite íntegro após restaurar o arquivo privado.")
		token_reuse_blocked = False
		try:
			complete_public_acceptance(raw_token, signature_data, 1)
		except frappe.PermissionError:
			token_reuse_blocked = True
		if not token_reuse_blocked:
			raise AssertionError("Token concluído foi reutilizado.")

		# A paper acceptance is a different proof: it has one private scanned copy
		# and hash, never forged selfie/signature fields from the digital flow.
		frappe.set_user(attendant)
		physical_order = _create_action_request_service_order(attendant)
		physical = record_physical_acceptance(
			physical_order,
			"Entrada",
			camera_selfie,
			"aceite-entrada.jpg",
		)
		physical_doc = frappe.get_doc("OS Acceptance", physical["acceptance"])
		physical_file = frappe.get_doc("File", physical_doc.physical_evidence_file)
		if (
			physical_doc.acceptance_method != "Físico"
			or physical_doc.selfie_file
			or physical_doc.signature_file
			or not physical_doc.physical_evidence_hash
			or not physical_doc.physical_collected_by
			or not physical_file.is_private
			or physical_file.attached_to_name != physical_order
			or not has_completed_physical_acceptance(physical_order, "Entrada")
		):
			raise AssertionError("Aceite físico não preservou sua própria evidência privada e distinta do aceite digital.")
		from tecponto_app.tecponto.service_order.aceites import validate_aceites

		physical_order_doc = frappe.get_doc("Service Order", physical_order)
		physical_order_doc.entry_photos = "Foto de entrada registrada no balcão."
		physical_order_doc.workflow_state = "Em diagnóstico"
		validate_aceites(physical_order_doc)
		physical_missing_file_blocked = False
		physical_path = physical_file.get_full_path()
		quarantined_physical_path = f"{physical_path}.integrity-check"
		os.replace(physical_path, quarantined_physical_path)
		try:
			try:
				has_completed_physical_acceptance(physical_order, "Entrada")
			except frappe.ValidationError:
				physical_missing_file_blocked = True
		finally:
			os.replace(quarantined_physical_path, physical_path)
		if not physical_missing_file_blocked:
			raise AssertionError("Aceite físico foi aceito sem a via assinada presente no disco.")
		physical_upload_blocked = False
		try:
			record_physical_acceptance(physical_order, "Retirada", "data:text/plain;base64,aGVsbG8=", "aceite.txt")
		except frappe.ValidationError:
			physical_upload_blocked = True
		if not physical_upload_blocked:
			raise AssertionError("Aceite físico aceitou arquivo fora de JPEG, PNG ou PDF.")

		# An attendant cannot skip the selfie. A Gestor may approve only a documented exception,
		# after which signature and LGPD consent remain mandatory.
		frappe.set_user(attendant)
		exception_issued = issue_os_acceptance(service_order, "Entrada")
		exception_token = exception_issued["link"].rstrip("/").rsplit("/", 1)[-1]
		frappe.set_user("Guest")
		selfie_skip_blocked = False
		try:
			complete_public_acceptance(exception_token, signature_data, 1)
		except frappe.ValidationError:
			selfie_skip_blocked = True
		if not selfie_skip_blocked:
			raise AssertionError("Aceite público concluiu sem selfie e sem exceção do Gestor.")

		frappe.set_user(attendant)
		exception_request = create_request(
			"acceptance_selfie_exception",
			exception_issued["acceptance"],
			"Cliente recusou a selfie; identidade conferida presencialmente no balcão.",
		)
		manager = _find_or_create_user("Tecponto Gestor")
		frappe.set_user(manager)
		approved_exception = approve_request(exception_request["name"])
		exception_doc = frappe.get_doc("OS Acceptance", exception_issued["acceptance"])
		if not approved_exception or not exception_doc.selfie_exception or not exception_doc.selfie_exception_reason or exception_doc.selfie_exception_by != manager or not exception_doc.selfie_exception_on:
			raise AssertionError("Exceção de selfie não ficou auditada no aceite após a aprovação do Gestor.")
		frappe.set_user("Guest")
		exception_completed = complete_public_acceptance(exception_token, signature_data, 1)
		if not exception_completed.get("completed") or exception_doc.name != exception_completed.get("acceptance"):
			raise AssertionError("Aceite excepcional não concluiu após assinatura e consentimento.")

		# Retirada uses the exact same public flow, but mirrors its signature to the pickup field.
		frappe.set_user(attendant)
		pickup_issued = issue_os_acceptance(service_order, "Retirada")
		pickup_token = pickup_issued["link"].rstrip("/").rsplit("/", 1)[-1]
		frappe.set_user("Guest")
		save_public_acceptance_selfie(pickup_token, camera_selfie)
		pickup_completed = complete_public_acceptance(pickup_token, signature_data, 1)
		if not pickup_completed.get("completed") or frappe.db.get_value("Service Order", service_order, "customer_signature") != signature_data:
			raise AssertionError("Aceite público de retirada não gravou a assinatura de retirada na OS.")

		# A third-party pickup keeps the signer identity on the acceptance; the selfie captured
		# by the public link belongs to that third party, never to the customer record by default.
		frappe.set_user("Administrator")
		frappe.db.set_value(
			"Service Order",
			service_order,
			{
				"picked_up_by": "Mariana Souza",
				"picked_up_doc": "RG 44.555.666-7",
				"picked_up_by_third_party": 1,
				"third_party_doc": "RG 44.555.666-7",
				"third_party_auth": "Autorização apresentada e conferida no balcão.",
			},
			update_modified=False,
		)
		frappe.set_user(attendant)
		third_issued = issue_os_acceptance(service_order, "Retirada", "Terceiro")
		third_token = third_issued["link"].rstrip("/").rsplit("/", 1)[-1]
		third_doc = frappe.get_doc("OS Acceptance", third_issued["acceptance"])
		if third_doc.signer_role != "Terceiro" or third_doc.signer_name != "Mariana Souza" or third_doc.signer_document != "RG 44.555.666-7" or not third_doc.signer_authorization:
			raise AssertionError("Aceite de terceiro não reteve nome, documento e autorização.")
		frappe.set_user("Guest")
		save_public_acceptance_selfie(third_token, camera_selfie)
		third_completed = complete_public_acceptance(third_token, signature_data, 1)
		third_doc.reload()
		if not third_completed.get("completed") or not third_doc.selfie_file or third_doc.status != "Concluído":
			raise AssertionError("Selfie do terceiro não foi vinculada ao aceite de retirada.")

		# Reemitir invalida um token pendente antes da captura de selfie/assinatura.
		frappe.set_user(attendant)
		pending = issue_os_acceptance(service_order, "Entrada")
		pending_token = pending["link"].rstrip("/").rsplit("/", 1)[-1]
		reissued = issue_os_acceptance(service_order, "Entrada")
		frappe.set_user("Guest")
		if get_public_acceptance(pending_token).get("valid"):
			raise AssertionError("Um link substituído continuou utilizável.")
		if not get_public_acceptance(reissued["link"].rstrip("/").rsplit("/", 1)[-1]).get("valid"):
			raise AssertionError("O novo link de aceite não ficou disponível.")

		invalid = get_public_acceptance("token-invalido-que-nao-existe")
		if invalid.get("valid"):
			raise AssertionError("Token inválido foi aceito pela rota pública.")

		frappe.set_user(attendant)
		expiring = issue_os_acceptance(service_order, "Retirada")
		expiring_token = expiring["link"].rstrip("/").rsplit("/", 1)[-1]
		frappe.db.set_value("OS Acceptance", expiring["acceptance"], "expires_on", add_to_date(now_datetime(), hours=-1))
		frappe.set_user("Guest")
		expired = get_public_acceptance(expiring_token)
		if expired.get("valid") or frappe.db.get_value("OS Acceptance", expiring["acceptance"], "status") != "Expirado":
			raise AssertionError("Token expirado continuou utilizável.")
		frappe.set_user("Administrator")
		full_evidence_audit = audit_completed_acceptance_evidence(service_order)
		if full_evidence_audit["issues"] or full_evidence_audit["checked"] < 4:
			raise AssertionError("Auditoria histórica não validou cada aceite concluído da mesma OS.")

		return {
			"status": "ok",
			"acceptance": acceptance.name,
			"guest_read_only": True,
			"imei_partial_only": bool(public_imei),
			"selfie_attached_to_service_order": True,
			"missing_selfie_blocks_completion": missing_selfie_completion_blocked,
			"camera_jpeg_only": True,
			"signature_and_consent_recorded": True,
			"evidence_audit": {"checked": full_evidence_audit["checked"], "issues": full_evidence_audit["issues"], "attendant_blocked": audit_permission_blocked, "missing_file_detected": missing_evidence_detected_by_audit},
			"consent_required": consent_required,
			"pickup_signature_recorded": True,
			"selfie_skip_blocked": selfie_skip_blocked,
			"selfie_exception_audited": bool(exception_doc.selfie_exception_request),
			"third_party_selfie_and_identity_recorded": bool(third_doc.selfie_file),
			"token_reuse_blocked": token_reuse_blocked,
			"reissued_token_invalidated": True,
			"invalid_token_blocked": not invalid.get("valid"),
			"expired_token_blocked": not expired.get("valid"),
			"physical_acceptance_private_and_distinct": True,
			"physical_acceptance_satisfies_entry_gate": True,
		}
	finally:
		frappe.set_user(previous_user)


def run_action_request_checks() -> dict:
	"""Acceptance checks for approval requests: no requester bypass, no expired execution."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		order_name = _create_action_request_service_order(attendant)
		limit = flt(frappe.db.get_single_value("Tecponto Settings", "discount_limit") or 0)
		discount = max(limit + 1, 1)

		frappe.set_user(attendant)
		created = create_request("service_order_discount", order_name, "Cliente solicitou exceção de desconto.", {"discount": discount})
		request = frappe.get_doc("Tecponto Request", created["name"])
		if request.status != "Pendente" or request.approver_role != "Tecponto Gestor":
			raise AssertionError("Trava não criou solicitação pendente para Gestor.")

		self_approval_blocked = False
		try:
			approve_request(request.name)
		except frappe.PermissionError:
			self_approval_blocked = True
		if not self_approval_blocked:
			raise AssertionError("Solicitante aprovou a própria solicitação.")

		frappe.set_user(manager)
		approved = approve_request(request.name)
		if approved["status"] != "Aprovada" or flt(frappe.db.get_value("Service Order", order_name, "discount")) != discount:
			raise AssertionError("Aprovação do Gestor não reexecutou a ação no motor.")

		frappe.set_user(attendant)
		rejected = create_request("service_order_discount", order_name, "Nova exceção recusável.", {"discount": discount + 1})
		frappe.set_user(manager)
		reject_request(rejected["name"])
		if flt(frappe.db.get_value("Service Order", order_name, "discount")) != discount:
			raise AssertionError("Reprovação executou uma ação indevidamente.")

		frappe.set_user(attendant)
		expired = create_request("service_order_discount", order_name, "Exceção que deve expirar.", {"discount": discount + 2})
		frappe.db.set_value("Tecponto Request", expired["name"], "expires_on", add_to_date(now_datetime(), hours=-1))
		expired_count = expire_requests()
		if frappe.db.get_value("Tecponto Request", expired["name"], "status") != "Expirada":
			raise AssertionError("Scheduler não expirou solicitação vencida.")
		if flt(frappe.db.get_value("Service Order", order_name, "discount")) != discount:
			raise AssertionError("Solicitação expirada executou uma ação.")

		# PDV: a exceção nasce antes de existir nota; a aprovação recria a venda pelo endpoint cirúrgico.
		demo_pos = _ensure_pos_demo_records()
		pos_discount = max(limit + 1, 1)
		pos_total = flt(79.90 - pos_discount, 2)
		if pos_total <= 0:
			raise AssertionError("Massa de teste do PDV não comporta desconto acima do limite.")
		pos_payload = {
			"customer": _get_or_create_demo_customer(),
			"items": [{"item_code": POS_BARCODE_ITEM, "qty": 1}],
			"discount_amount": pos_discount,
			"payments": [{"mode_of_payment": "Pix", "amount": pos_total, "installments": 1}],
			"idempotency_key": f"tp-request-pos-{frappe.generate_hash(length=20)}",
		}
		frappe.set_user(attendant)
		frappe.db.commit()
		pos_request = create_request(
			"pos_discount",
			pos_payload["customer"],
			"Desconto de balcão autorizado pelo cliente.",
			{"sale_payload": pos_payload},
		)
		if pos_request["name"] not in {row["name"] for row in list_my_requests()}:
			raise AssertionError("Lista Minhas solicitações não retornou a exceção do PDV.")

		frappe.set_user(manager)
		if pos_request["name"] not in {row["name"] for row in list_pending_approvals()}:
			raise AssertionError("Lista Aguardando minha aprovação não retornou a exceção do PDV.")
		pos_approved = approve_request(pos_request["name"])
		pos_result = frappe.parse_json(frappe.db.get_value("Tecponto Request", pos_request["name"], "execution_result"))
		if pos_approved["status"] != "Aprovada" or not pos_result.get("sale"):
			raise AssertionError("Aprovação do desconto do PDV não criou a venda pelo endpoint cirúrgico.")

		# Piso de custo: a venda é novamente resolvida no servidor quando o Gestor aprova.
		previous_discount_limit = frappe.db.get_single_value("Tecponto Settings", "discount_limit")
		floor_request = None
		floor_result = None
		try:
			frappe.db.set_single_value("Tecponto Settings", "discount_limit", 999)
			floor_payload = {
				"customer": _get_or_create_demo_customer(),
				"items": [{"item_code": POS_BARCODE_ITEM, "qty": 1}],
				"discount_amount": 70,
				"payments": [{"mode_of_payment": "Pix", "amount": 9.90, "installments": 1}],
				"idempotency_key": f"tp-request-floor-{frappe.generate_hash(length=20)}",
			}
			frappe.set_user(attendant)
			floor_blocked = False
			try:
				pos_create_sale(floor_payload)
			except frappe.ValidationError:
				floor_blocked = True
			if not floor_blocked:
				raise AssertionError("Atendente concluiu venda abaixo do custo sem solicitar aprovação.")
			frappe.db.commit()
			floor_request = create_request(
				"pos_price_floor",
				floor_payload["customer"],
				"Preço promocional abaixo do custo autorizado pelo cliente.",
				{"sale_payload": floor_payload},
			)
			frappe.set_user(manager)
			approve_request(floor_request["name"])
			floor_result = frappe.parse_json(frappe.db.get_value("Tecponto Request", floor_request["name"], "execution_result"))
			if not floor_result.get("sale"):
				raise AssertionError("Aprovação do piso de custo não reexecutou a venda pelo motor.")
		finally:
			frappe.db.set_single_value("Tecponto Settings", "discount_limit", previous_discount_limit)

		# Troca: a tentativa do atendente bate na faixa; a aprovação reaplica o valor sob o Gestor.
		frappe.set_user("Administrator")
		trade = frappe.get_doc(
			{
				"doctype": "Device Trade Evaluation",
				"customer": _get_or_create_demo_customer(),
				"device_type": "iPhone",
				"evaluated_device_desc": "Teste solicitação acima da tabela",
				"imei": f"TP-TRADE-{frappe.generate_hash(length=12)}",
				"table_min": 50,
				"table_max": 100,
				"destination": "Venda",
			}
		)
		trade.insert(ignore_permissions=True)
		frappe.set_user(attendant)
		trade_blocked = False
		try:
			set_tradein_approved_value(trade.name, 150)
		except frappe.ValidationError:
			trade_blocked = True
		if not trade_blocked:
			raise AssertionError("Atendente registrou valor acima da tabela sem solicitar aprovação.")
		frappe.db.commit()
		trade_request = create_request("tradein_over_max", trade.name, "Oferta excepcional para fechar a troca.", {"approved_value": 150})
		frappe.set_user(manager)
		approve_request(trade_request["name"])
		if flt(frappe.db.get_value("Device Trade Evaluation", trade.name, "approved_value")) != 150:
			raise AssertionError("Aprovação da troca não reaplicou o valor no motor.")

		# OS: a transição é executada pela role que o workflow exige, não por um bypass
		# do solicitante. O teste lê essa role do metadata em vez de duplicar o workflow.
		frappe.set_user(attendant)
		frappe.db.commit()
		move_request = create_request(
			"service_order_move",
			order_name,
			"Técnico precisa iniciar o diagnóstico desta OS.",
			{"target_state": "Em diagnóstico"},
		)
		workflow_approver = _find_or_create_user(move_request["approver_role"])
		# Restricted technicians can act only on their own OS. This mirrors the
		# production assignment that must exist before a technical transition.
		frappe.db.set_value("Service Order", order_name, "technician", workflow_approver, update_modified=False)
		frappe.set_user(workflow_approver)
		move_approved = approve_request(move_request["name"])
		if move_approved["status"] != "Aprovada" or frappe.db.get_value("Service Order", order_name, "workflow_state") != "Em diagnóstico":
			raise AssertionError("Aprovação da mudança de etapa não moveu a OS pelo workflow real.")

		# Transferência: o atendente prepara o mesmo Stock Entry, mas não o submete.
		demo_pos = _ensure_pos_demo_records()
		repair_warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
		commercial_warehouse = demo_pos["commercial_warehouse"]
		transfer_item = POS_BARCODE_ITEM
		commercial_before = _bin_qty(transfer_item, commercial_warehouse)
		repair_before = _bin_qty(transfer_item, repair_warehouse)
		frappe.set_user(attendant)
		transfer = create_stock_transfer(transfer_item, 1, commercial_warehouse, "")
		transfer_blocked = False
		try:
			submit_stock_transfer(transfer["item"]["name"])
		except frappe.PermissionError as error:
			transfer_blocked = "exige o Gestor" in str(error)
		if not transfer_blocked:
			raise AssertionError("Atendente submeteu transferência entre estoques sem aprovação.")
		frappe.db.commit()
		transfer_request = create_request(
			"stock_transfer",
			transfer["item"]["name"],
			"Reposição urgente de peça no Reparo.",
		)
		frappe.set_user(manager)
		approve_request(transfer_request["name"])
		if frappe.db.get_value("Stock Entry", transfer["item"]["name"], "docstatus") != 1:
			raise AssertionError("Aprovação da transferência não submeteu o Stock Entry.")
		if _bin_qty(transfer_item, commercial_warehouse) != commercial_before - 1 or _bin_qty(transfer_item, repair_warehouse) != repair_before + 1:
			raise AssertionError("Transferência aprovada não movimentou os dois depósitos corretamente.")

		# OS faturada: o mesmo workflow só segue quando o Gestor reexecuta o cancelamento.
		billed_order = _create_action_request_service_order(attendant)
		frappe.db.set_value("Service Order", billed_order, "sales_invoice", pos_result["sale"], update_modified=False)
		frappe.set_user(attendant)
		billed_cancel_blocked = False
		try:
			move_service_order(billed_order, "Cancelado")
		except frappe.PermissionError as error:
			billed_cancel_blocked = "OS faturada" in str(error)
		if not billed_cancel_blocked:
			raise AssertionError("Atendente cancelou OS faturada sem aprovação.")
		frappe.db.commit()
		billed_cancel_request = create_request(
			"billed_service_order_cancel",
			billed_order,
			"Cliente desistiu após o faturamento; solicitar cancelamento registrado.",
		)
		frappe.set_user(manager)
		desk_cancel_blocked_without_return = False
		try:
			move_service_order(billed_order, "Cancelado")
		except frappe.ValidationError:
			desk_cancel_blocked_without_return = True
		if not desk_cancel_blocked_without_return:
			raise AssertionError("Gestor cancelou OS faturada sem estornar a Sales Invoice.")
		approve_request(billed_cancel_request["name"])
		cancellation_request = frappe.get_doc("Tecponto Request", billed_cancel_request["name"])
		cancellation_result = frappe.parse_json(cancellation_request.execution_result or "{}")
		return_invoice = cancellation_result.get("return_invoice")
		if not return_invoice:
			raise AssertionError("Cancelamento faturado não criou a Sales Invoice Return obrigatória.")
		return_doc = frappe.get_doc("Sales Invoice", return_invoice)
		if return_doc.docstatus != 1 or not return_doc.is_return or return_doc.return_against != pos_result["sale"]:
			raise AssertionError("Estorno da OS faturada não ficou vinculado à nota original.")

		# Garantia-cortesia: a OS nasce normal; somente a decisao individual do Gestor
		# a converte em retrabalho gratuito, com a OS original revalidada pelo motor.
		frappe.set_user("Administrator")
		original_warranty_order = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order",
			original_warranty_order,
			{"workflow_state": "Entregue", "warranty_expiry": add_days(nowdate(), -1)},
			update_modified=False,
		)
		courtesy_target = _create_action_request_service_order(attendant)
		frappe.set_user(attendant)
		courtesy_request = create_request(
			"courtesy_warranty",
			courtesy_target,
			"Cliente solicitou cobertura excepcional apos a garantia contratual.",
			{"original_service_order": original_warranty_order},
		)
		frappe.set_user(manager)
		approve_request(courtesy_request["name"])
		courtesy_doc = frappe.get_doc("Service Order", courtesy_target)
		if not courtesy_doc.is_warranty or not courtesy_doc.courtesy_warranty or courtesy_doc.original_service_order != original_warranty_order:
			raise AssertionError("Aprovacao nao reexecutou a garantia-cortesia sob as regras da OS.")
		if frappe.db.get_value("Service Order", billed_order, "workflow_state") != "Cancelado":
			raise AssertionError("Aprovação não cancelou a OS faturada pelo workflow real.")

		return {
			"status": "ok",
			"created_pending": created["name"],
			"approved": approved["name"],
			"rejected": rejected["name"],
			"expired": expired["name"],
			"expired_count": expired_count,
			"self_approval_blocked": self_approval_blocked,
			"pos_discount": {"request": pos_request["name"], "sale": pos_result["sale"], "executed": True},
			"pos_price_floor": {"request": floor_request["name"], "sale": floor_result["sale"], "executed": True},
			"tradein_over_max": {"request": trade_request["name"], "evaluation": trade.name, "executed": True},
			"service_order_move": {"request": move_request["name"], "state": "Em diagnóstico", "executed": True},
			"stock_transfer": {"request": transfer_request["name"], "stock_entry": transfer["item"]["name"], "executed": True},
			"billed_service_order_cancel": {
				"request": billed_cancel_request["name"],
				"service_order": billed_order,
				"return_invoice": return_invoice,
				"desk_blocked_without_return": desk_cancel_blocked_without_return,
				"executed": True,
			},
			"courtesy_warranty": {"request": courtesy_request["name"], "service_order": courtesy_target, "executed": True},
		}
	finally:
		frappe.set_user(previous_user)


def run_pos_sale_checks() -> dict:
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		manager = _find_or_create_user("Tecponto Gestor")
		customer = _get_or_create_demo_customer()
		demo = _ensure_pos_demo_records()
		frappe.db.commit()

		commercial = demo["commercial_warehouse"]
		repair = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
		clearing = frappe.db.get_single_value("Tecponto Settings", "acquirer_clearing_account")
		if not repair or not clearing:
			raise AssertionError("Estoques e conta transitória precisam estar configurados para testar o PDV.")

		qty_before = _bin_qty(POS_BARCODE_ITEM, commercial)
		repair_before = _bin_qty(POS_BARCODE_ITEM, repair)
		clearing_before = _gl_balance(clearing)
		invoice_count_before = frappe.db.count("Sales Invoice", {"docstatus": 1})
		key = f"tp-pos-test-{frappe.generate_hash(length=20)}"
		payload = {
			"idempotency_key": key,
			"customer": customer,
			"items": [{"item_code": POS_BARCODE_ITEM, "qty": 1}],
			"discount_amount": 0,
			"payments": [
				{"mode_of_payment": "Pix", "amount": 35.50, "installments": 1},
				{"mode_of_payment": "Débito", "amount": 44.40, "installments": 1},
			],
		}

		frappe.set_user(attendant)
		if "Sales User" in frappe.get_roles(attendant):
			raise AssertionError("Atendente do endpoint cirúrgico não pode receber Sales User.")
		result = pos_create_sale(payload)
		frappe.db.commit()

		qty_after = _bin_qty(POS_BARCODE_ITEM, commercial)
		repair_after = _bin_qty(POS_BARCODE_ITEM, repair)
		clearing_after = _gl_balance(clearing)
		invoice_count_after = frappe.db.count("Sales Invoice", {"docstatus": 1})
		if flt(qty_before - qty_after, 3) != 1:
			raise AssertionError(f"Venda deveria baixar 1 unidade do Comercial: {qty_before} -> {qty_after}.")
		if repair_before != repair_after:
			raise AssertionError("Venda do PDV alterou indevidamente o estoque de Reparo.")
		if flt(clearing_after - clearing_before, 2) != 44.40:
			raise AssertionError(
				f"Cartão deveria aumentar Recebíveis de Cartão em 44,40: {clearing_before} -> {clearing_after}."
			)
		if invoice_count_after != invoice_count_before + 1:
			raise AssertionError("Finalização deveria criar exatamente uma Sales Invoice submetida.")
		if result["receipt"]["format"] != POS_RECEIPT_PRINT_FORMAT or not frappe.db.exists(
			"Print Format", POS_RECEIPT_PRINT_FORMAT
		):
			raise AssertionError("Cupom do PDV não foi gerado no formato Tecponto.")
		pos_download_receipt(result["sale"])
		receipt_bytes = frappe.local.response.get("filecontent") or b""
		if not receipt_bytes.startswith(b"%PDF"):
			raise AssertionError("Endpoint cirúrgico do cupom não renderizou um PDF.")

		request_doc = frappe.get_doc("Tecponto POS Sale Request", key)
		payment_metadata = json.loads(request_doc.payment_metadata)
		card_metadata = next(row for row in payment_metadata if row["mode_of_payment"] == "Débito")
		if card_metadata["account"] != clearing or flt(card_metadata["fee_pct"], 2) != 1.5:
			raise AssertionError("Taxa ou conta transitória do cartão não respeitou o Tecponto Settings.")
		if int(card_metadata["settlement_days"]) != 1:
			raise AssertionError("Prazo D+1 do débito não foi registrado na venda.")

		leaks = contains_sensitive_field(result, forbidden_values=set(demo["valuation_rates"]))
		if leaks:
			raise AssertionError(f"Custo vazou na resposta do endpoint do PDV: {', '.join(leaks)}")

		replay = pos_create_sale(payload)
		frappe.db.commit()
		if replay["sale"] != result["sale"] or not replay["idempotent_replay"]:
			raise AssertionError("Reenvio idempotente não retornou a mesma venda.")
		invoice_count_after_replay = frappe.db.count("Sales Invoice", {"docstatus": 1})
		if invoice_count_after_replay != invoice_count_after:
			raise AssertionError("Reenvio idempotente criou uma segunda nota.")
		if _bin_qty(POS_BARCODE_ITEM, commercial) != qty_after or _gl_balance(clearing) != clearing_after:
			raise AssertionError("Reenvio idempotente repetiu estoque ou lançamento contábil.")

		frappe.set_user(technician)
		technician_blocked = False
		try:
			pos_create_sale({**payload, "idempotency_key": f"tp-pos-tech-{frappe.generate_hash(length=20)}"})
		except frappe.PermissionError:
			technician_blocked = True
		if not technician_blocked:
			raise AssertionError("Técnico conseguiu finalizar venda pelo endpoint cirúrgico.")

		low_total = 4.90
		low_price_payload = {
			"customer": customer,
			"items": [{"item_code": POS_BARCODE_ITEM, "qty": 1}],
			"discount_amount": 75.00,
			"payments": [{"mode_of_payment": "Pix", "amount": low_total, "installments": 1}],
		}
		frappe.set_user(attendant)
		attendant_floor_blocked = False
		floor_error = ""
		try:
			pos_create_sale(
				{**low_price_payload, "idempotency_key": f"tp-pos-floor-att-{frappe.generate_hash(length=20)}"}
			)
		except frappe.ValidationError as exc:
			attendant_floor_blocked = True
			floor_error = str(exc)
		if not attendant_floor_blocked:
			raise AssertionError("Atendente conseguiu vender abaixo do custo.")
		if "piso comercial" not in floor_error.lower():
			raise AssertionError("Bloqueio de piso nao retornou a mensagem neutra esperada.")
		error_leaks = contains_sensitive_field({"message": floor_error}, forbidden_values=set(demo["valuation_rates"]))
		if error_leaks:
			raise AssertionError(f"Custo vazou na mensagem de erro do piso de preco: {', '.join(error_leaks)}")

		manager_qty_before = _bin_qty(POS_BARCODE_ITEM, commercial)
		frappe.set_user(manager)
		manager_result = pos_create_sale(
			{**low_price_payload, "idempotency_key": f"tp-pos-floor-gest-{frappe.generate_hash(length=20)}"}
		)
		frappe.db.commit()
		manager_qty_after = _bin_qty(POS_BARCODE_ITEM, commercial)
		if flt(manager_qty_before - manager_qty_after, 3) != 1:
			raise AssertionError("Override do Gestor não concluiu a venda abaixo do custo.")

		return {
			"status": "ok",
			"sale": {
				"name": result["sale"],
				"commercial_qty": {"before": qty_before, "after": qty_after},
				"repair_qty": {"before": repair_before, "after": repair_after},
				"card_receivables": {"before": clearing_before, "after": clearing_after, "delta": 44.40},
				"payments": result["payments"],
				"card_configuration": {
					"account": card_metadata["account"],
					"fee_pct": card_metadata["fee_pct"],
					"fee_amount": card_metadata["fee_amount"],
					"settlement_days": card_metadata["settlement_days"],
					"expected_settlement_date": card_metadata["expected_settlement_date"],
				},
				"receipt": result["receipt"],
			},
			"idempotency": {
				"first_sale": result["sale"],
				"replayed_sale": replay["sale"],
				"invoice_count_before_replay": invoice_count_after,
				"invoice_count_after_replay": invoice_count_after_replay,
			},
			"permissions": {
				"attendant": attendant,
				"attendant_has_sales_user": "Sales User" in frappe.get_roles(attendant),
				"technician": technician,
				"technician_blocked": technician_blocked,
			},
			"price_floor": {
				"attendant_blocked": attendant_floor_blocked,
				"error_sanitized": not error_leaks,
				"manager_sale": manager_result["sale"],
				"manager_qty": {"before": manager_qty_before, "after": manager_qty_after},
			},
			"sensitive_guard": {"checked_response": result["sale"], "leaked_fields": leaks},
		}
	finally:
		frappe.set_user(previous_user)


def run_pos_barcode_label_checks() -> dict:
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		demo = _ensure_pos_demo_records()
		item_code = _create_unlabelled_pos_item()
		valuation_rate = 5.55
		_ensure_pos_demo_stock(item_code, demo["commercial_warehouse"], valuation_rate)
		frappe.db.commit()

		if frappe.db.exists("Item Barcode", {"parent": item_code}):
			raise AssertionError("Item de teste deveria começar sem código de barras.")

		frappe.set_user(attendant)
		generated = pos_generate_item_barcode(item_code)
		frappe.db.commit()
		barcode_row = frappe.db.get_value(
			"Item Barcode",
			{"parent": item_code},
			["barcode", BARCODE_SYMBOLOGY_FIELD, "uom"],
			as_dict=True,
		)
		if not generated["created"] or not barcode_row or barcode_row.barcode != generated["barcode"]:
			raise AssertionError("Código gerado não foi salvo na child table nativa Item Barcode.")
		if (
			not barcode_row.barcode.startswith("TPC")
			or not barcode_row.barcode[3:].isdigit()
			or barcode_row.get(BARCODE_SYMBOLOGY_FIELD) != BARCODE_SYMBOLOGY_CODE128
		):
			raise AssertionError("Código interno não foi salvo como Code-128 Tecponto.")

		frappe.local.response.filecontent = None
		pos_download_barcode_label(item_code)
		label_pdf = frappe.local.response.get("filecontent") or b""
		if not label_pdf.startswith(b"%PDF") or not frappe.db.exists(
			"Print Format", POS_BARCODE_LABEL_PRINT_FORMAT
		):
			raise AssertionError("Etiqueta de barcode não renderizou como PDF.")
		page = PdfReader(BytesIO(label_pdf)).pages[0]
		width_mm = round(float(page.mediabox.width) * 25.4 / 72, 1)
		height_mm = round(float(page.mediabox.height) * 25.4 / 72, 1)
		if not (49 <= width_mm <= 51 and 29 <= height_mm <= 31):
			raise AssertionError(f"Etiqueta deveria medir 50x30 mm; recebeu {width_mm}x{height_mm} mm.")

		scan_result = search_pos_items(barcode=barcode_row.barcode, limit=1)
		found = next((row for row in scan_result["items"] if row["item_code"] == item_code), None)
		if not found:
			raise AssertionError("Bipe simulado não encontrou o item recém-etiquetado.")

		stock_result = list_stock_items(query=item_code, limit=5)
		stock_row = next((row for row in stock_result["items"] if row["item_code"] == item_code), None)
		if not stock_row or stock_row["barcode"] != barcode_row.barcode:
			raise AssertionError("Tela de estoque não recebeu o barcode nativo recém-gerado.")

		leaks = contains_sensitive_field(
			{"generated": generated, "scan": scan_result, "stock": stock_result},
			forbidden_values={valuation_rate},
		)
		if leaks:
			raise AssertionError(f"Custo vazou no fluxo de etiqueta: {', '.join(leaks)}")

		factory_before = frappe.get_all(
			"Item Barcode", filters={"parent": POS_BARCODE_ITEM}, fields=["barcode", "barcode_type", "uom"], order_by="idx"
		)
		factory_result = pos_generate_item_barcode(POS_BARCODE_ITEM)
		factory_after = frappe.get_all(
			"Item Barcode", filters={"parent": POS_BARCODE_ITEM}, fields=["barcode", "barcode_type", "uom"], order_by="idx"
		)
		if factory_result["created"] or factory_before != factory_after:
			raise AssertionError("Item com barcode de fábrica foi sobrescrito.")

		frappe.set_user(technician)
		technician_blocked = False
		try:
			pos_generate_item_barcode(item_code)
		except frappe.PermissionError:
			technician_blocked = True
		if not technician_blocked:
			raise AssertionError("Técnico conseguiu gerar etiqueta pelo endpoint do balcão.")

		return {
			"status": "ok",
			"generated": {
				"item_code": item_code,
				"barcode": barcode_row.barcode,
				"barcode_type": barcode_row.barcode_type,
				"saved_in": "Item Barcode",
			},
			"label": {
				"format": POS_BARCODE_LABEL_PRINT_FORMAT,
				"pdf_header": label_pdf[:4].decode(),
				"bytes": len(label_pdf),
				"size_mm": [width_mm, height_mm],
			},
			"scan": {
				"simulated_input": barcode_row.barcode,
				"found_item": found["item_code"],
				"available_qty": found["available_qty"],
			},
			"factory_barcode": {
				"item_code": POS_BARCODE_ITEM,
				"before": factory_before,
				"after": factory_after,
				"created": factory_result["created"],
			},
			"permissions": {"technician_blocked": technician_blocked},
			"sensitive_guard": {"leaked_fields": leaks},
		}
	finally:
		frappe.set_user(previous_user)


def run_pos_retail_barcode_catalog_checks() -> dict:
	"""Audit matrix for factory/internal codes, duplicate protection and stock receipt."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		ensure_item_barcode_source_field()
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		stock_uom = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
		suffix = frappe.generate_hash(length=7).upper()
		factory_barcode = f"000000{int(suffix, 16) % 10_000_000:07d}"
		factory_code = f"TP-BAR-FAB-{suffix}"
		internal_code = f"TP-BAR-INT-{suffix}"

		frappe.set_user(attendant)
		catalog_registration_blocked = False
		try:
			pos_register_retail_product({})
		except frappe.PermissionError:
			catalog_registration_blocked = True
		if not catalog_registration_blocked:
			raise AssertionError("Atendente ainda consegue cadastrar produto comercial pelo endpoint legado.")

		frappe.set_user(manager)
		factory = pos_register_retail_product(
			{
				"barcode": factory_barcode,
				"barcode_source": BARCODE_SOURCE_MANUFACTURER,
				"item_code": factory_code,
				"item_group": "Cabos",
				"item_name": f"Cabo de fábrica {suffix}",
				"selling_rate": 39.90,
				"stock_uom": stock_uom,
			}
		)
		factory_row = frappe.db.get_value(
			"Item Barcode",
			{"parent": factory_code, "barcode": factory_barcode},
			["barcode", BARCODE_SYMBOLOGY_FIELD, BARCODE_SOURCE_FIELD],
			as_dict=True,
		)
		if not factory_row or factory_row.get(BARCODE_SOURCE_FIELD) != BARCODE_SOURCE_MANUFACTURER:
			raise AssertionError("Código do fabricante não recebeu origem correta.")

		lookup = pos_lookup_retail_barcode(f"  {factory_barcode}  ")
		if lookup["state"] != "found" or lookup["item"]["item_code"] != factory_code:
			raise AssertionError("Leitura com zeros à esquerda não localizou o produto de fábrica.")

		duplicate_blocked = False
		try:
			pos_register_retail_product(
				{
					"barcode": factory_barcode,
					"barcode_source": BARCODE_SOURCE_MANUFACTURER,
					"item_code": f"TP-BAR-DUP-{suffix}",
					"item_group": "Cabos",
					"item_name": f"Duplicado {suffix}",
					"selling_rate": 19.90,
					"stock_uom": stock_uom,
				}
			)
		except frappe.ValidationError as error:
			duplicate_blocked = "Código já cadastrado" in str(error)
		if not duplicate_blocked:
			raise AssertionError("Código repetido não foi bloqueado com mensagem orientada.")

		internal = pos_register_retail_product(
			{
				"barcode_source": BARCODE_SOURCE_INTERNAL,
				"item_code": internal_code,
				"item_group": "Cabos",
				"item_name": f"Acessório sem código {suffix}",
				"selling_rate": 29.90,
				"stock_uom": stock_uom,
			}
		)
		internal_row = frappe.db.get_value(
			"Item Barcode",
			{"parent": internal_code},
			["barcode", BARCODE_SYMBOLOGY_FIELD, BARCODE_SOURCE_FIELD],
			as_dict=True,
		)
		if (
			not internal_row
			or not internal_row.barcode.startswith("TPC")
			or internal_row.get(BARCODE_SYMBOLOGY_FIELD) != BARCODE_SYMBOLOGY_CODE128
			or internal_row.get(BARCODE_SOURCE_FIELD) != BARCODE_SOURCE_INTERNAL
		):
			raise AssertionError(f"Código interno não foi criado como Code-128 Tecponto: {internal_row}")

		frappe.set_user(manager)
		warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
		before_qty = _bin_qty(factory_code, warehouse)
		receipt = pos_receive_retail_stock({"item_code": factory_code, "qty": 12, "incoming_rate": 8.5})
		if receipt["qty_before"] != before_qty or receipt["qty_after"] != before_qty + 12:
			raise AssertionError("Entrada não atualizou o estoque Comercial pelo documento nativo.")
		if frappe.db.get_value("Stock Entry", receipt["stock_entry"], "docstatus") != 1:
			raise AssertionError("Entrada não gerou Stock Entry submetido.")

		frappe.set_user(attendant)
		receipt_blocked = False
		try:
			pos_receive_retail_stock({"item_code": factory_code, "qty": 1, "incoming_rate": 8.5})
		except frappe.PermissionError:
			receipt_blocked = True
		if not receipt_blocked:
			raise AssertionError("Atendente conseguiu registrar entrada com custo.")

		scan = search_pos_items(barcode=internal["barcode"], limit=1)
		if not any(row["item_code"] == internal_code for row in scan["items"]):
			raise AssertionError("Código interno não foi localizado pelo PDV.")
		leaks = contains_sensitive_field(
			{"factory": factory, "internal": internal, "lookup": lookup, "receipt": receipt, "scan": scan},
			forbidden_values={8.5},
		)
		if leaks:
			raise AssertionError(f"Custo vazou no fluxo de catálogo: {', '.join(leaks)}")

		return {
			"status": "ok",
			"catalog_registration_blocked_for_attendant": catalog_registration_blocked,
			"factory": {"barcode": factory_barcode, "source": factory_row.get(BARCODE_SOURCE_FIELD)},
			"internal": {"barcode": internal_row.barcode, "type": internal_row.get(BARCODE_SYMBOLOGY_FIELD)},
			"duplicate_blocked": duplicate_blocked,
			"receipt": {"stock_entry": receipt["stock_entry"], "before": before_qty, "after": receipt["qty_after"]},
			"attendant_receipt_blocked": receipt_blocked,
			"sensitive_guard": {"leaked_fields": leaks},
		}
	finally:
		frappe.set_user(previous_user)


def save_pos_barcode_label_artifact() -> dict:
	previous_user = frappe.session.user
	try:
		frappe.set_user(TEST_USERS["Tecponto Atendente"][0])
		pos_download_barcode_label(POS_NAME_ITEM)
		content = frappe.local.response.get("filecontent") or b""
		output = Path(frappe.get_app_path("tecponto_app")).parent / "artifacts" / "bloco_3_5_pdv_3"
		output.mkdir(parents=True, exist_ok=True)
		pdf_path = output / "04-etiqueta-barcode-TP-PDV-NOME.pdf"
		pdf_path.write_bytes(content)
		return {"path": str(pdf_path), "bytes": len(content), "pdf_header": content[:4].decode()}
	finally:
		frappe.set_user(previous_user)


def _create_unlabelled_pos_item() -> str:
	suffix = frappe.generate_hash(length=6).upper()
	item_code = f"TP-PDV-ETIQ-{suffix}"
	stock_uom = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": f"Acessório a granel {suffix}",
			"item_group": "Cabos",
			"stock_uom": stock_uom,
			"is_stock_item": 1,
			"is_sales_item": 1,
			"disabled": 0,
			"standard_rate": 29.90,
		}
	)
	item.insert(ignore_permissions=True)
	return item.name


def _bin_qty(item_code: str, warehouse: str) -> float:
	return flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"), 3)


def _gl_balance(account: str) -> float:
	return flt(
		frappe.db.sql(
			"""
			select coalesce(sum(debit - credit), 0)
			from `tabGL Entry`
			where account = %s and is_cancelled = 0
			""",
			account,
		)[0][0],
		2,
	)


def ensure_pos_lookup_demo_data() -> dict:
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		result = _ensure_pos_demo_records()
		frappe.db.commit()
		return {"status": "ok", **result}
	finally:
		frappe.set_user(previous_user)


def _find_or_create_user(role: str) -> str:
	email, full_name = TEST_USERS[role]
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": full_name.split()[0],
				"last_name": " ".join(full_name.split()[1:]),
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)
	for frontend_role in FRONTEND_ROLES:
		if frontend_role != role:
			frappe.db.delete(
				"Has Role",
				{
					"parenttype": "User",
					"parent": user.name,
					"role": frontend_role,
				},
			)
	if role not in {entry.role for entry in user.roles}:
		user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
	frappe.db.commit()
	return user.name


def _find_or_create_multi_role_user() -> str:
	from tecponto_app.tecponto import user_access

	previous_user = frappe.session.user
	email = "front-multipapel@tecponto.local"
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Operador",
				"last_name": "Multipapel",
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)

	for frontend_role in FRONTEND_ROLES:
		frappe.db.delete(
			"Has Role",
			{
				"parenttype": "User",
				"parent": user.name,
				"role": frontend_role,
			},
		)
	try:
		frappe.set_user(user_access.get_owner_user())
		user.reload()
		assigned_roles = {entry.role for entry in user.roles}
		for role in ("Tecponto Atendente", "Tecponto Gestor"):
			if role not in assigned_roles:
				user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
		frappe.db.commit()
		return user.name
	finally:
		frappe.set_user(previous_user)


def _find_or_create_attendant_technician_user() -> str:
	"""A real multi-role account used to prove the backend keeps the role union."""
	from tecponto_app.tecponto import user_access

	previous_user = frappe.session.user
	email = "front-atendente-tecnico@tecponto.local"
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Atendente",
				"last_name": "Técnico",
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		)
		user.insert(ignore_permissions=True)

	for frontend_role in FRONTEND_ROLES:
		frappe.db.delete(
			"Has Role",
			{
				"parenttype": "User",
				"parent": user.name,
				"role": frontend_role,
			},
		)
	user.reload()
	try:
		# Fixture setup uses the protected owner path too; a transient technician
		# session must not bypass the rule that a person only grants roles it has.
		frappe.set_user(user_access.get_owner_user())
		for role in ("Tecponto Atendente", "Tecponto Tecnico"):
			user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
		frappe.db.commit()
		return user.name
	finally:
		frappe.set_user(previous_user)


def _get_or_create_demo_customer() -> str:
	customer_name = "Cliente Demo Front 3.1b"
	existing = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
	if existing:
		return existing

	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": customer_name,
			"customer_type": "Individual",
			"mobile_no": "(11) 90000-3101",
			"custom_cpf": "12345678909",
			"email_id": "cliente.demo.31b@tecponto.local",
		}
	)
	customer.insert(ignore_permissions=True)
	return customer.name


def _get_or_create_demo_device(customer: str) -> str:
	existing = frappe.db.get_value(
		"Customer Device",
		{"customer": customer, "imei_serial": "359999310000001"},
		"name",
	)
	if existing:
		return existing

	device = frappe.get_doc(
		{
			"doctype": "Customer Device",
			"customer": customer,
			"brand": "Apple",
			"model": "iPhone 11",
			"color": "Preto",
			"imei_serial": "359999310000001",
			"capacity": "128GB",
			"general_state": "Tela com riscos leves; carcaça sem amassados.",
			"registration_date": add_days(now_datetime().date(), 0),
		}
	)
	device.insert(ignore_permissions=True)
	return device.name


def _get_demo_item(is_stock_item: int) -> str:
	# A full CI run starts from an empty ERPNext site. Keep the service-order
	# fixtures self-contained instead of relying on locally seeded Items.
	item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
	stock_uom = frappe.db.get_value("UOM", {"enabled": 1}, "name") or "Nos"
	item_code = "TP-CI-PECA" if is_stock_item else "TP-CI-SERVICO"
	item_name = "Peça de teste CI" if is_stock_item else "Serviço de teste CI"
	if not frappe.db.exists("Item", item_code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_name,
				"item_group": item_group,
				"stock_uom": stock_uom,
				"is_stock_item": is_stock_item,
				"disabled": 0,
			}
		).insert(ignore_permissions=True)
	if is_stock_item:
		warehouse = _get_demo_warehouse()
		if not warehouse:
			raise AssertionError("Não há depósito para criar o estoque de teste da OS.")
		_ensure_pos_demo_stock(item_code, warehouse, valuation_rate=10)
	return item_code


def _get_demo_warehouse() -> str | None:
	reparo = frappe.get_all(
		"Warehouse",
		filters={"disabled": 0, "is_group": 0},
		or_filters={"warehouse_name": ["like", "%Reparo%"], "name": ["like", "%Reparo%"]},
		pluck="name",
		limit_page_length=1,
	)
	if reparo:
		return reparo[0]
	return frappe.db.get_value("Warehouse", {"disabled": 0, "is_group": 0}, "name")


def _upsert_demo_service_order(
	*,
	demo: dict,
	customer: str,
	device: str,
	service_item: str,
	part_item: str,
	warehouse: str | None,
	attendant: str,
	legacy_fixture: bool = True,
) -> str:
	marker = f"{DETAIL_DEMO_MARKER}: {demo['slug']}"
	existing = frappe.db.get_value("Service Order", {"internal_notes": marker}, "name")
	if existing:
		# Demo fixtures may have ended in terminal workflow states during prior checks.
		frappe.db.set_value("Service Order", existing, "workflow_state", "Entrada criada", update_modified=False)
		doc = frappe.get_doc("Service Order", existing)
	else:
		doc = frappe.new_doc("Service Order")
		doc.naming_series = "OS-.YYYY.-.#####"

	doc.customer = customer
	doc.customer_device = device
	doc.entry_date = now_datetime()
	doc.attendant = attendant
	doc.technician = None
	doc.priority = "Normal"
	doc.workflow_state = "Entrada criada"
	doc.reported_defect = demo["reported_defect"]
	doc.physical_state = "Riscos leves na tela; aparelho liga normalmente."
	doc.accessories_received = "Aparelho sem carregador."
	doc.entry_photos = "/files/demo-front-31b.jpg"
	doc.entry_signature = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAghX7JQAAAABJRU5ErkJggg=="
	doc.problem_found = demo["problem_found"]
	doc.diagnosis_date = now_datetime().date() if demo["problem_found"] else None
	doc.approval_status = "Pendente"
	doc.approval_deadline = add_days(now_datetime(), 2)
	doc.approval_channel = None
	doc.approved_by_attendant = None
	doc.approval_date = None
	doc.quote_locked = 0
	doc.budget_version = 1
	doc.internal_notes = marker

	doc.set("services", [])
	doc.append(
		"services",
		{
			"item_code": service_item,
			"description": "Mão de obra - troca de tela",
			"qty": 1,
			"rate": 120,
		},
	)
	doc.set("parts", [])
	doc.append(
		"parts",
		{
			"item_code": part_item,
			"description": "Tela compatível",
			"qty": 1,
			"warehouse": warehouse,
			"rate": 280,
		},
	)
	doc.save(ignore_permissions=True)
	if legacy_fixture:
		# Demo records represent OS issued before the public-link rollout. They keep
		# exercising old workflow paths without weakening the rule for new OS.
		frappe.db.set_value("Service Order", doc.name, "link_acceptance_required", 0, update_modified=False)

	values = {
		"workflow_state": demo["state"],
		"approval_status": demo["approval_status"],
		"approval_deadline": add_days(now_datetime(), 2),
		"quote_locked": 1 if demo["state"] in {"Pronto para retirada"} else 0,
	}
	if demo["approval_status"] == "Aprovado":
		values.update(
			{
				"approval_channel": "Presencial",
				"approved_by_attendant": attendant,
				"approval_date": now_datetime(),
			}
		)
	frappe.db.set_value("Service Order", doc.name, values, update_modified=True)
	return doc.name


def _create_action_request_service_order(attendant: str) -> str:
	"""Create an isolated OS because the visual demo records can be in terminal workflow states."""
	customer = _get_or_create_demo_customer()
	device = _get_or_create_demo_device(customer)
	demo = {
		"slug": f"action-request-{frappe.generate_hash(length=8)}",
		"state": "Entrada criada",
		"approval_status": "Pendente",
		"reported_defect": "OS isolada para validar solicitações de aprovação.",
		"problem_found": None,
	}
	return _upsert_demo_service_order(
		demo=demo,
		customer=customer,
		device=device,
		service_item=_get_demo_item(is_stock_item=0),
		part_item=_get_demo_item(is_stock_item=1),
		warehouse=_get_demo_warehouse(),
		attendant=attendant,
	)


def _check_role_panels(users: dict[str, str]) -> list[dict]:
	results = []
	for role, user in users.items():
		frappe.set_user(user)
		boot = get_boot()
		expected = resolve_panel([role])
		actual = boot["user"]["panel"]
		if actual != expected["panel"]:
			raise AssertionError(f"{user} abriu painel {actual}, esperado {expected['panel']}")
		results.append(
			{
				"user": user,
				"role": role,
				"panel": actual,
				"label": boot["user"]["role_label"],
			}
		)
	return results


def _check_multi_role_union(attendant: str) -> dict:
	"""The front shows a union; the server remains the authorization authority."""
	multi_role_user = _find_or_create_multi_role_user()
	frappe.set_user(multi_role_user)
	boot = get_boot()
	available_panels = [
		entry["panel"]
		for entry in boot["panels"]
		if entry["role"] in {"Tecponto Atendente", "Tecponto Gestor"}
	]
	if set(available_panels) != {"atendente", "gestor"}:
		raise AssertionError(f"Usuário multipapel recebeu papéis incorretos: {available_panels}")

	# The combined account can use counter and manager APIs through real roles.
	attendant_api_payload = search_pos_items(query="Película 3D", limit=1)
	if not attendant_api_payload["items"]:
		raise AssertionError("Usuário Atendente+Gestor perdeu acesso à API de balcão.")
	manager_reference = save_catalog_reference(
		"category",
		{"value": f"Multi papel {frappe.generate_hash(length=8)}", "active": True},
	)["item"]

	frappe.set_user(attendant)
	manager_api_blocked = False
	try:
		save_catalog_reference("category", {"name": manager_reference["name"], "value": "Nao deve editar"})
	except frappe.PermissionError:
		manager_api_blocked = True
	if not manager_api_blocked:
		raise AssertionError("Atendente sem papel Gestor conseguiu editar o catálogo.")

	leaks = contains_sensitive_field(
		{
			"unified_roles": {"boot": boot, "manager_reference": manager_reference},
			"attendant_api": attendant_api_payload,
		}
	)
	if leaks:
		raise AssertionError(f"Campos sensíveis vazaram na visão unificada: {', '.join(leaks)}")

	return {
		"user": multi_role_user,
		"roles": ["Tecponto Atendente", "Tecponto Gestor"],
		"available_panels": available_panels,
		"unified_visual_contract": "front_unifies_panels_without_changing_roles",
		"attendant_api_for_multi_role": "allowed",
		"attendant_only_manager_api": "blocked_403",
		"sensitive_guard": {"leaked_fields": leaks},
	}


def _check_service_order_api(user: str) -> dict:
	frappe.set_user(user)
	total_service_orders = frappe.db.count("Service Order")
	payload = list_service_orders(limit=5)
	if total_service_orders and not payload["items"]:
		raise AssertionError("A API tipada não retornou nenhuma OS apesar de existirem OS no banco.")

	return {
		"user": user,
		"database_count": total_service_orders,
		"returned_count": payload["count"],
		"fields": payload["fields"],
		"first_order": payload["items"][0]["name"] if payload["items"] else None,
	}


def _check_service_order_detail_api(user: str) -> dict:
	frappe.set_user(user)
	candidates = list_service_orders(limit=20)["items"]
	if not candidates:
		return {"user": user, "checked": False, "reason": "sem OS para detalhar"}

	details = []
	for candidate in candidates[:3]:
		payload = get_service_order_detail(candidate["name"])
		leaks = contains_sensitive_field(payload)
		if leaks:
			raise AssertionError(f"Campos sensíveis vazaram no detalhe da OS: {', '.join(leaks)}")
		details.append(
			{
				"name": payload["name"],
				"state": payload["workflow_state"],
				"actions": [action["action"] for action in payload["workflow_actions"]],
				"prints": [link["label"] for link in payload["print_links"]],
			}
		)

	return {"user": user, "checked": True, "details": details}


def _check_customer_device_search(user: str | None = None) -> dict:
	"""A check-in search must filter by the selected customer before limiting rows."""
	user = user or _find_or_create_user("Tecponto Atendente")
	frappe.set_user(user)
	customer = _get_or_create_demo_customer()
	device = _get_or_create_demo_device(customer)
	items = list_customer_devices(query="359999310000001", customer=customer, limit=8)["items"]
	if device not in {item["name"] for item in items}:
		raise AssertionError("Busca de aparelho do cliente nÃ£o retornou o aparelho cadastrado.")
	if any(item["customer"] != customer for item in items):
		raise AssertionError("Busca de aparelho retornou dispositivo de outro cliente.")

	wrong_customer = list_customer_devices(query="359999310000001", customer="Customer inexistente", limit=8)["items"]
	if wrong_customer:
		raise AssertionError("Filtro de cliente foi ignorado na busca de aparelhos.")

	return {"customer": customer, "device": device, "returned": len(items), "server_filtered": True}


def _check_attendant_navigation_apis(user: str) -> dict:
	frappe.set_user(user)
	payload = {
		"customers": search_customers(limit=5),
		"devices": list_customer_devices(limit=5),
		"trade_evaluations": list_trade_evaluations(limit=5),
		"stock_items": list_stock_items(limit=5, scope="repair-parts"),
		"sales": list_sales(limit=5),
	}
	leaks = contains_sensitive_field(payload)
	if leaks:
		raise AssertionError(f"Campos sensíveis vazaram nas APIs de navegação: {', '.join(leaks)}")

	return {
		"user": user,
		"customers": payload["customers"]["count"],
		"devices": payload["devices"]["count"],
		"trade_evaluations": payload["trade_evaluations"]["count"],
		"stock_items": payload["stock_items"]["count"],
		"sales": payload["sales"]["count"],
	}


def _check_dashboard_metrics(user: str) -> dict:
	frappe.set_user(user)
	payload = get_dashboard_metrics()
	leaks = contains_sensitive_field(payload)
	if leaks:
		raise AssertionError(f"Campos sensíveis vazaram nas métricas do painel: {', '.join(leaks)}")

	tickets = payload["sales_tickets"]
	if set(tickets) != {"retail", "service_order"}:
		raise AssertionError("Metricas de ticket nao foram separadas por balcao e OS.")
	for ticket in tickets.values():
		if not {"count", "total", "average"}.issubset(ticket):
			raise AssertionError("Ticket medio nao trouxe contagem, total e media.")

	service_orders = payload["service_orders"]
	if not {
		"awaiting_approval",
		"ready_for_pickup",
		"waiting_part",
	}.issubset(service_orders):
		raise AssertionError("Métricas de OS não trouxeram os filtros esperados por status.")

	return {
		"user": user,
		"sales_today_total": payload["sales_today_total"],
		"awaiting_approval": service_orders["awaiting_approval"],
		"ready_for_pickup": service_orders["ready_for_pickup"],
		"waiting_part": service_orders["waiting_part"],
	}


def _check_sensitive_guard(user: str) -> dict:
	frappe.set_user(user)
	payload = {
		"boot": get_boot(),
		"metrics": get_dashboard_metrics(),
		"service_orders": list_service_orders(limit=20),
		"daily_actions": list_daily_actions("tecnico"),
		"agenda_calendar": list_agenda_calendar("tecnico", str(nowdate()), str(add_days(nowdate(), 7))),
		"customers": search_customers(limit=5),
		"devices": list_customer_devices(limit=5),
		"stock_items": list_stock_items(limit=5, scope="repair-parts"),
	}
	leaks = contains_sensitive_field(payload)
	if leaks:
		raise AssertionError(f"Campos sensíveis vazaram para Técnico: {', '.join(leaks)}")

	return {
		"user": user,
		"checked_payloads": [
			"get_boot",
		"get_dashboard_metrics",
		"list_service_orders",
		"list_daily_actions",
		"list_agenda_calendar",
		"search_customers",
		"list_customer_devices",
		"list_stock_items",
		],
		"leaked_fields": leaks,
	}


def run_technician_scope_checks() -> dict:
	"""Prove technical-only reads are scoped, while accumulated roles stay additive."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		manager = _find_or_create_user("Tecponto Gestor")
		own_order = _create_action_request_service_order(attendant)
		other_order = _create_action_request_service_order(attendant)
		own_customer, own_device, own_label, own_imei = _create_technician_scope_customer_device("próprio")
		other_customer, other_device, other_label, other_imei = _create_technician_scope_customer_device("alheio")
		frappe.db.set_value(
			"Service Order",
			own_order,
			{"technician": technician, "customer": own_customer, "customer_device": own_device},
			update_modified=False,
		)
		frappe.db.set_value(
			"Service Order",
			other_order,
			{"technician": manager, "customer": other_customer, "customer_device": other_device},
			update_modified=False,
		)
		frappe.db.commit()

		frappe.set_user(technician)
		orders = list_service_orders(limit=100)
		order_names = {row["name"] for row in orders["items"]}
		if own_order not in order_names or other_order in order_names:
			raise AssertionError("Técnico recebeu OS não atribuída na lista.")
		if any(row.get("technician") != technician for row in orders["items"]):
			raise AssertionError("Lista do técnico contém OS atribuída a outra pessoa.")

		expected_total = frappe.db.count("Service Order", {"technician": technician})
		if orders["count"] != expected_total:
			raise AssertionError("Contador de OS do técnico ignorou o escopo da atribuição.")

		kanban = get_service_order_kanban(limit_per_column=40)
		for column in kanban["columns"]:
			if any(item.get("technician") != technician for item in column["items"]):
				raise AssertionError("Kanban do técnico contém OS atribuída a outra pessoa.")
			expected_column_count = frappe.db.count(
				"Service Order",
				{"technician": technician, "workflow_state": column["state"]},
			)
			if column["count"] != expected_column_count:
				raise AssertionError("Contador de coluna do Kanban ignorou o escopo técnico.")

		metrics = get_dashboard_metrics()
		if metrics["service_orders"]["total"] != expected_total or metrics["sales_visible"]:
			raise AssertionError("Dashboard técnico trouxe métricas globais ou vendas indevidas.")
		if metrics["service_orders"]["in_diagnosis"] != frappe.db.count(
			"Service Order", {"technician": technician, "workflow_state": "Em diagnóstico"}
		):
			raise AssertionError("Home técnica não contou diagnósticos da própria carteira.")
		if metrics["service_orders"]["ready_for_test"] != frappe.db.count(
			"Service Order", {"technician": technician, "workflow_state": "Teste final"}
		):
			raise AssertionError("Home técnica não contou OS prontas para teste da própria carteira.")
		statbar = {item["key"]: item["value"] for item in get_service_order_statbar()["items"]}
		if statbar["total"] != expected_total:
			raise AssertionError("StatBar do técnico ignorou o total de OS atribuídas.")
		if statbar["Em diagnóstico"] != frappe.db.count(
			"Service Order", {"technician": technician, "workflow_state": "Em diagnóstico"}
		):
			raise AssertionError("StatBar técnico não contou somente diagnósticos atribuídos.")

		customer_results = search_customers(query=own_label, limit=20)
		customer_names = {item["name"] for item in customer_results["items"]}
		if own_customer not in customer_names or other_customer in customer_names:
			raise AssertionError("Busca de clientes do técnico ignorou a carteira de suas OS.")
		if {"custom_cpf", "custom_rg", "email_id"}.intersection(customer_results["fields"]):
			raise AssertionError("Busca de clientes do técnico devolveu campos fiscais ou e-mail.")
		if any(
			item.get(field)
			for item in customer_results["items"]
			for field in ("custom_cpf", "custom_rg", "email_id")
		):
			raise AssertionError("Busca de clientes do técnico devolveu valores fiscais ou e-mail.")

		own_devices = list_customer_devices(query=own_imei, customer=own_customer, limit=20)["items"]
		if own_device not in {item["name"] for item in own_devices}:
			raise AssertionError("Técnico não encontrou aparelho vinculado à sua própria OS.")
		if list_customer_devices(query=other_imei, customer=other_customer, limit=20)["items"]:
			raise AssertionError("Técnico encontrou aparelho vinculado à OS de outra pessoa.")
		if list_customer_devices(query=other_imei, limit=20)["items"]:
			raise AssertionError("Busca global de aparelhos do técnico encontrou dispositivo alheio.")

		detail = get_service_order_detail(own_order)
		if any(detail["customer"].get(field) for field in ("custom_cpf", "custom_rg", "email_id")):
			raise AssertionError("Detalhe de OS do técnico devolveu dados fiscais ou e-mail do cliente.")
		if not detail.get("technical_view"):
			raise AssertionError("Detalhe técnico não sinalizou o contrato reduzido para a interface.")
		if not all(key in detail["parts"][0] for key in ("unit_price", "amount")):
			raise AssertionError("Detalhe de OS do técnico não devolveu o preço de venda da peça.")
		if detail["totals"]["discount"]:
			raise AssertionError("Detalhe de OS do técnico devolveu desconto interno em vez da projeção de venda.")
		if detail["totals"]["grand_total"] != detail["totals"]["service_total"] + detail["totals"]["parts_price_total"]:
			raise AssertionError("Detalhe de OS do técnico não totalizou os preços de venda.")
		diagnosed = save_technical_diagnosis(own_order, "Diagnóstico técnico restrito validado pela suíte.")
		if diagnosed["diagnosis"]["problem_found"] != "Diagnóstico técnico restrito validado pela suíte.":
			raise AssertionError("Técnico não conseguiu registrar diagnóstico na própria OS.")
		other_diagnosis_blocked = False
		try:
			save_technical_diagnosis(other_order, "Tentativa sem carteira.")
		except frappe.PermissionError:
			other_diagnosis_blocked = True
		if not other_diagnosis_blocked:
			raise AssertionError("Técnico registrou diagnóstico em OS alheia.")

		blocked_endpoints = {
			"vendas": lambda: list_sales(limit=1),
			"statbar_vendas": lambda: get_list_statbar("sales"),
			"trocas": lambda: list_trade_evaluations(limit=1),
			"statbar_trocas": lambda: get_list_statbar("trades"),
			"valor_troca": lambda: set_tradein_approved_value("inexistente", 1),
			"estoque_comercial": lambda: list_stock_items(limit=1, scope="commercial-products"),
		}
		for label, endpoint in blocked_endpoints.items():
			try:
				endpoint()
			except frappe.PermissionError:
				continue
			raise AssertionError(f"Técnico exclusivo acessou indevidamente: {label}.")

		mixed_user = _find_or_create_attendant_technician_user()
		frappe.set_user(mixed_user)
		if not list_sales(limit=1).get("fields"):
			raise AssertionError("Conta Atendente+Técnico perdeu o acesso de Atendente.")
		if list_service_orders(limit=100)["count"] < expected_total:
			raise AssertionError("Conta Atendente+Técnico recebeu escopo técnico indevido.")

		return {
			"technician": technician,
			"own_order": own_order,
			"other_order_blocked": other_order not in order_names,
			"scoped_total": expected_total,
			"sales_visible": metrics["sales_visible"],
			"blocked_endpoints": sorted(blocked_endpoints),
			"customer_device_scope": True,
			"fiscal_data_withheld": True,
			"technical_detail_sanitized": True,
			"own_diagnosis_saved": True,
			"multi_role_union_preserved": True,
		}
	finally:
		frappe.set_user(previous_user)


def run_tradein_frontend_checks() -> dict:
	"""Exercise the React-facing trade-in endpoints while leaving the atomic engine authoritative."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		customer = _get_or_create_demo_customer()

		def create_evaluation(*, suffix: str, value: float) -> dict:
			return create_trade_evaluation(
				{
					"customer": customer,
					"device_type": "iPhone",
					"model": f"Trade-in React {suffix}",
					"evaluated_device_desc": f"Trade-in React {suffix}",
					"imei": f"TP-FRONT-TRADE-{suffix}-{frappe.generate_hash(length=10)}",
					"physical_state": "B",
					"destination": "Venda",
					"suggested_value": value,
				}
			)["item"]

		frappe.set_user(attendant)
		seed = create_evaluation(suffix="SAIDA", value=300)
		seed = set_tradein_approved_value(seed["name"], 300)["item"]
		buyback = complete_trade_buyback(seed["name"])
		if not buyback["created_item"] or not buyback["item"].get("created_item"):
			raise AssertionError("Buyback pelo endpoint não criou o item único do aparelho usado.")
		output_devices = list_tradein_output_devices(query=seed["imei"], limit=5)["items"]
		output = next((item for item in output_devices if item["name"] == seed["imei"]), None)
		if not output:
			raise AssertionError("Aparelho recebido no Comercial não ficou disponível para a operação de troca.")

		received = create_evaluation(suffix="ENTRADA", value=250)
		received = set_tradein_approved_value(received["name"], 250)["item"]
		operation = confirm_tradein_operation(
			{"evaluation": received["name"], "device_out": output["name"], "difference": 100}
		)
		if operation["operation"]["atomic_status"] != "Concluída" or not operation["evaluation"].get("created_item"):
			raise AssertionError("Troca pelo endpoint não concluiu as duas pernas atômicas.")
		retry = confirm_tradein_operation(
			{"evaluation": received["name"], "device_out": output["name"], "difference": 100}
		)
		if retry["operation"]["name"] != operation["operation"]["name"]:
			raise AssertionError("Reenvio da troca criou uma segunda operação.")
		below_floor = create_evaluation(suffix="PISO", value=100)
		below_floor = set_tradein_approved_value(below_floor["name"], 100)["item"]
		below_floor_blocked = False
		try:
			confirm_tradein_operation({"evaluation": below_floor["name"], "device_out": output["name"], "difference": 0})
		except frappe.ValidationError:
			below_floor_blocked = True
		if not below_floor_blocked:
			raise AssertionError("Atendente confirmou troca abaixo do custo após a elevação do hook.")
		leaks = contains_sensitive_field({"buyback": buyback, "operation": operation, "devices": output_devices})
		if leaks:
			raise AssertionError(f"Endpoints de TROQUE vazaram campos sensíveis: {', '.join(leaks)}")

		frappe.set_user(technician)
		blocked = False
		try:
			create_evaluation(suffix="BLOQUEADO", value=100)
		except frappe.PermissionError:
			blocked = True
		if not blocked:
			raise AssertionError("Técnico acessou a criação de avaliação de troca.")

		return {
			"attendant": attendant,
			"buyback_item": buyback["created_item"],
			"operation": operation["operation"]["name"],
			"operation_idempotent": True,
			"below_cost_blocked_for_attendant": below_floor_blocked,
			"technician_blocked": blocked,
			"leaked_fields": leaks,
		}
	finally:
		frappe.set_user(previous_user)


def run_post_sale_checks() -> dict:
	"""Prove native returns preserve stock, payment mode and independent exchange documents."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		frappe.set_user(attendant)
		demo = _ensure_pos_demo_records()
		warehouse = demo["commercial_warehouse"]
		item = POS_BARCODE_ITEM
		before = _bin_qty(item, warehouse)
		sale = pos_create_sale({"idempotency_key": f"tp-return-pix-{frappe.generate_hash(length=16)}", "items": [{"item_code": item, "qty": 3}], "payments": [{"mode_of_payment": "Pix", "amount": 239.70, "installments": 1}]})
		after_sale = _bin_qty(item, warehouse)
		detail = get_sale_post_sale_detail(sale["sale"])
		returned = create_sales_return({"invoice": sale["sale"], "items": [{"item_code": item, "qty": 1}], "idempotency_key": f"tp-return-pix-request-{frappe.generate_hash(length=16)}"})
		after_return = _bin_qty(item, warehouse)
		return_doc = frappe.get_doc("Sales Invoice", returned["return_invoice"])
		if after_sale != before - 3 or after_return != after_sale + 1:
			raise AssertionError("Devolução parcial não restaurou somente a quantidade devolvida no Comercial.")
		if return_doc.return_against != sale["sale"] or not return_doc.is_return:
			raise AssertionError("Nota de retorno não ficou vinculada à venda original.")
		if not any(row.mode_of_payment == "Pix" for row in return_doc.payments):
			raise AssertionError("Estorno de Pix não preservou a forma de pagamento original.")
		if detail["items"][0]["available_qty"] != 3:
			raise AssertionError("Detalhe de pós-venda não expôs a quantidade ainda devolvível.")
		card_sale = pos_create_sale({"idempotency_key": f"tp-return-card-{frappe.generate_hash(length=16)}", "items": [{"item_code": POS_NAME_ITEM, "qty": 1}], "payments": [{"mode_of_payment": "Crédito à vista", "amount": 35.50, "installments": 1}]})
		card_return = create_sales_return({"invoice": card_sale["sale"], "items": [{"item_code": POS_NAME_ITEM, "qty": 1}], "idempotency_key": f"tp-return-card-request-{frappe.generate_hash(length=16)}"})
		card_sale_doc = frappe.get_doc("Sales Invoice", card_sale["sale"])
		card_return_doc = frappe.get_doc("Sales Invoice", card_return["return_invoice"])
		original_card = next((row for row in card_sale_doc.payments if row.mode_of_payment != "Pix"), None)
		returned_card = next((row for row in card_return_doc.payments if original_card and row.mode_of_payment == original_card.mode_of_payment), None)
		cash_account = frappe.db.get_value("Mode of Payment Account", {"parent": "Dinheiro", "company": card_sale_doc.company}, "default_account")
		if not returned_card or not original_card or returned_card.account != original_card.account or returned_card.account == cash_account:
			raise AssertionError("Estorno de cartao nao preservou a conta de recebiveis do cartao.")
		exchange_sale = pos_create_sale({"idempotency_key": f"tp-exchange-source-{frappe.generate_hash(length=16)}", "items": [{"item_code": item, "qty": 1}], "payments": [{"mode_of_payment": "Pix", "amount": 79.90, "installments": 1}]})
		exchange_key = f"tp-exchange-request-{frappe.generate_hash(length=16)}"
		exchange = exchange_sales_product({"invoice": exchange_sale["sale"], "items": [{"item_code": item, "qty": 1}], "idempotency_key": exchange_key, "new_sale": {"customer": "CONSUMIDOR FINAL", "items": [{"item_code": POS_NAME_ITEM, "qty": 1}], "discount_amount": 0, "payments": [{"mode_of_payment": "Pix", "amount": 35.50, "installments": 1}], "idempotency_key": f"{exchange_key}:sale"}})
		new_sale_name = exchange["new_sale"]["sale"]
		exchange_return = frappe.get_doc("Sales Invoice", exchange["return_invoice"])
		new_sale_doc = frappe.get_doc("Sales Invoice", new_sale_name)
		if exchange_return.return_against != exchange_sale["sale"] or exchange_return.name == new_sale_name:
			raise AssertionError("Troca nao gerou retorno e nova venda independentes.")
		if new_sale_name not in (exchange_return.remarks or "") or exchange_return.name not in (new_sale_doc.remarks or ""):
			raise AssertionError("Troca nao preservou o vinculo rastreavel entre devolucao e nova venda.")
		leaks = contains_sensitive_field({"detail": detail, "return": returned, "card_return": card_return, "exchange": exchange})
		if leaks:
			raise AssertionError(f"Pós-venda vazou custo: {', '.join(leaks)}")
		return {"sale": sale["sale"], "return": return_doc.name, "partial_stock": [before, after_sale, after_return], "payment_mode": "Pix", "card_payment_mode": "Crédito à vista", "exchange": {"return": exchange_return.name, "new_sale": new_sale_name}, "leaked_fields": leaks}
	finally:
		frappe.set_user(previous_user)


def run_technician_part_execution_checks() -> dict:
	"""A technician records part outcomes through the same idempotent stock engine as Desk."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		part_item = _ensure_part_request_repair_item()
		repair_warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
		if not repair_warehouse:
			raise AssertionError("Depósito de Reparo não configurado para validar execução técnica.")
		frappe.set_user("Administrator")
		_ensure_pos_demo_stock(part_item, repair_warehouse, valuation_rate=10.1237)
		selfie = BytesIO()
		Image.new("RGB", (24, 24), color=(22, 72, 110)).save(selfie, format="JPEG")
		selfie_data = "data:image/jpeg;base64," + b64encode(selfie.getvalue()).decode()
		signature = BytesIO()
		signature_canvas = Image.new("RGB", (160, 60), color=(245, 245, 245))
		signature_draw = ImageDraw.Draw(signature_canvas)
		signature_draw.line([(12, 42), (46, 14), (82, 46), (116, 16), (148, 38)], fill=(32, 36, 40), width=4)
		signature_canvas.save(signature, format="PNG")
		signature_data = "data:image/png;base64," + b64encode(signature.getvalue()).decode()

		def prepare_order(label: str):
			service_order = _create_action_request_service_order(attendant)
			frappe.set_user(attendant)
			issued = issue_os_acceptance(service_order, "Entrada")
			raw_token = issued["link"].rstrip("/").rsplit("/", 1)[-1]
			frappe.set_user("Guest")
			save_public_acceptance_selfie(raw_token, selfie_data)
			complete_public_acceptance(raw_token, signature_data, 1)
			frappe.set_user("Administrator")
			frappe.db.set_value(
				"Service Order",
				service_order,
				{
					"technician": technician,
					"workflow_state": "Em reparo",
					"approval_status": "Aprovado",
					"approval_channel": "Presencial",
					"approved_by_attendant": attendant,
					"approval_date": now_datetime(),
				},
				update_modified=False,
			)
			doc = frappe.get_doc("Service Order", service_order)
			frappe.db.set_value(
				doc.parts[0].doctype,
				doc.parts[0].name,
				{
					"item_code": part_item,
					"warehouse": repair_warehouse,
					"outcome": None,
					"loss_reason": None,
					"stock_entry": None,
					"reservation": None,
				},
				update_modified=False,
			)
			doc.reload()
			processar_pecas(doc)
			doc.reload()
			if not doc.parts[0].reservation:
				raise AssertionError("Peça aprovada não foi reservada antes da execução técnica.")
			return doc

		used_doc = prepare_order("usada")
		qty_before_used = _bin_qty(part_item, repair_warehouse)
		frappe.set_user(technician)
		used = set_service_order_part_outcome(used_doc.name, used_doc.parts[0].name, "Usada no reparo")
		used_part = used["parts"][0]
		qty_after_used = _bin_qty(part_item, repair_warehouse)
		if not used_part.get("stock_entry") or used_part.get("outcome") != "Usada no reparo" or qty_after_used >= qty_before_used:
			raise AssertionError("Uso técnico não baixou a peça no estoque de Reparo.")
		if not all(key in used_part for key in ("unit_price", "amount")):
			raise AssertionError("Execução técnica não preservou o preço de venda da peça.")
		if contains_sensitive_field(used_part, forbidden_values={10.1237}):
			raise AssertionError("Execução técnica expôs o custo da peça.")
		retry = set_service_order_part_outcome(used_doc.name, used_doc.parts[0].name, "Usada no reparo")
		if retry["parts"][0].get("stock_entry") != used_part["stock_entry"] or _bin_qty(part_item, repair_warehouse) != qty_after_used:
			raise AssertionError("Reenvio da baixa técnica duplicou a saída de estoque.")

		lost_doc = prepare_order("perdida")
		loss_reason_required = False
		try:
			set_service_order_part_outcome(lost_doc.name, lost_doc.parts[0].name, "Perdida")
		except frappe.ValidationError:
			loss_reason_required = True
		if not loss_reason_required:
			raise AssertionError("Perda de peça foi aceita sem motivo obrigatório.")
		lost = set_service_order_part_outcome(
			lost_doc.name,
			lost_doc.parts[0].name,
			"Perdida",
			"Perda da loja",
		)
		lost_part = lost["parts"][0]
		if not lost_part.get("stock_entry") or lost_part.get("outcome") != "Perdida" or lost_part.get("loss_reason") != "Perda da loja":
			raise AssertionError("Perda técnica não foi registrada pelo motor de peças.")
		other_doc = prepare_order("alheia")
		frappe.db.set_value("Service Order", other_doc.name, "technician", attendant, update_modified=False)
		frappe.set_user(technician)
		other_order_blocked = False
		try:
			set_service_order_part_outcome(other_doc.name, other_doc.parts[0].name, "Usada no reparo")
		except frappe.PermissionError:
			other_order_blocked = True
		if not other_order_blocked:
			raise AssertionError("Técnico registrou peça em uma OS fora da sua carteira.")
		leaks = contains_sensitive_field({"used": used, "lost": lost})
		if leaks:
			raise AssertionError(f"Execução técnica vazou dado sensível: {', '.join(leaks)}")

		return {
			"technician": technician,
			"used_stock_entry": used_part["stock_entry"],
			"used_qty_before": qty_before_used,
			"used_qty_after": qty_after_used,
			"idempotent": True,
			"loss_reason_required": loss_reason_required,
			"lost_stock_entry": lost_part["stock_entry"],
			"other_order_blocked": other_order_blocked,
			"leaked_fields": leaks,
		}
	finally:
		frappe.set_user(previous_user)


def run_technician_commission_checks() -> dict:
	"""Prove the commission screen reads only the caller's existing earnings."""
	if not frappe.db.exists("DocType", "Salary Component") or not frappe.db.exists("DocType", "Additional Salary"):
		return {
			"status": "skipped",
			"reason": "HRMS doctypes ausentes no runner local; validado no pipeline de CI com HRMS.",
		}
	previous_user = frappe.session.user
	previous_enabled = frappe.db.get_single_value("Tecponto Settings", "use_technician_commission")
	try:
		ensure_frontend_foundation()
		frappe.db.set_single_value("Tecponto Settings", "use_technician_commission", 1)
		frappe.clear_cache()
		technician = _find_or_create_user("Tecponto Tecnico")
		attendant = _find_or_create_user("Tecponto Atendente")
		peer = _find_or_create_commission_peer()
		frappe.db.commit()
		ensure_hr_foundation()
		own_employee = frappe.db.get_value("Employee", {"user_id": technician, "status": "Active"}, "name")
		peer_employee = frappe.db.get_value("Employee", {"user_id": peer, "status": "Active"}, "name")
		if not own_employee or not peer_employee:
			raise AssertionError("Foundation did not create active employees for commission checks.")

		own_order = _create_action_request_service_order(attendant)
		peer_order = _create_action_request_service_order(attendant)
		own_service = _assign_commission_service(own_order, technician, own_employee)
		peer_service = _assign_commission_service(peer_order, peer, peer_employee)
		_create_test_commission(own_employee, own_service, 24.0)
		_create_test_commission(peer_employee, peer_service, 31.0)
		frappe.db.commit()

		frappe.set_user(technician)
		payload = list_my_commissions(period="all")
		own_rows = [item for item in payload["items"] if item["service_order"] == own_order]
		if not own_rows or any(item["service_order"] == peer_order for item in payload["items"]):
			raise AssertionError("Commission endpoint exposed another technician's earnings.")
		if own_rows[0]["value"] != 24.0:
			raise AssertionError("Commission endpoint did not read the Additional Salary value.")
		leaks = contains_sensitive_field(payload)
		if leaks:
			raise AssertionError(f"Commission payload leaked sensitive fields: {', '.join(leaks)}")

		frappe.set_user(attendant)
		blocked = False
		try:
			list_my_commissions(period="all")
		except frappe.PermissionError:
			blocked = True
		if not blocked:
			raise AssertionError("Attendant accessed technician commission history.")

		return {
			"technician": technician,
			"own_service_order": own_order,
			"own_value": own_rows[0]["value"],
			"peer_hidden": True,
			"attendant_blocked": blocked,
			"leaked_fields": leaks,
		}
	finally:
		frappe.db.set_single_value("Tecponto Settings", "use_technician_commission", previous_enabled)
		frappe.clear_cache(doctype="Tecponto Settings")
		frappe.set_user(previous_user)


def run_lean_operation_checks() -> dict:
	"""Lean mode is opt-in for commissions and preserves real role authority."""
	previous_user = frappe.session.user
	previous_enabled = frappe.db.get_single_value("Tecponto Settings", "use_technician_commission")
	try:
		ensure_frontend_foundation()
		technician = _find_or_create_user("Tecponto Tecnico")
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		frappe.db.set_single_value("Tecponto Settings", "use_technician_commission", 0)

		frappe.set_user(technician)
		commission_hidden = False
		try:
			list_my_commissions(period="all")
		except frappe.PermissionError:
			commission_hidden = True
		if not commission_hidden:
			raise AssertionError("Comissão desativada ainda expôs a tela para o técnico.")

		frappe.set_user("Administrator")
		ensure_hr_foundation()
		if frappe.db.exists("Salary Component", "Comissão") and not previous_enabled:
			# Existing installations are never destructively changed. The important
			# assertion is that no new payroll document is generated while disabled.
			pass

		order_name = _create_action_request_service_order(attendant)
		limit = flt(frappe.db.get_single_value("Tecponto Settings", "discount_limit") or 0)
		multi_role_user = _find_or_create_multi_role_user()
		frappe.set_user(multi_role_user)
		direct = create_request(
			"service_order_discount",
			order_name,
			"Exceção executada sob papel Gestor acumulado.",
			{"discount": max(limit + 1, 1)},
		)
		if not direct.get("executed_directly") or direct.get("status") != "Executada":
			raise AssertionError("Usuário com papel aprovador acumulado não executou a ação diretamente.")
		if frappe.db.exists("Tecponto Request", direct.get("name")):
			raise AssertionError("Execução sob papel acumulado criou solicitação para autoaprovação.")
		if not frappe.db.exists(
			"Tecponto Access Audit",
			{"affected_user": multi_role_user, "change_type": "Ação sob papel acumulado"},
		):
			raise AssertionError("Execução sob papel acumulado não deixou trilha de auditoria.")

		frappe.set_user(attendant)
		pending = create_request(
			"service_order_discount",
			order_name,
			"Atendente sem papel Gestor solicita exceção.",
			{"discount": max(limit + 2, 2)},
		)
		if pending.get("status") != "Pendente" or pending.get("executed_directly"):
			raise AssertionError("Atendente sem papel Gestor contornou a solicitação de aprovação.")
		frappe.set_user(manager)
		if pending["name"] not in {row["name"] for row in list_pending_approvals()}:
			raise AssertionError("Fluxo normal de aprovação deixou de chegar ao Gestor.")

		from unittest.mock import patch
		from tecponto_app.tecponto.lean_operations import operation_shape

		with (
			patch("tecponto_app.tecponto.lean_operations.active_operational_users", return_value={technician}),
			patch("tecponto_app.tecponto.lean_operations.active_users_with_role", return_value={technician}),
		):
			one_person_shape = operation_shape()
		if not one_person_shape["single_operator"] or not one_person_shape["single_technician"]:
			raise AssertionError("Operação de uma pessoa não ativou a apresentação enxuta.")
		with (
			patch("tecponto_app.tecponto.lean_operations.active_operational_users", return_value={attendant, technician}),
			patch("tecponto_app.tecponto.lean_operations.active_users_with_role", return_value={technician}),
		):
			multi_person_shape = operation_shape()
		if multi_person_shape["single_operator"]:
			raise AssertionError("Operação com duas pessoas foi tratada indevidamente como enxuta.")

		return {
			"commissions_disabled": commission_hidden,
			"accumulated_role_execution": direct["status"],
			"audit_recorded": True,
			"single_role_request": pending["status"],
			"one_person_shape": one_person_shape,
			"multi_person_shape": multi_person_shape,
		}
	finally:
		frappe.db.set_single_value("Tecponto Settings", "use_technician_commission", previous_enabled)
		frappe.set_user(previous_user)


def run_operation_config_checks() -> dict:
	"""Prove the store operation contract is server-owned and reversible."""
	from tecponto_app.patches.v16_0.initialize_operation_settings_defaults import (
		OPERATION_DEFAULTS,
		execute as initialize_operation_settings_defaults,
	)

	previous_user = frappe.session.user
	fields = (
		"enable_repair_pillar",
		"enable_buy_pillar",
		"enable_tradein_pillar",
		"use_technician_commission",
		"diagnostic_fee_enabled",
		"diagnostic_fee_amount",
		"storage_fee_enabled",
		"storage_fee_amount",
		"storage_fee_start_days",
		"storage_fee_abandonment_days",
		"diagnosis_only_enabled",
		"payment_advance_enabled",
		"payment_installments_enabled",
		"payment_device_tradein_enabled",
		"default_warranty_days",
	)
	legacy_fields = tuple(OPERATION_DEFAULTS)
	legacy_before = frappe.db.get_singles_dict("Tecponto Settings")
	try:
		frappe.db.delete(
			"Singles",
			filters={"doctype": "Tecponto Settings", "field": ("in", legacy_fields)},
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
		legacy_after_first_run = frappe.db.get_singles_dict("Tecponto Settings")
		for fieldname in (
			"enable_repair_pillar",
			"enable_buy_pillar",
			"enable_tradein_pillar",
			"payment_advance_enabled",
			"payment_installments_enabled",
			"payment_device_tradein_enabled",
		):
			if legacy_after_first_run.get(fieldname) != "1":
				raise AssertionError(f"Patch não aplicou o default legado de {fieldname}.")
		if legacy_after_first_run.get("technician_assignment_mode") != "Dispatch":
			raise AssertionError("Patch não aplicou o modo Dispatch para atribuição técnica legada.")
		if legacy_after_first_run.get("unassigned_technician_alert_hours") != "4":
			raise AssertionError("Patch não aplicou o alerta de quatro horas para OS sem técnico.")
		if legacy_after_first_run.get("default_warranty_days") != "90":
			raise AssertionError("Patch não aplicou o prazo de garantia legado.")
		if legacy_after_first_run.get("diagnostic_fee_enabled") != "0":
			raise AssertionError("Patch sobrescreveu taxa de diagnóstico explicitamente desligada.")
		if legacy_after_first_run.get("storage_fee_start_days") != "0":
			raise AssertionError("Patch sobrescreveu prazo de armazenamento explicitamente configurado.")
		if legacy_after_first_run.get("use_technician_commission") != "0":
			raise AssertionError("Patch sobrescreveu comissão explicitamente desligada.")

		initialize_operation_settings_defaults()
		if frappe.db.get_singles_dict("Tecponto Settings") != legacy_after_first_run:
			raise AssertionError("Patch de defaults operacionais não é idempotente.")
	finally:
		frappe.db.delete(
			"Singles",
			filters={"doctype": "Tecponto Settings", "field": ("in", legacy_fields)},
		)
		legacy_restore = {
			fieldname: legacy_before[fieldname]
			for fieldname in legacy_fields
			if fieldname in legacy_before
		}
		if legacy_restore:
			frappe.db.set_single_value("Tecponto Settings", legacy_restore, update_modified=False)

	assignment_fields = ("technician_assignment_mode", "unassigned_technician_alert_hours")
	assignment_before = {
		fieldname: frappe.db.get_single_value("Tecponto Settings", fieldname)
		for fieldname in assignment_fields
	}
	try:
		frappe.db.delete("Singles", filters={"doctype": "Tecponto Settings", "field": ("in", assignment_fields)})
		frappe.clear_cache(doctype="Tecponto Settings")
		from tecponto_app.install import bootstrap_erpnext_foundation

		bootstrap_erpnext_foundation()
		if frappe.db.get_single_value("Tecponto Settings", "technician_assignment_mode") != "Dispatch":
			raise AssertionError("Bootstrap legado não preencheu o modo de atribuição obrigatório.")
		if frappe.db.get_single_value("Tecponto Settings", "unassigned_technician_alert_hours") != 4:
			raise AssertionError("Bootstrap legado não preencheu o alerta obrigatório.")

		frappe.db.set_single_value(
			"Tecponto Settings",
			{"technician_assignment_mode": "Pull", "unassigned_technician_alert_hours": 0},
			update_modified=False,
		)
		frappe.clear_cache(doctype="Tecponto Settings")
		bootstrap_erpnext_foundation()
		if frappe.db.get_single_value("Tecponto Settings", "technician_assignment_mode") != "Pull":
			raise AssertionError("Bootstrap sobrescreveu o modo de atribuição configurado.")
		if frappe.db.get_single_value("Tecponto Settings", "unassigned_technician_alert_hours") != 0:
			raise AssertionError("Bootstrap sobrescreveu o alerta explicitamente desativado.")
	finally:
		frappe.db.delete("Singles", filters={"doctype": "Tecponto Settings", "field": ("in", assignment_fields)})
		assignment_restore = {
			fieldname: value
			for fieldname, value in assignment_before.items()
			if value is not None
		}
		if assignment_restore:
			frappe.db.set_single_value("Tecponto Settings", assignment_restore, update_modified=False)
		frappe.clear_cache(doctype="Tecponto Settings")

	settings = frappe.get_single("Tecponto Settings")
	original = {field: settings.get(field) for field in fields}
	try:
		settings.update(
			{
				"enable_repair_pillar": 1,
				"enable_buy_pillar": 0,
				"enable_tradein_pillar": 0,
				"use_technician_commission": 0,
				"diagnostic_fee_enabled": 1,
				"diagnostic_fee_amount": 35,
				"storage_fee_enabled": 1,
				"storage_fee_amount": 4.5,
				"storage_fee_start_days": 30,
				"storage_fee_abandonment_days": 90,
				"diagnosis_only_enabled": 1,
				"payment_advance_enabled": 1,
				"payment_installments_enabled": 0,
				"payment_device_tradein_enabled": 0,
				"default_warranty_days": 90,
			}
		)
		settings.save(ignore_permissions=True)
		attendant = _find_or_create_user("Tecponto Atendente")
		frappe.set_user(attendant)
		lean_boot = get_boot()
		if lean_boot["features"]["pillars"] != {"repair": True, "buy": False, "tradein": False}:
			raise AssertionError("Contrato do motor não refletiu a loja só-REPARO.")
		if lean_boot["features"]["technician_commissions_enabled"]:
			raise AssertionError("Comissão desligada vazou no contrato de operação.")
		if lean_boot["features"]["diagnostic_fee"] != {"enabled": True, "amount": 35.0}:
			raise AssertionError("Taxa de diagnóstico não veio do serviço central.")
		if lean_boot["features"]["storage_fee"] != {"enabled": True, "amount": 4.5, "start_days": 30, "abandonment_days": 90}:
			raise AssertionError("Taxa de armazenamento não veio do serviço central.")
		if lean_boot["features"]["payments"] != {"advance_enabled": True, "installments_enabled": False, "device_tradein_enabled": False}:
			raise AssertionError("Flags de pagamento não vieram do serviço central.")

		frappe.set_user("Administrator")
		settings.update({"enable_buy_pillar": 1, "enable_tradein_pillar": 1})
		settings.save(ignore_permissions=True)
		frappe.set_user(attendant)
		complete_boot = get_boot()
		if complete_boot["features"]["pillars"] != {"repair": True, "buy": True, "tradein": True}:
			raise AssertionError("Contrato do motor não restaurou a loja completa.")

		return {
			"lean_store": lean_boot["features"],
			"complete_store_pillars": complete_boot["features"]["pillars"],
			"legacy_defaults_patch": "idempotent_without_overwriting_explicit_zero",
			"cost_guard_contract": "no_cost_fields",
		}
	finally:
		frappe.set_user("Administrator")
		settings.update(original)
		settings.save(ignore_permissions=True)
		frappe.set_user(previous_user)


def run_cash_session_checks() -> dict:
	"""Prove opening idempotency, derived balance and append-only cash movements."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		cash_point = f"Teste caixa 4.1 {frappe.generate_hash(length=10)}"
		key = f"tp-cash-open-{frappe.generate_hash(length=20)}"

		frappe.set_user(attendant)
		opened = open_cash_session(
			opening_amount=120.50,
			idempotency_key=key,
			opened_by=attendant,
			cash_point=cash_point,
		)
		if opened["drawer_balance"] != 120.50 or opened["movement_count"] != 1:
			raise AssertionError("Abertura não criou o saldo inicial derivado esperado.")

		replay = open_cash_session(
			opening_amount=120.50,
			idempotency_key=key,
			opened_by=attendant,
			cash_point=cash_point,
		)
		if replay["session"] != opened["session"] or not replay["idempotent_replay"]:
			raise AssertionError("Reenvio da abertura não retornou a mesma sessão de caixa.")
		if frappe.db.count(CASH_MOVEMENT_DOCTYPE, {"cash_session": opened["session"]}) != 1:
			raise AssertionError("Reenvio idempotente criou um segundo movimento de abertura.")

		supply_key = f"tp-cash-supply-{frappe.generate_hash(length=20)}"
		supply = record_cash_movement(
			cash_session=opened["session"],
			movement_type="Suprimento",
			direction="Entrada",
			amount=25.25,
			idempotency_key=supply_key,
			registered_by=attendant,
			reason="Troco adicional",
		)
		if not supply["movement"]:
			raise AssertionError("Motor não registrou o movimento de suprimento.")
		if not record_cash_movement(
			cash_session=opened["session"],
			movement_type="Suprimento",
			direction="Entrada",
			amount=25.25,
			idempotency_key=supply_key,
			registered_by=attendant,
			reason="Troco adicional",
		)["idempotent_replay"]:
			raise AssertionError("Reenvio do movimento não foi idempotente.")
		summary = get_cash_session_summary(opened["session"])
		if summary["drawer_balance"] != 145.75 or summary["movement_count"] != 2:
			raise AssertionError("Saldo da gaveta não foi derivado dos movimentos.")
		cash_leaks = contains_sensitive_field(summary, forbidden_values={BUDGET_COST_GUARD_VALUATION})
		if cash_leaks:
			raise AssertionError(f"Resumo de caixa vazou campo sensível: {', '.join(cash_leaks)}")

		movement = frappe.get_doc(CASH_MOVEMENT_DOCTYPE, supply["movement"])
		movement.reason = "Tentativa de alterar lançamento"
		immutable = False
		try:
			movement.save(ignore_permissions=True)
		except frappe.ValidationError:
			immutable = True
		if not immutable:
			raise AssertionError("Movimento de caixa pôde ser alterado após o registro.")
		deletion_blocked = False
		try:
			frappe.delete_doc(CASH_MOVEMENT_DOCTYPE, supply["movement"], ignore_permissions=True)
		except frappe.ValidationError:
			deletion_blocked = True
		if not deletion_blocked:
			raise AssertionError("Movimento de caixa pôde ser excluído após o registro.")

		frappe.set_user(technician)
		technician_blocked = False
		try:
			open_store_cash_session(50, f"tp-cash-tech-{frappe.generate_hash(length=20)}")
		except frappe.PermissionError:
			technician_blocked = True
		if not technician_blocked:
			raise AssertionError("Técnico conseguiu abrir o caixa da loja.")

		frappe.set_user(attendant)
		status_payload = get_store_cash_session()
		if "session" not in status_payload:
			raise AssertionError("Endpoint de status do caixa não retornou o contrato esperado.")
		return {
			"status": "ok",
			"session": opened["session"],
			"idempotency": {"opening": replay["idempotent_replay"], "movement": True},
			"drawer_balance": summary["drawer_balance"],
			"immutability": {"update_blocked": immutable, "deletion_blocked": deletion_blocked},
			"technician_blocked": technician_blocked,
			"sensitive_guard": {"leaked_fields": cash_leaks},
		}
	finally:
		frappe.set_user(previous_user)


def run_pos_cash_integration_checks() -> dict:
	"""Prove POS/returns and the cash ledger are one atomic, payment-aware operation."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		_ensure_default_test_cash_session(attendant)
		demo = _ensure_pos_demo_records()
		frappe.set_user(attendant)
		active_session = get_open_cash_session()
		frappe.db.set_value("Tecponto Cash Session", active_session["session"], "status", "Fechado", update_modified=False)
		closed_cash_blocked = False
		try:
			pos_create_sale(
				{
					"idempotency_key": f"tp-cash-closed-{frappe.generate_hash(length=18)}",
					"items": [{"item_code": POS_NAME_ITEM, "qty": 1}],
					"discount_amount": 0,
					"payments": [{"mode_of_payment": "Pix", "amount": 35.50, "installments": 1}],
				}
			)
		except frappe.ValidationError:
			closed_cash_blocked = True
		finally:
			frappe.db.set_value("Tecponto Cash Session", active_session["session"], "status", "Aberto", update_modified=False)
		if not closed_cash_blocked:
			raise AssertionError("PDV aceitou pagamento com caixa fechado.")

		cash_before = get_open_cash_session()["drawer_balance"]
		cash_sale = pos_create_sale(
			{
				"idempotency_key": f"tp-cash-sale-{frappe.generate_hash(length=18)}",
				"items": [{"item_code": POS_NAME_ITEM, "qty": 1}],
				"discount_amount": 0,
				"payments": [{"mode_of_payment": "Dinheiro", "amount": 35.50, "installments": 1}],
			}
		)
		cash_after_sale = get_open_cash_session()["drawer_balance"]
		if cash_after_sale != flt(cash_before + 35.50, 2):
			raise AssertionError("Venda em dinheiro não entrou na gaveta.")
		cash_movement = frappe.db.get_value(
			CASH_MOVEMENT_DOCTYPE,
			{"reference_doctype": "Sales Invoice", "reference_name": cash_sale["sale"], "payment_mode": "Dinheiro"},
			["direction", "affects_drawer"],
			as_dict=True,
		)
		if not cash_movement or cash_movement.direction != "Entrada" or not cash_movement.affects_drawer:
			raise AssertionError("Venda em dinheiro não criou o movimento de gaveta correto.")

		outside_before = get_open_cash_session()["drawer_balance"]
		outside_sale = pos_create_sale(
			{
				"idempotency_key": f"tp-cash-outside-{frappe.generate_hash(length=18)}",
				"items": [{"item_code": POS_BARCODE_ITEM, "qty": 1}],
				"discount_amount": 0,
				"payments": [
					{"mode_of_payment": "Pix", "amount": 35.50, "installments": 1},
					{"mode_of_payment": "Crédito à vista", "amount": 44.40, "installments": 1},
				],
			}
		)
		outside_after = get_open_cash_session()["drawer_balance"]
		if outside_after != outside_before:
			raise AssertionError("Pix ou cartão alteraram indevidamente a gaveta física.")
		outside_movements = frappe.get_all(
			CASH_MOVEMENT_DOCTYPE,
			filters={"reference_doctype": "Sales Invoice", "reference_name": outside_sale["sale"]},
			fields=["payment_mode", "affects_drawer"],
		)
		if {row.payment_mode for row in outside_movements} != {"Pix", "Crédito à vista"} or any(row.affects_drawer for row in outside_movements):
			raise AssertionError("Pix/cartão não foram registrados fora da gaveta como esperado.")

		return_key = f"tp-cash-return-{frappe.generate_hash(length=18)}"
		cash_before_return = get_open_cash_session()["drawer_balance"]
		cash_return = create_sales_return(
			{"invoice": cash_sale["sale"], "items": [{"item_code": POS_NAME_ITEM, "qty": 1}], "idempotency_key": return_key}
		)
		cash_after_return = get_open_cash_session()["drawer_balance"]
		if cash_after_return != flt(cash_before_return - 35.50, 2):
			raise AssertionError("Devolução em dinheiro não saiu da gaveta.")
		if not frappe.db.get_value(CASH_MOVEMENT_DOCTYPE, {"reference_name": cash_return["return_invoice"], "direction": "Saída", "affects_drawer": 1}, "name"):
			raise AssertionError("Devolução em dinheiro não criou estorno de gaveta.")
		movement_count = frappe.db.count(CASH_MOVEMENT_DOCTYPE, {"reference_name": cash_return["return_invoice"]})
		replay = create_sales_return(
			{"invoice": cash_sale["sale"], "items": [{"item_code": POS_NAME_ITEM, "qty": 1}], "idempotency_key": return_key}
		)
		if not replay["idempotent_replay"] or replay["return_invoice"] != cash_return["return_invoice"]:
			raise AssertionError("Reenvio da devolução não retornou a mesma nota de retorno.")
		if frappe.db.count(CASH_MOVEMENT_DOCTYPE, {"reference_name": cash_return["return_invoice"]}) != movement_count:
			raise AssertionError("Reenvio da devolução duplicou movimento de caixa.")

		invoice_count_before = frappe.db.count("Sales Invoice", {"docstatus": 1})
		cash_count_before = frappe.db.count(CASH_MOVEMENT_DOCTYPE)
		stock_before_failure = _bin_qty(POS_NAME_ITEM, demo["commercial_warehouse"])
		failed = False
		with patch("tecponto_app.tecponto.frontend.pos.record_sales_invoice_cash_movements", side_effect=RuntimeError("falha simulada após nota")):
			try:
				pos_create_sale(
					{
						"idempotency_key": f"tp-cash-atomic-{frappe.generate_hash(length=18)}",
						"items": [{"item_code": POS_NAME_ITEM, "qty": 1}],
						"discount_amount": 0,
						"payments": [{"mode_of_payment": "Dinheiro", "amount": 35.50, "installments": 1}],
					}
				)
			except RuntimeError:
				failed = True
		if not failed or frappe.db.count("Sales Invoice", {"docstatus": 1}) != invoice_count_before:
			raise AssertionError("Falha após a nota deixou uma Sales Invoice submetida pela metade.")
		if frappe.db.count(CASH_MOVEMENT_DOCTYPE) != cash_count_before or _bin_qty(POS_NAME_ITEM, demo["commercial_warehouse"]) != stock_before_failure:
			raise AssertionError("Rollback atômico deixou movimento de caixa ou estoque parcial.")

		leaks = contains_sensitive_field(
			{"cash_sale": cash_sale, "outside_sale": outside_sale, "cash_return": cash_return, "summary": get_open_cash_session()},
			forbidden_values=set(demo["valuation_rates"]),
		)
		if leaks:
			raise AssertionError(f"Integração de caixa vazou custo: {', '.join(leaks)}")
		return {
			"status": "ok",
			"cash_sale": cash_sale["sale"],
			"cash_return": cash_return["return_invoice"],
			"outside_drawer_unchanged": True,
			"return_replay": True,
			"atomic_rollback": True,
			"closed_cash_blocked": closed_cash_blocked,
			"leaked_fields": leaks,
		}
	finally:
		frappe.set_user(previous_user)


def run_cash_closing_checks() -> dict:
	"""Prove closing counts, explained discrepancies, drawer adjustments and a cost-safe statement."""
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		frappe.set_user(attendant)

		matched = open_cash_session(
			opening_amount=100,
			idempotency_key=f"tp-close-match-{frappe.generate_hash(length=18)}",
			opened_by=attendant,
			cash_point=f"Fechamento 4.3 {frappe.generate_hash(length=9)}",
		)
		record_drawer_adjustment(
			movement_type="Suprimento", amount=30, reason="Troco adicional", idempotency_key=f"tp-supply-{frappe.generate_hash(length=18)}", registered_by=attendant, cash_session=matched["session"],
		)
		record_drawer_adjustment(
			movement_type="Sangria", amount=20, reason="Retirada para cofre", idempotency_key=f"tp-withdraw-{frappe.generate_hash(length=18)}", registered_by=attendant, cash_session=matched["session"],
		)
		record_cash_movement(
			cash_session=matched["session"], movement_type="Recebimento de venda", direction="Entrada", amount=40, payment_mode="Pix", affects_drawer=False,
			idempotency_key=f"tp-close-pix-{frappe.generate_hash(length=18)}", registered_by=attendant, reference_doctype=CASH_SESSION_DOCTYPE, reference_name=matched["session"],
		)
		record_cash_movement(
			cash_session=matched["session"], movement_type="Recebimento de venda", direction="Entrada", amount=60, payment_mode="Crédito à vista", affects_drawer=False,
			idempotency_key=f"tp-close-card-{frappe.generate_hash(length=18)}", registered_by=attendant, reference_doctype=CASH_SESSION_DOCTYPE, reference_name=matched["session"],
		)
		statement = get_cash_statement(cash_session=matched["session"])
		expected = {row["payment_mode"]: row["expected_amount"] for row in statement["payment_totals"]}
		if expected != {"Dinheiro": 110.0, "Pix": 40.0, "Crédito à vista": 60.0} or statement["drawer_balance"] != 110.0:
			raise AssertionError("Extrato não derivou gaveta, Pix e cartão dos movimentos imutáveis.")
		if not any(row["movement_type"] == "Sangria" and row["reason"] == "Retirada para cofre" for row in statement["movements"]):
			raise AssertionError("Sangria não apareceu no extrato com motivo auditável.")
		closing = close_cash_session(
			counted_amounts=expected, reason="", idempotency_key=f"tp-close-clean-{frappe.generate_hash(length=18)}", closed_by=attendant, cash_session=matched["session"],
		)
		if closing["status"] != "Fechado" or any(row["difference"] for row in closing["closing"]["counts"]):
			raise AssertionError("Fechamento que bate não foi registrado limpo.")

		divergent = open_cash_session(
			opening_amount=75,
			idempotency_key=f"tp-close-diff-{frappe.generate_hash(length=18)}",
			opened_by=attendant,
			cash_point=f"Divergência 4.3 {frappe.generate_hash(length=9)}",
		)
		without_reason_blocked = False
		try:
			close_cash_session(counted_amounts={"Dinheiro": 70}, reason="", idempotency_key=f"tp-close-no-reason-{frappe.generate_hash(length=18)}", closed_by=attendant, cash_session=divergent["session"])
		except frappe.ValidationError:
			without_reason_blocked = True
		if not without_reason_blocked:
			raise AssertionError("Fechamento com divergência foi aceito sem motivo.")
		divergence = close_cash_session(
			counted_amounts={"Dinheiro": 70}, reason="Falta apurada na conferência", idempotency_key=f"tp-close-with-reason-{frappe.generate_hash(length=18)}", closed_by=attendant, cash_session=divergent["session"],
		)
		if divergence["status"] != "Fechado" or divergence["closing"]["reason"] != "Falta apurada na conferência" or divergence["closing"]["counts"][0]["difference"] != -5.0:
			raise AssertionError("Divergência com motivo não foi fechada e auditada como esperado.")

		# The React screen serializes counts through the public endpoint and pins the
		# session it rendered. Cover that path, not just the lower-level helper.
		endpoint_session = open_cash_session(
			opening_amount=45,
			idempotency_key=f"tp-close-endpoint-{frappe.generate_hash(length=18)}",
			opened_by=attendant,
			cash_point=f"Endpoint 4.3 {frappe.generate_hash(length=9)}",
		)
		endpoint_closing = close_store_cash_session(
			cash_session=endpoint_session["session"],
			counted_amounts=json.dumps({"Dinheiro": 45}),
			reason="",
			idempotency_key=f"tp-close-endpoint-ok-{frappe.generate_hash(length=18)}",
		)
		if endpoint_closing["status"] != "Fechado" or frappe.db.get_value(CASH_SESSION_DOCTYPE, endpoint_session["session"], "status") != "Fechado":
			raise AssertionError("Fechamento pelo endpoint da tela não persistiu a sessão fechada.")
		payment_blocked_after_close = False
		try:
			record_cash_movement(
				cash_session=endpoint_session["session"], movement_type="Recebimento de venda", direction="Entrada", amount=1,
				idempotency_key=f"tp-close-block-payment-{frappe.generate_hash(length=18)}", registered_by=attendant,
			)
		except frappe.ValidationError:
			payment_blocked_after_close = True
		if not payment_blocked_after_close:
			raise AssertionError("Caixa fechado aceitou pagamento após o fechamento.")
		daily_history = get_store_cash_session_history(limit=31)["sessions"]
		if not daily_history or not all({"opened_at", "turnover", "drawer_balance", "status"}.issubset(row) for row in daily_history):
			raise AssertionError("Histórico diário não expôs abertura, giro, saldo e status da jornada.")

		frappe.set_user(technician)
		technician_blocked = False
		try:
			get_store_cash_statement()
		except frappe.PermissionError:
			technician_blocked = True
		if not technician_blocked:
			raise AssertionError("Técnico conseguiu acessar o extrato do caixa.")

		leaks = contains_sensitive_field(statement, forbidden_values={BUDGET_COST_GUARD_VALUATION})
		if leaks:
			raise AssertionError(f"Extrato de caixa vazou custo ou margem: {', '.join(leaks)}")
		return {
			"status": "ok",
			"clean_closing": matched["session"],
			"divergence_closing": divergent["session"],
			"supply_and_withdrawal": True,
			"endpoint_closing": endpoint_session["session"],
			"closed_cash_blocks_payment": payment_blocked_after_close,
			"daily_history": len(daily_history),
			"technician_blocked": technician_blocked,
			"leaked_fields": leaks,
		}
	finally:
		frappe.set_user(previous_user)


def _ensure_default_test_cash_session(attendant: str) -> None:
	if get_open_cash_session():
		return
	open_cash_session(
		opening_amount=100,
		idempotency_key="tp-local-test-default-cash-session",
		opened_by=attendant,
	)


def run_service_order_cash_checks() -> dict:
	"""Prove OS receipts, conditional fees and non-cash consideration stay atomic."""
	previous_user = frappe.session.user
	settings_fields = [
		"diagnostic_fee_enabled",
		"diagnostic_fee_amount",
		"storage_fee_enabled",
		"storage_fee_amount",
		"payment_advance_enabled",
		"payment_installments_enabled",
		"payment_device_tradein_enabled",
	]
	settings_before = {field: frappe.db.get_single_value("Tecponto Settings", field) for field in settings_fields}
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		_ensure_default_test_cash_session(attendant)
		frappe.db.set_single_value(
			"Tecponto Settings",
			{
				"diagnostic_fee_enabled": 1,
				"diagnostic_fee_amount": 35,
				"storage_fee_enabled": 0,
				"storage_fee_amount": 4.5,
				"payment_advance_enabled": 1,
				"payment_installments_enabled": 1,
				"payment_device_tradein_enabled": 1,
			},
			update_modified=False,
		)

		def make_invoiced_order(slug: str, state: str = "Pronto para retirada"):
			order_name = _create_action_request_service_order(attendant)
			frappe.db.set_value(
				"Service Order",
				order_name,
				{"workflow_state": state, "link_acceptance_required": 0, "sales_invoice": None},
				update_modified=False,
			)
			from tecponto_app.tecponto.service_order.billing import gerar_nota

			doc = frappe.get_doc("Service Order", order_name)
			gerar_nota(doc)
			return frappe.get_doc("Service Order", order_name)

		frappe.set_user(attendant)
		cash_before = get_open_cash_session()["drawer_balance"]
		cash_order = make_invoiced_order("cash")
		cash_receipt = receive_service_order_payment(
			cash_order.name,
			{"kind": "regular", "amount": 50, "mode_of_payment": "Dinheiro", "idempotency_key": f"tp-os-cash-{frappe.generate_hash(length=18)}"},
		)
		if get_open_cash_session()["drawer_balance"] != flt(cash_before + 50, 2) or not cash_receipt["payment"]["affects_drawer"]:
			raise AssertionError("Pagamento de OS em dinheiro não entrou na gaveta.")

		diagnostic_order_name = _create_action_request_service_order(attendant)
		frappe.db.set_value(
			"Service Order", diagnostic_order_name, {"workflow_state": "Reprovado", "link_acceptance_required": 0, "diagnosis_fee_enabled": 1, "diagnosis_fee_value": 35}, update_modified=False
		)
		from tecponto_app.tecponto.service_order.billing import gerar_nota

		gerar_nota(frappe.get_doc("Service Order", diagnostic_order_name))
		diagnostic_fee = receive_service_order_payment(
			diagnostic_order_name,
			{"kind": "diagnostic_fee", "amount": 35, "mode_of_payment": "Pix", "idempotency_key": f"tp-os-diag-{frappe.generate_hash(length=18)}"},
		)
		if diagnostic_fee["payment"]["affects_drawer"]:
			raise AssertionError("Taxa de diagnóstico em Pix alterou a gaveta.")
		frappe.db.set_single_value("Tecponto Settings", "diagnostic_fee_enabled", 0)
		fee_disabled = False
		try:
			receive_service_order_payment(
			diagnostic_order_name,
				{"kind": "diagnostic_fee", "amount": 35, "mode_of_payment": "Pix", "idempotency_key": f"tp-os-diag-off-{frappe.generate_hash(length=18)}"},
			)
		except frappe.ValidationError:
			fee_disabled = True
		if not fee_disabled:
			raise AssertionError("Taxa de diagnóstico foi cobrada com o toggle desligado.")
		frappe.db.set_single_value("Tecponto Settings", "diagnostic_fee_enabled", 1)

		advance_order_name = _create_action_request_service_order(attendant)
		advance = receive_service_order_payment(
			advance_order_name,
			{"kind": "advance", "amount": 20, "mode_of_payment": "Dinheiro", "idempotency_key": f"tp-os-advance-{frappe.generate_hash(length=18)}"},
		)
		frappe.db.set_value("Service Order", advance_order_name, {"workflow_state": "Pronto para retirada", "link_acceptance_required": 0}, update_modified=False)
		gerar_nota(frappe.get_doc("Service Order", advance_order_name))
		advance_order = frappe.get_doc("Service Order", advance_order_name)
		advance_invoice = frappe.get_doc("Sales Invoice", advance_order.sales_invoice)
		if not advance["payment"]["cash_movement"] or flt(advance_invoice.outstanding_amount) >= flt(advance_invoice.grand_total):
			raise AssertionError("Sinal não foi alocado na nota da OS.")
		rest = receive_service_order_payment(
			advance_order.name,
			{"kind": "regular", "amount": flt(advance_invoice.outstanding_amount), "mode_of_payment": "Pix", "idempotency_key": f"tp-os-rest-{frappe.generate_hash(length=18)}"},
		)
		if rest["detail"]["finance"]["remaining_total"] != 0:
			raise AssertionError("Pagamento do restante não zerou o saldo da OS.")

		installment_order = make_invoiced_order("installment")
		first_installment = receive_service_order_payment(
			installment_order.name,
			{"kind": "installment", "amount": 30, "mode_of_payment": "Dinheiro", "idempotency_key": f"tp-os-installment-1-{frappe.generate_hash(length=18)}"},
		)
		second_installment = receive_service_order_payment(
			installment_order.name,
			{"kind": "installment", "amount": 30, "mode_of_payment": "Pix", "idempotency_key": f"tp-os-installment-2-{frappe.generate_hash(length=18)}"},
		)
		if not first_installment["payment"]["cash_movement"] or second_installment["payment"]["affects_drawer"]:
			raise AssertionError("Parcelas não registraram cada pagamento pela forma correta.")

		trade_order_name = _create_action_request_service_order(attendant)
		frappe.set_user("Administrator")
		trade = frappe.get_doc(
			{
				"doctype": "Device Trade Evaluation",
				"naming_series": "TROCA-.YYYY.-.####",
				"customer": frappe.db.get_value("Service Order", trade_order_name, "customer"),
				"evaluated_device_desc": "Aparelho usado como pagamento da OS",
				"approved_value": 40,
			}
		)
		trade.insert(ignore_permissions=True)
		frappe.set_user(attendant)
		trade_candidates = list_service_order_tradein_candidates(trade_order_name)
		if trade.name not in {item["name"] for item in trade_candidates["items"]}:
			raise AssertionError("Avaliação elegível não apareceu para abatimento da OS.")
		drawer_before_trade = get_open_cash_session()["drawer_balance"]
		trade_payment = receive_service_order_payment(
			trade_order_name,
			{"kind": "tradein", "amount": 40, "trade_evaluation": trade.name, "idempotency_key": f"tp-os-trade-{frappe.generate_hash(length=18)}"},
		)
		if trade_payment["payment"]["cash_movement"] or get_open_cash_session()["drawer_balance"] != drawer_before_trade:
			raise AssertionError("Aparelho como pagamento alterou indevidamente a gaveta.")

		cancel_order_name = _create_action_request_service_order(attendant)
		frappe.db.set_value("Service Order", cancel_order_name, "workflow_state", "Cancelado", update_modified=False)
		cancel_adjustment = receive_service_order_payment(
			cancel_order_name,
			{"kind": "cancellation_adjustment", "amount": 10, "mode_of_payment": "Dinheiro", "direction": "Saída", "reason": "Estorno complementar registrado.", "idempotency_key": f"tp-os-cancel-{frappe.generate_hash(length=18)}"},
		)
		if cancel_adjustment["payment"]["direction"] != "Saída" or not cancel_adjustment["payment"]["reason"]:
			raise AssertionError("Ajuste de cancelamento não ficou auditado.")

		atomic_order = make_invoiced_order("atomic")
		payment_count_before = frappe.db.count("Payment Entry", {"party": atomic_order.customer, "docstatus": 1})
		movement_count_before = frappe.db.count(CASH_MOVEMENT_DOCTYPE)
		atomic_failed = False
		with patch("tecponto_app.tecponto.service_order.payments.record_cash_movement", side_effect=RuntimeError("falha simulada após Payment Entry")):
			try:
				receive_service_order_payment(
					atomic_order.name,
					{"kind": "regular", "amount": 10, "mode_of_payment": "Dinheiro", "idempotency_key": f"tp-os-atomic-{frappe.generate_hash(length=18)}"},
				)
			except RuntimeError:
				atomic_failed = True
		if not atomic_failed or frappe.db.count(CASH_MOVEMENT_DOCTYPE) != movement_count_before or frappe.db.count("Payment Entry", {"party": atomic_order.customer, "docstatus": 1}) != payment_count_before:
			raise AssertionError("Falha na cobrança da OS deixou Payment Entry ou caixa pela metade.")
		if frappe.session.user != attendant:
			raise AssertionError("Falha na cobrança da OS não restaurou a sessão do atendente.")
		posting_failure_restores_session = False
		try:
			with native_financial_posting():
				if frappe.session.user != "Administrator":
					raise AssertionError("Elevação de postagem não entrou no escopo administrativo.")
				raise RuntimeError("falha simulada durante a postagem nativa")
		except RuntimeError:
			posting_failure_restores_session = frappe.session.user == attendant
		if not posting_failure_restores_session:
			raise AssertionError("Falha durante a postagem nativa deixou a sessão elevada.")

		finance = get_service_order_detail(advance_order.name)["finance"]
		leaks = contains_sensitive_field({"finance": finance, "payments": [cash_receipt, diagnostic_fee, advance, rest, first_installment, second_installment, trade_payment, cancel_adjustment]})
		if leaks:
			raise AssertionError(f"Pagamento de OS vazou custo ou margem: {', '.join(leaks)}")
		return {"status": "ok", "cash_receipt": cash_receipt["payment"]["name"], "diagnostic_toggle": fee_disabled, "advance_and_remainder": True, "installments": True, "tradein_no_drawer": True, "cancellation_adjustment": True, "atomic_rollback": True, "session_restored_after_posting_failure": posting_failure_restores_session, "leaked_fields": leaks}
	finally:
		frappe.db.set_single_value("Tecponto Settings", settings_before)
		frappe.set_user(previous_user)


def run_per_order_financial_summary_checks() -> dict:
	"""Prove the OS financial panel stays commercial outside the Director gate."""
	previous_user = frappe.session.user
	commission_enabled_before = frappe.db.get_single_value("Tecponto Settings", "use_technician_commission")
	try:
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		director = _find_or_create_user("Tecponto Diretor")
		technician = _find_or_create_user("Tecponto Tecnico")
		_ensure_default_test_cash_session(attendant)
		if frappe.db.exists("DocType", "Employee"):
			from tecponto_app.tecponto.hr import _ensure_default_gender, _ensure_employee_for_user, _get_default_company
			company = _get_default_company()
			gender = _ensure_default_gender()
			_ensure_employee_for_user(technician, company, gender)
		employee = frappe.db.get_value("Employee", {"user_id": technician, "status": "Active"}, "name")
		if not employee:
			raise AssertionError("Fundação não criou Employee ativo para a projeção financeira da OS.")

		order_name = _create_action_request_service_order(attendant)
		order = frappe.get_doc("Service Order", order_name)
		order.technician = technician
		order.services[0].technician = employee
		order.parts[0].valuation_rate = 63.5
		order.parts[0].outcome = "Usada no reparo"
		order.save(ignore_permissions=True)
		# ``gerar_nota`` reloads the order; persist the controlled cost fixture on
		# the child row rather than relying on an in-memory table value.
		frappe.db.set_value(
			"Service Order Part",
			order.parts[0].name,
			{"valuation_rate": 63.5, "outcome": "Usada no reparo"},
			update_modified=False,
		)
		frappe.db.set_value(
			"Service Order",
			order_name,
			{"workflow_state": "Pronto para retirada", "link_acceptance_required": 0, "sales_invoice": None},
			update_modified=False,
		)
		from tecponto_app.tecponto.service_order.billing import gerar_nota

		gerar_nota(frappe.get_doc("Service Order", order_name))
		order = frappe.get_doc("Service Order", order_name)
		# Billing may save/reload the parent table. Keep the controlled, used-part
		# fixture in the database before the Director projection is exercised.
		frappe.db.set_value(
			"Service Order Part",
			order.parts[0].name,
			{"valuation_rate": 63.5, "outcome": "Usada no reparo"},
			update_modified=False,
		)
		order = frappe.get_doc("Service Order", order_name)
		frappe.db.set_single_value("Tecponto Settings", "use_technician_commission", 1, update_modified=False)
		has_hrms = frappe.db.table_exists("Additional Salary")
		if has_hrms:
			_create_test_commission(employee, order.services[0].name, 24.0)

		frappe.set_user(attendant)
		receive_service_order_payment(
			order.name,
			{"kind": "regular", "amount": 100, "mode_of_payment": "Dinheiro", "idempotency_key": f"tp-os-finance-partial-{frappe.generate_hash(length=18)}"},
		)
		attendant_detail = get_service_order_detail(order.name)
		finance = attendant_detail["finance"]
		if finance["total_due"] <= 100 or finance["paid_total"] != 100 or finance["remaining_total"] != flt(finance["total_due"] - 100, 2):
			raise AssertionError("Resumo financeiro da OS não derivou corretamente o sinal e o saldo restante.")
		if not any(item["payment_mode"] == "Dinheiro" for item in finance["payments"]):
			raise AssertionError("Resumo financeiro da OS não trouxe a forma de pagamento registrada.")
		attendant_leaks = contains_sensitive_field(attendant_detail)
		if attendant_leaks:
			raise AssertionError(f"Detalhe comercial do Atendente vazou custo ou lucro: {', '.join(attendant_leaks)}")

		frappe.set_user(manager)
		manager_detail = get_service_order_detail(order.name)
		manager_leaks = contains_sensitive_field(manager_detail)
		if manager_leaks:
			raise AssertionError(f"Detalhe comercial do Gestor vazou custo ou lucro: {', '.join(manager_leaks)}")

		frappe.set_user(technician)
		technical_detail = get_service_order_detail(order.name)
		if any(technical_detail["finance"][key] for key in ("total_due", "paid_total", "remaining_total", "payments")):
			raise AssertionError("Técnico recebeu valores ou pagamentos no detalhe da OS.")

		blocked_roles = []
		for label, user in (("atendente", attendant), ("gestor", manager), ("tecnico", technician)):
			frappe.set_user(user)
			try:
				get_service_order_director_financial_summary(order.name)
			except frappe.PermissionError:
				blocked_roles.append(label)
			else:
				raise AssertionError(f"{label.title()} acessou custo ou lucro confidencial da OS.")

		frappe.set_user(director)
		director_finance = get_service_order_director_financial_summary(order.name)
		expected_labor = 24.0 if has_hrms else 0.0
		expected_total = 63.5 + expected_labor
		if director_finance["part_cost"] != 63.5 or director_finance["labor_cost_provisioned"] != expected_labor:
			raise AssertionError(f"Diretor não recebeu os custos reais de peça usada e mão de obra provisionada: {director_finance}")
		if director_finance["total_cost"] != expected_total or director_finance["gross_profit"] != flt(director_finance["revenue"] - expected_total, 2):
			raise AssertionError("Resultado bruto da OS não foi derivado dos custos reais.")

		frappe.set_user(attendant)
		remainder = receive_service_order_payment(
			order.name,
			{
				"kind": "regular",
				"amount": finance["remaining_total"],
				"mode_of_payment": "Pix",
				"idempotency_key": f"tp-os-finance-settled-{frappe.generate_hash(length=18)}",
			},
		)
		settled = remainder["detail"]["finance"]
		if settled["remaining_total"] != 0 or settled["paid_total"] != settled["total_due"]:
			raise AssertionError("Resumo financeiro da OS não marcou a quitação após o pagamento final.")
		return {
			"status": "ok",
			"partial_balance": finance["remaining_total"],
			"settled": True,
			"director_costs": {"parts": director_finance["part_cost"], "labor": director_finance["labor_cost_provisioned"]},
			"blocked_roles": blocked_roles,
			"attendant_leaks": attendant_leaks,
			"manager_leaks": manager_leaks,
		}
	finally:
		frappe.db.set_single_value("Tecponto Settings", "use_technician_commission", commission_enabled_before, update_modified=False)
		frappe.set_user(previous_user)


def run_technician_part_request_checks() -> dict:
	"""Prove 3.14-1: technician requests part needs without seeing cost or other people's requests."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		technician = _find_or_create_user("Tecponto Tecnico")
		attendant = _find_or_create_user("Tecponto Atendente")
		peer = _find_or_create_commission_peer()
		repair_item = _ensure_part_request_repair_item()

		catalog_order = _create_action_request_service_order(attendant)
		free_order = _create_action_request_service_order(attendant)
		peer_order = _create_action_request_service_order(attendant)
		for order_name, assignee in ((catalog_order, technician), (free_order, technician), (peer_order, peer)):
			order = frappe.get_doc("Service Order", order_name)
			order.set("parts", [])
			order.save(ignore_permissions=True)
			frappe.db.set_value(
				"Service Order",
				order_name,
				{"technician": assignee, "workflow_state": "Aprovado"},
				update_modified=False,
			)
		frappe.db.commit()

		frappe.set_user(technician)
		options = search_repair_part_options(query="Solicitacao Tecnica", limit=10)
		if repair_item not in {item["item_code"] for item in options["items"]}:
			raise AssertionError("Busca segura de pecas de Reparo nao retornou o item de teste.")
		catalog_request = create_technical_part_request(
			service_order=catalog_order,
			item=repair_item,
			qty=2,
			notes="Peca catalogada solicitada pela suite.",
		)
		if frappe.db.get_value("Service Order", catalog_order, "workflow_state") != "Aguardando peça":
			raise AssertionError("Solicitacao catalogada nao moveu a OS para Aguardando peca.")
		free_request = create_technical_part_request(
			service_order=free_order,
			free_description="Flex compativel ainda sem cadastro",
			qty=1,
			notes="Pedido livre sem travar a OS.",
		)
		if frappe.db.get_value("Service Order", free_order, "workflow_state") != "Aguardando peça":
			raise AssertionError("Solicitacao livre nao moveu a OS para Aguardando peca.")
		own_payload = list_my_technical_part_requests(limit=100)
		own_names = {item["name"] for item in own_payload["items"]}
		if catalog_request["name"] not in own_names or free_request["name"] not in own_names:
			raise AssertionError("Tecnico nao encontrou as proprias solicitacoes de peca.")
		leaks = contains_sensitive_field({"options": options, "requests": own_payload})
		if leaks:
			raise AssertionError(f"Solicitacao de peca vazou campo sensivel: {', '.join(leaks)}")

		frappe.set_user(peer)
		peer_request = create_technical_part_request(
			service_order=peer_order,
			free_description="Peca do tecnico de controle",
			qty=1,
			notes="Nao pode aparecer para outro tecnico.",
		)
		frappe.set_user(technician)
		scoped_names = {item["name"] for item in list_my_technical_part_requests(limit=200)["items"]}
		if peer_request["name"] in scoped_names:
			raise AssertionError("Tecnico visualizou solicitacao criada por outro tecnico.")
		other_order_blocked = False
		try:
			create_technical_part_request(
				service_order=peer_order,
				free_description="Tentativa em OS alheia",
				qty=1,
			)
		except frappe.PermissionError:
			other_order_blocked = True
		if not other_order_blocked:
			raise AssertionError("Tecnico conseguiu solicitar peca para OS alheia.")

		frappe.set_user(attendant)
		attendant_blocked = False
		try:
			list_my_technical_part_requests(limit=1)
		except frappe.PermissionError:
			attendant_blocked = True
		if not attendant_blocked:
			raise AssertionError("Atendente acessou solicitacoes tecnicas de peca.")

		return {
			"catalog_request": catalog_request["name"],
			"free_request": free_request["name"],
			"catalog_order_state": frappe.db.get_value("Service Order", catalog_order, "workflow_state"),
			"free_order_state": frappe.db.get_value("Service Order", free_order, "workflow_state"),
			"peer_request_hidden": peer_request["name"] not in scoped_names,
			"other_order_blocked": other_order_blocked,
			"attendant_blocked": attendant_blocked,
			"leaked_fields": leaks,
		}
	finally:
		frappe.set_user(previous_user)


def run_part_purchase_cycle_checks() -> dict:
	"""Prove 3.14-2: buyer queue, ordering, statuses and approval above threshold."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		technician = _find_or_create_user("Tecponto Tecnico")
		attendant = _find_or_create_user("Tecponto Atendente")
		manager = _find_or_create_user("Tecponto Gestor")
		director = _find_or_create_user("Tecponto Diretor")
		supplier = _ensure_part_request_supplier()
		repair_item = _ensure_part_request_repair_item()
		previous_threshold = frappe.db.get_single_value("Tecponto Settings", "purchase_approval_threshold")
		frappe.db.set_single_value("Tecponto Settings", "purchase_approval_threshold", 100)

		marker = f"3142-{now_datetime().strftime('%H%M%S%f')}"
		urgent_order = _create_action_request_service_order(attendant)
		later_order = _create_action_request_service_order(attendant)
		receivable_order = _create_action_request_service_order(attendant)
		expensive_order = _create_action_request_service_order(attendant)
		for order_name, deadline in (
			(urgent_order, add_days(today(), 1)),
			(later_order, add_days(today(), 5)),
			(receivable_order, add_days(today(), 3)),
			(expensive_order, add_days(today(), 2)),
		):
			order = frappe.get_doc("Service Order", order_name)
			order.set("parts", [])
			order.save(ignore_permissions=True)
			frappe.db.set_value(
				"Service Order",
				order_name,
				{"technician": technician, "workflow_state": "Aprovado", "estimated_deadline": deadline},
				update_modified=False,
			)
		frappe.db.commit()

		frappe.set_user(technician)
		later_request = create_technical_part_request(later_order, item=repair_item, qty=1, notes=f"{marker} later")
		urgent_request = create_technical_part_request(urgent_order, item=repair_item, qty=1, notes=f"{marker} urgent")
		receivable_request = create_technical_part_request(receivable_order, free_description=f"{marker} receber livre", qty=1)
		expensive_request = create_technical_part_request(expensive_order, item=repair_item, qty=1, notes=f"{marker} expensive")

		technician_blocked = False
		try:
			list_purchase_part_requests(query=marker)
		except frappe.PermissionError:
			technician_blocked = True
		if not technician_blocked:
			raise AssertionError("Tecnico acessou fila de compras.")

		frappe.set_user(director)
		queue = list_purchase_part_requests(query=marker, status="open", limit=10)
		ordered_names = [item["name"] for item in queue["items"]]
		if ordered_names.index(urgent_request["name"]) > ordered_names.index(later_request["name"]):
			raise AssertionError("Lista de compras nao ordenou pelo prazo prometido da OS.")
		cheap = mark_part_request_ordered(urgent_request["name"], supplier=supplier, expected_arrival=add_days(today(), 2), estimated_cost=50)
		if cheap["status"] != "Pedida":
			raise AssertionError("Compra abaixo do teto nao marcou como Pedida.")
		blocked_expensive = False
		try:
			mark_part_request_ordered(expensive_request["name"], supplier=supplier, expected_arrival=add_days(today(), 2), estimated_cost=150)
		except frappe.PermissionError:
			blocked_expensive = True
		if not blocked_expensive:
			raise AssertionError("Compra acima do teto passou sem aprovacao.")
		frappe.db.commit()
		approval = create_request(
			"part_purchase_above_threshold",
			expensive_request["name"],
			"Compra urgente para cumprir prazo do cliente.",
			{"supplier": supplier, "expected_arrival": str(add_days(today(), 2)), "estimated_cost": 150},
		)

		frappe.set_user(manager)
		approved = approve_request(approval["name"])
		if frappe.db.get_value("Tecponto Part Request", expensive_request["name"], "status") != "Pedida":
			raise AssertionError("Aprovacao nao executou a marcacao Pedida.")
		received = mark_part_request_ordered(receivable_request["name"], supplier=supplier, expected_arrival=add_days(today(), 1), estimated_cost=10)
		received = mark_part_request_received(received["name"], item=repair_item)
		if received["status"] != "Recebida" or not received["received_at"]:
			raise AssertionError("Marcacao Recebida nao gravou received_at.")
		cancelled = cancel_part_request(later_request["name"], "Fornecedor indisponivel no teste.")
		if cancelled["status"] != "Cancelada" or not cancelled["cancellation_reason"]:
			raise AssertionError("Cancelamento nao gravou motivo.")

		frappe.set_user(technician)
		own_payload = list_my_technical_part_requests(limit=200)
		leaks = contains_sensitive_field(own_payload)
		if leaks:
			raise AssertionError(f"Tecnico recebeu custo ou campo sensivel na solicitacao de peca: {', '.join(leaks)}")

		return {
			"ordered_by_urgency": ordered_names[:2],
			"cheap_status": cheap["status"],
			"expensive_blocked": blocked_expensive,
			"approval": approved["name"],
			"received_at": received["received_at"],
			"cancelled": cancelled["name"],
			"technician_blocked_from_purchase_queue": technician_blocked,
			"leaked_fields": leaks,
		}
	finally:
		if "previous_threshold" in locals():
			frappe.db.set_single_value("Tecponto Settings", "purchase_approval_threshold", previous_threshold or 0)
		frappe.set_user(previous_user)


def run_part_receipt_reservation_checks() -> dict:
	"""Prove 3.14-3 receipt, native reservation, notice and waiting-part SLA."""
	previous_user = frappe.session.user
	previous_in_test = frappe.flags.in_test
	try:
		frappe.flags.in_test = True
		# Foundation provisions native ERPNext records; keep this independent from
		# whatever role a preceding integration scenario left in the session.
		frappe.set_user("Administrator")
		ensure_frontend_foundation()
		technician = _find_or_create_user("Tecponto Tecnico")
		buyer = _find_or_create_user("Tecponto Gestor")
		supplier = _ensure_part_request_supplier()
		item = _ensure_part_request_repair_item()
		warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
		if not warehouse:
			raise AssertionError("Fixture sem depósito de Reparo.")
		marker = f"3143-{now_datetime().strftime('%H%M%S%f')}"
		available_before = flt(get_available_qty_to_reserve(item, warehouse))
		qty = available_before + 1
		attendant = _find_or_create_user("Tecponto Atendente")
		origin_order = _create_action_request_service_order(attendant)
		other_order = _create_action_request_service_order(attendant)
		blank_order = _create_action_request_service_order(attendant)
		for order_name in (origin_order, other_order, blank_order):
			frappe.db.set_value("Service Order", order_name, {"technician": technician, "workflow_state": "Aprovado"}, update_modified=False)
		frappe.db.commit()

		frappe.set_user(technician)
		receipt_request = create_technical_part_request(origin_order, item=item, qty=qty, notes=marker)
		blank_request = create_technical_part_request(blank_order, item=item, qty=1, notes=f"{marker}-blank")
		frappe.set_user(buyer)
		mark_part_request_ordered(receipt_request["name"], supplier=supplier, expected_arrival=add_days(today(), -1), estimated_cost=50)
		# Pedida without supplier promise is allowed in persisted legacy data and must
		# not generate a synthetic stage alarm.
		frappe.db.set_value("Tecponto Part Request", blank_request["name"], {"status": "Pedida", "expected_arrival": None}, update_modified=False)
		frappe.db.commit()
		late_clock = get_stage_clock(frappe.get_doc("Service Order", origin_order))
		blank_clock = get_stage_clock(frappe.get_doc("Service Order", blank_order))
		if not late_clock["is_stage_overdue"] or not late_clock["waiting_part_expected_arrival"]:
			raise AssertionError("Previsão vencida não marcou atraso na etapa Aguardando peça.")
		if blank_clock["is_stage_overdue"] or blank_clock["waiting_part_expected_arrival"]:
			raise AssertionError("Solicitação sem previsão gerou alerta falso de atraso.")

		notifications_before = frappe.db.count("Tecponto Notification", {"recipient": technician, "template_key": "part_received", "reference_name": receipt_request["name"]})
		received = mark_part_request_received(receipt_request["name"])
		if received["status"] != "Recebida" or not received["stock_entry"] or not received["reservation"]:
			raise AssertionError("Recebimento não gravou entrada e reserva nativas.")
		if not frappe.db.exists("Stock Entry", received["stock_entry"]) or not frappe.db.exists("Stock Reservation Entry", received["reservation"]):
			raise AssertionError("Documento de entrada ou reserva não foi persistido.")
		reservation = frappe.get_doc("Stock Reservation Entry", received["reservation"])
		if reservation.voucher_no != origin_order or flt(reservation.reserved_qty) != qty:
			raise AssertionError("Reserva não ficou vinculada à OS de origem.")
		if frappe.db.count("Tecponto Notification", {"recipient": technician, "template_key": "part_received", "reference_name": receipt_request["name"]}) != notifications_before + 1:
			raise AssertionError("Técnico não recebeu notificação assíncrona da peça recebida.")
		available_after_reservation = flt(get_available_qty_to_reserve(item, warehouse))

		other = frappe.get_doc("Service Order", other_order)
		other.append("parts", {"item_code": item, "qty": qty, "warehouse": warehouse, "technician": technician, "outcome": "Usada no reparo"})
		other_blocked = False
		try:
			other.save(ignore_permissions=True)
		except frappe.ValidationError:
			other_blocked = True
		if not other_blocked:
			raise AssertionError(
			f"Outra OS consumiu a disponibilidade reservada sem liberação do Gestor (antes={available_before}, reserva={reservation.reserved_qty}, depois={available_after_reservation}, pedido={qty})."
		)

		return {
			"receipt": receipt_request["name"],
			"stock_entry": received["stock_entry"],
			"reservation": received["reservation"],
			"technician_notified": True,
			"overdue_from_expected_arrival": late_clock["is_stage_overdue"],
			"blank_expected_arrival_has_no_alert": not blank_clock["is_stage_overdue"],
			"other_order_blocked": other_blocked,
		}
	finally:
		frappe.flags.in_test = previous_in_test
		frappe.set_user(previous_user)


def _find_or_create_commission_peer() -> str:
	user = "front-tecnico-comissao@tecponto.local"
	if not frappe.db.exists("User", user):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": user,
				"first_name": "Tecnico",
				"last_name": "Comissao",
				"enabled": 1,
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Has Role", {"parent": user, "parenttype": "User", "role": "Tecponto Tecnico"}):
		frappe.get_doc("User", user).append("roles", {"role": "Tecponto Tecnico"}).save(ignore_permissions=True)
	return user


def _assign_commission_service(order_name: str, technician: str, employee: str) -> str:
	doc = frappe.get_doc("Service Order", order_name)
	doc.technician = technician
	doc.services[0].technician = employee
	doc.save(ignore_permissions=True)
	return doc.services[0].name


def _create_test_commission(employee: str, service_row: str, amount: float) -> str:
	if not frappe.db.table_exists("Additional Salary"):
		return ""
	existing = frappe.db.get_value(
		"Additional Salary",
		{"ref_doctype": "Service Order Service", "ref_docname": service_row, "salary_component": "Comissão"},
		"name",
	)
	if existing:
		return existing
	company = frappe.db.get_value("Employee", employee, "company") or frappe.defaults.get_global_default("company")
	name = f"TST-COMM-{frappe.generate_hash(length=10).upper()}"
	# This fixture exercises only the read projection. HRMS correctly refuses a
	# normal insert without a Salary Structure Assignment, which is unrelated to
	# the technician-scope contract under test.
	frappe.db.sql(
		"""
		insert into `tabAdditional Salary`
			(name, owner, creation, modified, modified_by, docstatus, idx,
			employee, company, salary_component, type, payroll_date, currency,
			amount, ref_doctype, ref_docname)
		values
			(%(name)s, 'Administrator', %(now)s, %(now)s, 'Administrator', 1, 0,
			%(employee)s, %(company)s, 'Comissão', 'Earning', %(payroll_date)s, 'BRL',
			%(amount)s, 'Service Order Service', %(service_row)s)
		""",
		{
			"name": name,
			"now": now_datetime(),
			"employee": employee,
			"company": company,
			"payroll_date": nowdate(),
			"amount": amount,
			"service_row": service_row,
		},
	)
	return name


def _ensure_part_request_supplier() -> str:
	name = "Fornecedor Teste Pecas Tecponto"
	if frappe.db.exists("Supplier", name):
		return name
	frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": name,
			"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name") or "All Supplier Groups",
			"supplier_type": "Company",
		}
	).insert(ignore_permissions=True)
	return name


def _ensure_part_request_repair_item() -> str:
	group = "Peças de Reparo"
	if not frappe.db.exists("Item Group", group):
		frappe.get_doc(
			{
				"doctype": "Item Group",
				"item_group_name": group,
				"parent_item_group": "All Item Groups",
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
	item_code = "TP-REQ-PECA-TECNICA"
	values = {
		"item_name": "Peca Solicitacao Tecnica",
		"item_group": group,
		"stock_uom": "Nos",
		"is_stock_item": 1,
		"disabled": 0,
	}
	if frappe.db.exists("Item", item_code):
		frappe.db.set_value("Item", item_code, values, update_modified=False)
	else:
		frappe.get_doc({"doctype": "Item", "item_code": item_code, **values}).insert(ignore_permissions=True)
	return item_code


def _create_technician_scope_customer_device(label: str) -> tuple[str, str, str, str]:
	"""Create isolated customer/device data for the technical privacy regression test."""
	token = frappe.generate_hash(length=10).upper()
	customer_label = f"Cliente Escopo Técnico {label} {token}"
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": customer_label,
			"customer_type": "Individual",
			"mobile_no": "11999990000",
			"custom_whatsapp": "11999990000",
			"custom_cpf": "",
			"custom_rg": f"RG-{token}",
			CUSTOMER_NO_CPF_FIELD: 1,
			"email_id": f"{token.lower()}@privado.tecponto.local",
		}
	)
	customer.insert(ignore_permissions=True)
	imei = f"359{frappe.generate_hash(length=12).upper()}"
	device = frappe.get_doc(
		{
			"doctype": "Customer Device",
			"customer": customer.name,
			"brand": "Tecponto",
			"model": f"Teste escopo {label}",
			"imei_serial": imei,
			"registration_date": nowdate(),
		}
	)
	device.insert(ignore_permissions=True)
	return customer.name, device.name, customer_label, imei


def run_used_device_warranty_lookup_checks() -> dict:
	"""The used-device warranty lookup is operational data, never a public IMEI oracle."""
	previous_user = frappe.session.user
	try:
		ensure_frontend_foundation()
		attendant = _find_or_create_user("Tecponto Atendente")
		technician = _find_or_create_user("Tecponto Tecnico")
		customer = _get_or_create_demo_customer()
		serial_no = f"TP-UDW-GUARD-{frappe.generate_hash(length=12)}"
		warranty = frappe.get_doc(
			{
				"doctype": "Used Device Warranty",
				"serial_no": serial_no,
				"customer": customer,
				"item_code": _get_demo_item(is_stock_item=1),
				"sales_invoice": "TEST-USED-WARRANTY",
				"sale_date": nowdate(),
				"warranty_days": 90,
				"warranty_expiry": add_days(nowdate(), 90),
				"coverage": "Defeito de fábrica",
			}
		)
		warranty.insert(ignore_permissions=True, ignore_links=True)
		frappe.db.commit()

		frappe.set_user(attendant)
		allowed = consultar_garantia_usado(serial_no)
		if not allowed.get("exists") or allowed.get("name") != warranty.name:
			raise AssertionError("Atendente não consultou a garantia de aparelho usado autorizada.")

		blocked_users = {"technician": technician, "guest": "Guest"}
		for label, user in blocked_users.items():
			frappe.set_user(user)
			try:
				consultar_garantia_usado(serial_no)
			except frappe.PermissionError:
				continue
			raise AssertionError(f"Consulta de garantia aceitou indevidamente {label}.")

		return {
			"warranty": warranty.name,
			"attendant_allowed": True,
			"technician_blocked": True,
			"guest_blocked": True,
		}
	finally:
		frappe.set_user(previous_user)


def _check_statbar_guard(user: str) -> dict:
	"""The operational counters may expose sales totals, never cost or profitability."""
	frappe.set_user(user)
	payload = {
		"service_orders": get_service_order_statbar(),
		"customers": get_list_statbar("customers"),
		"trades": get_list_statbar("trades"),
		"repair_parts": get_list_statbar("stock:repair-parts"),
		"commercial_products": get_list_statbar("stock:commercial-products"),
		"sales": get_list_statbar("sales"),
		"catalog": get_list_statbar("catalog"),
	}
	leaks = contains_sensitive_field(payload)
	if leaks:
		raise AssertionError(f"StatBar expôs campos sensíveis: {', '.join(leaks)}")
	allowed_keys = {"key", "label", "value", "amount"}
	for scope, response in payload.items():
		for item in response["items"]:
			unexpected = set(item) - allowed_keys
			if unexpected:
				raise AssertionError(f"StatBar {scope} retornou campos fora da projeção segura: {sorted(unexpected)}")
			if scope != "sales" and "amount" in item:
				raise AssertionError(f"StatBar {scope} retornou valor financeiro indevido.")
	return {
		"checked_scopes": sorted(payload),
		"leaked_fields": leaks,
	}


def _check_manager_home_guard(user: str) -> dict:
	"""Manager home is revenue/volume-only; purchase queue is the sole cost exception."""
	previous_user = frappe.session.user
	try:
		frappe.set_user(user)
		home_payload = {
			"dashboard": get_dashboard_metrics(),
			"service_orders": get_service_order_statbar(),
			"sales": get_list_statbar("sales"),
			"repair_stock": get_list_statbar("stock:repair-parts"),
			"commercial_stock": get_list_statbar("stock:commercial-products"),
			"trades": get_list_statbar("trades"),
			"sales_list": list_sales(limit=10),
		}
		leaks = contains_sensitive_field(home_payload)
		if leaks:
			raise AssertionError(f"Home do Gestor expôs campo sensível: {', '.join(leaks)}")

		purchase_queue = list_purchase_part_requests(status="all", limit=10)
		queue_without_estimated_cost = {
			**purchase_queue,
			"items": [
				{key: value for key, value in item.items() if key != "estimated_cost"}
				for item in purchase_queue["items"]
			],
		}
		queue_leaks = contains_sensitive_field(queue_without_estimated_cost)
		if queue_leaks:
			raise AssertionError(f"Fila de compras do Gestor expôs campo sensível fora da exceção: {', '.join(queue_leaks)}")
		if any("estimated_cost" not in item for item in purchase_queue["items"]):
			raise AssertionError("A fila de compras deixou de projetar o custo estimado autorizado ao Gestor.")

		commission_blocked = False
		try:
			list_my_commissions()
		except frappe.PermissionError:
			commission_blocked = True
		if not commission_blocked:
			raise AssertionError("Gestor acessou comissão individual por endpoint técnico.")

		return {
			"home_leaked_fields": leaks,
			"purchase_queue_exception": "estimated_cost_only",
			"purchase_queue_leaked_fields": queue_leaks,
			"third_party_commissions": "blocked",
		}
	finally:
		frappe.set_user(previous_user)

def _check_director_financial_guard(director: str, manager: str, technician: str, attendant: str) -> dict:
	"""Director-only financial projection; other operational roles must be denied."""
	previous_user = frappe.session.user
	try:
		frappe.set_user(director)
		payload = get_director_financial_summary()
		expected = {
			"period",
			"revenue",
			"operational_cost",
			"retail_cost",
			"service_part_cost",
			"gross_operating_profit",
			"gross_margin_pct",
			"team_earnings_accrued",
			"technician_commissions_enabled",
			"net_profit_available",
		}
		if set(payload) != expected:
			raise AssertionError(f"Resumo financeiro do Diretor retornou campos inesperados: {sorted(set(payload) - expected)}")
		if payload["net_profit_available"]:
			raise AssertionError("Resultado financeiro foi rotulado como lucro liquido sem despesas completas.")

		blocked_roles = []
		for label, user in (("gestor", manager), ("tecnico", technician), ("atendente", attendant)):
			frappe.set_user(user)
			try:
				get_director_financial_summary()
			except frappe.PermissionError:
				blocked_roles.append(label)
			else:
				raise AssertionError(f"{label.title()} acessou o endpoint financeiro exclusivo do Diretor.")
		return {
			"director_sees": sorted(expected - {"period", "net_profit_available"}),
			"blocked_roles": blocked_roles,
			"net_profit_available": payload["net_profit_available"],
		}
	finally:
		frappe.set_user(previous_user)


def _check_director_strategic_report_guard(director: str, manager: str, technician: str, attendant: str) -> dict:
	"""Strategic cost, margin and team earnings remain Director-only."""
	previous_user = frappe.session.user
	try:
		frappe.set_user(director)
		payload = get_director_strategic_report("month")
		expected = {"period", "technician_commissions_enabled", "categories", "technicians", "item_costs", "service_order_costs", "trend"}
		if set(payload) != expected:
			raise AssertionError("Relatorio estrategico retornou uma projeção inesperada.")
		for row in payload["categories"]:
			if set(row) != {"category", "revenue"}:
				raise AssertionError("Categoria estrategica retornou campos inesperados.")
		for row in payload["technicians"]:
			if set(row) != {"technician", "service_orders", "labor_revenue", "team_earnings"}:
				raise AssertionError("Desempenho tecnico retornou campos inesperados.")
		for row in payload["item_costs"]:
			if set(row) != {"item_code", "item_name", "cost"}:
				raise AssertionError("Custo por produto retornou campos inesperados.")
		for row in payload["service_order_costs"]:
			if set(row) != {"service_order", "cost"}:
				raise AssertionError("Custo por OS retornou campos inesperados.")

		blocked_roles = []
		for label, user in (("gestor", manager), ("tecnico", technician), ("atendente", attendant)):
			frappe.set_user(user)
			try:
				get_director_strategic_report("month")
			except frappe.PermissionError:
				blocked_roles.append(label)
			else:
				raise AssertionError(f"{label.title()} acessou o relatorio estrategico exclusivo do Diretor.")
		return {
			"period": payload["period"]["key"],
			"director_fields": sorted(expected - {"period"}),
			"blocked_roles": blocked_roles,
		}
	finally:
		frappe.set_user(previous_user)


def _check_director_risk_agenda_guard(director: str, manager: str, technician: str, attendant: str) -> dict:
	"""Executive risks are Director-only and never include sensitive values by accident."""
	previous_user = frappe.session.user
	try:
		frappe.set_user(director)
		payload = get_director_risk_agenda()
		if set(payload) != {"items", "count", "risk_count"}:
			raise AssertionError("Agenda executiva retornou uma projeção inesperada.")
		leaks = contains_sensitive_field(payload)
		if leaks:
			raise AssertionError(f"Agenda executiva expôs dado financeiro fora do recorte: {', '.join(leaks)}")
		for item in payload["items"]:
			unexpected = set(item) - {
				"key", "kind", "tone", "title", "description", "urgency", "urgency_sort_at",
				"group_key", "group_label", "link", "reference_doctype", "reference_name",
				"selling_total",
			}
			if unexpected:
				raise AssertionError(f"Agenda executiva retornou campos fora da projeção: {sorted(unexpected)}")

		blocked_roles = []
		for label, user in (("gestor", manager), ("tecnico", technician), ("atendente", attendant)):
			frappe.set_user(user)
			try:
				get_director_risk_agenda()
			except frappe.PermissionError:
				blocked_roles.append(label)
			else:
				raise AssertionError(f"{label.title()} acessou a agenda executiva exclusiva do Diretor.")
		return {"director_visible": True, "blocked_roles": blocked_roles, "leaked_fields": leaks}
	finally:
		frappe.set_user(previous_user)


def _check_manager_operation_scope(manager: str, attendant: str) -> dict:
	"""Workload is a management-only, non-financial operational projection."""
	previous_user = frappe.session.user
	try:
		frappe.set_user(manager)
		payload = get_technician_workload()
		leaks = contains_sensitive_field(payload)
		if leaks:
			raise AssertionError(f"Carga por técnico expôs dado sensível: {', '.join(leaks)}")
		for item in payload["items"]:
			unexpected = set(item) - {"technician", "technician_name", "active_orders", "in_diagnosis", "waiting_part", "overdue"}
			if unexpected:
				raise AssertionError(f"Carga por técnico retornou campos fora da projeção: {sorted(unexpected)}")

		frappe.set_user(attendant)
		attendant_blocked = False
		try:
			get_technician_workload()
		except frappe.PermissionError:
			attendant_blocked = True
		if not attendant_blocked:
			raise AssertionError("Atendente acessou a carga de técnicos da loja.")

		return {
			"manager_visible": True,
			"technicians": len(payload["items"]),
			"attendant_blocked": True,
			"leaked_fields": leaks,
		}
	finally:
		frappe.set_user(previous_user)


def _check_management_stock_scope_routing(manager: str, director: str) -> dict:
	"""Management stock navigation must keep Reparo and Comercial physically separate."""
	previous_user = frappe.session.user
	try:
		repair_warehouse = frappe.db.get_single_value("Tecponto Settings", "repair_warehouse")
		commercial_warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
		if not repair_warehouse or not commercial_warehouse:
			raise AssertionError("Depósitos de Reparo e Comercial precisam estar configurados.")

		# ERPNext creates a native Item Price while seeding the fixture. This is setup
		# only; the assertions below always execute as Gestor and Diretor.
		frappe.set_user("Administrator")
		repair_item = _ensure_part_request_repair_item()
		_ensure_pos_demo_stock(repair_item, repair_warehouse, valuation_rate=10)
		commercial_item = _ensure_pos_demo_records()["items"][0]

		checked_roles = []
		for role, user in (("manager", manager), ("director", director)):
			frappe.set_user(user)
			repair = list_stock_items(query=repair_item, limit=5, scope="repair-parts")
			commercial = list_stock_items(query=commercial_item, limit=5, scope="commercial-products")
			if not repair["items"] or any(row["warehouse"] != repair_warehouse for row in repair["items"]):
				raise AssertionError(f"{role.title()} não recebeu o estoque exclusivo de Reparo.")
			if not commercial["items"] or any(row["warehouse"] != commercial_warehouse for row in commercial["items"]):
				raise AssertionError(f"{role.title()} não recebeu o estoque exclusivo Comercial.")
			leaks = contains_sensitive_field({"repair": repair, "commercial": commercial})
			if leaks:
				raise AssertionError(f"Estoque gerencial expôs campos sensíveis: {', '.join(leaks)}")
			checked_roles.append(role)

		return {
			"roles": checked_roles,
			"repair_warehouse": repair_warehouse,
			"commercial_warehouse": commercial_warehouse,
			"leaked_fields": [],
		}
	finally:
		frappe.set_user(previous_user)


def _check_budget_item_cost_guard(user: str) -> dict:
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		item_code = _get_or_create_budget_cost_guard_item()
		frappe.db.commit()

		frappe.set_user(user)
		payload = search_budget_items(query=item_code, line_type="part", limit=5)
		leaks = contains_sensitive_field(payload, forbidden_values={BUDGET_COST_GUARD_VALUATION})
		if leaks:
			raise AssertionError(f"Custo de item vazou na busca de orÃ§amento: {', '.join(leaks)}")

		item = next((entry for entry in payload["items"] if entry["item_code"] == item_code), None)
		if not item:
			raise AssertionError("Item sentinela de custo nÃ£o retornou na busca de orÃ§amento.")
		if flt(item.get("standard_rate")) != 0:
			raise AssertionError("Item sem preÃ§o de venda deveria retornar standard_rate 0, sem fallback de custo.")
		if item.get("has_price"):
			raise AssertionError("Item sem preÃ§o de venda deveria retornar has_price=false.")

		return {
			"user": user,
			"checked_payload": "search_budget_items",
			"item": item_code,
			"cost_value_checked": True,
			"returned_standard_rate": item.get("standard_rate"),
			"has_price": item.get("has_price"),
			"leaked_fields": leaks,
		}
	finally:
		frappe.set_user(previous_user)


def _get_or_create_budget_cost_guard_item() -> str:
	item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
	stock_uom = frappe.db.get_value("UOM", {"enabled": 1}, "name") or frappe.db.get_value("UOM", {}, "name") or "Nos"
	if frappe.db.exists("Item", BUDGET_COST_GUARD_ITEM):
		item = frappe.get_doc("Item", BUDGET_COST_GUARD_ITEM)
	else:
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": BUDGET_COST_GUARD_ITEM,
				"item_name": "Sentinela guard custo frontend",
				"item_group": item_group,
				"stock_uom": stock_uom,
				"is_stock_item": 1,
				"disabled": 0,
			}
		)
	item.disabled = 0
	item.is_stock_item = 1
	item.item_group = item_group
	item.stock_uom = stock_uom
	item.standard_rate = 0
	item.valuation_rate = BUDGET_COST_GUARD_VALUATION
	if item.is_new():
		item.insert(ignore_permissions=True)
	else:
		item.save(ignore_permissions=True)
	return item.name


def _check_pos_item_cost_guard(user: str, blocked_user: str) -> dict:
	previous_user = frappe.session.user
	try:
		frappe.set_user("Administrator")
		demo = _ensure_pos_demo_records()
		frappe.db.commit()

		frappe.set_user(user)
		if "Sales User" in frappe.get_roles(user):
			raise AssertionError("Atendente do PDV não pode receber a role Sales User.")

		barcode_payload = search_pos_items(barcode=POS_BARCODE_VALUE, limit=1)
		name_payload = search_pos_items(query="Película 3D", limit=5)
		missing_payload = search_pos_items(barcode="0000000000000", limit=1)
		payload = {
			"barcode": barcode_payload,
			"name": name_payload,
			"missing": missing_payload,
		}
		leaks = contains_sensitive_field(payload, forbidden_values=set(demo["valuation_rates"]))
		if leaks:
			raise AssertionError(f"Custo de item vazou na consulta do PDV: {', '.join(leaks)}")

		barcode_item = next(
			(entry for entry in barcode_payload["items"] if entry["item_code"] == POS_BARCODE_ITEM),
			None,
		)
		name_item = next(
			(entry for entry in name_payload["items"] if entry["item_code"] == POS_NAME_ITEM),
			None,
		)
		if not barcode_item:
			raise AssertionError("Busca do PDV por barcode não encontrou o item de teste.")
		if not name_item:
			raise AssertionError("Busca do PDV por nome não encontrou o item de teste.")
		if missing_payload["items"]:
			raise AssertionError("Barcode inexistente não deveria retornar produto.")
		if {barcode_item["warehouse"], name_item["warehouse"]} != {demo["commercial_warehouse"]}:
			raise AssertionError("Consulta do PDV retornou item fora do depósito Comercial.")
		if flt(barcode_item["standard_rate"]) != 79.90 or flt(name_item["standard_rate"]) != 35.50:
			raise AssertionError("Consulta do PDV não retornou os preços de venda esperados.")
		if barcode_item["item_group"] != "Cabos" or name_item["item_group"] != "Películas":
			raise AssertionError("Busca do PDV retornou massa de teste fora dos grupos comerciais corretos.")

		frappe.set_user(blocked_user)
		blocked = False
		try:
			search_pos_items(barcode=POS_BARCODE_VALUE, limit=1)
		except frappe.PermissionError:
			blocked = True
		if not blocked:
			raise AssertionError("Técnico não pode acessar a consulta operacional do PDV.")

		return {
			"user": user,
			"sales_user": False,
			"blocked_user": blocked_user,
			"blocked_by_backend": blocked,
			"commercial_warehouse": demo["commercial_warehouse"],
			"barcode_item": barcode_item["item_code"],
			"barcode_item_group": barcode_item["item_group"],
			"name_item": name_item["item_code"],
			"name_item_group": name_item["item_group"],
			"missing_barcode_count": len(missing_payload["items"]),
			"checked_payload": "search_pos_items",
			"leaked_fields": leaks,
		}
	finally:
		frappe.set_user(previous_user)


def _ensure_pos_demo_records() -> dict:
	warehouse = frappe.db.get_single_value("Tecponto Settings", "commercial_warehouse")
	if not warehouse:
		raise AssertionError("Depósito Comercial precisa estar configurado para testar o PDV.")

	stock_uom = frappe.db.get_value("UOM", {"enabled": 1}, "name") or frappe.db.get_value("UOM", {}, "name") or "Nos"
	items = []
	valuation_rates = []
	for item_code, item_name, item_group, selling_rate, valuation_rate, barcode in POS_DEMO_ITEMS:
		if not frappe.db.exists("Item Group", item_group):
			raise AssertionError(f"Grupo comercial {item_group} precisa existir para testar o PDV.")
		item = _ensure_pos_demo_item(
			item_code=item_code,
			item_name=item_name,
			item_group=item_group,
			stock_uom=stock_uom,
			selling_rate=selling_rate,
			barcode=barcode,
		)
		_ensure_pos_demo_stock(item.name, warehouse, valuation_rate)
		items.append(item.name)
		valuation_rates.append(valuation_rate)

	return {
		"commercial_warehouse": warehouse,
		"items": items,
		"barcode": POS_BARCODE_VALUE,
		"valuation_rates": valuation_rates,
	}


def _ensure_cashier_operator(user: str, *, badge_code: str, pin: str):
	if frappe.db.exists("Tecponto Cashier Operator", user):
		operator = frappe.get_doc("Tecponto Cashier Operator", user)
	else:
		operator = frappe.new_doc("Tecponto Cashier Operator")
		operator.user = user
	operator.active = 1
	operator.badge_code = badge_code
	operator.pin = pin
	operator.save(ignore_permissions=True)
	return operator


def _ensure_pos_demo_item(
	*,
	item_code: str,
	item_name: str,
	item_group: str,
	stock_uom: str,
	selling_rate: float,
	barcode: str | None,
):
	if frappe.db.exists("Item", item_code):
		item = frappe.get_doc("Item", item_code)
	else:
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_name,
				"item_group": item_group,
				"stock_uom": stock_uom,
				"is_stock_item": 1,
				"disabled": 0,
			}
		)
	item.item_name = item_name
	item.item_group = item_group
	item.stock_uom = stock_uom
	item.is_stock_item = 1
	item.disabled = 0
	item.standard_rate = selling_rate
	if barcode and barcode not in {row.barcode for row in item.get("barcodes") or []}:
		item.append("barcodes", {"barcode": barcode})
	if item.is_new():
		item.insert(ignore_permissions=True)
	else:
		item.save(ignore_permissions=True)
	return item


def _ensure_pos_demo_stock(item_code: str, warehouse: str, valuation_rate: float) -> None:
	# Service Order uses Stock Reservation Entry. Keep fixture stock aligned with
	# the same availability calculation the production reservation path uses.
	available_qty = flt(get_available_qty_to_reserve(item_code, warehouse))
	if available_qty >= 8:
		return

	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		raise AssertionError("Empresa padrão não configurada para criar estoque de demonstração do PDV.")
	stock_entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"purpose": "Material Receipt",
			"company": company,
			"posting_date": nowdate(),
			"remarks": f"Demo frontend PDV 3.5-1 - {item_code}",
			"items": [
				{
					"item_code": item_code,
					"qty": 8 - available_qty,
					"t_warehouse": warehouse,
					"basic_rate": valuation_rate,
					"set_basic_rate_manually": 1,
				}
			],
		}
	)
	stock_entry.insert(ignore_permissions=True)
	stock_entry.submit()
