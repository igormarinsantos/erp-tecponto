(async function () {
  const root = document.querySelector(".tp-tracking");
  if (!root) return;

  const token = root.dataset.token || window.location.pathname.split("/").pop();
  const card = root.querySelector(".tp-tracking-card");
  const escape = (value) => String(value || "").replace(/[&<>\"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character]);
  const formatDate = (value, withTime = true) => value ? new Intl.DateTimeFormat("pt-BR", withTime ? { dateStyle: "medium", timeStyle: "short" } : { dateStyle: "medium" }).format(new Date(value)) : "Não definida";
  const money = (value) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value || 0));
  const statusMeta = (status) => ({
    "Entrada criada": { label: "Recebido", next: "Seu aparelho seguirá para diagnóstico." },
    "Em diagnóstico": { label: "Em diagnóstico", next: "Nossa equipe está avaliando o aparelho." },
    "Aguardando aprovação": { label: "Aguardando aprovação", next: "Confira o orçamento e decida quando estiver pronto." },
    "Aprovado": { label: "Orçamento aprovado", next: "Seu aparelho seguirá para a etapa de reparo." },
    "Reprovado": { label: "Orçamento recusado", next: "Aguarde as instruções para retirada do aparelho." },
    "Orçamento expirado": { label: "Orçamento expirado", next: "Fale com a Tecponto para conhecer as próximas opções." },
    "Aguardando peça": { label: "Aguardando peça", next: "Estamos aguardando a peça necessária para continuar." },
    "Em reparo": { label: "Em reparo", next: "O reparo está sendo executado pela equipe técnica." },
    "Teste final": { label: "Em teste final", next: "Estamos validando o reparo antes da liberação." },
    "Pronto para retirada": { label: "Pronto para retirada", next: "Seu aparelho está pronto. Combine a retirada com a loja." },
    "Entregue": { label: "Atendimento concluído", next: "Obrigado por confiar na Tecponto." },
  }[status] || { label: status, next: "Acompanhe as próximas atualizações por aqui." });

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
    if (!response.ok || payload.exc || !payload.message?.completed) throw new Error("Não foi possível registrar sua decisão.");
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
    if (!response.ok || payload.exc || !payload.message?.link) throw new Error("Não foi possível validar o documento informado. Confira e tente novamente.");
    return payload.message;
  };

  const bindCopy = () => {
    const copyButton = card.querySelector("[data-copy-os]");
    copyButton?.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(copyButton.dataset.copyOs || "");
        copyButton.textContent = "Copiado";
        window.setTimeout(() => { copyButton.textContent = "Copiar"; }, 1600);
      } catch {
        copyButton.textContent = "Copie manualmente";
      }
    });
  };

  const renderTracking = (data) => {
    const order = data.service_order;
    const meta = statusMeta(order.workflow_state);
    const statusTone = order.workflow_state === "Entregue" || String(data.approval?.status || "").startsWith("Aprov") ? "success" : String(order.workflow_state).startsWith("Reprov") || String(data.approval?.status || "").startsWith("Reprov") ? "danger" : String(order.workflow_state).startsWith("Aguardando") ? "warning" : "info";
    const timeline = data.timeline.map((item) => `
      <li class="tp-tracking-step tp-tracking-step--${escape(item.state)}">
        <span class="tp-tracking-marker" aria-hidden="true">${item.state === "completed" ? "✓" : item.state === "current" ? "●" : ""}</span>
        <div class="tp-tracking-step-copy"><b>${escape(item.stage)}</b>${item.at ? `<small>${escape(formatDate(item.at))}</small>` : ""}${item.state === "current" ? '<span class="tp-current-stage">Etapa atual</span>' : ""}</div>
      </li>`).join("");
    const budget = data.budget ? `
      <section class="tp-tracking-budget" id="tracking-budget">
        <div class="tp-tracking-budget-heading"><div><p class="tp-section-kicker">ORÇAMENTO</p><h2>Detalhes do orçamento</h2><p>Versão ${escape(data.budget.version)}. Confira os itens antes de decidir.</p></div><b>${escape(money(data.budget.total))}</b></div>
        <h3>Mão de obra</h3><ul>${budgetLines(data.budget.services)}</ul>
        <h3>Peças</h3><ul>${budgetLines(data.budget.parts)}</ul>
        <div class="tp-tracking-decision" data-decision><p>Você aprova este orçamento?</p><div><button class="tp-tracking-secondary" type="button" data-reject>Reprovar</button><button class="tp-tracking-primary" type="button" data-approve>Aprovar orçamento</button></div></div>
      </section>` : data.approval ? `<section class="tp-tracking-decision-result"><b>Orçamento ${escape(data.approval.status.toLowerCase())}</b>${data.approval.date ? `<span>${escape(formatDate(data.approval.date))}</span>` : ""}</section>` : "";

    card.innerHTML = `
      <section class="tp-tracking-status-banner tp-status--${statusTone}">
        <div class="tp-status-copy"><p class="tp-tracking-brand">RASTREIO SEGURO</p><h1>${escape(meta.label)}</h1><p>Acompanhe cada etapa do seu atendimento. Esta página é somente para consulta.</p><div class="tp-next-stage"><span aria-hidden="true">○</span>${escape(meta.next)}</div></div>
        <div class="tp-status-actions"><span class="tp-status-badge">${escape(order.workflow_state)}</span><small>Última atualização: ${escape(formatDate(order.last_updated))}</small><div class="tp-status-buttons"><a class="tp-tracking-whatsapp" href="${escape(data.whatsapp_url)}" target="_blank" rel="noopener noreferrer">Falar no WhatsApp</a>${data.budget ? '<a class="tp-tracking-secondary tp-budget-link" href="#tracking-budget">Ver detalhes do orçamento</a>' : ""}</div></div>
      </section>
      <section class="tp-tracking-info-grid" aria-label="Dados do atendimento">
        <article><span class="tp-info-icon">▯</span><div><small>Aparelho</small><b>${escape(order.device)}</b></div></article>
        <article><span class="tp-info-icon">#</span><div><small>IMEI / serial</small><b>${escape(order.imei_suffix)}</b></div></article>
        <article><span class="tp-info-icon">▣</span><div><small>Número da OS</small><b>${escape(order.number)}</b></div><button aria-label="Copiar número da OS" class="tp-copy-button" data-copy-os="${escape(order.number)}" type="button">Copiar</button></article>
        <article><span class="tp-info-icon">◷</span><div><small>Previsão</small><b>${escape(order.estimated_deadline ? formatDate(order.estimated_deadline, false) : order.approval_deadline ? formatDate(order.approval_deadline, false) : "Atualização em breve")}</b></div></article>
        <article><span class="tp-info-icon">⌁</span><div><small>Defeito relatado</small><b>${escape(order.reported_defect)}</b></div></article>
        <article><span class="tp-info-icon">◌</span><div><small>Canal de atendimento</small><b>${escape(order.service_channel || "Balcão")}</b></div></article>
      </section>
      <div class="tp-tracking-layout">
        <section class="tp-tracking-timeline"><div class="tp-section-heading"><div><p class="tp-section-kicker">ACOMPANHAMENTO</p><h2>Andamento do reparo</h2></div></div><ol>${timeline}</ol></section>
        <aside class="tp-tracking-aside">
          <section class="tp-aside-card"><p class="tp-section-kicker">RESUMO DO ATENDIMENTO</p><h2>Resumo do atendimento</h2><dl><div><dt>Status atual</dt><dd>${escape(order.workflow_state)}</dd></div><div><dt>Número da OS</dt><dd>${escape(order.number)}</dd></div><div><dt>Data de entrada</dt><dd>${escape(formatDate(order.entry_date))}</dd></div><div><dt>Última atualização</dt><dd>${escape(formatDate(order.last_updated))}</dd></div>${order.warranty_expiry ? `<div><dt>Garantia até</dt><dd>${escape(formatDate(order.warranty_expiry, false))}</dd></div>` : ""}</dl></section>
          <section class="tp-aside-card tp-help-card"><p class="tp-section-kicker">PRECISA DE AJUDA?</p><h2>Fale com a Tecponto</h2><p>Nossa equipe está pronta para ajudar você pelo WhatsApp.</p><a class="tp-tracking-whatsapp" href="${escape(data.whatsapp_url)}" target="_blank" rel="noopener noreferrer">Falar no WhatsApp</a></section>
          <section class="tp-aside-card"><p class="tp-section-kicker">OBSERVAÇÕES</p><p>As atualizações aparecem automaticamente conforme o andamento do serviço. Continue acompanhando por aqui.</p></section>
        </aside>
      </div>
      ${budget}
      <footer class="tp-tracking-footer"><span>Atendimento ${escape(order.number)}</span><span>▣ Página segura para acompanhamento do serviço</span></footer>`;

    bindCopy();
    const approvalButton = card.querySelector("[data-approve]");
    const rejectionButton = card.querySelector("[data-reject]");
    const decisionArea = card.querySelector("[data-decision]");
    const submit = async (decision, notes) => {
      if (!decisionArea) return;
      decisionArea.querySelectorAll("button").forEach((button) => { button.disabled = true; });
      try { renderTracking(await sendDecision(decision, notes)); }
      catch (error) {
        const message = error instanceof Error ? error.message : "Não foi possível registrar sua decisão.";
        decisionArea.insertAdjacentHTML("beforeend", `<p class="tp-tracking-decision-error">${escape(message)}</p>`);
        decisionArea.querySelectorAll("button").forEach((button) => { button.disabled = false; });
      }
    };
    approvalButton?.addEventListener("click", () => {
      if (!decisionArea) return;
      decisionArea.innerHTML = '<div class="tp-tracking-identity"><span class="tp-tracking-identity-kicker">Confirmação do titular</span><b>Informe o CPF ou RG do titular</b><p>Antes de aprovar, vamos validar o documento e abrir o aceite com selfie e assinatura.</p><label for="tracking-identity-document">CPF ou RG</label><input autocomplete="off" id="tracking-identity-document" inputmode="numeric" maxlength="24" placeholder="Digite CPF ou RG"><div><button class="tp-tracking-secondary" type="button" data-cancel-approval>Voltar</button><button class="tp-tracking-primary" type="button" data-continue-approval>Continuar para o aceite</button></div></div>';
      decisionArea.querySelector("[data-cancel-approval]")?.addEventListener("click", () => renderTracking(data));
      decisionArea.querySelector("[data-continue-approval]")?.addEventListener("click", async () => {
        const input = decisionArea.querySelector("input");
        const identityDocument = input?.value.trim() || "";
        if (!identityDocument) { decisionArea.insertAdjacentHTML("beforeend", '<p class="tp-tracking-decision-error">Informe o CPF ou RG do titular.</p>'); return; }
        const continueButton = decisionArea.querySelector("[data-continue-approval]");
        continueButton.disabled = true;
        continueButton.textContent = "Validando...";
        try { const acceptance = await startBudgetAcceptance(identityDocument); window.location.assign(acceptance.link); }
        catch (error) {
          continueButton.disabled = false;
          continueButton.textContent = "Continuar para o aceite";
          decisionArea.querySelector(".tp-tracking-decision-error")?.remove();
          decisionArea.insertAdjacentHTML("beforeend", `<p class="tp-tracking-decision-error">${escape(error.message || "Não foi possível validar o documento informado.")}</p>`);
        }
      });
    });
    rejectionButton?.addEventListener("click", () => {
      if (!decisionArea) return;
      decisionArea.innerHTML = '<label for="tracking-reject-reason">Motivo da reprovação</label><textarea id="tracking-reject-reason" maxlength="500" placeholder="Explique por que não deseja aprovar."></textarea><div><button class="tp-tracking-secondary" type="button" data-cancel-reject>Voltar</button><button class="tp-tracking-primary" type="button" data-confirm-reject>Confirmar reprovação</button></div>';
      decisionArea.querySelector("[data-cancel-reject]")?.addEventListener("click", () => renderTracking(data));
      decisionArea.querySelector("[data-confirm-reject]")?.addEventListener("click", () => {
        const notes = decisionArea.querySelector("textarea")?.value.trim() || "";
        if (!notes) { decisionArea.insertAdjacentHTML("beforeend", '<p class="tp-tracking-decision-error">Informe o motivo da reprovação.</p>'); return; }
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
