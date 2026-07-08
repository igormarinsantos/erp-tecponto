import { type DragEvent, type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, Clock3, GripVertical, RefreshCw, UserRound, Wrench } from "lucide-react";

import { serviceOrders, type ServiceOrderKanbanColumn, type ServiceOrderKanbanResponse, type ServiceOrderSummary } from "./api";
import { BadgeStatus, Button, Card } from "./ui";
import { cx } from "./ui/utils";

type ToastTone = "success" | "error";
type WorkflowFlow = "approve" | "reject" | "pickup";

interface ServiceOrderKanbanProps {
  onChanged: () => void;
  onOpenWorkflowFlow: (name: string, flow: WorkflowFlow) => void;
  onOpenOrder: (name: string) => void;
  onShowList: () => void;
  onToast: (message: string, tone?: ToastTone) => void;
}

type KanbanState =
  | { status: "loading" }
  | { status: "ready"; data: ServiceOrderKanbanResponse }
  | { status: "error"; message: string };

interface DraggedCard {
  name: string;
  sourceState: string;
}

const VISIBLE_ITEMS_PER_COLUMN = 4;

export function ServiceOrderKanban({
  onChanged,
  onOpenOrder,
  onOpenWorkflowFlow,
  onShowList,
  onToast,
}: ServiceOrderKanbanProps) {
  const [state, setState] = useState<KanbanState>({ status: "loading" });
  const [dragged, setDragged] = useState<DraggedCard | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);
  const [moving, setMoving] = useState<string | null>(null);

  const loadKanban = useCallback(async (quiet = false) => {
    if (!quiet) {
      setState({ status: "loading" });
    }
    try {
      const data = await serviceOrders.kanban(18);
      setState({ status: "ready", data });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Falha ao carregar Kanban" });
    }
  }, []);

  useEffect(() => {
    void loadKanban();
  }, [loadKanban]);

  const totalOrders = useMemo(() => {
    if (state.status !== "ready") {
      return 0;
    }
    return state.data.columns.reduce((total, column) => total + column.count, 0);
  }, [state]);

  const moveCard = useCallback(
    async (targetState: string) => {
      if (state.status !== "ready" || !dragged || dragged.sourceState === targetState) {
        setDragged(null);
        setDropTarget(null);
        return;
      }

      const specialFlow = flowForTargetState(targetState);
      if (specialFlow) {
        const orderName = dragged.name;
        setDragged(null);
        setDropTarget(null);
        onOpenWorkflowFlow(orderName, specialFlow);
        return;
      }

      const previous = state.data;
      setMoving(dragged.name);
      setState({ status: "ready", data: moveCardLocally(previous, dragged.name, dragged.sourceState, targetState) });

      try {
        const result = await serviceOrders.move(dragged.name, targetState);
        await loadKanban(true);
        onChanged();
        onToast(
          result.changed
            ? `OS ${result.item.name} movida para ${result.item.workflow_state}.`
            : `OS ${result.item.name} já estava em ${result.item.workflow_state}.`,
        );
      } catch (error) {
        setState({ status: "ready", data: previous });
        onToast(error instanceof Error ? error.message : "Transição recusada pelo workflow.", "error");
      } finally {
        setMoving(null);
        setDragged(null);
        setDropTarget(null);
      }
    },
    [dragged, loadKanban, onChanged, onOpenWorkflowFlow, onToast, state],
  );

  if (state.status === "loading") {
    return (
      <Card className="min-h-[540px] p-5">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-tec-orange border-t-transparent" />
        <p className="mt-4 text-sm font-semibold text-tec-subtle">Carregando Kanban de OS</p>
      </Card>
    );
  }

  if (state.status === "error") {
    return (
      <Card className="p-5">
        <p className="text-sm font-semibold text-tec-red">{state.message}</p>
        <Button className="mt-4" icon={<RefreshCw size={17} />} onClick={() => void loadKanban()} variant="secondary">
          Tentar novamente
        </Button>
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-card bg-tec-orange/15 text-tec-orange">
            <Wrench size={20} />
          </span>
          <div>
            <h2 className="text-lg font-bold text-white">Kanban de OS</h2>
            <p className="text-xs text-tec-muted">{totalOrders.toLocaleString("pt-BR")} ordens no workflow</p>
          </div>
        </div>
        <Button icon={<RefreshCw size={17} />} onClick={() => void loadKanban(true)} variant="secondary">
          Atualizar
        </Button>
      </div>

      <div className="tp-kanban-grid">
        {state.data.columns.map((column) => (
          <KanbanColumn
            column={column}
            dropTarget={dropTarget}
            key={column.state}
            moving={moving}
            onDragEnd={() => {
              setDragged(null);
              setDropTarget(null);
            }}
            onDragStart={(item) => setDragged({ name: item.name, sourceState: column.state })}
            onDrop={() => void moveCard(column.state)}
            onOpenOrder={onOpenOrder}
            onShowList={onShowList}
            onSetDropTarget={setDropTarget}
          />
        ))}
      </div>
    </Card>
  );
}

function KanbanColumn({
  column,
  dropTarget,
  moving,
  onDragEnd,
  onDragStart,
  onDrop,
  onOpenOrder,
  onShowList,
  onSetDropTarget,
}: {
  column: ServiceOrderKanbanColumn;
  dropTarget: string | null;
  moving: string | null;
  onDragEnd: () => void;
  onDragStart: (item: ServiceOrderSummary) => void;
  onDrop: () => void;
  onOpenOrder: (name: string) => void;
  onShowList: () => void;
  onSetDropTarget: (state: string | null) => void;
}) {
  const tone = statusTone(column.state);
  const visibleItems = column.items.slice(0, VISIBLE_ITEMS_PER_COLUMN);
  const hiddenCount = Math.max(0, column.count - visibleItems.length);

  return (
    <section
      className={cx(
        "flex min-h-[280px] flex-col rounded-card border bg-tec-panel transition",
        tone.border,
        dropTarget === column.state && "border-tec-orange/80 bg-tec-orange/10",
      )}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          onSetDropTarget(null);
        }
      }}
      onDragOver={(event) => {
        event.preventDefault();
        onSetDropTarget(column.state);
      }}
      onDrop={(event) => {
        event.preventDefault();
        onDrop();
      }}
    >
      <header className="border-b border-tec-border/15 p-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className={cx("h-2.5 w-2.5 shrink-0 rounded-full", tone.dot)} />
              <h3 className="truncate text-sm font-bold text-white" title={column.state}>
                {column.state}
              </h3>
            </div>
            <p className="mt-1 text-xs text-tec-muted">{column.count.toLocaleString("pt-BR")} OS</p>
          </div>
          <span className={cx("rounded-full px-2 py-1 text-xs font-bold", tone.badge)}>{column.items.length}</span>
        </div>
      </header>

      <div className="flex-1 space-y-3 p-3">
        {visibleItems.length ? (
          visibleItems.map((item) => (
            <KanbanCard
              item={item}
              key={item.name}
              moving={moving === item.name}
              onDragEnd={onDragEnd}
              onDragStart={() => onDragStart(item)}
              onOpenOrder={onOpenOrder}
            />
          ))
        ) : (
          <div className="grid min-h-[120px] place-items-center rounded-card border border-dashed border-tec-border/20 px-4 text-center text-sm text-tec-muted">
            Sem OS neste estado.
          </div>
        )}
      </div>

      {hiddenCount ? (
        <footer className="border-t border-tec-border/15 p-3">
          <button
            className="w-full rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 text-xs font-bold text-tec-subtle transition hover:border-tec-orange/50 hover:text-white"
            onClick={onShowList}
            type="button"
          >
            Ver mais (+{hiddenCount.toLocaleString("pt-BR")})
          </button>
        </footer>
      ) : null}
    </section>
  );
}

function KanbanCard({
  item,
  moving,
  onDragEnd,
  onDragStart,
  onOpenOrder,
}: {
  item: ServiceOrderSummary;
  moving: boolean;
  onDragEnd: () => void;
  onDragStart: () => void;
  onOpenOrder: (name: string) => void;
}) {
  return (
    <button
      className={cx(
        "group w-full cursor-grab rounded-card border border-tec-border/20 bg-tec-panel-strong/70 p-3 text-left shadow-sm transition hover:border-tec-orange/55 hover:bg-tec-panel-strong active:cursor-grabbing",
        moving && "opacity-60",
      )}
      draggable={!moving}
      onClick={() => onOpenOrder(item.name)}
      onDragEnd={onDragEnd}
      onDragStart={(event: DragEvent<HTMLButtonElement>) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", item.name);
        onDragStart();
      }}
      title={`Abrir ${item.name}`}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-white">{item.name}</p>
          <p className="mt-1 truncate text-sm text-tec-subtle">{item.customer ?? "Cliente não informado"}</p>
        </div>
        <GripVertical className="shrink-0 text-tec-muted transition group-hover:text-tec-orange" size={17} />
      </div>

      <div className="mt-3 space-y-2 text-xs text-tec-muted">
        <CardLine icon={<Wrench size={14} />} text={item.reported_defect ?? "Defeito não informado"} />
        <CardLine icon={<UserRound size={14} />} text={item.technician ?? item.attendant ?? "Responsável não definido"} />
        <CardLine icon={<Clock3 size={14} />} text={formatDate(item.modified)} />
      </div>

      <div className="mt-3 flex items-center justify-between gap-2">
        <BadgeStatus status={item.workflow_state} />
        <ArrowRight className="text-tec-muted transition group-hover:text-tec-orange" size={16} />
      </div>
    </button>
  );
}

function CardLine({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <p className="flex min-w-0 items-center gap-2">
      <span className="shrink-0 text-tec-muted">{icon}</span>
      <span className="truncate">{text}</span>
    </p>
  );
}

function moveCardLocally(
  data: ServiceOrderKanbanResponse,
  name: string,
  sourceState: string,
  targetState: string,
): ServiceOrderKanbanResponse {
  const item = data.columns.flatMap((column) => column.items).find((entry) => entry.name === name);
  if (!item) {
    return data;
  }

  return {
    ...data,
    columns: data.columns.map((column) => {
      if (column.state === sourceState) {
        return {
          ...column,
          count: Math.max(0, column.count - 1),
          items: column.items.filter((entry) => entry.name !== name),
        };
      }
      if (column.state === targetState) {
        return {
          ...column,
          count: column.count + 1,
          items: [{ ...item, workflow_state: targetState }, ...column.items],
        };
      }
      return column;
    }),
  };
}

function statusTone(status: string) {
  if (["Entregue", "Pronto para retirada", "Teste final", "Aprovado"].includes(status)) {
    return {
      badge: "bg-tec-success/15 text-tec-success",
      border: "border-tec-success/25",
      dot: "bg-tec-success",
    };
  }
  if (["Reprovado", "Orçamento expirado", "Cancelado", "Sem conserto"].includes(status)) {
    return {
      badge: "bg-tec-red/15 text-tec-red",
      border: "border-tec-red/25",
      dot: "bg-tec-red",
    };
  }
  if (status === "Aguardando aprovação") {
    return {
      badge: "bg-tec-amber/15 text-tec-amber",
      border: "border-tec-amber/25",
      dot: "bg-tec-amber",
    };
  }
  if (status === "Aguardando peça") {
    return {
      badge: "bg-tec-purple/15 text-tec-purple",
      border: "border-tec-purple/25",
      dot: "bg-tec-purple",
    };
  }
  if (status === "Em diagnóstico") {
    return {
      badge: "bg-tec-orange/15 text-tec-orange",
      border: "border-tec-orange/25",
      dot: "bg-tec-orange",
    };
  }
  return {
    badge: "bg-tec-blue/15 text-tec-blue",
    border: "border-tec-blue/25",
    dot: "bg-tec-blue",
  };
}

function flowForTargetState(targetState: string): WorkflowFlow | null {
  if (targetState === "Aprovado") {
    return "approve";
  }
  if (targetState === "Reprovado") {
    return "reject";
  }
  if (targetState === "Entregue") {
    return "pickup";
  }
  return null;
}

function formatDate(value: string) {
  if (!value) {
    return "Sem data";
  }
  const date = new Date(value.replace(" ", "T"));
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
