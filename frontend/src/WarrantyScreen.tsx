import { useState, type ReactNode } from "react";
import { CalendarDays, CheckCircle2, ChevronRight, Clock3, Search, ShieldCheck, Smartphone, Wrench, XCircle } from "lucide-react";

import { checkin, type ServiceWarrantyResult } from "./api";
import { Button, Card } from "./ui";

export const WARRANTY_CHECKIN_CONTEXT_KEY = "tecponto.warranty.checkin-context";

export function WarrantyScreen({ onOpenOrder, onStartCheckin, onToast }: { onOpenOrder: (name: string) => void; onStartCheckin: () => void; onToast: (message: string, tone?: "success" | "error") => void }) {
  const [searchBy, setSearchBy] = useState<"os" | "imei" | "customer">("os");
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<ServiceWarrantyResult[]>([]);
  const [canStart, setCanStart] = useState(false);
  const [loading, setLoading] = useState(false);
  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try { const response = await checkin.searchWarranties(query.trim(), searchBy); setItems(response.items); setCanStart(response.can_start_service); }
    catch (caught) { onToast(caught instanceof Error ? caught.message : "Não foi possível consultar a garantia.", "error"); }
    finally { setLoading(false); }
  };
  const start = (item: ServiceWarrantyResult) => {
    if (!canStart) { onToast("Seu papel permite consultar, mas não abrir um atendimento.", "error"); return; }
    try { window.sessionStorage.setItem(WARRANTY_CHECKIN_CONTEXT_KEY, JSON.stringify({ customer: item.customer, customer_device: item.customer_device, original_service_order: item.status === "vigente" ? item.service_order : "", source_service_order: item.service_order, status: item.status })); }
    catch { onToast("Não foi possível preparar o check-in.", "error"); return; }
    onStartCheckin();
  };
  const inputLabel = searchBy === "os" ? "Número da OS" : searchBy === "imei" ? "IMEI ou aparelho" : "Cliente";
  const placeholder = searchBy === "os" ? "Ex.: OS-2026-00001" : searchBy === "imei" ? "Digite o IMEI ou modelo" : "Nome ou código do cliente";
  return <div className="mx-auto max-w-6xl space-y-5" data-testid="warranty-screen">
    <Card className="overflow-hidden border-tec-success/20 p-0">
      <div className="border-b border-tec-border/20 bg-tec-field/35 px-5 py-5 sm:px-6"><div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div className="flex items-start gap-3"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-card bg-tec-success/15 text-tec-success"><ShieldCheck size={22} /></span><div><p className="text-xs font-bold uppercase tracking-wide text-tec-success">Pós-venda</p><h2 className="mt-1 text-xl font-bold text-white">Atender garantia</h2><p className="mt-1 max-w-2xl text-sm leading-6 text-tec-subtle">Consulte a OS original, confira a cobertura e inicie o atendimento correto sem perder o histórico da entrega.</p></div></div><span className="inline-flex items-center gap-2 text-xs font-semibold text-tec-muted"><Clock3 size={15} />A garantia cobre o serviço, não a peça do cliente.</span></div></div>
      <div className="grid gap-3 p-5 sm:grid-cols-[190px_1fr_auto] sm:p-6"><label><span className="mb-1.5 block text-xs font-bold text-tec-muted">Buscar por</span><select className="tp-input" onChange={(event) => setSearchBy(event.target.value as typeof searchBy)} value={searchBy}><option value="os">Número da OS</option><option value="imei">IMEI / aparelho</option><option value="customer">Cliente</option></select></label><label><span className="mb-1.5 block text-xs font-bold text-tec-muted">{inputLabel}</span><input className="tp-input" onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void search(); }} placeholder={placeholder} value={query} /></label><div className="flex items-end"><Button className="w-full sm:w-auto" disabled={loading || !query.trim()} icon={<Search size={17} />} onClick={() => void search()} variant="primary">{loading ? "Consultando..." : "Consultar"}</Button></div></div>
    </Card>
    {items.length ? <p className="px-1 text-sm font-semibold text-tec-subtle">{items.length} garantia{items.length === 1 ? " localizada" : "s localizadas"}</p> : null}
    <section className="grid gap-4 xl:grid-cols-2">{items.map((item) => <WarrantyCard canStart={canStart} item={item} key={item.service_order} onOpenOrder={onOpenOrder} onStart={start} />)}{!loading && query.trim() && !items.length ? <Card className="p-10 text-center text-sm text-tec-muted xl:col-span-2">Nenhuma garantia encontrada neste recorte.</Card> : null}</section>
  </div>;
}

function WarrantyCard({ canStart, item, onOpenOrder, onStart }: { canStart: boolean; item: ServiceWarrantyResult; onOpenOrder: (name: string) => void; onStart: (item: ServiceWarrantyResult) => void }) {
  const active = item.status === "vigente";
  const StatusIcon = active ? CheckCircle2 : XCircle;
  return <Card className={`border p-0 ${active ? "border-tec-success/30" : "border-tec-red/30"}`}><div className="flex items-start justify-between gap-3 border-b border-tec-border/15 px-5 py-4"><div className="min-w-0"><button className="inline-flex items-center gap-1 font-bold text-white hover:text-tec-orange" onClick={() => onOpenOrder(item.service_order)} type="button">{item.service_order}<ChevronRight size={15} /></button><p className="mt-1 truncate text-sm text-tec-subtle">{item.customer} · {item.device_label}</p><p className="mt-1 text-xs text-tec-muted">IMEI: <span className="font-medium text-tec-subtle">{item.imei_serial || "não informado"}</span></p></div><span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${active ? "bg-tec-success/15 text-tec-success" : "bg-tec-red/15 text-tec-red"}`}><StatusIcon size={14} />{active ? "Vigente" : "Expirada"}</span></div><div className="space-y-4 p-5"><div className="grid grid-cols-2 gap-3 sm:grid-cols-3"><Fact icon={<CalendarDays size={15} />} label="Entregue em" value={item.delivery_date} /><Fact icon={<ShieldCheck size={15} />} label="Validade" value={item.warranty_expiry} /><Fact icon={<Clock3 size={15} />} label="Prazo" value={`${item.warranty_days} dias`} /></div><div className={`rounded-control px-3 py-2.5 text-sm font-bold ${active ? "bg-tec-success/10 text-tec-success" : "bg-tec-red/10 text-tec-red"}`}>{active ? `${item.remaining_days} dia(s) restante(s) de cobertura` : "Prazo encerrado: o novo atendimento será uma OS normal."}</div><div><p className="text-xs font-bold uppercase tracking-wide text-tec-muted">Cobertura desta garantia</p><ul className="mt-2 space-y-1.5 text-sm text-tec-subtle">{item.covered_services.map((service) => <li className="flex gap-2" key={service}><Wrench className="mt-0.5 shrink-0 text-tec-orange" size={14} />{service}</li>)}</ul><p className="mt-2 text-xs leading-5 text-tec-muted">{item.coverage}</p></div>{canStart ? <Button className="w-full" icon={active ? <ShieldCheck size={17} /> : <Smartphone size={17} />} onClick={() => onStart(item)} variant="primary">{active ? "Iniciar atendimento em garantia" : "Abrir nova OS normal"}</Button> : <p className="rounded-control bg-tec-field/50 px-3 py-2.5 text-xs font-semibold leading-5 text-tec-muted">Seu papel pode consultar. A abertura do atendimento é feita por Atendente ou Gestor.</p>}</div></Card>;
}

function Fact({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="min-w-0 rounded-control bg-tec-field/50 px-3 py-2.5"><span className="flex items-center gap-1.5 text-xs text-tec-muted">{icon}{label}</span><strong className="mt-1 block truncate text-sm text-tec-subtle">{value || "-"}</strong></div>;
}
