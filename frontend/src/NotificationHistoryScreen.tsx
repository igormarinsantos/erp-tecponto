import { Bell, CheckCheck, ChevronRight, Filter, LoaderCircle } from "lucide-react";
import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import { notifications, type NavigationTarget, type NotificationHistoryFilters, type TecpontoNotification } from "./api";
import { Button, Card } from "./ui";
import { cx } from "./ui/utils";

const PAGE_SIZE = 30;

const TYPE_LABELS: Record<string, string> = {
  approval: "Aprovações",
  deadline: "Prazos",
  pickup: "Retiradas",
  service_order: "Ordens de serviço",
};

type Period = NonNullable<NotificationHistoryFilters["period"]>;
type ReadState = NonNullable<NotificationHistoryFilters["read_state"]>;

function notificationOrderName(item: TecpontoNotification) {
  if (item.reference_doctype === "Service Order") {
    return item.reference_name;
  }
  return item.link ? new URL(item.link, window.location.origin).searchParams.get("order") : null;
}

function formatDate(value: string | null) {
  if (!value) return "Agora";
  const date = new Date(value.replace(" ", "T"));
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(date);
}

export function NotificationHistoryScreen({
  onNotificationsChanged,
  onOpenServiceOrder,
  onToast,
}: {
  onNotificationsChanged: () => Promise<void>;
  onOpenServiceOrder: (name: string) => void;
  onToast: (message: string, tone?: "success" | "error") => void;
}) {
  const [items, setItems] = useState<TecpontoNotification[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [type, setType] = useState("all");
  const [period, setPeriod] = useState<Period>("all");
  const [readState, setReadState] = useState<ReadState>("all");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const filters = useMemo<NotificationHistoryFilters>(() => ({
    from_date: fromDate || undefined,
    limit: PAGE_SIZE,
    notification_type: type === "all" ? undefined : type,
    period,
    read_state: readState,
    to_date: toDate || undefined,
  }), [fromDate, period, readState, toDate, type]);

  const load = useCallback(async (append = false) => {
    if (append) setLoadingMore(true);
    else setLoading(true);
    try {
      const response = await notifications.history({ ...filters, start: append ? items.length : 0 });
      setItems((current) => append ? [...current, ...response.items] : response.items);
      setTotal(response.total);
      setHasMore(response.has_more);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível carregar as notificações.", "error");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [filters, items.length, onToast]);

  useEffect(() => {
    void load();
  }, [load]);

  const markAllRead = async () => {
    try {
      await notifications.markAllRead();
      await Promise.all([load(), onNotificationsChanged()]);
      onToast("Todas as notificações foram marcadas como lidas.");
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível marcar as notificações.", "error");
    }
  };

  const openNotification = async (item: TecpontoNotification) => {
    try {
      if (!item.is_read) {
        await notifications.markRead(item.name);
        setItems((current) => current.map((currentItem) => currentItem.name === item.name ? { ...currentItem, is_read: true } : currentItem));
        await onNotificationsChanged();
      }
      const orderName = notificationOrderName(item);
      if (orderName) onOpenServiceOrder(orderName);
      else onToast("Esta notificação não possui um documento para abrir.");
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível abrir a notificação.", "error");
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl space-y-4">
      <Card className="p-4 md:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex items-start gap-3">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-control bg-tec-orange/15 text-tec-orange"><Bell size={20} /></span>
            <div>
              <h2 className="text-xl font-bold text-white">Histórico de notificações</h2>
              <p className="mt-1 text-sm text-tec-muted">{total} aviso{total === 1 ? "" : "s"} da sua operação.</p>
            </div>
          </div>
          <Button icon={<CheckCheck size={17} />} onClick={() => void markAllRead()} variant="secondary">
            Marcar todas como lidas
          </Button>
        </div>
      </Card>

      <Card className="p-4">
        <div className="flex items-center gap-2 text-sm font-bold text-white"><Filter size={17} className="text-tec-orange" /> Filtros</div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <FilterSelect label="Tipo" onChange={setType} value={type}>
            <option value="all">Todos os tipos</option>
            {Object.entries(TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </FilterSelect>
          <FilterSelect label="Período" onChange={(value) => setPeriod(value as Period)} value={period}>
            <option value="all">Todo o histórico</option>
            <option value="today">Hoje</option>
            <option value="7d">Últimos 7 dias</option>
            <option value="30d">Últimos 30 dias</option>
            <option value="custom">Personalizado</option>
          </FilterSelect>
          <FilterSelect label="Leitura" onChange={(value) => setReadState(value as ReadState)} value={readState}>
            <option value="all">Lidas e não lidas</option>
            <option value="unread">Não lidas</option>
            <option value="read">Lidas</option>
          </FilterSelect>
          {period === "custom" ? (
            <>
              <FilterDate label="De" onChange={setFromDate} value={fromDate} />
              <FilterDate label="Até" onChange={setToDate} value={toDate} />
            </>
          ) : null}
        </div>
      </Card>

      <Card className="overflow-hidden">
        {loading ? (
          <div className="flex min-h-56 items-center justify-center gap-2 text-sm text-tec-muted"><LoaderCircle className="animate-spin" size={18} /> Carregando notificações...</div>
        ) : items.length ? (
          <div className="divide-y divide-tec-border/15">
            {items.map((item) => (
              <button
                className={cx("flex w-full items-start gap-3 px-4 py-4 text-left transition hover:bg-tec-field/60 md:px-5", !item.is_read && "bg-tec-orange/[0.035]")}
                key={item.name}
                onClick={() => void openNotification(item)}
                type="button"
              >
                <span className={cx("mt-1 h-2.5 w-2.5 shrink-0 rounded-full", item.is_read ? "bg-tec-border/45" : "bg-tec-orange")} title={item.is_read ? "Lida" : "Não lida"} />
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-white">{item.title}</span>
                    <span className="rounded-full bg-tec-field px-2 py-0.5 text-[11px] font-bold text-tec-muted">{TYPE_LABELS[item.type] ?? item.type}</span>
                  </span>
                  <span className="mt-1 block text-sm text-tec-muted">{item.body}</span>
                  <span className="mt-2 block text-xs text-tec-subtle">{formatDate(item.creation)}</span>
                </span>
                <ChevronRight className="mt-1 shrink-0 text-tec-muted" size={18} />
              </button>
            ))}
          </div>
        ) : (
          <div className="min-h-56 px-5 py-16 text-center text-sm text-tec-muted">Nenhuma notificação encontrada para estes filtros.</div>
        )}
        {hasMore ? (
          <div className="border-t border-tec-border/15 p-3 text-center">
            <Button disabled={loadingMore} onClick={() => void load(true)} variant="secondary">
              {loadingMore ? "Carregando..." : `Mostrar mais (${Math.max(0, total - items.length)})`}
            </Button>
          </div>
        ) : null}
      </Card>
    </div>
  );
}

function FilterSelect({ children, label, onChange, value }: { children: ReactNode; label: string; onChange: (value: string) => void; value: string }) {
  return <label className="grid gap-1.5 text-xs font-bold text-tec-muted"><span>{label}</span><select className="h-10 rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-tec-text outline-none focus:border-tec-orange/70" onChange={(event) => onChange(event.target.value)} value={value}>{children}</select></label>;
}

function FilterDate({ label, onChange, value }: { label: string; onChange: (value: string) => void; value: string }) {
  return <label className="grid gap-1.5 text-xs font-bold text-tec-muted"><span>{label}</span><input className="h-10 rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-tec-text outline-none focus:border-tec-orange/70" onChange={(event) => onChange(event.target.value)} type="date" value={value} /></label>;
}
