from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

import frappe
from frappe.utils import today
from frappe.utils import add_days, add_to_date, flt, now_datetime, nowdate
from pypdf import PdfReader

from tecponto_app.tecponto.frontend.api import (
	contains_sensitive_field,
	get_dashboard_metrics,
	get_boot,
	get_service_order_detail,
	get_service_order_kanban,
	issue_os_acceptance,
	create_customer,
	list_customer_devices,
	list_service_orders,
	list_stock_items,
	list_trade_evaluations,
	move_service_order,
	create_stock_transfer,
	resolve_panel,
	search_budget_items,
	search_customers,
	search_pos_items,
	set_tradein_approved_value,
	submit_stock_transfer,
)
from tecponto_app.tecponto.acceptance import get_public_acceptance
from tecponto_app.tecponto.frontend.setup import FRONTEND_ROLES, ensure_frontend_foundation
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
from tecponto_app.tecponto.pending import complete_manual_task, create_manual_task, list_daily_actions


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
	try:
		ensure_frontend_foundation()
		users = {role: _find_or_create_user(role) for role in FRONTEND_ROLES}
		panel_checks = _check_role_panels(users)
		orders_check = _check_service_order_api(users["Tecponto Gestor"])
		detail_check = _check_service_order_detail_api(users["Tecponto Atendente"])
		navigation_check = _check_attendant_navigation_apis(users["Tecponto Atendente"])
		metrics_check = _check_dashboard_metrics(users["Tecponto Atendente"])
		guard_check = _check_sensitive_guard(users["Tecponto Tecnico"])
		budget_cost_guard = _check_budget_item_cost_guard(users["Tecponto Atendente"])
		pos_cost_guard = _check_pos_item_cost_guard(
			users["Tecponto Atendente"],
			users["Tecponto Tecnico"],
		)
		cashier_mode_checks = run_cashier_mode_checks()
		multi_role_context = _check_multi_role_context(users["Tecponto Atendente"])
		# Each group intentionally creates documents with naming series. Commit the
		# completed fixtures before the approval suite starts a fresh transaction.
		frappe.db.commit()
		action_request_checks = run_action_request_checks()
		frappe.db.commit()
		notification_checks = run_notification_checks()
		daily_action_checks = run_daily_action_checks()
		quick_stage_checks = run_quick_stage_move_checks()
		customer_registration_checks = run_customer_registration_checks()
		public_acceptance_checks = run_public_acceptance_checks()

		return {
			"status": "ok",
			"panel_checks": panel_checks,
			"service_order_api": orders_check,
			"service_order_detail_api": detail_check,
			"navigation_apis": navigation_check,
			"dashboard_metrics": metrics_check,
			"sensitive_guard": guard_check,
			"budget_cost_guard": budget_cost_guard,
			"pos_cost_guard": pos_cost_guard,
			"cashier_mode_checks": cashier_mode_checks,
			"multi_role_context": multi_role_context,
			"action_request_checks": action_request_checks,
			"notification_checks": notification_checks,
			"daily_action_checks": daily_action_checks,
			"quick_stage_checks": quick_stage_checks,
			"customer_registration_checks": customer_registration_checks,
			"public_acceptance_checks": public_acceptance_checks,
		}
	finally:
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
	original_state = None
	order_name = None
	try:
		demo = ensure_service_order_detail_demo_data()
		attendant = demo["attendant_user"]
		order_name = demo["orders"]["aprovacao"]["name"]
		original_state = frappe.db.get_value("Service Order", order_name, "workflow_state")

		frappe.set_user(attendant)
		before = list_daily_actions("atendente")
		if not any(item["reference_name"] == order_name for item in before["derived"]):
			raise AssertionError("OS aguardando aprovacao nao apareceu nas pendencias do Atendente.")

		frappe.db.set_value("Service Order", order_name, "workflow_state", "Entregue", update_modified=False)
		after = list_daily_actions("atendente")
		if any(item["reference_name"] == order_name for item in after["derived"]):
			raise AssertionError("Pendencia derivada continuou apos a OS ser resolvida.")

		task = create_manual_task("Retornar para cliente da pendencia diaria", str(today()))
		with_task = list_daily_actions("atendente")
		if not any(item["name"] == task["name"] for item in with_task["manual"]):
			raise AssertionError("Tarefa manual criada nao apareceu para o proprio usuario.")
		complete_manual_task(task["name"])
		after_task = list_daily_actions("atendente")
		if any(item["name"] == task["name"] for item in after_task["manual"]):
			raise AssertionError("Tarefa manual concluida continuou na lista aberta.")

		technician = _find_or_create_user("Tecponto Tecnico")
		frappe.set_user(technician)
		technical = list_daily_actions("tecnico")
		if any(item.get("reference_name") == order_name for item in technical["derived"]):
			raise AssertionError("Tecnico recebeu pendencia de OS atribuida ao Atendente.")
		return {
			"status": "ok",
			"derived_disappears": True,
			"manual_task_lifecycle": True,
			"role_scoped": True,
		}
	finally:
		if order_name and original_state:
			frappe.db.set_value("Service Order", order_name, "workflow_state", original_state, update_modified=False)
		frappe.set_user(previous_user)


def run_notification_checks() -> dict:
	"""Covers delivery, ownership, read state and the non-blocking enqueue boundary."""
	previous_user = frappe.session.user
	original_enqueue = frappe.enqueue
	try:
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
		if not any(item["reference_name"] == request["name"] for item in manager_notifications["items"]):
			raise AssertionError(f"Solicitacao criada nao notificou o aprovador. Destinatarios resolvidos: {notify._users_with_role('Tecponto Gestor')}")

		approve_request(request["name"])
		frappe.set_user(attendant)
		attendant_notifications = notify.list_notifications()
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
		return {"status": "ok", "request": request["name"], "decision_notified": True, "unread_before": before_read, "unread_after": after_read, "service_order_link": service_order_notification["link"], "async_failure_isolated": True}
	finally:
		frappe.enqueue = original_enqueue
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
		forbidden_keys = {"services", "parts", "rate", "cost", "valuation_rate", "sales_invoice", "customer_email"}
		if forbidden_keys & set(public["service_order"]):
			raise AssertionError("Projeção pública expôs dado interno da OS.")
		if frappe.db.get_value("OS Acceptance", acceptance.name, "status") != "Pendente":
			raise AssertionError("Consulta pública não pode consumir ou alterar um aceite pendente.")

		# Reemitir invalida o link anterior antes mesmo da captura de selfie/assinatura.
		frappe.set_user(attendant)
		reissued = issue_os_acceptance(service_order, "Entrada")
		frappe.set_user("Guest")
		if get_public_acceptance(raw_token).get("valid"):
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

		return {
			"status": "ok",
			"acceptance": acceptance.name,
			"guest_read_only": True,
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
		trade_request = create_request("tradein_over_max", trade.name, "Oferta excepcional para fechar a troca.", {"approved_value": 150})
		frappe.set_user(manager)
		approve_request(trade_request["name"])
		if flt(frappe.db.get_value("Device Trade Evaluation", trade.name, "approved_value")) != 150:
			raise AssertionError("Aprovação da troca não reaplicou o valor no motor.")

		# OS: a transição é executada pela role que o workflow exige, não por um bypass
		# do solicitante. O teste lê essa role do metadata em vez de duplicar o workflow.
		frappe.set_user(attendant)
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
		try:
			pos_create_sale(
				{**low_price_payload, "idempotency_key": f"tp-pos-floor-att-{frappe.generate_hash(length=20)}"}
			)
		except frappe.ValidationError:
			attendant_floor_blocked = True
		if not attendant_floor_blocked:
			raise AssertionError("Atendente conseguiu vender abaixo do custo.")

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
	for role in ("Tecponto Atendente", "Tecponto Tecnico"):
		if role not in assigned_roles:
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
		{"disabled": 0, "is_stock_item": is_stock_item},
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


def _check_multi_role_context(attendant: str) -> dict:
	multi_role_user = _find_or_create_multi_role_user()
	frappe.set_user(multi_role_user)
	boot = get_boot()
	available_panels = [
		entry["panel"]
		for entry in boot["panels"]
		if entry["role"] in {"Tecponto Atendente", "Tecponto Tecnico"}
	]
	if set(available_panels) != {"atendente", "tecnico"}:
		raise AssertionError(f"Usuário multipapel recebeu contextos incorretos: {available_panels}")

	# O seletor do front pode estar em Técnico, mas as roles reais ainda incluem Atendente.
	attendant_api_payload = search_pos_items(query="Película 3D", limit=1)
	if not attendant_api_payload["items"]:
		raise AssertionError("Usuário Atendente+Técnico perdeu acesso à API de balcão.")
	technical_context_payload = get_dashboard_metrics()

	demo_orders = ensure_service_order_detail_demo_data()
	entry_order = demo_orders["orders"]["entrada"]["name"]
	frappe.set_user(attendant)
	technical_api_blocked = False
	try:
		move_service_order(entry_order, "Em diagnóstico")
	except frappe.PermissionError:
		technical_api_blocked = True
	if not technical_api_blocked:
		raise AssertionError("Atendente sem papel técnico conseguiu mover OS para diagnóstico.")

	leaks = contains_sensitive_field(
		{
			"technical_context": {"boot": boot, "dashboard": technical_context_payload},
			"attendant_context": attendant_api_payload,
		}
	)
	if leaks:
		raise AssertionError(f"Campos sensíveis vazaram entre contextos: {', '.join(leaks)}")

	return {
		"user": multi_role_user,
		"roles": ["Tecponto Atendente", "Tecponto Tecnico"],
		"available_panels": available_panels,
		"visual_context_checked": "tecnico",
		"attendant_api_in_technical_context": "allowed",
		"attendant_only_technical_api": "blocked_403",
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


def _check_attendant_navigation_apis(user: str) -> dict:
	frappe.set_user(user)
	payload = {
		"customers": search_customers(limit=5),
		"devices": list_customer_devices(limit=5),
		"trade_evaluations": list_trade_evaluations(limit=5),
		"stock_items": list_stock_items(limit=5),
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
		"customers": search_customers(limit=5),
		"devices": list_customer_devices(limit=5),
		"trade_evaluations": list_trade_evaluations(limit=5),
		"stock_items": list_stock_items(limit=5),
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
		"search_customers",
			"list_customer_devices",
			"list_trade_evaluations",
			"list_stock_items",
		],
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
	current_qty = flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty") or 0)
	if current_qty >= 8:
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
					"qty": 8 - current_qty,
					"t_warehouse": warehouse,
					"basic_rate": valuation_rate,
					"set_basic_rate_manually": 1,
				}
			],
		}
	)
	stock_entry.insert(ignore_permissions=True)
	stock_entry.submit()
