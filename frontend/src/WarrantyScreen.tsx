import { useState } from "react";
import { ArrowRight, CalendarDays, Search, ShieldCheck, Smartphone, Wrench } from "lucide-react";

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
		try {
			window.sessionStorage.setItem(WARRANTY_CHECKIN_CONTEXT_KEY, JSON.stringify({ customer: item.customer, customer_device: item.customer_device, original_service_order: item.status === "vigente" ? item.service_order : "", source_service_order: item.service_order, status: item.status }));
		} catch { onToast("Não foi possível preparar o check-in.", "error"); return; }
		onStartCheckin();
	};
	return <div className="space-y-5"><Card className="p-5"><div className="flex items-start gap-3"><span className="grid h-11 w-11 place-items-center rounded-card bg-tec-success/15 text-tec-success"><ShieldCheck size={21} /></span><div><h2 className="text-xl font-bold text-white">Consulta e atendimento de garantia</h2><p className="mt-1 text-sm text-tec-muted">Localize pela OS, IMEI/aparelho ou cliente. A decisão de retrabalho continua no motor do Bloco 5.</p></div></div><div className="mt-5 grid gap-3 md:grid-cols-[190px_1fr_auto]"><select className="tp-input" onChange={(event) => setSearchBy(event.target.value as typeof searchBy)} value={searchBy}><option value="os">Número da OS</option><option value="imei">IMEI / aparelho</option><option value="customer">Cliente</option></select><input className="tp-input" onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void search(); }} placeholder={searchBy === "os" ? "Ex.: OS-2026-00001" : searchBy === "imei" ? "Digite o IMEI" : "Nome ou código do cliente"} value={query} /><Button disabled={loading || !query.trim()} icon={<Search size={17} />} onClick={() => void search()} variant="primary">{loading ? "Consultando..." : "Consultar"}</Button></div></Card><section className="grid gap-4 xl:grid-cols-2">{items.map((item) => <Card className={item.status === "vigente" ? "border-tec-success/35 p-5" : "border-tec-red/35 p-5"} key={item.service_order}><div className="flex items-start justify-between gap-3"><div><button className="font-bold text-white hover:text-tec-orange" onClick={() => onOpenOrder(item.service_order)} type="button">{item.service_order}</button><p className="mt-1 text-sm text-tec-subtle">{item.customer} · {item.device_label}</p><p className="mt-1 text-xs text-tec-muted">IMEI: {item.imei_serial || "não informado"}</p></div><span className={item.status === "vigente" ? "rounded-full bg-tec-success/15 px-3 py-1 text-xs font-bold text-tec-success" : "rounded-full bg-tec-red/15 px-3 py-1 text-xs font-bold text-tec-red"}>{item.status === "vigente" ? "Garantia vigente" : "Garantia expirada"}</span></div><div className="mt-4 grid gap-2 rounded-control bg-tec-field/55 p-3 text-sm sm:grid-cols-3"><span className="flex items-center gap-2 text-tec-muted"><CalendarDays size={15} />Entrega: <strong className="text-tec-subtle">{item.delivery_date}</strong></span><span className="flex items-center gap-2 text-tec-muted"><ShieldCheck size={15} />Prazo: <strong className="text-tec-subtle">{item.warranty_days} dias</strong></span><span className="flex items-center gap-2 text-tec-muted"><ShieldCheck size={15} />Validade: <strong className="text-tec-subtle">{item.warranty_expiry}</strong></span></div><p className={item.status === "vigente" ? "mt-3 font-bold text-tec-success" : "mt-3 font-bold text-tec-red"}>{item.status === "vigente" ? `${item.remaining_days} dia(s) restante(s)` : "Garantia expirada — o novo atendimento será uma OS normal com cobrança."}</p><div className="mt-4"><p className="text-xs font-bold uppercase tracking-wide text-tec-muted">O que cobre</p><ul className="mt-2 space-y-1 text-sm text-tec-subtle">{item.covered_services.map((service) => <li className="flex gap-2" key={service}><Wrench className="mt-0.5 shrink-0 text-tec-orange" size={14} />{service}</li>)}</ul><p className="mt-2 text-xs leading-5 text-tec-muted">{item.coverage}</p></div>{canStart ? <Button className="mt-5 w-full" icon={item.status === "vigente" ? <ShieldCheck size={17} /> : <Smartphone size={17} />} onClick={() => start(item)} variant="primary">{item.status === "vigente" ? "Iniciar atendimento em garantia" : "Abrir nova OS normal"}</Button> : <p className="mt-5 text-xs font-semibold text-tec-muted">Consulta disponível; a abertura deve ser feita pelo Atendente ou Gestor.</p>}</Card>)}{!loading && query.trim() && !items.length ? <Card className="p-8 text-center text-sm text-tec-muted xl:col-span-2">Nenhuma garantia encontrada neste recorte.</Card> : null}</section></div>;
}
