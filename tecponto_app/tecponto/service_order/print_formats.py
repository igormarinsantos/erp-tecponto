from __future__ import annotations

from base64 import b64encode
from io import BytesIO
from urllib.parse import quote

import frappe
from frappe.utils import flt, fmt_money, format_datetime, formatdate, get_url, get_url_to_form


DOCTYPE_SERVICE_ORDER = "Service Order"
MODULE_TECPONTO = "Tecponto"

PF_TERMO_ENTRADA = "Tecponto Termo de Entrada"
PF_TERMO_RETIRADA = "Tecponto Termo de Retirada"
PF_OS_ORCAMENTO = "Tecponto OS Orcamento"
PF_OS_ORCAMENTO_DISCRIMINADO = "Tecponto OS Orcamento Discriminado"
PF_LAUDO_TECNICO = "Tecponto Laudo Tecnico"
PF_TERMO_GARANTIA = "Tecponto Termo de Garantia"
PF_TERMO_PECA_CLIENTE = "Tecponto Termo de Peca do Cliente"
PF_ETIQUETA_QR = "Tecponto Etiqueta QR"
PF_ETIQUETA_INTERNA = "Tecponto Etiqueta Interna OS"
PF_TERMO_APARELHO_PAGAMENTO = "Tecponto Termo Aparelho como Pagamento"
PAYMENT_DOCTYPE = "Tecponto Service Order Payment"

PRINT_FORMAT_NAMES = (
	PF_TERMO_ENTRADA,
	PF_TERMO_RETIRADA,
	PF_OS_ORCAMENTO,
	PF_OS_ORCAMENTO_DISCRIMINADO,
	PF_LAUDO_TECNICO,
	PF_TERMO_GARANTIA,
	PF_TERMO_PECA_CLIENTE,
	PF_ETIQUETA_QR,
	PF_ETIQUETA_INTERNA,
	PF_TERMO_APARELHO_PAGAMENTO,
)


def ensure_service_order_print_formats() -> list[str]:
	created_or_updated = []
	for name, doc_type, html, css, margins in _print_format_definitions():
		if frappe.db.exists("Print Format", name):
			print_format = frappe.get_doc("Print Format", name)
		else:
			print_format = frappe.new_doc("Print Format")
			print_format.name = name

		values = {
			"doc_type": doc_type,
			"module": MODULE_TECPONTO,
			"standard": "No",
			"custom_format": 1,
			"disabled": 0,
			"print_format_for": "DocType",
			"print_format_type": "Jinja",
			"html": html,
			"css": css,
			"margin_top": margins.get("top", 10),
			"margin_bottom": margins.get("bottom", 10),
			"margin_left": margins.get("left", 10),
			"margin_right": margins.get("right", 10),
		}

		changed = print_format.is_new()
		for fieldname, value in values.items():
			if print_format.get(fieldname) != value:
				print_format.set(fieldname, value)
				changed = True

		if changed:
			print_format.save(ignore_permissions=True)
			created_or_updated.append(name)

	return created_or_updated


def get_service_order_print_context(doc) -> dict:
	from tecponto_app.tecponto.company_identity import get_company_identity
	from tecponto_app.tecponto.service_order.customer_supplied_part import requires_customer_supplied_part_term
	from tecponto_app.tecponto.service_order.inoperative_device import requires_inoperative_device_term

	customer = _customer(doc.get("customer"))
	device = _device(doc.get("customer_device"))
	services = [_service_row(row) for row in doc.get("services") or []]
	parts = [_part_row(row) for row in doc.get("parts") or []]
	used_parts = [row for row in parts if row.get("outcome") == "Usada no reparo"]
	store_parts = [row for row in parts if row.get("part_source") != "Cliente"]
	customer_parts = [row for row in parts if row.get("part_source") == "Cliente"]
	service_total = sum(row["amount"] for row in services)
	parts_total = sum(row["amount"] for row in parts)
	used_parts_total = sum(row["amount"] for row in used_parts)
	grand_total = flt(doc.get("grand_total")) or max(
		service_total + parts_total - flt(doc.get("discount")),
		0,
	)
	withdrawal_total = max(service_total + used_parts_total - flt(doc.get("discount")), 0)
	portal_lookup_url = f"{get_url()}/tecponto/acompanhar?service_order={quote(doc.name)}"
	internal_os_url = get_url_to_form(DOCTYPE_SERVICE_ORDER, doc.name)

	return {
		"company": get_company_identity(doc.get("company")),
		"customer": customer,
		"device": device,
		"device_label": _device_label(device),
		"services": services,
		"parts": parts,
		"store_parts": store_parts,
		"customer_parts": customer_parts,
		"used_parts": used_parts,
		"service_total": service_total,
		"parts_total": parts_total,
		"used_parts_total": used_parts_total,
		"discount": flt(doc.get("discount")),
		"grand_total": grand_total,
		"withdrawal_total": withdrawal_total,
		"service_total_fmt": _money(service_total),
		"parts_total_fmt": _money(parts_total),
		"used_parts_total_fmt": _money(used_parts_total),
		"discount_fmt": _money(flt(doc.get("discount"))),
		"grand_total_fmt": _money(grand_total),
		"withdrawal_total_fmt": _money(withdrawal_total),
		"approval_deadline": _datetime(doc.get("approval_deadline")),
		"estimated_deadline": _date(doc.get("estimated_deadline")),
		"entry_date": _datetime(doc.get("entry_date")),
		"entry_operating_condition": doc.get("entry_operating_condition") or "Liga e permite teste",
		"inoperative_device_term": _inoperative_term_context(doc) if requires_inoperative_device_term(doc) else None,
		"customer_part_term": _customer_part_term_context(doc) if requires_customer_supplied_part_term(doc) else None,
		"entry_acceptance": _acceptance_context(doc, "Entrada"),
		"pickup_acceptance": _acceptance_context(doc, "Retirada"),
		"budget_acceptance": _acceptance_context(doc, "Orçamento"),
		"has_customer_supplied_part": bool(customer_parts),
		"diagnosis_date": _date(doc.get("diagnosis_date")),
		"pickup_date": _datetime(doc.get("pickup_date")),
		"warranty_expiry": _date(doc.get("warranty_expiry")),
		"os_url": portal_lookup_url,
		"internal_os_url": internal_os_url,
		"qr_code": qr_code_data_uri(portal_lookup_url),
		"is_without_repair": bool(doc.get("pickup_without_repair")) or doc.get("workflow_state")
		in {"Reprovado", "Orçamento expirado", "Sem conserto", "Cancelado"},
		"picked_up_by": doc.get("picked_up_by") or customer.get("name") or doc.get("customer"),
		"picked_up_doc": doc.get("picked_up_doc"),
		"third_party_name": doc.get("third_party_doc") if doc.get("picked_up_by_third_party") else None,
	}


def _acceptance_context(doc, acceptance_type: str) -> dict | None:
	acceptance = frappe.db.get_value(
		"OS Acceptance",
		{"service_order": doc.name, "acceptance_type": acceptance_type, "status": "Concluído"},
		["acceptance_method", "signer_name", "used_on", "physical_collected_by", "physical_collected_on"],
		as_dict=True,
		order_by="used_on desc",
	)
	if not acceptance:
		return None
	method = acceptance.get("acceptance_method") or "Digital"
	return {
		"method": method,
		"signer_name": acceptance.get("signer_name") or doc.get("picked_up_by") or "Cliente",
		"accepted_on": _datetime(acceptance.get("used_on")),
		"collected_by": acceptance.get("physical_collected_by") or "",
		"collected_on": _datetime(acceptance.get("physical_collected_on")),
	}


def get_internal_service_order_print_context(doc) -> dict:
	"""Add the device password only for the explicitly internal label format."""
	context = get_service_order_print_context(doc)
	device = frappe.get_doc("Customer Device", doc.get("customer_device"))
	context["device"]["password"] = device.get_password("device_access_credential") or "-"
	return context


def get_service_order_payment_print_context(doc) -> dict:
	"""Safe A4 context for the non-monetary trade-in payment acknowledgement."""
	order = frappe.get_doc(DOCTYPE_SERVICE_ORDER, doc.service_order)
	context = get_service_order_print_context(order)
	evaluation = (
		frappe.get_doc("Device Trade Evaluation", doc.source_name)
		if doc.get("source_doctype") == "Device Trade Evaluation" and doc.get("source_name")
		else None
	)
	context.update(
		{
			"payment": {
				"name": doc.name,
				"amount": flt(doc.get("amount")),
				"amount_fmt": _money(doc.get("amount")),
				"created_at": _datetime(doc.get("creation")),
				"reason": doc.get("reason") or "-",
			},
			"trade_device": {
				"description": evaluation.get("evaluated_device_desc") if evaluation else "-",
				"model": evaluation.get("model") if evaluation else "-",
				"imei": evaluation.get("imei") if evaluation else "-",
				"condition": evaluation.get("physical_state") if evaluation else "-",
				"evaluation": evaluation.name if evaluation else "-",
			},
		}
	)
	return context


def _inoperative_term_context(doc) -> dict | None:
	acceptance = frappe.db.get_value(
		"OS Acceptance",
		{"service_order": doc.name, "acceptance_type": "Entrada", "status": "Concluído"},
		["inoperative_device_term_version", "inoperative_device_term_text", "inoperative_device_term_accepted_on"],
		as_dict=True,
	) or {}
	if not (
		acceptance.get("inoperative_device_term_version")
		and acceptance.get("inoperative_device_term_text")
		and acceptance.get("inoperative_device_term_accepted_on")
	):
		return None
	return {
		"version": acceptance["inoperative_device_term_version"],
		"text": acceptance["inoperative_device_term_text"],
		"accepted_on": _datetime(acceptance["inoperative_device_term_accepted_on"]),
	}


def _customer_part_term_context(doc) -> dict | None:
	acceptance = frappe.db.get_value(
		"OS Acceptance",
		{"service_order": doc.name, "acceptance_type": "Orçamento", "status": "Concluído"},
		["customer_part_term_version", "customer_part_term_text", "customer_part_term_accepted_on"],
		as_dict=True,
	) or {}
	if not (
		acceptance.get("customer_part_term_version")
		and acceptance.get("customer_part_term_text")
		and acceptance.get("customer_part_term_accepted_on")
	):
		return None
	return {
		"version": acceptance["customer_part_term_version"],
		"text": acceptance["customer_part_term_text"],
		"accepted_on": _datetime(acceptance["customer_part_term_accepted_on"]),
	}


def qr_code_data_uri(value: str) -> str:
	from pyqrcode import create as qrcreate

	stream = BytesIO()
	qrcreate(value).svg(stream, scale=3, background="#ffffff", module_color="#111111")
	svg = stream.getvalue()
	stream.close()
	return "data:image/svg+xml;base64,{0}".format(b64encode(svg).decode())


def _customer(customer_name: str | None) -> dict:
	if not customer_name:
		return {}

	data = frappe.get_doc("Customer", customer_name) if frappe.db.exists("Customer", customer_name) else None
	return {
		"name": data.get("customer_name") if data else customer_name,
		"mobile": (data.get("mobile_no") or data.get("phone") or "") if data else "",
		"email": data.get("email_id") if data else "",
	}


def _device(customer_device: str | None) -> dict:
	if not customer_device or not frappe.db.exists("Customer Device", customer_device):
		return {}

	device = frappe.get_doc("Customer Device", customer_device)
	return {
		"name": device.name,
		"brand": device.get("brand"),
		"model": device.get("model"),
		"color": device.get("color"),
		"imei_serial": device.get("imei_serial"),
		"capacity": device.get("capacity"),
		"general_state": device.get("general_state"),
		"notes": device.get("notes"),
	}


def _device_label(device: dict) -> str:
	parts = [
		device.get("brand"),
		device.get("model"),
		device.get("capacity"),
		device.get("color"),
	]
	return " ".join(part for part in parts if part) or "Aparelho não informado"


def _service_row(row) -> dict:
	qty = flt(row.get("qty"))
	rate = flt(row.get("rate"))
	return {
		"item_code": row.get("item_code"),
		"description": row.get("description") or _item_name(row.get("item_code")),
		"qty": qty,
		"rate": rate,
		"amount": qty * rate,
		"rate_fmt": _money(rate),
		"amount_fmt": _money(qty * rate),
	}


def _part_row(row) -> dict:
	qty = flt(row.get("qty"))
	rate = flt(row.get("rate"))
	return {
		"item_code": row.get("item_code"),
		"description": row.get("description") or _item_name(row.get("item_code")),
		"qty": qty,
		"rate": rate,
		"amount": qty * rate,
		"rate_fmt": _money(rate),
		"amount_fmt": _money(qty * rate),
		"outcome": row.get("outcome"),
		"part_source": row.get("part_source") or "Loja",
		"customer_part_note": row.get("customer_part_note") or "",
	}


def _item_name(item_code: str | None) -> str:
	if not item_code:
		return ""
	return frappe.get_cached_value("Item", item_code, "item_name") or item_code


def _money(value) -> str:
	return fmt_money(flt(value), currency=_currency())


def _currency() -> str:
	company = (
		frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name")
	)
	return frappe.db.get_value("Company", company, "default_currency") if company else "BRL"


def _date(value) -> str:
	return formatdate(value) if value else "-"


def _datetime(value) -> str:
	return format_datetime(value) if value else "-"


def _print_format_definitions():
	common_css = _common_css()
	label_css = common_css + _label_css()
	return (
		(PF_TERMO_ENTRADA, DOCTYPE_SERVICE_ORDER, _with_document_qr(_termo_entrada_html()), common_css, _a4_margins()),
		(PF_TERMO_RETIRADA, DOCTYPE_SERVICE_ORDER, _with_document_qr(_termo_retirada_html()), common_css, _a4_margins()),
		(PF_OS_ORCAMENTO, DOCTYPE_SERVICE_ORDER, _with_document_qr(_os_orcamento_html()), common_css, _a4_margins()),
		(PF_OS_ORCAMENTO_DISCRIMINADO, DOCTYPE_SERVICE_ORDER, _with_document_qr(_os_orcamento_discriminado_html()), common_css, _a4_margins()),
		(PF_LAUDO_TECNICO, DOCTYPE_SERVICE_ORDER, _with_document_qr(_laudo_tecnico_html()), common_css, _a4_margins()),
		(PF_TERMO_GARANTIA, DOCTYPE_SERVICE_ORDER, _with_document_qr(_termo_garantia_html()), common_css, _a4_margins()),
		(PF_TERMO_PECA_CLIENTE, DOCTYPE_SERVICE_ORDER, _with_document_qr(_termo_peca_cliente_html()), common_css, _a4_margins()),
		(PF_ETIQUETA_QR, DOCTYPE_SERVICE_ORDER, _etiqueta_qr_html(), label_css, {"top": 4, "bottom": 4, "left": 4, "right": 4}),
		(PF_ETIQUETA_INTERNA, DOCTYPE_SERVICE_ORDER, _etiqueta_interna_html(), label_css, {"top": 4, "bottom": 4, "left": 4, "right": 4}),
		(PF_TERMO_APARELHO_PAGAMENTO, PAYMENT_DOCTYPE, _with_document_qr(_termo_aparelho_pagamento_html()), common_css, _a4_margins()),
	)


def _with_document_qr(html: str) -> str:
	"""Add the same public portal QR to every A4 document without duplicating markup."""
	qr = '''
  <aside class="tp-document-qr">
    <img src="{{ tp.qr_code }}" alt="QR Code para acompanhar a OS">
    <div><strong>Acompanhe sua OS</strong><br><span>Escaneie para abrir o portal seguro.</span></div>
  </aside>
'''
	if "<footer>" in html:
		return html.replace("<footer>", qr + "<footer>")
	position = html.rfind("</div>")
	return f"{html[:position]}{qr}{html[position:]}" if position >= 0 else f"{html}{qr}"


def _a4_margins() -> dict:
	return {"top": 12, "bottom": 12, "left": 12, "right": 12}


def _context_line() -> str:
	return "{% set tp = get_service_order_print_context(doc) %}"


def _internal_context_line() -> str:
	return "{% set tp = get_internal_service_order_print_context(doc) %}"


def _termo_entrada_html() -> str:
	return _context_line() + """
<div class="tp-print">
  <header class="tp-header">
    <div>
	  {% if tp.company.logo_url %}<img class="tp-brand-logo" src="{{ tp.company.logo_url }}" alt="{{ tp.company.display_name }}">{% endif %}
      <h1>Termo de Entrada</h1>
      <p>Ordem de Serviço {{ doc.name }}</p>
	  <p>{{ tp.company.display_name }}{% if tp.company.legal_name and tp.company.legal_name != tp.company.display_name %} · {{ tp.company.legal_name }}{% endif %}{% if tp.company.cnpj %} · CNPJ {{ tp.company.cnpj }}{% endif %}</p>
    </div>
    <div class="tp-muted">Entrada: {{ tp.entry_date }}</div>
  </header>

  <section class="tp-grid two">
    <div>
      <h2>Cliente</h2>
      <p><strong>{{ tp.customer.name or doc.customer }}</strong></p>
      <p>Telefone: {{ tp.customer.mobile or "-" }}</p>
      <p>E-mail: {{ tp.customer.email or "-" }}</p>
    </div>
    <div>
      <h2>Aparelho</h2>
      <p><strong>{{ tp.device_label }}</strong></p>
      <p>IMEI / Serial: {{ tp.device.imei_serial or "-" }}</p>
      <p>Cadastro: {{ doc.customer_device or "-" }}</p>
    </div>
  </section>

  <section>
    <h2>Condição informada na entrada</h2>
    <p><strong>Defeito relatado:</strong> {{ doc.reported_defect or "-" }}</p>
    <p><strong>Estado físico declarado:</strong> {{ doc.physical_state or tp.device.general_state or "-" }}</p>
	<p><strong>Condição de funcionamento:</strong> {{ tp.entry_operating_condition }}</p>
    <p><strong>Riscos, trincos e observações:</strong> {{ doc.attendance_notes or tp.device.notes or "-" }}</p>
    <p><strong>Acessórios recebidos:</strong> {{ doc.accessories_received or "-" }}</p>
  </section>

  {% if tp.inoperative_device_term %}
  <section class="tp-notice">
    <h2>Termo de ciência — aparelho recebido sem funcionamento</h2>
    <p><strong>[PENDENTE REVISÃO JURÍDICA]</strong> Versão {{ tp.inoperative_device_term.version }} · Aceite digital: {{ tp.inoperative_device_term.accepted_on }}</p>
    <p class="tp-preline">{{ tp.inoperative_device_term.text }}</p>
  </section>
  {% endif %}

  <section class="tp-notice">
    <h2>Avisos ao cliente</h2>
    <p><strong>Senha do aparelho.</strong> Quando a senha, padrão ou código de desbloqueio for necessário para diagnóstico, será tratado apenas para execução do serviço e não será impresso neste termo.</p>
    <p><strong>LGPD.</strong> {{ tp.company.display_name }} usará os dados pessoais e do aparelho somente para atendimento, orçamento, execução do reparo, emissão de documentos, cobrança e contatos relacionados à OS.</p>
    <p><strong>Não retirada e estadia.</strong> Após a conclusão, recusa, expiração do orçamento ou aviso de retirada, a loja poderá registrar tentativas de contato. Se a cobrança de estadia estiver habilitada e comunicada ao cliente, a diária poderá ser aplicada após a carência informada, respeitando os limites configurados na OS.</p>
  </section>

  {% if doc.entry_signature %}
    <img class="tp-signature-img" src="{{ doc.entry_signature }}" alt="Assinatura de entrada do cliente">
  {% endif %}
  {% if tp.entry_acceptance %}
  <section class="tp-acceptance-stamp {% if tp.entry_acceptance.method == 'Físico' %}physical{% endif %}">
    {% if tp.entry_acceptance.method == 'Físico' %}<strong>Via física assinada e arquivada</strong> em {{ tp.entry_acceptance.collected_on }} por {{ tp.entry_acceptance.collected_by }}.
    {% else %}<strong>Aceito digitalmente</strong> por {{ tp.entry_acceptance.signer_name }}, em {{ tp.entry_acceptance.accepted_on }}. Evidências: selfie, assinatura e consentimento registrados.{% endif %}
  </section>
  {% endif %}
  <div class="tp-signatures">
    <div><span></span><p>Assinatura do cliente</p></div>
    <div><span></span><p>Atendente</p></div>
  </div>

  <footer>[MINUTA — revisar com advogado] Texto informativo, em linguagem simples, sujeito à validação jurídica da política de atendimento, LGPD, não-retirada e estadia.</footer>
</div>
"""


def _termo_retirada_html() -> str:
	return _context_line() + """
<div class="tp-print">
  <header class="tp-header">
    <div>
	  {% if tp.company.logo_url %}<img class="tp-brand-logo" src="{{ tp.company.logo_url }}" alt="{{ tp.company.display_name }}">{% endif %}
      <h1>Termo de Retirada</h1>
      <p>Ordem de Serviço {{ doc.name }}</p>
	  <p>{{ tp.company.display_name }}{% if tp.company.legal_name and tp.company.legal_name != tp.company.display_name %} · {{ tp.company.legal_name }}{% endif %}{% if tp.company.cnpj %} · CNPJ {{ tp.company.cnpj }}{% endif %}</p>
    </div>
    <div class="tp-muted">Retirada: {{ tp.pickup_date }}</div>
  </header>

  {% if tp.is_without_repair %}
  <section class="tp-alert">
    <h2>Retirada sem reparo</h2>
    <p>Esta OS está marcada como <strong>{{ doc.workflow_state }}</strong>. O aparelho é retirado sem execução de reparo final, por recusa, expiração do orçamento, ausência de conserto ou cancelamento registrado.</p>
  </section>
  {% endif %}

  <section class="tp-grid two">
    <div>
      <h2>Cliente</h2>
      <p><strong>{{ tp.customer.name or doc.customer }}</strong></p>
      <p>Documento de retirada: {{ doc.picked_up_doc or "-" }}</p>
    </div>
    <div>
      <h2>Aparelho</h2>
      <p><strong>{{ tp.device_label }}</strong></p>
      <p>IMEI / Serial: {{ tp.device.imei_serial or "-" }}</p>
      <p>Garantia até: <strong>{{ tp.warranty_expiry }}</strong></p>
    </div>
  </section>

  <section>
    <h2>Serviços executados</h2>
    <table>
      <thead><tr><th>Serviço</th><th class="num">Qtd</th><th class="num">Valor</th><th class="num">Total</th></tr></thead>
      <tbody>
      {% for row in tp.services %}
        <tr><td>{{ row.description }}</td><td class="num">{{ row.qty }}</td><td class="num">{{ row.rate_fmt }}</td><td class="num">{{ row.amount_fmt }}</td></tr>
      {% else %}
        <tr><td colspan="4">Nenhum serviço executado registrado.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </section>

  <section>
    <h2>Peças trocadas</h2>
    <table>
      <thead><tr><th>Peça</th><th class="num">Qtd</th><th class="num">Valor</th><th class="num">Total</th></tr></thead>
      <tbody>
      {% for row in tp.used_parts %}
        <tr><td>{{ row.description }}</td><td class="num">{{ row.qty }}</td><td class="num">{{ row.rate_fmt }}</td><td class="num">{{ row.amount_fmt }}</td></tr>
      {% else %}
        <tr><td colspan="4">Nenhuma peça trocada registrada.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </section>

  <section class="tp-total">
    <p>Serviços: {{ tp.service_total_fmt }}</p>
    <p>Peças trocadas: {{ tp.used_parts_total_fmt }}</p>
    <p>Desconto: {{ tp.discount_fmt }}</p>
    <h2>Total: {{ tp.withdrawal_total_fmt }}</h2>
  </section>

  <section>
    <h2>Retirada</h2>
    <p>Retirado por: <strong>{{ tp.picked_up_by or "-" }}</strong></p>
    {% if doc.picked_up_by_third_party %}
      <p>Retirada por terceiro autorizada. Documento/observação do terceiro: {{ doc.third_party_doc or "-" }}</p>
    {% endif %}
    <p>Observações: {{ doc.pickup_notes or "-" }}</p>
  </section>

  {% if doc.customer_signature %}
    <img class="tp-signature-img" src="{{ doc.customer_signature }}" alt="Assinatura do cliente">
  {% endif %}
  {% if tp.pickup_acceptance %}
  <section class="tp-acceptance-stamp {% if tp.pickup_acceptance.method == 'Físico' %}physical{% endif %}">
    {% if tp.pickup_acceptance.method == 'Físico' %}<strong>Via física assinada e arquivada</strong> em {{ tp.pickup_acceptance.collected_on }} por {{ tp.pickup_acceptance.collected_by }}.
    {% else %}<strong>Aceito digitalmente</strong> por {{ tp.pickup_acceptance.signer_name }}, em {{ tp.pickup_acceptance.accepted_on }}. Evidências: selfie, assinatura e consentimento registrados.{% endif %}
  </section>
  {% endif %}
  <div class="tp-signatures">
    <div><span></span><p>Assinatura de retirada</p></div>
    <div><span></span><p>Responsável {{ tp.company.display_name }}</p></div>
  </div>

  <footer>[MINUTA — revisar com advogado] Texto informativo de retirada, garantia e retirada por terceiro sujeito à revisão jurídica.</footer>
</div>
"""


def _os_orcamento_html() -> str:
	return _context_line() + """
<div class="tp-print">
  <header class="tp-header">
    <div>
	  {% if tp.company.logo_url %}<img class="tp-brand-logo" src="{{ tp.company.logo_url }}" alt="{{ tp.company.display_name }}">{% endif %}
      <h1>Orçamento</h1>
      <p>Ordem de Serviço {{ doc.name }}</p>
	      <p>{{ tp.company.display_name }}{% if tp.company.legal_name and tp.company.legal_name != tp.company.display_name %} · {{ tp.company.legal_name }}{% endif %}{% if tp.company.cnpj %} · CNPJ {{ tp.company.cnpj }}{% endif %}</p>
    </div>
    <div class="tp-deadline">Validade: {{ tp.approval_deadline }}</div>
  </header>

  <section class="tp-grid two">
    <div><h2>Cliente</h2><p><strong>{{ tp.customer.name or doc.customer }}</strong></p><p>Telefone: {{ tp.customer.mobile or "-" }}</p></div>
    <div><h2>Aparelho</h2><p><strong>{{ tp.device_label }}</strong></p><p>IMEI / Serial: {{ tp.device.imei_serial or "-" }}</p></div>
  </section>

  <section>
    <h2>Diagnóstico e solução proposta</h2>
    <p><strong>Problema encontrado:</strong> {{ doc.problem_found or "-" }}</p>
    <p><strong>Solução recomendada:</strong> {{ doc.recommended_solution or "-" }}</p>
    <p><strong>Prazo estimado:</strong> {{ tp.estimated_deadline }}</p>
  </section>

  <section>
    <h2>Serviços orçados</h2>
    <table>
      <thead><tr><th>Serviço</th><th class="num">Qtd</th><th class="num">Preço</th></tr></thead>
      <tbody>
      {% for row in tp.services %}
        <tr><td>{{ row.description }}</td><td class="num">{{ row.qty }}</td><td class="num">{{ row.amount_fmt }}</td></tr>
      {% else %}
        <tr><td colspan="3">Nenhum serviço orçado.</td></tr>
      {% endfor %}
      </tbody>
    </table>
    <p class="tp-muted tp-spaced">Os valores acima são fechados por serviço. A composição de venda pode ser discriminada pela loja quando solicitada.</p>
  </section>

  {% if tp.has_customer_supplied_part %}
  <section class="tp-notice"><strong>Peça fornecida pelo cliente.</strong> Este orçamento cobra somente a mão de obra. A peça do cliente não integra o estoque nem a garantia de fornecimento da loja.</section>
  {% endif %}

  <section class="tp-total"><p>Desconto: {{ tp.discount_fmt }}</p><h2>Total do orçamento: {{ tp.grand_total_fmt }}</h2></section>
  <section class="tp-notice"><p><strong>Validade de 48h úteis:</strong> este orçamento é válido até {{ tp.approval_deadline }}. Serviço adicional exige nova autorização.</p></section>
  <footer>Documento comercial. Valores de custo, margem e aquisição não fazem parte deste orçamento.</footer>
</div>
"""


def _os_orcamento_discriminado_html() -> str:
	return _context_line() + """
<div class="tp-print">
  <header class="tp-header">
    <div>
	  {% if tp.company.logo_url %}<img class="tp-brand-logo" src="{{ tp.company.logo_url }}" alt="{{ tp.company.display_name }}">{% endif %}
      <h1>Orçamento discriminado</h1>
      <p>Ordem de Serviço {{ doc.name }}</p>
	  <p>{{ tp.company.display_name }}{% if tp.company.legal_name and tp.company.legal_name != tp.company.display_name %} · {{ tp.company.legal_name }}{% endif %}{% if tp.company.cnpj %} · CNPJ {{ tp.company.cnpj }}{% endif %}</p>
    </div>
    <div class="tp-deadline">Validade: {{ tp.approval_deadline }}</div>
  </header>

  <section class="tp-grid two">
    <div>
      <h2>Cliente</h2>
      <p><strong>{{ tp.customer.name or doc.customer }}</strong></p>
      <p>Telefone: {{ tp.customer.mobile or "-" }}</p>
    </div>
    <div>
      <h2>Aparelho</h2>
      <p><strong>{{ tp.device_label }}</strong></p>
      <p>IMEI / Serial: {{ tp.device.imei_serial or "-" }}</p>
    </div>
  </section>

  <section>
    <h2>Diagnóstico</h2>
    <p><strong>Problema encontrado:</strong> {{ doc.problem_found or "-" }}</p>
    <p><strong>Causa provável:</strong> {{ doc.probable_cause or "-" }}</p>
    <p><strong>Solução recomendada:</strong> {{ doc.recommended_solution or "-" }}</p>
    <p><strong>Prazo estimado:</strong> {{ tp.estimated_deadline }}</p>
  </section>

  <section>
    <h2>Serviços</h2>
    <table>
      <thead><tr><th>Serviço</th><th class="num">Qtd</th><th class="num">Valor</th><th class="num">Total</th></tr></thead>
      <tbody>
      {% for row in tp.services %}
        <tr><td>{{ row.description }}</td><td class="num">{{ row.qty }}</td><td class="num">{{ row.rate_fmt }}</td><td class="num">{{ row.amount_fmt }}</td></tr>
      {% else %}
        <tr><td colspan="4">Nenhum serviço orçado.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </section>

  <section>
    <h2>Componentes de venda</h2>
    <table>
      <thead><tr><th>Peça</th><th class="num">Qtd</th><th class="num">Valor</th><th class="num">Total</th></tr></thead>
      <tbody>
      {% for row in tp.store_parts %}
        <tr><td>{{ row.description }}</td><td class="num">{{ row.qty }}</td><td class="num">{{ row.rate_fmt }}</td><td class="num">{{ row.amount_fmt }}</td></tr>
      {% else %}
        <tr><td colspan="4">Nenhum componente de venda orçado.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </section>

  {% if tp.has_customer_supplied_part %}
  <section class="tp-notice"><strong>Peça fornecida pelo cliente.</strong> {{ tp.customer_parts[0].customer_part_note or "Peça registrada como fornecida pelo cliente." }} Não há valor de peça cobrado neste orçamento.</section>
  {% endif %}

  <section class="tp-total">
    <p>Serviços: {{ tp.service_total_fmt }}</p>
    <p>Peças: {{ tp.parts_total_fmt }}</p>
    <p>Desconto: {{ tp.discount_fmt }}</p>
    <h2>Total do orçamento: {{ tp.grand_total_fmt }}</h2>
  </section>

  <section class="tp-notice">
    <p><strong>Valores discriminados de venda:</strong> esta composição mostra somente o preço comercial de serviços e componentes. Custo, margem e aquisição interna não são exibidos.</p>
    <p><strong>Validade de 48h úteis:</strong> este orçamento é válido até {{ tp.approval_deadline }}. Após esse prazo, a OS pode ser marcada como orçamento expirado e precisar de nova aprovação.</p>
  </section>
</div>
"""


def _laudo_tecnico_html() -> str:
	return _context_line() + """
<div class="tp-print">
  <header class="tp-header">
    <div>{% if tp.company.logo_url %}<img class="tp-brand-logo" src="{{ tp.company.logo_url }}" alt="{{ tp.company.display_name }}">{% endif %}<h1>Laudo técnico</h1><p>Ordem de Serviço {{ doc.name }}</p><p>{{ tp.company.display_name }}{% if tp.company.legal_name and tp.company.legal_name != tp.company.display_name %} · {{ tp.company.legal_name }}{% endif %}{% if tp.company.cnpj %} · CNPJ {{ tp.company.cnpj }}{% endif %}</p></div>
    <div class="tp-muted">Emitido em {{ frappe.utils.format_datetime(frappe.utils.now_datetime()) }}</div>
  </header>
  <section class="tp-grid two">
    <div><h2>Cliente</h2><p><strong>{{ tp.customer.name or doc.customer }}</strong></p></div>
    <div><h2>Aparelho</h2><p><strong>{{ tp.device_label }}</strong></p><p>IMEI / Serial: {{ tp.device.imei_serial or "-" }}</p></div>
  </section>
  <section><h2>Condição de entrada</h2><p><strong>Defeito relatado:</strong> {{ doc.reported_defect or "-" }}</p><p><strong>Condição de funcionamento:</strong> {{ tp.entry_operating_condition }}</p><p><strong>Condição visual:</strong> {{ doc.physical_state or tp.device.general_state or "-" }}</p></section>
  <section><h2>Diagnóstico</h2><p><strong>Problema encontrado:</strong> {{ doc.problem_found or "-" }}</p><p><strong>Causa provável:</strong> {{ doc.probable_cause or "-" }}</p><p><strong>Solução recomendada:</strong> {{ doc.recommended_solution or "-" }}</p><p><strong>Observações técnicas:</strong> {{ doc.diagnosis_notes or "-" }}</p></section>
  <section><h2>Execução e testes</h2><p>Serviços e componentes aplicados estão registrados na OS. Este laudo não divulga custos internos, margem ou dados de aquisição.</p><p><strong>Estado atual:</strong> {{ doc.workflow_state }}</p><p><strong>Técnico responsável:</strong> {{ doc.technician or "Não atribuído" }}</p></section>
  <footer>Documento técnico vinculado à OS {{ doc.name }}.</footer>
</div>
"""


def _termo_garantia_html() -> str:
	return _context_line() + """
<div class="tp-print">
  <header class="tp-header">
    <div>{% if tp.company.logo_url %}<img class="tp-brand-logo" src="{{ tp.company.logo_url }}" alt="{{ tp.company.display_name }}">{% endif %}<h1>Termo de garantia de serviço</h1><p>Ordem de Serviço {{ doc.name }}</p><p>{{ tp.company.display_name }}{% if tp.company.legal_name and tp.company.legal_name != tp.company.display_name %} · {{ tp.company.legal_name }}{% endif %}{% if tp.company.cnpj %} · CNPJ {{ tp.company.cnpj }}{% endif %}</p></div>
    <div class="tp-muted">Entrega: {{ tp.pickup_date }}</div>
  </header>
  <section class="tp-grid two"><div><h2>Cliente</h2><p><strong>{{ tp.customer.name or doc.customer }}</strong></p></div><div><h2>Aparelho</h2><p><strong>{{ tp.device_label }}</strong></p><p>IMEI / Serial: {{ tp.device.imei_serial or "-" }}</p></div></section>
  <section><h2>Cobertura</h2><p>A garantia cobre a mão de obra e o serviço executado nesta OS. O prazo é contado a partir da retirada confirmada, em {{ tp.pickup_date }}.</p><p><strong>Garantia válida até:</strong> {{ tp.warranty_expiry }}</p>{% if doc.is_warranty and doc.original_service_order %}<p>Retrabalho vinculado à OS original {{ doc.original_service_order }}. O prazo permanece o da entrega original.</p>{% endif %}</section>
  <section><h2>Exclusões</h2><p>Não cobre danos posteriores, mau uso, oxidação, quedas, intervenção de terceiros, falhas não relacionadas ao serviço executado nem peças fornecidas pelo cliente.</p>{% if tp.has_customer_supplied_part %}<p><strong>Peça do cliente:</strong> a peça fornecida pelo cliente não possui garantia de fornecimento pela loja.</p>{% endif %}</section>
  <footer>[MINUTA — revisar com advogado] Garantia vinculada à retirada real e à OS {{ doc.name }}.</footer>
</div>
"""


def _termo_peca_cliente_html() -> str:
	return _context_line() + """
<div class="tp-print">
	  <header class="tp-header"><div>{% if tp.company.logo_url %}<img class="tp-brand-logo" src="{{ tp.company.logo_url }}" alt="{{ tp.company.display_name }}">{% endif %}<h1>Termo de peça fornecida pelo cliente</h1><p>Ordem de Serviço {{ doc.name }}</p><p>{{ tp.company.display_name }}{% if tp.company.legal_name and tp.company.legal_name != tp.company.display_name %} · {{ tp.company.legal_name }}{% endif %}{% if tp.company.cnpj %} · CNPJ {{ tp.company.cnpj }}{% endif %}</p></div><div class="tp-muted">{{ tp.entry_date }}</div></header>
  <section class="tp-grid two"><div><h2>Cliente</h2><p><strong>{{ tp.customer.name or doc.customer }}</strong></p></div><div><h2>Aparelho</h2><p><strong>{{ tp.device_label }}</strong></p><p>IMEI / Serial: {{ tp.device.imei_serial or "-" }}</p></div></section>
  <section><h2>Peça informada</h2>{% for row in tp.customer_parts %}<p><strong>{{ row.description }}</strong>{% if row.customer_part_note %} · {{ row.customer_part_note }}{% endif %}</p>{% else %}<p>Nenhuma peça do cliente registrada nesta OS.</p>{% endfor %}</section>
  {% if tp.customer_part_term %}<section class="tp-notice"><p><strong>[PENDENTE REVISÃO JURÍDICA]</strong> Versão {{ tp.customer_part_term.version }} · Aceite digital: {{ tp.customer_part_term.accepted_on }}</p><p class="tp-preline">{{ tp.customer_part_term.text }}</p></section>{% else %}<section class="tp-notice"><p>Este termo deve ser aceito pelo cliente antes da execução quando houver peça fornecida por ele.</p></section>{% endif %}
  <footer>A peça fornecida pelo cliente não entra no estoque e não recebe garantia de fornecimento da loja.</footer>
</div>
"""


def _termo_aparelho_pagamento_html() -> str:
	return """
{% set tp = get_service_order_payment_print_context(doc) %}
<div class="tp-print">
	  <header class="tp-header"><div>{% if tp.company.logo_url %}<img class="tp-brand-logo" src="{{ tp.company.logo_url }}" alt="{{ tp.company.display_name }}">{% endif %}<h1>Termo de aparelho como pagamento</h1><p>Referência {{ doc.name }} · OS {{ doc.service_order }}</p><p>{{ tp.company.display_name }}{% if tp.company.legal_name and tp.company.legal_name != tp.company.display_name %} · {{ tp.company.legal_name }}{% endif %}{% if tp.company.cnpj %} · CNPJ {{ tp.company.cnpj }}{% endif %}</p></div><div class="tp-muted">{{ tp.payment.created_at }}</div></header>
  <section><h2>Cliente e OS</h2><p><strong>{{ tp.customer.name or "-" }}</strong></p><p>Aparelho em reparo: {{ tp.device_label }}</p></section>
  <section><h2>Aparelho entregue como pagamento</h2><p><strong>{{ tp.trade_device.description }}</strong></p><p>Modelo: {{ tp.trade_device.model }} · IMEI / Serial: {{ tp.trade_device.imei }}</p><p>Condição declarada: {{ tp.trade_device.condition }}</p><p>Avaliação: {{ tp.trade_device.evaluation }}</p></section>
  <section class="tp-total"><h2>Valor abatido: {{ tp.payment.amount_fmt }}</h2><p>Este abatimento é não monetário e não representa entrada de dinheiro na gaveta.</p></section>
  <section class="tp-notice"><p>[PENDENTE REVISÃO JURÍDICA] O cliente declara entregar o aparelho descrito para avaliação/compensação. A confirmação da operação, estoque e documentos fiscais seguem o fluxo interno registrado.</p></section>
  <footer>Termo operacional vinculado ao pagamento {{ doc.name }}.</footer>
</div>
"""


def _etiqueta_qr_html() -> str:
	return _context_line() + """
<div class="tp-label">
  <div class="tp-label-main">
	<p class="tp-label-brand">{{ tp.company.display_name }}</p>
    <h1>{{ doc.name }}</h1>
    <p>{{ tp.customer.name or doc.customer }}</p>
    <p>{{ tp.device_label }}</p>
    <p>IMEI: {{ tp.device.imei_serial or "-" }}</p>
  </div>
  <img src="{{ tp.qr_code }}" alt="QR Code da OS">
  <div class="tp-url">{{ tp.os_url }}</div>
</div>
"""


def _etiqueta_interna_html() -> str:
	return _internal_context_line() + """
<div class="tp-label tp-internal-label">
  <div class="tp-label-main">
	<p class="tp-label-brand">{{ tp.company.display_name }}</p>
    <h1>{{ doc.name }}</h1>
    <p>{{ tp.device_label }}</p>
    <p>Cliente: {{ tp.customer.name or doc.customer }}</p>
    <p>IMEI: {{ tp.device.imei_serial or "-" }}</p>
    <p class="tp-password"><strong>Senha / padrão:</strong> {{ tp.device.password or "Não informada" }}</p>
  </div>
  <img src="{{ tp.qr_code }}" alt="QR Code interno da OS">
  <div class="tp-url">USO INTERNO · {{ tp.internal_os_url }}</div>
</div>
"""


def _common_css() -> str:
	return """
.tp-print {
  color: #17202a;
  font-family: "Space Grotesk", "Helvetica Neue", Arial, sans-serif;
  font-size: 12px;
  line-height: 1.45;
}
.tp-header {
  align-items: flex-start;
  border-bottom: 3px solid #f05a22;
  display: flex;
  justify-content: space-between;
  margin-bottom: 14px;
  padding-bottom: 10px;
}
.tp-header h1 {
  font-size: 24px;
  letter-spacing: 0;
  margin: 0 0 4px;
}
.tp-brand-logo {
  display: block;
  max-height: 28px;
  max-width: 160px;
  object-fit: contain;
  object-position: left center;
  margin: 0 0 6px;
}
.tp-header p,
.tp-print p {
  margin: 2px 0;
}
.tp-muted {
  color: #4b5563;
  text-align: right;
}
.tp-spaced {
  margin-top: 8px !important;
}
.tp-grid.two {
  display: grid;
  gap: 12px;
  grid-template-columns: 1fr 1fr;
}
.tp-print section {
  border-bottom: 1px solid #d7dce1;
  margin-bottom: 12px;
  padding-bottom: 10px;
}
.tp-print h2 {
  color: #17202a;
  font-size: 13px;
  text-transform: uppercase;
  margin: 0 0 6px;
}
.tp-notice,
.tp-alert {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  padding: 10px;
}
.tp-alert {
  background: #fff7ed;
  border-color: #fed7aa;
}
.tp-preline {
  line-height: 1.45;
  white-space: pre-line;
}
.tp-deadline {
  background: #fff7ed;
  border: 1px solid #fdba74;
  color: #9a3412;
  font-weight: 700;
  padding: 8px 10px;
}
table {
  border-collapse: collapse;
  width: 100%;
}
th,
td {
  border: 1px solid #d1d5db;
  padding: 6px;
  vertical-align: top;
}
th {
  background: #edf1f4;
  text-align: left;
}
.num {
  text-align: right;
  white-space: nowrap;
}
.tp-total {
  margin-left: auto;
  max-width: 260px;
  text-align: right;
}
.tp-total h2 {
  font-size: 16px;
}
.tp-signatures {
  display: grid;
  gap: 30px;
  grid-template-columns: 1fr 1fr;
  margin-top: 36px;
}
.tp-signatures span {
  border-top: 1px solid #111827;
  display: block;
  height: 1px;
}
.tp-signatures p {
  text-align: center;
}
.tp-signature-img {
  display: block;
  max-height: 80px;
  max-width: 260px;
}
.tp-document-qr {
  align-items: center;
  background: #f7f9fa;
  border: 1px solid #d7dce1;
  display: flex;
  font-size: 10px;
  gap: 10px;
  margin-top: 14px;
  padding: 8px;
}
.tp-document-qr img {
  height: 42px;
  width: 42px;
}
.tp-document-qr span {
  color: #52606d;
}
.tp-acceptance-stamp {
  background: #e9f8ef;
  border: 1px solid #77c996 !important;
  border-left: 4px solid #178c4a !important;
  color: #155b35;
  padding: 9px 10px !important;
}
.tp-acceptance-stamp.physical {
  background: #fff8e7;
  border-color: #e7bd58 !important;
  border-left-color: #b7791f !important;
  color: #704a10;
}
footer {
  border-top: 1px solid #e5e7eb;
  color: #6b7280;
  font-size: 10px;
  margin-top: 18px;
  padding-top: 8px;
}
"""


def _label_css() -> str:
	return """
@page {
  size: 80mm 50mm;
}
.tp-label {
  border: 1px solid #111827;
  box-sizing: border-box;
  color: #111827;
  font-size: 9px;
  height: 48mm;
  padding: 4mm;
  position: relative;
  width: 78mm;
}
.tp-label-main {
  padding-right: 28mm;
}
.tp-label-brand {
  font-size: 7px;
  font-weight: 700;
  margin: 0 0 1mm !important;
  text-transform: uppercase;
}
.tp-label h1 {
  font-size: 16px;
  margin: 0 0 2mm;
}
.tp-label p {
  margin: 1mm 0;
}
.tp-label img {
  height: 24mm;
  position: absolute;
  right: 4mm;
  top: 4mm;
  width: 24mm;
}
.tp-internal-label .tp-password {
  border: 1px solid #111827;
  font-size: 8px;
  padding: 1.5mm;
}
.tp-url {
  bottom: 3mm;
  font-size: 6px;
  left: 4mm;
  position: absolute;
  right: 4mm;
  word-break: break-all;
}
"""
