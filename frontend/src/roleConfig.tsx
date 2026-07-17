import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Bell,
  Boxes,
  ClipboardCheck,
  ClipboardList,
  CreditCard,
  FileText,
  Gauge,
  Grid2X2,
  Handshake,
  MessageCircle,
  PackageSearch,
  Search,
  ShoppingCart,
  Smartphone,
  Star,
  Target,
  Users,
  Wrench,
  Zap,
} from "lucide-react";

import type { DashboardMetrics, NavigationTarget, RolePanel } from "./api";
import type { NavSection } from "./ui";

export interface MetricDefinition {
  icon: LucideIcon;
  label: string;
  tone: "orange" | "green" | "blue" | "purple" | "amber" | "red";
  value: (metrics: DashboardMetrics) => string | number;
  detail: string;
}

export interface ActionDefinition {
  disabledReason?: string;
  icon: LucideIcon;
  label: string;
  detail: string;
  externalHref?: string;
  opensCheckin?: boolean;
  pendingLabel?: string;
  target?: NavigationTarget;
}

export interface PanelDefinition {
  title: string;
  subtitle: string;
  tableTitle: string;
  nav: NavSection[];
  metrics: MetricDefinition[];
  actions: ActionDefinition[];
}

const commonActions: ActionDefinition[] = [
  {
    icon: ShoppingCart,
    label: "Lançar venda",
    detail: "Venda no balcão",
    target: "pos",
  },
  { icon: Wrench, label: "Nova OS", detail: "Atendimento", opensCheckin: true },
  { icon: Search, label: "Buscar cliente", detail: "Nome, telefone ou IMEI", target: "customers" },
];

const brl = new Intl.NumberFormat("pt-BR", {
  currency: "BRL",
  style: "currency",
});

export const panelDefinitions: Record<RolePanel, PanelDefinition> = {
  atendente: {
    title: "Olá, Atendente Tecponto!",
    subtitle: "Confira os atendimentos e vendas que precisam da sua atenção.",
    tableTitle: "Fila de atendimento",
    nav: [
      {
        label: "Início",
        items: [{ id: "overview", icon: Grid2X2, label: "Visão geral", subtitle: "O que precisa de você" }],
      },
      {
        label: "Reparo",
        items: [
          { id: "service-orders", icon: Wrench, label: "Ordens de serviço", subtitle: "Criar, buscar e acompanhar" },
          { id: "repair-parts", icon: PackageSearch, label: "Peças", subtitle: "Estoque de reparo" },
        ],
      },
      {
        label: "Venda",
        items: [
          { id: "pos", icon: ShoppingCart, label: "PDV / Lançar venda", subtitle: "Venda rápida no balcão" },
          { id: "sales", icon: CreditCard, label: "Vendas", subtitle: "Histórico do balcão" },
          { id: "commercial-products", icon: Boxes, label: "Produtos", subtitle: "Estoque comercial" },
        ],
      },
      {
        label: "Troca",
        items: [
          { id: "trade-ins", icon: Handshake, label: "Avaliações de troca", subtitle: "Ofertas e propostas" },
          { id: "used-devices", icon: Smartphone, label: "Aparelhos usados", subtitle: "Estoque de trade-in" },
        ],
      },
      {
        label: "Cadastros",
        items: [
          { id: "customers", icon: Users, label: "Clientes", subtitle: "Base e histórico" },
          { id: "devices", icon: Smartphone, label: "Aparelhos dos clientes", subtitle: "Cadastro e histórico" },
          { id: "services", icon: Wrench, label: "Serviços", subtitle: "Catálogo de mão de obra" },
        ],
      },
    ],
    metrics: [
      { icon: ShoppingCart, label: "Vendas do dia", tone: "green", value: (metrics) => brl.format(metrics.sales_today_total), detail: "PDV Tecponto" },
      { icon: FileText, label: "OS aguardando aprovação", tone: "orange", value: (metrics) => metrics.service_orders.awaiting_approval, detail: "Orçamentos na fila" },
      { icon: ClipboardCheck, label: "Prontas para retirada", tone: "green", value: (metrics) => metrics.service_orders.ready_for_pickup, detail: "Entrega no balcão" },
      { icon: PackageSearch, label: "Aguardando peça", tone: "blue", value: (metrics) => metrics.service_orders.waiting_part, detail: "Reparo pendente" },
    ],
    actions: [
      ...commonActions,
      { icon: Smartphone, label: "Cadastrar aparelho", detail: "Vincular ao cliente", target: "devices" },
      { icon: Handshake, label: "Avaliar troca", detail: "TROQUE", target: "trade-ins" },
      { icon: MessageCircle, label: "Enviar WhatsApp", detail: "Contato rápido", externalHref: "https://web.whatsapp.com/" },
    ],
  },
  tecnico: {
    title: "Olá, Técnico Tecponto!",
    subtitle: "Gerencie sua fila técnica e registre diagnósticos com segurança.",
    tableTitle: "Fila técnica",
    nav: [
      {
        label: "Atendimento técnico",
        items: [
          { id: "overview", icon: Grid2X2, label: "Visão geral", subtitle: "Sua operação técnica" },
          { id: "service-orders", icon: ClipboardList, label: "Minhas OS", subtitle: "Ordens atribuídas" },
			{ id: "repair-parts", icon: PackageSearch, label: "Peças solicitadas", subtitle: "Estoque de Reparo" },
        ],
      },
      {
        label: "Histórico técnico",
        items: [
          { id: "devices", icon: Smartphone, label: "Aparelhos dos clientes", subtitle: "Histórico dos aparelhos" },
          { id: "customers", icon: BarChart3, label: "Histórico técnico", subtitle: "Serviços e intervenções" },
          { id: "services", icon: Wrench, label: "Serviços", subtitle: "Consultar catálogo" },
        ],
      },
    ],
    metrics: [
      { icon: ClipboardList, label: "Minhas OS", tone: "orange", value: (metrics) => metrics.service_orders.total, detail: "Atribuídas a você" },
      { icon: PackageSearch, label: "Aguardando peça", tone: "purple", value: (metrics) => metrics.service_orders.waiting_part, detail: "Solicitações abertas" },
    ],
    actions: [
      { icon: Wrench, label: "Atualizar diagnóstico", detail: "Registrar avaliação", target: "service-orders" },
      { icon: PackageSearch, label: "Solicitar peça", detail: "Estoque Reparo", target: "parts-stock" },
      { icon: ClipboardCheck, label: "Finalizar reparo", detail: "Enviar para teste", target: "service-orders" },
    ],
  },
  gestor: {
    title: "Olá, Gestor Tecponto!",
    subtitle: "Acompanhe a operação da loja e as aprovações do dia.",
    tableTitle: "Operação da loja",
    nav: [
      {
        label: "Operação",
        items: [
          { id: "overview", icon: Grid2X2, label: "Visão geral", subtitle: "Painel do gestor" },
          { id: "service-orders", icon: Wrench, label: "Ordens de serviço", subtitle: "Acompanhar e controlar" },
          { id: "devices", icon: Smartphone, label: "Aparelhos dos clientes", subtitle: "Status e histórico" },
          { id: "trade-ins", icon: Handshake, label: "Trocas", subtitle: "Avaliações e propostas" },
          { id: "customers", icon: Users, label: "Clientes", subtitle: "Base e relacionamento" },
          { id: "services", icon: Wrench, label: "Serviços", subtitle: "Catálogo e preços base" },
          { id: "parts-stock", icon: Boxes, label: "Peças e estoque", subtitle: "Inventário e alertas" },
          { id: "sales", icon: CreditCard, label: "Financeiro", subtitle: "Receitas e vendas" },
        ],
      },
    ],
    metrics: [
      { icon: ShoppingCart, label: "Vendas do dia", tone: "green", value: (metrics) => brl.format(metrics.sales_today_total), detail: "Comercial" },
      { icon: Wrench, label: "OS em andamento", tone: "orange", value: (metrics) => metrics.service_orders.total, detail: "Na operação" },
      { icon: Bell, label: "OS atrasadas", tone: "red", value: (metrics) => metrics.service_orders.overdue, detail: "Ver críticas" },
    ],
    actions: [
      ...commonActions,
      { icon: ClipboardCheck, label: "Aprovar orçamento", detail: "Pendências", target: "service-orders" },
      { icon: Gauge, label: "Ver desempenho", detail: "Equipe e loja", target: "sales" },
    ],
  },
  diretor: {
    title: "Olá, Diretor!",
    subtitle: "Aqui está o desempenho consolidado da operação.",
    tableTitle: "Principais movimentos",
    nav: [
      {
        label: "Gestão",
        items: [
          { id: "overview", icon: Grid2X2, label: "Visão executiva", subtitle: "Panorama estratégico" },
          { id: "service-orders", icon: Wrench, label: "Ordens de serviço", subtitle: "Fila e conclusão" },
          { id: "devices", icon: Smartphone, label: "Aparelhos", subtitle: "Base e histórico" },
          { id: "trade-ins", icon: Handshake, label: "Trocas", subtitle: "Avaliações e ofertas" },
          { id: "customers", icon: Users, label: "Clientes", subtitle: "Relacionamento" },
          { id: "services", icon: Wrench, label: "Serviços", subtitle: "Catálogo e preços base" },
          { id: "parts-stock", icon: Boxes, label: "Peças e estoque", subtitle: "Produtos e insumos" },
          { id: "sales", icon: CreditCard, label: "Financeiro", subtitle: "Receitas e fluxo" },
        ],
      },
    ],
    metrics: [
      { icon: ShoppingCart, label: "Vendas de acessórios", tone: "orange", value: (metrics) => brl.format(metrics.sales_today_total), detail: "Comercial" },
      { icon: Wrench, label: "OS concluídas", tone: "blue", value: (metrics) => metrics.service_orders.total, detail: "Período atual" },
    ],
    actions: [
      {
        icon: ShoppingCart,
        label: "Lançar venda",
        detail: "Venda no balcão",
        target: "pos",
      },
      { icon: Wrench, label: "Abrir OS", detail: "Atendimento", target: "service-orders" },
      { icon: BarChart3, label: "Ver relatório", detail: "Indicadores", target: "sales" },
      { icon: Target, label: "Acompanhar metas", detail: "Resultados", target: "overview" },
    ],
  },
  sem_papel: {
    title: "Acesso Tecponto",
    subtitle: "Seu usuário ainda não tem um papel operacional Tecponto.",
    tableTitle: "Atendimentos recentes",
    nav: [
      {
        label: "Início",
        items: [{ id: "overview", icon: Grid2X2, label: "Visão geral", subtitle: "Aguardando liberação" }],
      },
    ],
    metrics: [
      { icon: Zap, label: "Acesso", tone: "amber", value: () => "Pendente", detail: "Solicite ao gestor" },
    ],
    actions: [],
  },
};

const panelOrder: RolePanel[] = ["atendente", "tecnico", "gestor", "diretor"];

const panelLabels: Record<RolePanel, string> = {
  atendente: "Atendente",
  tecnico: "Tecnico",
  gestor: "Gestor",
  diretor: "Diretor",
  sem_papel: "Sem papel",
};

const pillarForTarget: Partial<Record<NavigationTarget, string>> = {
  overview: "Inicio",
  "service-orders": "Reparo",
  "repair-parts": "Reparo",
  "parts-stock": "Reparo",
  pos: "Venda",
  sales: "Venda",
  "commercial-products": "Venda",
  "trade-ins": "Troca",
  "used-devices": "Troca",
  customers: "Cadastros",
  devices: "Cadastros",
  services: "Cadastros",
};

function unifiedNavigation(panels: RolePanel[]): NavSection[] {
  const sections = new Map<string, NavSection>();
  const seenTargets = new Set<NavigationTarget>();

  for (const panelName of panels) {
    for (const sourceSection of panelDefinitions[panelName].nav) {
      for (const item of sourceSection.items) {
        if (seenTargets.has(item.id)) continue;
        seenTargets.add(item.id);
        const label = pillarForTarget[item.id] ?? sourceSection.label;
        const section = sections.get(label) ?? { label, items: [] };
        section.items.push(item);
        sections.set(label, section);
      }
    }
  }

  const preferredOrder = ["Inicio", "Reparo", "Venda", "Troca", "Cadastros"];
  return [...sections.values()].sort((left, right) => {
    const leftIndex = preferredOrder.indexOf(left.label);
    const rightIndex = preferredOrder.indexOf(right.label);
    return (leftIndex < 0 ? preferredOrder.length : leftIndex) - (rightIndex < 0 ? preferredOrder.length : rightIndex);
  });
}

function uniqueByLabel<T extends { label: string }>(items: T[]): T[] {
  const labels = new Set<string>();
  return items.filter((item) => {
    if (labels.has(item.label)) return false;
    labels.add(item.label);
    return true;
  });
}

/** Display-only union: authorization remains entirely server-side. */
export function getUnifiedPanelDefinition(panels: RolePanel[], fullName: string): PanelDefinition {
  const resolvedPanels = panelOrder.filter((panel) => panels.includes(panel));
  if (resolvedPanels.length === 1) return panelDefinitions[resolvedPanels[0]];
  if (!resolvedPanels.length) return panelDefinitions.sem_papel;

  const definitions = resolvedPanels.map((panel) => panelDefinitions[panel]);
  const labels = resolvedPanels.map((panel) => panelLabels[panel]);
  const firstName = fullName.trim().split(/\s+/)[0] || "Tecponto";

  return {
    title: `Ola, ${firstName}!`,
    subtitle: `Visao unificada: ${labels.join(" + ")}.`,
    tableTitle: "Operacao unificada",
    nav: unifiedNavigation(resolvedPanels),
    metrics: uniqueByLabel(definitions.flatMap((definition) => definition.metrics)),
    actions: uniqueByLabel(definitions.flatMap((definition) => definition.actions)),
  };
}
