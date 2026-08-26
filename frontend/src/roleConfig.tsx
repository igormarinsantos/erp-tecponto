import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  BarChart3,
  BadgeDollarSign,
  Bell,
  Boxes,
  ClipboardCheck,
  ClipboardList,
  CreditCard,
  FileText,
  Gauge,
  Grid2X2,
  Handshake,
  Link2,
  MessageCircle,
  PackageSearch,
  Search,
  SearchCheck,
  ShoppingCart,
  Smartphone,
  Star,
  Target,
  Users,
	WalletCards,
  Wrench,
  Zap,
} from "lucide-react";

import type { DashboardMetrics, NavigationTarget, RolePanel } from "./api";
import type { NavItem, NavSection } from "./ui";

export interface MetricDefinition {
  icon: LucideIcon;
  label: string;
  tone: "orange" | "green" | "blue" | "purple" | "amber" | "red";
  value: (metrics: DashboardMetrics) => string | number;
  detail: string;
	pillar?: OperationPillar;
}

type OperationPillar = "repair" | "buy" | "tradein";

export interface OperationPillars {
	repair: boolean;
	buy: boolean;
	tradein: boolean;
}

export interface ActionDefinition {
  disabledReason?: string;
  icon: LucideIcon;
  label: string;
  detail: string;
  externalHref?: string;
  opensCheckin?: boolean;
  pendingLabel?: string;
	pillar?: OperationPillar;
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
		pillar: "buy",
    target: "pos",
  },
  { icon: Wrench, label: "Nova OS", detail: "Atendimento", opensCheckin: true, pillar: "repair" },
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
          { id: "repair-parts", icon: PackageSearch, label: "Peças", subtitle: "Estoque e solicitações", children: [
            { id: "repair-parts", icon: Boxes, label: "Estoque de reparo", subtitle: "Disponibilidade" },
          ] },
        ],
      },
      {
        label: "Venda",
        items: [
          { id: "pos", icon: ShoppingCart, label: "PDV / Lançar venda", subtitle: "Venda rápida no balcão" },
          { id: "cash-statement", icon: WalletCards, label: "Caixa", subtitle: "Extrato e fechamento" },
          { id: "sales", icon: CreditCard, label: "Vendas", subtitle: "Histórico do balcão" },
          { id: "commercial-products", icon: Boxes, label: "Produtos", subtitle: "Catálogo e variações", children: [
            { id: "commercial-products", icon: Boxes, label: "Catálogo", subtitle: "Estoque comercial" },
            { id: "product-categories", icon: Grid2X2, label: "Categorias", subtitle: "Hierarquia comercial" },
            { id: "product-attributes", icon: ClipboardList, label: "Atributos e variações", subtitle: "SKU e combinações" },
          ] },
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
          { id: "services", icon: Wrench, label: "Serviços", subtitle: "Catálogo e regras", children: [
            { id: "services", icon: Wrench, label: "Catálogo de serviços", subtitle: "Mão de obra" },
            { id: "service-categories", icon: Grid2X2, label: "Categorias de serviço", subtitle: "Organização do catálogo" },
            { id: "defect-service-mapping", icon: Link2, label: "Mapeamento defeito→serviço", subtitle: "Sugestões no check-in" },
          ] },
        ],
      },
    ],
    metrics: [
      { icon: ShoppingCart, label: "Vendas do dia", tone: "green", value: (metrics) => brl.format(metrics.sales_today_total), detail: "PDV Tecponto", pillar: "buy" },
      { icon: FileText, label: "OS aguardando aprovação", tone: "orange", value: (metrics) => metrics.service_orders.awaiting_approval, detail: "Orçamentos na fila", pillar: "repair" },
      { icon: ClipboardCheck, label: "Prontas para retirada", tone: "green", value: (metrics) => metrics.service_orders.ready_for_pickup, detail: "Entrega no balcão", pillar: "repair" },
      { icon: PackageSearch, label: "Aguardando peça", tone: "blue", value: (metrics) => metrics.service_orders.waiting_part, detail: "Reparo pendente", pillar: "repair" },
    ],
    actions: [
      ...commonActions,
      { icon: Smartphone, label: "Cadastrar aparelho", detail: "Vincular ao cliente", target: "devices" },
      { icon: Handshake, label: "Avaliar troca", detail: "TROQUE", pillar: "tradein", target: "trade-ins" },
      { icon: MessageCircle, label: "Enviar WhatsApp", detail: "Contato rápido", externalHref: "https://web.whatsapp.com/" },
    ],
  },
  tecnico: {
    title: "Olá, Técnico Tecponto!",
    subtitle: "Sua bancada: diagnósticos, reparos e peças das OS atribuídas a você.",
    tableTitle: "Fila técnica",
    nav: [
      {
        label: "Início",
        items: [
          { id: "overview", icon: Grid2X2, label: "Visão geral", subtitle: "Sua operação técnica" },
        ],
      },
      {
        label: "Reparo",
        items: [
          { id: "service-orders", icon: ClipboardList, label: "Minhas OS", subtitle: "Ordens atribuídas" },
          { id: "my-earnings", icon: BadgeDollarSign, label: "Minhas comissões", subtitle: "Lançamentos da sua mão de obra" },
          { id: "repair-parts", icon: PackageSearch, label: "Peças", subtitle: "Estoque e solicitações", children: [
            { id: "repair-parts", icon: Boxes, label: "Estoque de Reparo", subtitle: "Disponibilidade" },
            { id: "part-requests", icon: ClipboardList, label: "Solicitações de peça", subtitle: "Pedidos da sua bancada" },
          ] },
        ],
      },
      {
        label: "Cadastros",
        items: [
          { id: "devices", icon: Smartphone, label: "Aparelhos atendidos", subtitle: "Somente da sua carteira" },
          { id: "services", icon: Wrench, label: "Serviços", subtitle: "Consultar catálogo" },
        ],
      },
    ],
    metrics: [
      { icon: ClipboardList, label: "Minhas OS", tone: "orange", value: (metrics) => metrics.service_orders.total, detail: "Atribuídas a você" },
      { icon: SearchCheck, label: "Em diagnóstico", tone: "blue", value: (metrics) => metrics.service_orders.in_diagnosis, detail: "Na bancada" },
      { icon: PackageSearch, label: "Aguardando peça", tone: "purple", value: (metrics) => metrics.service_orders.waiting_part, detail: "Solicitações abertas" },
      { icon: ClipboardCheck, label: "Prontas para teste", tone: "green", value: (metrics) => metrics.service_orders.ready_for_test, detail: "Validação final" },
      { icon: AlertTriangle, label: "Atrasadas", tone: "red", value: (metrics) => metrics.service_orders.overdue, detail: "Pedem atenção" },
    ],
    actions: [
      { icon: ClipboardList, label: "Minhas OS", detail: "Fila da bancada", target: "service-orders" },
      { icon: Wrench, label: "Atualizar diagnóstico", detail: "Registrar avaliação", target: "service-orders" },
      { icon: PackageSearch, label: "Peças de reparo", detail: "Consultar disponibilidade", target: "repair-parts" },
      { icon: ClipboardCheck, label: "Finalizar reparo", detail: "Enviar para teste", target: "service-orders" },
    ],
  },
  gestor: {
    title: "Olá, Gestor Tecponto!",
    subtitle: "Acompanhe a operação da loja e as aprovações do dia.",
    tableTitle: "Operação da loja",
    nav: [
      {
        label: "Início",
        items: [
          { id: "overview", icon: Grid2X2, label: "Visão geral", subtitle: "Painel do gestor" },
        ],
      },
      {
        label: "Reparo",
        items: [
          { id: "service-orders", icon: Wrench, label: "Ordens de serviço", subtitle: "Acompanhar e controlar" },
          { id: "repair-parts", icon: Boxes, label: "Peças", subtitle: "Estoque e compras", children: [
            { id: "repair-parts", icon: Boxes, label: "Estoque de Reparo", subtitle: "Disponibilidade" },
            { id: "part-requests", icon: ClipboardList, label: "Solicitações de peça", subtitle: "Fila de compras" },
          ] },
        ],
      },
      {
        label: "Venda",
        items: [
          { id: "pos", icon: ShoppingCart, label: "PDV / Lançar venda", subtitle: "Venda rápida no balcão" },
          { id: "cash-statement", icon: WalletCards, label: "Caixa", subtitle: "Extrato e fechamento" },
          { id: "sales", icon: CreditCard, label: "Vendas", subtitle: "Volume e faturamento" },
          { id: "commercial-products", icon: ShoppingCart, label: "Produtos", subtitle: "Prateleira comercial", children: [
            { id: "commercial-products", icon: Boxes, label: "Catálogo", subtitle: "Estoque comercial" },
            { id: "product-categories", icon: Grid2X2, label: "Categorias", subtitle: "Hierarquia comercial" },
            { id: "product-attributes", icon: ClipboardList, label: "Atributos e variações", subtitle: "SKU e combinações" },
          ] },
        ],
      },
      {
        label: "Troca",
        items: [
          { id: "trade-ins", icon: Handshake, label: "Trocas", subtitle: "Avaliações e propostas" },
          { id: "used-devices", icon: Smartphone, label: "Aparelhos usados", subtitle: "Itens únicos de trade-in" },
        ],
      },
      {
        label: "Cadastros",
        items: [
          { id: "customers", icon: Users, label: "Clientes", subtitle: "Base e relacionamento" },
          { id: "devices", icon: Smartphone, label: "Aparelhos dos clientes", subtitle: "Cadastro e histórico" },
          { id: "services", icon: Wrench, label: "Serviços", subtitle: "Catálogo e regras", children: [
            { id: "services", icon: Wrench, label: "Catálogo de serviços", subtitle: "Mão de obra" },
            { id: "service-categories", icon: Grid2X2, label: "Categorias de serviço", subtitle: "Organização do catálogo" },
            { id: "defect-service-mapping", icon: Link2, label: "Mapeamento defeito→serviço", subtitle: "Sugestões no check-in" },
          ] },
        ],
      },
    ],
    metrics: [
      { icon: ShoppingCart, label: "Vendas do dia", tone: "green", value: (metrics) => brl.format(metrics.sales_today_total), detail: "Comercial" },
      { icon: Wrench, label: "OS em andamento", tone: "orange", value: (metrics) => metrics.service_orders.total, detail: "Na operação" },
      { icon: Bell, label: "OS atrasadas", tone: "red", value: (metrics) => metrics.service_orders.overdue, detail: "Ver críticas" },
    ],
    actions: [
      { icon: ClipboardCheck, label: "Aprovações", detail: "Decisões pendentes", target: "approval-requests" },
      { icon: Wrench, label: "Ordens de serviço", detail: "Operação da loja", target: "service-orders" },
      { icon: ClipboardList, label: "Compras de peças", detail: "Fila por urgência", target: "part-requests" },
      { icon: ShoppingCart, label: "Vendas", detail: "Volume do dia", target: "sales" },
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
			{ id: "repair-parts", icon: Boxes, label: "Estoque de Reparo", subtitle: "Disponibilidade de peças" },
			{ id: "commercial-products", icon: ShoppingCart, label: "Produtos", subtitle: "Prateleira comercial" },
			{ id: "used-devices", icon: Smartphone, label: "Aparelhos usados", subtitle: "Itens únicos de trade-in" },
          { id: "product-categories", icon: Grid2X2, label: "Categorias", subtitle: "Estrutura comercial" },
          { id: "sales", icon: CreditCard, label: "Financeiro", subtitle: "Receitas e fluxo" },
          { id: "cash-statement", icon: WalletCards, label: "Caixa", subtitle: "Extrato e fechamento" },
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
  overview: "Início",
  "service-orders": "Reparo",
  "repair-parts": "Reparo",
  "part-requests": "Reparo",
  "my-earnings": "Reparo",
  "parts-stock": "Reparo",
  pos: "Venda",
  "cash-statement": "Venda",
  sales: "Venda",
  "commercial-products": "Venda",
  "product-attributes": "Venda",
  "product-categories": "Venda",
  "service-categories": "Cadastros",
  "trade-ins": "Troca",
  "used-devices": "Troca",
  customers: "Cadastros",
  devices: "Cadastros",
  services: "Cadastros",
  "defect-service-mapping": "Cadastros",
};

function withSubmenus(nav: NavSection[]): NavSection[] {
  const byPillar = new Map<string, NavItem[]>();
  for (const section of nav) {
    for (const item of section.items.flatMap((source) => source.children?.length ? source.children : [source])) {
      const pillar = pillarForTarget[item.id] ?? section.label;
      byPillar.set(pillar, [...(byPillar.get(pillar) ?? []), item]);
    }
  }
  const preferredOrder = ["Início", "Reparo", "Venda", "Troca", "Cadastros"];
  return [...byPillar.entries()]
    .sort(([left], [right]) => (preferredOrder.indexOf(left) + preferredOrder.length + 1) % (preferredOrder.length + 1) - (preferredOrder.indexOf(right) + preferredOrder.length + 1) % (preferredOrder.length + 1))
    .map(([label, flatItems]) => {
    const consumed = new Set<NavigationTarget>();
    const grouped: NavItem[] = [];
    const take = (targets: NavigationTarget[]) => flatItems.filter((item) => targets.includes(item.id));
    const addGroup = (target: NavigationTarget, icon: LucideIcon, label: string, subtitle: string, targets: NavigationTarget[], extras: NavItem[] = []) => {
      const sourceChildren = take(targets);
      if (!sourceChildren.length) return;
      const children = [...sourceChildren, ...extras.filter((item) => !flatItems.some((source) => source.id === item.id && source.label === item.label))];
      targets.forEach((item) => consumed.add(item));
      grouped.push({ id: target, icon, label, subtitle, children });
    };
    for (const item of flatItems) {
      if (consumed.has(item.id)) continue;
      if (item.id === "repair-parts") {
        addGroup("repair-parts", PackageSearch, "Peças", "Estoque de reparo", ["repair-parts", "part-requests"]);
        continue;
      }
      if (item.id === "parts-stock") {
        addGroup("parts-stock", Boxes, "PeÃ§as", "Estoque e compras", ["parts-stock", "part-requests"], [
          { id: "part-requests", icon: ClipboardList, label: "SolicitaÃ§Ãµes de peÃ§a", subtitle: "Lista de compras" },
        ]);
        continue;
      }
      if (["commercial-products", "product-categories", "product-attributes"].includes(item.id)) {
        addGroup("commercial-products", Boxes, "Produtos", "Catálogo e variações", ["commercial-products", "product-categories", "product-attributes"], [
          { id: "product-attributes", icon: ClipboardList, label: "Atributos e variações", subtitle: "SKU e combinações" },
        ]);
        continue;
      }
      if (item.id === "services") {
        (["services", "service-categories", "defect-service-mapping"] as NavigationTarget[]).forEach((target) => consumed.add(target));
        const serviceChildren: NavItem[] = [
          { id: "services", icon: Wrench, label: "Catálogo de serviços", subtitle: "Mão de obra" },
        ];
        if (flatItems.some((source) => source.id === "service-categories")) {
          serviceChildren.push({ id: "service-categories", icon: Grid2X2, label: "Categorias de serviço", subtitle: "Organização do catálogo" });
        }
        if (flatItems.some((source) => source.id === "defect-service-mapping")) {
          serviceChildren.push({ id: "defect-service-mapping", icon: Link2, label: "Mapeamento defeito→serviço", subtitle: "Sugestões no check-in" });
        }
        grouped.push({ id: "services", icon: Wrench, label: "Serviços", subtitle: "Catálogo e regras", children: [
          ...serviceChildren,
        ] });
        continue;
      }
      grouped.push(item);
    }
    return { label, items: grouped };
  });
}

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

  const preferredOrder = ["Início", "Reparo", "Venda", "Troca", "Cadastros"];
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
export function getUnifiedPanelDefinition(
	panels: RolePanel[],
	fullName: string,
	brandName = "Empresa",
	commissionsEnabled = true,
	pillars: OperationPillars = { repair: true, buy: true, tradein: true },
): PanelDefinition {
	const resolvedPanels = panelOrder.filter((panel) => panels.includes(panel));
	if (resolvedPanels.length === 1) return withCommercialIdentity(withOperationPillars(withLeanOperationNavigation({ ...panelDefinitions[resolvedPanels[0]], nav: withSubmenus(panelDefinitions[resolvedPanels[0]].nav) }, commissionsEnabled), pillars), brandName);
	if (!resolvedPanels.length) return withCommercialIdentity(panelDefinitions.sem_papel, brandName);

  const definitions = resolvedPanels.map((panel) => panelDefinitions[panel]);
  const labels = resolvedPanels.map((panel) => panelLabels[panel]);
	const firstName = fullName.trim().split(/\s+/)[0] || brandName;

	return withCommercialIdentity(withOperationPillars(withLeanOperationNavigation({
    title: `Ola, ${firstName}!`,
    subtitle: `Visao unificada: ${labels.join(" + ")}.`,
    tableTitle: "Operacao unificada",
    nav: withSubmenus(unifiedNavigation(resolvedPanels)),
    metrics: uniqueByLabel(definitions.flatMap((definition) => definition.metrics)),
    actions: uniqueByLabel(definitions.flatMap((definition) => definition.actions)),
	}, commissionsEnabled), pillars), brandName);
}

function withLeanOperationNavigation(definition: PanelDefinition, commissionsEnabled: boolean): PanelDefinition {
	if (commissionsEnabled) return definition;
	return {
		...definition,
		nav: definition.nav.map((section) => ({
			...section,
			items: section.items.filter((item) => item.id !== "my-earnings"),
		})),
	};
}

function withOperationPillars(definition: PanelDefinition, pillars: OperationPillars): PanelDefinition {
	const isEnabled = (pillar: OperationPillar | undefined) => !pillar || pillars[pillar];
	const targetPillar = (target?: NavigationTarget): OperationPillar | undefined => {
		const section = target ? pillarForTarget[target] : undefined;
		if (section === "Reparo") return "repair";
		if (section === "Venda") return "buy";
		if (section === "Troca") return "tradein";
		return undefined;
	};
	const filterItems = (items: NavItem[]): NavItem[] => items.flatMap((item) => {
		const children = item.children ? filterItems(item.children) : undefined;
		if (!isEnabled(targetPillar(item.id))) return [];
		if (item.children && !children?.length) return [];
		return [{ ...item, ...(children ? { children } : {}) }];
	});
	const metricPillar = (metric: MetricDefinition): OperationPillar | undefined => {
		if (metric.pillar) return metric.pillar;
		if (/^Vendas/.test(metric.label)) return "buy";
		if (/OS|diagnóstico|peça|teste|atrasada/i.test(metric.label)) return "repair";
		return undefined;
	};

	return {
		...definition,
		nav: definition.nav.map((section) => ({ ...section, items: filterItems(section.items) })).filter((section) => section.items.length > 0),
		metrics: definition.metrics.filter((metric) => isEnabled(metricPillar(metric))),
		actions: definition.actions.filter((action) => isEnabled(action.pillar ?? targetPillar(action.target))),
	};
}

function withCommercialIdentity(definition: PanelDefinition, brandName: string): PanelDefinition {
	const replace = (value: string) => value.replace(/Tecponto/g, brandName);
	const mapItem = (item: NavItem): NavItem => ({
		...item,
		label: replace(item.label),
		subtitle: replace(item.subtitle),
		children: item.children?.map(mapItem),
	});
	return {
		...definition,
		title: replace(definition.title),
		subtitle: replace(definition.subtitle),
		tableTitle: replace(definition.tableTitle),
		nav: definition.nav.map((section) => ({ ...section, label: replace(section.label), items: section.items.map(mapItem) })),
		metrics: definition.metrics.map((metric) => ({ ...metric, label: replace(metric.label), detail: replace(metric.detail) })),
		actions: definition.actions.map((action) => ({ ...action, label: replace(action.label), detail: replace(action.detail) })),
	};
}
