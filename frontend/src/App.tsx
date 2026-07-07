import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, RefreshCw, Search as SearchIcon } from "lucide-react";

import {
  balcao,
  getBoot,
  logout,
  serviceOrders,
  type BootResponse,
  type CustomerDeviceSummary,
  type CustomerSummary,
  type DashboardMetrics,
  type NavigationTarget,
  type ServiceOrderSummary,
  type StockItemSummary,
  type TradeEvaluationSummary,
} from "./api";
import { panelDefinitions, type ActionDefinition } from "./roleConfig";
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
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<number | null>(null);

  async function load() {
    setState({ status: "loading" });
    try {
      const [boot, orderList, metrics] = await Promise.all([getBoot(), serviceOrders.list(12), balcao.getDashboardMetrics()]);
      setState({ status: "ready", boot, metrics, orders: orderList.items });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Falha ao carregar" });
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    return () => {
      if (toastTimer.current) {
        window.clearTimeout(toastTimer.current);
      }
    };
  }, []);

  const showComingSoon = useCallback((label: string, block = "bloco 3.1x") => {
    setToast(`${label}: em breve — ${block}`);
    if (toastTimer.current) {
      window.clearTimeout(toastTimer.current);
    }
    toastTimer.current = window.setTimeout(() => setToast(null), 3200);
  }, []);

  if (state.status === "loading") {
    return <LoadingShell />;
  }

  if (state.status === "error") {
    return (
      <main className="grid min-h-screen place-items-center p-6">
        <Card className="max-w-md p-6 text-center">
          <h1 className="text-xl font-bold text-white">Tecponto</h1>
          <p className="mt-3 text-sm text-tec-subtle">{state.message}</p>
          <Button className="mt-5" onClick={load} variant="primary">
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
        activeItemId={activeView}
        onComingSoon={showComingSoon}
        onNavigate={setActiveView}
        sections={panel.nav}
        user={state.boot.user}
      />
      <Topbar onComingSoon={showComingSoon} onLogout={logout} user={state.boot.user} />

      <main className="tp-main-shell p-4">
        <section className="mx-auto max-w-[1660px]">
          <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <h1 className="text-3xl font-black text-white md:text-4xl">
                {currentView ? currentView.title : panel.title}
              </h1>
              <p className="mt-1 text-sm text-tec-subtle">{currentView ? currentView.subtitle : panel.subtitle}</p>
            </div>
            <Button icon={<RefreshCw size={18} />} onClick={load}>
              Atualizar
            </Button>
          </div>

          {activeView === "overview" ? (
            <OverviewContent
              actions={panel.actions}
              metrics={state.metrics}
              onComingSoon={showComingSoon}
              onNavigate={setActiveView}
              orders={state.orders}
              panel={panel}
            />
          ) : (
            <NavigationContent
              activeView={activeView}
              onComingSoon={showComingSoon}
              onNavigate={setActiveView}
              orders={state.orders}
            />
          )}
        </section>
      </main>
      {toast ? <Toast message={toast} tone="success" /> : null}
    </div>
  );
}

function OverviewContent({
  actions,
  metrics,
  onComingSoon,
  onNavigate,
  orders,
  panel,
}: {
  actions: ActionDefinition[];
  metrics: DashboardMetrics;
  onComingSoon: (label: string, block?: string) => void;
  onNavigate: (target: NavigationTarget) => void;
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
          onShowAll={() => onNavigate("service-orders")}
          orders={orders}
          title={panel.tableTitle}
        />
        <RightRail actions={actions} onComingSoon={onComingSoon} onNavigate={onNavigate} />
      </div>
    </>
  );
}

function NavigationContent({
  activeView,
  onComingSoon,
  onNavigate,
  orders,
}: {
  activeView: NavigationTarget;
  onComingSoon: (label: string, block?: string) => void;
  onNavigate: (target: NavigationTarget) => void;
  orders: ServiceOrderSummary[];
}) {
  if (activeView === "service-orders") {
    return (
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <OperationsTable onComingSoon={onComingSoon} orders={orders} title="Ordens de serviço" />
        <ActionPanel
          actions={[
            { icon: SearchIcon, label: "Buscar cliente", detail: "Localizar cadastro", target: "customers" },
            { icon: RefreshCw, label: "Atualizar fila", detail: "Recarregar dados", soon: "bloco 3.1b" },
          ]}
          onComingSoon={onComingSoon}
          onNavigate={onNavigate}
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
  onShowAll,
  orders,
  title,
}: {
  onComingSoon: (label: string, block?: string) => void;
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
        onRowClick={(row) => onComingSoon(`Detalhe da OS ${row.name}`, "bloco 3.1b")}
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
}: {
  actions: ActionDefinition[];
  onComingSoon: (label: string, block?: string) => void;
  onNavigate: (target: NavigationTarget) => void;
}) {
  return (
    <aside className="space-y-4">
      <ActionPanel actions={actions} onComingSoon={onComingSoon} onNavigate={onNavigate} title="Ações rápidas" />
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
  title,
}: {
  actions: ActionDefinition[];
  onComingSoon: (label: string, block?: string) => void;
  onNavigate: (target: NavigationTarget) => void;
  title: string;
}) {
  return (
    <Card className="p-4">
      <h2 className="mb-4 text-lg font-bold text-white">{title}</h2>
      {actions.length ? (
        <div className="grid grid-cols-2 gap-3">
          {actions.map((action, index) => (
            <button
              className="min-h-[96px] rounded-card border border-tec-border/20 bg-white/[0.035] p-3 text-left transition hover:border-tec-orange/50 hover:bg-tec-orange/10"
              key={`${action.label}-${index}`}
              onClick={() => {
                if (action.soon) {
                  onComingSoon(action.label, action.soon);
                } else if (action.target) {
                  onNavigate(action.target);
                }
              }}
              title={action.soon ? `Em breve — ${action.soon}` : action.label}
              type="button"
            >
              <action.icon className="mb-3 text-tec-orange" size={22} />
              <span className="block text-sm font-bold text-white">{action.label}</span>
              <span className="mt-1 block text-xs text-tec-muted">{action.detail}</span>
              {action.soon ? (
                <span className="mt-2 inline-flex rounded-full bg-white/5 px-2 py-1 text-[10px] font-bold uppercase text-tec-muted">
                  Em breve
                </span>
              ) : null}
            </button>
          ))}
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
