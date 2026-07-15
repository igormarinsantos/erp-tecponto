(async function () {
	const root = document.querySelector(".tp-acceptance");
	if (!root) return;
	const token = root.dataset.token || window.location.pathname.split("/").pop();
	const card = root.querySelector(".tp-acceptance-card");
	let stream = null;
	const escape = (value) => String(value || "").replace(/[&<>\"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character]);
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
		const order = data.service_order;
		card.innerHTML = `
			<p class="tp-acceptance-brand">TECPONTO</p>
			<h1>Confirme seu atendimento</h1>
			<p>Confira os dados abaixo. Eles são somente leitura.</p>
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
			<section class="tp-camera" aria-labelledby="selfie-title">
				<div class="tp-camera-heading"><div><b id="selfie-title">Selfie de confirmação</b><p>Use somente a câmera ao vivo. Não aceitamos envio de fotos.</p></div><span class="tp-camera-required">Obrigatório</span></div>
				<div class="tp-camera-stage" data-camera-stage></div>
				<p class="tp-camera-feedback" data-camera-feedback aria-live="polite"></p>
			</section>
			<p class="tp-acceptance-readonly">A assinatura e o consentimento serão solicitados no próximo passo. Este link expira em ${escape(data.acceptance.expires_on)}.</p>`;

		const stage = card.querySelector("[data-camera-stage]");
		const feedback = card.querySelector("[data-camera-feedback]");
		const renderStart = () => {
			stage.innerHTML = data.acceptance.selfie_captured
				? `<div class="tp-camera-complete"><b>Selfie registrada</b><span>A próxima etapa coletará assinatura e consentimento.</span></div>`
				: `<button class="tp-camera-primary" type="button" data-start-camera>Abrir câmera</button>`;
			if (!data.acceptance.selfie_captured) stage.querySelector("[data-start-camera]").addEventListener("click", startCamera);
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
				feedback.textContent = "Selfie registrada com sucesso. A assinatura e o consentimento serão coletados no próximo passo.";
				renderStart();
			} catch (error) {
				button.disabled = false;
				button.textContent = "Confirmar selfie";
				feedback.textContent = error.message || "Não foi possível salvar a selfie.";
			}
		};
		renderStart();
	} catch (error) {
		card.classList.add("tp-acceptance-error");
		card.innerHTML = `<p class="tp-acceptance-brand">TECPONTO</p><h1>Link indisponível</h1><p>${escape(error.message)}</p>`;
	} finally {
		window.addEventListener("pagehide", stopCamera, { once: true });
	}
})();
