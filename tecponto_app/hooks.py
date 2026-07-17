app_name = "tecponto_app"
app_title = "Tecponto"
app_publisher = "Tecponto"
app_description = "Custom ERP app for Tecponto"
app_email = "admin@tecponto.local"
app_license = "mit"

# Tecponto owns the visual identity everywhere Frappe renders a page, including
# login, Desk and the public acceptance/tracking pages.
website_context = {
	"favicon": "/assets/tecponto_app/branding/favicon.ico",
}
base_template = "tecponto_app/templates/base.html"

jinja = {
	"methods": [
		"tecponto_app.tecponto.service_order.print_formats.get_service_order_print_context",
		"tecponto_app.tecponto.pos.get_item_barcode_label_context",
	],
}

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Tecponto"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Tecponto"]]},
	{
		"dt": "Role",
		"filters": [
			[
				"role_name",
				"in",
				[
					"Tecponto Atendente",
					"Tecponto Tecnico",
					"Tecponto Gestor",
					"Tecponto Diretor",
				],
			]
		],
	},
	{"dt": "Tecponto Settings"},
	{
		"dt": "Custom DocPerm",
		"filters": [
			[
				"parent",
				"in",
				[
					"Customer Device",
					"Device Trade Evaluation",
					"Item",
					"Service Order",
					"Trade-In Operation",
					"Tecponto Settings",
				],
			]
		],
	},
	{"dt": "Workflow", "filters": [["name", "=", "Service Order"]]},
	{"dt": "Kanban Board", "filters": [["name", "=", "OS - Operacao"]]},
	{
		"dt": "Print Format",
		"filters": [
			[
				"name",
				"in",
				[
					"Tecponto Termo de Entrada",
					"Tecponto Termo de Retirada",
					"Tecponto OS Orcamento",
					"Tecponto Etiqueta QR",
					"Tecponto Cupom PDV",
					"Tecponto Etiqueta Barcode",
				],
			]
		],
	},
	{
		"dt": "Workflow State",
		"filters": [
			[
				"name",
				"in",
				[
					"Entrada criada",
					"Em diagnóstico",
					"Aguardando aprovação",
					"Aprovado",
					"Reprovado",
					"Orçamento expirado",
					"Aguardando peça",
					"Em reparo",
					"Teste final",
					"Pronto para retirada",
					"Entregue",
					"Sem conserto",
					"Cancelado",
					"Aprovado para compra",
					"Comprado",
				],
			]
		],
	},
	{
		"dt": "Workflow Action Master",
		"filters": [
			[
				"name",
				"in",
				[
					"Aguardando aprovação",
					"Aguardando peça",
					"Aprovado",
					"Cancelado",
					"Em diagnóstico",
					"Em reparo",
					"Entregue",
					"Expirar orçamento",
					"Pronto para retirada",
					"Reprovado",
					"Sem conserto",
					"Teste final",
				],
			]
		],
	},
	{"dt": "POS Profile", "filters": [["name", "=", "Tecponto Balcão"]]},
]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "tecponto_app",
# 		"logo": "/assets/tecponto_app/logo.png",
# 		"title": "Tecponto",
# 		"route": "/tecponto_app",
# 		"has_permission": "tecponto_app.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/tecponto_app/css/tecponto_app.css"
# app_include_js = "/assets/tecponto_app/js/tecponto_app.js"

# include js, css files in header of web template
# web_include_css = "/assets/tecponto_app/css/tecponto_app.css"
# web_include_js = "/assets/tecponto_app/js/tecponto_app.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "tecponto_app/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "tecponto_app/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "tecponto_app.utils.jinja_methods",
# 	"filters": "tecponto_app.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "tecponto_app.install.before_install"
# after_install = "tecponto_app.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "tecponto_app.uninstall.before_uninstall"
# after_uninstall = "tecponto_app.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "tecponto_app.utils.before_app_install"
# after_app_install = "tecponto_app.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "tecponto_app.utils.before_app_uninstall"
# after_app_uninstall = "tecponto_app.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "tecponto_app.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "tecponto_app.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
permission_query_conditions = {
	"Service Order": "tecponto_app.tecponto.permissions.service_order_query",
	"Tecponto Notification": "tecponto_app.tecponto.notify.notification_query",
}

has_permission = {
	"Service Order": "tecponto_app.tecponto.permissions.service_order_has_permission",
	"Tecponto Notification": "tecponto_app.tecponto.notify.notification_has_permission",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Customer": {
		"validate": "tecponto_app.tecponto.customer.validate_customer_registration",
	},
	"Item": {
		"before_validate": "tecponto_app.tecponto.stock.apply_item_valuation_defaults",
		"validate": "tecponto_app.tecponto.stock.validate_item_barcodes",
	},
	"Service Order": {
		"before_validate": "tecponto_app.tecponto.stock.apply_service_order_stock_defaults",
		"validate": [
			"tecponto_app.tecponto.service_order.stage_clock.set_stage_entered_at",
			"tecponto_app.tecponto.pricing.validate_service_order_pricing",
			"tecponto_app.tecponto.service_order.aceites.validate_aceites",
			"tecponto_app.tecponto.service_order.policies.validate_repare_rules",
			"tecponto_app.tecponto.service_order.budget.validate_budget_lock",
			"tecponto_app.tecponto.service_order.deadline.set_approval_deadline",
		],
		"on_update": [
			"tecponto_app.tecponto.service_order.budget.reset_locked_budget_if_changed",
			"tecponto_app.tecponto.service_order.parts.processar_pecas",
			"tecponto_app.tecponto.service_order.advance.processar_sinal",
			"tecponto_app.tecponto.service_order.billing.gerar_nota",
			"tecponto_app.tecponto.service_order.commission.gerar_comissao",
			"tecponto_app.tecponto.tracking.on_service_order_updated",
			"tecponto_app.tecponto.notify.on_service_order_updated",
		],
	},
	"Tecponto Request": {
		"after_insert": "tecponto_app.tecponto.notify.on_request_created",
		"on_update": "tecponto_app.tecponto.notify.on_request_updated",
	},
	"Device Trade Evaluation": {
		"validate": "tecponto_app.tecponto.tradein.evaluation.validar_avaliacao",
		"on_update": [
			"tecponto_app.tecponto.tradein.buyback.concretizar_compra",
			"tecponto_app.tecponto.tradein.cannibalization.canibalizar",
		],
	},
	"Trade-In Operation": {
		"on_update": "tecponto_app.tecponto.tradein.operation.confirmar_troca",
	},
	"Sales Invoice": {
		"before_validate": [
			"tecponto_app.tecponto.stock.apply_sales_stock_defaults",
			"tecponto_app.tecponto.used_device_warranty.validate_used_device_serials",
		],
		"validate": [
			"tecponto_app.tecponto.pos.validate_pos_warehouse",
			"tecponto_app.tecponto.pricing.validate_sales_pricing",
		],
		"on_submit": "tecponto_app.tecponto.used_device_warranty.create_used_device_warranties",
	},
	"POS Invoice": {
		"before_validate": [
			"tecponto_app.tecponto.stock.apply_sales_stock_defaults",
			"tecponto_app.tecponto.used_device_warranty.validate_used_device_serials",
		],
		"validate": [
			"tecponto_app.tecponto.pos.validate_pos_warehouse",
			"tecponto_app.tecponto.pricing.validate_sales_pricing",
		],
	},
	"Material Request": {
		"before_validate": "tecponto_app.tecponto.purchasing.apply_buying_warehouse_defaults",
	},
	"Purchase Order": {
		"before_validate": "tecponto_app.tecponto.purchasing.apply_buying_warehouse_defaults",
		"before_submit": "tecponto_app.tecponto.purchasing.validate_purchase_approval_threshold",
	},
	"Purchase Receipt": {
		"before_validate": "tecponto_app.tecponto.purchasing.apply_buying_warehouse_defaults",
	},
	"Purchase Invoice": {
		"before_validate": "tecponto_app.tecponto.purchasing.apply_buying_warehouse_defaults",
	},
	"Stock Entry": {
		"validate": "tecponto_app.tecponto.stock.validate_transfer_role",
	},
}

after_migrate = [
	"tecponto_app.tecponto.stock.ensure_moving_average_valuation",
	"tecponto_app.tecponto.payments.ensure_card_receivables_setup",
	"tecponto_app.tecponto.hr.ensure_hr_foundation",
	"tecponto_app.tecponto.frontend.setup.ensure_frontend_foundation",
	"tecponto_app.tecponto.workflow.ensure_service_order_workflow",
	"tecponto_app.tecponto.tradein.workflow.ensure_tradein_workflow_states",
	"tecponto_app.tecponto.tradein.buyback.ensure_serial_batch_for_used_devices",
	"tecponto_app.tecponto.service_order.deadline.ensure_guarulhos_holiday_list",
	"tecponto_app.tecponto.service_order.parts.ensure_stock_reservation_for_service_order",
	"tecponto_app.tecponto.pos.ensure_pos_profile",
	"tecponto_app.tecponto.pos.ensure_item_barcode_source_field",
	"tecponto_app.tecponto.cashier.ensure_cashier_sales_invoice_field",
	"tecponto_app.tecponto.service_order.kanban.ensure_service_order_kanban",
	"tecponto_app.tecponto.service_order.print_formats.ensure_service_order_print_formats",
	"tecponto_app.tecponto.tracking.ensure_tracking_lifecycle",
	"tecponto_app.tecponto.service_catalog.ensure_service_catalog",
	"tecponto_app.tecponto.defect_service_mapping.ensure_defect_service_mappings",
	"tecponto_app.tecponto.service_order.stage_sla.ensure_stage_slas",
	"tecponto_app.tecponto.branding.ensure_branding_assets",
]

website_route_rules = [
	{"from_route": "/tecponto", "to_route": "tecponto"},
	{"from_route": "/tecponto/nova-os", "to_route": "tecponto"},
	{"from_route": "/tecponto/caixa", "to_route": "tecponto"},
	{"from_route": "/tecponto/aceite/<token>", "to_route": "aceite"},
	{"from_route": "/tecponto/rastreio/<token>", "to_route": "rastreio"},
]

role_home_page = {
	"Tecponto Atendente": "tecponto",
	"Tecponto Tecnico": "tecponto",
	"Tecponto Gestor": "tecponto",
	"Tecponto Diretor": "tecponto",
}

after_build = "tecponto_app.tecponto.frontend.build.build_frontend"

# Scheduled Tasks
# ---------------

scheduler_events = {
	"hourly": [
		"tecponto_app.tecponto.notify.notify_due_service_orders",
	],
	"daily": [
		"tecponto_app.tecponto.service_order.deadline.expirar_orcamentos",
		"tecponto_app.tecponto.requests.expire_requests",
	],
}

# Testing
# -------

# before_tests = "tecponto_app.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "tecponto_app.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "tecponto_app.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "tecponto_app.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["tecponto_app.utils.before_request"]
# after_request = ["tecponto_app.utils.after_request"]

# Job Events
# ----------
# before_job = ["tecponto_app.utils.before_job"]
# after_job = ["tecponto_app.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"tecponto_app.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
