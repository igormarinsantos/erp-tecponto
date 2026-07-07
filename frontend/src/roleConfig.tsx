import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Bell,
  Boxes,
  ClipboardCheck,
  ClipboardList,
  CreditCard,
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
  icon: LucideIcon;
  label: string;
  detail: string;
  target?: NavigationTarget;
  soon?: string;
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
  { icon: ShoppingCart, label: "Lançar venda", detail: "Balcão", soon: "bloco 3.1x" },
  { icon: Wrench, label: "Nova OS", detail: "Atendimento", soon: "bloco 3.1c" },
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
    tableTitle: "Atendimentos recentes",
    nav: [
      {
        label: "Início",
        items: [{ id: "overview", icon: Grid2X2, label: "Visão geral", subtitle: "O que precisa de você" }],
      },
      {
        label: "Menu principal",
        items: [
          { id: "service-orders", icon: Wrench, label: "Ordens de serviço", subtitle: "Criar, buscar e acompanhar" },
          { id: "customers", icon: Users, label: "Clientes", subtitle: "Base e histórico" },
          { id: "devices", icon: Smartphone, label: "Aparelhos", subtitle: "Aparelhos e acessórios" },
          { id: "trade-ins", icon: Handshake, label: "Trocas", subtitle: "Avaliações e propostas" },
          { id: "parts-stock", icon: Boxes, label: "Peças e estoque", subtitle: "Consulta de disponibilidade" },
        ],
      },
    ],
    metrics: [
      { icon: ShoppingCart, label: "Vendas do dia", tone: "green", value: (metrics) => brl.format(metrics.sales_today_total), detail: "PDV Tecponto" },
      { icon: Wrench, label: "OS aguardando aprovação", tone: "orange", value: (metrics) => metrics.service_orders.awaiting_approval, detail: "Orçamentos na fila" },
      { icon: ClipboardCheck, label: "Prontas para retirada", tone: "green", value: (metrics) => metrics.service_orders.ready_for_pickup, detail: "Entrega no balcão" },
      { icon: PackageSearch, label: "Aguardando peça", tone: "blue", value: (metrics) => metrics.service_orders.waiting_part, detail: "Reparo pendente" },
    ],
    actions: [
      ...commonActions,
      { icon: Smartphone, label: "Cadastrar aparelho", detail: "Vincular ao cliente", soon: "bloco 3.1c" },
      { icon: Handshake, label: "Avaliar troca", detail: "TROQUE", soon: "bloco 3.1x" },
      { icon: MessageCircle, label: "Enviar WhatsApp", detail: "Contato rápido", soon: "bloco 3.1x" },
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
          { id: "parts-stock", icon: PackageSearch, label: "Peças solicitadas", subtitle: "Solicitações e cotações" },
        ],
      },
      {
        label: "Histórico técnico",
        items: [
          { id: "devices", icon: Smartphone, label: "Aparelhos dos clientes", subtitle: "Histórico dos aparelhos" },
          { id: "customers", icon: BarChart3, label: "Histórico técnico", subtitle: "Serviços e intervenções" },
        ],
      },
    ],
    metrics: [
      { icon: ClipboardList, label: "Minhas OS", tone: "orange", value: (metrics) => metrics.service_orders.total, detail: "Atribuídas a você" },
      { icon: PackageSearch, label: "Aguardando peça", tone: "purple", value: (metrics) => metrics.service_orders.waiting_part, detail: "Solicitações abertas" },
      { icon: Wrench, label: "Diagnósticos hoje", tone: "blue", value: () => 0, detail: "Registrados" },
      { icon: ClipboardCheck, label: "Prontas para teste", tone: "green", value: () => 0, detail: "Em bancada" },
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
          { id: "sales", icon: ShoppingCart, label: "Vendas e acessórios", subtitle: "Vendas e performance" },
          { id: "customers", icon: Users, label: "Equipe", subtitle: "Técnicos e atendentes" },
        ],
      },
      {
        label: "Relacionamento",
        items: [
          { id: "devices", icon: Smartphone, label: "Aparelhos dos clientes", subtitle: "Status e histórico" },
          { id: "parts-stock", icon: BarChart3, label: "Relatórios", subtitle: "Indicadores e BI" },
        ],
      },
    ],
    metrics: [
      { icon: ShoppingCart, label: "Vendas do dia", tone: "green", value: (metrics) => brl.format(metrics.sales_today_total), detail: "Comercial" },
      { icon: Wrench, label: "OS em andamento", tone: "orange", value: (metrics) => metrics.service_orders.total, detail: "Na operação" },
      { icon: Bell, label: "OS atrasadas", tone: "red", value: (metrics) => metrics.service_orders.overdue, detail: "Ver críticas" },
      { icon: Target, label: "Meta do dia", tone: "blue", value: () => "R$ 0,00", detail: "Acompanhamento" },
    ],
    actions: [
      ...commonActions,
      { icon: ClipboardCheck, label: "Aprovar orçamento", detail: "Pendências", target: "service-orders" },
      { icon: Gauge, label: "Ver desempenho", detail: "Equipe e loja", soon: "bloco 3.1x" },
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
          { id: "sales", icon: Target, label: "Vendas e acessórios", subtitle: "PDV e receita" },
          { id: "service-orders", icon: Wrench, label: "Ordens de serviço", subtitle: "Fila e conclusão" },
          { id: "parts-stock", icon: CreditCard, label: "Financeiro", subtitle: "Receitas e fluxo" },
          { id: "customers", icon: BarChart3, label: "Relatórios", subtitle: "Indicadores" },
        ],
      },
    ],
    metrics: [
      { icon: CreditCard, label: "Faturamento do mês", tone: "green", value: () => "R$ 0,00", detail: "Consolidado" },
      { icon: ShoppingCart, label: "Vendas de acessórios", tone: "orange", value: (metrics) => brl.format(metrics.sales_today_total), detail: "Comercial" },
      { icon: Wrench, label: "OS concluídas", tone: "blue", value: (metrics) => metrics.service_orders.total, detail: "Período atual" },
      { icon: Star, label: "Satisfação", tone: "green", value: () => "0,0/5", detail: "Clientes" },
    ],
    actions: [
      { icon: ShoppingCart, label: "Lançar venda", detail: "PDV", soon: "bloco 3.1x" },
      { icon: Wrench, label: "Abrir OS", detail: "Atendimento", soon: "bloco 3.1c" },
      { icon: BarChart3, label: "Ver relatório", detail: "Indicadores", soon: "bloco 3.1x" },
      { icon: Target, label: "Acompanhar metas", detail: "Resultados", soon: "bloco 3.1x" },
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
