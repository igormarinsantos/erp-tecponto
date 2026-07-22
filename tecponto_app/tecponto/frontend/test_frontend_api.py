from __future__ import annotations

import json
import os
from base64 import b64encode
from datetime import datetime
from io import BytesIO
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
from tecponto_app.tecponto.frontend.api import (
	contains_sensitive_field,
	get_dashboard_metrics,
	get_boot,
	get_list_statbar,
	get_service_order_statbar,
	get_service_order_detail,
	get_service_order_kanban,
	issue_os_acceptance,
	add_catalog_service_to_service_order,
	create_service_order_checkin,
	get_checkin_delivery_suggestion,
	list_defect_service_mappings,
	list_warranty_candidates,
	create_customer,
	list_catalog_references,
	list_catalog_services,
	list_customer_devices,
	list_service_orders,
	list_stock_items,
	list_sales,
	list_trade_evaluations,
	move_service_order,
	create_stock_transfer,
	resolve_panel,
	search_budget_items,
	search_customers,
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
	submit_stock_transfer,
)
from tecponto_app.tecponto.acceptance import (
	audit_completed_acceptance_evidence,
	assert_completed_acceptance_evidence,
	complete_public_acceptance,
	get_public_acceptance,
	save_public_acceptance_selfie,
)
from tecponto_app.tecponto.tracking import (
	INVALID_LINK_MESSAGE,
	TRACKING_STAGES,
	decide_public_tracking_budget,
	get_public_tracking,
	issue_tracking_link,
	issue_service_order_tracking_link,
	on_service_order_updated,
	revoke_service_order_tracking_link,
	start_public_tracking_budget_acceptance,
)
from tecponto_app.tecponto.frontend.setup import FRONTEND_ROLES, ensure_frontend_foundation
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
	ensure_item_barcode_source_field,
)
from tecponto_app.tecponto import notify
from tecponto_app.tecponto.cashier import CASHIER_OPERATOR_FIELD
from tecponto_app.tecponto.pending import complete_manual_task, create_manual_task, list_agenda_calendar, list_daily_actions
from tecponto_app.tecponto.used_device_warranty import consultar_garantia_usado
from tecponto_app.tecponto.service_order.stage_clock import get_stage_clock
from tecponto_app.tecponto.service_order.stage_sla import add_commercial_business_hours, get_stage_slas


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
		ensure_frontend_foundation()
		users = {role: _find_or_create_user(role) for role in FRONTEND_ROLES}
		panel_checks = _check_role_panels(users)
		orders_check = _check_service_order_api(users["Tecponto Gestor"])
		detail_check = _check_service_order_detail_api(users["Tecponto Atendente"])
		navigation_check = _check_attendant_navigation_apis(users["Tecponto Atendente"])
		metrics_check = _check_dashboard_metrics(users["Tecponto Atendente"])
		device_search_check = _check_customer_device_search(users["Tecponto Atendente"])
		statbar_guard = _check_statbar_guard(users["Tecponto Atendente"])
		guard_check = _check_sensitive_guard(users["Tecponto Tecnico"])
		technician_scope_check = run_technician_scope_checks()
		used_device_warranty_lookup = run_used_device_warranty_lookup_checks()
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
		service_catalog_checks = run_service_catalog_checks()
		product_category_checks = run_product_category_checks()
		product_variant_checks = run_product_variant_checks()
		marketplace_listing_checks = run_marketplace_listing_checks()
		marketplace_reporting_checks = run_marketplace_reporting_checks()
		defect_service_mapping_checks = run_defect_service_mapping_checks()
		stage_sla_checks = run_stage_sla_checks()
		stage_clock_checks = run_stage_clock_checks()
		public_acceptance_checks = run_public_acceptance_checks()
		tracking_checks = run_public_tracking_checks()
		tracking_budget_checks = run_public_tracking_budget_checks()
		tracking_lifecycle_checks = run_tracking_lifecycle_checks()

		return {
			"status": "ok",
			"panel_checks": panel_checks,
			"service_order_api": orders_check,
			"service_order_detail_api": detail_check,
			"navigation_apis": navigation_check,
			"dashboard_metrics": metrics_check,
			"customer_device_search": device_search_check,
			"statbar_guard": statbar_guard,
			"sensitive_guard": guard_check,
			"technician_scope": technician_scope_check,
			"used_device_warranty_lookup": used_device_warranty_lookup,
			"budget_cost_guard": budget_cost_guard,
			"pos_cost_guard": pos_cost_guard,
			"cashier_mode_checks": cashier_mode_checks,
			"multi_role_union": multi_role_context,
			"action_request_checks": action_request_checks,
			"notification_checks": notification_checks,
			"daily_action_checks": daily_action_checks,
			"quick_stage_checks": quick_stage_checks,
			"customer_registration_checks": customer_registration_checks,
			"service_catalog_checks": service_catalog_checks,
			"product_category_checks": product_category_checks,
			"product_variant_checks": product_variant_checks,
			"marketplace_listing_checks": marketplace_listing_checks,
			"marketplace_reporting_checks": marketplace_reporting_checks,
			"defect_service_mapping_checks": defect_service_mapping_checks,
			"stage_sla_checks": stage_sla_checks,
			"stage_clock_checks": stage_clock_checks,
			"public_acceptance_checks": public_acceptance_checks,
			"tracking_checks": tracking_checks,
			"tracking_budget_checks": tracking_budget_checks,
			"tracking_lifecycle_checks": tracking_lifecycle_checks,
		}
	finally:
		frappe.flags.in_test = previous_in_test
		frappe.set_user(previous_user)


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
			or approved_doc.workflow_state != "Aprovado"
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
					"estimated_deadline": "",
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
		frappe.set_user(manager)
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
			frappe.set_user(_find_or_create_user("Tecponto Gestor"))
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
		old = add_to_date(now_datetime(), hours=-48)
		frappe.db.set_value("Service Order", order.name, {"workflow_state": "Entrada criada", "stage_entered_at": old, "estimated_deadline": add_days(now_datetime().date(), -1)}, update_modified=False)
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
		expected = {"Em diagnóstico", "Sem conserto", "Cancelado"}
		if destinations != expected:
			raise AssertionError(f"Opções rápidas não batem com o workflow: {destinations}")
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
		frappe.set_user(workflow_approver)
		if request["name"] not in {row["name"] for row in list_pending_approvals()}:
			raise AssertionError("A role exigida pelo workflow não recebeu a solicitação do controle rápido.")

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
		approve_request(billed_cancel_request["name"])
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
			"billed_service_order_cancel": {"request": billed_cancel_request["name"], "service_order": billed_order, "executed": True},
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
	user.reload()
	assigned_roles = {entry.role for entry in user.roles}
	for role in ("Tecponto Atendente", "Tecponto Gestor"):
		if role not in assigned_roles:
			user.append("roles", {"role": role})
	user.save(ignore_permissions=True)
	frappe.db.commit()
	return user.name


def _find_or_create_attendant_technician_user() -> str:
	"""A real multi-role account used to prove the backend keeps the role union."""
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
	for role in ("Tecponto Atendente", "Tecponto Tecnico"):
		user.append("roles", {"role": role})
	user.save(ignore_permissions=True)
	frappe.db.commit()
	return user.name


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
	item = frappe.db.get_value(
		"Item",
		{"disabled": 0, "is_stock_item": is_stock_item, "has_serial_no": 0},
		"name",
	)
	if not item:
		raise AssertionError("Não há item de teste disponível para montar o orçamento da OS.")
	return item


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
		statbar = {item["key"]: item["value"] for item in get_service_order_statbar()["items"]}
		if statbar["Entrada criada"] != frappe.db.count(
			"Service Order", {"technician": technician, "workflow_state": "Entrada criada"}
		):
			raise AssertionError("StatBar do técnico ignorou a atribuição da OS.")

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
			"multi_role_union_preserved": True,
		}
	finally:
		frappe.set_user(previous_user)


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
