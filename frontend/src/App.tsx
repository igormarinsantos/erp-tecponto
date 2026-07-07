import { FormEvent, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Clock3,
  FileText,
  Printer,
  RefreshCw,
  Search as SearchIcon,
  Smartphone,
  Tag,
  UserRound,
  Wrench,
} from "lucide-react";

import {
  balcao,
  getBoot,
  logout,
  serviceOrders,
  type BootResponse,
  type CheckinResponse,
  type CustomerDeviceSummary,
  type CustomerSummary,
  type DashboardMetrics,
  type NavigationTarget,
  type ServiceOrderBudgetLine,
  type ServiceOrderDetailResponse,
  type ServiceOrderPrintLink,
  type ServiceOrderTimelineEvent,
  type ServiceOrderWorkflowAction,
  type ServiceOrderSummary,
  type StockItemSummary,
  type TradeEvaluationSummary,
} from "./api";
import { CheckinWizard } from "./CheckinWizard";
import { panelDefinitions, type ActionDefinition } from "./roleConfig";
import { BudgetDecisionModal, PickupModal } from "./ServiceOrderFlows";
import { BadgeStatus, Button, Card, DataTable, MetricCard, Sidebar, Toast, Topbar, type TableColumn } from "./ui";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; boot: BootResponse; metrics: DashboardMetrics; orders: ServiceOrderSummary[] }
  | { status: "error"; message: string };

const viewTitles: Record<NavigationTarget, { title: string; subtitle: string }> = {
  overview: {
    title: "Visão geral",
    subtitle: "Atendimentos, pendências e atalhos do balcão.",
  },
  "service-orders": {
    title: "Ordens de serviço",
    subtitle: "Fila de OS com status e responsáveis.",
  },
  "service-order-detail": {
    title: "Detalhe da OS",
    subtitle: "Cliente, aparelho, orçamento, workflow e impressos.",
  },
  customers: {
    title: "Clientes",
    subtitle: "Busca por nome, telefone, e-mail ou código.",
  },
  devices: {
    title: "Aparelhos",
    subtitle: "Aparelhos cadastrados para atendimento.",
  },
  "trade-ins": {
    title: "Trocas",
    subtitle: "Avaliações e propostas do TROQUE.",
  },
  "parts-stock": {
    title: "Peças e estoque",
    subtitle: "Consulta de disponibilidade por depósito.",
  },
  sales: {
    title: "Vendas e acessórios",
    subtitle: "Acesso rápido ao fluxo de venda do balcão.",
  },
};

export function App() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [activeView, setActiveView] = useState<NavigationTarget>("overview");
  const [checkinOpen, setCheckinOpen] = useState(false);
  const [selectedOrderName, setSelectedOrderName] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<number | null>(null);

  const load = useCallback(async (options?: { quiet?: boolean }) => {
    if (!options?.quiet) {
      setState({ status: "loading" });
    }
    try {
      const [boot, orderList, metrics] = await Promise.all([getBoot(), serviceOrders.list(12), balcao.getDashboardMetrics()]);
      setState({ status: "ready", boot, metrics, orders: orderList.items });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Falha ao carregar" });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    return () => {
      if (toastTimer.current) {
        window.clearTimeout(toastTimer.current);
      }
    };
  }, []);

  const showToast = useCallback((message: string) => {
    setToast(message);
    if (toastTimer.current) {
      window.clearTimeout(toastTimer.current);
    }
    toastTimer.current = window.setTimeout(() => setToast(null), 3200);
  }, []);

  const showComingSoon = useCallback((label: string, block = "bloco 3.1x") => {
    showToast(`${label}: em breve — ${block}`);
  }, [showToast]);

  const openServiceOrder = useCallback((name: string) => {
    setSelectedOrderName(name);
    setActiveView("service-order-detail");
  }, []);

  const startCheckin = useCallback(() => {
    setCheckinOpen(true);
  }, []);

  const handleCheckinCreated = useCallback((response: CheckinResponse) => {
    void load({ quiet: true });
    showToast(`OS ${response.service_order.name} criada com foto e assinatura.`);
  }, [load, showToast]);

  if (state.status === "loading") {
    return <LoadingShell />;
  }

  if (state.status === "error") {
    return (
      <main className="grid min-h-screen place-items-center p-6">
        <Card className="max-w-md p-6 text-center">
          <h1 className="text-xl font-bold text-white">Tecponto</h1>
          <p className="mt-3 text-sm text-tec-subtle">{state.message}</p>
          <Button className="mt-5" onClick={() => void load()} variant="primary">
            Tentar novamente
          </Button>
        </Card>
      </main>
    );
  }

  const panel = panelDefinitions[state.boot.user.panel] ?? panelDefinitions.sem_papel;
  const currentView = activeView === "overview" ? null : viewTitles[activeView];

  return (
    <div className="min-h-screen">
      <Sidebar
        activeItemId={activeView === "service-order-detail" ? "service-orders" : activeView}
        onComingSoon={showComingSoon}
        onNavigate={setActiveView}
        sections={panel.nav}
        user={state.boot.user}
      />
      <Topbar onComingSoon={showComingSoon} onLogout={logout} user={state.boot.user} />

      <main className="tp-main-shell p-4">
        <section className="tp-content-shell mx-auto">
          <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <h1 className="text-3xl font-black text-white md:text-4xl">
                {currentView ? currentView.title : panel.title}
              </h1>
              <p className="mt-1 text-sm text-tec-subtle">{currentView ? currentView.subtitle : panel.subtitle}</p>
            </div>
            <Button icon={<RefreshCw size={18} />} onClick={() => void load()}>
              Atualizar
            </Button>
          </div>

          {activeView === "overview" ? (
            <OverviewContent
              actions={panel.actions}
              metrics={state.metrics}
              onComingSoon={showComingSoon}
              onNavigate={setActiveView}
              onStartCheckin={startCheckin}
              onOpenServiceOrder={openServiceOrder}
              orders={state.orders}
              panel={panel}
            />
          ) : (
            <NavigationContent
              activeView={activeView}
              onComingSoon={showComingSoon}
              onNavigate={setActiveView}
              onOpenServiceOrder={openServiceOrder}
              onStartCheckin={startCheckin}
              orders={state.orders}
              selectedOrderName={selectedOrderName}
            />
          )}
        </section>
      </main>
      <CheckinWizard
        onClose={() => setCheckinOpen(false)}
        onCreated={handleCheckinCreated}
        onOpenOrder={openServiceOrder}
        open={checkinOpen}
      />
      {toast ? <Toast message={toast} tone="success" /> : null}
    </div>
  );
}

function OverviewContent({
  actions,
  metrics,
  onComingSoon,
  onNavigate,
  onOpenServiceOrder,
  onStartCheckin,
  orders,
  panel,
}: {
  actions: ActionDefinition[];
  metrics: DashboardMetrics;
  onComingSoon: (label: string, block?: string) => void;
  onNavigate: (target: NavigationTarget) => void;
  onOpenServiceOrder: (name: string) => void;
  onStartCheckin: () => void;
  orders: ServiceOrderSummary[];
  panel: (typeof panelDefinitions)[keyof typeof panelDefinitions];
}) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {panel.metrics.map((metric) => (
          <MetricCard
            detail={metric.detail}
            icon={<metric.icon size={22} />}
            key={metric.label}
            label={metric.label}
            tone={metric.tone}
            value={metric.value(metrics)}
          />
        ))}
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <OperationsTable
          onComingSoon={onComingSoon}
          onOpenOrder={onOpenServiceOrder}
          onShowAll={() => onNavigate("service-orders")}
          orders={orders}
          title={panel.tableTitle}
        />
        <RightRail actions={actions} onComingSoon={onComingSoon} onNavigate={onNavigate} onStartCheckin={onStartCheckin} />
      </div>
    </>
  );
}

function NavigationContent({
  activeView,
  onComingSoon,
  onNavigate,
  onOpenServiceOrder,
  onStartCheckin,
  orders,
  selectedOrderName,
}: {
  activeView: NavigationTarget;
  onComingSoon: (label: string, block?: string) => void;
  onNavigate: (target: NavigationTarget) => void;
  onOpenServiceOrder: (name: string) => void;
  onStartCheckin: () => void;
  orders: ServiceOrderSummary[];
  selectedOrderName: string | null;
}) {
  if (activeView === "service-order-detail") {
    return selectedOrderName ? (
      <ServiceOrderDetail
        name={selectedOrderName}
        onBack={() => onNavigate("service-orders")}
        onComingSoon={onComingSoon}
      />
    ) : (
      <Card className="p-5 text-sm text-tec-subtle">Selecione uma OS na fila para abrir o detalhe.</Card>
    );
  }

  if (activeView === "service-orders") {
    return (
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <OperationsTable
          onComingSoon={onComingSoon}
          onOpenOrder={onOpenServiceOrder}
          orders={orders}
          title="Ordens de serviço"
        />
        <ActionPanel
          actions={[
            { icon: Wrench, label: "Nova OS", detail: "Check-in do balcão", soon: "bloco 3.1c" },
            { icon: SearchIcon, label: "Buscar cliente", detail: "Localizar cadastro", target: "customers" },
            { icon: RefreshCw, label: "Atualizar fila", detail: "Recarregar dados", soon: "bloco 3.1b" },
          ]}
          onComingSoon={onComingSoon}
          onNavigate={onNavigate}
          onStartCheckin={onStartCheckin}
          title="Atalhos de OS"
        />
      </div>
    );
  }

  if (activeView === "customers") {
    return <CustomerLookup />;
  }

  if (activeView === "devices") {
    return <DeviceLookup />;
  }

  if (activeView === "trade-ins") {
    return <TradeLookup />;
  }

  if (activeView === "parts-stock") {
    return <StockLookup />;
  }

  return <SalesLookup onComingSoon={onComingSoon} onNavigate={onNavigate} />;
}

function OperationsTable({
  onComingSoon,
  onOpenOrder,
  onShowAll,
  orders,
  title,
}: {
  onComingSoon: (label: string, block?: string) => void;
  onOpenOrder: (name: string) => void;
  onShowAll?: () => void;
  orders: ServiceOrderSummary[];
  title: string;
}) {
  const columns = useMemo<Array<TableColumn<ServiceOrderSummary>>>(
    () => [
      {
        key: "name",
        label: "OS",
        render: (row) => <span className="font-semibold text-white">{row.name}</span>,
      },
      {
        key: "customer",
        label: "Cliente",
        render: (row) => (
          <span>
            <span className="block text-white">{row.customer ?? "Cliente não informado"}</span>
            <span className="block text-xs text-tec-muted">{row.customer_device ?? "Aparelho não vinculado"}</span>
          </span>
        ),
      },
      {
        key: "description",
        label: "Descrição",
        render: (row) => row.reported_defect ?? "Sem descrição",
      },
      {
        key: "status",
        label: "Status",
        render: (row) => <BadgeStatus status={row.workflow_state} />,
      },
      {
        key: "responsible",
        label: "Responsável",
        render: (row) => row.technician ?? row.attendant ?? "Não definido",
      },
      {
        key: "updated",
        label: "Atualização",
        render: (row) => formatDate(row.modified),
      },
    ],
    [],
  );

  return (
    <Card className="p-4">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-white">{title}</h2>
          <span className="rounded-full bg-tec-orange/20 px-2 py-1 text-xs font-bold text-tec-orange">
            {orders.length}
          </span>
        </div>
        <Button icon={<RefreshCw size={17} />} onClick={() => onComingSoon("Filtros da OS", "bloco 3.1b")}>
          Filtros
        </Button>
      </div>
      <DataTable
        columns={columns}
        emptyLabel="Nenhuma OS encontrada para este papel."
        onRowClick={(row) => onOpenOrder(row.name)}
        rows={orders}
      />
      {onShowAll ? (
        <button
          className="mx-auto mt-4 flex items-center gap-2 text-sm font-semibold text-tec-subtle hover:text-white"
          onClick={onShowAll}
          title="Abrir lista completa de ordens de serviço"
          type="button"
        >
          Ver todos os atendimentos
          <ArrowRight size={17} />
        </button>
      ) : null}
    </Card>
  );
}

function ServiceOrderDetail({
  name,
  onBack,
  onComingSoon,
}: {
  name: string;
  onBack: () => void;
  onComingSoon: (label: string, block?: string) => void;
}) {
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "ready"; detail: ServiceOrderDetailResponse }
    | { status: "error"; message: string }
  >({ status: "loading" });
  const [activeFlow, setActiveFlow] = useState<"approve" | "reject" | "pickup" | null>(null);

  useEffect(() => {
    let mounted = true;
    setActiveFlow(null);
    setState({ status: "loading" });
    serviceOrders
      .detail(name)
      .then((detail) => {
        if (mounted) {
          setState({ status: "ready", detail });
        }
      })
      .catch((error) => {
        if (mounted) {
          setState({ status: "error", message: error instanceof Error ? error.message : "Falha ao abrir a OS" });
        }
      });
    return () => {
      mounted = false;
    };
  }, [name]);

  if (state.status === "loading") {
    return (
      <Card className="p-6">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-tec-orange border-t-transparent" />
        <p className="mt-4 text-sm font-semibold text-tec-subtle">Carregando detalhe da OS {name}</p>
      </Card>
    );
  }

  if (state.status === "error") {
    return (
      <Card className="p-6">
        <Button icon={<ArrowLeft size={17} />} onClick={onBack}>
          Voltar
        </Button>
        <p className="mt-4 text-sm text-tec-red">{state.message}</p>
      </Card>
    );
  }

  const detail = state.detail;
  const customerLabel = detail.customer?.customer_name ?? detail.customer?.name ?? "Cliente não informado";
  const deviceLabel =
    [detail.device?.brand, detail.device?.model, detail.device?.color].filter(Boolean).join(" ") ||
    detail.device?.name ||
    "Aparelho não vinculado";

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <button
              className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-tec-subtle hover:text-white"
              onClick={onBack}
              type="button"
            >
              <ArrowLeft size={17} />
              Voltar para a fila
            </button>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-2xl font-black text-white">{detail.name}</h2>
              <BadgeStatus status={detail.workflow_state} />
              {detail.priority ? <span className="rounded-full bg-white/5 px-3 py-1 text-xs text-tec-subtle">{detail.priority}</span> : null}
            </div>
            <p className="mt-2 max-w-3xl text-sm text-tec-subtle">{detail.reported_defect ?? "Sem defeito informado"}</p>
          </div>
          <PrintLinks links={detail.print_links} />
        </div>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <IdentityCard
              icon={<UserRound size={20} />}
              lines={[
                ["Cliente", customerLabel],
                ["Telefone", detail.customer?.mobile_no ?? "Não informado"],
                ["E-mail", detail.customer?.email_id ?? "Não informado"],
                ["Atendente", detail.attendant ?? "Não definido"],
              ]}
              title="Cliente"
            />
            <IdentityCard
              icon={<Smartphone size={20} />}
              lines={[
                ["Aparelho", deviceLabel],
                ["IMEI / Serial", detail.device?.imei_serial ?? "Não informado"],
                ["Capacidade", detail.device?.capacity ?? "Não informada"],
                ["Estado declarado", detail.physical_state ?? "Não informado"],
              ]}
              title="Aparelho"
            />
          </div>

          <BudgetCard detail={detail} />
          <TimelineCard events={detail.timeline} />
        </div>

        <aside className="space-y-4">
          <WorkflowCard
            actions={detail.workflow_actions}
            detail={detail}
            onComingSoon={onComingSoon}
            onOpenFlow={setActiveFlow}
          />
          <Card className="p-4">
            <h3 className="text-base font-bold text-white">Atendimento</h3>
            <dl className="mt-4 space-y-3 text-sm">
              <DetailLine label="Entrada" value={formatDate(detail.entry_date)} />
              <DetailLine label="Prazo de aprovação" value={detail.approval_deadline ? formatDate(detail.approval_deadline) : "Não definido"} />
              <DetailLine label="Técnico" value={detail.technician ?? "Não definido"} />
              <DetailLine label="Garantia até" value={detail.warranty.warranty_expiry || "Não aplicada"} />
              <DetailLine label="Atualização" value={formatDate(detail.modified)} />
            </dl>
          </Card>
        </aside>
      </div>
      <BudgetDecisionModal
        detail={detail}
        mode="approve"
        onClose={() => setActiveFlow(null)}
        onUpdated={(updated) => setState({ status: "ready", detail: updated })}
        open={activeFlow === "approve"}
      />
      <BudgetDecisionModal
        detail={detail}
        mode="reject"
        onClose={() => setActiveFlow(null)}
        onUpdated={(updated) => setState({ status: "ready", detail: updated })}
        open={activeFlow === "reject"}
      />
      <PickupModal
        detail={detail}
        onClose={() => setActiveFlow(null)}
        onUpdated={(updated) => setState({ status: "ready", detail: updated })}
        open={activeFlow === "pickup"}
      />
    </div>
  );
}

function IdentityCard({
  icon,
  lines,
  title,
}: {
  icon: ReactNode;
  lines: Array<[string, string]>;
  title: string;
}) {
  return (
    <Card className="p-4">
      <div className="mb-4 flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-card bg-tec-orange/15 text-tec-orange">{icon}</span>
        <h3 className="text-base font-bold text-white">{title}</h3>
      </div>
      <dl className="space-y-3 text-sm">
        {lines.map(([label, value]) => (
          <DetailLine key={label} label={label} value={value} />
        ))}
      </dl>
    </Card>
  );
}

function BudgetCard({ detail }: { detail: ServiceOrderDetailResponse }) {
  return (
    <Card className="p-4">
      <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-base font-bold text-white">Orçamento</h3>
          <p className="text-xs text-tec-muted">
            Versão {detail.totals.budget_version} · {detail.totals.quote_locked ? "travado" : "em edição"}
          </p>
        </div>
        <span className="tp-metric-value text-2xl font-bold text-white">{formatCurrency(detail.totals.grand_total)}</span>
      </div>

      <BudgetLines lines={detail.services} title="Serviços" type="service" />
      <div className="mt-4">
        <BudgetLines lines={detail.parts} title="Peças" type="part" />
      </div>

      <div className="mt-5 grid gap-3 border-t border-tec-border/20 pt-4 text-sm sm:grid-cols-2 xl:grid-cols-4">
        <TotalPill label="Mão de obra" value={formatCurrency(detail.totals.service_total)} />
        <TotalPill label="Peças" value={formatCurrency(detail.totals.parts_price_total)} />
        <TotalPill label="Desconto" value={formatCurrency(detail.totals.discount)} />
        <TotalPill label="Total" value={formatCurrency(detail.totals.grand_total)} strong />
      </div>
    </Card>
  );
}

function BudgetLines({
  lines,
  title,
  type,
}: {
  lines: ServiceOrderBudgetLine[];
  title: string;
  type: "service" | "part";
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-bold text-white">{title}</h4>
        <span className="rounded-full bg-white/5 px-2 py-1 text-xs text-tec-muted">{lines.length}</span>
      </div>
      <div className="overflow-hidden rounded-card border border-tec-border/20">
        {lines.length ? (
          lines.map((line, index) => (
            <div
              className="grid gap-3 border-b border-tec-border/15 bg-white/[0.018] p-3 text-sm last:border-0 md:grid-cols-[minmax(0,1fr)_90px_120px_120px]"
              key={`${line.item_code ?? title}-${index}`}
            >
              <div className="min-w-0">
                <p className="truncate font-semibold text-white">{line.description || line.item_code || "Item sem descrição"}</p>
                <p className="mt-1 text-xs text-tec-muted">
                  {line.item_code ?? "Sem item"}
                  {type === "service" && line.technician ? ` · ${line.technician}` : ""}
                  {type === "part" && line.outcome ? ` · ${line.outcome}` : ""}
                </p>
              </div>
              <span className="text-tec-subtle">Qtd. {line.qty.toLocaleString("pt-BR")}</span>
              <span className="text-tec-subtle">{formatCurrency(line.unit_price)}</span>
              <span className="font-semibold text-white">{formatCurrency(line.amount)}</span>
            </div>
          ))
        ) : (
          <p className="p-3 text-sm text-tec-muted">Nenhuma linha registrada.</p>
        )}
      </div>
    </div>
  );
}

function WorkflowCard({
  actions,
  detail,
  onComingSoon,
  onOpenFlow,
}: {
  actions: ServiceOrderWorkflowAction[];
  detail: ServiceOrderDetailResponse;
  onComingSoon: (label: string, block?: string) => void;
  onOpenFlow: (flow: "approve" | "reject" | "pickup") => void;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-base font-bold text-white">Ações do workflow</h3>
        <BadgeStatus status={detail.workflow_state} />
      </div>
      <div className="mt-4 space-y-3">
        {actions.length ? (
          actions.map((action) => (
            <button
              className="flex w-full items-center justify-between gap-3 rounded-card border border-tec-border/20 bg-white/[0.035] p-3 text-left transition hover:border-tec-orange/50 hover:bg-tec-orange/10"
              key={`${action.action}-${action.next_state}`}
              onClick={() => {
                if (action.next_state === "Aprovado") {
                  onOpenFlow("approve");
                } else if (action.next_state === "Reprovado") {
                  onOpenFlow("reject");
                } else if (action.next_state === "Entregue") {
                  onOpenFlow("pickup");
                } else {
                  onComingSoon(`${action.action} ${detail.name}`, "bloco 3.1x");
                }
              }}
              title={workflowActionTitle(action)}
              type="button"
            >
              <span>
                <span className="block text-sm font-bold text-white">{workflowActionLabel(action)}</span>
                <span className="mt-1 block text-xs text-tec-muted">Vai para {action.next_state}</span>
              </span>
              <ArrowRight className="text-tec-orange" size={17} />
            </button>
          ))
        ) : (
          <div className="rounded-card border border-tec-border/20 bg-white/[0.025] p-4 text-sm text-tec-muted">
            Nenhuma ação disponível para este papel neste estado.
          </div>
        )}
      </div>
    </Card>
  );
}

function workflowActionLabel(action: ServiceOrderWorkflowAction) {
  if (action.next_state === "Aprovado") {
    return "Aprovar";
  }
  if (action.next_state === "Reprovado") {
    return "Reprovar";
  }
  if (action.next_state === "Entregue") {
    return "Entregar";
  }
  return action.action;
}

function workflowActionTitle(action: ServiceOrderWorkflowAction) {
  if (["Aprovado", "Reprovado", "Entregue"].includes(action.next_state)) {
    return `Abrir fluxo para ${workflowActionLabel(action).toLowerCase()}`;
  }
  return "Ação ainda não disponível neste bloco";
}

function TimelineCard({ events }: { events: ServiceOrderTimelineEvent[] }) {
  return (
    <Card className="p-4">
      <h3 className="text-base font-bold text-white">Histórico</h3>
      <div className="mt-4 space-y-4">
        {events.map((event, index) => (
          <div className="flex gap-3" key={`${event.title}-${index}`}>
            <span className={`mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full ${timelineToneClass(event.tone)}`}>
              <Clock3 size={15} />
            </span>
            <div className="min-w-0 border-b border-tec-border/15 pb-4 last:border-0 last:pb-0">
              <p className="font-semibold text-white">{event.title}</p>
              <p className="mt-1 text-sm text-tec-subtle">{event.detail ?? "Sem detalhe"}</p>
              <p className="mt-1 text-xs text-tec-muted">{event.date ? formatDate(event.date) : "Sem data"}</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function PrintLinks({ links }: { links: ServiceOrderPrintLink[] }) {
  const icons = [FileText, Printer, Tag];
  return (
    <div className="flex flex-wrap gap-2">
      {links.map((link, index) => {
        const Icon = icons[index] ?? Printer;
        return (
          <a
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control border border-tec-border/30 bg-tec-panel-strong/70 px-4 text-sm font-semibold text-tec-text transition hover:border-tec-orange/50"
            href={link.url}
            key={link.format}
            rel="noreferrer"
            target="_blank"
            title={`Abrir ${link.label}`}
          >
            <Icon size={17} />
            {link.label}
          </a>
        );
      })}
    </div>
  );
}

function DetailLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-tec-muted">{label}</dt>
      <dd className="max-w-[68%] text-right font-semibold text-tec-subtle">{value}</dd>
    </div>
  );
}

function TotalPill({ label, strong, value }: { label: string; strong?: boolean; value: string }) {
  return (
    <div className="rounded-card border border-tec-border/20 bg-white/[0.025] p-3">
      <p className="text-xs text-tec-muted">{label}</p>
      <p className={strong ? "mt-1 font-bold text-white" : "mt-1 font-semibold text-tec-subtle"}>{value}</p>
    </div>
  );
}

function CustomerLookup() {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<CustomerSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const search = useCallback(async (nextQuery: string) => {
    setStatus("loading");
    try {
      const response = await balcao.searchCustomers(nextQuery, 12);
      setRows(response.items);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void search("");
  }, [search]);

  const columns = useMemo<Array<TableColumn<CustomerSummary>>>(
    () => [
      { key: "name", label: "Código", render: (row) => <span className="font-semibold text-white">{row.name}</span> },
      { key: "customer_name", label: "Nome", render: (row) => row.customer_name ?? row.name },
      { key: "mobile_no", label: "Telefone", render: (row) => row.mobile_no ?? "Sem telefone" },
      { key: "email_id", label: "E-mail", render: (row) => row.email_id ?? "Sem e-mail" },
      { key: "modified", label: "Atualização", render: (row) => formatDate(row.modified) },
    ],
    [],
  );

  return (
    <LookupCard
      columns={columns}
      emptyLabel={status === "error" ? "Falha ao buscar clientes." : "Nenhum cliente encontrado."}
      onSearch={(event) => {
        event.preventDefault();
        void search(query);
      }}
      placeholder="Buscar cliente por nome, telefone ou e-mail"
      query={query}
      rows={rows}
      setQuery={setQuery}
      status={status}
      title="Clientes"
    />
  );
}

function DeviceLookup() {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<CustomerDeviceSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const search = useCallback(async (nextQuery: string) => {
    setStatus("loading");
    try {
      const response = await balcao.listDevices(nextQuery, 12);
      setRows(response.items);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void search("");
  }, [search]);

  const columns = useMemo<Array<TableColumn<CustomerDeviceSummary>>>(
    () => [
      { key: "name", label: "Cadastro", render: (row) => <span className="font-semibold text-white">{row.name}</span> },
      { key: "customer", label: "Cliente", render: (row) => row.customer ?? "Sem cliente" },
      { key: "model", label: "Aparelho", render: (row) => [row.brand, row.model].filter(Boolean).join(" ") || "Sem modelo" },
      { key: "imei_serial", label: "IMEI / Serial", render: (row) => row.imei_serial ?? "Não informado" },
      { key: "capacity", label: "Capacidade", render: (row) => row.capacity ?? "Não informada" },
    ],
    [],
  );

  return (
    <LookupCard
      columns={columns}
      emptyLabel={status === "error" ? "Falha ao buscar aparelhos." : "Nenhum aparelho encontrado."}
      onSearch={(event) => {
        event.preventDefault();
        void search(query);
      }}
      placeholder="Buscar por cliente, modelo ou IMEI"
      query={query}
      rows={rows}
      setQuery={setQuery}
      status={status}
      title="Aparelhos"
    />
  );
}

function TradeLookup() {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<TradeEvaluationSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const search = useCallback(async (nextQuery: string) => {
    setStatus("loading");
    try {
      const response = await balcao.listTradeEvaluations(nextQuery, 12);
      setRows(response.items);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void search("");
  }, [search]);

  const columns = useMemo<Array<TableColumn<TradeEvaluationSummary>>>(
    () => [
      { key: "name", label: "Avaliação", render: (row) => <span className="font-semibold text-white">{row.name}</span> },
      { key: "customer", label: "Cliente", render: (row) => row.customer ?? "Sem cliente" },
      { key: "device", label: "Aparelho", render: (row) => row.evaluated_device_desc ?? row.model ?? "Sem descrição" },
      { key: "imei", label: "IMEI / Serial", render: (row) => row.imei ?? "Não informado" },
      { key: "status", label: "Status", render: (row) => <BadgeStatus status={row.workflow_state} /> },
    ],
    [],
  );

  return (
    <LookupCard
      columns={columns}
      emptyLabel={status === "error" ? "Falha ao buscar trocas." : "Nenhuma avaliação encontrada."}
      onSearch={(event) => {
        event.preventDefault();
        void search(query);
      }}
      placeholder="Buscar por cliente, aparelho ou IMEI"
      query={query}
      rows={rows}
      setQuery={setQuery}
      status={status}
      title="Trocas"
    />
  );
}

function StockLookup() {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<StockItemSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const search = useCallback(async (nextQuery: string) => {
    setStatus("loading");
    try {
      const response = await balcao.listStockItems(nextQuery, 12);
      setRows(response.items);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void search("");
  }, [search]);

  const columns = useMemo<Array<TableColumn<StockItemSummary>>>(
    () => [
      { key: "item_code", label: "Item", render: (row) => <span className="font-semibold text-white">{row.item_code}</span> },
      { key: "item_name", label: "Descrição", render: (row) => row.item_name ?? row.item_code },
      { key: "item_group", label: "Grupo", render: (row) => row.item_group ?? "Sem grupo" },
      { key: "warehouse", label: "Estoque", render: (row) => row.warehouse ?? "Sem depósito" },
      { key: "available_qty", label: "Disponível", render: (row) => row.available_qty.toLocaleString("pt-BR") },
    ],
    [],
  );

  return (
    <LookupCard
      columns={columns}
      emptyLabel={status === "error" ? "Falha ao consultar estoque." : "Nenhum item encontrado."}
      onSearch={(event) => {
        event.preventDefault();
        void search(query);
      }}
      placeholder="Buscar peça, produto ou depósito"
      query={query}
      rows={rows}
      setQuery={setQuery}
      status={status}
      title="Peças e estoque"
    />
  );
}

function SalesLookup({
  onComingSoon,
  onNavigate,
}: {
  onComingSoon: (label: string, block?: string) => void;
  onNavigate: (target: NavigationTarget) => void;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
      <Card className="p-4">
        <h2 className="text-lg font-bold text-white">Vendas e acessórios</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Button icon={<SearchIcon size={17} />} onClick={() => onNavigate("parts-stock")} variant="secondary">
            Consultar item
          </Button>
          <Button icon={<SearchIcon size={17} />} onClick={() => onNavigate("customers")} variant="secondary">
            Buscar cliente
          </Button>
        </div>
      </Card>
      <ActionPanel actions={[]} onComingSoon={onComingSoon} onNavigate={onNavigate} title="Atalhos" />
    </div>
  );
}

function LookupCard<T>({
  columns,
  emptyLabel,
  onSearch,
  placeholder,
  query,
  rows,
  setQuery,
  status,
  title,
}: {
  columns: Array<TableColumn<T>>;
  emptyLabel: string;
  onSearch: (event: FormEvent<HTMLFormElement>) => void;
  placeholder: string;
  query: string;
  rows: T[];
  setQuery: (query: string) => void;
  status: "loading" | "ready" | "error";
  title: string;
}) {
  return (
    <Card className="p-4">
      <form className="mb-4 flex flex-col gap-3 md:flex-row" onSubmit={onSearch}>
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-tec-muted" size={18} />
          <input
            className="h-11 w-full rounded-control border border-tec-border/25 bg-white/[0.035] pl-11 pr-4 text-sm text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70"
            onChange={(event) => setQuery(event.target.value)}
            placeholder={placeholder}
            type="search"
            value={query}
          />
        </div>
        <Button icon={<SearchIcon size={17} />} type="submit" variant="primary">
          Buscar
        </Button>
      </form>
      <div className="mb-4 flex items-center gap-3">
        <h2 className="text-lg font-bold text-white">{title}</h2>
        <span className="rounded-full bg-tec-orange/20 px-2 py-1 text-xs font-bold text-tec-orange">
          {status === "loading" ? "..." : rows.length}
        </span>
      </div>
      <DataTable columns={columns} emptyLabel={status === "loading" ? "Carregando..." : emptyLabel} rows={rows} />
    </Card>
  );
}

function RightRail({
  actions,
  onComingSoon,
  onNavigate,
  onStartCheckin,
}: {
  actions: ActionDefinition[];
  onComingSoon: (label: string, block?: string) => void;
  onNavigate: (target: NavigationTarget) => void;
  onStartCheckin: () => void;
}) {
  return (
    <aside className="space-y-4">
      <ActionPanel
        actions={actions}
        onComingSoon={onComingSoon}
        onNavigate={onNavigate}
        onStartCheckin={onStartCheckin}
        title="Ações rápidas"
      />
      <Card className="p-4">
        <h2 className="text-lg font-bold text-white">Alertas</h2>
        <div className="mt-4 space-y-3 text-sm">
          <AlertLine onComingSoon={onComingSoon} tone="red" title="Aprovações pendentes" />
          <AlertLine onComingSoon={onComingSoon} tone="amber" title="Peças aguardando chegada" />
          <AlertLine onComingSoon={onComingSoon} tone="green" title="Mensagens do WhatsApp" />
        </div>
      </Card>
    </aside>
  );
}

function ActionPanel({
  actions,
  onComingSoon,
  onNavigate,
  onStartCheckin,
  title,
}: {
  actions: ActionDefinition[];
  onComingSoon: (label: string, block?: string) => void;
  onNavigate: (target: NavigationTarget) => void;
  onStartCheckin?: () => void;
  title: string;
}) {
  return (
    <Card className="p-4">
      <h2 className="mb-4 text-lg font-bold text-white">{title}</h2>
      {actions.length ? (
        <div className="grid grid-cols-2 gap-3">
          {actions.map((action, index) => {
            const opensCheckin = action.soon === "bloco 3.1c" && onStartCheckin;
            return (
              <button
                className="min-h-[96px] rounded-card border border-tec-border/20 bg-white/[0.035] p-3 text-left transition hover:border-tec-orange/50 hover:bg-tec-orange/10"
                key={`${action.label}-${index}`}
                onClick={() => {
                  if (opensCheckin) {
                    onStartCheckin();
                  } else if (action.soon) {
                    onComingSoon(action.label, action.soon);
                  } else if (action.target) {
                    onNavigate(action.target);
                  }
                }}
                title={opensCheckin ? action.label : action.soon ? `Em breve — ${action.soon}` : action.label}
                type="button"
              >
                <action.icon className="mb-3 text-tec-orange" size={22} />
                <span className="block text-sm font-bold text-white">{action.label}</span>
                <span className="mt-1 block text-xs text-tec-muted">{action.detail}</span>
                {action.soon && !opensCheckin ? (
                  <span className="mt-2 inline-flex rounded-full bg-white/5 px-2 py-1 text-[10px] font-bold uppercase text-tec-muted">
                    Em breve
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      ) : (
        <div className="rounded-card border border-tec-border/20 bg-white/[0.025] p-4 text-sm text-tec-muted">
          Selecione uma ação no painel principal.
        </div>
      )}
    </Card>
  );
}

function AlertLine({
  onComingSoon,
  title,
  tone,
}: {
  onComingSoon: (label: string, block?: string) => void;
  title: string;
  tone: "red" | "amber" | "green";
}) {
  const toneClass = {
    red: "bg-tec-red/20 text-tec-red",
    amber: "bg-tec-amber/20 text-tec-amber",
    green: "bg-tec-green/20 text-tec-green",
  }[tone];

  return (
    <button
      className="flex w-full items-center justify-between border-b border-tec-border/20 pb-3 text-left last:border-0 last:pb-0"
      onClick={() => onComingSoon(title, "bloco 3.1x")}
      title={`Em breve — bloco 3.1x`}
      type="button"
    >
      <span className="flex items-center gap-3 text-tec-subtle">
        <span className={`h-2.5 w-2.5 rounded-full ${toneClass}`} />
        {title}
      </span>
      <span className="text-xs font-bold text-tec-orange">Ver</span>
    </button>
  );
}

function LoadingShell() {
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <Card className="w-full max-w-md p-6 text-center">
        <div className="mx-auto h-12 w-12 animate-spin rounded-full border-2 border-tec-orange border-t-transparent" />
        <p className="mt-4 text-sm font-semibold text-tec-subtle">Carregando Tecponto</p>
      </Card>
    </main>
  );
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

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    currency: "BRL",
    style: "currency",
  }).format(value || 0);
}

function timelineToneClass(tone: ServiceOrderTimelineEvent["tone"]) {
  return {
    amber: "bg-tec-amber/20 text-tec-amber",
    blue: "bg-tec-blue/20 text-tec-blue",
    green: "bg-tec-green/20 text-tec-green",
    orange: "bg-tec-orange/20 text-tec-orange",
    red: "bg-tec-red/20 text-tec-red",
  }[tone];
}
