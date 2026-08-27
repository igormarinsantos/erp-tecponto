(function () {
  const form = document.querySelector("[data-portal-lookup]");
  if (!form) return;
  const error = form.querySelector("[data-error]");
  form.addEventListener("submit", async (event) => {
    event.preventDefault(); error.hidden = true;
    const button = form.querySelector("button"); button.disabled = true;
    try {
      const response = await fetch("/api/method/tecponto_app.tecponto.tracking.lookup_public_portal", { method: "POST", credentials: "omit", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ service_order: form.service_order.value.trim(), identity: form.identity.value.trim() }) });
      const payload = await response.json();
      if (!response.ok || !payload.message?.valid || !payload.message?.portal_url) throw new Error(payload.message?.message || "Não foi possível localizar um atendimento com esses dados.");
      window.location.assign(payload.message.portal_url);
    } catch (requestError) { error.textContent = requestError instanceof Error ? requestError.message : "Não foi possível localizar um atendimento com esses dados."; error.hidden = false; button.disabled = false; }
  });
})();
