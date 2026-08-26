"""Versioned acknowledgement for a part supplied by the customer."""

from __future__ import annotations

from tecponto_app.tecponto.company_identity import get_company_identity


CUSTOMER_PART_TERM_VERSION = "PECA-FORNECIDA-CLIENTE-1.0"


def requires_customer_supplied_part_term(order) -> bool:
	return bool(order.get("customer_supplied_part_term_required")) or any(
		(row.get("part_source") or "Loja") == "Cliente" for row in (order.get("parts") or [])
	)


def build_customer_supplied_part_term(order) -> dict[str, str]:
	identity = get_company_identity()
	company = identity["display_name"] or identity["legal_name"] or "a empresa responsável"
	return {
		"version": CUSTOMER_PART_TERM_VERSION,
		"text": (
			"TERMO DE CIÊNCIA — PEÇA FORNECIDA PELO CLIENTE\n\n"
			"[PENDENTE REVISÃO JURÍDICA] — Esta minuta deve ser revisada antes do uso com clientes reais.\n\n"
			f"O(a) cliente declara que fornecerá a peça utilizada na OS {order.name}. {company} cobrará somente a mão de obra correspondente. "
			"A peça fornecida pelo cliente não integra o estoque da loja e não possui garantia de fornecimento pela empresa. "
			"Eventual defeito, incompatibilidade ou falha da peça do cliente poderá exigir novo diagnóstico e nova autorização antes de qualquer serviço adicional."
		),
	}
