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

import type { RolePanel } from "./api";
import type { NavSection } from "./ui";

export interface MetricDefinition {
  icon: LucideIcon;
  label: string;
  tone: "orange" | "green" | "blue" | "purple" | "amber" | "red";
  value: (count: number) => string | number;
  detail: string;
}

export interface ActionDefinition {
  icon: LucideIcon;
  label: string;
  detail: string;
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
  { icon: ShoppingCart, label: "Lançar venda", detail: "Balcão" },
  { icon: Wrench, label: "Nova OS", detail: "Atendimento" },
  { icon: Search, label: "Buscar cliente", detail: "Nome, telefone ou IMEI" },
];

export const panelDefinitions: Record<RolePanel, PanelDefinition> = {
  atendente: {
    title: "Olá, Atendente Tecponto!",
    subtitle: "Confira os atendimentos e vendas que precisam da sua atenção.",
    tableTitle: "Atendimentos recentes",
    nav: [
      {
        label: "Início",
        items: [{ icon: Grid2X2, label: "Visão geral", subtitle: "O que precisa de você", active: true }],
      },
      {
        label: "Atendimentos",
        items: [
          { icon: Wrench, label: "Ordens de serviço", subtitle: "Consertos e garantias" },
          { icon: Smartphone, label: "Aparelhos e clientes", subtitle: "Cadastro e histórico" },
          { icon: Handshake, label: "Avaliações de troca", subtitle: "Usados e ofertas" },
        ],
      },
      {
        label: "Vendas e estoque",
        items: [
          { icon: Boxes, label: "Peças e estoque", subtitle: "Itens disponíveis" },
          { icon: ShoppingCart, label: "Vendas e acessórios", subtitle: "Vendas e entregas" },
        ],
      },
    ],
    metrics: [
      { icon: ShoppingCart, label: "Vendas do dia", tone: "green", value: () => "R$ 0,00", detail: "PDV Tecponto" },
      { icon: Wrench, label: "OS aguardando aprovação", tone: "orange", value: (count) => count, detail: "Orçamentos na fila" },
      { icon: ClipboardCheck, label: "Prontas para retirada", tone: "green", value: (count) => count, detail: "Entrega no balcão" },
      { icon: PackageSearch, label: "Aguardando peça", tone: "blue", value: (count) => count, detail: "Reparo pendente" },
    ],
    actions: [
      ...commonActions,
      { icon: Smartphone, label: "Cadastrar aparelho", detail: "Vincular ao cliente" },
      { icon: Handshake, label: "Avaliar troca", detail: "TROQUE" },
      { icon: MessageCircle, label: "Enviar WhatsApp", detail: "Contato rápido" },
    ],
  },
  tecnico: {
    title: "Olá, Técnico Tecponto!",
    subtitle: "Gerencie sua fila técnica e registre diagnósticos sem ver custo.",
    tableTitle: "Fila técnica",
    nav: [
      {
        label: "Atendimento técnico",
        items: [
          { icon: Grid2X2, label: "Visão geral", subtitle: "Sua operação técnica", active: true },
          { icon: ClipboardList, label: "Minhas OS", subtitle: "Ordens atribuídas" },
          { icon: PackageSearch, label: "Peças solicitadas", subtitle: "Solicitações e cotações" },
        ],
      },
      {
        label: "Histórico técnico",
        items: [
          { icon: Smartphone, label: "Aparelhos dos clientes", subtitle: "Histórico dos aparelhos" },
          { icon: BarChart3, label: "Histórico técnico", subtitle: "Serviços e intervenções" },
        ],
      },
    ],
    metrics: [
      { icon: ClipboardList, label: "Minhas OS", tone: "orange", value: (count) => count, detail: "Atribuídas a você" },
      { icon: PackageSearch, label: "Aguardando peça", tone: "purple", value: (count) => count, detail: "Solicitações abertas" },
      { icon: Wrench, label: "Diagnósticos hoje", tone: "blue", value: () => 0, detail: "Registrados" },
      { icon: ClipboardCheck, label: "Prontas para teste", tone: "green", value: () => 0, detail: "Em bancada" },
    ],
    actions: [
      { icon: Wrench, label: "Atualizar diagnóstico", detail: "Registrar avaliação" },
      { icon: PackageSearch, label: "Solicitar peça", detail: "Estoque Reparo" },
      { icon: ClipboardCheck, label: "Finalizar reparo", detail: "Enviar para teste" },
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
          { icon: Grid2X2, label: "Visão geral", subtitle: "Painel do gestor", active: true },
          { icon: Wrench, label: "Ordens de serviço", subtitle: "Acompanhar e controlar" },
          { icon: ShoppingCart, label: "Vendas e acessórios", subtitle: "Vendas e performance" },
          { icon: Users, label: "Equipe", subtitle: "Técnicos e atendentes" },
        ],
      },
      {
        label: "Relacionamento",
        items: [
          { icon: Smartphone, label: "Aparelhos dos clientes", subtitle: "Status e histórico" },
          { icon: BarChart3, label: "Relatórios", subtitle: "Indicadores e BI" },
        ],
      },
    ],
    metrics: [
      { icon: ShoppingCart, label: "Vendas do dia", tone: "green", value: () => "R$ 0,00", detail: "Comercial" },
      { icon: Wrench, label: "OS em andamento", tone: "orange", value: (count) => count, detail: "Na operação" },
      { icon: Bell, label: "OS atrasadas", tone: "red", value: () => 0, detail: "Ver críticas" },
      { icon: Target, label: "Meta do dia", tone: "blue", value: () => "R$ 0,00", detail: "Acompanhamento" },
    ],
    actions: [
      ...commonActions,
      { icon: ClipboardCheck, label: "Aprovar orçamento", detail: "Pendências" },
      { icon: Gauge, label: "Ver desempenho", detail: "Equipe e loja" },
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
          { icon: Grid2X2, label: "Visão executiva", subtitle: "Panorama estratégico", active: true },
          { icon: Target, label: "Vendas e acessórios", subtitle: "PDV e receita" },
          { icon: Wrench, label: "Ordens de serviço", subtitle: "Fila e conclusão" },
          { icon: CreditCard, label: "Financeiro", subtitle: "Receitas e fluxo" },
          { icon: BarChart3, label: "Relatórios", subtitle: "Indicadores" },
        ],
      },
    ],
    metrics: [
      { icon: CreditCard, label: "Faturamento do mês", tone: "green", value: () => "R$ 0,00", detail: "Consolidado" },
      { icon: ShoppingCart, label: "Vendas de acessórios", tone: "orange", value: () => "R$ 0,00", detail: "Comercial" },
      { icon: Wrench, label: "OS concluídas", tone: "blue", value: (count) => count, detail: "Período atual" },
      { icon: Star, label: "Satisfação", tone: "green", value: () => "0,0/5", detail: "Clientes" },
    ],
    actions: [
      { icon: ShoppingCart, label: "Lançar venda", detail: "PDV" },
      { icon: Wrench, label: "Abrir OS", detail: "Atendimento" },
      { icon: BarChart3, label: "Ver relatório", detail: "Indicadores" },
      { icon: Target, label: "Acompanhar metas", detail: "Resultados" },
    ],
  },
  sem_papel: {
    title: "Acesso Tecponto",
    subtitle: "Seu usuário ainda não tem um papel operacional Tecponto.",
    tableTitle: "Atendimentos recentes",
    nav: [
      {
        label: "Início",
        items: [{ icon: Grid2X2, label: "Visão geral", subtitle: "Aguardando liberação", active: true }],
      },
    ],
    metrics: [
      { icon: Zap, label: "Acesso", tone: "amber", value: () => "Pendente", detail: "Solicite ao gestor" },
    ],
    actions: [],
  },
};
