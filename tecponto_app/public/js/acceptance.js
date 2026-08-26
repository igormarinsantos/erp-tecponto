(async function () {
	const root = document.querySelector(".tp-acceptance");
	if (!root) return;
	const token = root.dataset.token || window.location.pathname.split("/").pop();
	const card = root.querySelector(".tp-acceptance-card");
	let stream = null;
	let signatureData = null;
	let drawing = false;
	const escape = (value) => String(value || "").replace(/[&<>\"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character]);
	const applyIdentity = (identity) => {
		const name = identity?.display_name || "Empresa responsável";
		const header = root.querySelector(".tp-public-header");
		if (header) header.innerHTML = `${identity?.logo_url ? `<img alt="${escape(name)}" class="tp-public-logo" src="${escape(identity.logo_url)}">` : `<strong class="tp-public-wordmark">${escape(name)}</strong>`}<span>Atendimento seguro</span>`;
		document.title = `Aceite | ${name}`;
		return name;
	};
	const stopCamera = () => {
		stream?.getTracks().forEach((track) => track.stop());
		stream = null;
	};
	const cameraMessage = (error) => error?.name === "NotAllowedError"
		? "Não foi possível acessar a câmera. Permita o uso da câmera no navegador e tente novamente."
		: "Não foi possível iniciar a câmera. Verifique se ela está disponível e tente novamente.";

	try {
		const response = await fetch(`/api/method/tecponto_app.tecponto.acceptance.get_public_acceptance?token=${encodeURIComponent(token)}`, { credentials: "omit" });
		const payload = await response.json();
		const data = payload.message;
		if (!data || !data.valid) throw new Error(data?.message || "Este link não está disponível.");
		const companyName = applyIdentity(data.identity);
		const order = data.service_order;
		const inoperativeTerm = data.acceptance.inoperative_device_term;
		const customerPartTerm = data.acceptance.customer_part_term;
		card.innerHTML = `
			<p class="tp-acceptance-brand">${data.acceptance.type === "Orçamento" ? "APROVAÇÃO DE ORÇAMENTO" : "ACEITE DIGITAL"}</p>
			<h1>${data.acceptance.type === "Orçamento" ? "Confirme seu orçamento" : "Confirme seu atendimento"}</h1>
			<p>Confira os dados abaixo. Eles são somente leitura.</p>
			<div class="tp-acceptance-grid">
				<div class="tp-acceptance-field"><b>Ordem de serviço</b>${escape(order.number)}</div>
				<div class="tp-acceptance-field"><b>Tipo de aceite</b>${escape(data.acceptance.type)}</div>
				<div class="tp-acceptance-field"><b>Cliente</b>${escape(order.customer)}</div>
				<div class="tp-acceptance-field"><b>Aparelho</b>${escape(order.device)}</div>
				<div class="tp-acceptance-field"><b>IMEI / Serial</b>${escape(order.imei_suffix)}</div>
				<div class="tp-acceptance-field"><b>Defeito relatado</b>${escape(order.reported_defect)}</div>
				<div class="tp-acceptance-field"><b>Estado declarado</b>${escape(order.physical_state)}</div>
				<div class="tp-acceptance-field"><b>Condição na entrada</b>${escape(order.entry_operating_condition)}</div>
				<div class="tp-acceptance-field"><b>Acessórios</b>${escape(order.accessories_received)}</div>
			</div>
			${inoperativeTerm ? `<section class="tp-acceptance-notice"><b>Termo de ciência — aparelho recebido sem funcionamento</b><br><small>[PENDENTE REVISÃO JURÍDICA] · versão ${escape(inoperativeTerm.version)}</small><p class="tp-acceptance-term">${escape(inoperativeTerm.text)}</p></section>` : ""}
			${customerPartTerm ? `<section class="tp-acceptance-notice"><b>Termo de ciência — peça fornecida pelo cliente</b><br><small>[PENDENTE REVISÃO JURÍDICA] · versão ${escape(customerPartTerm.version)}</small><p class="tp-acceptance-term">${escape(customerPartTerm.text)}</p></section>` : ""}
			<div class="tp-acceptance-notice"><b>Privacidade e LGPD</b><br>${escape(data.lgpd_notice.text)}</div>
			<section class="tp-camera" aria-labelledby="selfie-title">
				<div class="tp-camera-heading"><div><b id="selfie-title">Selfie de confirmação</b><p>Use somente a câmera ao vivo. Não aceitamos envio de fotos.</p></div><span class="tp-camera-required">Obrigatório</span></div>
				<div class="tp-camera-stage" data-camera-stage></div>
				<p class="tp-camera-feedback" data-camera-feedback aria-live="polite"></p>
			</section>
			<p class="tp-acceptance-readonly">Este link expira em ${escape(data.acceptance.expires_on)} e só pode ser usado uma vez.</p>`;

		const stage = card.querySelector("[data-camera-stage]");
		const feedback = card.querySelector("[data-camera-feedback]");
		const renderStart = () => {
			stage.innerHTML = data.acceptance.selfie_captured || data.acceptance.selfie_exception
				? ""
				: `<button class="tp-camera-primary" type="button" data-start-camera>Abrir câmera</button>`;
			if (data.acceptance.selfie_captured || data.acceptance.selfie_exception) {
				renderSignatureAndConsent(Boolean(data.acceptance.selfie_exception));
			} else {
				stage.querySelector("[data-start-camera]").addEventListener("click", startCamera);
			}
		};
		const renderSignatureAndConsent = (selfieException = false) => {
			stage.innerHTML = `
				<div class="tp-camera-complete"><b>${selfieException ? "Selfie dispensada pelo Gestor" : "Selfie registrada"}</b><span>${selfieException ? "Assine e confirme o consentimento para concluir esta exceção." : "Assine e confirme o consentimento para concluir."}</span></div>
				<section class="tp-signature" aria-labelledby="signature-title">
					<b id="signature-title">Assinatura do cliente</b>
					<p>Assine no quadro abaixo para confirmar este aceite.</p>
					<canvas class="tp-signature-canvas" aria-label="Quadro de assinatura"></canvas>
					<div class="tp-camera-actions"><button class="tp-camera-secondary" type="button" data-clear-signature>Limpar assinatura</button></div>
				</section>
				<label class="tp-lgpd-consent"><input type="checkbox" data-lgpd-consent> <span>Li e concordo com o termo de consentimento LGPD, versão ${escape(data.lgpd_notice.version)}.</span></label>
				${inoperativeTerm ? `<label class="tp-lgpd-consent"><input type="checkbox" data-inoperative-term-consent> <span>Li e estou ciente do Termo de ciência — aparelho recebido sem funcionamento, versão ${escape(inoperativeTerm.version)}.</span></label>` : ""}
				${customerPartTerm ? `<label class="tp-lgpd-consent"><input type="checkbox" data-customer-part-term-consent> <span>Li e estou ciente do Termo de ciência — peça fornecida pelo cliente, versão ${escape(customerPartTerm.version)}.</span></label>` : ""}
				<div class="tp-camera-actions"><button class="tp-camera-primary" type="button" data-complete-acceptance disabled>Concluir aceite</button></div>`;
			const canvas = stage.querySelector(".tp-signature-canvas");
			const consent = stage.querySelector("[data-lgpd-consent]");
			const inoperativeConsent = stage.querySelector("[data-inoperative-term-consent]");
			const customerPartConsent = stage.querySelector("[data-customer-part-term-consent]");
			const complete = stage.querySelector("[data-complete-acceptance]");
			const resizeCanvas = () => {
				const ratio = window.devicePixelRatio || 1;
				canvas.width = Math.max(600, canvas.clientWidth || 600) * ratio;
				canvas.height = 180 * ratio;
				const context = canvas.getContext("2d");
				context.scale(ratio, ratio);
				context.fillStyle = "#ffffff";
				context.fillRect(0, 0, canvas.width / ratio, canvas.height / ratio);
				context.strokeStyle = "#202428";
				context.lineWidth = 3;
				context.lineCap = "round";
				context.lineJoin = "round";
			};
			const point = (event) => {
				const rect = canvas.getBoundingClientRect();
				return { x: event.clientX - rect.left, y: event.clientY - rect.top };
			};
			const syncComplete = () => { complete.disabled = !signatureData || !consent.checked || Boolean(inoperativeTerm && !inoperativeConsent?.checked) || Boolean(customerPartTerm && !customerPartConsent?.checked); };
			const clearSignature = () => { signatureData = null; resizeCanvas(); syncComplete(); };
			canvas.addEventListener("pointerdown", (event) => {
				const context = canvas.getContext("2d");
				const current = point(event);
				drawing = true;
				context.beginPath();
				context.moveTo(current.x, current.y);
				canvas.setPointerCapture(event.pointerId);
			});
			canvas.addEventListener("pointermove", (event) => {
				if (!drawing) return;
				const current = point(event);
				const context = canvas.getContext("2d");
				context.lineTo(current.x, current.y);
				context.stroke();
			});
			const finishSignature = (event) => {
				if (!drawing) return;
				drawing = false;
				if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
				signatureData = canvas.toDataURL("image/png");
				syncComplete();
			};
			canvas.addEventListener("pointerup", finishSignature);
			canvas.addEventListener("pointercancel", finishSignature);
			stage.querySelector("[data-clear-signature]").addEventListener("click", clearSignature);
			consent.addEventListener("change", syncComplete);
			inoperativeConsent?.addEventListener("change", syncComplete);
			customerPartConsent?.addEventListener("change", syncComplete);
			complete.addEventListener("click", completeAcceptance);
			resizeCanvas();
		};
		const renderCamera = () => {
			stage.innerHTML = `<video class="tp-camera-video" autoplay muted playsinline aria-label="Prévia da câmera"></video><div class="tp-camera-actions"><button class="tp-camera-secondary" type="button" data-cancel-camera>Cancelar</button><button class="tp-camera-primary" type="button" data-capture-selfie>Capturar selfie</button></div>`;
			stage.querySelector("[data-cancel-camera]").addEventListener("click", () => { stopCamera(); renderStart(); });
			stage.querySelector("[data-capture-selfie]").addEventListener("click", captureSelfie);
			stage.querySelector("video").srcObject = stream;
		};
		const startCamera = async () => {
			if (!navigator.mediaDevices?.getUserMedia) {
				feedback.textContent = "Este navegador não oferece acesso à câmera. Abra o link em um celular ou tablet atualizado.";
				return;
			}
			try {
				feedback.textContent = "";
				stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
				renderCamera();
			} catch (error) {
				feedback.textContent = cameraMessage(error);
			}
		};
		const captureSelfie = () => {
			const video = stage.querySelector("video");
			if (!video?.videoWidth) {
				feedback.textContent = "A câmera ainda está iniciando. Aguarde um instante e tente novamente.";
				return;
			}
			const canvas = document.createElement("canvas");
			canvas.width = video.videoWidth;
			canvas.height = video.videoHeight;
			canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
			const imageData = canvas.toDataURL("image/jpeg", .9);
			stopCamera();
			stage.innerHTML = `<img class="tp-camera-preview" alt="Prévia da selfie capturada"><div class="tp-camera-actions"><button class="tp-camera-secondary" type="button" data-retake-selfie>Refazer</button><button class="tp-camera-primary" type="button" data-save-selfie>Confirmar selfie</button></div>`;
			stage.querySelector("img").src = imageData;
			stage.querySelector("[data-retake-selfie]").addEventListener("click", startCamera);
			stage.querySelector("[data-save-selfie]").addEventListener("click", () => saveSelfie(imageData));
		};
		const saveSelfie = async (imageData) => {
			const button = stage.querySelector("[data-save-selfie]");
			button.disabled = true;
			button.textContent = "Salvando...";
			try {
				const response = await fetch("/api/method/tecponto_app.tecponto.acceptance.save_public_acceptance_selfie", {
					method: "POST",
					credentials: "omit",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ token, image_data: imageData }),
				});
				const payload = await response.json();
				if (!response.ok || payload.exc || !payload.message?.saved) throw new Error(payload._server_messages ? "Não foi possível salvar a selfie. Tente novamente." : "Não foi possível salvar a selfie.");
				data.acceptance.selfie_captured = true;
				feedback.textContent = "Selfie registrada com sucesso. Assine e confirme o consentimento para concluir.";
				renderStart();
			} catch (error) {
				button.disabled = false;
				button.textContent = "Confirmar selfie";
				feedback.textContent = error.message || "Não foi possível salvar a selfie.";
			}
		};
		const completeAcceptance = async () => {
			const button = stage.querySelector("[data-complete-acceptance]");
			const consent = stage.querySelector("[data-lgpd-consent]");
			if (!signatureData || !consent?.checked || (inoperativeTerm && !stage.querySelector("[data-inoperative-term-consent]")?.checked) || (customerPartTerm && !stage.querySelector("[data-customer-part-term-consent]")?.checked)) {
				feedback.textContent = (inoperativeTerm || customerPartTerm)
					? "Assine e confirme o consentimento LGPD e o termo adicional antes de concluir."
					: "Assine e confirme o consentimento LGPD antes de concluir.";
				return;
			}
			button.disabled = true;
			button.textContent = "Concluindo...";
			try {
				const response = await fetch("/api/method/tecponto_app.tecponto.acceptance.complete_public_acceptance", {
					method: "POST",
					credentials: "omit",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ token, signature_data: signatureData, lgpd_consent: 1, inoperative_term_consent: inoperativeTerm ? 1 : 0, customer_part_term_consent: customerPartTerm ? 1 : 0 }),
				});
				const payload = await response.json();
				if (!response.ok || payload.exc || !payload.message?.completed) throw new Error("Não foi possível concluir o aceite.");
				stopCamera();
				const completionTitle = data.acceptance.type === "Orçamento" ? "Orçamento aprovado" : "Aceite concluído";
				const completionCopy = data.acceptance.type === "Orçamento"
					? `Sua aprovação foi registrada com selfie, assinatura e consentimento. ${companyName} seguirá com o reparo.`
					: "Sua confirmação foi registrada com sucesso. Você pode devolver este aparelho ao atendente.";
				card.innerHTML = `<p class="tp-acceptance-brand">${data.acceptance.type === "Orçamento" ? "APROVAÇÃO DE ORÇAMENTO" : "ACEITE DIGITAL"}</p><h1>${completionTitle}</h1><p>${completionCopy}</p><div class="tp-acceptance-notice"><b>Registro concluído</b><br>Selfie, assinatura e consentimento foram vinculados a este atendimento.</div>`;
			} catch (error) {
				button.disabled = false;
				button.textContent = "Concluir aceite";
				feedback.textContent = error.message || "Não foi possível concluir o aceite.";
			}
		};
		renderStart();
	} catch (error) {
		card.classList.add("tp-acceptance-error");
		card.innerHTML = `<p class="tp-acceptance-brand">ACEITE DIGITAL</p><h1>Link indisponível</h1><p>${escape(error.message)}</p>`;
	} finally {
		window.addEventListener("pagehide", stopCamera, { once: true });
	}
})();
