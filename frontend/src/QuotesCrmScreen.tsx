import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  CheckCircle2,
  FileText,
  Hourglass,
  Phone,
  Search,
  TrendingUp,
  XCircle,
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

export function QuotesCrmScreen({
  onOpenOrder,
  onToast,
}: {
  onOpenOrder: (name: string) => void;
  onToast: (message: string, tone?: "success" | "error") => void;
}) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<QuotesCrmResponse | null>(null);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [searchQuery, setSearchQuery] = useState("");
  const [actionModal, setActionModal] = useState<{
    type: "follow_up" | "approve" | "reject";
    order: QuoteCrmItem;
  } | null>(null);
  const [modalChannel, setModalChannel] = useState<"WhatsApp" | "Telefone" | "Presencial" | "Link">("WhatsApp");
  const [modalResult, setModalResult] = useState("Sem resposta");
  const [modalRejectionReason, setModalRejectionReason] = useState("Preço elevado");
  const [modalNotes, setModalNotes] = useState("");
  const [modalAttachment, setModalAttachment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await serviceOrders.quotesCrm({
        status: statusFilter !== "all" ? statusFilter : undefined,
        query: searchQuery.trim() || undefined,
      });
      setData(res);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Falha ao carregar CRM de orçamentos", "error");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchQuery, onToast]);

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
          attachment: modalChannel !== "Link" ? (modalAttachment.trim() || "Autorização registrada no balcão") : undefined,
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
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {[
              { id: "all", label: "Todos" },
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
          <div className="w-full sm:w-80">
            <div className="relative">
              <input
                type="text"
                placeholder="Buscar por cliente, aparelho ou OS..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void loadData(); }}
                className="tp-input w-full pr-8"
              />
              <Search className="absolute right-2.5 top-2.5 text-tec-muted" size={15} />
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
        <div className="space-y-3">
          {data.items.map((item: QuoteCrmItem) => {
            const isItemPending = item.approval_status === "Pendente" || item.workflow_state === "Aguardando aprovação";
            const isItemApproved = item.approval_status === "Aprovado" || item.workflow_state === "Aprovado";
            const isItemRejected = item.approval_status === "Reprovado" || item.workflow_state === "Reprovado";
            const whatsappMsg = `Olá, ${item.contact_name}. Aqui é da Tecponto. Passando para verificar se você conseguiu analisar a proposta do seu ${item.device_label} (OS ${item.name}) no valor de ${formatCurrency(item.grand_total)}?`;
            const whatsappLink = buildWhatsAppUrl(item.phone, whatsappMsg);

            return (
              <Card key={item.name} className="border-tec-border/30 p-4 transition hover:border-tec-border">
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

                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-tec-border/15 pt-3">
                  <div className="flex items-center gap-2">
                    {whatsappLink ? (
                      <a
                        href={whatsappLink}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 rounded-control border border-emerald-500/30 bg-emerald-950/20 px-3 py-1 text-xs font-bold text-emerald-400 hover:bg-emerald-900/30"
                      >
                        <Phone size={13} /> Cobrar WhatsApp
                      </a>
                    ) : null}
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setActionModal({ type: "follow_up", order: item });
                        setModalNotes("");
                      }}
                    >
                      Registrar Follow-up
                    </Button>
                  </div>
                  <div className="flex items-center gap-2">
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
                      <select
                        className="tp-input mt-1 w-full"
                        value={modalChannel}
                        onChange={(e) => setModalChannel(e.target.value as "WhatsApp" | "Telefone" | "Presencial" | "Link")}
                      >
                        <option value="WhatsApp">WhatsApp</option>
                        <option value="Ligação Telefônica">Ligação Telefônica</option>
                        <option value="Presencial / Balcão">Presencial / Balcão</option>
                        <option value="E-mail">E-mail</option>
                      </select>
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
                    <select
                      className="tp-input mt-1 w-full"
                      value={modalChannel}
                      onChange={(e) => setModalChannel(e.target.value as "WhatsApp" | "Telefone" | "Presencial" | "Link")}
                    >
                      <option value="WhatsApp">WhatsApp</option>
                      <option value="Presencial">Presencial / Balcão</option>
                      <option value="Telefone">Ligação Telefônica</option>
                      <option value="Link">Link Digital / Portal</option>
                    </select>
                  </div>
                  {modalChannel !== "Link" && (
                    <div>
                      <label className="block text-xs font-semibold text-tec-amber">Comprovante / Documento anexo (obrigatório)</label>
                      <input
                        type="text"
                        className="tp-input mt-1 w-full"
                        value={modalAttachment}
                        onChange={(e) => setModalAttachment(e.target.value)}
                        placeholder="Ex.: Anexo, áudio/print de conversa ou número do termo"
                      />
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
                      <select
                        className="tp-input mt-1 w-full"
                        value={modalChannel}
                        onChange={(e) => setModalChannel(e.target.value as "WhatsApp" | "Telefone" | "Presencial" | "Link")}
                      >
                        <option value="WhatsApp">WhatsApp</option>
                        <option value="Presencial">Presencial / Balcão</option>
                        <option value="Telefone">Ligação Telefônica</option>
                        <option value="Link">Link Digital / Portal</option>
                      </select>
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
