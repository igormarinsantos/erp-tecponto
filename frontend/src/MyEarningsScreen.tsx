import { useCallback, useEffect, useMemo, useState } from "react";
import { BadgeDollarSign, CalendarDays, ClipboardList } from "lucide-react";

import { earnings, type OwnEarningItem } from "./api";
import { Card, DataTable, LayeredFilters, ListGridToggle, StatBar, type ListPresentation, type TableColumn } from "./ui";
import { parseServerDate } from "./utils/date";

const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const dateFormatter = new Intl.DateTimeFormat("pt-BR");

function formatDate(value: string) {
  const date = parseServerDate(value);
  return date ? dateFormatter.format(date) : value || "-";
}

export function MyEarningsScreen({ onOpenServiceOrder }: { onOpenServiceOrder: (name: string) => void }) {
  const [period, setPeriod] = useState("month");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [items, setItems] = useState<OwnEarningItem[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [presentation, setPresentation] = useState<ListPresentation>(() => window.localStorage.getItem("tecponto.my-earnings.presentation") === "grid" ? "grid" : "list");

  const load = useCallback(async () => {
    setStatus("loading");
    try {
      const response = await earnings.list(period, fromDate, toDate);
      setItems(response.items);
      setTotal(response.total);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [fromDate, period, toDate]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { window.localStorage.setItem("tecponto.my-earnings.presentation", presentation); }, [presentation]);

  const columns = useMemo<Array<TableColumn<OwnEarningItem>>>(() => [
    { key: "service_order", label: "OS", render: (row) => <span className="font-semibold text-white">{row.service_order}</span> },
    { key: "service_name", label: "Serviço", render: (row) => <span className="block max-w-[24rem] truncate" title={row.service_name}>{row.service_name}</span> },
    { key: "value", label: "Comissão", render: (row) => <span className="font-bold text-tec-success">{currency.format(row.value)}</span> },
    { key: "date", label: "Data", render: (row) => formatDate(row.date) },
    { key: "payment_status", label: "Situação", render: (row) => <span className="rounded-full bg-tec-field px-2.5 py-1 text-xs font-bold text-tec-subtle">{row.payment_status}</span> },
  ], []);

  return <div className="space-y-4">
    <div className="flex justify-end"><ListGridToggle onChange={setPresentation} value={presentation} /></div>
    <StatBar items={[{ key: "total", label: "No período", value: items.length, detail: "Lançamentos próprios", icon: <ClipboardList size={19} />, tone: "blue" }, { key: "value", label: "Comissão", value: total, displayValue: currency.format(total), detail: "Valor já lançado", icon: <BadgeDollarSign size={19} />, tone: "green" }]} />
    <LayeredFilters active={period} filters={[{ key: "month", label: "Este mês" }, { key: "7d", label: "Últimos 7 dias" }, { key: "all", label: "Tudo" }]} onClear={() => { setPeriod("month"); setFromDate(""); setToDate(""); }} onSelect={setPeriod} secondaryActive={period} secondaryFilters={[{ key: "custom", label: "Personalizado" }]} onSecondarySelect={setPeriod}>
      {period === "custom" ? <div className="grid gap-3 sm:grid-cols-2"><label className="text-xs font-bold text-tec-subtle">De<input className="tp-input mt-1 w-full" onChange={(event) => setFromDate(event.target.value)} type="date" value={fromDate} /></label><label className="text-xs font-bold text-tec-subtle">Até<input className="tp-input mt-1 w-full" onChange={(event) => setToDate(event.target.value)} type="date" value={toDate} /></label></div> : null}
    </LayeredFilters>
    {status === "error" ? <Card className="p-5 text-sm font-semibold text-tec-red">Não foi possível consultar suas comissões.</Card> : null}
    {presentation === "grid" ? <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{items.map((item) => <button className="rounded-card border border-tec-border/15 bg-tec-panel p-4 text-left transition hover:border-tec-orange/50 hover:bg-tec-field" key={`${item.service_order}-${item.service_name}-${item.date}`} onClick={() => onOpenServiceOrder(item.service_order)} type="button"><div className="flex items-start justify-between gap-3"><span className="font-bold text-white">{item.service_order}</span><span className="font-bold text-tec-success">{currency.format(item.value)}</span></div><p className="mt-2 truncate text-sm font-semibold text-tec-text" title={item.service_name}>{item.service_name}</p><div className="mt-4 flex items-center justify-between text-xs font-semibold text-tec-muted"><span>{formatDate(item.date)}</span><span>{item.payment_status}</span></div></button>)}{!items.length && status === "ready" ? <Card className="p-5 text-sm text-tec-muted sm:col-span-2 xl:col-span-3">Nenhuma comissão lançada neste período.</Card> : null}</section> : <DataTable columns={columns} emptyLabel={status === "loading" ? "Carregando comissões..." : "Nenhuma comissão lançada neste período."} onRowClick={(row) => onOpenServiceOrder(row.service_order)} rows={items} tableMinWidthClassName="min-w-[760px]" />}
    <p className="flex items-center gap-2 text-xs text-tec-muted"><CalendarDays size={14} /> Situação “Em folha” aparece quando o lançamento já está vinculado à folha do ERPNext.</p>
  </div>;
}
