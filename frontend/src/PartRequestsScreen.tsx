import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ClipboardList, Clock3, DollarSign, PackageCheck, PackagePlus, Search, Truck } from "lucide-react";

import { partRequests, type PurchasePartRequest, type RepairPartOption, type TechnicalPartRequest } from "./api";
import { ApprovalRequestModal } from "./ApprovalRequestModal";
import { BadgeStatus, Button, Card, DataTable, Modal, StatBar, type TableColumn } from "./ui";

type Toast = (message: string, tone?: "success" | "error") => void;
const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function PartRequestsScreen({
  onOpenServiceOrder,
  onToast = () => undefined,
}: {
  onOpenServiceOrder: (name: string) => void;
  onToast?: Toast;
}) {
  const [buyerMode, setBuyerMode] = useState(false);
  const [technicalItems, setTechnicalItems] = useState<TechnicalPartRequest[]>([]);
  const [purchaseItems, setPurchaseItems] = useState<PurchasePartRequest[]>([]);
  const [purchaseStats, setPurchaseStats] = useState<Array<{ key: string; label: string; value: number }>>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("open");
  const [orderModal, setOrderModal] = useState<PurchasePartRequest | null>(null);
  const [receiveModal, setReceiveModal] = useState<PurchasePartRequest | null>(null);
  const [receiveBusy, setReceiveBusy] = useState<string | null>(null);
  const [cancelModal, setCancelModal] = useState<PurchasePartRequest | null>(null);

  const load = async () => {
    setState("loading");
    try {
      const purchase = await partRequests.listPurchase(statusFilter, query);
      setBuyerMode(true);
      setPurchaseItems(purchase.items);
      setPurchaseStats(purchase.statbar);
      setState("ready");
    } catch {
      try {
        const response = await partRequests.listMine();
        setBuyerMode(false);
        setTechnicalItems(response.items);
        setState("ready");
      } catch {
        setState("error");
      }
    }
  };

  useEffect(() => { void load(); }, [statusFilter]);

  if (buyerMode) {
    return (
      <PurchasePartRequestsView
        cancelModal={cancelModal}
        items={purchaseItems}
        onCancelClose={() => setCancelModal(null)}
        onOpenServiceOrder={onOpenServiceOrder}
        onOrdered={() => { setOrderModal(null); void load(); }}
        onRefresh={() => void load()}
        onSearch={() => void load()}
        onShowCancel={setCancelModal}
        onShowOrder={setOrderModal}
        onShowReceive={setReceiveModal}
        onCloseReceive={() => setReceiveModal(null)}
        onToast={onToast}
        orderModal={orderModal}
        receiveModal={receiveModal}
        query={query}
        receiveBusy={receiveBusy}
        setQuery={setQuery}
        setReceiveBusy={setReceiveBusy}
        setStatusFilter={setStatusFilter}
        statbar={purchaseStats}
        state={state}
        statusFilter={statusFilter}
      />
    );
  }

  return <TechnicalPartRequestsView items={technicalItems} onOpenServiceOrder={onOpenServiceOrder} onRefresh={() => void load()} state={state} />;
}

function TechnicalPartRequestsView({
  items,
  onOpenServiceOrder,
  onRefresh,
  state,
}: {
  items: TechnicalPartRequest[];
  onOpenServiceOrder: (name: string) => void;
  onRefresh: () => void;
  state: "loading" | "ready" | "error";
}) {
  const columns = useMemo<Array<TableColumn<TechnicalPartRequest>>>(() => [
    { key: "service_order", label: "OS", render: (row) => <span className="font-bold text-white">{row.service_order}</span> },
    { key: "part", label: "Peca solicitada", render: (row) => <span className="font-semibold text-tec-text">{row.item ?? row.free_description ?? "Peca nao identificada"}</span> },
    { key: "qty", label: "Qtd.", render: (row) => row.qty.toLocaleString("pt-BR") },
    { key: "status", label: "Status", render: (row) => <BadgeStatus status={row.status} /> },
    { key: "requested_at", label: "Solicitada em", render: (row) => formatDate(row.requested_at) },
  ], []);
  const requested = items.filter((item) => item.status === "Solicitada").length;

  return <div className="space-y-4">
    <StatBar items={[
      { key: "all", label: "Minhas solicitacoes", value: items.length, detail: "Pedidos da sua bancada", icon: <ClipboardList size={19} />, tone: "blue" },
      { key: "requested", label: "Aguardando compra", value: requested, detail: "Ainda nao pedidas", icon: <PackagePlus size={19} />, tone: "amber" },
    ]} />
    {state === "error" ? <Card className="p-5 text-sm font-semibold text-tec-red">Nao foi possivel consultar suas solicitacoes.</Card> : null}
    <Card className="p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-xl font-bold text-white">Solicitacoes de peca</h2><p className="mt-1 text-sm text-tec-muted">Acompanhe somente o que voce pediu para as suas OS.</p></div>
        <Button icon={<Search size={17} />} onClick={onRefresh} variant="secondary">Atualizar</Button>
      </div>
      <DataTable columns={columns} emptyLabel={state === "loading" ? "Carregando solicitacoes..." : "Nenhuma solicitacao de peca aberta."} onRowClick={(row) => onOpenServiceOrder(row.service_order)} rows={items} tableMinWidthClassName="min-w-[720px]" />
    </Card>
  </div>;
}

function PurchasePartRequestsView({
  cancelModal,
  items,
  onCancelClose,
  onOpenServiceOrder,
  onOrdered,
  onRefresh,
  onSearch,
  onShowCancel,
  onShowOrder,
  onShowReceive,
  onCloseReceive,
  onToast,
  orderModal,
  receiveModal,
  query,
  receiveBusy,
  setQuery,
  setReceiveBusy,
  setStatusFilter,
  statbar,
  state,
  statusFilter,
}: {
  cancelModal: PurchasePartRequest | null;
  items: PurchasePartRequest[];
  onCancelClose: () => void;
  onOpenServiceOrder: (name: string) => void;
  onOrdered: () => void;
  onRefresh: () => void;
  onSearch: () => void;
  onShowCancel: (item: PurchasePartRequest) => void;
  onShowOrder: (item: PurchasePartRequest) => void;
  onShowReceive: (item: PurchasePartRequest) => void;
  onCloseReceive: () => void;
  onToast: Toast;
  orderModal: PurchasePartRequest | null;
  receiveModal: PurchasePartRequest | null;
  query: string;
  receiveBusy: string | null;
  setQuery: (value: string) => void;
  setReceiveBusy: (value: string | null) => void;
  setStatusFilter: (value: string) => void;
  statbar: Array<{ key: string; label: string; value: number }>;
  state: "loading" | "ready" | "error";
  statusFilter: string;
}) {
  const columns = useMemo<Array<TableColumn<PurchasePartRequest>>>(() => [
    { key: "service_order", label: "OS / urgencia", render: (row) => <div><span className="block font-bold text-white">{row.service_order}</span><span className="text-xs text-tec-muted">Prazo: {formatDate(row.service_order_deadline) || "Sem data"}</span></div> },
    { key: "part", label: "Peca", render: (row) => <span className="font-semibold text-tec-text">{row.item ?? row.free_description ?? "Peca nao identificada"}</span> },
    { key: "qty", label: "Qtd.", render: (row) => row.qty.toLocaleString("pt-BR") },
    { key: "status", label: "Status", render: (row) => <div className="flex flex-wrap items-center gap-2"><BadgeStatus status={row.status} />{row.is_late ? <span className="rounded-full bg-tec-red/15 px-2 py-1 text-xs font-bold text-tec-red">Atrasada</span> : null}</div> },
    { key: "supplier", label: "Fornecedor", render: (row) => row.supplier ?? "Nao pedido" },
    { key: "arrival", label: "Chegada", render: (row) => formatDate(row.expected_arrival) || "-" },
    { key: "cost", label: "Custo estimado", render: (row) => brl.format(row.estimated_cost || 0) },
    { key: "actions", label: "", className: "text-right", render: (row) => <PartRequestActions item={row} onOpenServiceOrder={onOpenServiceOrder} onReceive={async () => {
      setReceiveBusy(row.name);
      try {
        await partRequests.markReceived(row.name, row.item ?? undefined);
        onToast("Solicitacao marcada como recebida.", "success");
        onRefresh();
      } catch (error) {
        onToast(error instanceof Error ? error.message : "Nao foi possivel receber a peca.", "error");
      } finally {
        setReceiveBusy(null);
      }
    }} onShowCancel={onShowCancel} onShowOrder={onShowOrder} onShowReceive={onShowReceive} receiveBusy={receiveBusy === row.name} /> },
  ], [onOpenServiceOrder, onRefresh, onShowCancel, onShowOrder, onShowReceive, onToast, receiveBusy, setReceiveBusy]);

  return <div className="space-y-4">
    <StatBar items={statbar.map((item) => ({ ...item, detail: statDetail(item.key), icon: statIcon(item.key), tone: statTone(item.key) }))} />
    <Card className="p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-xl font-bold text-white">Lista de compras de pecas</h2><p className="mt-1 text-sm text-tec-muted">Fila ordenada pelo prazo prometido da OS. O WhatsApp continua fora; aqui fica o registro e a cobranca.</p></div>
        <Button icon={<Search size={17} />} onClick={onRefresh} variant="secondary">Atualizar</Button>
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {[
          ["open", "Abertas"],
          ["Solicitada", "Solicitadas"],
          ["Pedida", "Pedidas"],
          ["Recebida", "Recebidas"],
          ["Cancelada", "Canceladas"],
          ["all", "Todas"],
        ].map(([key, label]) => <button className={`rounded-full border px-3 py-2 text-xs font-bold ${statusFilter === key ? "border-tec-orange bg-tec-orange text-tec-graphite" : "border-tec-border/20 bg-tec-field text-tec-subtle"}`} key={key} onClick={() => setStatusFilter(key)} type="button">{label}</button>)}
        <form className="ml-auto flex min-w-[260px] flex-1 gap-2" onSubmit={(event) => { event.preventDefault(); onSearch(); }}>
          <input className="tp-input min-w-0 flex-1" onChange={(event) => setQuery(event.target.value)} placeholder="Buscar OS, peca ou solicitacao" value={query} />
          <Button icon={<Search size={16} />} type="submit">Buscar</Button>
        </form>
      </div>
      {state === "error" ? <p className="mb-3 rounded-card border border-tec-red/25 bg-tec-red/10 p-3 text-sm font-semibold text-tec-red">Nao foi possivel carregar a lista de compras.</p> : null}
      <DataTable columns={columns} emptyLabel={state === "loading" ? "Carregando compras..." : "Nenhuma solicitacao no filtro atual."} rows={items} tableMinWidthClassName="min-w-[1040px]" />
    </Card>
    {orderModal ? <MarkOrderedModal item={orderModal} onClose={onOrdered} onToast={onToast} /> : null}
    {receiveModal ? <ReceivePartModal item={receiveModal} onClose={onCloseReceive} onDone={onRefresh} onToast={onToast} /> : null}
    {cancelModal ? <CancelPartRequestModal item={cancelModal} onClose={onCancelClose} onDone={onRefresh} onToast={onToast} /> : null}
  </div>;
}

function PartRequestActions({ item, onOpenServiceOrder, onReceive, onShowCancel, onShowOrder, onShowReceive, receiveBusy }: {
  item: PurchasePartRequest;
  onOpenServiceOrder: (name: string) => void;
  onReceive: () => Promise<void>;
  onShowCancel: (item: PurchasePartRequest) => void;
  onShowOrder: (item: PurchasePartRequest) => void;
  onShowReceive: (item: PurchasePartRequest) => void;
  receiveBusy: boolean;
}) {
  return <div className="flex flex-wrap justify-end gap-2">
    <Button onClick={() => onOpenServiceOrder(item.service_order)} variant="ghost">OS</Button>
    {item.status === "Solicitada" ? <Button icon={<Truck size={15} />} onClick={() => onShowOrder(item)} variant="primary">Pedida</Button> : null}
    {item.status === "Pedida" ? <Button disabled={receiveBusy} icon={<PackageCheck size={15} />} onClick={() => item.item ? void onReceive() : onShowReceive(item)} variant="primary">{receiveBusy ? "Recebendo..." : "Recebida"}</Button> : null}
    {["Solicitada", "Pedida"].includes(item.status) ? <Button onClick={() => onShowCancel(item)} variant="danger">Cancelar</Button> : null}
  </div>;
}

function MarkOrderedModal({ item, onClose, onToast }: { item: PurchasePartRequest; onClose: () => void; onToast: Toast }) {
  const [supplier, setSupplier] = useState(item.supplier ?? "");
  const [expectedArrival, setExpectedArrival] = useState(item.expected_arrival || "");
  const [estimatedCost, setEstimatedCost] = useState(item.estimated_cost ? String(item.estimated_cost) : "");
  const [busy, setBusy] = useState(false);
  const [approval, setApproval] = useState<{ supplier: string; expected_arrival: string; estimated_cost?: number } | null>(null);

  const submit = async () => {
    const payload = { supplier: supplier.trim(), expected_arrival: expectedArrival, estimated_cost: Number(estimatedCost || 0) };
    if (!payload.supplier || !payload.expected_arrival) {
      onToast("Informe fornecedor e previsao de chegada.", "error");
      return;
    }
    setBusy(true);
    try {
      await partRequests.markOrdered(item.name, payload);
      onToast("Solicitacao marcada como pedida.", "success");
      onClose();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Nao foi possivel marcar como pedida.";
      if (message.toLowerCase().includes("aprova")) {
        setApproval(payload);
      } else {
        onToast(message, "error");
      }
    } finally {
      setBusy(false);
    }
  };

  return <>
    <Modal className="max-w-xl" onClose={onClose} open title={`Marcar ${item.name} como pedida`}>
      <div className="space-y-4">
        <p className="rounded-card border border-tec-border/15 bg-tec-field/60 p-3 text-sm text-tec-subtle">Registre o pedido feito ao fornecedor por fora. Se o custo estimado passar do teto, o motor vai exigir aprovacao.</p>
        <label className="block text-xs font-bold uppercase text-tec-muted">Fornecedor<input autoFocus className="tp-input mt-1 w-full" onChange={(event) => setSupplier(event.target.value)} placeholder="Nome exato do fornecedor" value={supplier} /></label>
        <label className="block text-xs font-bold uppercase text-tec-muted">Previsao de chegada<input className="tp-input mt-1 w-full" onChange={(event) => setExpectedArrival(event.target.value)} type="date" value={expectedArrival} /></label>
        <label className="block text-xs font-bold uppercase text-tec-muted">Custo estimado<input className="tp-input mt-1 w-full" min="0" onChange={(event) => setEstimatedCost(event.target.value)} step="0.01" type="number" value={estimatedCost} /></label>
        <div className="flex justify-end gap-2"><Button onClick={onClose} variant="ghost">Cancelar</Button><Button disabled={busy} onClick={() => void submit()} variant="primary">{busy ? "Validando..." : "Marcar pedida"}</Button></div>
      </div>
    </Modal>
    {approval ? <ApprovalRequestModal
      onClose={() => setApproval(null)}
      onCreated={onClose}
      onToast={onToast}
      open
      payload={approval}
      referenceName={item.name}
      requestType="part_purchase_above_threshold"
      title="Esta compra de peca ultrapassa o teto configurado. Deseja solicitar aprovacao do Gestor?"
    /> : null}
  </>;
}

function ReceivePartModal({ item, onClose, onDone, onToast }: { item: PurchasePartRequest; onClose: () => void; onDone: () => void; onToast: Toast }) {
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<RepairPartOption[]>([]);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      partRequests.searchOptions(query).then((response) => setOptions(response.items)).catch(() => setOptions([]));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [query]);
  const submit = async () => {
    if (!selected) { onToast("Confirme o Item de Reparo que chegou.", "error"); return; }
    setBusy(true);
    try {
      await partRequests.markReceived(item.name, selected);
      onToast("Peça recebida no Reparo e reservada para a OS.", "success");
      onDone(); onClose();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível receber a peça.", "error");
    } finally { setBusy(false); }
  };
  return <Modal className="max-w-xl" onClose={onClose} open title={`Confirmar item recebido — ${item.name}`}>
    <div className="space-y-4">
      <p className="rounded-card border border-tec-blue/25 bg-tec-blue/10 p-3 text-sm text-tec-subtle">O técnico descreveu: <strong className="text-white">{item.free_description || "Peça sem item definido"}</strong>. Escolha o Item de Reparo correto para gerar a entrada e a reserva da OS.</p>
      <label className="block text-xs font-bold uppercase text-tec-muted">Buscar Item de Reparo<input autoFocus className="tp-input mt-1 w-full" onChange={(event) => { setQuery(event.target.value); setSelected(""); }} placeholder="Nome ou código do item" value={query} /></label>
      <div className="max-h-60 space-y-2 overflow-y-auto">{options.map((option) => <button className={`flex w-full items-center justify-between rounded-control border px-3 py-3 text-left text-sm ${selected === option.item_code ? "border-tec-orange bg-tec-orange/10 text-white" : "border-tec-border/20 bg-tec-field text-tec-subtle"}`} key={option.item_code} onClick={() => setSelected(option.item_code)} type="button"><span className="font-semibold">{option.item_name}</span><span className="text-xs text-tec-muted">{option.item_code}</span></button>)}</div>
      <div className="flex justify-end gap-2"><Button onClick={onClose} variant="secondary">Cancelar</Button><Button disabled={!selected || busy} icon={<PackageCheck size={17} />} onClick={() => void submit()} variant="primary">{busy ? "Recebendo..." : "Receber e reservar"}</Button></div>
    </div>
  </Modal>;
}

function CancelPartRequestModal({ item, onClose, onDone, onToast }: { item: PurchasePartRequest; onClose: () => void; onDone: () => void; onToast: Toast }) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!reason.trim()) return;
    setBusy(true);
    try {
      await partRequests.cancel(item.name, reason.trim());
      onToast("Solicitacao cancelada.", "success");
      onDone();
      onClose();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Nao foi possivel cancelar.", "error");
    } finally {
      setBusy(false);
    }
  };
  return <Modal className="max-w-lg" onClose={onClose} open title={`Cancelar ${item.name}`}>
    <label className="block text-xs font-bold uppercase text-tec-muted">Motivo obrigatório<textarea className="tp-input mt-1 min-h-28 w-full" onChange={(event) => setReason(event.target.value)} value={reason} /></label>
    <div className="mt-4 flex justify-end gap-2"><Button onClick={onClose} variant="ghost">Voltar</Button><Button disabled={!reason.trim() || busy} onClick={() => void submit()} variant="danger">Cancelar solicitacao</Button></div>
  </Modal>;
}

export function PartRequestModal({
  onClose,
  onCreated,
  open,
  serviceOrder,
}: {
  onClose: () => void;
  onCreated: () => void;
  open: boolean;
  serviceOrder: string;
}) {
  const [mode, setMode] = useState<"catalog" | "free">("catalog");
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<RepairPartOption[]>([]);
  const [item, setItem] = useState("");
  const [freeDescription, setFreeDescription] = useState("");
  const [qty, setQty] = useState("1");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setMode("catalog"); setQuery(""); setOptions([]); setItem(""); setFreeDescription(""); setQty("1"); setNotes(""); setError(null); setSubmitting(false);
  }, [open, serviceOrder]);
  useEffect(() => {
    if (!open || mode !== "catalog") return;
    const timer = window.setTimeout(() => {
      partRequests.searchOptions(query).then((response) => setOptions(response.items)).catch(() => setOptions([]));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [open, mode, query]);

  async function submit() {
    setError(null);
    const numericQty = Number(qty);
    if (mode === "catalog" && !item) { setError("Selecione uma peca do catalogo ou use descricao livre."); return; }
    if (mode === "free" && !freeDescription.trim()) { setError("Descreva a peca necessaria."); return; }
    if (!Number.isFinite(numericQty) || numericQty <= 0) { setError("Informe uma quantidade maior que zero."); return; }
    setSubmitting(true);
    try {
      await partRequests.create(serviceOrder, { item: mode === "catalog" ? item : undefined, free_description: mode === "free" ? freeDescription.trim() : undefined, qty: numericQty, notes: notes.trim() || undefined });
      onCreated(); onClose();
    } catch (caught) {
      setError(caught instanceof Error ? normalizeError(caught.message) : "Nao foi possivel registrar a solicitacao.");
    } finally { setSubmitting(false); }
  }

  return <Modal className="max-w-2xl" onClose={onClose} open={open} title={`Solicitar peca para ${serviceOrder}`}>
    <div className="space-y-5">
      <p className="rounded-card border border-tec-blue/25 bg-tec-blue/10 p-3 text-sm text-tec-subtle">O pedido registra a necessidade e move a OS para <strong className="text-white">Aguardando peca</strong>. A compra continua sendo tratada pelo Gestor/Diretor.</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {(["catalog", "free"] as const).map((next) => <button className={`rounded-control border px-4 py-3 text-left text-sm font-bold ${mode === next ? "border-tec-orange bg-tec-orange/15 text-white" : "border-tec-border/20 bg-tec-field text-tec-subtle"}`} key={next} onClick={() => setMode(next)} type="button">{next === "catalog" ? "Peca do catalogo" : "Descricao livre"}<span className="mt-1 block text-xs font-medium text-tec-muted">{next === "catalog" ? "Vincule uma peca de Reparo" : "Ainda nao cadastrada no estoque"}</span></button>)}
      </div>
      {mode === "catalog" ? <div className="space-y-3"><label className="block text-xs font-bold uppercase text-tec-muted">Buscar peca<input autoFocus className="tp-input mt-1 w-full" onChange={(event) => { setQuery(event.target.value); setItem(""); }} placeholder="Nome ou referencia" value={query} /></label><div className="max-h-52 space-y-2 overflow-y-auto">{options.map((option) => <button className={`flex w-full items-center justify-between rounded-control border px-3 py-3 text-left text-sm ${item === option.item_code ? "border-tec-orange bg-tec-orange/10 text-white" : "border-tec-border/20 bg-tec-field text-tec-subtle"}`} key={option.item_code} onClick={() => setItem(option.item_code)} type="button"><span className="font-semibold">{option.item_name}</span><span className="text-xs text-tec-muted">{option.item_code}</span></button>)}{query && !options.length ? <p className="p-3 text-sm text-tec-muted">Nenhuma peca encontrada. Voce pode usar descricao livre.</p> : null}</div></div> : <label className="block text-xs font-bold uppercase text-tec-muted">Peca necessaria<textarea autoFocus className="tp-input mt-1 min-h-28 w-full resize-y" onChange={(event) => setFreeDescription(event.target.value)} placeholder="Ex.: tela OLED compativel para iPhone 12" value={freeDescription} /></label>}
      <div className="grid gap-3 sm:grid-cols-[160px_1fr]"><label className="block text-xs font-bold uppercase text-tec-muted">Quantidade<input className="tp-input mt-1 w-full" min="0.001" onChange={(event) => setQty(event.target.value)} step="0.001" type="number" value={qty} /></label><label className="block text-xs font-bold uppercase text-tec-muted">Observacao<textarea className="tp-input mt-1 min-h-11 w-full resize-y" onChange={(event) => setNotes(event.target.value)} placeholder="Detalhes tecnicos, urgencia ou compatibilidade" value={notes} /></label></div>
      {error ? <p className="rounded-card border border-tec-red/25 bg-tec-red/10 p-3 text-sm font-semibold text-tec-red">{error}</p> : null}
      <div className="flex justify-end gap-2"><Button onClick={onClose} variant="secondary">Cancelar</Button><Button disabled={submitting} icon={<PackagePlus size={17} />} onClick={() => void submit()} variant="primary">{submitting ? "Registrando..." : "Solicitar peca"}</Button></div>
    </div>
  </Modal>;
}

function statDetail(key: string) {
  return ({ requested: "Aguardando pedido", ordered: "Com fornecedor", late: "Passou da previsao", received_month: "Entraram no mes" } as Record<string, string>)[key] ?? "Fila de compras";
}

function statIcon(key: string) {
  if (key === "requested") return <PackagePlus size={19} />;
  if (key === "ordered") return <Truck size={19} />;
  if (key === "late") return <AlertTriangle size={19} />;
  if (key === "received_month") return <PackageCheck size={19} />;
  return <DollarSign size={19} />;
}

function statTone(key: string): "blue" | "orange" | "green" | "amber" {
  if (key === "requested") return "amber";
  if (key === "ordered") return "blue";
  if (key === "late") return "orange";
  if (key === "received_month") return "green";
  return "orange";
}

function formatDate(value: string) {
  if (!value) return "";
  const date = new Date(value.includes("T") ? value : value.replace(" ", "T"));
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("pt-BR", value.length <= 10 ? { dateStyle: "short" } : { dateStyle: "short", timeStyle: "short" }).format(date);
}

function normalizeError(value: string) { return value.replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim(); }
