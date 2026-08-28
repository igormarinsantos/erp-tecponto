import { useEffect, useState, type ReactNode } from "react";
import { BarChart3, Building2, ReceiptText, Settings2, ShieldCheck, Users, WalletCards } from "lucide-react";

import { balcao, type AdministrativeSalesReport, type NavigationTarget } from "./api";
import { Button, Card, LayeredFilters, StatBar } from "./ui";

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

type Period = "today" | "7d" | "month";

export function AdministrativeCenterScreen({
  canViewDirectorFinancial,
  canOpenSystemSettings,
  onNavigate,
  onToast,
}: {
  canViewDirectorFinancial: boolean;
  canOpenSystemSettings: boolean;
  onNavigate: (target: NavigationTarget) => void;
  onToast: (message: string, tone?: "success" | "error") => void;
}) {
  const [period, setPeriod] = useState<Period>("month");
  const [report, setReport] = useState<AdministrativeSalesReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void balcao.getAdministrativeSalesReport(period)
      .then((value) => { if (!cancelled) setReport(value); })
      .catch((error) => { if (!cancelled) onToast(error instanceof Error ? error.message : "Não foi possível carregar o relatório de vendas.", "error"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [onToast, period]);

  return <div className="space-y-5" data-testid="administrative-center-screen">
    <section className="grid gap-3 md:grid-cols-3">
      <AdminAction icon={<Users size={20} />} label="Pessoas e acessos" detail="Contas, papéis e controles individuais." onClick={() => onNavigate("user-management")} />
      <AdminAction icon={<WalletCards size={20} />} label="Caixa e extrato" detail="Sessão, conferência e movimentos da gaveta." onClick={() => onNavigate("cash-statement")} />
      <AdminAction icon={<Settings2 size={20} />} label="Configurações da loja" detail={canOpenSystemSettings ? "Operação, identidade, SLA e taxas." : "Disponível a administradores do sistema."} disabled={!canOpenSystemSettings} onClick={() => onNavigate("administration-settings")} />
    </section>

    <Card className="p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-white"><BarChart3 className="text-tec-orange" size={20} /><h2 className="text-lg font-bold">Relatório de vendas</h2></div>
          <p className="mt-1 text-sm text-tec-subtle">Notas, recebimentos e movimentos reais, sem contabilidade paralela.</p>
        </div>
        <span className="inline-flex items-center gap-2 text-xs font-semibold text-tec-muted"><ShieldCheck size={15} className="text-tec-success" />Somente leitura</span>
      </div>
      <div className="mt-4">
        <LayeredFilters active={period} filters={[{ key: "today", label: "Hoje" }, { key: "7d", label: "7 dias" }, { key: "month", label: "Mês" }]} onSelect={(value) => setPeriod(value as Period)} />
      </div>
      {loading ? <p className="py-10 text-center text-sm text-tec-muted">Carregando vendas...</p> : report ? <SalesReport report={report} /> : null}
    </Card>

    {canViewDirectorFinancial ? <Card className="flex items-start gap-3 border-tec-purple/25 bg-tec-purple/5 p-5"><Building2 className="mt-0.5 text-tec-purple" size={20} /><div><h2 className="font-bold text-white">Indicadores financeiros do Diretor</h2><p className="mt-1 text-sm text-tec-subtle">Sua conta acumula o papel Diretor. Custos, margem e lucro bruto permanecem nas telas financeiras exclusivas desse papel.</p><Button className="mt-3" onClick={() => onNavigate("overview")}>Abrir visão executiva</Button></div></Card> : <Card className="flex items-start gap-3 p-5"><ReceiptText className="mt-0.5 text-tec-blue" size={20} /><div><h2 className="font-bold text-white">Financeiro sensível protegido</h2><p className="mt-1 text-sm text-tec-subtle">Esta conta administra a operação, mas não possui o papel Diretor. Custos, margem e lucro não são carregados nesta área.</p></div></Card>}
  </div>;
}

function AdminAction({ detail, disabled, icon, label, onClick }: { detail: string; disabled?: boolean; icon: ReactNode; label: string; onClick: () => void }) {
  return <button className="flex min-h-28 items-start gap-3 rounded-card border border-tec-border/20 bg-tec-panel p-4 text-left transition hover:border-tec-orange/50 hover:bg-tec-field disabled:cursor-not-allowed disabled:opacity-55" disabled={disabled} onClick={onClick} title={disabled ? detail : label} type="button"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">{icon}</span><span><strong className="block text-sm text-white">{label}</strong><span className="mt-1 block text-xs leading-5 text-tec-muted">{detail}</span></span></button>;
}

function SalesReport({ report }: { report: AdministrativeSalesReport }) {
  return <div className="mt-4 space-y-5">
    <StatBar items={[
      { key: "sales", label: "Vendas líquidas", value: report.totals.net_sales, displayValue: brl.format(report.totals.net_sales), detail: String(report.totals.invoices) + " notas no período", icon: <ReceiptText size={18} />, tone: "green" },
      { key: "returns", label: "Devoluções", value: report.totals.returns, displayValue: brl.format(report.totals.returns), detail: "Estornos registrados", icon: <ReceiptText size={18} />, tone: "amber" },
      { key: "payments", label: "Recebimentos", value: report.totals.cash_movements, detail: String(report.totals.payment_entries) + " lançamentos nativos", icon: <WalletCards size={18} />, tone: "blue" },
    ]} />
    <div className="grid gap-4 lg:grid-cols-2">
      <ReportList title="Por categoria" empty="Nenhuma venda categorizada neste período." rows={report.categories.map((row) => ({ label: row.category, detail: String(row.quantity) + " item(ns)", value: brl.format(row.revenue) }))} />
      <ReportList title="Por forma de pagamento" empty="Nenhum recebimento movimentado neste período." rows={report.payment_methods.map((row) => ({ label: row.payment_mode, detail: row.affects_drawer ? "Movimenta a gaveta" : "Fora da gaveta", value: brl.format(row.amount) }))} />
    </div>
  </div>;
}

function ReportList({ empty, rows, title }: { empty: string; rows: Array<{ label: string; detail: string; value: string }>; title: string }) {
  return <section className="overflow-hidden rounded-card border border-tec-border/20"><header className="border-b border-tec-border/15 bg-tec-field/45 px-4 py-3"><h3 className="font-bold text-white">{title}</h3></header><div className="divide-y divide-tec-border/15">{rows.map((row) => <div className="flex items-center justify-between gap-3 px-4 py-3" key={row.label}><span className="min-w-0"><strong className="block truncate text-sm text-white">{row.label}</strong><span className="block text-xs text-tec-muted">{row.detail}</span></span><strong className="shrink-0 text-sm text-tec-success">{row.value}</strong></div>)}{!rows.length ? <p className="px-4 py-5 text-sm text-tec-muted">{empty}</p> : null}</div></section>;
}
