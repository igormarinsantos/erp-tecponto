(async function () {
	const root = document.querySelector(".tp-tracking");
	if (!root) return;
	const token = root.dataset.token || window.location.pathname.split("/").pop();
	const card = root.querySelector(".tp-tracking-card");
	const escape = (value) => String(value || "").replace(/[&<>\"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character]);
	const formatDate = (value) => value ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "";

	try {
		const response = await fetch(`/api/method/tecponto_app.tecponto.tracking.get_public_tracking?token=${encodeURIComponent(token)}`, { credentials: "omit" });
		const payload = await response.json();
		const data = payload.message;
		if (!data || !data.valid) throw new Error(data?.message || "Este link de rastreio não está disponível.");
		const order = data.service_order;
		const timeline = data.timeline.map((item) => `
			<li class="tp-tracking-step tp-tracking-step--${escape(item.state)}">
				<span class="tp-tracking-marker" aria-hidden="true"></span>
				<div><b>${escape(item.stage)}</b>${item.at ? `<small>${escape(formatDate(item.at))}</small>` : ""}</div>
			</li>`).join("");
		card.innerHTML = `
			<p class="tp-tracking-brand">TECPONTO</p>
			<p class="tp-tracking-kicker">Acompanhe seu reparo</p>
			<h1>${escape(order.workflow_state)}</h1>
			<p class="tp-tracking-copy">Acompanhe cada etapa do seu atendimento. Esta página é somente para consulta.</p>
			<section class="tp-tracking-summary">
				<div><span>Aparelho</span><b>${escape(order.device)}</b></div>
				<div><span>IMEI / serial</span><b>${escape(order.imei_suffix)}</b></div>
				<div class="tp-tracking-wide"><span>Defeito relatado</span><b>${escape(order.reported_defect)}</b></div>
				${order.approval_deadline ? `<div class="tp-tracking-wide"><span>Prazo para aprovação</span><b>${escape(formatDate(order.approval_deadline))}</b></div>` : ""}
				${order.warranty_expiry ? `<div class="tp-tracking-wide"><span>Garantia até</span><b>${escape(new Intl.DateTimeFormat("pt-BR").format(new Date(order.warranty_expiry)))}</b></div>` : ""}
			</section>
			<section class="tp-tracking-timeline"><h2>Andamento do reparo</h2><ol>${timeline}</ol></section>
			<a class="tp-tracking-whatsapp" href="${escape(data.whatsapp_url)}" target="_blank" rel="noopener noreferrer">Falar no WhatsApp</a>
			<p class="tp-tracking-reference">Atendimento ${escape(order.number)}</p>`;
	} catch (error) {
		card.classList.add("tp-tracking-error");
		card.innerHTML = `<p class="tp-tracking-brand">TECPONTO</p><h1>Link indisponível</h1><p>${escape(error.message)}</p>`;
	}
})();
