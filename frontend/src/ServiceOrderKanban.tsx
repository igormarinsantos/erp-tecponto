import { type DragEvent, type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, Clock3, GripVertical, RefreshCw, UserRound, Wrench } from "lucide-react";

import {
  serviceOrders,
  type ServiceOrderKanbanColumn,
  type ServiceOrderKanbanResponse,
  type ServiceOrderQueryParams,
  type ServiceOrderSummary,
} from "./api";
import { BadgeStatus, Button, Card } from "./ui";
import { ApprovalRequestModal } from "./ApprovalRequestModal";
import { WorkflowMoveMenu } from "./WorkflowMoveMenu";
import { cx } from "./ui/utils";

type ToastTone = "success" | "error";
type WorkflowFlow = "approve" | "reject" | "pickup";
type KanbanPeriodMode = "7d" | "14d" | "custom";

export interface ServiceOrderKanbanFilters {
  period: {
    fromDate: string;
    mode: KanbanPeriodMode;
    toDate: string;
  };
  query: string;
  status: string;
}

interface ServiceOrderKanbanProps {
  filterBar?: ReactNode;
  filters: ServiceOrderKanbanFilters;
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
const COMPACT_KANBAN_QUERY = "(max-width: 1535px)";

export function ServiceOrderKanban({
  filterBar,
  filters,
  onChanged,
  onOpenOrder,
  onOpenWorkflowFlow,
  onShowList,
  onToast,
}: ServiceOrderKanbanProps) {
  const [state, setState] = useState<KanbanState>({ status: "loading" });
  const [dragged, setDragged] = useState<DraggedCard | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);
  const [expandedState, setExpandedState] = useState<string | null>(null);
  const [compactMode, setCompactMode] = useState(false);
  const [moving, setMoving] = useState<string | null>(null);
  const [moveApproval, setMoveApproval] = useState<{ name: string; targetState: string; requestType: "service_order_move" | "billed_service_order_cancel" } | null>(null);

  const loadKanban = useCallback(async (quiet = false) => {
    if (!quiet) {
      setState({ status: "loading" });
    }
    try {
      const data = await serviceOrders.kanban(40, toKanbanQueryParams(filters));
      setState({ status: "ready", data });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Falha ao carregar Kanban" });
    }
  }, [filters]);

  useEffect(() => {
    void loadKanban();
  }, [loadKanban]);

  useEffect(() => {
    const query = window.matchMedia(COMPACT_KANBAN_QUERY);
    const update = () => setCompactMode(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  const filteredColumns = useMemo(() => {
    if (state.status !== "ready") {
      return [];
    }
    return state.data.columns.map((column) => {
      const items = column.items.filter((item) => matchesKanbanFilters(item, filters));
      const statusSelected = filters.status !== "all" && column.state !== filters.status;
      return {
        ...column,
        count: statusSelected ? 0 : items.length,
        items: statusSelected ? [] : items,
      };
    });
  }, [filters, state]);

  const totalOrders = useMemo(() => filteredColumns.reduce((total, column) => total + column.count, 0), [filteredColumns]);

  useEffect(() => {
    if (state.status !== "ready" || !state.data.columns.length) {
      return;
    }
    setExpandedState((current) =>
      current && state.data.columns.some((column) => column.state === current) ? current : null,
    );
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
        const message = error instanceof Error ? error.message : "Transição recusada pelo workflow.";
        if (message.includes("OS faturada") && targetState === "Cancelado") {
          setMoveApproval({ name: dragged.name, targetState, requestType: "billed_service_order_cancel" });
        } else if (message.includes("Seu papel não permite mover")) {
          setMoveApproval({ name: dragged.name, targetState, requestType: "service_order_move" });
        } else {
          onToast(message, "error");
        }
      } finally {
        setMoving(null);
        setDragged(null);
        setDropTarget(null);
      }
    },
    [dragged, loadKanban, onChanged, onOpenWorkflowFlow, onToast, state],
  );

  const quickMoveCard = useCallback(async (item: ServiceOrderSummary, targetState: string) => {
    const specialFlow = flowForTargetState(targetState);
    if (specialFlow) {
      onOpenWorkflowFlow(item.name, specialFlow);
      return;
    }
    setMoving(item.name);
    try {
      const result = await serviceOrders.move(item.name, targetState);
      await loadKanban(true);
      onChanged();
      onToast(result.changed ? `OS ${item.name} movida para ${result.item.workflow_state}.` : `OS ${item.name} já estava nesta etapa.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Transição recusada pelo workflow.";
      if (message.includes("OS faturada") && targetState === "Cancelado") {
        setMoveApproval({ name: item.name, targetState, requestType: "billed_service_order_cancel" });
      } else if (message.includes("Seu papel não permite mover")) {
        setMoveApproval({ name: item.name, targetState, requestType: "service_order_move" });
      } else {
        onToast(message, "error");
      }
    } finally {
      setMoving(null);
    }
  }, [loadKanban, onChanged, onOpenWorkflowFlow, onToast]);

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
    <>
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
      {filterBar ? <div className="mb-4">{filterBar}</div> : null}

      <div
        className={compactMode ? "tp-kanban-compact-grid" : "tp-kanban-grid"}
        style={
          compactMode
            ? {
                gridTemplateColumns: filteredColumns
                  .map((column) => (column.state === expandedState ? "minmax(0, 1fr)" : "42px"))
                  .join(" "),
              }
            : undefined
        }
      >
        {filteredColumns.map((column) => (
          <KanbanColumn
            compact={compactMode}
            column={column}
            dropTarget={dropTarget}
            expanded={!compactMode || column.state === expandedState}
            key={column.state}
            moving={moving}
            urgent={columnHasUrgentDeadline(column)}
            onExpand={() => setExpandedState(column.state)}
            onDragEnd={() => {
              setDragged(null);
              setDropTarget(null);
            }}
            onDragStart={(item) => setDragged({ name: item.name, sourceState: column.state })}
            onDrop={() => void moveCard(column.state)}
            onOpenOrder={onOpenOrder}
            onQuickMove={(item, targetState) => void quickMoveCard(item, targetState)}
            onShowList={onShowList}
            onSetDropTarget={setDropTarget}
          />
        ))}
      </div>
    </Card>
    <ApprovalRequestModal
      onClose={() => setMoveApproval(null)}
      onCreated={() => setMoveApproval(null)}
      onToast={onToast}
      open={Boolean(moveApproval)}
      payload={moveApproval?.requestType === "service_order_move" ? { target_state: moveApproval.targetState } : {}}
      referenceName={moveApproval?.name ?? ""}
      requestType={moveApproval?.requestType ?? "service_order_move"}
      title={moveApproval?.requestType === "billed_service_order_cancel"
        ? "Esta OS já possui nota fiscal. Deseja solicitar ao Gestor o cancelamento faturado?"
        : `Seu papel não permite mover esta OS para ${moveApproval?.targetState ?? "esta etapa"}. Deseja solicitar aprovação?`}
    />
    </>
  );
}

function KanbanColumn({
  compact,
  column,
  dropTarget,
  expanded,
  moving,
  urgent,
  onDragEnd,
  onDragStart,
  onDrop,
  onExpand,
  onOpenOrder,
  onQuickMove,
  onShowList,
  onSetDropTarget,
}: {
  compact: boolean;
  column: ServiceOrderKanbanColumn;
  dropTarget: string | null;
  expanded: boolean;
  moving: string | null;
  urgent: boolean;
  onExpand: () => void;
  onDragEnd: () => void;
  onDragStart: (item: ServiceOrderSummary) => void;
  onDrop: () => void;
  onOpenOrder: (name: string) => void;
  onQuickMove: (item: ServiceOrderSummary, targetState: string) => void;
  onShowList: () => void;
  onSetDropTarget: (state: string | null) => void;
}) {
  const tone = statusTone(column.state);
  const visibleItems = column.items.slice(0, VISIBLE_ITEMS_PER_COLUMN);
  const hiddenCount = Math.max(0, column.count - visibleItems.length);

  if (compact && !expanded) {
    return (
      <section
        className={cx(
          "group min-h-[430px] rounded-card border bg-tec-panel transition",
          tone.border,
          urgent && "tp-kanban-urgent-rail",
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
          onExpand();
          onDrop();
        }}
      >
        <button
          className="flex h-full min-h-[430px] w-full flex-col items-center gap-3 rounded-card px-2 py-3 text-center transition hover:bg-tec-field/55"
          onClick={onExpand}
          title={urgent ? `Abrir funil ${column.state} - prazo urgente` : `Abrir funil ${column.state}`}
          type="button"
        >
          <span className={cx("h-2.5 w-2.5 shrink-0 rounded-full", tone.dot)} />
          <span className={cx("rounded-full px-2 py-1 text-[10px] font-bold", tone.badge)}>{column.count}</span>
          <span className="tp-kanban-rail-label text-xs font-bold text-tec-subtle">{column.state}</span>
        </button>
      </section>
    );
  }

  return (
    <section
      className={cx(
        "flex min-h-[280px] flex-col rounded-card border bg-tec-panel transition",
        tone.border,
        urgent && "tp-kanban-urgent-column",
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
      <header className="border-b border-tec-border/10 p-3">
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
              onQuickMove={onQuickMove}
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
  onQuickMove,
}: {
  item: ServiceOrderSummary;
  moving: boolean;
  onDragEnd: () => void;
  onDragStart: () => void;
  onOpenOrder: (name: string) => void;
  onQuickMove: (item: ServiceOrderSummary, targetState: string) => void;
}) {
  return (
    <article
      className={cx(
        "group w-full cursor-grab rounded-card border border-tec-border/20 bg-tec-panel-strong/70 p-3 text-left shadow-sm transition hover:border-tec-orange/55 hover:bg-tec-panel-strong active:cursor-grabbing",
        moving && "opacity-60",
      )}
      data-tp-context="service-order"
      data-tp-customer={item.customer ?? ""}
      data-tp-label={item.customer ?? item.name}
      data-tp-name={item.name}
      data-tp-workflow-state={item.workflow_state ?? ""}
      draggable={!moving}
      onDragEnd={onDragEnd}
      onDragStart={(event: DragEvent<HTMLElement>) => {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", item.name);
        onDragStart();
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <button className="min-w-0 text-left" onClick={() => onOpenOrder(item.name)} title={`Abrir ${item.name}`} type="button">
          <p className="truncate text-sm font-bold text-white">{item.name}</p>
          <p className="mt-1 truncate text-sm text-tec-subtle">{item.customer ?? "Cliente não informado"}</p>
        </button>
        <GripVertical className="shrink-0 text-tec-muted transition group-hover:text-tec-orange" size={17} />
      </div>

      <div className="mt-3 space-y-2 text-xs text-tec-muted">
        <CardLine icon={<Wrench size={14} />} text={item.reported_defect ?? "Defeito não informado"} />
        <CardLine icon={<UserRound size={14} />} text={item.technician ?? item.attendant ?? "Responsável não definido"} />
        <CardLine icon={<Clock3 size={14} />} text={formatDate(item.modified)} />
      </div>

      <div className="mt-3 flex items-center justify-between gap-2">
        <BadgeStatus status={item.workflow_state} />
        <WorkflowMoveMenu actions={item.workflow_transitions} busy={moving} onSelect={(action) => onQuickMove(item, action.next_state)} />
      </div>
    </article>
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

function columnHasUrgentDeadline(column: ServiceOrderKanbanColumn) {
  return column.items.some((item) => isUrgentDeadline(item.approval_deadline));
}

function isUrgentDeadline(value: string | null | undefined) {
  if (!value) {
    return false;
  }
  const deadline = parseKanbanDate(value);
  if (!deadline) {
    return false;
  }
  return deadline.getTime() - Date.now() <= 24 * 60 * 60 * 1000;
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
      border: "border-tec-border/15",
      dot: "bg-tec-success",
    };
  }
  if (["Reprovado", "Orçamento expirado", "Cancelado", "Sem conserto"].includes(status)) {
    return {
      badge: "bg-tec-red/15 text-tec-red",
      border: "border-tec-border/15",
      dot: "bg-tec-red",
    };
  }
  if (status === "Aguardando aprovação") {
    return {
      badge: "bg-tec-amber/15 text-tec-amber",
      border: "border-tec-border/15",
      dot: "bg-tec-amber",
    };
  }
  if (status === "Aguardando peça") {
    return {
      badge: "bg-tec-purple/15 text-tec-purple",
      border: "border-tec-border/15",
      dot: "bg-tec-purple",
    };
  }
  if (status === "Em diagnóstico") {
    return {
      badge: "bg-tec-orange/15 text-tec-orange",
      border: "border-tec-border/15",
      dot: "bg-tec-orange",
    };
  }
  return {
    badge: "bg-tec-blue/15 text-tec-blue",
    border: "border-tec-border/15",
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

function matchesKanbanFilters(item: ServiceOrderSummary, filters: ServiceOrderKanbanFilters) {
  if (filters.status !== "all" && item.workflow_state !== filters.status) {
    return false;
  }

  const bounds = getKanbanPeriodBounds(filters.period);
  if (bounds) {
    const date = parseKanbanDate(item.modified);
    if (!date || date < bounds.start || date > bounds.end) {
      return false;
    }
  }

  const query = normalizeKanbanText(filters.query);
  if (!query) {
    return true;
  }

  return normalizeKanbanText(
    [
      item.name,
      item.customer,
      item.customer_device,
      item.reported_defect,
      item.workflow_state,
      item.technician,
      item.attendant,
      item.priority,
    ]
      .filter(Boolean)
      .join(" "),
  ).includes(query);
}

function toKanbanQueryParams(filters: ServiceOrderKanbanFilters): ServiceOrderQueryParams {
  const params: ServiceOrderQueryParams = {};
  const query = filters.query.trim();
  if (query) {
    params.query = query;
  }
  if (filters.status !== "all") {
    params.status = filters.status;
  }

  if (filters.period.mode === "custom") {
    if (filters.period.fromDate) {
      params.from_date = filters.period.fromDate;
    }
    if (filters.period.toDate) {
      params.to_date = filters.period.toDate;
    }
  } else {
    const bounds = getKanbanPeriodBounds(filters.period);
    if (bounds) {
      params.from_date = formatKanbanDateInputValue(bounds.start);
      params.to_date = formatKanbanDateInputValue(bounds.end);
    }
  }

  return params;
}

function getKanbanPeriodBounds(period: ServiceOrderKanbanFilters["period"]) {
  const now = new Date();
  const end = endOfKanbanDay(period.mode === "custom" && period.toDate ? parseKanbanDateInput(period.toDate) : now);
  let start: Date | null;

  if (period.mode === "custom") {
    start = period.fromDate ? startOfKanbanDay(parseKanbanDateInput(period.fromDate)) : null;
  } else {
    start = startOfKanbanDay(addKanbanCalendarDays(now, period.mode === "14d" ? -13 : -6));
  }

  if (!start && !period.toDate) {
    return null;
  }

  return {
    end,
    start: start ?? startOfKanbanDay(new Date(0)),
  };
}

function normalizeKanbanText(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function parseKanbanDate(value: string) {
  if (!value) {
    return null;
  }
  const date = new Date(value.replace(" ", "T"));
  return Number.isNaN(date.getTime()) ? null : date;
}

function parseKanbanDateInput(value: string) {
  const [year, month, day] = value.split("-").map((part) => Number.parseInt(part, 10));
  return new Date(year, month - 1, day);
}

function formatKanbanDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function startOfKanbanDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
}

function endOfKanbanDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
}

function addKanbanCalendarDays(date: Date, days: number) {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
}
