from __future__ import annotations

from base64 import b64encode
from io import BytesIO

import frappe
from frappe.utils import flt, fmt_money, format_datetime, formatdate, get_url_to_form


DOCTYPE_SERVICE_ORDER = "Service Order"
MODULE_TECPONTO = "Tecponto"

PF_TERMO_ENTRADA = "Tecponto Termo de Entrada"
PF_TERMO_RETIRADA = "Tecponto Termo de Retirada"
PF_OS_ORCAMENTO = "Tecponto OS Orcamento"
PF_ETIQUETA_QR = "Tecponto Etiqueta QR"
PF_CUPOM_PDV = "Tecponto Cupom PDV"

PRINT_FORMAT_NAMES = (
	PF_TERMO_ENTRADA,
	PF_TERMO_RETIRADA,
	PF_OS_ORCAMENTO,
	PF_ETIQUETA_QR,
)


def ensure_service_order_print_formats() -> list[str]:
	created_or_updated = []
	for name, html, css, margins in _print_format_definitions():
		if frappe.db.exists("Print Format", name):
			print_format = frappe.get_doc("Print Format", name)
		else:
			print_format = frappe.new_doc("Print Format")
			print_format.name = name

		values = {
			"doc_type": DOCTYPE_SERVICE_ORDER,
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

	if _ensure_pos_receipt_branding():
		created_or_updated.append(PF_CUPOM_PDV)
	return created_or_updated


def _ensure_pos_receipt_branding() -> bool:
	"""Keep the native Sales Invoice receipt commercial-brand aware.

	The print format itself remains a Tecponto technical record, while the
	receipt heading is resolved from the invoice company at render time.
	"""
	if not frappe.db.exists("Print Format", PF_CUPOM_PDV):
		return False
	print_format = frappe.get_doc("Print Format", PF_CUPOM_PDV)
	old_heading = "<h1>TECPONTO</h1>"
	if old_heading not in (print_format.html or ""):
		return False
	context = "{% set tp_company = frappe.get_attr('tecponto_app.tecponto.company_identity.get_company_identity')(doc.company) %}"
	print_format.html = (print_format.html or "").replace(old_heading, f"{context}\\n    <h1>{{{{ tp_company.display_name }}}}</h1>")
	print_format.save(ignore_permissions=True)
	return True


def get_service_order_print_context(doc) -> dict:
	from tecponto_app.tecponto.company_identity import get_company_identity

	customer = _customer(doc.get("customer"))
	device = _device(doc.get("customer_device"))
	services = [_service_row(row) for row in doc.get("services") or []]
	parts = [_part_row(row) for row in doc.get("parts") or []]
	used_parts = [row for row in parts if row.get("outcome") == "Usada no reparo"]
	service_total = sum(row["amount"] for row in services)
	parts_total = sum(row["amount"] for row in parts)
	used_parts_total = sum(row["amount"] for row in used_parts)
	grand_total = flt(doc.get("grand_total")) or max(
		service_total + parts_total - flt(doc.get("discount")),
		0,
	)
	withdrawal_total = max(service_total + used_parts_total - flt(doc.get("discount")), 0)
	os_url = get_url_to_form(DOCTYPE_SERVICE_ORDER, doc.name)

	return {
		"company": get_company_identity(),
		"customer": customer,
		"device": device,
		"device_label": _device_label(device),
		"services": services,
		"parts": parts,
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
		"diagnosis_date": _date(doc.get("diagnosis_date")),
		"pickup_date": _datetime(doc.get("pickup_date")),
		"warranty_expiry": _date(doc.get("warranty_expiry")),
		"os_url": os_url,
		"qr_code": qr_code_data_uri(os_url),
		"is_without_repair": doc.get("workflow_state")
		in {"Reprovado", "Orçamento expirado", "Sem conserto", "Cancelado"},
		"picked_up_by": doc.get("picked_up_by") or customer.get("name") or doc.get("customer"),
		"picked_up_doc": doc.get("picked_up_doc"),
		"third_party_name": doc.get("third_party_doc") if doc.get("picked_up_by_third_party") else None,
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
		"description": _item_name(row.get("item_code")),
		"qty": qty,
		"rate": rate,
		"amount": qty * rate,
		"rate_fmt": _money(rate),
		"amount_fmt": _money(qty * rate),
		"outcome": row.get("outcome"),
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
		(PF_TERMO_ENTRADA, _termo_entrada_html(), common_css, _a4_margins()),
		(PF_TERMO_RETIRADA, _termo_retirada_html(), common_css, _a4_margins()),
		(PF_OS_ORCAMENTO, _os_orcamento_html(), common_css, _a4_margins()),
		(PF_ETIQUETA_QR, _etiqueta_qr_html(), label_css, {"top": 4, "bottom": 4, "left": 4, "right": 4}),
	)


def _a4_margins() -> dict:
	return {"top": 12, "bottom": 12, "left": 12, "right": 12}


def _context_line() -> str:
	return "{% set tp = get_service_order_print_context(doc) %}"


def _termo_entrada_html() -> str:
	return _context_line() + """
<div class="tp-print">
  <header class="tp-header">
    <div>
      <h1>Termo de Entrada</h1>
      <p>Ordem de Serviço {{ doc.name }}</p>
	  <p>{{ tp.company.legal_name }}{% if tp.company.cnpj %} · CNPJ {{ tp.company.cnpj }}{% endif %}</p>
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
    <p><strong>Riscos, trincos e observações:</strong> {{ doc.attendance_notes or tp.device.notes or "-" }}</p>
    <p><strong>Acessórios recebidos:</strong> {{ doc.accessories_received or "-" }}</p>
  </section>

  <section class="tp-notice">
    <h2>Avisos ao cliente</h2>
    <p><strong>Senha do aparelho.</strong> Quando a senha, padrão ou código de desbloqueio for necessário para diagnóstico, será tratado apenas para execução do serviço e não será impresso neste termo.</p>
    <p><strong>LGPD.</strong> {{ tp.company.display_name }} usará os dados pessoais e do aparelho somente para atendimento, orçamento, execução do reparo, emissão de documentos, cobrança e contatos relacionados à OS.</p>
    <p><strong>Não retirada e estadia.</strong> Após a conclusão, recusa, expiração do orçamento ou aviso de retirada, a loja poderá registrar tentativas de contato. Se a cobrança de estadia estiver habilitada e comunicada ao cliente, a diária poderá ser aplicada após a carência informada, respeitando os limites configurados na OS.</p>
  </section>

  {% if doc.entry_signature %}
    <img class="tp-signature-img" src="{{ doc.entry_signature }}" alt="Assinatura de entrada do cliente">
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
      <h1>Termo de Retirada</h1>
      <p>Ordem de Serviço {{ doc.name }}</p>
	  <p>{{ tp.company.legal_name }}{% if tp.company.cnpj %} · CNPJ {{ tp.company.cnpj }}{% endif %}</p>
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
      <h1>OS / Orçamento</h1>
      <p>Ordem de Serviço {{ doc.name }}</p>
	  <p>{{ tp.company.legal_name }}{% if tp.company.cnpj %} · CNPJ {{ tp.company.cnpj }}{% endif %}</p>
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
    <h2>Mão de obra</h2>
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
    <h2>Peças</h2>
    <table>
      <thead><tr><th>Peça</th><th class="num">Qtd</th><th class="num">Valor</th><th class="num">Total</th></tr></thead>
      <tbody>
      {% for row in tp.parts %}
        <tr><td>{{ row.description }}</td><td class="num">{{ row.qty }}</td><td class="num">{{ row.rate_fmt }}</td><td class="num">{{ row.amount_fmt }}</td></tr>
      {% else %}
        <tr><td colspan="4">Nenhuma peça orçada.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </section>

  <section class="tp-total">
    <p>Serviços: {{ tp.service_total_fmt }}</p>
    <p>Peças: {{ tp.parts_total_fmt }}</p>
    <p>Desconto: {{ tp.discount_fmt }}</p>
    <h2>Total do orçamento: {{ tp.grand_total_fmt }}</h2>
  </section>

  <section class="tp-notice">
    <p><strong>Validade de 48h úteis:</strong> este orçamento é válido até {{ tp.approval_deadline }}. Após esse prazo, a OS pode ser marcada como orçamento expirado e precisar de nova aprovação.</p>
  </section>
</div>
"""


def _etiqueta_qr_html() -> str:
	return _context_line() + """
<div class="tp-label">
  <div class="tp-label-main">
    <h1>{{ doc.name }}</h1>
    <p>{{ tp.customer.name or doc.customer }}</p>
    <p>{{ tp.device_label }}</p>
    <p>IMEI: {{ tp.device.imei_serial or "-" }}</p>
  </div>
  <img src="{{ tp.qr_code }}" alt="QR Code da OS">
  <div class="tp-url">{{ tp.os_url }}</div>
</div>
"""


def _common_css() -> str:
	return """
.tp-print {
  color: #1f2937;
  font-size: 12px;
  line-height: 1.45;
}
.tp-header {
  align-items: flex-start;
  border-bottom: 2px solid #111827;
  display: flex;
  justify-content: space-between;
  margin-bottom: 14px;
  padding-bottom: 10px;
}
.tp-header h1 {
  font-size: 22px;
  margin: 0 0 4px;
}
.tp-header p,
.tp-print p {
  margin: 2px 0;
}
.tp-muted {
  color: #4b5563;
  text-align: right;
}
.tp-grid.two {
  display: grid;
  gap: 12px;
  grid-template-columns: 1fr 1fr;
}
.tp-print section {
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 12px;
  padding-bottom: 10px;
}
.tp-print h2 {
  font-size: 14px;
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
  background: #f3f4f6;
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
.tp-url {
  bottom: 3mm;
  font-size: 6px;
  left: 4mm;
  position: absolute;
  right: 4mm;
  word-break: break-all;
}
"""
