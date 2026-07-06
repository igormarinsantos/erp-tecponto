import { useEffect, useMemo, useState } from "react";
import { ArrowRight, RefreshCw } from "lucide-react";

import { getBoot, logout, serviceOrders, type BootResponse, type ServiceOrderSummary } from "./api";
import { panelDefinitions, type ActionDefinition } from "./roleConfig";
import { BadgeStatus, Button, Card, DataTable, MetricCard, Sidebar, Topbar, type TableColumn } from "./ui";

type LoadState =
  | { status: "loading" }
  | { status: "ready"; boot: BootResponse; orders: ServiceOrderSummary[] }
  | { status: "error"; message: string };

export function App() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  async function load() {
    setState({ status: "loading" });
    try {
      const [boot, orderList] = await Promise.all([getBoot(), serviceOrders.list(12)]);
      setState({ status: "ready", boot, orders: orderList.items });
    } catch (error) {
      setState({ status: "error", message: error instanceof Error ? error.message : "Falha ao carregar" });
    }
  }

  useEffect(() => {
    void load();
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

  return (
    <div className="min-h-screen">
      <Sidebar sections={panel.nav} user={state.boot.user} />
      <Topbar onLogout={logout} user={state.boot.user} />

      <main className="p-4 lg:pl-[calc(var(--tp-sidebar-width)+24px)]">
        <section className="mx-auto max-w-[1660px]">
          <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <h1 className="text-3xl font-black text-white md:text-4xl">{panel.title}</h1>
              <p className="mt-1 text-sm text-tec-subtle">{panel.subtitle}</p>
            </div>
            <Button icon={<RefreshCw size={18} />} onClick={load}>
              Atualizar
            </Button>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {panel.metrics.map((metric) => (
              <MetricCard
                detail={metric.detail}
                icon={<metric.icon size={22} />}
                key={metric.label}
                label={metric.label}
                tone={metric.tone}
                value={metric.value(state.orders.length)}
              />
            ))}
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
            <OperationsTable orders={state.orders} title={panel.tableTitle} />
            <RightRail actions={panel.actions} />
          </div>
        </section>
      </main>
    </div>
  );
}

function OperationsTable({ orders, title }: { orders: ServiceOrderSummary[]; title: string }) {
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
        <Button icon={<RefreshCw size={17} />}>Filtros</Button>
      </div>
      <DataTable columns={columns} emptyLabel="Nenhuma OS encontrada para este papel." rows={orders} />
      <button className="mx-auto mt-4 flex items-center gap-2 text-sm font-semibold text-tec-subtle hover:text-white">
        Ver todos os atendimentos
        <ArrowRight size={17} />
      </button>
    </Card>
  );
}

function RightRail({ actions }: { actions: ActionDefinition[] }) {
  return (
    <aside className="space-y-4">
      <Card className="p-4">
        <h2 className="mb-4 text-lg font-bold text-white">Ações rápidas</h2>
        <div className="grid grid-cols-2 gap-3">
          {actions.map((action, index) => (
            <button
              className="min-h-[96px] rounded-card border border-tec-border/20 bg-white/[0.035] p-3 text-left transition hover:border-tec-orange/50 hover:bg-tec-orange/10"
              key={`${action.label}-${index}`}
              title={action.label}
              type="button"
            >
              <action.icon className="mb-3 text-tec-orange" size={22} />
              <span className="block text-sm font-bold text-white">{action.label}</span>
              <span className="mt-1 block text-xs text-tec-muted">{action.detail}</span>
            </button>
          ))}
        </div>
      </Card>
      <Card className="p-4">
        <h2 className="text-lg font-bold text-white">Alertas</h2>
        <div className="mt-4 space-y-3 text-sm">
          <AlertLine tone="red" title="Aprovações pendentes" />
          <AlertLine tone="amber" title="Peças aguardando chegada" />
          <AlertLine tone="green" title="Mensagens do WhatsApp" />
        </div>
      </Card>
    </aside>
  );
}

function AlertLine({ title, tone }: { title: string; tone: "red" | "amber" | "green" }) {
  const toneClass = {
    red: "bg-tec-red/20 text-tec-red",
    amber: "bg-tec-amber/20 text-tec-amber",
    green: "bg-tec-green/20 text-tec-green",
  }[tone];

  return (
    <div className="flex items-center justify-between border-b border-tec-border/20 pb-3 last:border-0 last:pb-0">
      <span className="flex items-center gap-3 text-tec-subtle">
        <span className={`h-2.5 w-2.5 rounded-full ${toneClass}`} />
        {title}
      </span>
      <span className="text-xs font-bold text-tec-orange">Ver</span>
    </div>
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
