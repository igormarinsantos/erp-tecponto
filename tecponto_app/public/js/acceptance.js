(async function () {
	const root = document.querySelector(".tp-acceptance");
	if (!root) return;
	const token = root.dataset.token || window.location.pathname.split("/").pop();
	const card = root.querySelector(".tp-acceptance-card");
	const escape = (value) => String(value || "").replace(/[&<>\"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character]);
	try {
		const response = await fetch(`/api/method/tecponto_app.tecponto.acceptance.get_public_acceptance?token=${encodeURIComponent(token)}`, { credentials: "omit" });
		const payload = await response.json();
		const data = payload.message;
		if (!data || !data.valid) throw new Error(data?.message || "Este link não está disponível.");
		const order = data.service_order;
		card.innerHTML = `
			<p class="tp-acceptance-brand">TECPONTO</p>
			<h1>Confirme seu atendimento</h1>
			<p>Confira os dados abaixo. Nesta etapa, eles são somente leitura.</p>
			<div class="tp-acceptance-grid">
				<div class="tp-acceptance-field"><b>Ordem de serviço</b>${escape(order.number)}</div>
				<div class="tp-acceptance-field"><b>Tipo de aceite</b>${escape(data.acceptance.type)}</div>
				<div class="tp-acceptance-field"><b>Cliente</b>${escape(order.customer)}</div>
				<div class="tp-acceptance-field"><b>Aparelho</b>${escape(order.device)}</div>
				<div class="tp-acceptance-field"><b>IMEI / Serial</b>${escape(order.imei)}</div>
				<div class="tp-acceptance-field"><b>Defeito relatado</b>${escape(order.reported_defect)}</div>
				<div class="tp-acceptance-field"><b>Estado declarado</b>${escape(order.physical_state)}</div>
				<div class="tp-acceptance-field"><b>Acessórios</b>${escape(order.accessories_received)}</div>
			</div>
			<div class="tp-acceptance-notice"><b>Privacidade e LGPD</b><br>${escape(data.lgpd_notice.text)}</div>
			<p class="tp-acceptance-readonly">A captura de selfie, assinatura e consentimento será solicitada no próximo passo. Este link expira em ${escape(data.acceptance.expires_on)}.</p>`;
	} catch (error) {
		card.classList.add("tp-acceptance-error");
		card.innerHTML = `<p class="tp-acceptance-brand">TECPONTO</p><h1>Link indisponível</h1><p>${escape(error.message)}</p>`;
	}
})();
