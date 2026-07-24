import { Check, ChevronDown, ChevronRight, Clock3, RefreshCw, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { approvalRequests, type ApprovalRequest } from "./api";
import { Button, Card } from "./ui";

type Toast = (message: string, tone?: "success" | "error") => void;

const REQUEST_TYPE_LABELS: Record<string, string> = {
  "Cancelar OS faturada": "Cancelar OS faturada",
  "Compra de peça acima do teto": "Compra de peça acima do teto",
  "Desconto acima do limite": "Desconto acima do limite",
  "Garantia-cortesia": "Garantia-cortesia",
  "Transferência entre estoques": "Transferência entre estoques",
  "Troca acima da tabela": "Troca acima da tabela",
  "Venda abaixo do custo": "Venda abaixo do custo",
  billed_service_order_cancel: "Cancelar OS faturada",
  courtesy_warranty: "Garantia-cortesia",
  pos_discount: "Desconto no PDV",
  pos_price_floor: "Venda abaixo do piso",
  part_purchase_above_threshold: "Compra de peca acima do teto",
  service_order_move: "Mover OS fora do papel",
  stock_transfer: "Transferencia entre estoques",
  tradein_over_max: "Troca acima da tabela",
};

function requestTypeLabel(value?: string) {
  return REQUEST_TYPE_LABELS[value ?? ""] ?? value ?? "Solicitacao";
}

function RequestRow({ item, pending, onDecide }: {
  item: ApprovalRequest;
  pending?: boolean;
  onDecide?: (name: string, decision: "approve" | "reject") => void;
}) {
  return (
    <li className="border-b border-tec-border/15 px-3 py-3 last:border-b-0">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-bold text-white">{requestTypeLabel(item.request_type)}</p>
          <p className="mt-1 text-xs leading-5 text-tec-subtle">{item.reason ?? "Sem motivo informado."}</p>
        </div>
        <span className={item.status === "Pendente" ? "rounded-full bg-tec-amber/15 px-2 py-1 text-xs font-bold text-tec-amber" : "rounded-full bg-tec-field px-2 py-1 text-xs font-bold text-tec-muted"}>
          {item.status}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-tec-muted">
        <span>Solicitante: {item.requested_by}</span>
        <span className="inline-flex items-center gap-1"><Clock3 size={13} />Expira: {formatExpiry(item.expires_on)}</span>
      </div>
      {item.reference_name ? <p className="mt-2 text-xs font-semibold text-tec-muted">Documento: {item.reference_name}</p> : null}
      {pending && onDecide ? (
        <div className="mt-3 flex justify-end gap-2">
          <Button icon={<X size={15} />} onClick={() => onDecide(item.name, "reject")} variant="danger">Reprovar</Button>
          <Button icon={<Check size={15} />} onClick={() => onDecide(item.name, "approve")} variant="primary">Aprovar</Button>
        </div>
      ) : null}
    </li>
  );
}

function RequestGroups({
  items,
  pending,
  onDecide,
  totalByType,
}: {
  items: ApprovalRequest[];
  pending?: boolean;
  onDecide?: (name: string, decision: "approve" | "reject") => void;
  totalByType?: Record<string, number>;
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const groups = useMemo(() => {
    const grouped = new Map<string, ApprovalRequest[]>();
    for (const item of items) {
      const key = item.request_type || "other";
      grouped.set(key, [...(grouped.get(key) ?? []), item]);
    }
    return [...grouped.entries()];
  }, [items]);

  if (!groups.length) {
    return <li className="rounded-control border border-dashed border-tec-border/20 p-3 text-sm text-tec-muted">Nenhuma pendencia para decidir.</li>;
  }

  return (
    <ul className="mt-3 space-y-2">
      {groups.map(([type, group]) => {
        const multiple = group.length > 1;
        const open = expanded[type] ?? false;
        const total = totalByType?.[type] ?? group.length;
        return (
          <li className="overflow-hidden rounded-control border border-tec-border/15 bg-tec-field/45" key={type}>
            {multiple ? (
              <button
                aria-expanded={open}
                className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left transition hover:bg-tec-orange/10"
                onClick={() => setExpanded((current) => ({ ...current, [type]: !open }))}
                type="button"
              >
                <span className="min-w-0">
                  <span className="block text-sm font-bold text-white">{group.length === total ? total : group.length + " de " + total} solicitacoes: {requestTypeLabel(type)}</span>
                  <span className="mt-1 block text-xs text-tec-muted">Expandir para decidir uma a uma.</span>
                </span>
                {open ? <ChevronDown className="shrink-0 text-tec-muted" size={17} /> : <ChevronRight className="shrink-0 text-tec-muted" size={17} />}
              </button>
            ) : null}
            {(!multiple || open) ? (
              <ul className={multiple ? "border-t border-tec-border/15" : ""}>
                {group.map((item) => <RequestRow item={item} key={item.name} onDecide={onDecide} pending={pending} />)}
              </ul>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}

export function ApprovalRequestsPanel({
  compact = false,
  onOpenAll,
  onToast,
}: {
  compact?: boolean;
  onOpenAll?: () => void;
  onToast: Toast;
}) {
  const [mine, setMine] = useState<ApprovalRequest[]>([]);
  const [pending, setPending] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ownRequests, pendingRequests] = await Promise.all([approvalRequests.mine(), approvalRequests.pending()]);
      setMine(ownRequests);
      setPending(pendingRequests.sort((left, right) => left.expires_on.localeCompare(right.expires_on)));
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Nao foi possivel carregar as solicitacoes.", "error");
    } finally {
      setLoading(false);
    }
  }, [onToast]);

  useEffect(() => { void load(); }, [load]);

  const decide = async (name: string, decision: "approve" | "reject") => {
    try {
      await approvalRequests[decision](name);
      onToast(decision === "approve" ? "Solicitacao aprovada e acao executada." : "Solicitacao reprovada.", "success");
      await load();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Nao foi possivel decidir a solicitacao.", "error");
    }
  };

  const visiblePending = compact ? pending.slice(0, 5) : pending;
  const pendingTypeCounts = useMemo(
    () => pending.reduce<Record<string, number>>((counts, item) => ({ ...counts, [item.request_type || "other"]: (counts[item.request_type || "other"] ?? 0) + 1 }), {}),
    [pending],
  );

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white">Central de aprovacoes</h2>
          <p className="mt-1 text-xs text-tec-muted">{compact ? "Mostrando as " + visiblePending.length + " decisoes mais urgentes de " + pending.length + "." : "Pendencias derivadas das travas reais do motor."}</p>
        </div>
        <Button icon={<RefreshCw className={loading ? "animate-spin" : ""} size={16} />} onClick={() => void load()} variant="ghost">Atualizar</Button>
      </div>
      {compact ? (
        <>
          <RequestGroups items={visiblePending} onDecide={decide} pending totalByType={pendingTypeCounts} />
          {pending.length > visiblePending.length && onOpenAll ? (
            <button className="mx-auto mt-4 flex items-center gap-2 text-sm font-bold text-tec-orange hover:text-tec-digital-orange" onClick={onOpenAll} type="button">
              Ver todas ({pending.length}) <ChevronRight size={16} />
            </button>
          ) : null}
        </>
      ) : (
        <div className="mt-4 grid gap-4 xl:grid-cols-2">
          <section>
            <h3 className="text-sm font-bold text-white">Minhas solicitacoes</h3>
            {mine.length ? <RequestGroups items={mine} /> : <p className="mt-3 rounded-control border border-dashed border-tec-border/20 p-3 text-sm text-tec-muted">Nenhuma solicitacao registrada.</p>}
          </section>
          <section>
            <h3 className="text-sm font-bold text-white">Aguardando minha aprovacao</h3>
            <RequestGroups items={pending} onDecide={decide} pending />
          </section>
        </div>
      )}
    </Card>
  );
}

function formatExpiry(value: string) {
  const date = new Date(value.replace(" ", "T"));
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}
