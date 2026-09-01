import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  CheckCircle2,
  FileText,
  Hourglass,
  Ellipsis,
  LayoutGrid,
  List,
  Phone,
  Search,
  TrendingUp,
  XCircle,
  Upload,
} from "lucide-react";

import { serviceOrders, type QuoteCrmItem, type QuotesCrmResponse } from "./api";
import { Button, Card } from "./ui";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    currency: "BRL",
    style: "currency",
  }).format(value || 0);
}

function buildWhatsAppUrl(phone: string | null | undefined, message: string) {
  const digits = (phone ?? "").replace(/\D/g, "");
  if (!digits) {
    return null;
  }
  const normalized = digits.startsWith("55") ? digits : `55${digits}`;
  return `https://wa.me/${normalized}?text=${encodeURIComponent(message)}`;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value.replace(" ", "T")));
}

type CrmPeriodMode = "none" | "7d" | "14d" | "custom";

function formatDateParam(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function crmPeriodParams(mode: CrmPeriodMode, fromDate: string, toDate: string) {
  if (mode === "none") return {};
  if (mode === "custom") return { from_date: fromDate || undefined, to_date: toDate || undefined };
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - (mode === "14d" ? 13 : 6));
  return { from_date: formatDateParam(start), to_date: formatDateParam(end) };
}

function readPrivateEvidence(file: File) {
  const allowed = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
  if (!allowed.includes(file.type)) throw new Error("Envie uma foto, imagem ou PDF.");
  if (file.size > 8 * 1024 * 1024) throw new Error("O comprovante deve ter no máximo 8 MB.");
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Não foi possível ler o comprovante."));
    reader.readAsDataURL(file);
  });
}

type CrmChannel = "WhatsApp" | "Telefone" | "Presencial" | "E-mail" | "Link";
const CONTACT_CHANNELS: Array<{ label: string; value: CrmChannel }> = [
  { label: "WhatsApp", value: "WhatsApp" },
  { label: "Telefone", value: "Telefone" },
  { label: "Balcão", value: "Presencial" },
  { label: "E-mail", value: "E-mail" },
];

function ChannelPills({ includeLink = false, onChange, value }: { includeLink?: boolean; onChange: (channel: CrmChannel) => void; value: CrmChannel }) {
  const channels = includeLink ? [...CONTACT_CHANNELS, { label: "Link", value: "Link" as CrmChannel }] : CONTACT_CHANNELS;
  return <div className="mt-1 flex flex-wrap gap-2">{channels.map((channel) => (
    <button
      className={`rounded-full border px-3 py-1.5 text-xs font-bold transition ${value === channel.value ? "border-tec-orange bg-tec-orange text-white" : "border-tec-border/50 bg-tec-field/50 text-tec-subtle hover:text-white"}`}
      key={channel.value}
      onClick={() => onChange(channel.value)}
      type="button"
    >{channel.label}</button>
  ))}</div>;
}

export function QuotesCrmScreen({
  onOpenOrder,
  onToast,
}: {
  onOpenOrder: (name: string) => void;
  onToast: (message: string, tone?: "success" | "error") => void;
}) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<QuotesCrmResponse | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [periodMode, setPeriodMode] = useState<CrmPeriodMode>("none");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "grid">("grid");
  const [openActionsOrder, setOpenActionsOrder] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [actionModal, setActionModal] = useState<{
    type: "follow_up" | "approve" | "reject";
    order: QuoteCrmItem;
  } | null>(null);
  const [modalChannel, setModalChannel] = useState<CrmChannel>("WhatsApp");
  const [modalResult, setModalResult] = useState("Sem resposta");
  const [modalRejectionReason, setModalRejectionReason] = useState("Preço elevado");
  const [modalNotes, setModalNotes] = useState("");
  const [modalAttachment, setModalAttachment] = useState("");
  const [modalAttachmentName, setModalAttachmentName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await serviceOrders.quotesCrm({
        status: statusFilter !== "all" ? statusFilter : undefined,
        query: searchQuery.trim() || undefined,
		in_progress: periodMode === "none",
		...crmPeriodParams(periodMode, fromDate, toDate),
      });
      setData(res);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Falha ao carregar CRM de orçamentos", "error");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, periodMode, fromDate, toDate, searchQuery, onToast]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleModalSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!actionModal) return;
    setSubmitting(true);
    try {
      if (actionModal.type === "follow_up") {
        await serviceOrders.recordFollowUp(actionModal.order.name, modalChannel, modalResult, modalNotes);
        onToast("Follow-up registrado com sucesso!", "success");
      } else if (actionModal.type === "approve") {
        await serviceOrders.decideBudget(actionModal.order.name, {
          decision: "approve",
          channel: modalChannel,
          notes: modalNotes,
          attachment: modalChannel !== "Link" ? modalAttachment : undefined,
        });
        onToast("Orçamento aprovado com sucesso!", "success");
      } else if (actionModal.type === "reject") {
        const finalNotes = modalRejectionReason + (modalNotes.trim() ? ` — ${modalNotes.trim()}` : "");
        await serviceOrders.decideBudget(actionModal.order.name, {
          decision: "reject",
          channel: modalChannel,
          notes: finalNotes,
        });
        onToast("Orçamento reprovado e registrado.", "success");
      }
      setActionModal(null);
      setModalNotes("");
      setModalAttachment("");
      setModalAttachmentName("");
      void loadData();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Falha ao executar ação", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const summary = data?.summary ?? {
    pending_count: 0,
    approved_count: 0,
    rejected_count: 0,
    expired_count: 0,
    conversion_rate: 0,
  };

  return (
    <div className="mx-auto max-w-7xl space-y-5" data-testid="quotes-crm-screen">
      {/* Header Banner */}
      <Card className="overflow-hidden border-tec-orange/20 p-0">
        <div className="border-b border-tec-border/20 bg-tec-field/35 px-5 py-5 sm:px-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-start gap-3">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-card bg-tec-orange/15 text-tec-orange">
                <FileText size={22} />
              </span>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-tec-orange">CRM Comercial</p>
                <h2 className="mt-1 text-xl font-bold text-white">Funil de Orçamentos</h2>
                <p className="mt-1 max-w-2xl text-sm leading-6 text-tec-subtle">
                  Acompanhe propostas enviadas, agilize follow-ups pelo WhatsApp e registre decisões de aprovação ou recusa do cliente.
                </p>
              </div>
            </div>
            <span className="inline-flex items-center gap-2 text-xs font-semibold text-tec-muted">
              <TrendingUp size={15} /> Conversão calculada em tempo real
            </span>
          </div>
        </div>
      </Card>

      {/* Top Statbar */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-tec-subtle">Pendentes de Resposta</span>
            <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-xs font-bold text-amber-400">
              Aguardando
            </span>
          </div>
          <p className="mt-2 text-2xl font-bold text-white">{summary.pending_count}</p>
          <p className="mt-1 text-xs text-tec-muted">Orçamentos em análise com o cliente</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-tec-subtle">Aprovados</span>
            <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-xs font-bold text-emerald-400">
              Convertidos
            </span>
          </div>
          <p className="mt-2 text-2xl font-bold text-white">{summary.approved_count}</p>
          <p className="mt-1 text-xs text-tec-muted">Liberados para bancada técnica</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-tec-subtle">Recusados / Perdidos</span>
            <span className="rounded-full bg-rose-500/20 px-2 py-0.5 text-xs font-bold text-rose-400">
              Perdas
            </span>
          </div>
          <p className="mt-2 text-2xl font-bold text-white">{summary.rejected_count}</p>
          <p className="mt-1 text-xs text-tec-muted">Recusados pelo cliente</p>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-tec-subtle">Taxa de Conversão</span>
            <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-xs font-bold text-blue-400">
              Eficiência
            </span>
          </div>
          <p className="mt-2 text-2xl font-bold text-white">{summary.conversion_rate}%</p>
          <p className="mt-1 text-xs text-tec-muted">Aprovações sobre o total decidido</p>
        </Card>
      </div>

      {/* Filters & Search */}
      <Card className="p-4">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-tec-border/15 pb-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-tec-subtle">Recorte</p>
              <p className="mt-1 text-sm font-semibold text-white">
                {periodMode === "none" ? "Aparelhos na loja" : "Histórico por período"}
              </p>
              <p className="mt-0.5 text-xs text-tec-muted">
                {periodMode === "none" ? "Padrão: sai somente quando a retirada é registrada." : "Inclui orçamentos de aparelhos já retirados."}
              </p>
            </div>
            <div className="flex w-full items-center gap-2 sm:w-auto">
              <div className="flex rounded-control border border-tec-border/40 bg-tec-field/50 p-1" aria-label="Modo de visualização">
                <button aria-label="Visualização em grid" className={`rounded px-2 py-1 ${viewMode === "grid" ? "bg-tec-orange text-white" : "text-tec-muted"}`} onClick={() => setViewMode("grid")} type="button"><LayoutGrid size={16} /></button>
                <button aria-label="Visualização em linha" className={`rounded px-2 py-1 ${viewMode === "list" ? "bg-tec-orange text-white" : "text-tec-muted"}`} onClick={() => setViewMode("list")} type="button"><List size={16} /></button>
              </div>
              <div className="relative flex-1 sm:w-80">
                <input type="text" placeholder="Buscar por cliente, aparelho ou OS..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void loadData(); }} className="tp-input w-full pr-8" />
                <Search className="absolute right-2.5 top-2.5 text-tec-muted" size={15} />
              </div>
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-wide text-tec-subtle">Status do orçamento</p>
            <div className="flex flex-wrap items-center gap-2">
            {[
              { id: "all", label: "Todos os status" },
              { id: "pending", label: "Pendentes" },
              { id: "approved", label: "Aprovados" },
              { id: "rejected", label: "Recusados" },
              { id: "expired", label: "Expirados" },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setStatusFilter(tab.id)}
                className={`rounded-control px-3.5 py-1.5 text-xs font-bold transition ${
                  statusFilter === tab.id
                    ? "bg-tec-orange text-white"
                    : "bg-tec-field/60 text-tec-subtle hover:bg-tec-field hover:text-white"
                }`}
              >
                {tab.label}
              </button>
            ))}
            </div>
          </div>

          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-bold uppercase tracking-wide text-tec-subtle">Período opcional</p>
              {periodMode !== "none" ? <button className="text-xs font-bold text-tec-orange" onClick={() => { setPeriodMode("none"); setFromDate(""); setToDate(""); }} type="button">Remover período</button> : null}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {([{"id":"7d","label":"Últimos 7 dias"},{"id":"14d","label":"Últimos 14 dias"},{"id":"custom","label":"Personalizado"}] as Array<{id: CrmPeriodMode; label: string}>).map((option) => <button className={`rounded-control px-3 py-1.5 text-xs font-bold ${periodMode === option.id ? "bg-tec-orange text-white" : "border border-tec-border/30 text-tec-subtle"}`} key={option.id} onClick={() => setPeriodMode(option.id)} type="button">{option.label}</button>)}
              {periodMode === "custom" ? <>
                <input aria-label="Data inicial do CRM" className="tp-input w-auto" onChange={(event) => setFromDate(event.target.value)} type="date" value={fromDate} />
                <span className="text-xs text-tec-muted">até</span>
                <input aria-label="Data final do CRM" className="tp-input w-auto" onChange={(event) => setToDate(event.target.value)} type="date" value={toDate} />
              </> : null}
            </div>
          </div>
        </div>
      </Card>

      {/* Items list */}
      {loading ? (
        <Card className="p-10 text-center text-sm text-tec-muted">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-tec-orange border-t-transparent" />
          <p className="mt-3">Carregando funil de orçamentos...</p>
        </Card>
      ) : !data?.items.length ? (
        <Card className="p-10 text-center text-sm text-tec-muted">
          Nenhum orçamento encontrado para os filtros selecionados.
        </Card>
      ) : (
        <div className={viewMode === "grid" ? "grid gap-4 lg:grid-cols-2 xl:grid-cols-3" : "space-y-3"}>
          {data.items.map((item: QuoteCrmItem) => {
            const followUps = item.follow_ups ?? [];
            const isItemPending = item.approval_status === "Pendente" || item.workflow_state === "Aguardando aprovação";
            const isItemApproved = item.approval_status === "Aprovado" || item.workflow_state === "Aprovado";
            const isItemRejected = item.approval_status === "Reprovado" || item.workflow_state === "Reprovado";
            const whatsappMsg = `Olá, ${item.contact_name}. Aqui é da Tecponto. Passando para verificar se você conseguiu analisar a proposta do seu ${item.device_label} (OS ${item.name}) no valor de ${formatCurrency(item.grand_total)}?`;
            const whatsappLink = buildWhatsAppUrl(item.phone, whatsappMsg);

            return (
              <Card key={item.name} className={`border-tec-border/30 p-4 transition hover:border-tec-border ${viewMode === "grid" ? "flex h-full flex-col" : ""}`}>
                <div className="flex flex-wrap items-start justify-between gap-3 border-b border-tec-border/15 pb-3">
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => onOpenOrder(item.name)}
                      className="text-base font-bold text-white hover:text-tec-orange hover:underline"
                    >
                      {item.name}
                    </button>
                    {isItemApproved ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                        <CheckCircle2 size={13} /> Aprovado
                      </span>
                    ) : isItemRejected ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 px-2.5 py-0.5 text-xs font-semibold text-rose-400">
                        <XCircle size={13} /> Recusado
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-400">
                        <Hourglass size={13} /> Aguardando ({item.days_pending}d)
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-tec-subtle">Total da Proposta</span>
                    <p className="text-base font-bold text-emerald-400">{formatCurrency(item.grand_total)}</p>
                  </div>
                </div>

                <div className="grid gap-3 pt-3 sm:grid-cols-3 text-xs">
                  <div>
                    <span className="text-tec-subtle">Cliente & Aparelho:</span>
                    <p className="mt-0.5 font-semibold text-white">{item.contact_name}</p>
                    <p className="text-tec-muted">{item.device_label}</p>
                  </div>
                  <div>
                    <span className="text-tec-subtle">Diagnóstico / Defeito:</span>
                    <p className="mt-0.5 text-white">{item.problem_found || item.reported_defect || "Não informado"}</p>
                  </div>
                  <div>
                    <span className="text-tec-subtle">Histórico da Decisão:</span>
                    <p className="mt-0.5 text-white">
                      {item.approval_notes ? item.approval_notes : isItemPending ? "Aguardando retorno do cliente" : "Sem notas adicionais"}
                    </p>
                  </div>
                </div>

                <div className="mt-3 border-t border-tec-border/15 pt-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-bold uppercase tracking-wide text-tec-subtle">Follow-ups</p>
                    <span className="text-xs text-tec-muted">{followUps.length} contato(s)</span>
                  </div>
                  {followUps.length ? (
                    <ol className="mt-2 space-y-2">
                      {followUps.slice(0, viewMode === "grid" ? 3 : 5).map((followUp, index) => (
                        <li className="relative border-l border-tec-orange/35 pl-3 text-xs" key={`${followUp.date}-${index}`}>
                          <div className="flex flex-wrap items-center gap-x-2 text-tec-subtle">
                            <span className="font-bold text-white">{followUp.channel}</span>
                            <span>{formatDateTime(followUp.date)}</span>
                          </div>
                          <p className="mt-0.5 text-tec-muted">{followUp.result} · {followUp.user}</p>
                          {followUp.notes ? <p className="mt-0.5 text-tec-subtle">{followUp.notes}</p> : null}
                        </li>
                      ))}
                    </ol>
                  ) : <p className="mt-2 text-xs text-tec-muted">Nenhum follow-up registrado.</p>}
                </div>

                <div className={`mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-tec-border/15 pt-3 ${viewMode === "grid" ? "mt-auto" : ""}`}>
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <button
                        aria-expanded={openActionsOrder === item.name}
                        aria-label={`Mais ações de ${item.name}`}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-control border border-tec-border/40 text-tec-muted hover:bg-tec-surface-hover hover:text-white"
                        onClick={() => setOpenActionsOrder((current) => current === item.name ? null : item.name)}
                        type="button"
                      >
                        <Ellipsis size={17} />
                      </button>
                      {openActionsOrder === item.name ? (
                        <div className="absolute bottom-10 left-0 z-20 min-w-52 rounded-control border border-tec-border bg-tec-surface p-1.5 shadow-xl">
                          {whatsappLink ? (
                            <a
                              href={whatsappLink}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center gap-2 rounded px-2.5 py-2 text-xs font-semibold text-tec-text hover:bg-tec-surface-hover"
                              onClick={() => setOpenActionsOrder(null)}
                            >
                              <Phone size={14} /> Cobrar pelo WhatsApp
                            </a>
                          ) : null}
                          <button
                            className="flex w-full items-center gap-2 rounded px-2.5 py-2 text-left text-xs font-semibold text-tec-text hover:bg-tec-surface-hover"
                            onClick={() => {
                              setOpenActionsOrder(null);
                              setActionModal({ type: "follow_up", order: item });
                              setModalNotes("");
                            }}
                            type="button"
                          >
                            <FileText size={14} /> Registrar follow-up manual
                          </button>
                        </div>
                      ) : null}
                    </div>
                    {isItemPending && (
                      <>
                        <Button
                          className="bg-emerald-600 hover:bg-emerald-500 text-white"
                          onClick={() => {
                            setActionModal({ type: "approve", order: item });
                            setModalNotes("");
                          }}
                        >
                          Aprovar
                        </Button>
                        <Button
                          variant="secondary"
                          className="text-rose-400 border-rose-500/40 hover:bg-rose-500/10"
                          onClick={() => {
                            setActionModal({ type: "reject", order: item });
                            setModalNotes("");
                          }}
                        >
                          Recusar
                        </Button>
                      </>
                    )}
                    <Button variant="primary" onClick={() => onOpenOrder(item.name)}>
                      Abrir OS
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Action Modal */}
      {actionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <Card className="w-full max-w-lg p-5">
            <div className="flex items-center justify-between border-b border-tec-border pb-3">
              <h3 className="text-base font-bold text-white">
                {actionModal.type === "follow_up" && `Registrar Follow-up · ${actionModal.order.name}`}
                {actionModal.type === "approve" && `Aprovar Orçamento · ${actionModal.order.name}`}
                {actionModal.type === "reject" && `Reprovar Orçamento · ${actionModal.order.name}`}
              </h3>
              <button
                type="button"
                onClick={() => setActionModal(null)}
                className="text-tec-muted hover:text-white"
              >
                ✕
              </button>
            </div>

            <form className="mt-4 space-y-3" onSubmit={handleModalSubmit}>
              {actionModal.type === "follow_up" && (
                <>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label className="block text-xs font-semibold text-tec-subtle">Canal de contato</label>
                      <ChannelPills onChange={setModalChannel} value={modalChannel} />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-tec-subtle">Resultado</label>
                      <select
                        className="tp-input mt-1 w-full"
                        value={modalResult}
                        onChange={(e) => setModalResult(e.target.value)}
                      >
                        <option value="Sem resposta">Sem resposta / Não atendeu</option>
                        <option value="Pediu mais tempo">Pediu mais tempo</option>
                        <option value="Dúvida técnica">Dúvida técnica</option>
                        <option value="Negociando desconto">Negociando desconto</option>
                        <option value="Vai decidir hoje">Vai decidir hoje</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-tec-subtle">Observações</label>
                    <textarea
                      rows={3}
                      className="tp-input mt-1 w-full"
                      value={modalNotes}
                      onChange={(e) => setModalNotes(e.target.value)}
                      placeholder="Detalhes da conversa ou combinados com o cliente..."
                    />
                  </div>
                </>
              )}

              {actionModal.type === "approve" && (
                <>
                  <div>
                    <label className="block text-xs font-semibold text-tec-subtle">Canal da Autorização</label>
                    <ChannelPills includeLink onChange={setModalChannel} value={modalChannel} />
                  </div>
                  {modalChannel !== "Link" && (
                    <div>
                      <label className="block text-xs font-semibold text-tec-amber">Comprovante / Documento anexo (obrigatório)</label>
                      <label className="mt-1 flex cursor-pointer items-center gap-3 rounded-control border border-dashed border-tec-amber/50 bg-tec-amber/5 p-3 text-sm text-tec-subtle hover:bg-tec-amber/10">
                        <Upload className="text-tec-amber" size={18} />
                        <span>{modalAttachmentName || "Selecionar foto, print ou PDF (máx. 8 MB)"}</span>
                        <input
                          accept="image/jpeg,image/png,image/webp,application/pdf"
                          className="sr-only"
                          onChange={async (event) => {
                            const file = event.target.files?.[0];
                            if (!file) return;
                            try {
                              setModalAttachment(await readPrivateEvidence(file));
                              setModalAttachmentName(file.name);
                            } catch (error) {
                              setModalAttachment("");
                              setModalAttachmentName("");
                              onToast(error instanceof Error ? error.message : "Comprovante inválido.", "error");
                            }
                          }}
                          type="file"
                        />
                      </label>
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-semibold text-tec-subtle">Observações (opcional)</label>
                    <input
                      type="text"
                      className="tp-input mt-1 w-full"
                      value={modalNotes}
                      onChange={(e) => setModalNotes(e.target.value)}
                      placeholder="Ex.: Aprovado pelo cliente sem alterações"
                    />
                  </div>
                </>
              )}

              {actionModal.type === "reject" && (
                <>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label className="block text-xs font-semibold text-tec-subtle">Motivo da Recusa</label>
                      <select
                        className="tp-input mt-1 w-full"
                        value={modalRejectionReason}
                        onChange={(e) => setModalRejectionReason(e.target.value)}
                      >
                        <option value="Preço elevado">Preço elevado / Achou caro</option>
                        <option value="Inviável financeiramente">Inviável financeiramente</option>
                        <option value="Prefere comprar novo">Prefere comprar novo</option>
                        <option value="Prazo incompatível">Prazo incompatível</option>
                        <option value="Desistiu do reparo">Desistiu do reparo</option>
                        <option value="Outro">Outro motivo</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-tec-subtle">Canal da Resposta</label>
                      <ChannelPills includeLink onChange={setModalChannel} value={modalChannel} />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-tec-subtle">Observações adicionais</label>
                    <input
                      type="text"
                      className="tp-input mt-1 w-full"
                      value={modalNotes}
                      onChange={(e) => setModalNotes(e.target.value)}
                      placeholder="Detalhes da recusa..."
                    />
                  </div>
                </>
              )}

              <div className="flex items-center justify-end gap-2 pt-3">
                <Button disabled={submitting} type="button" variant="secondary" onClick={() => setActionModal(null)}>
                  Cancelar
                </Button>
                <Button
                  disabled={submitting}
                  type="submit"
                  variant="primary"
                  className={actionModal.type === "reject" ? "bg-rose-600 hover:bg-rose-500 text-white" : undefined}
                >
                  {submitting ? "Gravando..." : "Confirmar"}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  );
}
