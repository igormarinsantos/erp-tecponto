import { type PointerEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, FileText, PenLine, Printer, RotateCcw, XCircle } from "lucide-react";

import { serviceOrders, type BudgetDecisionPayload, type PickupPayload, type ServiceOrderDetailResponse } from "./api";
import { Button, Modal } from "./ui";

type ApprovalMode = "approve" | "reject";
type ApprovalChannel = BudgetDecisionPayload["channel"];

const approvalChannels: ApprovalChannel[] = ["Presencial", "Telefone", "WhatsApp"];

interface FlowProps {
  detail: ServiceOrderDetailResponse;
  onClose: () => void;
  onUpdated: (detail: ServiceOrderDetailResponse) => void;
  open: boolean;
}

interface BudgetDecisionModalProps extends FlowProps {
  mode: ApprovalMode;
}

export function BudgetDecisionModal({ detail, mode, onClose, onUpdated, open }: BudgetDecisionModalProps) {
  const [channel, setChannel] = useState<ApprovalChannel>("Presencial");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }
    setChannel("Presencial");
    setNotes("");
    setError(null);
    setSubmitting(false);
  }, [open, mode, detail.name]);

  const rejecting = mode === "reject";
  const canSubmit = !rejecting || Boolean(notes.trim());

  async function submit() {
    setError(null);
    if (!canSubmit) {
      setError("Informe o motivo da reprovação.");
      return;
    }
    setSubmitting(true);
    try {
      const updated = await serviceOrders.decideBudget(detail.name, {
        channel,
        decision: mode,
        notes: notes.trim(),
      });
      onUpdated(updated);
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? normalizeFrappeError(caught.message) : "Falha ao registrar a decisão.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      className="max-w-4xl"
      onClose={onClose}
      open={open}
      title={rejecting ? `Reprovar orçamento ${detail.name}` : `Aprovar orçamento ${detail.name}`}
    >
      <div className="grid max-h-[78vh] gap-4 overflow-y-auto pr-1 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="space-y-4">
          <BudgetSummary detail={detail} />
          <label className="block">
            <span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Canal do aceite</span>
            <div className="grid gap-2 sm:grid-cols-3">
              {approvalChannels.map((nextChannel) => (
                <button
                  className={`rounded-control border px-3 py-2 text-sm font-bold transition ${
                    channel === nextChannel
                      ? "border-tec-orange bg-tec-orange/20 text-white"
                      : "border-tec-border/25 bg-tec-field text-tec-subtle hover:border-tec-orange/50"
                  }`}
                  key={nextChannel}
                  onClick={() => setChannel(nextChannel)}
                  type="button"
                >
                  {nextChannel}
                </button>
              ))}
            </div>
          </label>
          <TextArea
            label={rejecting ? "Motivo da reprovação" : "Observação do aceite"}
            onChange={setNotes}
            placeholder={rejecting ? "Ex.: cliente recusou o valor por WhatsApp." : "Ex.: cliente aprovou por telefone com ciência da validade."}
            required={rejecting}
            value={notes}
          />
          {error ? <ErrorBox message={error} /> : null}
        </section>
        <aside className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4">
          <h3 className="text-sm font-bold text-white">Registro no motor</h3>
          <dl className="mt-4 space-y-3 text-sm">
            <FlowLine label="Atendente" value="Usuário logado" />
            <FlowLine label="Prazo 48h úteis" value={deadlineText(detail.approval_deadline)} />
            <FlowLine label="Versão" value={`Orçamento v${detail.totals.budget_version}`} />
            <FlowLine label="Total" value={formatCurrency(detail.totals.grand_total)} />
          </dl>
          <Button
            className="mt-5 w-full"
            disabled={!canSubmit || submitting}
            icon={rejecting ? <XCircle size={17} /> : <CheckCircle2 size={17} />}
            onClick={submit}
            variant={rejecting ? "secondary" : "primary"}
          >
            {submitting ? "Registrando..." : rejecting ? "Reprovar" : "Aprovar"}
          </Button>
        </aside>
      </div>
    </Modal>
  );
}

export function PickupModal({ detail, onClose, onUpdated, open }: FlowProps) {
  const [thirdParty, setThirdParty] = useState(false);
  const [pickedUpBy, setPickedUpBy] = useState("");
  const [pickedUpDoc, setPickedUpDoc] = useState("");
  const [notes, setNotes] = useState("");
  const [signature, setSignature] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }
    setThirdParty(false);
    setPickedUpBy("");
    setPickedUpDoc("");
    setNotes("");
    setSignature(null);
    setError(null);
    setSubmitting(false);
  }, [open, detail.name]);

  const termLink = detail.print_links.find((link) => link.label === "Termo de retirada");
  const canSubmit = Boolean(signature) && (!thirdParty || (pickedUpBy.trim() && pickedUpDoc.trim()));

  async function submit() {
    setError(null);
    if (!signature) {
      setError("Colete a assinatura de retirada antes de entregar.");
      return;
    }
    if (thirdParty && (!pickedUpBy.trim() || !pickedUpDoc.trim())) {
      setError("Informe nome e documento de quem está retirando.");
      return;
    }

    const payload: PickupPayload = {
      customer_signature: signature,
      picked_up_by: pickedUpBy.trim(),
      picked_up_doc: pickedUpDoc.trim(),
      pickup_notes: notes.trim(),
      third_party: thirdParty,
      third_party_auth: thirdParty ? "Retirada por terceiro registrada no balcão Tecponto." : "",
    };

    setSubmitting(true);
    try {
      const updated = await serviceOrders.completePickup(detail.name, payload);
      onUpdated(updated);
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? friendlyPickupError(caught.message) : "Falha ao concluir a entrega.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal className="max-w-5xl" onClose={onClose} open={open} title={`Retirada ${detail.name}`}>
      <div className="grid max-h-[78vh] gap-4 overflow-y-auto pr-1 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="space-y-4">
          <PickupReview detail={detail} />
          <div className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4">
            <label className="flex items-start gap-3 text-sm text-tec-subtle">
              <input
                checked={thirdParty}
                className="mt-1 h-4 w-4 accent-tec-orange"
                onChange={(event) => setThirdParty(event.target.checked)}
                type="checkbox"
              />
              <span>
                <span className="block font-bold text-white">Terceiro retirando</span>
                <span>Marque quando não for o próprio cliente que está retirando o aparelho.</span>
              </span>
            </label>
            {thirdParty ? (
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <Field label="Nome de quem retira" onChange={setPickedUpBy} required value={pickedUpBy} />
                <Field label="Documento" onChange={setPickedUpDoc} required value={pickedUpDoc} />
              </div>
            ) : null}
            <TextArea
              label="Observação da retirada"
              onChange={setNotes}
              placeholder="Ex.: aparelho conferido no balcão, cliente recebeu orientações de garantia."
              value={notes}
            />
          </div>
          <SignaturePad
            guidance="O cliente ou responsável assina confirmando a retirada do aparelho."
            onChange={setSignature}
            signature={signature}
            title="Assinatura de retirada"
          />
          {error ? <ErrorBox message={error} /> : null}
        </section>
        <aside className="space-y-4">
          <div className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4">
            <h3 className="text-sm font-bold text-white">Financeiro</h3>
            <dl className="mt-4 space-y-3 text-sm">
              <FlowLine label="Nota" value={detail.finance.sales_invoice ?? "Sem nota"} />
              <FlowLine label="Status da nota" value={detail.finance.sales_invoice_status ?? "Não paga/ausente"} />
              <FlowLine label="Total" value={formatCurrency(detail.totals.grand_total)} />
            </dl>
            <p className="mt-4 rounded-card border border-tec-amber/25 bg-tec-amber/10 p-3 text-xs text-tec-amber">
              Se a nota não estiver paga, o motor bloqueia a entrega. Gere a nota e receba o pagamento primeiro.
            </p>
          </div>
          <div className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4">
            <h3 className="text-sm font-bold text-white">Impressão</h3>
            {termLink ? (
              <a
                className="mt-3 flex min-h-11 items-center justify-between gap-3 rounded-card border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-tec-subtle transition hover:border-tec-orange/50 hover:text-white"
                href={termLink.url}
                rel="noreferrer"
                target="_blank"
              >
                <span>Termo de Retirada</span>
                <Printer className="text-tec-orange" size={17} />
              </a>
            ) : (
              <p className="mt-3 text-sm text-tec-muted">Termo de retirada não disponível.</p>
            )}
          </div>
          <Button
            className="w-full"
            disabled={!canSubmit || submitting}
            icon={<CheckCircle2 size={17} />}
            onClick={submit}
            variant="primary"
          >
            {submitting ? "Entregando..." : "Entregar"}
          </Button>
        </aside>
      </div>
    </Modal>
  );
}

function BudgetSummary({ detail }: { detail: ServiceOrderDetailResponse }) {
  return (
    <div className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-white">Orçamento</h3>
          <p className="text-xs text-tec-muted">Validade: {deadlineText(detail.approval_deadline)}</p>
        </div>
        <strong className="tp-metric-value text-2xl text-white">{formatCurrency(detail.totals.grand_total)}</strong>
      </div>
      <CompactLines label="Serviços" lines={detail.services} />
      <CompactLines label="Peças" lines={detail.parts} />
    </div>
  );
}

function PickupReview({ detail }: { detail: ServiceOrderDetailResponse }) {
  return (
    <div className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4">
      <div className="mb-4 flex items-center gap-3">
        <FileText className="text-tec-orange" size={20} />
        <div>
          <h3 className="text-base font-bold text-white">Conferência do reparo</h3>
          <p className="text-xs text-tec-muted">Confira serviços, peças e garantia antes da assinatura.</p>
        </div>
      </div>
      <CompactLines label="Serviços executados" lines={detail.services} />
      <CompactLines label="Peças trocadas" lines={detail.parts.filter((line) => line.outcome !== "Perdida")} />
      <dl className="mt-4 grid gap-3 border-t border-tec-border/20 pt-4 text-sm sm:grid-cols-3">
        <FlowLine label="Garantia até" value={detail.warranty.warranty_expiry || "Após entrega"} />
        <FlowLine label="Status" value={detail.workflow_state ?? "Sem status"} />
        <FlowLine label="Total" value={formatCurrency(detail.totals.grand_total)} />
      </dl>
    </div>
  );
}

function CompactLines({ label, lines }: { label: string; lines: ServiceOrderDetailResponse["services"] }) {
  return (
    <div className="mt-3">
      <p className="mb-2 text-xs font-bold uppercase text-tec-muted">{label}</p>
      {lines.length ? (
        <div className="overflow-hidden rounded-card border border-tec-border/15">
          {lines.map((line, index) => (
            <div className="flex items-start justify-between gap-3 border-b border-tec-border/10 p-3 text-sm last:border-0" key={`${label}-${index}`}>
              <span className="min-w-0">
                <span className="block truncate font-semibold text-white">{line.description || line.item_code || "Linha sem descrição"}</span>
                <span className="mt-1 block text-xs text-tec-muted">Qtd. {line.qty.toLocaleString("pt-BR")}</span>
              </span>
              <span className="shrink-0 font-semibold text-tec-subtle">{formatCurrency(line.amount)}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="rounded-card border border-tec-border/15 p-3 text-sm text-tec-muted">Nenhuma linha registrada.</p>
      )}
    </div>
  );
}

function SignaturePad({
  guidance,
  onChange,
  signature,
  title,
}: {
  guidance: string;
  onChange: (value: string | null) => void;
  signature: string | null;
  title: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawing = useRef(false);

  const resetCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.fillStyle = "#fff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.strokeStyle = "#111827";
    context.lineWidth = 3;
    context.lineCap = "round";
    context.lineJoin = "round";
    onChange(null);
  }, [onChange]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const ratio = window.devicePixelRatio || 1;
    canvas.width = 720 * ratio;
    canvas.height = 220 * ratio;
    canvas.style.width = "100%";
    canvas.style.height = "220px";
    const context = canvas.getContext("2d");
    if (context) {
      context.scale(ratio, ratio);
    }
    resetCanvas();
  }, [resetCanvas]);

  function point(event: PointerEvent<HTMLCanvasElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  function begin(event: PointerEvent<HTMLCanvasElement>) {
    const context = canvasRef.current?.getContext("2d");
    if (!context) {
      return;
    }
    const current = point(event);
    drawing.current = true;
    context.beginPath();
    context.moveTo(current.x, current.y);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function move(event: PointerEvent<HTMLCanvasElement>) {
    if (!drawing.current) {
      return;
    }
    const context = canvasRef.current?.getContext("2d");
    if (!context) {
      return;
    }
    const current = point(event);
    context.lineTo(current.x, current.y);
    context.stroke();
  }

  function end(event: PointerEvent<HTMLCanvasElement>) {
    if (!drawing.current) {
      return;
    }
    drawing.current = false;
    event.currentTarget.releasePointerCapture(event.pointerId);
    onChange(canvasRef.current?.toDataURL("image/png") ?? null);
  }

  return (
    <div className="grid gap-4 rounded-card border border-tec-border/20 bg-tec-panel-strong p-4 lg:grid-cols-[minmax(0,1fr)_260px]">
      <section>
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-card bg-tec-orange/15 text-tec-orange">
            <PenLine size={18} />
          </span>
          <h3 className="text-base font-bold text-white">{title}</h3>
        </div>
        <p className="mt-3 text-sm text-tec-subtle">{guidance}</p>
        <canvas
          className="mt-4 touch-none rounded-card border border-tec-border/30 bg-white"
          onPointerCancel={end}
          onPointerDown={begin}
          onPointerMove={move}
          onPointerUp={end}
          ref={canvasRef}
        />
      </section>
      <aside>
        <h4 className="text-sm font-bold text-white">Status</h4>
        <p className={`mt-3 text-sm ${signature ? "text-tec-success" : "text-tec-amber"}`}>
          {signature ? "Assinatura capturada." : "Assine no quadro para liberar a entrega."}
        </p>
        <Button className="mt-5 w-full" icon={<RotateCcw size={17} />} onClick={resetCanvas}>
          Limpar
        </Button>
      </aside>
    </div>
  );
}

function Field({
  label,
  onChange,
  required,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  required?: boolean;
  value: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-bold uppercase text-tec-muted">
        {label}
        {required ? " *" : ""}
      </span>
      <input
        className="h-11 w-full rounded-control border border-tec-border/25 bg-tec-field px-3 text-sm text-white outline-none focus:border-tec-orange/70"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      />
    </label>
  );
}

function TextArea({
  label,
  onChange,
  placeholder,
  required,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  value: string;
}) {
  return (
    <label className="mt-4 block">
      <span className="mb-1 block text-xs font-bold uppercase text-tec-muted">
        {label}
        {required ? " *" : ""}
      </span>
      <textarea
        className="min-h-[120px] w-full resize-none rounded-control border border-tec-border/25 bg-tec-field p-3 text-sm text-white outline-none focus:border-tec-orange/70"
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
    </label>
  );
}

function ErrorBox({ message }: { message: string }) {
  return <div className="rounded-card border border-tec-red/30 bg-tec-red/10 p-3 text-sm text-tec-red">{message}</div>;
}

function FlowLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-tec-muted">{label}</dt>
      <dd className="mt-1 font-semibold text-tec-subtle">{value}</dd>
    </div>
  );
}

function deadlineText(value: string) {
  if (!value) {
    return "Sem prazo";
  }
  const date = new Date(value.replace(" ", "T"));
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const diff = date.getTime() - Date.now();
  const formatted = new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit",
  }).format(date);
  if (diff <= 0) {
    return `${formatted} · vencido`;
  }
  const hours = Math.floor(diff / 3_600_000);
  const minutes = Math.floor((diff % 3_600_000) / 60_000);
  return `${formatted} · faltam ${hours}h ${minutes}min`;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", { currency: "BRL", style: "currency" }).format(value || 0);
}

function normalizeFrappeError(message: string) {
  return message.replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim();
}

function friendlyPickupError(message: string) {
  const normalized = normalizeFrappeError(message);
  const lower = normalized.toLowerCase();
  if (lower.includes("nota") || lower.includes("paid") || lower.includes("paga")) {
    return "Não foi possível entregar: gere a nota e receba o pagamento primeiro. Depois volte para concluir a retirada.";
  }
  return normalized || "Falha ao concluir a entrega.";
}
