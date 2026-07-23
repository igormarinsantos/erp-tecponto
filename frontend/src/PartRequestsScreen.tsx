import { useEffect, useMemo, useState } from "react";
import { ClipboardList, PackagePlus, Search } from "lucide-react";

import { partRequests, type RepairPartOption, type TechnicalPartRequest } from "./api";
import { BadgeStatus, Button, Card, DataTable, Modal, StatBar, type TableColumn } from "./ui";

export function PartRequestsScreen({ onOpenServiceOrder }: { onOpenServiceOrder: (name: string) => void }) {
  const [items, setItems] = useState<TechnicalPartRequest[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  const load = async () => {
    setState("loading");
    try {
      const response = await partRequests.listMine();
      setItems(response.items);
      setState("ready");
    } catch {
      setState("error");
    }
  };

  useEffect(() => { void load(); }, []);
  const columns = useMemo<Array<TableColumn<TechnicalPartRequest>>>(() => [
    { key: "service_order", label: "OS", render: (row) => <span className="font-bold text-white">{row.service_order}</span> },
    { key: "part", label: "Peça solicitada", render: (row) => <span className="font-semibold text-tec-text">{row.item ?? row.free_description ?? "Peça não identificada"}</span> },
    { key: "qty", label: "Qtd.", render: (row) => row.qty.toLocaleString("pt-BR") },
    { key: "status", label: "Status", render: (row) => <BadgeStatus status={row.status} /> },
    { key: "requested_at", label: "Solicitada em", render: (row) => formatDate(row.requested_at) },
  ], []);
  const requested = items.filter((item) => item.status === "Solicitada").length;

  return <div className="space-y-4">
    <StatBar items={[
      { key: "all", label: "Minhas solicitações", value: items.length, detail: "Pedidos da sua bancada", icon: <ClipboardList size={19} />, tone: "blue" },
      { key: "requested", label: "Aguardando compra", value: requested, detail: "Ainda não pedidas", icon: <PackagePlus size={19} />, tone: "amber" },
    ]} />
    {state === "error" ? <Card className="p-5 text-sm font-semibold text-tec-red">Não foi possível consultar suas solicitações.</Card> : null}
    <Card className="p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="text-xl font-bold text-white">Solicitações de peça</h2><p className="mt-1 text-sm text-tec-muted">Acompanhe somente o que você pediu para as suas OS.</p></div>
        <Button icon={<Search size={17} />} onClick={() => void load()} variant="secondary">Atualizar</Button>
      </div>
      <DataTable columns={columns} emptyLabel={state === "loading" ? "Carregando solicitações..." : "Nenhuma solicitação de peça aberta."} onRowClick={(row) => onOpenServiceOrder(row.service_order)} rows={items} tableMinWidthClassName="min-w-[720px]" />
    </Card>
  </div>;
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
    if (mode === "catalog" && !item) { setError("Selecione uma peça do catálogo ou use descrição livre."); return; }
    if (mode === "free" && !freeDescription.trim()) { setError("Descreva a peça necessária."); return; }
    if (!Number.isFinite(numericQty) || numericQty <= 0) { setError("Informe uma quantidade maior que zero."); return; }
    setSubmitting(true);
    try {
      await partRequests.create(serviceOrder, { item: mode === "catalog" ? item : undefined, free_description: mode === "free" ? freeDescription.trim() : undefined, qty: numericQty, notes: notes.trim() || undefined });
      onCreated(); onClose();
    } catch (caught) {
      setError(caught instanceof Error ? normalizeError(caught.message) : "Não foi possível registrar a solicitação.");
    } finally { setSubmitting(false); }
  }

  return <Modal className="max-w-2xl" onClose={onClose} open={open} title={`Solicitar peça para ${serviceOrder}`}>
    <div className="space-y-5">
      <p className="rounded-card border border-tec-blue/25 bg-tec-blue/10 p-3 text-sm text-tec-subtle">O pedido registra a necessidade e move a OS para <strong className="text-white">Aguardando peça</strong>. A compra continua sendo tratada pelo Gestor/Diretor.</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {(["catalog", "free"] as const).map((next) => <button className={`rounded-control border px-4 py-3 text-left text-sm font-bold ${mode === next ? "border-tec-orange bg-tec-orange/15 text-white" : "border-tec-border/20 bg-tec-field text-tec-subtle"}`} key={next} onClick={() => setMode(next)} type="button">{next === "catalog" ? "Peça do catálogo" : "Descrição livre"}<span className="mt-1 block text-xs font-medium text-tec-muted">{next === "catalog" ? "Vincule uma peça de Reparo" : "Ainda não cadastrada no estoque"}</span></button>)}
      </div>
      {mode === "catalog" ? <div className="space-y-3"><label className="block text-xs font-bold uppercase text-tec-muted">Buscar peça<input autoFocus className="tp-input mt-1 w-full" onChange={(event) => { setQuery(event.target.value); setItem(""); }} placeholder="Nome ou referência" value={query} /></label><div className="max-h-52 space-y-2 overflow-y-auto">{options.map((option) => <button className={`flex w-full items-center justify-between rounded-control border px-3 py-3 text-left text-sm ${item === option.item_code ? "border-tec-orange bg-tec-orange/10 text-white" : "border-tec-border/20 bg-tec-field text-tec-subtle"}`} key={option.item_code} onClick={() => setItem(option.item_code)} type="button"><span className="font-semibold">{option.item_name}</span><span className="text-xs text-tec-muted">{option.item_code}</span></button>)}{query && !options.length ? <p className="p-3 text-sm text-tec-muted">Nenhuma peça encontrada. Você pode usar descrição livre.</p> : null}</div></div> : <label className="block text-xs font-bold uppercase text-tec-muted">Peça necessária<textarea autoFocus className="tp-input mt-1 min-h-28 w-full resize-y" onChange={(event) => setFreeDescription(event.target.value)} placeholder="Ex.: tela OLED compatível para iPhone 12" value={freeDescription} /></label>}
      <div className="grid gap-3 sm:grid-cols-[160px_1fr]"><label className="block text-xs font-bold uppercase text-tec-muted">Quantidade<input className="tp-input mt-1 w-full" min="0.001" onChange={(event) => setQty(event.target.value)} step="0.001" type="number" value={qty} /></label><label className="block text-xs font-bold uppercase text-tec-muted">Observação<textarea className="tp-input mt-1 min-h-11 w-full resize-y" onChange={(event) => setNotes(event.target.value)} placeholder="Detalhes técnicos, urgência ou compatibilidade" value={notes} /></label></div>
      {error ? <p className="rounded-card border border-tec-red/25 bg-tec-red/10 p-3 text-sm font-semibold text-tec-red">{error}</p> : null}
      <div className="flex justify-end gap-2"><Button onClick={onClose} variant="secondary">Cancelar</Button><Button disabled={submitting} icon={<PackagePlus size={17} />} onClick={() => void submit()} variant="primary">{submitting ? "Registrando..." : "Solicitar peça"}</Button></div>
    </div>
  </Modal>;
}

function formatDate(value: string) { return value ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value.replace(" ", "T"))) : "-"; }
function normalizeError(value: string) { return value.replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim(); }
