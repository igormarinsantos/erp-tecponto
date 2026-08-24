"""Versioned additional entry acknowledgement for devices that cannot be tested."""

from __future__ import annotations

import frappe

from tecponto_app.tecponto.company_identity import get_company_identity


ENTRY_OPERATING_CONDITION_OK = "Liga e permite teste"
ENTRY_OPERATING_CONDITION_PARTIAL = "Liga parcialmente"
ENTRY_OPERATING_CONDITION_INOPERATIVE = "Não liga / sem condições de teste"
ENTRY_OPERATING_CONDITIONS = {
	ENTRY_OPERATING_CONDITION_OK,
	ENTRY_OPERATING_CONDITION_PARTIAL,
	ENTRY_OPERATING_CONDITION_INOPERATIVE,
}
INOPERATIVE_ENTRY_CONDITIONS = {
	ENTRY_OPERATING_CONDITION_PARTIAL,
	ENTRY_OPERATING_CONDITION_INOPERATIVE,
}
INOPERATIVE_DEVICE_TERM_VERSION = "APARELHO-SEM-FUNCIONAMENTO-1.0"


def requires_inoperative_device_term(order) -> bool:
	return (order.get("entry_operating_condition") or "").strip() in INOPERATIVE_ENTRY_CONDITIONS


def build_inoperative_device_term(order) -> dict[str, str]:
	"""Freeze the legal-minute text and data facts at issuance time.

	The accepted snapshot remains attached to the OS Acceptance record even if the
	company profile or the device record is edited later.
	"""
	identity = get_company_identity()
	device = frappe.db.get_value(
		"Customer Device",
		order.get("customer_device"),
		["brand", "model", "color", "imei_serial"],
		as_dict=True,
	) or {}
	customer = frappe.db.get_value(
		"Customer",
		order.get("customer"),
		["customer_name", "custom_cpf", "custom_rg", "mobile_no", "custom_whatsapp"],
		as_dict=True,
	) or {}
	device_label = " ".join(part for part in (device.get("brand"), device.get("model")) if part) or "Não informado"
	document = customer.get("custom_cpf") or customer.get("custom_rg") or "Não informado"
	phone = customer.get("custom_whatsapp") or customer.get("mobile_no") or "Não informado"
	company_legal = identity["legal_name"] or identity["display_name"]
	company_display = identity["display_name"] or company_legal
	cnpj = identity["cnpj"] or "Não informado"
	text = f"""TERMO DE CIÊNCIA — APARELHO RECEBIDO SEM FUNCIONAMENTO

[PENDENTE REVISÃO JURÍDICA] — Esta é uma minuta própria, redigida para esta instalação, a ser revisada por advogado e DPO antes do uso definitivo com clientes reais.

Ao entregar o aparelho a {company_display} ({company_legal}, CNPJ {cnpj}), o(a) cliente declara estar ciente de que o equipamento foi recebido sem funcionamento, sem inicialização ou sem condições técnicas suficientes para a realização de testes funcionais completos.

Em razão dessa condição, o diagnóstico realizado no momento da entrada limita-se aos testes tecnicamente possíveis enquanto o equipamento permanece inoperante, além da análise visual e física dos componentes acessíveis.

O(a) cliente reconhece que determinadas falhas, defeitos ou danos preexistentes podem não ser identificados no diagnóstico inicial, uma vez que sua constatação depende do restabelecimento das funções básicas do aparelho e da realização de testes com o equipamento ligado e operacional.

Após o restabelecimento do funcionamento básico, poderão ser identificadas falhas adicionais em componentes ou funções, incluindo, entre outros: placa lógica; tela e touch; câmeras; Face ID, Touch ID ou sensores biométricos; Wi-Fi e Bluetooth; áudio, microfone e alto-falantes; conectores e sistema de carga; bateria; sensores; vibração; rede e sinal; botões; e demais componentes eletrônicos ou funções internas.

A eventual identificação posterior dessas falhas não significa que tenham sido causadas durante o reparo, podendo tratar-se de defeitos ou danos já presentes no aparelho, mas que não puderam ser tecnicamente testados enquanto o equipamento permanecia sem funcionamento.

Caso sejam constatadas novas falhas que demandem peças, reparos ou procedimentos adicionais, a {company_display} comunicará o(a) cliente e apresentará novo diagnóstico e, quando aplicável, orçamento complementar, antes da realização de qualquer serviço adicional que necessite de autorização.

O(a) cliente declara compreender que o restabelecimento de uma função básica do aparelho não representa garantia de funcionamento integral de todos os demais componentes, uma vez que a avaliação completa somente poderá ser realizada após o equipamento voltar a apresentar condições mínimas de teste.

Este termo tem como finalidade registrar as condições técnicas do aparelho no momento da entrada e as limitações inerentes ao diagnóstico de um equipamento recebido sem funcionamento.

IDENTIFICAÇÃO DO APARELHO
Aparelho: {device_label}
Marca / Modelo: {device_label}
IMEI / Número de série: {device.get("imei_serial") or "Não informado"}
Cor: {device.get("color") or "Não informada"}
Ordem de Serviço: {order.name}

CONDIÇÃO NA ENTRADA
Defeito relatado pelo cliente: {order.get("reported_defect") or "Não informado"}
Condição visual do aparelho: {order.get("physical_state") or "Não informada"}
O aparelho liga? {order.get("entry_operating_condition") or "Não informado"}

CIÊNCIA DO CLIENTE
Declaro que fui informado(a) sobre as limitações do diagnóstico inicial e estou ciente de que outros defeitos ou danos preexistentes poderão ser identificados somente após o restabelecimento das funções básicas do equipamento.

Nome do cliente: {customer.get("customer_name") or order.get("customer") or "Não informado"}
CPF/RG: {document}
Telefone: {phone}
Assinatura / aceite digital: registrado via link seguro, com selfie, assinatura e consentimento LGPD."""
	return {"version": INOPERATIVE_DEVICE_TERM_VERSION, "text": text}


def public_inoperative_device_term(term_text: str, order) -> str:
	"""Project the accepted text safely for the public token page.

	The immutable acceptance snapshot deliberately retains the complete device and
	customer facts for the internal PDF/audit trail. The public link is not an
	identity document, so it never repeats the full IMEI, CPF/RG, phone, or name.
	"""
	device = frappe.db.get_value(
		"Customer Device", order.get("customer_device"), ["imei_serial"], as_dict=True
	) or {}
	customer = frappe.db.get_value(
		"Customer",
		order.get("customer"),
		["customer_name", "custom_cpf", "custom_rg", "mobile_no", "custom_whatsapp"],
		as_dict=True,
	) or {}
	public_text = term_text
	imei = device.get("imei_serial") or ""
	document = customer.get("custom_cpf") or customer.get("custom_rg") or ""
	phone = customer.get("custom_whatsapp") or customer.get("mobile_no") or ""
	name = customer.get("customer_name") or ""
	if imei:
		public_text = public_text.replace(imei, f"•••• {imei[-4:]}")
	if document:
		public_text = public_text.replace(document, f"•••• {document[-3:]}")
	if phone:
		public_text = public_text.replace(phone, f"•••• {phone[-4:]}")
	if name:
		public_text = public_text.replace(name, "Cliente titular")
	return public_text
