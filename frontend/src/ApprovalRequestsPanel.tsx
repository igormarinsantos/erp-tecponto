import { Check, Clock3, RefreshCw, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { approvalRequests, type ApprovalRequest } from "./api";
import { Button, Card } from "./ui";

type Toast = (message: string, tone?: "success" | "error") => void;

function RequestRow({ item, pending, onDecide }: {
  item: ApprovalRequest;
  pending?: boolean;
  onDecide?: (name: string, decision: "approve" | "reject") => void;
}) {
  return (
    <li className="rounded-control border border-tec-border/15 bg-tec-field/45 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-bold text-white">{item.request_type ?? "Solicitação"}</p>
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
      {pending && onDecide ? (
        <div className="mt-3 flex justify-end gap-2">
          <Button icon={<X size={15} />} onClick={() => onDecide(item.name, "reject")} variant="danger">Reprovar</Button>
          <Button icon={<Check size={15} />} onClick={() => onDecide(item.name, "approve")} variant="primary">Aprovar</Button>
        </div>
      ) : null}
    </li>
  );
}

export function ApprovalRequestsPanel({ onToast }: { onToast: Toast }) {
  const [mine, setMine] = useState<ApprovalRequest[]>([]);
  const [pending, setPending] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ownRequests, pendingRequests] = await Promise.all([approvalRequests.mine(), approvalRequests.pending()]);
      setMine(ownRequests);
      setPending(pendingRequests);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível carregar as solicitações.", "error");
    } finally {
      setLoading(false);
    }
  }, [onToast]);

  useEffect(() => { void load(); }, [load]);

  const decide = async (name: string, decision: "approve" | "reject") => {
    try {
      await approvalRequests[decision](name);
      onToast(decision === "approve" ? "Solicitação aprovada e a ação foi executada." : "Solicitação reprovada.", "success");
      await load();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível decidir a solicitação.", "error");
    }
  };

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white">Central de aprovações</h2>
          <p className="mt-1 text-xs text-tec-muted">Pendências derivadas das travas reais do motor.</p>
        </div>
        <Button icon={<RefreshCw className={loading ? "animate-spin" : ""} size={16} />} onClick={() => void load()} variant="ghost">Atualizar</Button>
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <section>
          <h3 className="text-sm font-bold text-white">Minhas solicitações</h3>
          <ul className="mt-3 space-y-2">
            {mine.length ? mine.map((item) => <RequestRow item={item} key={item.name} />) : <li className="rounded-control border border-dashed border-tec-border/20 p-3 text-sm text-tec-muted">Nenhuma solicitação registrada.</li>}
          </ul>
        </section>
        <section>
          <h3 className="text-sm font-bold text-white">Aguardando minha aprovação</h3>
          <ul className="mt-3 space-y-2">
            {pending.length ? pending.map((item) => <RequestRow item={item} key={item.name} onDecide={decide} pending />) : <li className="rounded-control border border-dashed border-tec-border/20 p-3 text-sm text-tec-muted">Nenhuma pendência para decidir.</li>}
          </ul>
        </section>
      </div>
    </Card>
  );
}

function formatExpiry(value: string) {
  const date = new Date(value.replace(" ", "T"));
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}
