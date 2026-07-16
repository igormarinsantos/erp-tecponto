(async function () {
	const root = document.querySelector(".tp-tracking");
	if (!root) return;
	const token = root.dataset.token || window.location.pathname.split("/").pop();
	const card = root.querySelector(".tp-tracking-card");
	const escape = (value) => String(value || "").replace(/[&<>\"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character]);
	const formatDate = (value) => value ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "";
	const money = (value) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value || 0));
	const budgetLines = (items) => items.length
		? items.map((item) => `<li><span>${escape(item.description)} <small>${escape(item.quantity)} x ${escape(money(item.unit_price))}</small></span><b>${escape(money(item.line_total))}</b></li>`).join("")
		: `<li class="tp-tracking-empty">Nenhuma linha registrada.</li>`;
	const sendDecision = async (decision, notes = "") => {
		const response = await fetch("/api/method/tecponto_app.tecponto.tracking.decide_public_tracking_budget", {
			method: "POST",
			credentials: "omit",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ token, decision, notes }),
		});
		const payload = await response.json();
		if (!response.ok || payload.exc || !payload.message?.completed) {
			throw new Error(payload._server_messages ? "Não foi possível registrar sua decisão." : "Não foi possível registrar sua decisão.");
		}
		return payload.message.tracking;
	};
	const startBudgetAcceptance = async (identityDocument) => {
		const response = await fetch("/api/method/tecponto_app.tecponto.tracking.start_public_tracking_budget_acceptance", {
			method: "POST",
			credentials: "omit",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ token, identity_document: identityDocument }),
		});
		const payload = await response.json();
		if (!response.ok || payload.exc || !payload.message?.link) {
			throw new Error("Não foi possível validar o documento informado. Confira e tente novamente.");
		}
		return payload.message;
	};
	const renderTracking = (data) => {
		const order = data.service_order;
		const timeline = data.timeline.map((item) => `
			<li class="tp-tracking-step tp-tracking-step--${escape(item.state)}">
				<span class="tp-tracking-marker" aria-hidden="true"></span>
				<div><b>${escape(item.stage)}</b>${item.at ? `<small>${escape(formatDate(item.at))}</small>` : ""}</div>
			</li>`).join("");
		const budget = data.budget ? `
			<section class="tp-tracking-budget">
				<div class="tp-tracking-budget-heading"><div><h2>Seu orçamento</h2><p>Versão ${escape(data.budget.version)}. Confira os itens antes de decidir.</p></div><b>${escape(money(data.budget.total))}</b></div>
				<h3>Mão de obra</h3><ul>${budgetLines(data.budget.services)}</ul>
				<h3>Peças</h3><ul>${budgetLines(data.budget.parts)}</ul>
				<div class="tp-tracking-decision" data-decision><p>Você aprova este orçamento?</p><div><button class="tp-tracking-secondary" type="button" data-reject>Reprovar</button><button class="tp-tracking-primary" type="button" data-approve>Aprovar orçamento</button></div></div>
			</section>` : data.approval ? `<section class="tp-tracking-decision-result"><b>Orçamento ${escape(data.approval.status.toLowerCase())}</b>${data.approval.date ? `<span>${escape(formatDate(data.approval.date))}</span>` : ""}</section>` : "";
		card.innerHTML = `
			<p class="tp-tracking-brand">RASTREIO SEGURO</p>
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
			${budget}
			<section class="tp-tracking-timeline"><h2>Andamento do reparo</h2><ol>${timeline}</ol></section>
			<a class="tp-tracking-whatsapp" href="${escape(data.whatsapp_url)}" target="_blank" rel="noopener noreferrer">Falar no WhatsApp</a>
			<p class="tp-tracking-reference">Atendimento ${escape(order.number)}</p>`;

		const approvalButton = card.querySelector("[data-approve]");
		const rejectionButton = card.querySelector("[data-reject]");
		const decisionArea = card.querySelector("[data-decision]");
		const submit = async (decision, notes) => {
			if (!decisionArea) return;
			decisionArea.querySelectorAll("button").forEach((button) => { button.disabled = true; });
			try {
				renderTracking(await sendDecision(decision, notes));
			} catch (error) {
				const message = error instanceof Error ? error.message : "Não foi possível registrar sua decisão.";
				decisionArea.insertAdjacentHTML("beforeend", `<p class="tp-tracking-decision-error">${escape(message)}</p>`);
				decisionArea.querySelectorAll("button").forEach((button) => { button.disabled = false; });
			}
		};
		approvalButton?.addEventListener("click", () => {
			if (!decisionArea) return;
			decisionArea.innerHTML = `<div class="tp-tracking-identity"><span class="tp-tracking-identity-kicker">Confirmação do titular</span><b>Informe o CPF ou RG do titular</b><p>Antes de aprovar, vamos validar o documento e abrir o aceite com selfie e assinatura.</p><label for="tracking-identity-document">CPF ou RG</label><input autocomplete="off" id="tracking-identity-document" inputmode="numeric" maxlength="24" placeholder="Digite CPF ou RG"><div><button class="tp-tracking-secondary" type="button" data-cancel-approval>Voltar</button><button class="tp-tracking-primary" type="button" data-continue-approval>Continuar para o aceite</button></div></div>`;
			decisionArea.querySelector("[data-cancel-approval]")?.addEventListener("click", () => renderTracking(data));
			decisionArea.querySelector("[data-continue-approval]")?.addEventListener("click", async () => {
				const input = decisionArea.querySelector("input");
				const identityDocument = input?.value.trim() || "";
				if (!identityDocument) {
					decisionArea.insertAdjacentHTML("beforeend", `<p class="tp-tracking-decision-error">Informe o CPF ou RG do titular.</p>`);
					return;
				}
				const continueButton = decisionArea.querySelector("[data-continue-approval]");
				continueButton.disabled = true;
				continueButton.textContent = "Validando...";
				try {
					const acceptance = await startBudgetAcceptance(identityDocument);
					window.location.assign(acceptance.link);
				} catch (error) {
					continueButton.disabled = false;
					continueButton.textContent = "Continuar para o aceite";
					decisionArea.querySelector(".tp-tracking-decision-error")?.remove();
					decisionArea.insertAdjacentHTML("beforeend", `<p class="tp-tracking-decision-error">${escape(error.message || "Não foi possível validar o documento informado.")}</p>`);
				}
			});
		});
		rejectionButton?.addEventListener("click", () => {
			if (!decisionArea) return;
			decisionArea.innerHTML = `<label for="tracking-reject-reason">Motivo da reprovação</label><textarea id="tracking-reject-reason" maxlength="500" placeholder="Explique por que não deseja aprovar."></textarea><div><button class="tp-tracking-secondary" type="button" data-cancel-reject>Voltar</button><button class="tp-tracking-primary" type="button" data-confirm-reject>Confirmar reprovação</button></div>`;
			decisionArea.querySelector("[data-cancel-reject]")?.addEventListener("click", () => renderTracking(data));
			decisionArea.querySelector("[data-confirm-reject]")?.addEventListener("click", () => {
				const notes = decisionArea.querySelector("textarea")?.value.trim() || "";
				if (!notes) {
					decisionArea.insertAdjacentHTML("beforeend", `<p class="tp-tracking-decision-error">Informe o motivo da reprovação.</p>`);
					return;
				}
				submit("reject", notes);
			});
		});
	};

	try {
		const response = await fetch(`/api/method/tecponto_app.tecponto.tracking.get_public_tracking?token=${encodeURIComponent(token)}`, { credentials: "omit" });
		const payload = await response.json();
		const data = payload.message;
		if (!data || !data.valid) throw new Error(data?.message || "Este link de rastreio não está disponível.");
		renderTracking(data);
	} catch (error) {
		card.classList.add("tp-tracking-error");
		card.innerHTML = `<p class="tp-tracking-brand">RASTREIO SEGURO</p><h1>Link indisponível</h1><p>${escape(error.message)}</p>`;
	}
})();
