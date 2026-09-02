import { FormEvent, type KeyboardEvent as ReactKeyboardEvent, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowRightLeft,
  BadgeInfo,
  Barcode,
  Box,
	Boxes,
  CalendarDays,
  CalendarClock,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  Copy,
	Edit3,
  CircleDollarSign,
  CreditCard,
  FileText,
  History,
  Hourglass,
  MoreHorizontal,
  Package,
	PackageCheck,
	PackagePlus,
  Plus,
  Printer,
  RefreshCw,
  Search as SearchIcon,
  Send,
  ShieldAlert,
  ShoppingCart,
  Smartphone,
  Tag,
  Ticket,
  Target,
	QrCode,
  UserRound,
  Users,
  Wrench,
  XCircle,
  Trash2,
} from "lucide-react";

import {
  balcao,
	 approvalRequests,
	 catalogListings,
  productCategories,
  dailyActions,
  getBoot,
  logout,
  notifications,
  pos,
  serviceCatalog,
  serviceOrders,
  type BudgetItemSummary,
	type AcceptanceIssueResponse,
  type BudgetLineType,
  type BudgetWarehouseSummary,
  type BootResponse,
  type CheckinResponse,
  type LoggedUser,
  type CreateCustomerPayload,
  type CustomerDeviceSummary,
  type CustomerSummary,
  type DashboardMetrics,
  type DirectorFinancialSummary,
	 type DirectorRiskAgenda,
  type DirectorStrategicReport,
  type TechnicianWorkloadItem,
  type AgendaCalendarEvent,
  type DailyActionsResponse,
  type NavigationTarget,
  type NotificationListResponse,
  type QuoteSendPayload,
  type RolePanel,
  type ServiceOrderBudgetLine,
  type ServiceOrderDetailResponse,
	 type ServiceOrderPaymentPayload,
	 type ServiceOrderTradeinCandidate,
  type ServiceOrderPrintLink,
  type ServiceOrderQueryParams,
  type ServiceOrderTimelineEvent,
  type ServiceOrderWorkflowAction,
  type ServiceCatalogService,
  type ServiceOrderSummary,
  type ServiceOrderStatBarResponse,
	type SaleSummary,
  type TrackingLinkResponse,
	 type TechnicalBudgetCatalogItem,
	 type TechnicalBudgetLine,
	 type TechnicalBudgetResponse,
  type StockItemSummary,
	 type CommercialCatalogItem,
	 type ProductCategoryNode,
  type TecpontoNotification,
  type TecpontoTask,
  type TradeEvaluationSummary,
	 type CreateTradeEvaluationPayload,
	 type TradeOutputDevice,
} from "./api";
import { login } from "./api/auth";
import { isAuthRequiredError } from "./api/client";
import { CheckinWizard } from "./CheckinWizard";
import { QuotesCrmScreen } from "./QuotesCrmScreen";
import { WarrantyScreen } from "./WarrantyScreen";
import { CashierMode } from "./CashierMode";
import { ApprovalRequestModal } from "./ApprovalRequestModal";
import { ApprovalRequestsPanel } from "./ApprovalRequestsPanel";
import { DeviceRegistrationModal } from "./DeviceRegistrationModal";
import { LoginScreen, type LoginReason } from "./LoginScreen";
import { PosScreen } from "./PosScreen";
import { RetailProductModal } from "./RetailProductModal";
import { VariantProductModal } from "./VariantProductModal";
import { ListingMetadataModal } from "./ListingMetadataModal";
import { ProductCategoryScreen } from "./ProductCategoryScreen";
import { ProductVariantAttributesScreen } from "./ProductVariantAttributesScreen";
import { NotificationHistoryScreen } from "./NotificationHistoryScreen";
import { MyEarningsScreen } from "./MyEarningsScreen";
import { PartRequestModal, PartRequestsScreen } from "./PartRequestsScreen";
import { UserManagementScreen } from "./UserManagementScreen";
import { CashStatementScreen } from "./CashStatementScreen";
import { AdministrativeCenterScreen } from "./AdministrativeCenterScreen";
import { AdministrationSettingsScreen } from "./AdministrationSettingsScreen";
import { RegistryEditorModal } from "./RegistryEditorModal";
import { getUnifiedPanelDefinition, panelDefinitions, type ActionDefinition, type OperationPillars } from "./roleConfig";
import { ServiceOrderKanban } from "./ServiceOrderKanban";
import { ServiceCatalogScreen } from "./ServiceCatalogScreen";
import { ServiceCategoriesScreen } from "./ServiceCategoriesScreen";
import { WorkflowMoveMenu } from "./WorkflowMoveMenu";
import { BudgetDecisionModal, PickupModal } from "./ServiceOrderFlows";
import {
  BadgeStatus,
  Button,
  Card,
  ContextMenu,
  DataTable,
  getStatBarVisual,
  getStoredListPresentation,
  LayeredFilters,
  ListGridToggle,
  MetricCard,
  Modal,
  Sidebar,
  StatBar,
  Toast,
  Topbar,
  WhatsAppLogo,
  type ContextMenuItem,
  type ListPresentation,
  type QuickFilter,
  type TableColumn,
} from "./ui";
import { cx } from "./ui/utils";
import { parseServerDate } from "./utils/date";

const LIST_PAGE_SIZE = 20;

type LoadState =
  | { status: "loading" }
  | { status: "login_required"; reason: LoginReason; message?: string }
  | { status: "no_role"; boot: BootResponse }
  | { status: "ready"; boot: BootResponse; metrics: DashboardMetrics; notifications: NotificationListResponse; orders: ServiceOrderSummary[] }
  | { status: "error"; message: string };
type ServiceOrderListState =
  | { status: "loading" }
  | { status: "ready"; count: number; items: ServiceOrderSummary[] }
  | { status: "error"; message: string };
type ToastState = { message: string; tone: "success" | "error" };
type ServiceOrderFlow = "approve" | "reject" | "pickup";
type ServiceOrdersViewMode = "list" | "grid" | "kanban";
type AppTheme = "dark" | "light";
type AppDensity = "comfortable" | "compact";
type AgendaDefaultView = "month" | "week" | "list";
type ContextMenuKind = "customer" | "global" | "product" | "service-order";
type PendingPosBarcode = { code: string; id: number };
type PendingRetailBarcode = { code: string; id: number };

interface TecpontoContextTarget {
	barcode?: string | null;
  customer?: string | null;
  kind: ContextMenuKind;
  label?: string | null;
  name?: string | null;
  workflowState?: string | null;
}

interface TecpontoContextMenuState {
  target: TecpontoContextTarget;
  x: number;
  y: number;
}
type QueueFilter = "all" | "Aguardando aprovação" | "Entrada criada" | "Em diagnóstico" | "Diagnosticado — aguardando orçamento" | "Aprovado" | "Aguardando peça" | "Em reparo" | "Teste final" | "Pronto para retirada" | "Entregue" | "Reprovado";
type DashboardPeriodMode = "none" | "7d" | "14d" | "custom";

function commercialName() {
  return window.tecpontoBoot?.identity?.display_name || "Empresa";
}

interface DashboardPeriodFilter {
  mode: DashboardPeriodMode;
  fromDate: string;
  toDate: string;
}

interface ServiceOrderFilterState {
	assignment: "all" | "assigned" | "unassigned";
  period: DashboardPeriodFilter;
	priority: "all" | "Alta" | "Media" | "Normal";
  query: string;
  status: QueueFilter;
}

const SERVICE_ORDERS_VIEW_KEY = "tecponto.service-orders.view";
const THEME_STORAGE_PREFIX = "tecponto.theme.";
const DENSITY_STORAGE_PREFIX = "tecponto.density.";
const AGENDA_VIEW_STORAGE_PREFIX = "tecponto.agenda.v2.view.";
const BARCODE_MIN_LENGTH = 6;
const BARCODE_KEY_INTERVAL_MS = 100;
const DEFAULT_DASHBOARD_PERIOD: DashboardPeriodFilter = {
  fromDate: "",
  mode: "none",
  toDate: "",
};
const DEFAULT_SERVICE_ORDER_FILTERS: ServiceOrderFilterState = {
	assignment: "all",
  period: DEFAULT_DASHBOARD_PERIOD,
	priority: "all",
  query: "",
  status: "all",
};
const QUEUE_FILTERS: Array<{ label: string; value: QueueFilter }> = [
  { label: "Todos os status", value: "all" },
  { label: "Aguardando aprovação", value: "Aguardando aprovação" },
  { label: "Aguardando orçamento", value: "Diagnosticado — aguardando orçamento" },
  { label: "Entrada criada", value: "Entrada criada" },
  { label: "Entregues", value: "Entregue" },
  { label: "Reprovados", value: "Reprovado" },
];
const DASHBOARD_PERIOD_OPTIONS: Array<{ label: string; value: DashboardPeriodMode }> = [
  { label: "Últimos 7 dias", value: "7d" },
  { label: "Últimos 14 dias", value: "14d" },
  { label: "Personalizado", value: "custom" },
];
const CASHIER_ROUTE = "/tecponto/caixa";
const CHECKIN_ROUTE = "/tecponto/nova-os";
const CHECKIN_RETURN_TO_KEY = "tecponto.checkin.return-to";
const CHECKIN_OPEN_ORDER_KEY = "tecponto.checkin.open-order";
const CHECKIN_TRACKING_LINK_KEY = "tecponto.checkin.tracking-link";
const CHECKIN_NAVIGATION_TARGET_KEY = "tecponto.checkin.navigate-to";

function getThemeStorageKey(userName: string) {
  return `${THEME_STORAGE_PREFIX}${userName}`;
}

function getDensityStorageKey(userName: string) {
  return `${DENSITY_STORAGE_PREFIX}${userName}`;
}

function readStoredTheme(userName: string): AppTheme {
  try {
    const stored = window.localStorage.getItem(getThemeStorageKey(userName));
    return stored === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

function readStoredDensity(userName: string): AppDensity {
  try {
    return window.localStorage.getItem(getDensityStorageKey(userName)) === "compact" ? "compact" : "comfortable";
  } catch {
    return "comfortable";
  }
}

function readStoredAgendaDefault(userName: string): AgendaDefaultView {
  try {
    const stored = window.localStorage.getItem(`${AGENDA_VIEW_STORAGE_PREFIX}${userName}`);
    return stored === "list" || stored === "week" ? stored : "month";
  } catch {
    return "month";
  }
}

function readContextTarget(element: HTMLElement | null): TecpontoContextTarget {
  const kind = element?.dataset.tpContext as ContextMenuKind | undefined;
  if (!element || !kind || !["customer", "product", "service-order"].includes(kind)) {
    return { kind: "global" };
  }
  return {
	barcode: element.dataset.tpBarcode ?? null,
    customer: element.dataset.tpCustomer ?? null,
    kind,
    label: element.dataset.tpLabel ?? element.dataset.tpName ?? null,
    name: element.dataset.tpName ?? null,
    workflowState: element.dataset.tpWorkflowState ?? null,
  };
}

function contextMenuTitle(target: TecpontoContextTarget) {
  if (target.kind === "service-order" && target.name) {
    return target.name;
  }
  if (target.kind === "customer") {
    return target.label ?? "Cliente";
  }
  if (target.kind === "product") {
    return target.label ?? target.name ?? "Produto";
  }
  return "Atalhos";
}

function contextMenuSubtitle(target: TecpontoContextTarget) {
  if (target.kind === "service-order") {
    return [target.customer, target.workflowState].filter(Boolean).join(" - ");
  }
  return "Clique direito para abrir";
}

function serviceOrderPrintUrl(name: string, format: string) {
  return `/printview?doctype=Service%20Order&name=${encodeURIComponent(name)}&format=${encodeURIComponent(format)}&no_letterhead=0`;
}

function workflowFlowForState(state: string | null | undefined): ServiceOrderFlow | null {
  if (state === "Aguardando aprovação" || state === "Aguardando aprovaÃ§Ã£o") {
    return "approve";
  }
  if (state === "Pronto para retirada") {
    return "pickup";
  }
  return null;
}

const viewTitles: Record<NavigationTarget, { title: string; subtitle: string }> = {
  overview: {
    title: "Visão geral",
    subtitle: "Atendimentos, pendências e atalhos do balcão.",
  },
  "mesa-flow": {
    title: "Mesa / Fluxo",
    subtitle: "Filas de trabalho organizadas pelo próximo passo.",
  },
  "service-orders": {
    title: "Ordens de serviço",
    subtitle: "Fila de OS com status e responsáveis.",
  },
  "service-order-detail": {
    title: "Detalhe da OS",
    subtitle: "Cliente, aparelho, orçamento, workflow e impressos.",
  },
  "quotes-crm": {
    title: "CRM de Orçamentos",
    subtitle: "Acompanhamento de propostas, decisões do cliente e follow-up.",
  },
	warranties: {
		title: "Garantias",
		subtitle: "Consultar cobertura e iniciar atendimento de retorno.",
	},
  customers: {
    title: "Clientes",
    subtitle: "Busca por nome, telefone, e-mail ou código.",
  },
  devices: {
    title: "Aparelhos",
    subtitle: "Aparelhos cadastrados para atendimento.",
  },
  services: {
    title: "Serviços",
    subtitle: "Catálogo de mão de obra, preços e prazos sugeridos.",
  },
  "service-categories": {
    title: "Categorias de serviço",
    subtitle: "Organização da mão de obra e dos prazos sugeridos.",
  },
  "trade-ins": {
    title: "Trocas",
    subtitle: "Avaliações e propostas do TROQUE.",
  },
  "parts-stock": {
    title: "Peças e estoque",
    subtitle: "Consulta de disponibilidade por depósito.",
  },
  "repair-parts": {
    title: "Peças de reparo",
    subtitle: "Disponibilidade exclusiva do depósito de Reparo.",
  },
  "my-earnings": {
    title: "Minhas comissões",
    subtitle: "Lançamentos da sua mão de obra.",
  },
  "part-requests": {
    title: "Solicitações de peça",
    subtitle: "Necessidades registradas para as suas OS.",
  },
  "commercial-products": {
    title: "Produtos",
    subtitle: "Disponibilidade exclusiva do estoque Comercial.",
  },
  "product-attributes": {
    title: "Atributos e variações",
    subtitle: "Atributos nativos, valores e combinações de produtos.",
  },
  "product-categories": {
    title: "Categorias de produtos",
    subtitle: "Hierarquia comercial e disponibilidade para venda online.",
  },
  "used-devices": {
    title: "Aparelhos usados",
    subtitle: "Seminovos recebidos no fluxo de troca.",
  },
  pos: {
    title: "PDV do balcão",
    subtitle: "Venda rápida por código de barras ou busca de produto.",
  },
  "cash-statement": {
    title: "Caixa e extrato",
    subtitle: "Conferência da gaveta, movimentos e fechamento diário.",
  },
  sales: {
    title: "Vendas e acessórios",
    subtitle: "Acesso rápido ao fluxo de venda do balcão.",
  },
  "approval-requests": {
    title: "Central de aprovacoes",
    subtitle: "Solicitacoes que exigem decisao de Gestor ou Diretor.",
  },
  notifications: {
    title: "Notificações",
    subtitle: "Histórico de avisos e encaminhamentos da operação.",
  },
  "user-management": {
    title: "Pessoas e acessos",
    subtitle: "Contas, papéis operacionais e controles individuais.",
  },
  administration: {
    title: "Administração",
    subtitle: "Configurações, pessoas, caixa e relatório de vendas.",
  },
  "administration-settings": {
    title: "Configurações da loja",
    subtitle: "Operação, identidade, SLA e taxas de cartão.",
  },
};

export function App() {
	const cashierMode = window.location.pathname.replace(/\/+$/, "") === CASHIER_ROUTE;
	const checkinPage = window.location.pathname.replace(/\/+$/, "") === CHECKIN_ROUTE;
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [activeView, setActiveView] = useState<NavigationTarget>("overview");
  const [globalSearchOpen, setGlobalSearchOpen] = useState(false);
	const [globalSearchQuery, setGlobalSearchQuery] = useState("");
  const [accountOpen, setAccountOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [preferencesOpen, setPreferencesOpen] = useState(false);
  const [contextMenu, setContextMenu] = useState<TecpontoContextMenuState | null>(null);
  const [selectedOrderName, setSelectedOrderName] = useState<string | null>(null);
  const [pendingOrderFlow, setPendingOrderFlow] = useState<ServiceOrderFlow | null>(null);
  const [pendingPosBarcode, setPendingPosBarcode] = useState<PendingPosBarcode | null>(null);
  const [pendingRetailBarcode, setPendingRetailBarcode] = useState<PendingRetailBarcode | null>(null);
  const [pendingServiceOrderStatus, setPendingServiceOrderStatus] = useState<QueueFilter | null>(null);
  const [checkinDirty, setCheckinDirty] = useState(false);
  const [serviceOrdersView, setServiceOrdersView] = useState<ServiceOrdersViewMode>(getStoredServiceOrdersView);
  const [density, setDensity] = useState<AppDensity>("comfortable");
  const [agendaPreferenceVersion, setAgendaPreferenceVersion] = useState(0);
  const [theme, setTheme] = useState<AppTheme>("dark");
  const [toast, setToast] = useState<ToastState | null>(null);
  const toastTimer = useRef<number | null>(null);

  const load = useCallback(async (options?: { quiet?: boolean }) => {
    if (!options?.quiet) {
      setState({ status: "loading" });
    }
    try {
      const boot = await getBoot();
      if (boot.user.panel === "sem_papel" && !boot.user.can_manage_users) {
        setState({ status: "no_role", boot });
        return;
      }
      if (boot.user.panel === "sem_papel" && boot.user.can_manage_users) {
        setActiveView("user-management");
      }
      const [orderList, metrics, notificationList] = await Promise.all([serviceOrders.list(12), balcao.getDashboardMetrics(), notifications.list()]);
      setState({ status: "ready", boot, metrics, notifications: notificationList, orders: orderList.items });
    } catch (error) {
      if (isAuthRequiredError(error)) {
        setState({ status: "login_required", reason: "guest" });
        return;
      }
      setState({ status: "error", message: error instanceof Error ? error.message : "Falha ao carregar" });
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    document.documentElement.dataset.tecpontoTheme = theme;
  }, [theme]);

  useEffect(() => {
    document.documentElement.dataset.tecpontoDensity = density;
  }, [density]);

  useEffect(() => {
    if (state.status === "ready" || state.status === "no_role") {
      document.title = state.boot.identity.display_name;
    }
  }, [state]);

  useEffect(() => {
    const onSessionExpired = () => {
      setState({
        message: "Sua sessão expirou. Entre novamente para continuar.",
        reason: "expired",
        status: "login_required",
      });
    };
    window.addEventListener("tecponto:session-expired", onSessionExpired);
    return () => window.removeEventListener("tecponto:session-expired", onSessionExpired);
  }, []);

  useEffect(() => {
    const onHelpShortcut = (event: KeyboardEvent) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      const isEditing = Boolean(target?.closest("input, textarea, select, [contenteditable='true']"));
      if (event.key !== "F1" && (event.key !== "?" || isEditing || event.ctrlKey || event.metaKey || event.altKey)) {
        return;
      }
      event.preventDefault();
      setHelpOpen(true);
    };
    window.addEventListener("keydown", onHelpShortcut);
    return () => window.removeEventListener("keydown", onHelpShortcut);
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(SERVICE_ORDERS_VIEW_KEY, serviceOrdersView);
    } catch {
      // Preference persistence is useful, not critical to the workflow.
    }
  }, [serviceOrdersView]);

  useEffect(() => {
    if (state.status !== "ready") {
      return;
    }
    setTheme(readStoredTheme(state.boot.user.name));
    setDensity(readStoredDensity(state.boot.user.name));
  }, [state]);

  useEffect(() => {
    return () => {
      if (toastTimer.current) {
        window.clearTimeout(toastTimer.current);
      }
    };
  }, []);

  const showToast = useCallback((message: string, tone: ToastState["tone"] = "success") => {
    setToast({ message, tone });
    if (toastTimer.current) {
      window.clearTimeout(toastTimer.current);
    }
    toastTimer.current = window.setTimeout(() => setToast(null), 3200);
  }, []);

	const operationPillars = (state.status === "ready" || state.status === "no_role")
		? state.boot.features.pillars
		: { repair: true, buy: true, tradein: true };

  useEffect(() => {
    if (state.status !== "ready") {
      return;
    }

    let buffer = "";
    let lastKeyAt = 0;
    let resetTimer: number | null = null;
    const reset = () => {
      buffer = "";
      lastKeyAt = 0;
      if (resetTimer) {
        window.clearTimeout(resetTimer);
        resetTimer = null;
      }
    };
    const isEditable = (target: EventTarget | null) => {
      const element = target instanceof HTMLElement ? target : null;
      return Boolean(element?.closest("input, textarea, select, [contenteditable='true']"));
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.ctrlKey || event.altKey || event.metaKey || isEditable(event.target)) {
        return;
      }

      if (event.key === "Enter") {
        const scanned = buffer;
        const isScannerSequence = scanned.length >= BARCODE_MIN_LENGTH && Date.now() - lastKeyAt <= BARCODE_KEY_INTERVAL_MS * 2;
        reset();
        if (!isScannerSequence) {
          return;
        }
        if (!operationPillars.buy) {
          return;
        }
        event.preventDefault();
        setPendingPosBarcode({ code: scanned, id: Date.now() });
        setActiveView("pos");
        return;
      }

      if (event.key.length !== 1 || !/^[A-Za-z0-9._-]$/.test(event.key)) {
        reset();
        return;
      }

      const now = Date.now();
      if (now - lastKeyAt > BARCODE_KEY_INTERVAL_MS) {
        buffer = "";
      }
      buffer += event.key;
      lastKeyAt = now;
      if (resetTimer) {
        window.clearTimeout(resetTimer);
      }
      resetTimer = window.setTimeout(reset, BARCODE_KEY_INTERVAL_MS * 3);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      reset();
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [operationPillars.buy, state.status]);

  const copyToClipboard = useCallback(
    async (value: string, label: string) => {
      try {
        await navigator.clipboard.writeText(value);
        showToast(`${label} copiado.`);
      } catch {
        showToast("Nao foi possivel copiar para a area de transferencia.", "error");
      }
    },
    [showToast],
  );

  const openServiceOrder = useCallback((name: string, flow: ServiceOrderFlow | null = null) => {
    setSelectedOrderName(name);
    setPendingOrderFlow(flow);
    setActiveView("service-order-detail");
  }, []);

  useEffect(() => {
    try {
			const navigationTarget = window.sessionStorage.getItem(CHECKIN_NAVIGATION_TARGET_KEY);
			if (navigationTarget && navigationTarget in viewTitles) {
				window.sessionStorage.removeItem(CHECKIN_NAVIGATION_TARGET_KEY);
				setActiveView(navigationTarget as NavigationTarget);
			}
      const orderName = window.sessionStorage.getItem(CHECKIN_OPEN_ORDER_KEY);
      if (!orderName) return;
      window.sessionStorage.removeItem(CHECKIN_OPEN_ORDER_KEY);
      openServiceOrder(orderName);
    } catch {
      // Returning to the default screen remains safe when session storage is unavailable.
    }
  }, [openServiceOrder]);

  const openServiceOrderList = useCallback((status: QueueFilter = "all") => {
    setPendingServiceOrderStatus(status);
    setActiveView("service-orders");
  }, []);

  const clearPendingOrderFlow = useCallback(() => {
    setPendingOrderFlow(null);
  }, []);

  const startCheckin = useCallback(() => {
		if (!operationPillars.repair) {
			showToast("O pilar REPARO está desativado nesta loja.", "error");
			return;
		}
    try {
      window.sessionStorage.setItem(CHECKIN_RETURN_TO_KEY, `${window.location.pathname}${window.location.search}${window.location.hash}`);
    } catch {
      // Direct access to the page has a deterministic fallback.
    }
    window.location.assign(CHECKIN_ROUTE);
  }, [operationPillars.repair, showToast]);

  const closeCheckinPage = useCallback(() => {
    let returnTo = "/tecponto";
    try {
      const stored = window.sessionStorage.getItem(CHECKIN_RETURN_TO_KEY);
      window.sessionStorage.removeItem(CHECKIN_RETURN_TO_KEY);
      if (stored?.startsWith("/tecponto") && stored !== CHECKIN_ROUTE) {
        returnTo = stored;
      }
    } catch {
      // The safe default is intentional for a direct visit to the route.
    }
    window.location.assign(returnTo);
  }, []);

	const navigateFromSidebar = useCallback((target: NavigationTarget) => {
		if (!checkinPage) {
			setActiveView(target);
			return;
		}

		if (checkinDirty && !window.confirm("Existem dados nao salvos no check-in. Deseja sair mesmo assim?")) {
			return;
		}

		try {
			window.sessionStorage.removeItem(CHECKIN_RETURN_TO_KEY);
			window.sessionStorage.setItem(CHECKIN_NAVIGATION_TARGET_KEY, target);
		} catch {
			// The default route remains available if session storage is unavailable.
		}
		window.location.assign("/tecponto");
	}, [checkinDirty, checkinPage]);

  const openCreatedCheckinOrder = useCallback((response: CheckinResponse) => {
    try {
      window.sessionStorage.removeItem(CHECKIN_RETURN_TO_KEY);
      window.sessionStorage.setItem(CHECKIN_OPEN_ORDER_KEY, response.service_order.name);
      window.sessionStorage.setItem(
        CHECKIN_TRACKING_LINK_KEY,
        JSON.stringify({ serviceOrder: response.service_order.name, tracking: response.tracking }),
      );
    } catch {
      // The shell still opens when storage is unavailable.
    }
    window.location.assign("/tecponto");
  }, []);

  const toggleNotifications = useCallback(() => {
    setNotificationsOpen((current) => !current);
  }, []);

  useEffect(() => {
    if (!notificationsOpen) {
      return;
    }

    const closeFromOutside = (event: PointerEvent) => {
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest("[data-tp-notifications]")) {
        return;
      }
      setNotificationsOpen(false);
    };
    const closeWithEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setNotificationsOpen(false);
      }
    };

    document.addEventListener("pointerdown", closeFromOutside);
    window.addEventListener("keydown", closeWithEscape);
    return () => {
      document.removeEventListener("pointerdown", closeFromOutside);
      window.removeEventListener("keydown", closeWithEscape);
    };
  }, [notificationsOpen]);

  useEffect(() => {
    const clampMenuPosition = (clientX: number, clientY: number) => ({
      x: Math.max(12, Math.min(clientX, window.innerWidth - 304)),
      y: Math.max(12, Math.min(clientY, window.innerHeight - 440)),
    });

    const onContextMenu = (event: MouseEvent) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      const contextSource = target?.closest<HTMLElement>("[data-tp-context]") ?? null;
      const nativeTarget = target?.closest("input, textarea, select, canvas, [contenteditable='true']");
      const selectedText = window.getSelection()?.toString();
		if (!contextSource || nativeTarget || selectedText) {
        return;
      }
      event.preventDefault();
      setContextMenu({
        ...clampMenuPosition(event.clientX, event.clientY),
        target: readContextTarget(contextSource),
      });
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === ".") {
        event.preventDefault();
        setContextMenu({
          ...clampMenuPosition(Math.min(window.innerWidth - 320, 340), 92),
          target: { kind: "global" },
        });
      }
    };

    document.addEventListener("contextmenu", onContextMenu);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("contextmenu", onContextMenu);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  const toggleTheme = useCallback(() => {
    if (state.status !== "ready") {
      return;
    }
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      try {
        window.localStorage.setItem(getThemeStorageKey(state.boot.user.name), next);
      } catch {
        // Theme preference is local comfort, not business-critical.
      }
      return next;
    });
  }, [state]);

  const savePreferences = useCallback((next: { agendaDefault: AgendaDefaultView; density: AppDensity; theme: AppTheme }) => {
    if (state.status !== "ready") {
      return;
    }
    const userName = state.boot.user.name;
    setTheme(next.theme);
    setDensity(next.density);
    try {
      window.localStorage.setItem(getThemeStorageKey(userName), next.theme);
      window.localStorage.setItem(getDensityStorageKey(userName), next.density);
      window.localStorage.setItem(`${AGENDA_VIEW_STORAGE_PREFIX}${userName}`, next.agendaDefault);
    } catch {
      // These choices affect only presentation and must not interrupt operations.
    }
    setAgendaPreferenceVersion((current) => current + 1);
    showToast("Preferências salvas.");
  }, [showToast, state]);

  const contextMenuItems = useMemo<Array<ContextMenuItem>>(() => {
    if (!contextMenu) {
      return [];
    }

    if (contextMenu.target.kind === "service-order" && contextMenu.target.name) {
      const orderName = contextMenu.target.name;
      const flow = workflowFlowForState(contextMenu.target.workflowState);
      const items: ContextMenuItem[] = [
        {
          detail: contextMenu.target.workflowState ?? "Abrir detalhe completo",
          icon: <Wrench size={17} />,
          label: "Abrir OS",
          onSelect: () => openServiceOrder(orderName),
        },
        {
          detail: orderName,
          icon: <Copy size={17} />,
          label: "Copiar numero da OS",
          onSelect: () => void copyToClipboard(orderName, "Numero da OS"),
        },
      ];

      if (flow === "approve") {
        items.push(
          {
            detail: "Registra canal, atendente e observacao",
            icon: <CheckCircle2 size={17} />,
            label: "Aprovar orcamento",
            onSelect: () => openServiceOrder(orderName, "approve"),
            separatorBefore: true,
          },
          {
            detail: "Exige motivo da recusa",
            icon: <XCircle size={17} />,
            label: "Reprovar orcamento",
            onSelect: () => openServiceOrder(orderName, "reject"),
          },
        );
      }

      if (flow === "pickup") {
        items.push({
          detail: "Coleta assinatura e terceiro, se houver",
          icon: <CheckCircle2 size={17} />,
          label: "Iniciar retirada",
          onSelect: () => openServiceOrder(orderName, "pickup"),
          separatorBefore: true,
        });
      }

      items.push(
        {
          detail: "PDF do check-in",
          icon: <FileText size={17} />,
          label: "Termo de entrada",
          onSelect: () => window.open(serviceOrderPrintUrl(orderName, "Tecponto Termo de Entrada"), "_blank", "noopener,noreferrer"),
          separatorBefore: true,
        },
        {
          detail: "PDF do orcamento",
          icon: <Printer size={17} />,
          label: "Orcamento",
          onSelect: () => window.open(serviceOrderPrintUrl(orderName, "Tecponto OS Orcamento"), "_blank", "noopener,noreferrer"),
        },
        {
          detail: "Etiqueta do saquinho",
          icon: <Tag size={17} />,
          label: "Etiqueta QR",
          onSelect: () => window.open(serviceOrderPrintUrl(orderName, "Tecponto Etiqueta QR"), "_blank", "noopener,noreferrer"),
        },
        {
          detail: "PDF de entrega",
          icon: <Printer size={17} />,
          label: "Termo de retirada",
          onSelect: () => window.open(serviceOrderPrintUrl(orderName, "Tecponto Termo de Retirada"), "_blank", "noopener,noreferrer"),
        },
      );
      return items;
    }

		if (contextMenu.target.kind === "customer" && contextMenu.target.name) {
			const customerName = contextMenu.target.label ?? contextMenu.target.name;
			return [
				{
					detail: contextMenu.target.name,
					icon: <UserRound size={17} />,
					label: "Buscar cliente",
					onSelect: () => {
						setGlobalSearchQuery(customerName);
						setGlobalSearchOpen(true);
					},
				},
				{
					detail: customerName,
					icon: <Copy size={17} />,
					label: "Copiar nome",
					onSelect: () => void copyToClipboard(customerName, "Nome do cliente"),
				},
			];
		}

		if (contextMenu.target.kind === "product" && contextMenu.target.name) {
			const itemCode = contextMenu.target.name;
			const actions: ContextMenuItem[] = [
				{
					detail: itemCode,
					icon: <Copy size={17} />,
					label: "Copiar código do item",
					onSelect: () => void copyToClipboard(itemCode, "Código do item"),
				},
			];
			if (contextMenu.target.barcode && operationPillars.buy) {
				actions.push({
					detail: "Adiciona o item ao carrinho",
					icon: <ShoppingCart size={17} />,
					label: "Vender no PDV",
					onSelect: () => {
						setPendingPosBarcode({ code: contextMenu.target.barcode as string, id: Date.now() });
						setActiveView("pos");
					},
					separatorBefore: true,
				});
			}
			return actions;
		}

    return [
      ...(operationPillars.repair ? [{
        detail: "Fluxo completo de check-in",
        icon: <Plus size={17} />,
        label: "Nova OS",
        onSelect: startCheckin,
      }] : []),
      {
        detail: "Cliente, aparelho, OS ou venda",
        icon: <SearchIcon size={17} />,
        label: "Busca global",
        onSelect: () => setGlobalSearchOpen(true),
      },
      ...(operationPillars.repair ? [{
        detail: "Lista e Kanban",
        icon: <Wrench size={17} />,
        label: "Ordens de servico",
        onSelect: () => setActiveView("service-orders"),
      }] : []),
      {
        detail: "Cadastro e historico",
        icon: <UserRound size={17} />,
        label: "Clientes",
        onSelect: () => setActiveView("customers"),
      },
      {
        detail: "Consulta e cadastro avulso",
        icon: <Smartphone size={17} />,
        label: "Aparelhos",
        onSelect: () => setActiveView("devices"),
      },
      ...(operationPillars.repair ? [{
        detail: "Disponibilidade por deposito",
        icon: <Package size={17} />,
        label: "Pecas e estoque",
        onSelect: () => setActiveView("parts-stock"),
      }] : []),
      ...(operationPillars.buy ? [{
        detail: "Leitor USB ou busca por nome",
        icon: <ShoppingCart size={17} />,
        label: "Lancar venda",
        onSelect: () => setActiveView("pos"),
        separatorBefore: true,
      }] : []),
      {
        detail: "Recarrega numeros e filas",
        icon: <RefreshCw size={17} />,
        label: "Atualizar dados",
        onSelect: () => void load({ quiet: true }),
      },
    ];
  }, [contextMenu, copyToClipboard, load, openServiceOrder, operationPillars.buy, operationPillars.repair, startCheckin]);

  const handleCheckinCreated = useCallback((response: CheckinResponse) => {
    void load({ quiet: true });
    showToast(`OS ${response.service_order.name} criada com foto e assinatura.`);
  }, [load, showToast]);

  const handleLogin = useCallback(async (credentials: { password: string; user: string }) => {
    await login(credentials);
    window.location.assign(cashierMode ? CASHIER_ROUTE : "/tecponto");
  }, [cashierMode]);

  if (state.status === "loading") {
    return <LoadingShell />;
  }

  if (state.status === "login_required") {
    return <LoginScreen message={state.message} onLogin={handleLogin} reason={state.reason} />;
  }

  if (state.status === "no_role") {
    return <NoRoleScreen boot={state.boot} onLogout={logout} onRetry={() => void load()} />;
  }

  if (state.status === "error") {
    return (
      <main className="grid min-h-screen place-items-center p-6">
        <Card className="max-w-md p-6 text-center">
          <h1 className="text-xl font-bold text-white">{commercialName()}</h1>
          <p className="mt-3 text-sm text-tec-subtle">{state.message}</p>
          <Button className="mt-5" onClick={() => void load()} variant="primary">
            Tentar novamente
          </Button>
        </Card>
      </main>
    );
  }

  const contextOptions = state.boot.panels.filter((option) => state.boot.user.roles.includes(option.role));
  (window as unknown as { tecpontoCurrentRoles?: string[] }).tecpontoCurrentRoles = state.boot.user.roles;
  const rolePanels = contextOptions.map((option) => option.panel);
  const visualUser = rolePanels.length > 1
    ? {
      ...state.boot.user,
      role_label: contextOptions.map((option) => option.label).join(" + "),
      role_name: contextOptions.map((option) => option.role).join(", "),
      subtitle: "Visao unificada",
    }
    : state.boot.user;
  const brandName = state.boot.identity.display_name;
  const basePanel = getUnifiedPanelDefinition(
    rolePanels,
    state.boot.user.full_name,
    brandName,
    state.boot.features.technician_commissions_enabled,
		state.boot.features.pillars,
  );
  const panel = state.boot.user.can_manage_users
    ? {
      ...basePanel,
      nav: basePanel.nav.map((section) => section.label === "Administração"
        ? { ...section, items: [...section.items, { id: "administration" as NavigationTarget, icon: Users, label: "Administração", subtitle: "Pessoas, caixa e relatórios" }] }
        : section,
      ),
    }
    : basePanel;
  const currentView = activeView === "overview"
    ? null
    : activeView === "service-order-detail" && !state.metrics.sales_visible
      ? { title: "Detalhe da OS", subtitle: "Diagnóstico, execução e workflow da sua bancada." }
      : viewTitles[activeView];

  if (cashierMode) {
    return (
      <>
        <CashierMode brandName={brandName} onExit={() => window.location.assign("/tecponto")} onToast={showToast} singleOperator={state.boot.features.single_operator} />
        {toast ? <Toast message={toast.message} tone={toast.tone} /> : null}
      </>
    );
  }

  return (
    <div className="min-h-screen">
      <Sidebar
        activeItemId={activeView === "service-order-detail" ? "service-orders" : activeView}
        canOpenSystemSettings={state.boot.user.roles.includes("System Manager")}
		identity={state.boot.identity}
        onOpenAccount={() => setAccountOpen(true)}
        onLogout={logout}
        onOpenHelp={() => setHelpOpen(true)}
        onNavigate={navigateFromSidebar}
        onOpenPreferences={() => setPreferencesOpen(true)}
        onOpenSystemSettings={() => setActiveView("administration-settings")}
        sections={panel.nav}
        user={visualUser}
      />
      <Topbar
        onLogout={logout}
        onOpenNotifications={toggleNotifications}
		onGlobalSearchChange={(value) => {
			setGlobalSearchQuery(value);
			setGlobalSearchOpen(true);
		}}
		globalSearchOpen={globalSearchOpen}
		globalSearchQuery={globalSearchQuery}
		onOpenSearch={() => setGlobalSearchOpen(true)}
		searchDropdown={
			<GlobalSearchDropdown
				onClose={() => {
					setGlobalSearchOpen(false);
					setGlobalSearchQuery("");
				}}
				onNavigate={(target, message) => {
					setGlobalSearchOpen(false);
					setGlobalSearchQuery("");
					setActiveView(target);
					if (message) showToast(message);
				}}
				onOpenOrder={(name) => {
					setGlobalSearchOpen(false);
					setGlobalSearchQuery("");
					openServiceOrder(name);
				}}
				query={globalSearchQuery}
			/>
		}
        onToggleTheme={toggleTheme}
        theme={theme}
        unreadNotificationCount={state.notifications.unread_count}
        user={visualUser}
      />

      <main className="tp-main-shell p-4">
        <section className="tp-content-shell">
          {!checkinPage && activeView !== "pos" ? (
            <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <h1 className="text-3xl font-bold text-white md:text-4xl">
                  {currentView ? currentView.title : panel.title}
                </h1>
                <p className="mt-1 text-sm text-tec-subtle">{currentView ? currentView.subtitle : panel.subtitle}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2 md:justify-end">
                {activeView === "service-orders" ? (
                  <ServiceOrderViewToggle onChange={setServiceOrdersView} value={serviceOrdersView} />
                ) : null}
                <Button icon={<RefreshCw size={18} />} onClick={() => void load()}>
                  Atualizar
                </Button>
              </div>
            </div>
          ) : null}

          {checkinPage ? (
            <CheckinWizard
			  brandName={brandName}
			  diagnosisOnlyEnabled={state.boot.features.diagnosis_only_enabled}
              onClose={closeCheckinPage}
              onCreated={handleCheckinCreated}
				onDirtyChange={setCheckinDirty}
              onOpenOrder={openCreatedCheckinOrder}
              presentation="page"
            />
          ) : activeView === "overview" ? (
            <OverviewContent
              actions={panel.actions}
              onNavigate={setActiveView}
              onStartCheckin={startCheckin}
              onOpenServiceOrder={openServiceOrder}
              onToast={showToast}
              onOpenServiceOrderList={openServiceOrderList}
              agendaPanel={rolePanels.length > 1 ? "unified" : visualUser.panel}
              agendaStorageKey={state.boot.user.name}
              agendaPreferenceVersion={agendaPreferenceVersion}
              canApprove={rolePanels.includes("gestor") || rolePanels.includes("diretor")}
              homePanel={rolePanels.length === 1 ? visualUser.panel : "unified"}
              showSales={state.metrics.sales_visible}
              metrics={state.metrics}
              canViewDirectorFinancial={state.boot.user.roles.includes("Tecponto Diretor")}
              singleOperator={state.boot.features.single_operator}
              pillars={operationPillars}
            />
          ) : (
            <NavigationContent
              activeView={activeView}
              initialPosBarcode={pendingPosBarcode}
              initialRetailBarcode={pendingRetailBarcode}
              canReceiveStock={state.boot.user.roles.some((role) => role === "Tecponto Gestor" || role === "System Manager")}
              canEditServiceCatalog={state.boot.user.roles.some((role) => role === "Tecponto Gestor" || role === "Tecponto Diretor" || role === "System Manager")}
              canEditProductCategories={state.boot.user.roles.some((role) => role === "Tecponto Gestor" || role === "Tecponto Diretor" || role === "System Manager")}
			  canEditBasicRegistries={state.boot.user.roles.some((role) => ["Tecponto Atendente", "Tecponto Gestor", "Tecponto Diretor", "System Manager"].includes(role))}
              canViewStoreOperations={state.boot.user.roles.some((role) => role === "Tecponto Gestor" || role === "Tecponto Diretor" || role === "System Manager")}
			  canAssignTechnician={state.boot.user.roles.some((role) => role === "Tecponto Gestor" || role === "System Manager")}
			  canViewDirectorFinancial={state.boot.user.roles.includes("Tecponto Diretor")}
			  technicianAssignment={state.boot.features.technician_assignment}
			  activeTechnicians={state.boot.features.active_technicians}
			  singleTechnician={state.boot.features.single_technician}
			  commissionsEnabled={state.boot.features.technician_commissions_enabled}
			  canManageUsers={state.boot.user.can_manage_users}
			  canOpenSystemSettings={state.boot.user.can_manage_users}
			  isRestrictedTechnician={!state.metrics.sales_visible}
              onInitialPosBarcodeHandled={() => setPendingPosBarcode(null)}
              onInitialRetailBarcodeHandled={() => setPendingRetailBarcode(null)}
              initialServiceOrderStatus={pendingServiceOrderStatus}
              onInitialServiceOrderStatusHandled={() => setPendingServiceOrderStatus(null)}
              onRegisterUnknownRetailBarcode={(code) => {
                setPendingRetailBarcode({ code, id: Date.now() });
                setActiveView("commercial-products");
              }}
              onNavigate={setActiveView}
              onNotificationsChanged={async () => {
                const next = await notifications.list();
                setState((current) => current.status === "ready" ? { ...current, notifications: next } : current);
              }}
              onOpenServiceOrder={openServiceOrder}
              onRefreshData={() => void load({ quiet: true })}
              initialOrderFlow={pendingOrderFlow}
              onInitialOrderFlowHandled={clearPendingOrderFlow}
              onToast={showToast}
              onStartCheckin={startCheckin}
              orders={state.orders}
              serviceOrdersView={serviceOrdersView}
              selectedOrderName={selectedOrderName}
              setServiceOrdersView={setServiceOrdersView}
            />
          )}
        </section>
      </main>
      <NotificationsPanel
        notifications={state.notifications}
        onClose={() => setNotificationsOpen(false)}
        onNavigate={(target, orderName) => {
          setNotificationsOpen(false);
          setActiveView(target);
          if (orderName) {
            setSelectedOrderName(orderName);
          }
        }}
        onMarkAllRead={async () => {
          await notifications.markAllRead();
          const next = await notifications.list();
          setState((current) => current.status === "ready" ? { ...current, notifications: next } : current);
        }}
        onMarkRead={async (name) => {
          await notifications.markRead(name);
          const next = await notifications.list();
          setState((current) => current.status === "ready" ? { ...current, notifications: next } : current);
        }}
        onOpenAll={() => {
          setNotificationsOpen(false);
          setActiveView("notifications");
        }}
        open={notificationsOpen}
      />
      <HelpModal
        onClose={() => setHelpOpen(false)}
        onNavigate={(target) => {
          setHelpOpen(false);
          setActiveView(target);
        }}
        onStartCheckin={() => {
          setHelpOpen(false);
          startCheckin();
        }}
        open={helpOpen}
      />
      <AccountModal onClose={() => setAccountOpen(false)} open={accountOpen} user={visualUser} />
      <PreferencesModal
        agendaDefault={readStoredAgendaDefault(state.boot.user.name)}
        density={density}
        onClose={() => setPreferencesOpen(false)}
        onSave={savePreferences}
        open={preferencesOpen}
        theme={theme}
      />
      {contextMenu ? (
        <ContextMenu
          items={contextMenuItems}
          onClose={() => setContextMenu(null)}
          subtitle={contextMenuSubtitle(contextMenu.target)}
          title={contextMenuTitle(contextMenu.target)}
          x={contextMenu.x}
          y={contextMenu.y}
        />
      ) : null}
      {toast ? <Toast message={toast.message} tone={toast.tone} /> : null}
    </div>
  );
}

type GlobalSearchState =
  | { status: "idle" }
  | { status: "loading" }
  | {
      status: "ready";
      customers: CustomerSummary[];
      devices: CustomerDeviceSummary[];
      orders: ServiceOrderSummary[];
      term: string;
    }
  | { status: "error"; message: string };

function GlobalSearchDropdown({
  onClose,
  onNavigate,
  onOpenOrder,
  query,
}: {
  onClose: () => void;
  onNavigate: (target: NavigationTarget, message?: string) => void;
  onOpenOrder: (name: string) => void;
  query: string;
}) {
  const [searchState, setSearchState] = useState<GlobalSearchState>({ status: "idle" });
  const [selectedIndex, setSelectedIndex] = useState(0);
  const trimmedQuery = query.trim();

  useEffect(() => {
    if (trimmedQuery.length < 2) {
      setSearchState({ status: "idle" });
      return;
    }

    let cancelled = false;
    setSearchState({ status: "loading" });
    const timer = window.setTimeout(() => {
      Promise.all([
        serviceOrders.list({ limit: 6, query: trimmedQuery }),
        balcao.searchCustomers(trimmedQuery, 6),
        balcao.listDevices(trimmedQuery, 6),
      ])
        .then(([orders, customers, devices]) => {
          if (!cancelled) {
            setSearchState({
              customers: customers.items,
              devices: devices.items,
              orders: orders.items,
              status: "ready",
              term: trimmedQuery,
            });
          }
        })
        .catch((caught) => {
          if (!cancelled) {
            setSearchState({
              message: caught instanceof Error ? caught.message : "Não foi possível buscar agora.",
              status: "error",
            });
          }
        });
    }, 220);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [trimmedQuery]);

  const results = searchState.status === "ready"
    ? [
      ...searchState.orders.map((item) => ({ kind: "order" as const, item })),
      ...searchState.customers.map((item) => ({ kind: "customer" as const, item })),
      ...searchState.devices.map((item) => ({ kind: "device" as const, item })),
    ]
    : [];

  useEffect(() => {
    setSelectedIndex(0);
  }, [trimmedQuery, searchState.status]);

  const chooseResult = useCallback((index: number) => {
    const result = results[index];
    if (!result) return;
    if (result.kind === "order") {
      onOpenOrder(result.item.name);
      return;
    }
    if (result.kind === "customer") {
      onNavigate("customers", `Cliente localizado: ${result.item.customer_name ?? result.item.name}`);
      return;
    }
    onNavigate("devices", `Aparelho localizado: ${result.item.imei_serial ?? result.item.name}`);
  }, [onNavigate, onOpenOrder, results]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (!results.length) return;
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setSelectedIndex((current) => (current + 1) % results.length);
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setSelectedIndex((current) => (current - 1 + results.length) % results.length);
      }
      if (event.key === "Enter") {
        event.preventDefault();
        chooseResult(selectedIndex);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [chooseResult, onClose, results.length, selectedIndex]);

  const totalResults =
    searchState.status === "ready"
      ? searchState.orders.length + searchState.customers.length + searchState.devices.length
      : 0;

  return (
    <div className="absolute left-0 top-[calc(100%+0.5rem)] z-50 w-full overflow-hidden rounded-card border border-tec-border/25 bg-tec-panel-strong p-2 shadow-panel" role="listbox">
      <div className="max-h-[min(62vh,540px)] space-y-2 overflow-y-auto p-1">
        {searchState.status === "idle" ? (
          <div className="rounded-control bg-tec-field/60 px-3 py-3 text-sm text-tec-muted">
            Digite pelo menos 2 caracteres para buscar OS, clientes e aparelhos.
          </div>
        ) : null}

        {searchState.status === "loading" ? (
          <div className="flex items-center gap-3 rounded-control bg-tec-field/60 px-3 py-3 text-sm font-semibold text-tec-subtle">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-tec-orange border-t-transparent" />
            Buscando registros...
          </div>
        ) : null}

        {searchState.status === "error" ? (
          <div className="rounded-control border border-tec-red/30 bg-tec-red/10 px-3 py-3 text-sm font-semibold text-red-100">
            {searchState.message}
          </div>
        ) : null}

        {searchState.status === "ready" ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3 px-2 py-1">
              <p className="text-xs font-semibold text-tec-subtle">
                {totalResults} resultado{totalResults === 1 ? "" : "s"} para <span className="text-white">{searchState.term}</span>
              </p>
              <span className="text-[11px] font-semibold text-tec-muted">↑↓ navegar · Enter abrir · Esc fechar</span>
            </div>

            <GlobalSearchSection
              emptyText="Nenhuma OS encontrada."
              title="Ordens de serviço"
            >
              {searchState.orders.map((order) => (
                <button
                  className={`flex w-full items-center justify-between gap-4 rounded-control border px-3 py-2.5 text-left transition ${selectedIndex === searchState.orders.indexOf(order) ? "border-tec-orange/60 bg-tec-orange/10" : "border-tec-border/15 bg-tec-field/55 hover:border-tec-orange/45 hover:bg-tec-orange/10"}`}
                  key={order.name}
                  onClick={() => chooseResult(searchState.orders.indexOf(order))}
                  type="button"
                >
                  <span className="min-w-0">
                    <span className="block font-bold text-white">{order.name}</span>
                    <span className="mt-1 block truncate text-sm text-tec-muted">
                      {order.customer ?? "Cliente não informado"} · {order.reported_defect ?? "Sem defeito informado"}
                    </span>
                  </span>
                  <BadgeStatus status={order.workflow_state} />
                </button>
              ))}
            </GlobalSearchSection>

            <GlobalSearchSection
              emptyText="Nenhum cliente encontrado."
              title="Clientes"
            >
              {searchState.customers.map((customer) => (
                <button
                  className={`flex w-full items-center justify-between gap-4 rounded-control border px-3 py-2.5 text-left transition ${selectedIndex === searchState.orders.length + searchState.customers.indexOf(customer) ? "border-tec-orange/60 bg-tec-orange/10" : "border-tec-border/15 bg-tec-field/55 hover:border-tec-orange/45 hover:bg-tec-orange/10"}`}
                  key={customer.name}
                  onClick={() => chooseResult(searchState.orders.length + searchState.customers.indexOf(customer))}
                  type="button"
                >
                  <span className="min-w-0">
                    <span className="block font-bold text-white">{customer.customer_name ?? customer.name}</span>
                    <span className="mt-1 block truncate text-sm text-tec-muted">
                      {[customer.mobile_no, customer.custom_whatsapp, customer.email_id].filter(Boolean).join(" · ") || "Sem contato"}
                    </span>
                  </span>
                  <ArrowRight className="text-tec-muted" size={17} />
                </button>
              ))}
            </GlobalSearchSection>

            <GlobalSearchSection
              emptyText="Nenhum aparelho encontrado."
              title="Aparelhos"
            >
              {searchState.devices.map((device) => (
                <button
                  className={`flex w-full items-center justify-between gap-4 rounded-control border px-3 py-2.5 text-left transition ${selectedIndex === searchState.orders.length + searchState.customers.length + searchState.devices.indexOf(device) ? "border-tec-orange/60 bg-tec-orange/10" : "border-tec-border/15 bg-tec-field/55 hover:border-tec-orange/45 hover:bg-tec-orange/10"}`}
                  key={device.name}
                  onClick={() => chooseResult(searchState.orders.length + searchState.customers.length + searchState.devices.indexOf(device))}
                  type="button"
                >
                  <span className="min-w-0">
                    <span className="block font-bold text-white">
                      {[device.brand, device.model, device.color].filter(Boolean).join(" ") || device.name}
                    </span>
                    <span className="mt-1 block truncate text-sm text-tec-muted">
                      {device.imei_serial ?? "Sem IMEI"} · {device.customer ?? "Cliente não vinculado"}
                    </span>
                  </span>
                  <ArrowRight className="text-tec-muted" size={17} />
                </button>
              ))}
            </GlobalSearchSection>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function GlobalSearchSection({
  children,
  emptyText,
  title,
}: {
  children: ReactNode;
  emptyText: string;
  title: string;
}) {
  const hasChildren = Array.isArray(children) ? children.length > 0 : Boolean(children);

  return (
    <section className="rounded-card border border-tec-border/15 bg-tec-panel-strong p-4">
      <h3 className="text-base font-bold text-white">{title}</h3>
      <div className="mt-3 space-y-2">
        {hasChildren ? children : <p className="rounded-control bg-tec-field/45 px-4 py-3 text-sm text-tec-muted">{emptyText}</p>}
      </div>
    </section>
  );
}

function NotificationsPanel({
  notifications,
  onClose,
  onMarkAllRead,
  onMarkRead,
  onNavigate,
  onOpenAll,
  open,
}: {
  notifications: NotificationListResponse;
  onClose: () => void;
  onMarkAllRead: () => Promise<void>;
  onMarkRead: (name: string) => Promise<void>;
  onNavigate: (target: NavigationTarget, orderName?: string) => void;
  onOpenAll: () => void;
  open: boolean;
}) {
  if (!open) {
    return null;
  }

  return (
    <section
      className="fixed right-5 top-[calc(var(--tp-topbar-height)_+_0.75rem)] z-40 flex h-[calc(100vh_-_var(--tp-topbar-height)_-_1.5rem)] w-[min(380px,calc(100vw-1.5rem))] flex-col rounded-card border border-tec-border/20 bg-tec-panel-strong p-3 shadow-panel"
      data-tp-notifications="panel"
      role="menu"
    >
      <div className="mb-2 flex items-start justify-between gap-3 px-1">
        <div>
          <h2 className="text-base font-bold text-white">Notificações</h2>
          <p className="mt-1 text-xs text-tec-muted">{notifications.unread_count} não lida{notifications.unread_count === 1 ? "" : "s"}.</p>
        </div>
        <div className="flex items-center gap-1">
          {notifications.unread_count ? <button className="rounded-control px-2 py-1 text-xs font-bold text-tec-orange transition hover:bg-tec-field" onClick={() => void onMarkAllRead()} type="button">Marcar todas</button> : null}
          <button className="rounded-control px-2 py-1 text-xs font-bold text-tec-muted transition hover:bg-tec-field hover:text-white" onClick={onClose} type="button">Fechar</button>
        </div>
      </div>
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {notifications.items.length ? notifications.items.map((item) => (
          <button
            className={cx("w-full rounded-card border p-3 text-left transition hover:border-tec-orange/45", item.is_read ? "border-tec-border/15 bg-tec-field/40" : "border-tec-orange/35 bg-tec-field/70")}
            key={item.name}
            onClick={() => {
              if (!item.is_read) void onMarkRead(item.name);
              const linkedOrderName = item.link
                ? new URL(item.link, window.location.origin).searchParams.get("order")
                : null;
              const orderName = item.reference_doctype === "Service Order"
                ? item.reference_name
                : linkedOrderName;
              if (orderName) onNavigate("service-order-detail", orderName);
              else onNavigate("overview");
            }}
            type="button"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0"><p className="font-bold text-white">{item.title}</p><p className="mt-1 text-sm text-tec-muted">{item.body}</p></div>
              {!item.is_read ? <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-tec-orange" title="Não lida" /> : null}
            </div>
          </button>
        )) : <p className="rounded-control bg-tec-field/45 px-4 py-5 text-center text-sm text-tec-muted">Nenhuma notificação por enquanto.</p>}
      </div>
      <button className="mt-3 w-full rounded-control px-3 py-2 text-sm font-bold text-tec-orange transition hover:bg-tec-field" onClick={onOpenAll} type="button">Ver todas <span aria-hidden="true">→</span></button>
    </section>
  );
}

function AccountModal({ onClose, open, user }: { onClose: () => void; open: boolean; user: LoggedUser }) {
  return (
    <Modal className="max-w-lg" onClose={onClose} open={open} title="Meu perfil / conta">
      <div className="flex items-center gap-4 rounded-card border border-tec-border/20 bg-tec-field/55 p-4">
        <div className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-tec-blue text-lg font-bold text-white">{user.initials}</div>
        <div className="min-w-0">
          <p className="truncate text-lg font-bold text-white">{user.full_name}</p>
          <p className="truncate text-sm text-tec-muted">{user.name}</p>
        </div>
      </div>
      <dl className="mt-5 divide-y divide-tec-border/15 rounded-card border border-tec-border/15 bg-tec-panel-strong px-4">
        <div className="flex items-start justify-between gap-5 py-3"><dt className="text-sm text-tec-muted">Papéis ativos</dt><dd className="max-w-[62%] text-right text-sm font-bold text-white">{user.role_label}</dd></div>
        <div className="flex items-start justify-between gap-5 py-3"><dt className="text-sm text-tec-muted">Visão atual</dt><dd className="text-right text-sm font-bold text-white">{user.subtitle}</dd></div>
      </dl>
      <p className="mt-4 text-sm text-tec-muted">Dados de conta e permissões são administrados pelo responsável da loja.</p>
    </Modal>
  );
}

function PreferencesModal({
  agendaDefault,
  density,
  onClose,
  onSave,
  open,
  theme,
}: {
  agendaDefault: AgendaDefaultView;
  density: AppDensity;
  onClose: () => void;
  onSave: (next: { agendaDefault: AgendaDefaultView; density: AppDensity; theme: AppTheme }) => void;
  open: boolean;
  theme: AppTheme;
}) {
  const [nextTheme, setNextTheme] = useState<AppTheme>(theme);
  const [nextDensity, setNextDensity] = useState<AppDensity>(density);
  const [nextAgendaDefault, setNextAgendaDefault] = useState<AgendaDefaultView>(agendaDefault);

  useEffect(() => {
    if (!open) return;
    setNextTheme(theme);
    setNextDensity(density);
    setNextAgendaDefault(agendaDefault);
  }, [agendaDefault, density, open, theme]);

  const choiceClass = (selected: boolean) => cx(
    "rounded-control border px-3 py-2 text-sm font-bold transition",
    selected ? "border-tec-orange bg-tec-orange text-tec-graphite" : "border-tec-border/25 bg-tec-field text-tec-subtle hover:border-tec-orange/45 hover:text-white",
  );

  return (
    <Modal className="max-w-xl" onClose={onClose} open={open} title="Preferências">
      <div className="space-y-6">
        <section>
          <h3 className="text-base font-bold text-white">Tema</h3>
          <p className="mt-1 text-sm text-tec-muted">Escolha a aparência que fica salva apenas para a sua conta.</p>
          <div className="mt-3 inline-flex flex-wrap gap-2" role="group" aria-label="Tema">
            <button className={choiceClass(nextTheme === "dark")} onClick={() => setNextTheme("dark")} type="button">Escuro</button>
            <button className={choiceClass(nextTheme === "light")} onClick={() => setNextTheme("light")} type="button">Claro</button>
          </div>
        </section>
        <section>
          <h3 className="text-base font-bold text-white">Densidade</h3>
          <p className="mt-1 text-sm text-tec-muted">Compacta reduz a altura das linhas para quem trabalha com listas longas.</p>
          <div className="mt-3 inline-flex flex-wrap gap-2" role="group" aria-label="Densidade da interface">
            <button className={choiceClass(nextDensity === "comfortable")} onClick={() => setNextDensity("comfortable")} type="button">Confortável</button>
            <button className={choiceClass(nextDensity === "compact")} onClick={() => setNextDensity("compact")} type="button">Compacta</button>
          </div>
        </section>
        <section>
          <h3 className="text-base font-bold text-white">Visão padrão da agenda</h3>
          <p className="mt-1 text-sm text-tec-muted">A agenda abre nesta visão quando você entra no painel.</p>
          <div className="mt-3 inline-flex flex-wrap gap-2" role="group" aria-label="Visão padrão da agenda">
            {(["month", "week", "list"] as const).map((view) => <button className={choiceClass(nextAgendaDefault === view)} key={view} onClick={() => setNextAgendaDefault(view)} type="button">{view === "month" ? "Mês" : view === "week" ? "Semana" : "Lista"}</button>)}
          </div>
        </section>
      </div>
      <div className="mt-7 flex justify-end gap-2">
        <Button onClick={onClose}>Cancelar</Button>
        <Button onClick={() => { onSave({ agendaDefault: nextAgendaDefault, density: nextDensity, theme: nextTheme }); onClose(); }} variant="primary">Salvar preferências</Button>
      </div>
    </Modal>
  );
}

function HelpModal({
  onClose,
  onNavigate,
  onStartCheckin,
  open,
}: {
  onClose: () => void;
  onNavigate: (target: NavigationTarget) => void;
  onStartCheckin: () => void;
  open: boolean;
}) {
  return (
    <Modal className="max-w-3xl" onClose={onClose} open={open} title="Ajuda rápida">
      <div className="grid gap-4 md:grid-cols-2">
        <button
          className="rounded-card border border-tec-border/15 bg-tec-field/65 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-orange/10"
          onClick={onStartCheckin}
          type="button"
        >
          <span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
            <Wrench size={20} />
          </span>
          <span className="mt-4 block text-base font-bold text-white">Abrir nova OS</span>
          <span className="mt-1 block text-sm text-tec-muted">Inicia o check-in com cliente, aparelho, foto e assinatura.</span>
        </button>

        <button
          className="rounded-card border border-tec-border/15 bg-tec-field/65 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-orange/10"
          onClick={() => onNavigate("service-orders")}
          type="button"
        >
          <span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
            <SearchIcon size={20} />
          </span>
          <span className="mt-4 block text-base font-bold text-white">Encontrar uma OS</span>
          <span className="mt-1 block text-sm text-tec-muted">Abre a fila com busca, filtros e Kanban.</span>
        </button>

        <button
          className="rounded-card border border-tec-border/15 bg-tec-field/65 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-orange/10"
          onClick={() => onNavigate("customers")}
          type="button"
        >
          <span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
            <UserRound size={20} />
          </span>
          <span className="mt-4 block text-base font-bold text-white">Buscar cliente</span>
          <span className="mt-1 block text-sm text-tec-muted">Consulta por nome, telefone, CPF, RG ou e-mail.</span>
        </button>

        <button
          className="rounded-card border border-tec-border/15 bg-tec-field/65 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-orange/10"
          onClick={() => onNavigate("devices")}
          type="button"
        >
          <span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
            <Smartphone size={20} />
          </span>
          <span className="mt-4 block text-base font-bold text-white">Cadastrar aparelho</span>
          <span className="mt-1 block text-sm text-tec-muted">Abre a tela de aparelhos com cadastro avulso e foto.</span>
        </button>
      </div>

      <div className="mt-5 rounded-card border border-tec-border/15 bg-tec-panel-strong p-4 text-sm text-tec-subtle">
        Os fluxos críticos continuam sendo validados pelo motor do ERPNext: foto e assinatura no check-in, orçamento aprovado,
        nota paga na retirada e permissões por papel.
      </div>
    </Modal>
  );
}

function OverviewContent({
  actions,
  onNavigate,
  onOpenServiceOrderList,
  onOpenServiceOrder,
  onToast,
  onStartCheckin,
  agendaPanel,
  agendaStorageKey,
  agendaPreferenceVersion,
  canApprove,
  homePanel,
  showSales,
  metrics,
  canViewDirectorFinancial,
  singleOperator,
	 pillars,
}: {
  actions: ActionDefinition[];
  onNavigate: (target: NavigationTarget) => void;
  onOpenServiceOrder: (name: string) => void;
  onOpenServiceOrderList: (status: QueueFilter) => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  onStartCheckin: () => void;
  agendaPanel: RolePanel | "unified";
  agendaStorageKey: string;
  agendaPreferenceVersion: number;
  canApprove: boolean;
  homePanel: RolePanel | "unified";
  showSales: boolean;
  metrics: DashboardMetrics;
  canViewDirectorFinancial: boolean;
  singleOperator: boolean;
	 pillars: OperationPillars;
}) {
  const [serviceOrderStats, setServiceOrderStats] = useState<ServiceOrderStatBarResponse["items"]>([]);
  const [salesStats, setSalesStats] = useState<Array<{ key: string; label: string; value: number; amount?: number }>>([]);
  const [directorFinancial, setDirectorFinancial] = useState<DirectorFinancialSummary | null>(null);
	const [directorRiskAgenda, setDirectorRiskAgenda] = useState<DirectorRiskAgenda | null>(null);
  const [directorStrategic, setDirectorStrategic] = useState<DirectorStrategicReport | null>(null);
  const [directorPeriod, setDirectorPeriod] = useState<"7d" | "month">("month");

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      pillars.repair ? serviceOrders.statBar() : Promise.resolve({ items: [] }),
      showSales && pillars.buy ? balcao.getListStatBar("sales") : Promise.resolve({ items: [] }),
    ])
      .then(([serviceOrdersResponse, salesResponse]) => {
        if (!cancelled) {
          setServiceOrderStats(serviceOrdersResponse.items);
          setSalesStats(salesResponse.items);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setServiceOrderStats([]);
          setSalesStats([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [pillars.buy, pillars.repair, showSales]);

  useEffect(() => {
    let cancelled = false;
    if (!canViewDirectorFinancial) {
      setDirectorFinancial(null);
		setDirectorRiskAgenda(null);
      setDirectorStrategic(null);
      return () => { cancelled = true; };
    }
    void balcao.getDirectorFinancialSummary()
      .then((summary) => {
        if (!cancelled) setDirectorFinancial(summary);
      })
      .catch(() => {
        if (!cancelled) setDirectorFinancial(null);
      });
		void balcao.getDirectorRiskAgenda()
			.then((agenda) => {
				if (!cancelled) setDirectorRiskAgenda(agenda);
			})
			.catch(() => {
				if (!cancelled) setDirectorRiskAgenda(null);
			});
    void balcao.getDirectorStrategicReport(directorPeriod)
      .then((report) => {
        if (!cancelled) setDirectorStrategic(report);
      })
      .catch(() => {
        if (!cancelled) setDirectorStrategic(null);
      });
    return () => { cancelled = true; };
  }, [canViewDirectorFinancial, directorPeriod]);

  const isManagerHome = homePanel === "gestor" || homePanel === "diretor" || (homePanel === "unified" && canApprove);
  const managerTicketItems = isManagerHome ? [
    ...(pillars.buy ? [{
      key: "retail-ticket",
      label: "Ticket balcão",
      value: metrics.sales_tickets.retail.average ?? 0,
      displayValue: metrics.sales_tickets.retail.average === null ? "Sem vendas" : metrics.sales_tickets.retail.average.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }),
      detail: `${metrics.sales_tickets.retail.count} venda(s) no dia`,
      icon: <Ticket size={19} />,
      tone: "blue" as const,
    }] : []),
    ...(pillars.repair ? [{
      key: "service-ticket",
      label: "Ticket de OS",
      value: metrics.sales_tickets.service_order.average ?? 0,
      displayValue: metrics.sales_tickets.service_order.average === null ? "Sem OS faturada" : metrics.sales_tickets.service_order.average.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }),
      detail: `${metrics.sales_tickets.service_order.count} OS faturada(s) no dia`,
      icon: <Wrench size={19} />,
      tone: "orange" as const,
    }] : []),
    {
      key: "daily-goal",
      label: "Meta diária",
      value: 0,
      displayValue: "Não configurada",
      detail: "Defina período e indicador",
      icon: <Target size={19} />,
      tone: "amber" as const,
    },
  ] : [];
  const statItems = [
    ...serviceOrderStats.map((item) => ({ ...item, ...getStatBarVisual("service_orders", item.key) })),
    ...salesStats.map((item) => ({
      ...item,
      ...getStatBarVisual("sales", item.key),
      displayValue: item.key === "amount" ? item.value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : undefined,
    })),
    ...managerTicketItems,
  ];

  return (
    <>
      <HomeSectorActions
        actions={actions}
        heading={isManagerHome ? "Ações de gestão" : "Atalhos do setor"}
        onNavigate={onNavigate}
        onStartCheckin={onStartCheckin}
        subtitle={isManagerHome ? "Decisões e filas que mantêm a operação da loja fluindo." : "Ações frequentes para manter o balcão em movimento."}
      />
      {directorFinancial ? <DirectorFinancialPanel summary={directorFinancial} /> : null}
      {directorStrategic ? <DirectorStrategicPanel onPeriodChange={setDirectorPeriod} period={directorPeriod} report={directorStrategic} /> : null}
			{directorRiskAgenda ? <DirectorRiskAgendaPanel agenda={directorRiskAgenda} onOpenOrder={onOpenServiceOrder} /> : null}
      <section className="mt-4">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-xl font-bold text-white">{isManagerHome ? "Operação da loja" : "Operação agora"}</h2>
            <p className="mt-1 text-sm text-tec-muted">
              {isManagerHome
                ? pillars.buy
                  ? "OS por etapa e vendas do dia. Custo, margem, lucro e comissões de terceiros não aparecem aqui."
                  : "OS por etapa. Custo, margem, lucro e comissões de terceiros não aparecem aqui."
                : showSales && pillars.buy
                  ? "OS por etapa e vendas do dia. Sem custo, margem ou lucro."
                  : "Suas OS por etapa. Sem dados de vendas, custo ou margem."}
            </p>
          </div>
          <button className="text-sm font-bold text-tec-orange hover:text-tec-digital-orange" onClick={() => onOpenServiceOrderList("all")} type="button">
            Ver Ordens de servico <ArrowRight className="ml-1 inline" size={16} />
          </button>
        </div>
        <StatBar
          items={statItems}
          onSelect={(key) => onOpenServiceOrderList(QUEUE_FILTERS.some((filter) => filter.value === key) ? key as QueueFilter : "all")}
        />
      </section>
      <div className={singleOperator ? "mt-4 max-w-5xl" : "mt-4"}>
        <DailyActionsPanel key={`${agendaStorageKey}:${agendaPreferenceVersion}`} onOpenOrder={onOpenServiceOrder} onToast={onToast} panel={agendaPanel} storageKey={agendaStorageKey} />
      </div>
      {canApprove && !singleOperator ? <div className="mt-4">
        <ApprovalRequestsPanel compact onOpenAll={() => onNavigate("approval-requests")} onToast={onToast} />
      </div> : null}
    </>
  );
}

function DirectorFinancialPanel({ summary }: { summary: DirectorFinancialSummary }) {
  const money = (value: number) => value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const cards = [
    { label: "Receita realizada", value: money(summary.revenue), detail: "Vendas faturadas hoje", icon: <CreditCard size={19} />, tone: "text-tec-green" },
    { label: "Custo operacional", value: money(summary.operational_cost), detail: "Mercadoria e pecas baixadas", icon: <Box size={19} />, tone: "text-tec-orange" },
    { label: "Lucro bruto operacional", value: money(summary.gross_operating_profit), detail: `Margem bruta: ${summary.gross_margin_pct.toFixed(1)}%`, icon: <CircleDollarSign size={19} />, tone: "text-tec-blue" },
    ...(summary.technician_commissions_enabled ? [{ label: "Comissoes provisionadas", value: money(summary.team_earnings_accrued), detail: "Lancamentos de mao de obra", icon: <Target size={19} />, tone: "text-tec-purple" }] : []),
  ];

  return (
    <section className="mt-4 rounded-card border border-tec-border/20 bg-tec-panel p-4">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-xl font-bold text-white">Resultado operacional</h2>
          <p className="mt-1 text-sm text-tec-muted">{summary.period.label}. Nao inclui despesas fixas, impostos ou folha salarial fixa.</p>
        </div>
        <span className="rounded-full bg-tec-field px-3 py-1 text-xs font-bold text-tec-subtle">Resultado bruto, nao lucro liquido</span>
      </div>
      <div className={`grid gap-3 sm:grid-cols-2 ${summary.technician_commissions_enabled ? "xl:grid-cols-4" : "xl:grid-cols-3"}`}>
        {cards.map((card) => (
          <Card className="border-tec-border/15 bg-tec-field/55 p-4" key={card.label}>
            <span className={`grid h-9 w-9 place-items-center rounded-control bg-tec-panel-strong ${card.tone}`}>{card.icon}</span>
            <p className="mt-3 text-sm font-semibold text-tec-muted">{card.label}</p>
            <p className="mt-1 text-2xl font-bold text-white">{card.value}</p>
            <p className="mt-1 text-xs text-tec-subtle">{card.detail}</p>
          </Card>
        ))}
      </div>
    </section>
  );
}

function DirectorRiskAgendaPanel({ agenda, onOpenOrder }: { agenda: DirectorRiskAgenda; onOpenOrder: (name: string) => void }) {
  const topItems = agenda.items.slice(0, 8);
  const urgencyLabel: Record<DirectorRiskAgenda["items"][number]["urgency"], string> = {
    overdue: "Critico",
    high: "Critico",
    due_today: "Hoje",
    normal: "Hoje",
    scheduled: "Programado",
    low: "Programado",
  };

  return (
    <section className="mt-4 rounded-card border border-tec-border/20 bg-tec-panel p-4" id="executive-risk-agenda">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-xl font-bold text-white">Riscos executivos</h2>
          <p className="mt-1 text-sm text-tec-muted">Operacao herdada mais riscos derivados de estoque, compras, aprovacoes e retiradas.</p>
        </div>
        <span className="rounded-full bg-tec-red/15 px-3 py-1 text-xs font-bold text-tec-red">{agenda.risk_count} risco(s) ativo(s)</span>
      </div>
      {topItems.length ? <div className="divide-y divide-tec-border/15 rounded-control border border-tec-border/15 bg-tec-field/40">
        {topItems.map((item) => (
          <button
            className="flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-tec-field"
            key={item.key}
            onClick={() => item.reference_doctype === "Service Order" && item.reference_name ? onOpenOrder(item.reference_name) : window.location.assign(item.link)}
            type="button"
          >
            <ShieldAlert className={item.urgency === "overdue" || item.urgency === "high" ? "shrink-0 text-tec-red" : "shrink-0 text-tec-amber"} size={18} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-bold text-white">{item.title}</span>
              <span className="mt-0.5 block truncate text-xs text-tec-muted">{item.description}</span>
            </span>
            <span className={`shrink-0 rounded-full px-2 py-1 text-[11px] font-bold ${item.urgency === "overdue" || item.urgency === "high" ? "bg-tec-red/15 text-tec-red" : "bg-tec-amber/15 text-tec-amber"}`}>{urgencyLabel[item.urgency]}</span>
            <ChevronRight className="shrink-0 text-tec-subtle" size={16} />
          </button>
        ))}
      </div> : <p className="rounded-control border border-dashed border-tec-border/25 px-4 py-5 text-sm text-tec-muted">Nenhum risco derivado no momento.</p>}
      {agenda.count > topItems.length ? <p className="mt-3 text-sm text-tec-muted">Mostrando os {topItems.length} mais urgentes de {agenda.count} acoes.</p> : null}
    </section>
  );
}

function DirectorStrategicPanel({
  report,
  period,
  onPeriodChange,
}: {
  report: DirectorStrategicReport;
  period: "7d" | "month";
  onPeriodChange: (period: "7d" | "month") => void;
}) {
  const money = (value: number) => value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  const trendMaximum = Math.max(...report.trend.map((item) => item.revenue), 1);
  const listEmpty = <p className="py-4 text-sm text-tec-muted">Sem dados no periodo.</p>;

  return (
    <section className="mt-4 grid gap-4 xl:grid-cols-2">
      <div className="flex flex-wrap items-center justify-between gap-2 xl:col-span-2">
        <div>
          <h2 className="text-xl font-bold text-white">Indicadores estrategicos</h2>
          <p className="mt-1 text-sm text-tec-muted">Cortes financeiros exclusivos da diretoria.</p>
        </div>
        <div className="flex rounded-control border border-tec-border/25 bg-tec-field p-1">
          {[{ key: "month" as const, label: "Este mes" }, { key: "7d" as const, label: "7 dias" }].map((option) => (
            <button className={`rounded-control px-3 py-1.5 text-xs font-bold transition ${period === option.key ? "bg-tec-orange text-tec-graphite" : "text-tec-muted hover:text-white"}`} key={option.key} onClick={() => onPeriodChange(option.key)} type="button">
              {option.label}
            </button>
          ))}
        </div>
      </div>
      <Card className="border-tec-border/20 bg-tec-panel p-4">
        <div className="mb-4 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-white">Receita por categoria</h2>
            <p className="text-sm text-tec-muted">Hierarquia comercial e de servicos no periodo.</p>
          </div>
          <Tag className="text-tec-orange" size={18} />
        </div>
        {report.categories.length ? <div className="space-y-3">
          {report.categories.map((item) => (
            <div className="flex items-center justify-between gap-3" key={item.category}>
              <span className="min-w-0 truncate text-sm font-semibold text-white">{item.category}</span>
              <span className="shrink-0 text-sm font-bold text-tec-orange">{money(item.revenue)}</span>
            </div>
          ))}
        </div> : listEmpty}
      </Card>

      <Card className="border-tec-border/20 bg-tec-panel p-4">
        <div className="mb-4 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-white">Desempenho tecnico</h2>
            <p className="text-sm text-tec-muted">{report.technician_commissions_enabled ? "OS faturadas, mao de obra e comissoes provisionadas." : "OS faturadas e mao de obra no periodo."}</p>
          </div>
          <UserRound className="text-tec-purple" size={18} />
        </div>
        {report.technicians.length ? <div className="space-y-3">
          {report.technicians.map((item) => (
            <div className="flex items-center justify-between gap-3" key={item.technician}>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">{item.technician}</p>
                <p className="text-xs text-tec-muted">{item.service_orders} OS faturada(s) · MO {money(item.labor_revenue)}</p>
              </div>
              {report.technician_commissions_enabled ? <span className="shrink-0 text-sm font-bold text-tec-purple">{money(item.team_earnings)}</span> : null}
            </div>
          ))}
        </div> : listEmpty}
      </Card>

      <Card className="border-tec-border/20 bg-tec-panel p-4">
        <div className="mb-4 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-white">Maior custo por produto</h2>
            <p className="text-sm text-tec-muted">Custos das saídas faturadas no periodo.</p>
          </div>
          <Package className="text-tec-amber" size={18} />
        </div>
        {report.item_costs.length ? <div className="space-y-3">
          {report.item_costs.map((item) => (
            <div className="flex items-center justify-between gap-3" key={item.item_code}>
              <div className="min-w-0"><p className="truncate text-sm font-semibold text-white">{item.item_name}</p><p className="truncate text-xs text-tec-muted">{item.item_code}</p></div>
              <span className="shrink-0 text-sm font-bold text-tec-amber">{money(item.cost)}</span>
            </div>
          ))}
        </div> : listEmpty}
      </Card>

      <Card className="border-tec-border/20 bg-tec-panel p-4">
        <div className="mb-4 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-white">Maior custo por OS</h2>
            <p className="text-sm text-tec-muted">Pecas usadas em reparos faturados.</p>
          </div>
          <Wrench className="text-tec-red" size={18} />
        </div>
        {report.service_order_costs.length ? <div className="space-y-3">
          {report.service_order_costs.map((item) => (
            <div className="flex items-center justify-between gap-3" key={item.service_order}>
              <span className="text-sm font-semibold text-white">{item.service_order}</span>
              <span className="shrink-0 text-sm font-bold text-tec-red">{money(item.cost)}</span>
            </div>
          ))}
        </div> : listEmpty}
      </Card>

      <Card className="border-tec-border/20 bg-tec-panel p-4 xl:col-span-2">
        <div className="mb-4 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-white">Tendencia de faturamento</h2>
            <p className="text-sm text-tec-muted">{report.period.label}: receita faturada por dia.</p>
          </div>
          <Ticket className="text-tec-blue" size={18} />
        </div>
        {report.trend.length ? <div className="flex h-28 items-end gap-2">
          {report.trend.map((item) => (
            <div className="flex min-w-0 flex-1 flex-col items-center gap-2" key={item.date} title={`${item.date}: ${money(item.revenue)}`}>
              <div className="w-full rounded-t-control bg-tec-blue/75" style={{ height: `${Math.max(8, (item.revenue / trendMaximum) * 88)}px` }} />
              <span className="text-[10px] text-tec-subtle">{item.date.slice(8, 10)}</span>
            </div>
          ))}
        </div> : listEmpty}
      </Card>
    </section>
  );
}

function HomeSectorActions({
  actions,
  heading = "Atalhos do setor",
  onNavigate,
  onStartCheckin,
  subtitle = "Ações frequentes para manter o balcão em movimento.",
}: {
  actions: ActionDefinition[];
  heading?: string;
  onNavigate: (target: NavigationTarget) => void;
  onStartCheckin: () => void;
  subtitle?: string;
}) {
  const shortcuts = actions.slice(0, 4).map((action, index) => ({ action, key: `F${index + 2}` }));

  const runAction = useCallback((action: ActionDefinition) => {
    if (action.opensCheckin) {
      onStartCheckin();
    } else if (action.externalHref) {
      window.open(action.externalHref, "_blank", "noopener,noreferrer");
    } else if (action.target) {
      onNavigate(action.target);
    }
  }, [onNavigate, onStartCheckin]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (
        event.defaultPrevented ||
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement ||
        event.target instanceof HTMLSelectElement
      ) {
        return;
      }
      const shortcut = shortcuts.find((item) => item.key === event.key);
      if (!shortcut) {
        return;
      }
      event.preventDefault();
      runAction(shortcut.action);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [runAction, shortcuts]);

  return (
    <section>
      <div className="mb-3">
        <h2 className="text-xl font-bold text-white">{heading}</h2>
        <p className="mt-1 text-sm text-tec-muted">{subtitle}</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
        {shortcuts.map(({ action, key }) => {
          const ActionIcon = action.icon;
          const highlighted = action.target === "pos";
          return (
            <button
              aria-keyshortcuts={key}
              className={cx(
                "group flex min-h-28 items-center gap-4 rounded-card border p-4 text-left transition",
                highlighted
                  ? "border-tec-orange bg-tec-orange text-tec-ink shadow-glow hover:bg-tec-digital-orange"
                  : "border-tec-border/20 bg-tec-panel hover:border-tec-orange/50 hover:bg-tec-field",
              )}
              key={action.label}
              onClick={() => runAction(action)}
              type="button"
            >
              <span className={cx("grid h-12 w-12 shrink-0 place-items-center rounded-control", highlighted ? "bg-tec-ink/15 text-tec-ink" : "bg-tec-orange/10 text-tec-orange")}>
                <ActionIcon size={25} />
              </span>
              <span className="min-w-0 flex-1">
                <span className={cx("block text-base font-bold", highlighted ? "text-tec-ink" : "text-white")}>{action.label}</span>
                <span className={cx("mt-1 block text-xs", highlighted ? "text-tec-ink/80" : "text-tec-muted")}>{action.detail}</span>
              </span>
              <kbd className={cx("rounded-control border px-2 py-1 text-xs font-bold", highlighted ? "border-tec-ink/25 bg-tec-ink/10 text-tec-ink" : "border-tec-border/20 bg-tec-field text-tec-muted")}>{key}</kbd>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function DashboardPeriodControl({
  filter,
  onChange,
  resultCount,
}: {
  filter: DashboardPeriodFilter;
  onChange: (filter: DashboardPeriodFilter) => void;
  resultCount: number;
}) {
  const updateMode = (mode: DashboardPeriodMode) => {
    onChange({
      fromDate: mode === "custom" ? filter.fromDate : "",
      mode,
      toDate: mode === "custom" ? filter.toDate : "",
    });
  };

  return (
    <div className="mb-4 flex flex-col gap-3 rounded-card border border-tec-border/20 bg-tec-panel/65 p-3 shadow-sm lg:flex-row lg:items-center lg:justify-between">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
          <Clock3 size={18} />
        </span>
        <div>
          <p className="text-sm font-bold text-white">Período do painel</p>
          <p className="text-xs text-tec-muted">{resultCount} atendimentos na fila filtrada</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {DASHBOARD_PERIOD_OPTIONS.map((option) => {
          const selected = filter.mode === option.value;
          return (
            <button
              aria-pressed={selected}
              className={cx(
                "min-h-9 rounded-control border px-3 text-xs font-bold transition",
                selected
                  ? "border-tec-orange bg-tec-orange text-tec-ink shadow-glow"
                  : "border-tec-border/20 bg-tec-field/70 text-tec-subtle hover:border-tec-orange/50 hover:text-tec-text",
              )}
              key={option.value}
              onClick={() => updateMode(option.value)}
              type="button"
            >
              {option.label}
            </button>
          );
        })}
        {filter.mode === "custom" ? (
          <div className="flex flex-wrap items-center gap-2">
            <input
              aria-label="Data inicial do período personalizado"
              className="h-9 rounded-control border border-tec-border/20 bg-tec-field px-3 text-xs font-semibold text-tec-text outline-none focus:border-tec-orange/70"
              onChange={(event) => onChange({ ...filter, fromDate: event.target.value })}
              type="date"
              value={filter.fromDate}
            />
            <span className="text-xs font-semibold text-tec-muted">até</span>
            <input
              aria-label="Data final do período personalizado"
              className="h-9 rounded-control border border-tec-border/20 bg-tec-field px-3 text-xs font-semibold text-tec-text outline-none focus:border-tec-orange/70"
              onChange={(event) => onChange({ ...filter, toDate: event.target.value })}
              type="date"
              value={filter.toDate}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function NavigationContent({
  activeView,
  initialPosBarcode,
  initialRetailBarcode,
  initialServiceOrderStatus,
  canReceiveStock,
  canEditServiceCatalog,
  canEditProductCategories,
	canEditBasicRegistries,
  canViewStoreOperations,
	canAssignTechnician,
	canViewDirectorFinancial,
	 technicianAssignment,
	 activeTechnicians,
	 singleTechnician,
	 commissionsEnabled,
	canManageUsers,
	canOpenSystemSettings,
	 isRestrictedTechnician,
  onInitialPosBarcodeHandled,
  onInitialRetailBarcodeHandled,
  onInitialServiceOrderStatusHandled,
  onRegisterUnknownRetailBarcode,
  initialOrderFlow,
  onInitialOrderFlowHandled,
  onNavigate,
  onNotificationsChanged,
  onOpenServiceOrder,
  onRefreshData,
  onStartCheckin,
  onToast,
  orders,
  serviceOrdersView,
  selectedOrderName,
  setServiceOrdersView,
}: {
  activeView: NavigationTarget;
  canReceiveStock: boolean;
  canEditServiceCatalog: boolean;
  canEditProductCategories: boolean;
	canEditBasicRegistries: boolean;
  canViewStoreOperations: boolean;
	canAssignTechnician: boolean;
	canViewDirectorFinancial: boolean;
	technicianAssignment: BootResponse["features"]["technician_assignment"];
	 activeTechnicians: number;
	 singleTechnician: boolean;
	 commissionsEnabled: boolean;
	canManageUsers: boolean;
	canOpenSystemSettings: boolean;
	 isRestrictedTechnician: boolean;
  initialPosBarcode: PendingPosBarcode | null;
  initialRetailBarcode: PendingRetailBarcode | null;
  initialServiceOrderStatus: QueueFilter | null;
  initialOrderFlow: ServiceOrderFlow | null;
  onInitialPosBarcodeHandled: () => void;
  onInitialRetailBarcodeHandled: () => void;
  onInitialServiceOrderStatusHandled: () => void;
  onRegisterUnknownRetailBarcode: (barcode: string) => void;
  onInitialOrderFlowHandled: () => void;
  onNavigate: (target: NavigationTarget) => void;
  onNotificationsChanged: () => Promise<void>;
  onOpenServiceOrder: (name: string, flow?: ServiceOrderFlow | null) => void;
  onRefreshData: () => void;
  onStartCheckin: () => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  orders: ServiceOrderSummary[];
  serviceOrdersView: ServiceOrdersViewMode;
  selectedOrderName: string | null;
  setServiceOrdersView: (value: ServiceOrdersViewMode) => void;
}) {
  const [serviceOrderFilters, setServiceOrderFilters] = useState<ServiceOrderFilterState>(DEFAULT_SERVICE_ORDER_FILTERS);
  const [serviceOrderListState, setServiceOrderListState] = useState<ServiceOrderListState>({
    count: orders.length,
    items: orders,
    status: "ready",
  });
  const [serviceOrderStats, setServiceOrderStats] = useState<ServiceOrderStatBarResponse["items"]>([]);
  const serviceOrderQueryParams = useMemo(() => toServiceOrderQueryParams(serviceOrderFilters, 100), [serviceOrderFilters]);
  const serviceOrderSourceOrders = serviceOrderListState.status === "ready" ? serviceOrderListState.items : orders;
  const serviceOrderScreenOrders = filterOrdersForServiceOrderScreen(serviceOrderSourceOrders, serviceOrderFilters);
  const serviceOrderResultCount = serviceOrderScreenOrders.length;

  useEffect(() => {
    if (activeView !== "service-orders" || !initialServiceOrderStatus) {
      return;
    }
    setServiceOrderFilters({ ...DEFAULT_SERVICE_ORDER_FILTERS, status: initialServiceOrderStatus });
    onInitialServiceOrderStatusHandled();
  }, [activeView, initialServiceOrderStatus, onInitialServiceOrderStatusHandled]);

  useEffect(() => {
    if (activeView !== "service-orders") {
      return;
    }

    let cancelled = false;
    setServiceOrderListState((current) => (current.status === "ready" ? current : { status: "loading" }));
    serviceOrders
      .list(serviceOrderQueryParams)
      .then((response) => {
        if (!cancelled) {
          setServiceOrderListState({ count: response.count, items: response.items, status: "ready" });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setServiceOrderListState({
            message: error instanceof Error ? error.message : "Falha ao filtrar ordens de serviço.",
            status: "error",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeView, serviceOrderQueryParams]);

  useEffect(() => {
    if (activeView === "service-orders") {
      void serviceOrders.statBar().then((response) => setServiceOrderStats(response.items)).catch(() => setServiceOrderStats([]));
    }
  }, [activeView]);

  if (activeView === "service-order-detail") {
    return selectedOrderName ? (
      <ServiceOrderDetail
        initialFlow={initialOrderFlow}
		isRestrictedTechnician={isRestrictedTechnician}
		canViewDirectorFinancial={canViewDirectorFinancial}
        name={selectedOrderName}
        onBack={() => onNavigate("service-orders")}
        onInitialFlowHandled={onInitialOrderFlowHandled}
        onToast={onToast}
      />
    ) : (
      <Card className="p-5 text-sm text-tec-subtle">Selecione uma OS na fila para abrir o detalhe.</Card>
    );
  }

  if (activeView === "mesa-flow") {
    return (
      <MesaFlowBoard
		canAssignTechnician={canAssignTechnician}
        canViewStoreOperations={canViewStoreOperations}
        isRestrictedTechnician={isRestrictedTechnician}
		technicianAssignment={technicianAssignment}
		activeTechnicians={activeTechnicians}
        onOpenOrder={onOpenServiceOrder}
        onToast={onToast}
      />
    );
  }

  if (activeView === "service-orders") {
    const serviceOrderFilterBar = (
      <ServiceOrderFilterBar
        filters={serviceOrderFilters}
        onChange={setServiceOrderFilters}
        resultCount={serviceOrderResultCount}
      />
    );

    return (
      <div className="tp-layout-grid">
        <section className="min-w-0 space-y-4">
          <StatBar
            items={serviceOrderStats.map((item) => ({ ...item, ...getStatBarVisual("service_orders", item.key) }))}
            onSelect={(status) => setServiceOrderFilters((current) => ({ ...current, status: status === "total" ? "all" : status as QueueFilter }))}
          />
          {canViewStoreOperations && !singleTechnician ? <TechnicianWorkloadPanel /> : null}
          {serviceOrderListState.status === "error" ? (
            <Card className="p-4 text-sm font-semibold text-tec-red">{serviceOrderListState.message}</Card>
          ) : null}
          {serviceOrdersView === "kanban" ? (
            <ServiceOrderKanban
              filterBar={serviceOrderFilterBar}
              filters={serviceOrderFilters}
              onChanged={onRefreshData}
              onOpenOrder={onOpenServiceOrder}
              onOpenWorkflowFlow={onOpenServiceOrder}
              onShowList={() => setServiceOrdersView("list")}
              onToast={onToast}
            />
          ) : (
            <OperationsTable
              filterBar={serviceOrderFilterBar}
              onOpenOrder={(name) => onOpenServiceOrder(name)}
				onRefresh={onRefreshData}
              onToast={onToast}
              orders={serviceOrderScreenOrders}
              presentation={serviceOrdersView === "grid" ? "grid" : "list"}
              showQuickStatusFilters={false}
              title="Lista de OS"
            />
          )}
        </section>
        <aside className="space-y-4">
          <ActionPanel
            actions={isRestrictedTechnician ? [
              { icon: ClipboardCheck, label: "Minhas OS", detail: "Fila técnica", target: "service-orders" },
              { icon: Boxes, label: "Peças de reparo", detail: "Consultar disponibilidade", target: "repair-parts" },
            ] : [
              { icon: Wrench, label: "Nova OS", detail: "Check-in do balcão", opensCheckin: true },
              { icon: SearchIcon, label: "Buscar cliente", detail: "Localizar cadastro", target: "customers" },
              { icon: Smartphone, label: "Aparelhos", detail: "Buscar IMEI", target: "devices" },
            ]}
            onNavigate={onNavigate}
            onStartCheckin={onStartCheckin}
            title="Atalhos de OS"
          />
        </aside>
      </div>
    );
  }

	if (activeView === "quotes-crm") {
		return <QuotesCrmScreen onOpenOrder={onOpenServiceOrder} onToast={onToast} />;
	}

	if (activeView === "warranties") {
		return <WarrantyScreen onOpenOrder={onOpenServiceOrder} onStartCheckin={onStartCheckin} onToast={onToast} />;
	}

  if (activeView === "approval-requests") {
    return <ApprovalRequestsPanel onToast={onToast} />;
  }

  if (activeView === "notifications") {
    return <NotificationHistoryScreen onNotificationsChanged={onNotificationsChanged} onOpenServiceOrder={onOpenServiceOrder} onToast={onToast} />;
  }

  if (activeView === "user-management") {
    return canManageUsers ? <UserManagementScreen onToast={onToast} /> : <Card className="p-5 text-sm font-semibold text-tec-red">Você não possui acesso à gestão de pessoas.</Card>;
  }

  if (activeView === "administration") {
    return canManageUsers ? <AdministrativeCenterScreen canOpenSystemSettings={canOpenSystemSettings} canViewDirectorFinancial={canViewDirectorFinancial} onNavigate={onNavigate} onToast={onToast} /> : <Card className="p-5 text-sm font-semibold text-tec-red">Você não possui acesso à Administração.</Card>;
  }

  if (activeView === "administration-settings") {
    return canManageUsers ? <AdministrationSettingsScreen activeTechnicians={activeTechnicians} onBack={() => onNavigate("administration")} onToast={onToast} /> : <Card className="p-5 text-sm font-semibold text-tec-red">Você não possui acesso às configurações.</Card>;
  }

  if (activeView === "my-earnings" && commissionsEnabled) {
    return <MyEarningsScreen onOpenServiceOrder={onOpenServiceOrder} />;
  }

  if (activeView === "part-requests") {
    return <PartRequestsScreen onOpenServiceOrder={onOpenServiceOrder} onToast={onToast} />;
  }

  if (activeView === "cash-statement") {
    return <CashStatementScreen onToast={onToast} />;
  }

  if (activeView === "customers") {
      return <CustomerLookup canEdit={canEditBasicRegistries} onToast={onToast} />;
  }

  if (activeView === "devices") {
    return <DeviceLookup canEdit={canEditBasicRegistries} onToast={onToast} />;
  }

  if (activeView === "services") {
    return <ServiceCatalogScreen canEdit={canEditServiceCatalog} onToast={onToast} />;
  }

  if (activeView === "service-categories") {
    return <ServiceCategoriesScreen canEdit={canEditServiceCatalog} onToast={onToast} />;
  }

  if (activeView === "product-categories") {
    return <ProductCategoryScreen canEdit={canEditProductCategories} onToast={onToast} />;
  }

  if (activeView === "product-attributes") {
    return <ProductVariantAttributesScreen canEdit={canEditProductCategories} onToast={onToast} />;
  }

  if (activeView === "trade-ins") {
    return <TradeLookup onToast={onToast} />;
  }

  if (activeView === "parts-stock" || activeView === "repair-parts" || activeView === "commercial-products" || activeView === "used-devices") {
    return <StockLookup canEditRepairParts={canEditBasicRegistries} canManageVariantProducts={canEditProductCategories} canReceiveStock={canReceiveStock} initialBarcode={initialRetailBarcode} onInitialBarcodeHandled={onInitialRetailBarcodeHandled} onToast={onToast} scope={activeView} />;
  }

  if (activeView === "pos") {
    return <PosScreen initialBarcode={initialPosBarcode} onInitialBarcodeHandled={onInitialPosBarcodeHandled} onRegisterUnknownBarcode={onRegisterUnknownRetailBarcode} onToast={onToast} />;
  }

  return <SalesLookup onNavigate={onNavigate} />;
}

const MESA_FLOW_QUEUES = [
  { detail: "Entradas que precisam de conferência e encaminhamento.", states: ["Entrada criada"], title: "Receber e conferir" },
  { detail: "Aparelhos na bancada aguardando avaliação técnica.", states: ["Em diagnóstico", "Em diagnostico"], title: "Diagnosticar" },
  { detail: "Diagnósticos concluídos com responsável explícito pela precificação.", states: ["Diagnosticado — aguardando orçamento"], title: "Precificar" },
  { detail: "Orçamentos que precisam de envio, retorno ou decisão.", states: ["Aguardando aprovação", "Aprovado"], title: "Orçamento" },
  { detail: "OS paradas por disponibilidade de componente.", states: ["Aguardando peça", "Aguardando peca"], title: "Peças" },
  { detail: "Execução, baixa de peça e teste final.", states: ["Em reparo", "Teste final"], title: "Executar e testar" },
  { detail: "Aparelhos para devolver ao cliente, com ou sem reparo.", states: ["Pronto para retirada", "Reprovado", "Orçamento expirado", "Sem conserto"], title: "Retirada" },
] as const;

function MesaFlowBoard({
	activeTechnicians,
	canAssignTechnician,
  canViewStoreOperations,
  isRestrictedTechnician,
	technicianAssignment,
  onOpenOrder,
  onToast,
}: {
	activeTechnicians: number;
	canAssignTechnician: boolean;
  canViewStoreOperations: boolean;
  isRestrictedTechnician: boolean;
	technicianAssignment: BootResponse["features"]["technician_assignment"];
  onOpenOrder: (name: string) => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
}) {
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "ready"; items: ServiceOrderSummary[] }
    | { status: "error"; message: string }
  >({ status: "loading" });
	const [unassigned, setUnassigned] = useState<ServiceOrderSummary[]>([]);
	const [technicians, setTechnicians] = useState<TechnicianWorkloadItem[]>([]);
	const [preferredTechnician, setPreferredTechnician] = useState("");

  const load = useCallback(async () => {
    setState((current) => current.status === "ready" ? current : { status: "loading" });
    try {
      // The endpoint scopes the response to the logged-in role; the Mesa never broadens that query in React.
      const response = await serviceOrders.list({ limit: 100 });
      setState({ status: "ready", items: response.items });
		if (canAssignTechnician || (isRestrictedTechnician && (technicianAssignment.mode === "Pull" || activeTechnicians === 1))) {
			const available = await serviceOrders.listUnassigned(100);
			setUnassigned(available.items);
		}
		if (canAssignTechnician && activeTechnicians >= 2) {
			const workload = await balcao.getTechnicianWorkload();
			setTechnicians(workload.items);
		}
    } catch (caught) {
      setState({ status: "error", message: caught instanceof Error ? caught.message : "Não foi possível carregar a Mesa." });
    }
  }, [activeTechnicians, canAssignTechnician, isRestrictedTechnician, technicianAssignment.mode]);

  useEffect(() => {
    void load();
  }, [load]);

  const queues = useMemo(() => {
    const items = state.status === "ready" ? state.items : [];
    return MESA_FLOW_QUEUES.map((queue) => ({
      ...queue,
      items: items.filter((item) => queue.states.includes((item.workflow_state ?? "") as never)),
    }));
  }, [state]);

  const total = queues.reduce((count, queue) => count + queue.items.length, 0);
  const overdue = queues.flatMap((queue) => queue.items).filter((item) => item.stage_clock?.is_overdue).length;
	const unassignedOverdue = unassigned.filter((item) => item.unassigned_overdue).length;

  return (
    <div className="space-y-5">
      <section className="flex flex-col gap-4 rounded-card border border-tec-border/15 bg-tec-panel-strong/55 p-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-tec-orange">Mesa / Fluxo</p>
          <h1 className="tp-display mt-1 text-3xl font-bold text-white">{isRestrictedTechnician ? "Sua bancada, por próximo passo" : "A operação, organizada por próxima ação"}</h1>
          <p className="mt-2 max-w-3xl text-sm text-tec-subtle">
            {isRestrictedTechnician
              ? "Somente as OS atribuídas a você. Abra uma tarefa para executar a etapa técnica e avançar pelo workflow."
              : "Cada fila mostra o que a loja precisa fazer agora. As permissões e aprovações continuam sendo decididas pelo motor."}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="rounded-control border border-tec-border/15 bg-tec-field px-3 py-2 text-right">
            <span className="block text-xs font-bold text-tec-muted">Na Mesa</span>
            <span className="text-lg font-bold text-white">{total} OS</span>
          </div>
          {overdue ? <div className="rounded-control border border-tec-red/30 bg-tec-red/10 px-3 py-2 text-right"><span className="block text-xs font-bold text-tec-red">Atrasadas</span><span className="text-lg font-bold text-tec-red">{overdue}</span></div> : null}
		  {unassigned.length ? <div className={cx("rounded-control border px-3 py-2 text-right", unassignedOverdue ? "border-tec-red/30 bg-tec-red/10" : "border-tec-amber/30 bg-tec-amber/10")}><span className={cx("block text-xs font-bold", unassignedOverdue ? "text-tec-red" : "text-tec-amber")}>Sem técnico</span><span className={cx("text-lg font-bold", unassignedOverdue ? "text-tec-red" : "text-tec-amber")}>{unassigned.length}</span></div> : null}
          <Button icon={<RefreshCw size={17} />} onClick={() => void load()} variant="secondary">Atualizar</Button>
        </div>
      </section>

      {!canViewStoreOperations && !isRestrictedTechnician ? <Card className="border-tec-amber/30 bg-tec-amber/5 p-4 text-sm text-tec-amber">A Mesa respeita o escopo do seu papel. Algumas filas podem não estar disponíveis para este acesso.</Card> : null}
      {state.status === "error" ? <Card className="border-tec-red/30 p-5 text-sm font-semibold text-tec-red">{state.message}</Card> : null}
      {state.status === "loading" ? <Card className="p-6"><div className="h-9 w-9 animate-spin rounded-full border-2 border-tec-orange border-t-transparent" /><p className="mt-3 text-sm font-semibold text-tec-subtle">Organizando a Mesa...</p></Card> : null}

	  {state.status === "ready" && canAssignTechnician && activeTechnicians >= 2 ? <MesaTechnicianWorkloadBoard items={technicians} mode={technicianAssignment.mode} onAssign={(technician) => {
        setPreferredTechnician(technician);
        window.requestAnimationFrame(() => document.getElementById("mesa-sem-tecnico")?.scrollIntoView({ behavior: "smooth", block: "center" }));
      }} /> : null}

      {state.status === "ready" ? <div className="grid gap-4 xl:grid-cols-2 2xl:grid-cols-3">
		{unassigned.length ? <MesaAssignmentQueue canAssignTechnician={canAssignTechnician && technicianAssignment.mode === "Dispatch"} canClaim={isRestrictedTechnician && (technicianAssignment.mode === "Pull" || activeTechnicians === 1)} canIntervene={canAssignTechnician && technicianAssignment.mode === "Pull"} items={unassigned} onChanged={load} onOpenOrder={onOpenOrder} onToast={onToast} preferredTechnician={preferredTechnician} technicians={technicians} /> : null}
        {queues.map((queue) => <MesaFlowQueue canAssignTechnician={canAssignTechnician} key={queue.title} onChanged={load} onOpenOrder={onOpenOrder} onToast={onToast} queue={queue} technicians={technicians} />)}
      </div> : null}
    </div>
  );
}

function MesaFlowQueue({
	canAssignTechnician,
	onChanged,
  onOpenOrder,
  onToast,
  queue,
	technicians,
}: {
	canAssignTechnician: boolean;
	onChanged: () => Promise<void>;
  onOpenOrder: (name: string) => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  queue: (typeof MESA_FLOW_QUEUES)[number] & { items: ServiceOrderSummary[] };
	technicians: TechnicianWorkloadItem[];
}) {
  const visibleItems = queue.items.slice(0, 8);
  return (
    <Card className="flex min-h-64 flex-col overflow-hidden p-0">
      <header className="border-b border-tec-border/15 bg-tec-field/35 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-white">{queue.title}</h2>
            <p className="mt-1 text-xs leading-relaxed text-tec-muted">{queue.detail}</p>
          </div>
          <span className="rounded-full bg-tec-orange/15 px-2.5 py-1 text-xs font-bold text-tec-orange">{queue.items.length}</span>
        </div>
      </header>
      <div className="flex-1 space-y-2 p-3">
        {visibleItems.map((order) => <MesaFlowOrderCard canAssignTechnician={canAssignTechnician} key={order.name} onChanged={onChanged} onOpenOrder={onOpenOrder} onToast={onToast} order={order} technicians={technicians} />)}
        {!visibleItems.length ? <div className="grid min-h-28 place-items-center rounded-control border border-dashed border-tec-border/20 px-4 text-center text-sm text-tec-muted">Nenhuma OS nesta etapa.</div> : null}
      </div>
      {queue.items.length > visibleItems.length ? <footer className="border-t border-tec-border/15 p-3 text-center text-xs font-bold text-tec-muted">+{queue.items.length - visibleItems.length} OS nesta fila</footer> : null}
    </Card>
  );
}

function MesaFlowOrderCard({ canAssignTechnician, onChanged, onOpenOrder, onToast, order, technicians }: { canAssignTechnician: boolean; onChanged: () => Promise<void>; onOpenOrder: (name: string) => void; onToast: (message: string, tone?: ToastState["tone"]) => void; order: ServiceOrderSummary; technicians: TechnicianWorkloadItem[] }) {
  const next = nextActionForOrder(order);
  const blockerEntry = Object.entries(order.workflow_blockers).find(([target]) => order.workflow_transitions.some((action) => action.next_state === target));
  const requestable = blockerEntry && order.workflow_requestable_transitions.includes(blockerEntry[0]);
  const buttonLabel = requestable ? "Abrir para solicitar aprovação" : `Abrir · ${next.label}`;

  return (
    <article className={cx("rounded-control border border-tec-border/15 bg-tec-field/45 p-3 transition hover:border-tec-orange/45", order.stage_clock?.is_overdue && "border-tec-red/45 bg-tec-red/5")}>
      <div className="flex items-start justify-between gap-3">
        <button className="min-w-0 text-left" onClick={() => onOpenOrder(order.name)} type="button">
          <span className="block truncate text-sm font-bold text-white">{order.name}</span>
          <span className="mt-0.5 block truncate text-xs text-tec-subtle">{order.customer ?? "Cliente não informado"}</span>
        </button>
        {order.stage_clock?.is_overdue ? <span className="shrink-0 text-[11px] font-bold text-tec-red">Atrasada</span> : null}
      </div>
      <p className="mt-3 line-clamp-2 text-xs leading-relaxed text-tec-muted">{compactServiceOrderDescription(order.reported_defect)}</p>
	  <div className="mt-3 grid gap-1 text-xs text-tec-muted sm:grid-cols-2"><span>Técnico: <strong className="text-tec-subtle">{order.technician ?? "Sem técnico"}</strong></span><span>Recebido por: <strong className="text-tec-subtle">{order.attendant ?? "Não informado"}</strong></span></div>
	  {order.pricing_responsibility ? <p className="mt-2 text-xs font-bold text-tec-amber">Precificação com: {order.pricing_responsibility}</p> : null}
      <div className="mt-3 rounded-control bg-tec-panel px-3 py-2">
        <span className="block text-[10px] font-bold uppercase tracking-wide text-tec-muted">Próximo passo</span>
        <span className="mt-0.5 block text-sm font-bold text-tec-text">{next.label}</span>
        {blockerEntry ? <span className={cx("mt-1 block text-xs", requestable ? "text-tec-amber" : "text-tec-muted")}>{blockerEntry[1]}</span> : null}
      </div>
      <Button className="mt-3 w-full" icon={<ArrowRight size={16} />} onClick={() => {
        if (blockerEntry && !requestable) onToast(blockerEntry[1], "error");
        onOpenOrder(order.name);
      }} variant={requestable ? "secondary" : "primary"}>{buttonLabel}</Button>
	  {canAssignTechnician && order.technician ? <TechnicianAssignmentControl current={order.technician} mode="transfer" onChanged={onChanged} onToast={onToast} order={order.name} technicians={technicians} /> : null}
    </article>
  );
}

function MesaTechnicianWorkloadBoard({ items, mode, onAssign }: { items: TechnicianWorkloadItem[]; mode: "Pull" | "Dispatch"; onAssign: (technician: string) => void }) {
  const totals = items.reduce((total, item) => ({
    active_orders: total.active_orders + item.active_orders,
    in_diagnosis: total.in_diagnosis + item.in_diagnosis,
    waiting_part: total.waiting_part + item.waiting_part,
    overdue: total.overdue + item.overdue,
  }), { active_orders: 0, in_diagnosis: 0, waiting_part: 0, overdue: 0 });

  return <Card className="p-5">
    <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
      <div>
        <p className="text-xs font-bold uppercase tracking-wide text-tec-orange">Gestão de bancada</p>
        <h2 className="mt-1 text-xl font-bold text-white">Carga da equipe</h2>
        <p className="mt-1 text-sm text-tec-muted">{mode === "Pull" ? "Pull ativo: o técnico assume normalmente; atribuição do gestor é uma exceção auditada." : "Use a carga real antes de distribuir uma OS."}</p>
      </div>
      <span className={cx("rounded-full px-3 py-1.5 text-xs font-bold", mode === "Pull" ? "bg-tec-blue/15 text-tec-blue" : "bg-tec-orange/15 text-tec-orange")}>Modo {mode}</span>
    </div>
    <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      {[["OS ativas", totals.active_orders, "text-white"], ["Em diagnóstico", totals.in_diagnosis, "text-tec-blue"], ["Aguardando peça", totals.waiting_part, "text-tec-amber"], ["Atrasadas", totals.overdue, totals.overdue ? "text-tec-red" : "text-tec-success"]].map(([label, value, tone]) => <div className="rounded-control border border-tec-border/15 bg-tec-field/55 p-3" key={String(label)}><span className="block text-xs font-bold text-tec-muted">{label}</span><strong className={cx("mt-1 block text-xl", String(tone))}>{value}</strong></div>)}
    </div>
    {!items.length ? <p className="mt-4 rounded-control border border-dashed border-tec-border/20 p-3 text-sm text-tec-muted">Nenhuma OS ativa atribuída a técnico.</p> : <div className="mt-4 grid gap-3 md:grid-cols-2 2xl:grid-cols-3">{items.map((item) => <article className={cx("rounded-control border bg-tec-field/55 p-4", item.overdue ? "border-tec-red/35" : "border-tec-border/15")} key={item.technician}>
      <div className="flex items-start justify-between gap-3"><div className="min-w-0"><strong className="block truncate text-sm text-white" title={item.technician_name}>{item.technician_name}</strong><span className="mt-1 block text-xs text-tec-muted">{item.active_orders} OS ativas</span></div>{item.overdue ? <span className="shrink-0 rounded-full bg-tec-red/15 px-2 py-1 text-xs font-bold text-tec-red">{item.overdue} atrasada{item.overdue > 1 ? "s" : ""}</span> : null}</div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs"><span className="rounded-control bg-tec-panel px-2 py-2 text-tec-muted"><strong className="block text-sm text-tec-text">{item.in_diagnosis}</strong>diagnóstico</span><span className="rounded-control bg-tec-panel px-2 py-2 text-tec-muted"><strong className="block text-sm text-tec-text">{item.waiting_part}</strong>peças</span><span className="rounded-control bg-tec-panel px-2 py-2 text-tec-muted"><strong className="block text-sm text-tec-text">{item.active_orders}</strong>em curso</span></div>
      <p className="mt-3 text-xs text-tec-muted">Capacidade: <strong className="text-tec-subtle">limite não configurado</strong></p>
      <Button className="mt-3 w-full" onClick={() => onAssign(item.technician)} variant="secondary">{mode === "Pull" ? "Intervir e atribuir" : "Distribuir OS"}</Button>
    </article>)}</div>}
  </Card>;
}

function MesaAssignmentQueue({ canAssignTechnician, canClaim, canIntervene, items, onChanged, onOpenOrder, onToast, preferredTechnician, technicians }: { canAssignTechnician: boolean; canClaim: boolean; canIntervene: boolean; items: ServiceOrderSummary[]; onChanged: () => Promise<void>; onOpenOrder: (name: string) => void; onToast: (message: string, tone?: ToastState["tone"]) => void; preferredTechnician: string; technicians: TechnicianWorkloadItem[] }) {
  const managerAction = canAssignTechnician || canIntervene;
  return <section id="mesa-sem-tecnico">
  <Card className={cx("flex min-h-64 flex-col overflow-hidden p-0", items.some((item) => item.unassigned_overdue) && "border-tec-red/45")}>
    <header className="border-b border-tec-amber/25 bg-tec-amber/5 p-4"><div className="flex justify-between gap-3"><div><h2 className="text-lg font-bold text-white">{canClaim ? "Disponíveis para assumir" : "Sem técnico"}</h2><p className="mt-1 text-xs text-tec-muted">{canClaim ? "Escolha uma OS livre e assuma a responsabilidade." : canIntervene ? "Pull ativo. Intervenha somente por urgência, ausência ou backlog; a justificativa é obrigatória." : "Distribua as OS antes que parem na entrada."}</p></div><span className="rounded-full bg-tec-amber/15 px-2.5 py-1 text-xs font-bold text-tec-amber">{items.length}</span></div></header>
    <div className="flex-1 space-y-2 p-3">{items.slice(0, 8).map((order) => <article className={cx("rounded-control border bg-tec-field/45 p-3", order.unassigned_overdue ? "border-tec-red/45" : "border-tec-border/15")} key={order.name}><button className="text-left" onClick={() => onOpenOrder(order.name)} type="button"><strong className="block text-sm text-white">{order.name}</strong><span className="text-xs text-tec-muted">{order.customer ?? "Cliente não informado"} · {order.customer_device ?? "Aparelho não informado"}</span></button><p className="mt-2 line-clamp-2 text-xs text-tec-muted">{compactServiceOrderDescription(order.reported_defect)}</p><div className="mt-2 flex justify-between gap-2 text-xs"><span className="text-tec-muted">Prioridade: {order.priority ?? "Normal"}</span>{order.unassigned_overdue ? <strong className="text-tec-red">{order.unassigned_waiting_hours}h úteis</strong> : <span className="text-tec-muted">Sem técnico</span>}</div>{canClaim ? <ClaimServiceOrderButton onChanged={onChanged} onToast={onToast} order={order.name} /> : null}{managerAction ? <TechnicianAssignmentControl mode={canIntervene ? "intervention" : "assign"} onChanged={onChanged} onToast={onToast} order={order.name} preferredTechnician={preferredTechnician} technicians={technicians} /> : null}</article>)}</div>
  </Card>
  </section>;
}

function ClaimServiceOrderButton({ onChanged, onToast, order }: { onChanged: () => Promise<void>; onToast: (message: string, tone?: ToastState["tone"]) => void; order: string }) {
  const [busy, setBusy] = useState(false);
  return <Button className="mt-3 w-full" disabled={busy} onClick={() => { setBusy(true); void serviceOrders.claim(order).then(() => { onToast("OS assumida por você.", "success"); return onChanged(); }).catch((error) => onToast(error instanceof Error ? error.message : "Não foi possível assumir a OS.", "error")).finally(() => setBusy(false)); }}>{busy ? "Assumindo..." : "Assumir"}</Button>;
}

function TechnicianAssignmentControl({ current, mode, onChanged, onToast, order, preferredTechnician = "", technicians }: { current?: string; mode: "assign" | "intervention" | "transfer"; onChanged: () => Promise<void>; onToast: (message: string, tone?: ToastState["tone"]) => void; order: string; preferredTechnician?: string; technicians: TechnicianWorkloadItem[] }) {
  const [technician, setTechnician] = useState("");
  const [observation, setObservation] = useState("");
  const [busy, setBusy] = useState(false);
  const requiresObservation = mode === "transfer" || mode === "intervention";
  const options = technicians.filter((item) => item.technician !== current);
  useEffect(() => { if (preferredTechnician && preferredTechnician !== current) setTechnician(preferredTechnician); }, [current, preferredTechnician]);
  const selectLabel = mode === "transfer" ? "Novo técnico" : mode === "intervention" ? "Técnico para a intervenção" : "Técnico para atribuir";
  const placeholder = mode === "transfer" ? "Motivo da transferência (obrigatório)" : "Justificativa da intervenção (obrigatória)";
  const submitLabel = mode === "transfer" ? "Confirmar transferência" : mode === "intervention" ? "Confirmar intervenção" : "Atribuir";
  return <div className="mt-3 space-y-2 border-t border-tec-border/15 pt-3"><select aria-label={selectLabel} className="tp-input" onChange={(event) => setTechnician(event.target.value)} value={technician}><option value="">{mode === "transfer" ? "Transferir para..." : "Escolher técnico"}</option>{options.map((item) => <option key={item.technician} value={item.technician}>{item.technician_name || item.technician}</option>)}</select>{requiresObservation && technician ? <input className="tp-input" onChange={(event) => setObservation(event.target.value)} placeholder={placeholder} value={observation} /> : null}<Button className="w-full" disabled={busy || !technician || (requiresObservation && !observation.trim())} onClick={() => { setBusy(true); const action = mode === "transfer" ? serviceOrders.transfer(order, technician, observation) : serviceOrders.assign(order, technician, observation); void action.then(() => { onToast(mode === "transfer" ? "OS transferida." : mode === "intervention" ? "Intervenção registrada e técnico atribuído." : "Técnico atribuído.", "success"); setTechnician(""); setObservation(""); return onChanged(); }).catch((error) => onToast(error instanceof Error ? error.message : "Não foi possível alterar o técnico.", "error")).finally(() => setBusy(false)); }} variant="secondary">{busy ? "Salvando..." : submitLabel}</Button></div>;
}

function ServiceOrderFilterBar({
  filters,
  onChange,
  resultCount,
}: {
  filters: ServiceOrderFilterState;
  onChange: (filters: ServiceOrderFilterState) => void;
  resultCount: number;
}) {
  const updatePeriodMode = (mode: DashboardPeriodMode) => {
    onChange({
      ...filters,
      period: {
        fromDate: mode === "custom" ? filters.period.fromDate : "",
        mode,
        toDate: mode === "custom" ? filters.period.toDate : "",
      },
    });
  };
  const resetFilters = () => onChange(DEFAULT_SERVICE_ORDER_FILTERS);
  return (
    <LayeredFilters
      active={filters.status}
      filters={QUEUE_FILTERS.map((filter) => ({ key: filter.value, label: filter.label }))}
      onClear={resetFilters}
      onSelect={(status) => onChange({ ...filters, status: status as QueueFilter })}
      onSecondarySelect={(mode) => updatePeriodMode(mode as DashboardPeriodMode)}
      secondaryActive={filters.period.mode === "none" ? undefined : filters.period.mode}
      secondaryFilters={DASHBOARD_PERIOD_OPTIONS.map((option) => ({ key: option.value, label: option.label }))}
      primary={<>
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="min-w-0 flex-1 space-y-3">
          <label className="relative block min-w-0">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tec-muted" size={17} />
            <input
              className="h-11 w-full rounded-control border border-tec-border/20 bg-tec-field pl-10 pr-3 text-sm font-medium text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70"
              onChange={(event) => onChange({ ...filters, query: event.target.value })}
              placeholder="Buscar OS, cliente, IMEI, aparelho ou defeito..."
              type="search"
              value={filters.query}
            />
          </label>

            <div className="flex flex-wrap items-center gap-3 text-xs font-semibold text-tec-muted">
              <span>{resultCount} OS no recorte</span>
				{filters.period.mode === "none"
					? <span>Recorte padrão: aparelhos na loja · sai somente na retirada</span>
					: <span>Histórico pelo período selecionado · inclui retiradas</span>}
            </div>
			<p className="pt-1 text-xs font-bold uppercase tracking-wide text-tec-subtle">Status da OS</p>
          </div>
        </div>
      </>}
    >
				<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
					{filters.period.mode === "custom" ? <div className="sm:col-span-2 xl:col-span-3">
						<span className="mb-2 inline-flex items-center gap-2 text-xs font-semibold text-tec-muted"><Clock3 size={14} />Periodo personalizado</span>
						<div className="flex flex-wrap items-center gap-2">
							<input aria-label="Data inicial do filtro de OS" className="h-9 rounded-control border border-tec-border/20 bg-tec-field px-3 text-xs font-semibold text-tec-text outline-none focus:border-tec-orange/70" onChange={(event) => onChange({ ...filters, period: { ...filters.period, fromDate: event.target.value } })} type="date" value={filters.period.fromDate} />
							<span className="text-xs font-semibold text-tec-muted">ate</span>
							<input aria-label="Data final do filtro de OS" className="h-9 rounded-control border border-tec-border/20 bg-tec-field px-3 text-xs font-semibold text-tec-text outline-none focus:border-tec-orange/70" onChange={(event) => onChange({ ...filters, period: { ...filters.period, toDate: event.target.value } })} type="date" value={filters.period.toDate} />
						</div>
					</div> : null}
					<label className="text-xs font-bold text-tec-subtle">
						Prioridade
						<select className="tp-input mt-1 w-full" onChange={(event) => onChange({ ...filters, priority: event.target.value as ServiceOrderFilterState["priority"] })} value={filters.priority}>
							<option value="all">Todas</option>
							<option value="Alta">Alta</option>
							<option value="Media">Média</option>
							<option value="Normal">Normal</option>
						</select>
					</label>
					<label className="text-xs font-bold text-tec-subtle">
						Atribuição técnica
						<select className="tp-input mt-1 w-full" onChange={(event) => onChange({ ...filters, assignment: event.target.value as ServiceOrderFilterState["assignment"] })} value={filters.assignment}>
							<option value="all">Todas as OS</option>
							<option value="assigned">Com técnico atribuído</option>
							<option value="unassigned">Sem técnico atribuído</option>
						</select>
					</label>
				</div>
    </LayeredFilters>
  );
}

function OperationsTable({
  filterBar,
  onOpenOrder,
	onRefresh,
  onToast,
  onShowAll,
  orders,
  presentation = "list",
  showQuickStatusFilters = true,
  title,
}: {
  filterBar?: ReactNode;
  onOpenOrder: (name: string) => void;
	onRefresh?: () => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  onShowAll?: () => void;
  orders: ServiceOrderSummary[];
  presentation?: ListPresentation;
  showQuickStatusFilters?: boolean;
  title: string;
}) {
  const [activeFilter, setActiveFilter] = useState<QueueFilter>("all");
  const [searchOpen, setSearchOpen] = useState(false);
  const [tableQuery, setTableQuery] = useState("");
  const [movingOrder, setMovingOrder] = useState<string | null>(null);
  const [moveApproval, setMoveApproval] = useState<{ name: string; targetState: string; requestType: "service_order_move" | "billed_service_order_cancel" } | null>(null);
  const [visibleCount, setVisibleCount] = useState(LIST_PAGE_SIZE);

  async function handleQuickMove(row: ServiceOrderSummary, action: ServiceOrderWorkflowAction) {
    if (["Aprovado", "Reprovado", "Entregue"].includes(action.next_state)) {
      onOpenOrder(row.name);
      onToast("Esta etapa exige o fluxo completo da OS. Abra o detalhe para concluir.");
      return;
    }
    setMovingOrder(row.name);
    try {
      const result = await serviceOrders.move(row.name, action.next_state);
      onToast(result.changed ? `OS ${row.name} movida para ${result.item.workflow_state}.` : `OS ${row.name} já estava nesta etapa.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Transição recusada pelo workflow.";
      if (message.includes("OS faturada") && action.next_state === "Cancelado") {
        setMoveApproval({ name: row.name, targetState: action.next_state, requestType: "billed_service_order_cancel" });
      } else if (message.includes("Seu papel não permite mover")) {
        setMoveApproval({ name: row.name, targetState: action.next_state, requestType: "service_order_move" });
      } else {
        onToast(message, "error");
      }
    } finally {
      setMovingOrder(null);
    }
  }
  const visibleOrders = useMemo(() => {
    const effectiveQuery = filterBar ? "" : tableQuery.trim();
    const statusOrders =
      showQuickStatusFilters && activeFilter !== "all"
        ? orders.filter((order) => order.workflow_state === activeFilter)
        : orders;
    return effectiveQuery
      ? statusOrders.filter((order) => matchesServiceOrderSearch(order, effectiveQuery))
      : statusOrders;
  }, [activeFilter, filterBar, orders, showQuickStatusFilters, tableQuery]);
  useEffect(() => setVisibleCount(LIST_PAGE_SIZE), [visibleOrders]);
  const displayedOrders = visibleOrders.slice(0, visibleCount);

  const columns = useMemo<Array<TableColumn<ServiceOrderSummary>>>(
    () => [
      {
        className: "w-[132px] whitespace-nowrap",
        key: "name",
        label: "OS",
        render: (row) => <span className="font-semibold text-white">{row.name}</span>,
      },
      {
        className: "w-[190px]",
        key: "customer",
        label: "Cliente",
        render: (row) => (
          <span className="block min-w-0">
            <span className="block truncate text-white" title={row.customer ?? "Cliente nao informado"}>
              {row.customer ?? "Cliente nao informado"}
            </span>
            <span className="block truncate text-xs text-tec-muted" title={row.customer_device ?? "Aparelho nao vinculado"}>
              {row.customer_device ?? "Aparelho nao vinculado"}
            </span>
          </span>
        ),
      },
      {
        className: "w-[270px]",
        key: "description",
        label: "Descrição",
        render: (row) => {
          const description = compactServiceOrderDescription(row.reported_defect);
          return (
            <span className="block truncate text-tec-subtle" title={row.reported_defect ?? "Sem descricao"}>
              {description}
            </span>
          );
        },
      },
      {
        className: "w-[150px]",
        key: "status",
        label: "Status",
		render: (row) => <div className="flex items-center gap-2"><BadgeStatus status={row.workflow_state} />{row.stage_clock?.is_overdue ? <span className="text-xs font-bold text-red-400">Atrasada</span> : null}</div>,
      },
      {
        className: "w-[142px]",
        key: "next_action",
        label: "Proxima acao",
        render: (row) => <NextActionPill order={row} />,
      },
      {
        className: "w-[160px]",
        key: "responsible",
        label: "Técnico",
        render: (row) => (
          <span className="block truncate" title={row.technician ?? "Sem técnico"}>
            {row.technician ?? "Sem técnico"}
          </span>
        ),
      },
	  {
		className: "w-[150px]",
		key: "attendant",
		label: "Recebido por",
		render: (row) => <span className="block truncate" title={row.attendant ?? "Não informado"}>{row.attendant ?? "Não informado"}</span>,
	  },
      {
        className: "w-[102px] whitespace-nowrap",
        key: "updated",
        label: "Atualização",
        render: (row) => formatDate(row.modified),
      },
      {
        className: "w-[156px] text-right",
        key: "action",
        label: "",
        render: (row) => (
          <div className="flex justify-end gap-2">
			<WorkflowMoveMenu
				actions={row.workflow_transitions}
				blockedTransitions={row.workflow_blockers}
				busy={movingOrder === row.name}
				onRequestApproval={(action) => setMoveApproval({
					name: row.name,
					targetState: action.next_state,
					requestType: action.next_state === "Cancelado" && row.has_sales_invoice ? "billed_service_order_cancel" : "service_order_move",
				})}
				onSelect={(action) => void handleQuickMove(row, action)}
				requestableTransitions={row.workflow_requestable_transitions}
			/>
            <button className="inline-flex min-h-8 items-center gap-2 rounded-control border border-tec-border/20 bg-tec-field px-3 text-xs font-bold text-tec-text transition hover:border-tec-orange/50 hover:bg-tec-orange/10" onClick={(event) => { event.stopPropagation(); onOpenOrder(row.name); }} title={`Abrir ${row.name}`} type="button">Abrir <ArrowRight size={14} /></button>
          </div>
        ),
      },
    ],
    [movingOrder, onOpenOrder, onToast],
  );

  return (
    <Card className="p-5">
      <div className="mb-4 flex flex-col gap-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-white">{title}</h2>
            <span className="rounded-full bg-tec-orange/20 px-2 py-1 text-xs font-bold text-tec-orange">
              {orders.length}
            </span>
          </div>
          {filterBar ? null : (
            <Button icon={<SearchIcon size={17} />} onClick={() => setSearchOpen((current) => !current)}>
              {searchOpen ? "Ocultar busca" : "Buscar"}
            </Button>
          )}
        </div>
        {filterBar}
        {!filterBar && searchOpen ? (
          <label className="relative block max-w-xl">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tec-muted" size={17} />
            <input
              className="h-10 w-full rounded-control border border-tec-border/20 bg-tec-field pl-10 pr-3 text-sm font-medium text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70"
              onChange={(event) => setTableQuery(event.target.value)}
              placeholder="Buscar na fila..."
              type="search"
              value={tableQuery}
            />
          </label>
        ) : null}
        {showQuickStatusFilters ? (
          <div className="flex flex-wrap gap-2">
            {QUEUE_FILTERS.map((filter) => {
              const selected = activeFilter === filter.value;
              return (
                <button
                  className={cx(
                    "min-h-8 rounded-full border px-4 text-xs font-bold transition",
                    selected
                      ? "border-tec-orange bg-tec-orange text-tec-ink shadow-glow"
                      : "border-tec-border/20 bg-tec-field/60 text-tec-subtle hover:border-tec-orange/50 hover:text-tec-text",
                  )}
                  key={filter.value}
                  onClick={() => setActiveFilter(filter.value)}
                  type="button"
                >
                  {filter.label}
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
      {presentation === "grid" ? (
        <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
          {displayedOrders.map((row) => (
            <button
              className="rounded-card border border-tec-border/15 bg-tec-field/45 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-field"
              data-tp-context="service-order"
              data-tp-customer={row.customer ?? ""}
              data-tp-label={row.customer ?? row.name}
              data-tp-name={row.name}
              data-tp-workflow-state={row.workflow_state ?? ""}
              key={row.name}
              onClick={() => onOpenOrder(row.name)}
              type="button"
            >
              <div className="flex items-start justify-between gap-3">
                <span className="font-bold text-white">{row.name}</span>
				<div className="flex items-center gap-2"><BadgeStatus status={row.workflow_state} />{row.stage_clock?.is_overdue ? <span className="text-xs font-bold text-red-400">Atrasada</span> : null}</div>
              </div>
              <span className="mt-3 block truncate text-sm font-semibold text-tec-text">{row.customer ?? "Cliente não informado"}</span>
              <span className="mt-1 block truncate text-xs text-tec-muted">{row.customer_device ?? "Aparelho não vinculado"}</span>
              <span className="mt-3 block line-clamp-2 text-sm leading-5 text-tec-subtle">{compactServiceOrderDescription(row.reported_defect)}</span>
              <div className="mt-4 flex items-center justify-between gap-3 border-t border-tec-border/15 pt-3">
                <NextActionPill order={row} />
                <span className="inline-flex items-center gap-1 text-xs font-bold text-tec-orange">Abrir <ArrowRight size={14} /></span>
              </div>
            </button>
          ))}
          {!visibleOrders.length ? <p className="col-span-full py-8 text-center text-sm text-tec-muted">Nenhuma OS encontrada para este recorte.</p> : null}
        </div>
      ) : (
        <DataTable
          columns={columns}
          emptyLabel="Nenhuma OS encontrada para este papel."
          getRowProps={(row) => ({
            "data-tp-context": "service-order",
            "data-tp-customer": row.customer ?? "",
            "data-tp-label": row.customer ?? row.name,
            "data-tp-name": row.name,
            "data-tp-workflow-state": row.workflow_state ?? "",
          })}
          onRowClick={(row) => onOpenOrder(row.name)}
          rows={displayedOrders}
        />
      )}
      <ProgressiveListFooter shown={displayedOrders.length} total={visibleOrders.length} onShowMore={() => setVisibleCount((current) => current + LIST_PAGE_SIZE)} />
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
      <ApprovalRequestModal
        onClose={() => setMoveApproval(null)}
        onCreated={(request) => {
          setMoveApproval(null);
          if (request?.executed_directly) onRefresh?.();
        }}
        onToast={onToast}
        open={Boolean(moveApproval)}
        payload={moveApproval?.requestType === "service_order_move" ? { target_state: moveApproval.targetState } : {}}
        referenceName={moveApproval?.name ?? ""}
        requestType={moveApproval?.requestType ?? "service_order_move"}
        title={moveApproval?.requestType === "billed_service_order_cancel"
          ? "Esta OS possui nota fiscal vinculada. Ao aprovar, o Gestor cancelará/estornará a nota fiscal e só então concluirá o cancelamento da OS. Deseja solicitar essa ação?"
          : `Seu papel não permite mover esta OS para ${moveApproval?.targetState ?? "esta etapa"}. Deseja solicitar aprovação?`}
      />
    </Card>
  );
}

function NextActionPill({ order }: { order: ServiceOrderSummary }) {
  const next = nextActionForOrder(order);
  return (
    <span
      className={cx(
        "inline-flex min-h-7 items-center whitespace-nowrap rounded-full px-3 text-xs font-bold",
        next.tone === "orange" && "bg-tec-orange/15 text-tec-orange",
        next.tone === "blue" && "bg-tec-blue/15 text-tec-blue",
        next.tone === "green" && "bg-tec-success/15 text-tec-success",
        next.tone === "amber" && "bg-tec-amber/15 text-tec-amber",
        next.tone === "muted" && "bg-tec-field text-tec-muted",
      )}
    >
      {next.label}
    </span>
  );
}

function nextActionForOrder(order: ServiceOrderSummary): {
  label: string;
  tone: "amber" | "blue" | "green" | "muted" | "orange";
} {
  if (order.next_action) {
    return order.next_action;
  }
  switch (order.workflow_state) {
    case "Entrada criada":
      return { label: "Aguardar tecnico", tone: "muted" };
    case "Em diagnostico":
    case "Em diagnóstico":
      return { label: "Diagnosticar", tone: "blue" };
    case "Diagnosticado — aguardando orçamento":
      return { label: `Precificar · ${order.pricing_responsibility ?? "responsável pendente"}`, tone: "amber" };
    case "Aguardando aprovação":
    case "Aguardando aprovaÃ§Ã£o":
      return { label: "Cobrar aceite", tone: "amber" };
    case "Aguardando peça":
    case "Aguardando peca":
      return { label: "Acompanhar peca", tone: "orange" };
    case "Em reparo":
      return { label: "Acompanhar reparo", tone: "blue" };
    case "Pronto para retirada":
      return { label: "Chamar retirada", tone: "green" };
    case "Entregue":
      return { label: "Concluida", tone: "muted" };
    case "Reprovado":
    case "Orçamento expirado":
    case "OrÃ§amento expirado":
      return { label: "Retirada sem reparo", tone: "orange" };
    default:
      return { label: "Abrir OS", tone: "muted" };
  }
}

function ServiceOrderDetail({
  initialFlow,
	isRestrictedTechnician,
	canViewDirectorFinancial,
  name,
  onBack,
  onInitialFlowHandled,
  onToast,
}: {
  initialFlow: ServiceOrderFlow | null;
	 isRestrictedTechnician: boolean;
	 canViewDirectorFinancial: boolean;
  name: string;
  onBack: () => void;
  onInitialFlowHandled: () => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
}) {
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "ready"; detail: ServiceOrderDetailResponse }
    | { status: "error"; message: string }
  >({ status: "loading" });
  const [activeFlow, setActiveFlow] = useState<"approve" | "reject" | "pickup" | null>(null);
  const [actionsOpen, setActionsOpen] = useState(false);
  const [budgetLineType, setBudgetLineType] = useState<BudgetLineType | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [quoteSendOpen, setQuoteSendOpen] = useState(false);
  const [acceptanceType, setAcceptanceType] = useState<"Entrada" | "Retirada" | null>(null);
  const [courtesyWarrantyOpen, setCourtesyWarrantyOpen] = useState(false);
  const [moveApproval, setMoveApproval] = useState<{ targetState: string; requestType: "service_order_move" | "billed_service_order_cancel" } | null>(null);
  const [checkinTracking, setCheckinTracking] = useState<TrackingLinkResponse | null>(null);
  const [activeStageScreen, setActiveStageScreen] = useState<ServiceOrderStageScreen>("entrada");
  const initialFlowRef = useRef(initialFlow);

  useEffect(() => {
    initialFlowRef.current = initialFlow;
  }, [initialFlow]);

  useEffect(() => {
    try {
      const stored = window.sessionStorage.getItem(CHECKIN_TRACKING_LINK_KEY);
      window.sessionStorage.removeItem(CHECKIN_TRACKING_LINK_KEY);
      if (!stored) {
        setCheckinTracking(null);
        return;
      }
      const parsed = JSON.parse(stored) as { serviceOrder?: string; tracking?: TrackingLinkResponse };
      setCheckinTracking(parsed.serviceOrder === name ? parsed.tracking ?? null : null);
    } catch {
      setCheckinTracking(null);
    }
  }, [name]);

  useEffect(() => {
    let mounted = true;
    setActiveFlow(null);
    setActionsOpen(false);
    setBudgetLineType(null);
    setHistoryOpen(false);
    setQuoteSendOpen(false);
		setAcceptanceType(null);
    setCourtesyWarrantyOpen(false);
    setMoveApproval(null);
    setState({ status: "loading" });
    serviceOrders
      .detail(name)
      .then((detail) => {
        if (mounted) {
          setState({ status: "ready", detail });
          setActiveStageScreen(serviceOrderStageScreenForState(detail.workflow_state));
          if (initialFlowRef.current) {
            setActiveFlow(initialFlowRef.current);
            onInitialFlowHandled();
          }
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
  }, [name, onInitialFlowHandled]);

  useEffect(() => {
    if (state.status === "ready") {
      setActiveStageScreen(serviceOrderStageScreenForState(state.detail.workflow_state));
    }
  }, [state]);

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
  const whatsappUrl = buildWhatsAppUrl(
    detail.customer?.custom_whatsapp || detail.customer?.mobile_no,
    `Olá, ${customerLabel}. Aqui é da ${commercialName()}. Sobre a OS ${detail.name} (${deviceLabel}), podemos falar por aqui?`,
  );

  async function handleSimpleWorkflowMove(nextState: string) {
    try {
      const moveResult = await serviceOrders.move(detail.name, nextState);
      const updated = await serviceOrders.detail(detail.name);
      setState({ status: "ready", detail: updated });
      onToast(moveResult.changed ? `OS movida para ${updated.workflow_state}.` : `OS já estava em ${updated.workflow_state}.`);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Não foi possível avançar o workflow.";
      if (message.includes("OS faturada") && nextState === "Cancelado") {
        setMoveApproval({ targetState: nextState, requestType: "billed_service_order_cancel" });
      } else if (message.includes("Seu papel não permite mover")) {
        setMoveApproval({ targetState: nextState, requestType: "service_order_move" });
      } else {
        onToast(message, "error");
      }
    }
  }

  async function startNoRepairPickup() {
    try {
      const moveResult = await serviceOrders.move(detail.name, "Pronto para retirada");
      const updated = await serviceOrders.detail(detail.name);
      setState({ status: "ready", detail: updated });
      setActiveFlow("pickup");
      onToast(moveResult.changed ? "OS preparada para retirada sem reparo." : "A retirada sem reparo já está pronta para conferência.");
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Não foi possível preparar a retirada sem reparo.";
      if (message.includes("Seu papel não permite mover")) {
        setMoveApproval({ targetState: "Pronto para retirada", requestType: "service_order_move" });
      } else {
        onToast(message, "error");
      }
    }
  }

  async function refreshServiceOrder(message = "Atendimento atualizado.") {
    try {
      const updated = await serviceOrders.detail(detail.name);
      setState({ status: "ready", detail: updated });
      onToast(message);
    } catch (caught) {
      onToast(caught instanceof Error ? caught.message : "Não foi possível atualizar a OS.", "error");
    }
  }

	if (isRestrictedTechnician || detail.technical_view) {
		return (
			<TechnicalServiceOrderDetail
				detail={detail}
				onBack={onBack}
				onMove={handleSimpleWorkflowMove}
				onToast={onToast}
				onRefresh={refreshServiceOrder}
				onSaveDiagnosis={async (problemFound) => {
					try {
						const updated = await serviceOrders.saveDiagnosis(detail.name, problemFound);
						setState({ status: "ready", detail: updated });
						onToast("Diagnóstico salvo na OS.");
					} catch (caught) {
						onToast(caught instanceof Error ? caught.message : "Não foi possível salvar o diagnóstico.", "error");
						throw caught;
					}
				}}
				onCompleteDiagnosis={async (problemFound, pricingResponsibility) => {
					const updated = await serviceOrders.completeDiagnosis(detail.name, problemFound, pricingResponsibility);
					setState({ status: "ready", detail: updated });
					onToast(`Diagnóstico concluído. Precificação: ${pricingResponsibility}.`);
				}}
				onSetPartOutcome={async (partName, outcome, lossReason) => {
					try {
						const updated = await serviceOrders.setPartOutcome(detail.name, partName, outcome, lossReason);
						setState({ status: "ready", detail: updated });
						onToast(outcome === "Perdida" ? "Perda de peça registrada e encaminhada pelo motor." : "Peça baixada no estoque de Reparo.");
					} catch (caught) {
						onToast(caught instanceof Error ? caught.message : "Não foi possível registrar a peça.", "error");
						throw caught;
					}
				}}
			/>
		);
	}

  return (
    <div className="space-y-4">
      <TrackingLinkBanner
        customerName={customerLabel}
        initialTracking={checkinTracking}
        onToast={onToast}
        phone={detail.customer?.custom_whatsapp || detail.customer?.mobile_no}
        serviceOrder={detail.name}
      />
      <ServiceOrderHero
        detail={detail}
        onBack={onBack}
        onOpenActions={() => setActionsOpen(true)}
        onOpenAcceptance={setAcceptanceType}
        onOpenBudgetEditor={setBudgetLineType}
        onOpenQuoteSend={() => setQuoteSendOpen(true)}
      />
      <FastPathConversionCard detail={detail} onConverted={(updated) => { setState({ status: "ready", detail: updated }); onToast("OS convertida para o caminho completo; novo valor enviado para aprovação."); }} onToast={onToast} />

      <ServiceOrderStageTabs active={activeStageScreen} detail={detail} onChange={setActiveStageScreen} />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_330px]">
        <main className="min-w-0">
          <ServiceOrderStageScreenContent
            active={activeStageScreen}
            canViewDirectorFinancial={canViewDirectorFinancial}
            customerLabel={customerLabel}
            detail={detail}
            deviceLabel={deviceLabel}
            onOpenAcceptance={setAcceptanceType}
            onOpenBudgetEditor={setBudgetLineType}
            onOpenHistory={() => setHistoryOpen(true)}
            onOpenQuoteSend={() => setQuoteSendOpen(true)}
			onCompleteDiagnosis={async (problemFound, pricingResponsibility) => {
				const updated = await serviceOrders.completeDiagnosis(detail.name, problemFound, pricingResponsibility);
				setState({ status: "ready", detail: updated });
				onToast(`Diagnóstico concluído. Precificação: ${pricingResponsibility}.`);
			}}
            onToast={onToast}
            onUpdated={(updated) => setState({ status: "ready", detail: updated })}
            whatsappUrl={whatsappUrl}
          />
        </main>

        <aside className="space-y-4">
          <ServiceOrderFinanceSnapshot detail={detail} />
          <ServiceOrderPersistentOverview detail={detail} />
          <NextActionCard
            actions={detail.workflow_transitions}
            blockedTransitions={detail.workflow_blockers}
            detail={detail}
            onOpenFlow={setActiveFlow}
            onOpenHistory={() => setHistoryOpen(true)}
            onOpenQuoteSend={() => setQuoteSendOpen(true)}
            onRefresh={() => void refreshServiceOrder()}
            onSimpleMove={handleSimpleWorkflowMove}
            onStartNoRepairPickup={() => void startNoRepairPickup()}
			onRequestApproval={(targetState) => setMoveApproval({
				targetState,
				requestType: targetState === "Cancelado" && Boolean(detail.finance.sales_invoice) ? "billed_service_order_cancel" : "service_order_move",
			})}
          />
		  <WorkflowSideStepper detail={detail} />
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
      <BudgetLineModal
        detail={detail}
        lineType={budgetLineType}
        onClose={() => setBudgetLineType(null)}
        onToast={onToast}
        onUpdated={(updated) => setState({ status: "ready", detail: updated })}
      />
      <QuoteSendModal
        detail={detail}
        onClose={() => setQuoteSendOpen(false)}
        onToast={onToast}
        onUpdated={(updated) => setState({ status: "ready", detail: updated })}
        open={quoteSendOpen}
      />
      <ServiceOrderHistoryModal detail={detail} onClose={() => setHistoryOpen(false)} open={historyOpen} />
      <ServiceOrderActionsModal
        detail={detail}
        onClose={() => setActionsOpen(false)}
		onOpenCourtesyWarranty={() => {
			setActionsOpen(false);
			setCourtesyWarrantyOpen(true);
		}}
		onOpenAcceptance={(type) => {
			setActionsOpen(false);
			setAcceptanceType(type);
		}}
        onOpenBudgetEditor={(type) => {
          setActionsOpen(false);
          setBudgetLineType(type);
        }}
        onOpenHistory={() => {
          setActionsOpen(false);
          setHistoryOpen(true);
        }}
        onOpenQuoteSend={() => {
          setActionsOpen(false);
          setQuoteSendOpen(true);
        }}
        onRefresh={() => void refreshServiceOrder("OS atualizada.")}
        open={actionsOpen}
      />
		<AcceptanceLinkModal
			acceptanceType={acceptanceType}
			serviceOrder={detail.name}
			onClose={() => setAcceptanceType(null)}
			onToast={onToast}
		/>
      <CourtesyWarrantyRequestModal
        detail={detail}
        onClose={() => setCourtesyWarrantyOpen(false)}
        onToast={onToast}
        open={courtesyWarrantyOpen}
      />
      <ApprovalRequestModal
        onClose={() => setMoveApproval(null)}
        onCreated={(request) => {
          setMoveApproval(null);
          if (request?.executed_directly) void refreshServiceOrder("OS atualizada.");
        }}
        onToast={onToast}
        open={Boolean(moveApproval)}
        payload={moveApproval?.requestType === "service_order_move" ? { target_state: moveApproval.targetState } : {}}
        referenceName={detail.name}
        requestType={moveApproval?.requestType ?? "service_order_move"}
        title={moveApproval?.requestType === "billed_service_order_cancel"
          ? "Esta OS possui nota fiscal vinculada. Ao aprovar, o Gestor cancelará/estornará a nota fiscal e só então concluirá o cancelamento da OS. Deseja solicitar essa ação?"
          : `Seu papel não permite mover esta OS para ${moveApproval?.targetState ?? "esta etapa"}. Deseja solicitar aprovação?`}
      />
    </div>
  );
}

function TrackingLinkCard({
  customerName,
  onClose,
  onOpen,
  onToast,
  open,
  phone,
  serviceOrder,
}: {
  customerName: string;
  onClose: () => void;
  onOpen: () => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  open: boolean;
  phone?: string | null;
  serviceOrder: string;
}) {
  const [tracking, setTracking] = useState<TrackingLinkResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) {
      setTracking(null);
      setLoading(false);
    }
  }, [open]);

  async function generate() {
    setLoading(true);
    try {
      setTracking(await serviceOrders.issueTrackingLink(serviceOrder));
    } catch (caught) {
      onToast(caught instanceof Error ? caught.message : "Não foi possível gerar o link de rastreio.", "error");
    } finally {
      setLoading(false);
    }
  }

  async function copyLink() {
    if (!tracking) return;
    try {
      await navigator.clipboard.writeText(tracking.link);
      onToast("Link de rastreio copiado.");
    } catch {
      onToast("Não foi possível copiar automaticamente. Selecione o link e copie.", "error");
    }
  }

  const trackingWhatsApp = tracking
    ? buildWhatsAppUrl(
        phone,
        `Olá, ${customerName}. Acompanhe sua OS ${serviceOrder} e aprove o orçamento por aqui: ${tracking.link}`,
      )
    : null;

  return (
    <>
      <Card className="p-4">
        <div className="flex items-start gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-control bg-tec-blue/15 text-tec-blue">
            <QrCode size={20} />
          </span>
          <div className="min-w-0">
            <h3 className="text-sm font-bold text-tec-text">Rastreio do cliente</h3>
            <p className="mt-1 text-xs font-medium leading-relaxed text-tec-muted">
              Gere o QR e o link seguro para o cliente acompanhar a OS e decidir o orçamento.
            </p>
            <Button className="mt-3" icon={<QrCode size={16} />} onClick={onOpen} variant="secondary">
              Gerar link de rastreio
            </Button>
          </div>
        </div>
      </Card>
      <Modal className="max-w-lg" onClose={onClose} open={open} title={`Rastreio da OS ${serviceOrder}`}>
        {!tracking ? (
          <div className="space-y-5">
            <p className="text-sm leading-relaxed text-tec-subtle">
              O novo link substitui qualquer link anterior desta OS por segurança. Ele permite somente acompanhar o reparo e aprovar ou reprovar o orçamento.
            </p>
            <Button disabled={loading} icon={<QrCode size={17} />} onClick={() => void generate()} variant="primary">
              {loading ? "Gerando link..." : "Gerar link seguro"}
            </Button>
          </div>
        ) : (
          <div className="space-y-5">
            <div className="grid place-items-center rounded-card border border-tec-border/15 bg-white p-4">
              <img alt={`QR Code do rastreio da OS ${serviceOrder}`} className="h-48 w-48" src={tracking.qr_svg} />
            </div>
            <label className="block text-xs font-bold uppercase tracking-wide text-tec-muted">
              Link do cliente
              <input className="tp-input mt-2" readOnly value={tracking.link} />
            </label>
            <p className="text-xs font-medium text-tec-muted">
              {tracking.expires_on
                ? `Válido até ${formatDate(tracking.expires_on)}.`
                : "Ativo durante o reparo e por 90 dias após a retirada."} O cliente não consegue alterar os dados da OS.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button icon={<Copy size={16} />} onClick={() => void copyLink()} variant="secondary">Copiar link</Button>
              {trackingWhatsApp ? (
                <a className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control border border-tec-whatsapp/35 bg-tec-whatsapp/10 px-4 text-sm font-bold text-tec-whatsapp transition hover:bg-tec-whatsapp/20" href={trackingWhatsApp} rel="noreferrer" target="_blank">
                  <WhatsAppLogo size={17} />
                  Enviar por WhatsApp
                </a>
              ) : (
                <Button disabled icon={<WhatsAppLogo size={17} />} title="Cadastre o WhatsApp do cliente para enviar por aqui." variant="secondary">Sem WhatsApp</Button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}

function TrackingLinkBanner({
  customerName,
  initialTracking,
  onToast,
  phone,
  serviceOrder,
}: {
  customerName: string;
  initialTracking?: TrackingLinkResponse | null;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  phone?: string | null;
  serviceOrder: string;
}) {
  const [tracking, setTracking] = useState<TrackingLinkResponse | null>(initialTracking ?? null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setTracking(initialTracking ?? null);
  }, [initialTracking, serviceOrder]);

  async function generate() {
    setLoading(true);
    try {
      setTracking(await serviceOrders.issueTrackingLink(serviceOrder));
    } catch (caught) {
      onToast(caught instanceof Error ? caught.message : "Não foi possível gerar o link de rastreio.", "error");
    } finally {
      setLoading(false);
    }
  }

  async function copyLink() {
    if (!tracking) return;
    try {
      await navigator.clipboard.writeText(tracking.link);
      onToast("Link de rastreio copiado.");
    } catch {
      onToast("Não foi possível copiar automaticamente.", "error");
    }
  }

  const trackingWhatsApp = tracking
    ? buildWhatsAppUrl(phone, `Olá, ${customerName}. Acompanhe sua OS ${serviceOrder}: ${tracking.link}`)
    : null;

  return (
    <section aria-label="Link de rastreio do cliente" className="tp-tracking-banner">
      <div className="min-w-0 p-5 sm:p-6">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-card bg-tec-orange/15 text-tec-orange">
            <QrCode size={22} />
          </span>
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-tec-orange/85">Link de rastreio do cliente</p>
            <p className="mt-1 text-sm text-tec-subtle">Acompanhe o reparo e decida o orçamento em tempo real.</p>
          </div>
        </div>

        {tracking ? (
          <>
            <p className="tp-display mt-5 truncate text-2xl font-bold text-tec-orange sm:text-3xl" title={tracking.link}>
              {tracking.link.replace(/^https?:\/\//, "")}
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {trackingWhatsApp ? (
                <a className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control border border-tec-orange/35 bg-tec-orange/10 px-4 text-sm font-bold text-tec-orange transition hover:bg-tec-orange/20" href={trackingWhatsApp} rel="noreferrer" target="_blank">
                  <Send size={16} />
                  Compartilhar com o cliente
                </a>
              ) : null}
              <Button icon={<Copy size={16} />} onClick={() => void copyLink()} variant="secondary">Copiar link</Button>
              <Button icon={<ArrowRight size={16} />} onClick={() => window.open(tracking.link, "_blank", "noopener,noreferrer")} variant="secondary">Abrir link</Button>
            </div>
            <p className="mt-3 text-xs font-medium text-tec-muted">
              {tracking.expires_on ? `Válido até ${formatDate(tracking.expires_on)}.` : "Ativo durante o reparo e por 90 dias após a retirada."}
            </p>
          </>
        ) : (
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <p className="max-w-2xl text-sm leading-relaxed text-tec-subtle">
              Gere o link seguro para o cliente acompanhar esta OS. Uma nova emissão substitui o link anterior por segurança.
            </p>
            <Button disabled={loading} icon={<QrCode size={17} />} onClick={() => void generate()} variant="primary">
              {loading ? "Gerando link..." : "Gerar link e QR"}
            </Button>
          </div>
        )}
      </div>
      <div className="tp-tracking-qr">
        {tracking ? (
          <img alt={`QR Code do rastreio da OS ${serviceOrder}`} className="h-40 w-40 sm:h-44 sm:w-44" src={tracking.qr_svg} />
        ) : (
          <div className="grid h-40 w-40 place-items-center rounded-card border border-dashed border-tec-orange/35 bg-tec-field/35 p-4 text-center text-xs font-semibold text-tec-muted sm:h-44 sm:w-44">
            O QR aparece após gerar o link.
          </div>
        )}
      </div>
    </section>
  );
}

function FastPathConversionCard({ detail, onConverted, onToast }: { detail: ServiceOrderDetailResponse; onConverted: (detail: ServiceOrderDetailResponse) => void; onToast: (message: string, tone?: ToastState["tone"]) => void }) {
  const [busy, setBusy] = useState(false);
  if (detail.caminho !== "Rápido" || !["Entrada criada", "Em reparo"].includes(detail.workflow_state ?? "")) return null;
  const convert = async () => {
    const reason = window.prompt("O que o técnico encontrou além do previsto?")?.trim();
    if (!reason) return;
    const rawValue = window.prompt("Qual é o novo valor total para aprovação do cliente?", String(detail.totals.grand_total || ""));
    const newValue = Number(String(rawValue ?? "").replace(",", "."));
    if (!Number.isFinite(newValue) || newValue <= 0) { onToast("Informe um novo valor válido.", "error"); return; }
    const notes = window.prompt("Observação para o cliente (opcional)", "Encontramos um serviço adicional durante a execução.") ?? "";
    setBusy(true);
    try { onConverted(await serviceOrders.convertFast(detail.name, reason, newValue, notes)); }
    catch (caught) { onToast(caught instanceof Error ? caught.message : "Não foi possível converter a OS.", "error"); }
    finally { setBusy(false); }
  };
  return <Card className="border-tec-amber/30 bg-tec-amber/5 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wide text-tec-amber">Caminho rápido</p><p className="mt-1 text-sm text-tec-subtle">Se apareceu algo além do combinado, converta e peça aprovação do novo valor.</p></div><Button disabled={busy} onClick={() => void convert()} variant="secondary">{busy ? "Convertendo..." : "Converter para completo"}</Button></div></Card>;
}

function TechnicalServiceOrderDetail({
  detail,
  onBack,
  onMove,
	onToast,
  onRefresh,
  onSaveDiagnosis,
	onCompleteDiagnosis,
	 onSetPartOutcome,
}: {
  detail: ServiceOrderDetailResponse;
  onBack: () => void;
  onMove: (nextState: string) => Promise<void>;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  onRefresh: (message?: string) => Promise<void>;
  onSaveDiagnosis: (problemFound: string) => Promise<void>;
	onCompleteDiagnosis: (problemFound: string, pricingResponsibility: "Técnico" | "Balcão") => Promise<void>;
	 onSetPartOutcome: (partName: string, outcome: "Usada no reparo" | "Perdida", lossReason?: string) => Promise<void>;
}) {
  const [diagnosis, setDiagnosis] = useState(detail.diagnosis.problem_found ?? "");
  const [activeStageScreen, setActiveStageScreen] = useState<ServiceOrderStageScreen>(() => serviceOrderStageScreenForState(detail.workflow_state));
  const [savingDiagnosis, setSavingDiagnosis] = useState(false);
	const [pricingResponsibility, setPricingResponsibility] = useState<"Técnico" | "Balcão">(detail.diagnosis.default_pricing_responsibility);
  const [moving, setMoving] = useState(false);
	const [moveApproval, setMoveApproval] = useState<{ targetState: string; requestType: "service_order_move" | "billed_service_order_cancel" } | null>(null);
  const [partRequestOpen, setPartRequestOpen] = useState(false);
	const [partOutcomeTarget, setPartOutcomeTarget] = useState<ServiceOrderBudgetLine | null>(null);
  const deviceLabel =
    [detail.device?.brand, detail.device?.model, detail.device?.color].filter(Boolean).join(" ") ||
    detail.device?.name ||
    "Aparelho não vinculado";

  useEffect(() => {
    setDiagnosis(detail.diagnosis.problem_found ?? "");
  }, [detail.diagnosis.problem_found, detail.name]);

  useEffect(() => {
    setActiveStageScreen(serviceOrderStageScreenForState(detail.workflow_state));
  }, [detail.name, detail.workflow_state]);

  async function saveDiagnosis() {
    setSavingDiagnosis(true);
    try {
      await onSaveDiagnosis(diagnosis);
    } finally {
      setSavingDiagnosis(false);
    }
  }

	async function completeDiagnosis() {
		setSavingDiagnosis(true);
		try { await onCompleteDiagnosis(diagnosis, pricingResponsibility); }
		finally { setSavingDiagnosis(false); }
	}

  async function move(action: ServiceOrderWorkflowAction) {
    setMoving(true);
    try {
      await onMove(action.next_state);
    } finally {
      setMoving(false);
    }
  }

  return (
    <div className="space-y-4">
      <ServiceOrderHero
        detail={detail}
        onBack={onBack}
        onOpenActions={() => undefined}
        onOpenBudgetEditor={() => undefined}
        showActionsMenu={false}
        showBudgetAction={false}
      />
      <FastPathConversionCard detail={detail} onConverted={() => void onRefresh("OS convertida para o caminho completo e enviada para aprovação.")} onToast={onToast} />
      <ServiceOrderStageTabs active={activeStageScreen} detail={detail} onChange={setActiveStageScreen} />

      <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-4">
          {activeStageScreen === "entrada" ? <>
          <div className="grid gap-4 lg:grid-cols-2">
            <IdentityCard
              icon={<UserRound size={20} />}
              lines={[["Cliente", detail.customer?.customer_name ?? detail.customer?.name ?? "Não informado"], ["Atendente", detail.attendant ?? "Não definido"]]}
              title="Atendimento atribuído"
            />
            <IdentityCard
              icon={<Smartphone size={20} />}
              lines={[
                ["Aparelho", deviceLabel],
                ["IMEI / Serial", detail.device?.imei_serial ?? "Não informado"],
                ["Estado declarado", detail.physical_state ?? "Não informado"],
              ]}
              title="Aparelho"
            />
          </div>
          <ServiceOrderAttendanceCard detail={detail} />
          <TimelineCard events={detail.timeline} />
          </> : null}

          {activeStageScreen === "diagnostico" ? <>
          <Card className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-xl font-bold text-white">Diagnóstico técnico</h3>
                <p className="mt-1 text-sm text-tec-muted">Registre o problema encontrado para manter a execução rastreável.</p>
              </div>
              {detail.diagnosis.diagnosis_date ? <span className="rounded-full bg-tec-success/10 px-3 py-1 text-xs font-bold text-tec-success">Registrado em {formatDate(detail.diagnosis.diagnosis_date)}</span> : null}
            </div>
            <textarea
              className="mt-4 min-h-32 w-full rounded-control border border-tec-border/20 bg-tec-field p-3 text-sm font-medium text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70"
              onChange={(event) => setDiagnosis(event.target.value)}
              placeholder="Descreva o defeito encontrado, causa provável e orientação técnica."
              value={diagnosis}
            />
            {detail.workflow_state === "Em diagnóstico" ? <div className="mt-4 rounded-control border border-tec-border/20 bg-tec-field/45 p-4">
				<p className="text-sm font-bold text-white">Quem faz a precificação agora?</p>
				<select className="tp-input mt-2" onChange={(event) => setPricingResponsibility(event.target.value as "Técnico" | "Balcão")} value={pricingResponsibility}>
					<option disabled={!detail.diagnosis.technician_pricing_available} value="Técnico">Técnico continua{!detail.diagnosis.technician_pricing_available ? " — papel técnico necessário" : ""}</option>
					<option value="Balcão">Encaminhar ao Balcão</option>
				</select>
				{!detail.diagnosis.technician_pricing_available ? <p className="mt-2 text-xs text-tec-amber">Este usuário não possui papel com capacidade de precificação técnica; encaminhe ao Balcão.</p> : null}
			</div> : <HandoffStatus detail={detail} />}
            <div className="mt-3 flex flex-wrap justify-end gap-2">
              <Button disabled={!diagnosis.trim() || savingDiagnosis} icon={<FileText size={17} />} onClick={() => void saveDiagnosis()} variant="primary">
                {savingDiagnosis ? "Salvando..." : "Salvar diagnóstico"}
              </Button>
			  {detail.workflow_state === "Em diagnóstico" ? <Button disabled={!diagnosis.trim() || savingDiagnosis} icon={<ArrowRight size={17} />} onClick={() => void completeDiagnosis()} variant="primary">Concluir e repassar</Button> : null}
            </div>
          </Card>
		  {detail.workflow_state === "Diagnosticado — aguardando orçamento" && detail.diagnosis.pricing_responsibility === "Técnico" ? <TechnicalBudgetEditor onCompleted={() => onRefresh("Orçamento concluído e encaminhado para aprovação.")} onToast={onToast} serviceOrder={detail.name} /> : null}
          <TimelineCard events={detail.timeline} />
          </> : null}

          {activeStageScreen === "aprovacao" ? <>
          <StageHeading title="Aprovação" description="A decisão do cliente e seus aceites são conduzidos pelos fluxos autorizados." />
          <Card className="p-5"><h3 className="text-lg font-bold text-white">Situação da decisão</h3><dl className="mt-4 space-y-3 text-sm"><DetailLine label="Status" value={detail.approval_status ?? "Pendente"} /><DetailLine label="Canal" value={detail.approval.channel ?? "Ainda não informado"} /><DetailLine label="Data" value={detail.approval.approval_date ? formatDate(detail.approval.approval_date) : "Pendente"} /></dl></Card>
          <TimelineCard events={detail.timeline} />
          </> : null}

          {activeStageScreen === "execucao" ? <>
          <Card className="p-5">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-xl font-bold text-white">Execução do reparo</h3>
                <p className="mt-1 text-sm text-tec-muted">Serviços, peças e resultado técnico desta OS.</p>
              </div>
              <span className="rounded-full bg-tec-field px-3 py-1 text-xs font-bold text-tec-subtle">{detail.parts.length} peça(s)</span>
            </div>

            <TechnicalLineList lines={detail.services} title="Serviços" type="service" />
            <div className="mt-4">
					<TechnicalLineList lines={detail.parts} onRecordPartOutcome={setPartOutcomeTarget} title="Peças aplicadas" type="part" />
            </div>
          </Card>
          <TimelineCard events={detail.timeline} />
          </> : null}

          {activeStageScreen === "retirada" ? <TechnicalFinanceStageCard detail={detail} /> : null}
        </div>

        <aside className="space-y-4">
          <ServiceOrderFinanceSnapshot detail={detail} />
          <ServiceOrderPersistentOverview detail={detail} />
          <Card className="p-5">
            <p className="text-xs font-bold uppercase tracking-wide text-tec-muted">Etapa atual</p>
            <div className="mt-3 flex items-center justify-between gap-3">
              <BadgeStatus status={detail.workflow_state} />
              <WorkflowMoveMenu
                actions={detail.workflow_transitions}
				blockedTransitions={detail.workflow_blockers}
                busy={moving}
				onRequestApproval={(action) => setMoveApproval({
					targetState: action.next_state,
					requestType: action.next_state === "Cancelado" && Boolean(detail.finance.sales_invoice) ? "billed_service_order_cancel" : "service_order_move",
				})}
                onSelect={(action) => void move(action)}
				requestableTransitions={detail.workflow_requestable_transitions}
                status={detail.workflow_state}
                variant="status"
              />
            </div>
            <p className="mt-4 text-sm text-tec-subtle">As transições disponíveis vêm do workflow do motor e só afetam esta OS atribuída.</p>
          </Card>
          <Card className="p-5">
            <p className="text-xs font-bold uppercase tracking-wide text-tec-muted">Peças</p>
            <h3 className="mt-2 text-lg font-bold text-white">Faltou uma peça?</h3>
            <p className="mt-2 text-sm text-tec-subtle">Registre a necessidade. A compra é acompanhada sem interromper o seu trabalho técnico.</p>
            <Button className="mt-4 w-full" icon={<PackagePlus size={17} />} onClick={() => setPartRequestOpen(true)} variant="primary">Solicitar peça</Button>
          </Card>
          <ServiceOrderAttendanceCard detail={detail} />
		  <WorkflowSideStepper detail={detail} />
        </aside>
      </div>
      <PartRequestModal onClose={() => setPartRequestOpen(false)} onCreated={() => void onRefresh("Solicitação de peça registrada. OS movida para Aguardando peça.")} open={partRequestOpen} serviceOrder={detail.name} />
		<PartOutcomeModal
			onClose={() => setPartOutcomeTarget(null)}
			onSubmit={async (outcome, lossReason) => {
				if (!partOutcomeTarget?.name) return;
				await onSetPartOutcome(partOutcomeTarget.name, outcome, lossReason);
				setPartOutcomeTarget(null);
			}}
			part={partOutcomeTarget}
		/>
		<ApprovalRequestModal
			onClose={() => setMoveApproval(null)}
			onCreated={(request) => {
				setMoveApproval(null);
				if (request?.executed_directly) void onRefresh("OS atualizada.");
			}}
			onToast={onToast}
			open={Boolean(moveApproval)}
			payload={moveApproval?.requestType === "service_order_move" ? { target_state: moveApproval.targetState } : {}}
			referenceName={detail.name}
			requestType={moveApproval?.requestType ?? "service_order_move"}
			title={moveApproval?.requestType === "billed_service_order_cancel"
				? "Esta OS possui nota fiscal vinculada. Ao aprovar, o Gestor cancelará/estornará a nota fiscal e só então concluirá o cancelamento da OS. Deseja solicitar essa ação?"
				: `Seu papel não permite mover esta OS para ${moveApproval?.targetState ?? "esta etapa"}. Deseja solicitar aprovação?`}
		/>
    </div>
  );
}

function TechnicalFinanceStageCard({ detail }: { detail: ServiceOrderDetailResponse }) {
  return (
    <Card className="p-5">
      <p className="text-xs font-bold uppercase tracking-wide text-tec-muted">Financeiro e retirada</p>
      <h3 className="mt-2 text-xl font-bold text-white">Situação de entrega</h3>
      <p className="mt-2 text-sm leading-6 text-tec-subtle">
        A retirada é acompanhada aqui para contexto operacional. Valores e resultados comerciais permanecem restritos aos papéis autorizados.
      </p>
      <dl className="mt-5 space-y-3 text-sm">
        <DetailLine label="Status" value={detail.pickup.without_repair ? "Retirada sem reparo" : detail.pickup.pickup_date ? "Entregue" : "Em preparação"} />
        <DetailLine label="Aceite de retirada" value={detail.pickup.has_signature ? "Registrado" : "Pendente"} />
        <DetailLine label="Data de retirada" value={detail.pickup.pickup_date ? formatDate(detail.pickup.pickup_date) : "Ainda não registrada"} />
      </dl>
    </Card>
  );
}

function TechnicalBudgetEditor({ onCompleted, onToast, serviceOrder }: { onCompleted: () => Promise<void>; onToast: (message: string, tone?: ToastState["tone"]) => void; serviceOrder: string }) {
	const [budget, setBudget] = useState<TechnicalBudgetResponse | null>(null);
	const [catalog, setCatalog] = useState<TechnicalBudgetCatalogItem[]>([]);
	const [kind, setKind] = useState<BudgetLineType>("service");
	const [query, setQuery] = useState("");
	const [customerPartDescription, setCustomerPartDescription] = useState("");
	const [busy, setBusy] = useState(false);

	const load = useCallback(async () => {
		try { setBudget(await serviceOrders.technicalBudget(serviceOrder)); }
		catch (caught) { onToast(caught instanceof Error ? caught.message : "Não foi possível carregar o orçamento.", "error"); }
	}, [onToast, serviceOrder]);

	useEffect(() => { void load(); }, [load]);
	useEffect(() => {
		let active = true;
		const timer = window.setTimeout(async () => {
			try {
				const response = kind === "service" ? await serviceOrders.searchTechnicalBudgetServices(query) : await serviceOrders.searchTechnicalBudgetParts(query);
				if (active) setCatalog(response.items);
			} catch (caught) { if (active) onToast(caught instanceof Error ? caught.message : "Não foi possível buscar o catálogo.", "error"); }
		}, 180);
		return () => { active = false; window.clearTimeout(timer); };
	}, [kind, onToast, query]);

	async function add(item: TechnicalBudgetCatalogItem) {
		setBusy(true);
		try {
			setBudget(await serviceOrders.addTechnicalBudgetLine(serviceOrder, kind === "service" ? { type: kind, catalog_service: item.name, description: item.description, qty: 1, selling_price: item.selling_price, duration: item.duration, duration_unit: item.duration_unit } : { type: kind, item_code: item.item_code, description: item.description, qty: 1, selling_price: item.selling_price, source: "Loja" }));
			onToast("Linha adicionada ao orçamento.");
		} catch (caught) { onToast(caught instanceof Error ? caught.message : "Não foi possível adicionar a linha.", "error"); }
		finally { setBusy(false); }
	}

	return <Card className="p-5">
		<div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wide text-tec-orange">Precificação técnica</p><h3 className="mt-1 text-xl font-bold text-white">Montar orçamento</h3><p className="mt-1 text-sm text-tec-muted">Somente preço de venda e disponibilidade do depósito Reparo.</p></div><span className="rounded-full bg-tec-field px-3 py-1 text-sm font-bold text-white">{formatCurrency(budget?.selling_total ?? 0)}</span></div>
		<div className="mt-4 grid gap-2 sm:grid-cols-2"><Button onClick={() => setKind("service")} variant={kind === "service" ? "primary" : "secondary"}>Serviços</Button><Button onClick={() => setKind("part")} variant={kind === "part" ? "primary" : "secondary"}>Peças</Button></div>
		<input className="tp-input mt-3" onChange={(event) => setQuery(event.target.value)} placeholder={`Buscar ${kind === "service" ? "serviço" : "peça"}`} value={query} />
		{kind === "part" ? <div className="mt-2 flex gap-2"><input className="tp-input" onChange={(event) => setCustomerPartDescription(event.target.value)} placeholder="Ou descreva uma peça fornecida pelo cliente" value={customerPartDescription} /><Button disabled={busy || !customerPartDescription.trim()} onClick={async () => { setBusy(true); try { setBudget(await serviceOrders.addTechnicalBudgetLine(serviceOrder, { type: "part", description: customerPartDescription, qty: 1, selling_price: 0, source: "Cliente" })); setCustomerPartDescription(""); } catch (caught) { onToast(caught instanceof Error ? caught.message : "Não foi possível adicionar a peça do cliente.", "error"); } finally { setBusy(false); } }}>Adicionar do cliente</Button></div> : null}
		<div className="mt-3 max-h-56 space-y-2 overflow-auto">{catalog.map((item) => <button className="flex w-full items-center justify-between gap-3 rounded-control border border-tec-border/15 bg-tec-field/45 p-3 text-left hover:border-tec-orange/45" disabled={busy} key={item.name ?? item.item_code} onClick={() => void add(item)} type="button"><span><span className="block text-sm font-bold text-white">{item.description}</span><span className="text-xs text-tec-muted">{item.category ?? "Sem categoria"}{item.available_qty !== undefined ? ` · Disponível ${item.available_qty}` : item.duration ? ` · ${item.duration} ${item.duration_unit}` : ""}</span></span><span className="shrink-0 font-bold text-tec-orange">{formatCurrency(item.selling_price)}</span></button>)}</div>
		<div className="mt-5 space-y-2">{[...(budget?.services ?? []), ...(budget?.parts ?? [])].map((line) => <TechnicalBudgetLineEditor disabled={busy} key={line.name} line={line} onChanged={setBudget} onToast={onToast} serviceOrder={serviceOrder} />)}{budget && !budget.services.length && !budget.parts.length ? <p className="rounded-control border border-dashed border-tec-border/20 p-4 text-sm text-tec-muted">Inclua ao menos uma linha.</p> : null}</div>
		<div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-tec-border/15 pt-4"><p className="text-xs text-tec-muted">Versão {budget?.budget_version ?? 1} · {budget?.quote_locked ? "travado" : "em edição"}</p><div className="flex flex-wrap gap-2"><Button disabled={!budget} icon={<Printer size={16} />} onClick={async () => { const preview = window.open("", "_blank"); try { const response = await serviceOrders.technicalBudgetPrint(serviceOrder); if (preview) { preview.document.write(response.html); preview.document.close(); preview.focus(); preview.print(); } } catch (caught) { preview?.close(); onToast(caught instanceof Error ? caught.message : "Não foi possível imprimir.", "error"); } }}>Imprimir</Button><Button disabled={!budget} onClick={async () => { try { const response = await serviceOrders.exportTechnicalBudget(serviceOrder); const url = URL.createObjectURL(new Blob([response.content], { type: "text/csv;charset=utf-8" })); const anchor = document.createElement("a"); anchor.href = url; anchor.download = response.filename; anchor.click(); URL.revokeObjectURL(url); } catch (caught) { onToast(caught instanceof Error ? caught.message : "Não foi possível exportar.", "error"); } }}>Exportar</Button><Button disabled={busy || !budget || budget.services.length + budget.parts.length === 0} icon={<CheckCircle2 size={17} />} onClick={async () => { setBusy(true); try { await serviceOrders.completeTechnicalBudget(serviceOrder); await onCompleted(); } catch (caught) { onToast(caught instanceof Error ? caught.message : "Não foi possível concluir o orçamento.", "error"); } finally { setBusy(false); } }} variant="primary">Concluir orçamento</Button></div></div>
	</Card>;
}

function TechnicalBudgetLineEditor({ disabled, line, onChanged, onToast, serviceOrder }: { disabled: boolean; line: TechnicalBudgetLine; onChanged: (budget: TechnicalBudgetResponse) => void; onToast: (message: string, tone?: ToastState["tone"]) => void; serviceOrder: string }) {
	const [qty, setQty] = useState(String(line.qty));
	const [price, setPrice] = useState(String(line.selling_price));
	return <div className="grid gap-2 rounded-control border border-tec-border/15 bg-tec-field/45 p-3 sm:grid-cols-[minmax(0,1fr)_90px_120px_auto] sm:items-end"><div><p className="text-sm font-bold text-white">{line.description}</p><p className="text-xs text-tec-muted">{line.type === "part" ? `${line.source} · disponível ${line.available_qty ?? 0}` : line.category ?? "Serviço"}</p></div><label><span className="text-[10px] font-bold uppercase text-tec-muted">Qtd.</span><input className="tp-input mt-1" min="0.01" onChange={(event) => setQty(event.target.value)} step="0.01" type="number" value={qty} /></label><label><span className="text-[10px] font-bold uppercase text-tec-muted">Venda</span><input className="tp-input mt-1" min="0" onChange={(event) => setPrice(event.target.value)} step="0.01" type="number" value={price} /></label><div className="flex gap-1"><Button disabled={disabled} onClick={async () => { try { onChanged(await serviceOrders.updateTechnicalBudgetLine(serviceOrder, line.type, line.name, { qty: Number(qty), selling_price: Number(price) })); } catch (caught) { onToast(caught instanceof Error ? caught.message : "Não foi possível editar.", "error"); } }}>Salvar</Button><Button disabled={disabled} onClick={async () => { try { onChanged(await serviceOrders.removeTechnicalBudgetLine(serviceOrder, line.type, line.name)); } catch (caught) { onToast(caught instanceof Error ? caught.message : "Não foi possível remover.", "error"); } }}><XCircle size={16} /></Button></div></div>;
}

function TechnicalLineList({
  lines,
	 onRecordPartOutcome,
  title,
  type,
}: {
  lines: ServiceOrderBudgetLine[];
	 onRecordPartOutcome?: (line: ServiceOrderBudgetLine) => void;
  title: string;
  type: "service" | "part";
}) {
  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-bold text-white">{title}</h4>
        <span className="rounded-full bg-tec-field px-2 py-1 text-xs font-semibold text-tec-muted">{lines.length}</span>
      </div>
      <div className="overflow-hidden rounded-card border border-tec-border/15">
        {lines.length ? lines.map((line, index) => (
			<div className="flex flex-wrap items-center justify-between gap-3 border-b border-tec-border/15 bg-tec-field/40 px-3 py-3 text-sm last:border-0" key={`${line.name ?? line.item_code ?? title}-${index}`}>
            <div className="min-w-0">
              <p className="truncate font-semibold text-white">{line.description || line.item_code || "Item sem descrição"}</p>
              <p className="mt-1 text-xs text-tec-muted">
                {line.item_code ?? "Sem item"} · Qtd. {line.qty.toLocaleString("pt-BR")}
                {type === "service" && line.service_duration ? ` · ${line.service_duration} ${(line.duration_unit ?? "Horas").toLowerCase()}` : ""}
                {type === "part" && line.outcome ? ` · ${line.outcome}` : ""}
              </p>
            </div>
				<div className="flex shrink-0 items-center gap-2">
					{type === "service" && line.unit_price !== undefined ? <span className="text-sm font-bold text-tec-subtle">MO {formatCurrency(line.unit_price)}</span> : null}
					{type === "part" ? <TechnicalPartStatus line={line} /> : null}
					{type === "part" && !line.stock_entry && line.name && onRecordPartOutcome ? (
						<Button className="!min-h-8 !px-2.5 !py-1.5 text-xs" icon={<CheckCircle2 size={14} />} onClick={() => onRecordPartOutcome(line)}>
							Registrar
						</Button>
					) : null}
				</div>
          </div>
        )) : <p className="bg-tec-field/35 px-3 py-4 text-sm text-tec-muted">Nenhuma linha registrada.</p>}
      </div>
    </section>
  );
}

function TechnicalPartStatus({ line }: { line: ServiceOrderBudgetLine }) {
	if (line.stock_entry) {
		const lost = line.outcome === "Perdida";
		return <span className={cx("rounded-full px-2 py-1 text-xs font-bold", lost ? "bg-tec-red/15 text-tec-red" : "bg-tec-success/15 text-tec-success")}>{lost ? "Perdida" : "Usada"}</span>;
	}
	if (line.reservation) {
		return <span className="rounded-full bg-tec-blue/15 px-2 py-1 text-xs font-bold text-tec-blue">Reservada</span>;
	}
	return <span className="rounded-full bg-tec-field px-2 py-1 text-xs font-bold text-tec-muted">Pendente</span>;
}

function PartOutcomeModal({
	onClose,
	onSubmit,
	part,
}: {
	onClose: () => void;
	onSubmit: (outcome: "Usada no reparo" | "Perdida", lossReason?: string) => Promise<void>;
	part: ServiceOrderBudgetLine | null;
}) {
	const [outcome, setOutcome] = useState<"Usada no reparo" | "Perdida">("Usada no reparo");
	const [lossReason, setLossReason] = useState("");
	const [submitting, setSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!part) return;
		setOutcome("Usada no reparo");
		setLossReason("");
		setSubmitting(false);
		setError(null);
	}, [part]);

	async function submit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		if (outcome === "Perdida" && !lossReason) {
			setError("Selecione o motivo obrigatório da perda.");
			return;
		}
		setSubmitting(true);
		setError(null);
		try {
			await onSubmit(outcome, lossReason);
		} catch (caught) {
			setError(caught instanceof Error ? caught.message : "Não foi possível registrar a peça.");
		} finally {
			setSubmitting(false);
		}
	}

	return (
		<Modal className="max-w-lg" onClose={onClose} open={Boolean(part)} title="Registrar uso da peça">
			<form className="space-y-4" onSubmit={submit}>
				<div className="rounded-card border border-tec-border/15 bg-tec-field/45 p-4">
					<p className="font-bold text-white">{part?.description || part?.item_code}</p>
					<p className="mt-1 text-sm text-tec-muted">Quantidade: {part?.qty.toLocaleString("pt-BR") ?? "0"}. A baixa é executada pelo motor no estoque de Reparo.</p>
				</div>
				<div className="grid gap-2 sm:grid-cols-2">
					{(["Usada no reparo", "Perdida"] as const).map((value) => (
						<button className={cx("rounded-control border px-3 py-3 text-left text-sm font-bold transition", outcome === value ? "border-tec-orange bg-tec-orange text-tec-ink shadow-glow" : "border-tec-border/20 bg-tec-field text-tec-subtle hover:border-tec-orange/50")} key={value} onClick={() => setOutcome(value)} type="button">
							{value}
						</button>
					))}
				</div>
				{outcome === "Perdida" ? <label className="block"><span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Motivo da perda <span className="text-tec-orange">obrigatório</span></span><select className="tp-input" onChange={(event) => setLossReason(event.target.value)} required value={lossReason}><option value="">Selecione o motivo</option><option>Perda da loja</option><option>Responsabilidade do técnico</option><option>Garantia do fornecedor</option></select></label> : null}
				{error ? <p className="rounded-control border border-tec-red/35 bg-tec-red/10 px-3 py-2 text-sm font-semibold text-tec-red">{error}</p> : null}
				<div className="flex justify-end gap-2"><Button onClick={onClose}>Cancelar</Button><Button disabled={submitting || (outcome === "Perdida" && !lossReason)} icon={<CheckCircle2 size={16} />} type="submit" variant="primary">{submitting ? "Registrando..." : "Confirmar"}</Button></div>
			</form>
		</Modal>
	);
}

function ServiceOrderHero({
  detail,
  onBack,
  onOpenActions,
  onOpenAcceptance,
  onOpenBudgetEditor,
	onOpenQuoteSend,
	showBudgetAction = true,
	showActionsMenu = true,
}: {
  detail: ServiceOrderDetailResponse;
  onBack: () => void;
  onOpenActions: () => void;
  onOpenAcceptance?: (type: "Entrada" | "Retirada") => void;
  onOpenBudgetEditor: (type: BudgetLineType) => void;
	onOpenQuoteSend?: () => void;
	showBudgetAction?: boolean;
	showActionsMenu?: boolean;
}) {
  return (
    <Card className="overflow-hidden p-0">
      <div className="border-b border-tec-border/10 bg-tec-panel-strong/55 p-5">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <button
              className="mb-4 inline-flex items-center gap-2 text-sm font-bold text-tec-subtle transition hover:text-white"
              onClick={onBack}
              type="button"
            >
              <ArrowLeft size={17} />
              Voltar para a fila
            </button>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="tp-display text-3xl font-bold leading-tight text-white">{detail.name}</h2>
              <BadgeStatus status={detail.workflow_state} />
              {detail.priority ? (
                <span className="rounded-full border border-tec-border/15 bg-tec-field px-3 py-1 text-xs font-bold text-tec-subtle">
                  {detail.priority}
                </span>
              ) : null}
            </div>
            <p className="mt-3 max-w-4xl text-sm font-medium text-tec-subtle">
              {detail.reported_defect ?? "Sem defeito informado"}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 xl:justify-end">
            {showBudgetAction ? (
              <Button
                icon={<Plus size={17} />}
                onClick={() => onOpenBudgetEditor("service")}
                variant="primary"
              >
                Cadastrar orçamento
              </Button>
            ) : null}
            {showBudgetAction ? (
              <Button icon={<Package size={17} />} onClick={() => onOpenBudgetEditor("part")} variant="secondary">
                Adicionar peça
              </Button>
            ) : null}
            {detail.workflow_state === "Entrada criada" && onOpenAcceptance ? (
              <Button icon={<QrCode size={17} />} onClick={() => onOpenAcceptance("Entrada")} variant="secondary">
                Gerar aceite
              </Button>
            ) : null}
            {detail.workflow_state === "Aguardando aprovação" && detail.services.length + detail.parts.length > 0 && onOpenQuoteSend ? (
              <Button icon={<Send size={17} />} onClick={onOpenQuoteSend} variant="primary">
                Enviar orçamento
              </Button>
            ) : null}
            {detail.print_links.length ? <PrintPrimaryLink links={detail.print_links} /> : null}
            {showActionsMenu ? (
              <button
                className="grid h-10 w-10 place-items-center rounded-control border border-tec-border/15 bg-tec-field text-tec-subtle transition hover:border-tec-orange/50 hover:text-white"
                onClick={onOpenActions}
                title="Ações da OS"
                type="button"
              >
                <MoreHorizontal size={18} />
              </button>
            ) : null}
          </div>
        </div>
      </div>
      <WorkflowStepper detail={detail} />
    </Card>
  );
}

type ServiceOrderStageScreen = "entrada" | "diagnostico" | "aprovacao" | "execucao" | "retirada";

const SERVICE_ORDER_STAGE_SCREENS: Array<{
  key: ServiceOrderStageScreen;
  label: string;
  description: string;
  icon: typeof ClipboardCheck;
}> = [
  { key: "entrada", label: "Entrada", description: "Check-in e aceite", icon: ClipboardCheck },
  { key: "diagnostico", label: "Diagnóstico e orçamento", description: "Laudo, composição e envio", icon: SearchIcon },
  { key: "aprovacao", label: "Aprovação", description: "Decisão do cliente", icon: CheckCircle2 },
  { key: "execucao", label: "Execução", description: "Peças e reparo", icon: Wrench },
  { key: "retirada", label: "Retirada", description: "Pagamento e entrega", icon: CircleDollarSign },
];

function serviceOrderStageScreenForState(state: string | null): ServiceOrderStageScreen {
  if (state === "Entrada criada") return "entrada";
  if (state === "Em diagnóstico") return "diagnostico";
  if (["Em diagnóstico", "Diagnosticado — aguardando orçamento"].includes(state ?? "")) return "diagnostico";
  if (state === "Aguardando aprovação") return "aprovacao";
  if (["Aprovado", "Aguardando peça", "Em reparo", "Teste final"].includes(state ?? "")) return "execucao";
  return "retirada";
}

function ServiceOrderStageTabs({
  active,
  detail,
  onChange,
}: {
  active: ServiceOrderStageScreen;
  detail: ServiceOrderDetailResponse;
  onChange: (screen: ServiceOrderStageScreen) => void;
}) {
  const current = serviceOrderStageScreenForState(detail.workflow_state);
  const stageScreens = detail.caminho === "Rápido" ? SERVICE_ORDER_STAGE_SCREENS.filter((stage) => !["diagnostico", "aprovacao"].includes(stage.key)) : SERVICE_ORDER_STAGE_SCREENS;

  return (
    <Card className="p-2">
      <nav aria-label="Etapas da ordem de serviço" className="grid gap-1 sm:grid-cols-2 xl:grid-cols-6">
        {stageScreens.map(({ key, label, description, icon: Icon }) => {
          const selected = active === key;
          const isCurrent = current === key;
          return (
            <button
              className={cx(
                "flex min-h-16 items-center gap-3 rounded-control border px-3 py-2 text-left transition",
                selected
                  ? "border-tec-orange/70 bg-tec-orange/10 text-white shadow-glow"
                  : "border-transparent text-tec-subtle hover:border-tec-border/30 hover:bg-tec-field/60",
              )}
              key={key}
              onClick={() => onChange(key)}
              type="button"
            >
              <span className={cx("grid h-9 w-9 shrink-0 place-items-center rounded-control", selected ? "bg-tec-orange text-tec-ink" : "bg-tec-field text-tec-muted")}>
                <Icon size={18} />
              </span>
              <span className="min-w-0">
                <span className="flex items-center gap-2 text-sm font-bold">
                  {label}
                  {isCurrent ? <span className="rounded-full bg-tec-orange/15 px-2 py-0.5 text-[10px] font-bold uppercase text-tec-orange">Atual</span> : null}
                </span>
                <span className="mt-0.5 block text-xs text-tec-muted">{description}</span>
              </span>
            </button>
          );
        })}
      </nav>
    </Card>
  );
}

function ServiceOrderPersistentOverview({ detail }: { detail: ServiceOrderDetailResponse }) {
  const [open, setOpen] = useState(false);
  const device = [detail.device?.brand, detail.device?.model].filter(Boolean).join(" ") || detail.device?.name || "Não informado";
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-bold uppercase tracking-wide text-tec-muted">Visão geral da OS</p>
        <button className="text-xs font-bold text-tec-orange hover:text-white" onClick={() => setOpen((value) => !value)} type="button">{open ? "Recolher" : "Ver mais"}</button>
      </div>
      <div className="mt-3 flex items-center justify-between gap-3">
        <h3 className="text-lg font-bold text-white">{detail.name}</h3>
        <BadgeStatus status={detail.workflow_state} />
      </div>
      <dl className="mt-4 space-y-3 text-sm">
        <DetailLine label="Cliente" value={detail.customer?.customer_name ?? detail.customer?.name ?? "Não informado"} />
        <DetailLine label="Aparelho" value={device} />
        <DetailLine label="Técnico" value={detail.technician ?? "Não definido"} />
        {open ? <><DetailLine label="Prioridade" value={detail.priority ?? "Normal"} /><DetailLine label="Defeito relatado" value={detail.reported_defect ?? "Não informado"} /><DetailLine label="Prazo atual" value={detail.approval_deadline ? formatDate(detail.approval_deadline) : "Não definido"} /><DetailLine label="Atualizada" value={formatDate(detail.modified)} /></> : null}
      </dl>
    </Card>
  );
}

function ServiceOrderFinanceSnapshot({ detail }: { detail: ServiceOrderDetailResponse }) {
  const payments = detail.finance.payments.slice(-3).reverse();
  const situation = detail.finance.sales_invoice
    ? detail.finance.remaining_total > 0 ? "Saldo em aberto" : "Quitada"
    : detail.finance.paid_total > 0 ? "Sinal registrado" : "Sem cobrança emitida";
  return (
    <Card className="p-5">
      <p className="text-xs font-bold uppercase tracking-wide text-tec-muted">Financeiro desta OS</p>
      <p className="mt-2 text-sm font-bold text-white">{situation}</p>
      <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-3 xl:grid-cols-1">
        {[["Total", detail.finance.total_due], ["Pago", detail.finance.paid_total], ["Falta", detail.finance.remaining_total]].map(([label, value]) => <div className="rounded-control bg-tec-field/45 px-3 py-2" key={String(label)}><dt className="text-xs font-semibold text-tec-muted">{label}</dt><dd className="mt-1 font-bold text-tec-subtle">{formatCurrency(Number(value))}</dd></div>)}
      </dl>
      {payments.length ? <div className="mt-4 space-y-2 border-t border-tec-border/20 pt-3">{payments.map((payment) => <div className="flex items-center justify-between gap-3 text-xs" key={payment.name}><span className="truncate text-tec-muted">{payment.payment_mode || payment.kind}</span><strong className={payment.direction === "Saída" ? "text-tec-red" : "text-tec-success"}>{payment.direction === "Saída" ? "−" : "+"}{formatCurrency(payment.amount)}</strong></div>)}</div> : <p className="mt-4 text-xs text-tec-muted">Nenhum recebimento registrado.</p>}
    </Card>
  );
}

function ApprovalDecisionCard({
  detail,
  onOpenQuoteSend,
  onToast,
  onUpdated,
}: {
  detail: ServiceOrderDetailResponse;
  onOpenQuoteSend?: () => void;
  onToast: (msg: string, tone?: ToastState["tone"]) => void;
  onUpdated: (detail: ServiceOrderDetailResponse) => void;
}) {
  const [decisionMode, setDecisionMode] = useState<"idle" | "approve" | "reject">("idle");
  const [channel, setChannel] = useState<"WhatsApp" | "Telefone" | "Presencial" | "Link">("WhatsApp");
  const [rejectionReason, setRejectionReason] = useState("Preço elevado");
  const [notes, setNotes] = useState("");
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const status = detail.approval_status || (detail.workflow_state === "Aguardando aprovação" ? "Pendente" : detail.workflow_state);
  const isPending = status === "Pendente" || detail.workflow_state === "Aguardando aprovação";
  const isApproved = status === "Aprovado" || detail.workflow_state === "Aprovado";
  const isRejected = status === "Reprovado" || detail.workflow_state === "Reprovado";
  const isExpired = detail.workflow_state === "Orçamento expirado";

  const handleDecision = async (decision: "approve" | "reject") => {
    if (decision === "approve" && channel !== "Link" && !attachmentFile) {
      onToast("Anexe uma foto, imagem ou PDF real como comprovante da aprovação.", "error");
      return;
    }
    setSubmitting(true);
    try {
      const finalNotes = decision === "reject"
        ? (rejectionReason + (notes.trim() ? ` — ${notes.trim()}` : ""))
        : notes.trim();
      let attachment: string | undefined;
      if (decision === "approve" && channel !== "Link" && attachmentFile) {
        attachment = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Arquivo inválido."));
          reader.onerror = () => reject(new Error("Não foi possível ler o arquivo."));
          reader.readAsDataURL(attachmentFile);
        });
      }
      const updated = await serviceOrders.decideBudget(detail.name, {
        decision,
        channel,
        notes: finalNotes,
        attachment,
      });
      onUpdated(updated);
      onToast(decision === "approve" ? "Orçamento aprovado com sucesso!" : "Orçamento reprovado e registrado.", "success");
      setDecisionMode("idle");
      setNotes("");
      setAttachmentFile(null);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Falha ao registrar decisão do orçamento", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-tec-border/15 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-white">Decisão do Orçamento</h3>
            {isApproved ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
                <CheckCircle2 size={13} /> Aprovado
              </span>
            ) : isRejected ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 px-2.5 py-0.5 text-xs font-semibold text-rose-400">
                <XCircle size={13} /> Reprovado
              </span>
            ) : isExpired ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-400">
                <Clock3 size={13} /> Validade Expirada
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-400">
                <Hourglass size={13} /> Aguardando Decisão
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-tec-muted">
            {isPending && "Proposta enviada ao cliente. Registre a resposta obtida ou reenvie o link."}
            {isApproved && "Orçamento formalmente aceito. A OS está liberada para execução técnica."}
            {isRejected && "Cliente recusou a proposta. Encaminhe o aparelho para retirada sem reparo."}
            {isExpired && "Prazo de validade esgotado. Renove a proposta ou finalize o atendimento."}
          </p>
        </div>
        {isPending && onOpenQuoteSend ? (
          <Button icon={<Send size={15} />} onClick={onOpenQuoteSend} variant="secondary">
            Reenviar orçamento
          </Button>
        ) : null}
      </div>

      {isPending && decisionMode === "idle" && (
        <div className="mt-4 space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-control border border-tec-border/20 bg-tec-field/30 p-3">
              <span className="text-xs text-tec-muted">Status de envio</span>
              <p className="mt-1 font-semibold text-white">
                {detail.quote_sent ? "Enviado ao cliente" : "Não enviado"}
              </p>
            </div>
            <div className="rounded-control border border-tec-border/20 bg-tec-field/30 p-3">
              <span className="text-xs text-tec-muted">Canal preferencial</span>
              <p className="mt-1 font-semibold text-white">{detail.approval.channel || "WhatsApp / Link"}</p>
            </div>
            <div className="rounded-control border border-tec-border/20 bg-tec-field/30 p-3">
              <span className="text-xs text-tec-muted">Total da proposta</span>
              <p className="mt-1 font-bold text-tec-orange">
                {formatCurrency(detail.totals.grand_total)}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              className="bg-emerald-600 hover:bg-emerald-500 text-white"
              icon={<CheckCircle2 size={16} />}
              onClick={() => { setDecisionMode("approve"); setNotes(""); }}
              type="button"
            >
              Registrar Aprovação no Balcão
            </Button>
            <Button
              className="border-rose-500/40 text-rose-400 hover:bg-rose-500/10"
              icon={<XCircle size={16} />}
              onClick={() => { setDecisionMode("reject"); setNotes(""); }}
              type="button"
              variant="secondary"
            >
              Registrar Recusa / Reprovação
            </Button>
          </div>
        </div>
      )}

      {isPending && decisionMode === "approve" && (
        <form
          className="mt-4 rounded-control border border-emerald-500/30 bg-emerald-950/10 p-4 space-y-3"
          onSubmit={(e) => { e.preventDefault(); void handleDecision("approve"); }}
        >
          <h4 className="text-sm font-bold text-emerald-400">Confirmar Aprovação do Orçamento</h4>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-tec-muted">Canal da autorização</label>
              <select
                className="tp-input mt-1 w-full"
                onChange={(e) => setChannel(e.target.value as "WhatsApp" | "Telefone" | "Presencial" | "Link")}
                value={channel}
              >
                <option value="WhatsApp">WhatsApp</option>
                <option value="Presencial">Presencial / Balcão</option>
                <option value="Telefone">Ligação Telefônica</option>
              </select>
              <p className="mt-1 text-[11px] text-tec-muted">
                Aprovação via Link Digital só acontece quando o próprio cliente decide pelo link de rastreio — não é um canal que o balcão registra manualmente.
              </p>
            </div>
            <div>
              <label className="block text-xs font-semibold text-tec-muted">Observações (opcional)</label>
              <input
                className="tp-input mt-1 w-full"
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Ex.: Aprovado pelo cliente sem alterações"
                value={notes}
              />
            </div>
          </div>
          {channel !== "Link" && (
            <div>
              <label className="block text-xs font-semibold text-tec-amber">
                Comprovante / Documento anexo (obrigatório para aprovação manual)
              </label>
              <input
                accept="image/jpeg,image/png,application/pdf"
                className="tp-input mt-1 w-full"
                onChange={(e) => setAttachmentFile(e.target.files?.[0] ?? null)}
                type="file"
              />
              <p className="mt-1 text-[11px] text-tec-muted">
                Foto, imagem ou PDF real (print da conversa, áudio transcrito, termo físico escaneado). Sem o link digital, a comprovação é anexada ao histórico permanente da OS.
              </p>
            </div>
          )}
          <div className="flex items-center gap-2 pt-2">
            <Button disabled={submitting || (channel !== "Link" && !attachmentFile)} type="submit" variant="primary">
              {submitting ? "Gravando..." : "Confirmar Aprovação"}
            </Button>
            <Button disabled={submitting} onClick={() => setDecisionMode("idle")} type="button" variant="secondary">
              Cancelar
            </Button>
          </div>
        </form>
      )}

      {isPending && decisionMode === "reject" && (
        <form
          className="mt-4 rounded-control border border-rose-500/30 bg-rose-950/10 p-4 space-y-3"
          onSubmit={(e) => { e.preventDefault(); void handleDecision("reject"); }}
        >
          <h4 className="text-sm font-bold text-rose-400">Registrar Reprovação / Recusa do Orçamento</h4>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-semibold text-tec-muted">Motivo da recusa (obrigatório)</label>
              <select
                className="tp-input mt-1 w-full"
                onChange={(e) => setRejectionReason(e.target.value)}
                value={rejectionReason}
              >
                <option value="Preço elevado">Preço elevado / Achou caro</option>
                <option value="Inviável financeiramente">Inviável financeiramente</option>
                <option value="Prefere comprar novo">Prefere comprar novo</option>
                <option value="Prazo incompatível">Prazo incompatível</option>
                <option value="Desistiu do reparo">Desistiu do reparo</option>
                <option value="Outro">Outro motivo</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-tec-muted">Canal da resposta</label>
              <select
                className="tp-input mt-1 w-full"
                onChange={(e) => setChannel(e.target.value as "WhatsApp" | "Telefone" | "Presencial" | "Link")}
                value={channel}
              >
                <option value="WhatsApp">WhatsApp</option>
                <option value="Balcão">Presencial / Balcão</option>
                <option value="Telefone">Ligação Telefônica</option>
                <option value="Link">Link Digital / Portal</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-tec-muted">Observações adicionais</label>
            <input
              className="tp-input mt-1 w-full"
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Detalhes da recusa..."
              value={notes}
            />
          </div>
          <div className="flex items-center gap-2 pt-2">
            <Button className="bg-rose-600 hover:bg-rose-500 text-white" disabled={submitting} type="submit">
              {submitting ? "Gravando..." : "Confirmar Reprovação"}
            </Button>
            <Button disabled={submitting} onClick={() => setDecisionMode("idle")} type="button" variant="secondary">
              Cancelar
            </Button>
          </div>
        </form>
      )}

      {(isApproved || isRejected || isExpired) && (
        <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
          <div className="rounded-control border border-tec-border/20 bg-tec-field/30 p-3">
            <dt className="text-xs text-tec-muted">Canal da decisão</dt>
            <dd className="mt-1 font-semibold text-white">{detail.approval.channel || "Não informado"}</dd>
          </div>
          <div className="rounded-control border border-tec-border/20 bg-tec-field/30 p-3">
            <dt className="text-xs text-tec-muted">Registrado por</dt>
            <dd className="mt-1 font-semibold text-white">{detail.approval.approved_by_attendant || "Sistema"}</dd>
          </div>
          <div className="rounded-control border border-tec-border/20 bg-tec-field/30 p-3">
            <dt className="text-xs text-tec-muted">Data da decisão</dt>
            <dd className="mt-1 font-semibold text-white">
              {detail.approval.approval_date ? formatDate(detail.approval.approval_date) : "Não informada"}
            </dd>
          </div>
          <div className="rounded-control border border-tec-border/20 bg-tec-field/30 p-3">
            <dt className="text-xs text-tec-muted">Total final</dt>
            <dd className="mt-1 font-bold text-tec-orange">{formatCurrency(detail.totals.grand_total)}</dd>
          </div>
        </dl>
      )}

      {detail.approval.notes ? (
        <div className="mt-3 rounded-control border border-tec-border/20 bg-tec-field/20 p-3 text-xs text-tec-muted">
          <span className="font-semibold text-tec-subtle">Notas da decisão:</span> {detail.approval.notes}
        </div>
      ) : null}
    </Card>
  );
}

function QuoteFollowUpCard({
  detail,
  onToast,
  onUpdated,
}: {
  detail: ServiceOrderDetailResponse;
  onToast: (msg: string, tone?: ToastState["tone"]) => void;
  onUpdated: (detail: ServiceOrderDetailResponse) => void;
}) {
  const [channel, setChannel] = useState("WhatsApp");
  const [result, setResult] = useState("Sem resposta");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleRecord = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const updated = await serviceOrders.recordFollowUp(detail.name, channel, result, notes);
      onUpdated(updated);
      onToast("Follow-up registrado com sucesso no histórico da OS.", "success");
      setNotes("");
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Falha ao registrar follow-up", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="p-5">
      <div className="border-b border-tec-border/15 pb-3">
        <h3 className="text-lg font-bold text-white">Follow-up de Contato com o Cliente</h3>
        <p className="mt-1 text-xs text-tec-muted">
          Registre tentativas de contato, negociações ou dúvidas do cliente enquanto o orçamento está em análise.
        </p>
      </div>
      <form className="mt-4 space-y-3" onSubmit={handleRecord}>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-semibold text-tec-muted">Canal utilizado</label>
            <select
              className="tp-input mt-1 w-full"
              onChange={(e) => setChannel(e.target.value)}
              value={channel}
            >
              <option value="WhatsApp">WhatsApp</option>
              <option value="Ligação Telefônica">Ligação Telefônica</option>
              <option value="Presencial / Balcão">Presencial / Balcão</option>
              <option value="E-mail">E-mail</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-tec-muted">Resultado do contato</label>
            <select
              className="tp-input mt-1 w-full"
              onChange={(e) => setResult(e.target.value)}
              value={result}
            >
              <option value="Sem resposta">Sem resposta / Não atendeu</option>
              <option value="Pediu mais tempo">Pediu mais tempo para decidir</option>
              <option value="Dúvida técnica">Dúvida sobre peças ou serviços</option>
              <option value="Negociando desconto">Negociando desconto / parcelamento</option>
              <option value="Vai decidir hoje">Prometeu responder ainda hoje</option>
            </select>
          </div>
        </div>
        <div>
          <label className="block text-xs font-semibold text-tec-muted">Observações (opcional)</label>
          <input
            className="tp-input mt-1 w-full"
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Ex.: Cliente pediu para ligar novamente às 17h"
            value={notes}
          />
        </div>
        <div className="flex justify-end pt-1">
          <Button disabled={submitting} type="submit" variant="secondary">
            {submitting ? "Gravando..." : "Registrar Follow-up"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function ServiceOrderStageScreenContent({
  active,
  canViewDirectorFinancial,
  customerLabel,
  detail,
  deviceLabel,
  onOpenAcceptance,
  onOpenBudgetEditor,
  onOpenHistory,
  onOpenQuoteSend,
	onCompleteDiagnosis,
  onToast,
  onUpdated,
  whatsappUrl,
}: {
  active: ServiceOrderStageScreen;
  canViewDirectorFinancial: boolean;
  customerLabel: string;
  detail: ServiceOrderDetailResponse;
  deviceLabel: string;
  onOpenAcceptance: (type: "Entrada" | "Retirada") => void;
  onOpenBudgetEditor: (type: BudgetLineType) => void;
  onOpenHistory: () => void;
  onOpenQuoteSend: () => void;
	onCompleteDiagnosis: (problemFound: string, pricingResponsibility: "Técnico" | "Balcão") => Promise<void>;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  onUpdated: (detail: ServiceOrderDetailResponse) => void;
  whatsappUrl: string | null;
}) {
  if (active === "entrada") {
	const editEntry = async () => {
		const reportedDefect = window.prompt("Defeito relatado", detail.reported_defect ?? "");
		if (reportedDefect === null) return;
		const physicalState = window.prompt("Estado físico", detail.physical_state ?? "");
		if (physicalState === null) return;
		const contactName = window.prompt("Contato desta OS", detail.os_contact_name ?? "");
		if (contactName === null) return;
		const contactPhone = window.prompt("Telefone do contato desta OS", detail.os_contact_phone ?? "");
		if (contactPhone === null) return;
		const credential = window.prompt("Nova senha/PIN/padrão (deixe vazio para manter a atual)", "");
		if (credential === null) return;
		try {
			const updated = await serviceOrders.updateEntry(detail.name, {
				reported_defect: reportedDefect,
				physical_state: physicalState,
				os_contact_name: contactName,
				os_contact_phone: contactPhone,
				device_access_type: detail.device_access_type || "PIN",
				entry_operating_condition: detail.entry_operating_condition || "Liga e permite teste",
				...(credential ? { device_access_credential: credential } : {}),
			});
			onUpdated(updated);
			onToast("Informações da Entrada atualizadas e registradas no histórico.");
		} catch (error) {
			onToast(error instanceof Error ? error.message : "Não foi possível editar a Entrada.", "error");
		}
	};
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3"><StageHeading title="Entrada" description="Conferência do cliente, aparelho e evidências da recepção." /><Button onClick={() => void editEntry()} variant="secondary">Editar informações</Button></div>
        <div className="grid gap-4 lg:grid-cols-2">
          <IdentityCard
            action={whatsappUrl ? <a className="mt-4 inline-flex min-h-10 items-center justify-center gap-2 rounded-control border border-tec-whatsapp/35 bg-tec-whatsapp/10 px-4 text-sm font-bold text-tec-whatsapp transition hover:bg-tec-whatsapp/20" href={whatsappUrl} rel="noreferrer" target="_blank"><WhatsAppLogo size={17} />Abrir WhatsApp</a> : undefined}
            icon={<UserRound size={20} />}
            lines={[["Cliente", customerLabel], ["Contato desta OS", detail.os_contact_name || customerLabel], ["Telefone desta OS", detail.os_contact_phone || detail.customer?.custom_whatsapp || detail.customer?.mobile_no || "Não informado"], ["E-mail", detail.customer?.email_id ?? "Não informado"], ["Atendente", detail.attendant ?? "Não definido"]]}
            title="Cliente"
          />
          <IdentityCard icon={<Smartphone size={20} />} lines={[["Aparelho", deviceLabel], ["IMEI / Serial", detail.device?.imei_serial ?? "Não informado"], ["Capacidade", detail.device?.capacity ?? "Não informada"], ["Condição na entrada", detail.entry_operating_condition ?? detail.physical_state ?? "Não informada"]]} title="Aparelho" />
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <ServiceOrderAttendanceCard detail={detail} />
          <StageAcceptanceCard detail={detail} onOpenAcceptance={onOpenAcceptance} />
        </div>
        <TimelineCard events={detail.timeline} onOpenHistory={onOpenHistory} />
      </div>
    );
  }

  if (active === "diagnostico") {
		const hasBudget = detail.services.length + detail.parts.length > 0;
    return (
      <div className="space-y-4">
        <StageHeading title="Diagnóstico e orçamento" description="Laudo técnico, prazo estimado e composição comercial em uma única tela de bancada." />
        <DiagnosisTechnicalCard detail={detail} onComplete={onCompleteDiagnosis} onToast={onToast} onUpdated={onUpdated} />
        <BudgetCard detail={detail} onOpenBudgetEditor={onOpenBudgetEditor} onToast={onToast} onUpdated={onUpdated} />
        <Card className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <h3 className="text-lg font-bold text-white">Enviar orçamento ao cliente</h3>
            <p className="mt-1 text-sm text-tec-muted">O motor exige diagnóstico salvo e ao menos um item de orçamento antes de avançar para aprovação.</p>
          </div>
          <Button disabled={!hasBudget || !detail.diagnosis.problem_found?.trim()} icon={<Send size={17} />} onClick={onOpenQuoteSend} title={!hasBudget ? "Inclua ao menos um serviço ou peça no orçamento." : undefined} variant="primary">Enviar ao cliente</Button>
        </Card>
        <TimelineCard events={detail.timeline} onOpenHistory={onOpenHistory} />
      </div>
    );
  }

  if (active === "aprovacao") {
    return (
      <div className="space-y-4">
        <StageHeading title="Aprovação" description="Decisão do cliente, evidências de aceite e próximo encaminhamento." />
        <ApprovalDecisionCard detail={detail} onOpenQuoteSend={onOpenQuoteSend} onToast={onToast} onUpdated={onUpdated} />
        {detail.approval_status === "Pendente" || detail.workflow_state === "Aguardando aprovação" ? (
          <QuoteFollowUpCard detail={detail} onToast={onToast} onUpdated={onUpdated} />
        ) : null}
        <BudgetCard detail={detail} onOpenBudgetEditor={onOpenBudgetEditor} onToast={onToast} onUpdated={onUpdated} />
        <TimelineCard events={detail.timeline} onOpenHistory={onOpenHistory} />
      </div>
    );
  }

  if (active === "execucao") {
    return (
      <div className="space-y-4">
        <StageHeading title="Execução" description="Acompanhe serviços, reservas, reparo e testes desta OS." />
        <Card className="p-5"><StageLineList lines={detail.services} title="Serviços planejados" /><div className="mt-5"><StageLineList lines={detail.parts} title="Peças e reservas" type="part" /></div></Card>
        <TimelineCard events={detail.timeline} onOpenHistory={onOpenHistory} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <StageHeading title="Retirada" description="Pagamentos reais, saldo da OS e conclusão de retirada." />
      <ServiceOrderPaymentCard canViewDirectorFinancial={canViewDirectorFinancial} detail={detail} onToast={onToast} onUpdated={onUpdated} />
      <Card className="p-5"><h3 className="text-lg font-bold text-white">Retirada</h3><dl className="mt-4 space-y-3 text-sm"><DetailLine label="Status" value={detail.pickup.without_repair ? "Retirada sem reparo" : detail.pickup.pickup_date ? "Entregue" : "Aguardando retirada"} /><DetailLine label="Data" value={detail.pickup.pickup_date ? formatDate(detail.pickup.pickup_date) : "Ainda não registrada"} /><DetailLine label="Aceite" value={detail.pickup.has_signature ? "Assinatura registrada" : "Pendente"} /></dl></Card>
    </div>
  );
}

function DiagnosisTechnicalCard({
	detail,
	onComplete,
	onToast,
	onUpdated,
}: {
	detail: ServiceOrderDetailResponse;
	onComplete: (problemFound: string, pricingResponsibility: "Técnico" | "Balcão") => Promise<void>;
	onToast: (message: string, tone?: ToastState["tone"]) => void;
	onUpdated: (detail: ServiceOrderDetailResponse) => void;
}) {
	const isDiagnosing = detail.workflow_state === "Em diagnóstico";
	const [problemFound, setProblemFound] = useState(detail.diagnosis.problem_found ?? "");
	const [responsibility, setResponsibility] = useState<"Técnico" | "Balcão">(detail.diagnosis.default_pricing_responsibility);
	const [editing, setEditing] = useState(isDiagnosing || !detail.diagnosis.problem_found);
	const [saving, setSaving] = useState(false);

	useEffect(() => {
		setProblemFound(detail.diagnosis.problem_found ?? "");
		setEditing(detail.workflow_state === "Em diagnóstico" || !detail.diagnosis.problem_found);
	}, [detail.diagnosis.problem_found, detail.workflow_state]);

	const saveDraft = async () => {
		if (!problemFound.trim()) {
			onToast("Informe o laudo técnico antes de salvar.", "error");
			return;
		}
		setSaving(true);
		try {
			const updated = await serviceOrders.saveDiagnosis(detail.name, problemFound.trim());
			onUpdated(updated);
			onToast("Laudo técnico salvo.");
			if (!isDiagnosing) setEditing(false);
		} catch (err) {
			onToast(err instanceof Error ? err.message : "Falha ao salvar laudo.", "error");
		} finally {
			setSaving(false);
		}
	};

	const handleComplete = async () => {
		if (!problemFound.trim()) {
			onToast("Informe o laudo técnico antes de concluir.", "error");
			return;
		}
		setSaving(true);
		try {
			await onComplete(problemFound.trim(), responsibility);
			setEditing(false);
		} catch (err) {
			onToast(err instanceof Error ? err.message : "Falha ao concluir diagnóstico.", "error");
		} finally {
			setSaving(false);
		}
	};

	return (
		<Card className="p-5">
			<div className="flex flex-wrap items-center justify-between gap-3 border-b border-tec-border/15 pb-4">
				<div className="flex items-center gap-3">
					<div className="grid size-10 place-items-center rounded-control bg-tec-orange/15 text-tec-orange">
						<Wrench size={20} />
					</div>
					<div>
						<h3 className="text-lg font-bold text-white">Laudo Técnico</h3>
						<p className="text-xs text-tec-muted">
							Defeito constatado e parecer da bancada técnica
						</p>
					</div>
				</div>
				<div className="flex items-center gap-2">
					<span className={`rounded-full px-3 py-1 text-xs font-bold ${
						detail.diagnosis.problem_found ? "bg-tec-success/20 text-tec-success" : "bg-tec-amber/20 text-tec-amber"
					}`}>
						{detail.diagnosis.problem_found ? `Registrado em ${formatDate(detail.diagnosis.diagnosis_date ?? detail.modified)}` : "Diagnóstico pendente"}
					</span>
					{!editing && !detail.totals.quote_locked ? (
						<Button className="px-3 py-1 text-xs" onClick={() => setEditing(true)} variant="secondary">
							Editar laudo
						</Button>
					) : null}
				</div>
			</div>

			{editing ? (
				<div className="mt-4 space-y-4">
					<div>
						<label className="block text-sm font-semibold text-white">Defeito constatado / Parecer técnico</label>
						<p className="mt-1 text-xs text-tec-muted">Descreva o resultado da análise e os reparos necessários para a solução.</p>
						<textarea
							className="tp-input mt-2 min-h-[100px] w-full resize-y"
							onChange={(e) => setProblemFound(e.target.value)}
							placeholder="Ex.: Tela trincada com touch inoperante e bateria com ciclo degradado (74% de saúde). Necessária troca da tela e substituição da bateria."
							value={problemFound}
						/>
					</div>

					{isDiagnosing ? (
						<div className="rounded-control border border-tec-border/20 bg-tec-field/40 p-4">
							<label className="block text-sm font-semibold text-white">Encaminhamento da Precificação (Bloco K)</label>
							<p className="mt-1 text-xs text-tec-muted">Defina quem é responsável por orçar as peças e serviços desta OS.</p>
							<select
								className="tp-input mt-2"
								onChange={(event) => setResponsibility(event.target.value as "Técnico" | "Balcão")}
								value={responsibility}
							>
								<option disabled={!detail.diagnosis.technician_pricing_available} value="Técnico">
									Técnico continua precificando{!detail.diagnosis.technician_pricing_available ? " (exige papel técnico)" : ""}
								</option>
								<option value="Balcão">Encaminhar ao Balcão / Atendente</option>
							</select>
						</div>
					) : null}

					<div className="flex justify-end gap-3 pt-2">
						{!isDiagnosing ? (
							<Button onClick={() => setEditing(false)} variant="ghost">Cancelar</Button>
						) : null}
						<Button disabled={saving || !problemFound.trim()} onClick={saveDraft} variant="secondary">
							{saving ? "Salvando..." : "Salvar rascunho"}
						</Button>
						{isDiagnosing ? (
							<Button disabled={saving || !problemFound.trim()} icon={<ArrowRight size={17} />} onClick={handleComplete} variant="primary">
								{saving ? "Concluindo..." : "Concluir e repassar"}
							</Button>
						) : null}
					</div>
				</div>
			) : (
				<div className="mt-4 space-y-3">
					<p className="rounded-control bg-tec-field/50 p-4 text-sm leading-6 text-tec-subtle">
						{detail.diagnosis.problem_found}
					</p>
					<HandoffStatus detail={detail} />
				</div>
			)}
		</Card>
	);
}

function HandoffStatus({ detail }: { detail: ServiceOrderDetailResponse }) {
	if (!detail.diagnosis.pricing_responsibility) return null;
	return <Card className="border-tec-amber/30 bg-tec-amber/5 p-4">
		<p className="text-xs font-bold uppercase tracking-wide text-tec-amber">Repasse explícito</p>
		<p className="mt-2 text-sm font-bold text-white">Precificação com: {detail.diagnosis.pricing_responsibility}</p>
		<p className="mt-1 text-xs text-tec-muted">Diagnóstico concluído por {detail.diagnosis.completed_by ?? "usuário não identificado"}{detail.diagnosis.completed_at ? ` em ${formatDate(detail.diagnosis.completed_at)}` : ""}.</p>
		{detail.diagnosis.budget_review_required ? <p className="mt-2 text-xs font-bold text-tec-orange">Diagnóstico reaberto: revise o orçamento antes de enviar. A versão já enviada não foi invalidada.</p> : null}
	</Card>;
}

function StageHeading({ description, title }: { description: string; title: string }) {
  return <Card className="p-5"><p className="text-xs font-bold uppercase tracking-wide text-tec-orange">Área da etapa</p><h2 className="mt-2 text-2xl font-bold text-white">{title}</h2><p className="mt-2 text-sm text-tec-subtle">{description}</p></Card>;
}

function StageAcceptanceCard({ detail, onOpenAcceptance }: { detail: ServiceOrderDetailResponse; onOpenAcceptance: (type: "Entrada" | "Retirada") => void }) {
  const type = detail.workflow_state === "Pronto para retirada" ? "Retirada" : "Entrada";
  const status = detail.acceptance[type];
  if (status.completed) {
    return <Card className="border-emerald-500/30 bg-emerald-950/10 p-5">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="text-emerald-400" size={18} />
        <h3 className="text-lg font-bold text-white">Aceite de {type.toLowerCase()} concluído</h3>
      </div>
      <p className="mt-2 text-sm text-tec-subtle">
        {status.method === "Físico" ? "Via física arquivada" : "Concluído por link digital"}
        {status.completed_by ? ` · por ${status.completed_by}` : ""}
        {status.completed_on ? ` · em ${formatDate(status.completed_on)}` : ""}
      </p>
      <Button className="mt-4" icon={<QrCode size={17} />} onClick={() => onOpenAcceptance(type)} variant="ghost">Gerar novo aceite</Button>
    </Card>;
  }
  return <Card className="p-5"><h3 className="text-lg font-bold text-white">Aceite do cliente</h3><p className="mt-2 text-sm text-tec-subtle">Gere o link digital ou arquive a folha física assinada. O motor valida a evidência antes do avanço.</p><Button className="mt-4" icon={<QrCode size={17} />} onClick={() => onOpenAcceptance(type)} variant="secondary">{type === "Entrada" ? "Gerar aceite de entrada" : "Gerar aceite de retirada"}</Button></Card>;
}

function StageLineList({ lines, title, type = "service" }: { lines: ServiceOrderBudgetLine[]; title: string; type?: "service" | "part" }) {
  return <section><div className="mb-3 flex items-center justify-between"><h3 className="text-lg font-bold text-white">{title}</h3><span className="rounded-full bg-tec-field px-2.5 py-1 text-xs font-bold text-tec-muted">{lines.length}</span></div>{lines.length ? <div className="overflow-hidden rounded-card border border-tec-border/15">{lines.map((line, index) => <div className="flex flex-wrap items-center justify-between gap-3 border-b border-tec-border/15 bg-tec-field/45 px-4 py-3 last:border-0" key={line.name ?? `${title}-${index}`}><div className="min-w-0"><p className="font-semibold text-white">{line.description || line.item_code || "Item sem descrição"}</p><p className="mt-1 text-xs text-tec-muted">Qtd. {line.qty.toLocaleString("pt-BR")}{type === "part" && line.outcome ? ` · ${line.outcome}` : ""}</p></div>{type === "part" ? <TechnicalPartStatus line={line} /> : <span className="text-sm font-bold text-tec-subtle">{formatCurrency(line.amount ?? (line.unit_price ?? 0) * line.qty)}</span>}</div>)}</div> : <p className="rounded-card border border-dashed border-tec-border/20 p-4 text-sm text-tec-muted">Nenhum item registrado nesta OS.</p>}</section>;
}

const COMPLETE_SERVICE_ORDER_STEPS = ["Entrada", "Diagnóstico e orçamento", "Aprovação", "Execução", "Pago", "Retirada"];
const FAST_SERVICE_ORDER_STEPS = ["Entrada / preço", "Execução", "Pago", "Retirada"];

function serviceOrderSteps(detail: ServiceOrderDetailResponse) {
  return detail.caminho === "Rápido" ? FAST_SERVICE_ORDER_STEPS : COMPLETE_SERVICE_ORDER_STEPS;
}

function WorkflowStepper({ detail }: { detail: ServiceOrderDetailResponse }) {
  const steps = serviceOrderSteps(detail);
  const activeIndex = serviceOrderStepIndex(detail.workflow_state, detail.caminho);
  const subtitles = serviceOrderStepSubtitles(detail, activeIndex, steps);

  return (
    <div className="grid gap-2 p-4 xl:grid-cols-5">
      {steps.map((step, index) => {
        const done = index < activeIndex;
        const active = index === activeIndex;
        const StepIcon = workflowStepIcon(index);
        return (
          <div
            className={cx(
              "relative rounded-control border p-3 transition md:after:absolute md:after:-right-2 md:after:top-1/2 md:after:h-px md:after:w-4 md:after:bg-tec-border/25 md:last:after:hidden",
              active
                ? "border-tec-orange/60 bg-tec-orange/10 shadow-glow"
                : done
                  ? "border-tec-success/20 bg-tec-success/5"
                  : "border-tec-border/10 bg-tec-field/35",
            )}
            key={step}
          >
            <div className="flex items-center gap-2">
              <span
                className={cx(
                  "grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold",
                  active
                    ? "bg-tec-orange text-tec-ink"
                    : done
                      ? "bg-tec-success/20 text-tec-success"
                      : "bg-tec-field text-tec-muted",
                )}
              >
                {done ? <CheckCircle2 size={15} /> : active ? index + 1 : <StepIcon size={14} />}
              </span>
              <span>
                <span className={cx("block text-xs font-bold", active ? "text-tec-orange" : done ? "text-tec-success" : "text-tec-muted")}>
                  {step}
                </span>
                <span className="mt-0.5 block text-[11px] font-semibold text-tec-muted">{subtitles[index]}</span>
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function WorkflowSideStepper({ detail }: { detail: ServiceOrderDetailResponse }) {
  const steps = serviceOrderSteps(detail);
  const activeIndex = serviceOrderStepIndex(detail.workflow_state, detail.caminho);
  const subtitles = serviceOrderStepSubtitles(detail, activeIndex, steps);

  return (
    <Card className="p-4">
      <p className="text-xs font-bold uppercase tracking-wide text-tec-muted">Etapas do reparo</p>
      <ol className="mt-4 space-y-0">
        {steps.map((step, index) => {
          const done = index < activeIndex;
          const active = index === activeIndex;
          const StepIcon = workflowStepIcon(index);
          return (
            <li className="relative flex min-h-12 gap-3 pb-3 last:pb-0" key={step}>
              {index < steps.length - 1 ? <span className={cx("absolute left-3.5 top-7 h-[calc(100%-16px)] w-px", done ? "bg-tec-success/50" : "bg-tec-border/30")} /> : null}
              <span className={cx(
                "relative z-10 grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold",
                active ? "bg-tec-orange text-tec-ink shadow-glow" : done ? "bg-tec-success/20 text-tec-success" : "bg-tec-field text-tec-muted",
              )}>
                {done ? <CheckCircle2 size={15} /> : active ? index + 1 : <StepIcon size={14} />}
              </span>
              <span className="min-w-0 pt-0.5">
                <span className={cx("block text-sm font-bold", active ? "text-tec-orange" : done ? "text-tec-success" : "text-tec-subtle")}>{step}</span>
                <span className="mt-0.5 block text-xs text-tec-muted">{active ? "Etapa atual" : subtitles[index]}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}

function workflowStepIcon(index: number) {
  return [ClipboardCheck, SearchIcon, Send, Wrench, Package][index] ?? FileText;
}

function serviceOrderStepIndex(state: string | null, path: "Rápido" | "Completo" = "Completo") {
  if (path === "Rápido") {
    if (state === "Entrada criada") return 0;
    if (["Em reparo", "Teste final"].includes(state ?? "")) return 1;
    if (state === "Pronto para retirada") return 2;
    return 3;
  }
  if (state === "Entrada criada") {
    return 0;
  }
  if (["Em diagnóstico", "Diagnosticado — aguardando orçamento"].includes(state ?? "")) {
    return 1;
  }
  if (state === "Aguardando aprovação") {
    return 2;
  }
  if (["Aprovado", "Aguardando peça", "Em reparo", "Teste final"].includes(state ?? "")) {
    return 3;
  }
  if (["Pronto para retirada", "Entregue", "Cancelado", "Reprovado", "Orçamento expirado", "Sem conserto"].includes(state ?? "")) {
    return state === "Pronto para retirada" ? 4 : 5;
  }
  return 1;
}

function serviceOrderStepSubtitles(detail: ServiceOrderDetailResponse, activeIndex: number, steps: string[]) {
  return steps.map((step, index) => {
    if (step === "Entrada") {
      return formatDate(detail.entry_date);
    }
    if (index < activeIndex) {
      return "Concluída";
    }
    if (index === activeIndex) {
      return step === "Aprovação" ? "Pendente" : "Em andamento";
    }
    return "Pendente";
  });
}

function NextActionCard({
  actions,
  blockedTransitions,
  detail,
  onOpenFlow,
  onOpenHistory,
  onOpenQuoteSend,
  onRefresh,
  onSimpleMove,
  onStartNoRepairPickup,
	onRequestApproval,
}: {
  actions: ServiceOrderWorkflowAction[];
  blockedTransitions: Record<string, string>;
  detail: ServiceOrderDetailResponse;
  onOpenFlow: (flow: "approve" | "reject" | "pickup") => void;
  onOpenHistory: () => void;
  onOpenQuoteSend: () => void;
  onRefresh: () => void;
  onSimpleMove: (nextState: string) => Promise<void>;
  onStartNoRepairPickup: () => void;
  onRequestApproval: (targetState: string) => void;
}) {
  const action = nextRecommendedAction(detail);
  const isQuoteSendAction = action.kind === "quote-send";
  const isNoRepairPickupAction = action.kind === "no-repair-pickup";
  const buttonIcon = action.flow ? <ArrowRight size={17} /> : isQuoteSendAction ? <Send size={17} /> : isNoRepairPickupAction ? <PackageCheck size={17} /> : <RefreshCw size={17} />;
  const [movingTo, setMovingTo] = useState<string | null>(null);

  async function handleWorkflowAction(workflowAction: ServiceOrderWorkflowAction) {
    if (workflowAction.next_state === "Aprovado") {
      onOpenFlow("approve");
      return;
    }
    if (workflowAction.next_state === "Reprovado") {
      onOpenFlow("reject");
      return;
    }
    if (workflowAction.next_state === "Entregue") {
      onOpenFlow("pickup");
      return;
    }

    setMovingTo(workflowAction.next_state);
    try {
      await onSimpleMove(workflowAction.next_state);
    } finally {
      setMovingTo(null);
    }
  }

  return (
    <Card className="border-tec-orange/25 bg-tec-orange/5 p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-card bg-tec-orange text-tec-ink shadow-glow">
          <Send size={20} />
        </span>
        <div className="min-w-0">
          <p className="text-sm font-bold text-tec-orange">Próxima ação recomendada</p>
          <h3 className="mt-1 text-xl font-bold text-white">{action.title}</h3>
          <p className="mt-2 text-sm text-tec-subtle">{action.description}</p>
        </div>
      </div>
      <Button
        className="mt-5 w-full"
        icon={buttonIcon}
        onClick={() => {
          if (action.flow) {
            onOpenFlow(action.flow);
          } else if (isQuoteSendAction) {
            onOpenQuoteSend();
			} else if (isNoRepairPickupAction) {
				onStartNoRepairPickup();
          } else {
            onRefresh();
          }
        }}
        variant="primary"
      >
        {action.button}
      </Button>
      <p className="mt-3 text-xs font-medium text-tec-muted">{action.hint}</p>

      <div className="mt-5 border-t border-tec-border/15 pt-4">
        <p className="text-xs font-bold uppercase tracking-wide text-tec-muted">Outras ações</p>
        <div className="mt-2 space-y-2">
          {actions.length ? actions.map((workflowAction) => (
            <button
              className="group flex w-full items-center justify-between gap-3 rounded-control border border-tec-border/15 bg-tec-field/60 px-3 py-2.5 text-left transition hover:border-tec-orange/45 hover:bg-tec-orange/10 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-tec-field/60"
              disabled={Boolean(movingTo) || (Boolean(blockedTransitions[workflowAction.next_state]) && !detail.workflow_requestable_transitions.includes(workflowAction.next_state))}
              key={`${workflowAction.action}-${workflowAction.next_state}`}
              onClick={() => {
                if (blockedTransitions[workflowAction.next_state]) {
                  onRequestApproval(workflowAction.next_state);
                  return;
                }
                void handleWorkflowAction(workflowAction);
              }}
              title={blockedTransitions[workflowAction.next_state] || workflowActionTitle(workflowAction)}
              type="button"
            >
              <span className="min-w-0">
                <span className="block text-sm font-bold text-white">{movingTo === workflowAction.next_state ? "Atualizando..." : workflowActionLabel(workflowAction)}</span>
                <span className={cx("mt-0.5 block text-xs", blockedTransitions[workflowAction.next_state] ? "text-tec-amber" : "text-tec-muted")}>{blockedTransitions[workflowAction.next_state] || workflowActionDescription(workflowAction)}</span>
				{blockedTransitions[workflowAction.next_state] && detail.workflow_requestable_transitions.includes(workflowAction.next_state) ? <span className="mt-1 block text-xs font-bold text-tec-orange">Solicitar aprovação</span> : null}
              </span>
              <ArrowRight className="shrink-0 text-tec-orange transition group-hover:translate-x-0.5" size={16} />
            </button>
          )) : (
            <p className="rounded-control bg-tec-field/45 px-3 py-2.5 text-xs font-medium text-tec-muted">Nenhuma outra ação disponível para este papel.</p>
          )}
          <button
            className="group flex w-full items-center justify-between gap-3 rounded-control border border-tec-border/15 bg-tec-field/35 px-3 py-2.5 text-left transition hover:border-tec-orange/45 hover:bg-tec-field"
            onClick={onOpenHistory}
            type="button"
          >
            <span className="flex items-center gap-2 text-sm font-bold text-tec-subtle"><History size={16} className="text-tec-orange" /> Ver histórico da OS</span>
            <ArrowRight className="shrink-0 text-tec-orange transition group-hover:translate-x-0.5" size={16} />
          </button>
        </div>
      </div>
    </Card>
  );
}

function nextRecommendedAction(detail: ServiceOrderDetailResponse): {
  button: string;
  description: string;
  flow: "approve" | "reject" | "pickup" | null;
  hint: string;
  kind?: "quote-send" | "no-repair-pickup";
  title: string;
} {
	const state = detail.workflow_state;
	const projected = detail.next_action;
	if (projected?.label === "Enviar orçamento ao cliente") {
		return {
			button: "Enviar orçamento",
			description: "O orçamento avançou, mas ainda não há registro de envio ao cliente.",
			flow: null,
			hint: "Registre o canal usado para manter a passagem rastreável.",
			kind: "quote-send",
			title: projected.label,
		};
	}
	if (projected?.label === "Acompanhar aceite") {
		return {
			button: "Atualizar atendimento",
			description: "O envio já foi registrado. A próxima responsabilidade é acompanhar a decisão do cliente.",
			flow: null,
			hint: "Aprovação e reprovação continuam pelos fluxos com canal e responsável.",
			title: projected.label,
		};
	}
	if (projected && ["Em diagnóstico", "Diagnosticado — aguardando orçamento"].includes(state ?? "")) {
		return {
			button: "Atualizar dados",
			description: state === "Em diagnóstico" ? "Use a tela de Diagnóstico abaixo; ela distingue rascunho salvo de diagnóstico ainda vazio." : `Use a única tela de Orçamento abaixo. Repasse explícito: ${detail.diagnosis.pricing_responsibility ?? "responsável ainda não definido"}.`,
			flow: null,
			hint: "A Mesa e o detalhe usam a mesma leitura de completude.",
			title: projected.label,
		};
	}
  if (state === "Aguardando aprovação") {
    return {
      button: "Enviar para aprovação",
      description: "O orçamento está pronto. Envie para o cliente analisar e aguarde o retorno.",
      flow: null,
      hint: "Dica: você pode adicionar observações antes de enviar ao cliente.",
      kind: "quote-send",
      title: "Enviar para aprovação",
    };
  }
  if (state === "Pronto para retirada") {
    return {
      button: "Iniciar retirada",
      description: "Confira o serviço executado, colete a assinatura de retirada e finalize a entrega.",
      flow: "pickup",
      hint: "O motor ainda bloqueia a entrega se a nota não estiver paga.",
      title: "Coletar assinatura e entregar",
    };
  }
	if (["Reprovado", "Orçamento expirado", "Sem conserto"].includes(state ?? "")) {
		return {
			button: "Preparar retirada sem reparo",
			description: "O aparelho será devolvido sem execução de reparo. Gere o aceite de retirada e conclua a entrega.",
			flow: null,
			hint: "A OS será encaminhada para retirada; não é necessário criar nova OS.",
			kind: "no-repair-pickup",
			title: "Devolver aparelho sem reparo",
		};
	}
  return {
    button: "Atualizar atendimento",
    description: "Revise os dados da OS e avance pelo workflow quando a próxima etapa estiver pronta.",
    flow: null,
    hint: "Ações críticas continuam validadas pelo motor do ERPNext.",
    title: "Manter OS atualizada",
  };
}

function ServiceOrderAttendanceCard({ detail }: { detail: ServiceOrderDetailResponse }) {
  const rows: Array<[ReactNode, string, string]> = [
    [<CalendarClock size={15} />, "Entrada", formatDate(detail.entry_date)],
    [
      <Clock3 size={15} />,
      "Prazo de aprovação",
      detail.approval_deadline ? formatDate(detail.approval_deadline) : "Não definido",
    ],
	[<UserRound size={15} />, "Técnico", detail.technician ?? "Sem técnico"],
	[<UserRound size={15} />, "Recebido por", detail.attendant ?? "Não informado"],
    [<BadgeInfo size={15} />, "Garantia até", detail.warranty.warranty_expiry || "Não aplicada"],
    ...(detail.warranty.is_warranty && detail.warranty.original_service_order
      ? [[<BadgeInfo size={15} />, "Retrabalho em garantia", `OS original ${detail.warranty.original_service_order}`] as [ReactNode, string, string]]
      : []),
    [<RefreshCw size={15} />, "Atualização", formatDate(detail.modified)],
  ];

  return (
    <Card className="p-5">
      <h3 className="text-lg font-bold text-white">Atendimento</h3>
      <dl className="mt-4 space-y-3 text-sm">
        {rows.map(([icon, label, value]) => (
          <div className="flex items-start justify-between gap-3 rounded-control bg-tec-field/45 px-3 py-2" key={label}>
            <dt className="flex min-w-0 items-center gap-2 font-semibold text-tec-muted">
              <span className="text-tec-orange">{icon}</span>
              {label}
            </dt>
            <dd className="max-w-[50%] text-right font-bold text-tec-subtle">{value}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

function ServiceOrderPaymentCard({
	canViewDirectorFinancial,
	detail,
	onToast,
	onUpdated,
}: {
	canViewDirectorFinancial: boolean;
	detail: ServiceOrderDetailResponse;
	onToast: (message: string, tone?: ToastState["tone"]) => void;
	onUpdated: (detail: ServiceOrderDetailResponse) => void;
}) {
	type PaymentKind = ServiceOrderPaymentPayload["kind"];
	const [open, setOpen] = useState(false);
	const [kind, setKind] = useState<PaymentKind>("regular");
	const [amount, setAmount] = useState("");
	const [mode, setMode] = useState("Dinheiro");
	const [direction, setDirection] = useState<"Entrada" | "Saída">("Saída");
	const [reason, setReason] = useState("");
	const [tradeins, setTradeins] = useState<ServiceOrderTradeinCandidate[]>([]);
	const [tradein, setTradein] = useState("");
	const [loadingTradeins, setLoadingTradeins] = useState(false);
	const [submitting, setSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [directorFinance, setDirectorFinance] = useState<import("./api/types").ServiceOrderDirectorFinancialSummary | null>(null);
	const [directorFinanceError, setDirectorFinanceError] = useState<string | null>(null);

	useEffect(() => {
		if (!canViewDirectorFinancial || detail.technical_view) {
			setDirectorFinance(null);
			return;
		}
		let cancelled = false;
		setDirectorFinanceError(null);
		serviceOrders.directorFinancialSummary(detail.name)
			.then((response) => { if (!cancelled) setDirectorFinance(response); })
			.catch(() => { if (!cancelled) setDirectorFinanceError("Não foi possível carregar o resultado bruto desta OS."); });
		return () => { cancelled = true; };
	}, [canViewDirectorFinancial, detail.name, detail.technical_view]);

	const options = useMemo(() => {
		const items: Array<{ value: PaymentKind; label: string }> = [];
		if (detail.finance.sales_invoice) items.push({ value: "regular", label: "Pagamento da OS" });
		if (detail.finance.options.advance && !detail.finance.sales_invoice) items.push({ value: "advance", label: "Sinal" });
		if (detail.finance.options.installments && detail.finance.sales_invoice) items.push({ value: "installment", label: "Parcela" });
		if (detail.finance.options.diagnostic_fee && detail.finance.sales_invoice && ["Reprovado", "Orçamento expirado"].includes(detail.workflow_state || "")) items.push({ value: "diagnostic_fee", label: "Taxa de diagnóstico" });
		if (detail.finance.options.storage_fee && detail.finance.sales_invoice) items.push({ value: "storage_fee", label: "Taxa de armazenamento" });
		if (detail.finance.options.tradein && detail.finance.remaining_total > 0) items.push({ value: "tradein", label: "Aparelho como pagamento" });
		if (detail.workflow_state === "Cancelado") items.push({ value: "cancellation_adjustment", label: "Ajuste de cancelamento" });
		return items;
	}, [detail]);

	useEffect(() => {
		if (!open) return;
		const first = options[0]?.value ?? "regular";
		setKind(first);
		setAmount(detail.finance.remaining_total > 0 ? detail.finance.remaining_total.toFixed(2) : "");
		setMode("Dinheiro");
		setDirection("Saída");
		setReason("");
		setTradein("");
		setTradeins([]);
		setError(null);
	}, [detail.name, detail.finance.remaining_total, open, options]);

	useEffect(() => {
		if (!open || kind !== "tradein") return;
		let cancelled = false;
		setLoadingTradeins(true);
		serviceOrders.tradeinCandidates(detail.name)
			.then((response) => {
				if (!cancelled) setTradeins(response.items);
			})
			.catch((caught) => {
				if (!cancelled) setError(caught instanceof Error ? caught.message : "Não foi possível carregar avaliações.");
			})
			.finally(() => { if (!cancelled) setLoadingTradeins(false); });
		return () => { cancelled = true; };
	}, [detail.name, kind, open]);

	useEffect(() => {
		if (kind === "diagnostic_fee") {
			setAmount("");
		}
		if (kind === "tradein") {
			const selected = tradeins.find((item) => item.name === tradein);
			if (selected) setAmount(selected.amount.toFixed(2));
		}
	}, [kind, tradein, tradeins]);

	if (detail.technical_view) return null;
	const hasOptions = options.length > 0;
	const isCancellation = kind === "cancellation_adjustment";
	const requiresReason = isCancellation;
	const selectedTradein = tradeins.find((item) => item.name === tradein);
	const effectiveAmount = Number(amount.replace(",", "."));
	const canSubmit = hasOptions && effectiveAmount > 0 && (!requiresReason || Boolean(reason.trim())) && (kind !== "tradein" || Boolean(selectedTradein));

	async function submit() {
		if (!canSubmit) return;
		setSubmitting(true);
		setError(null);
		try {
			const response = await serviceOrders.collectPayment(detail.name, {
				kind,
				amount: effectiveAmount,
				mode_of_payment: kind === "tradein" ? undefined : mode,
				direction: isCancellation ? direction : "Entrada",
				reason: reason.trim(),
				trade_evaluation: kind === "tradein" ? tradein : undefined,
				idempotency_key: `os-payment-${detail.name}-${crypto.randomUUID()}`,
			});
			onUpdated(response.detail);
			setOpen(false);
			onToast(response.payment.idempotent_replay ? "Pagamento já estava registrado." : "Pagamento registrado no financeiro e no caixa.");
		} catch (caught) {
			setError(caught instanceof Error ? caught.message : "Não foi possível registrar o pagamento.");
		} finally {
			setSubmitting(false);
		}
	}

	return (
		<Card className="p-5">
			<div className="flex items-center justify-between gap-3">
				<div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-control bg-tec-success/10 text-tec-success"><CreditCard size={19} /></span><div><h3 className="text-lg font-bold text-white">Financeiro da OS</h3><p className="text-xs text-tec-muted">Recebimentos sempre exigem caixa aberto.</p></div></div>
				<Button disabled={!hasOptions} onClick={() => setOpen(true)} variant="secondary">Receber</Button>
			</div>
			<dl className="mt-4 grid gap-2 text-sm sm:grid-cols-3">
				{[["Total", detail.finance.total_due], ["Pago", detail.finance.paid_total], ["Restante", detail.finance.remaining_total]].map(([label, value]) => <div className="rounded-control bg-tec-field/45 px-3 py-2" key={String(label)}><dt className="text-xs font-semibold text-tec-muted">{label}</dt><dd className="mt-1 font-bold text-tec-subtle">{formatCurrency(Number(value))}</dd></div>)}
			</dl>
			{detail.finance.payments.length ? <div className="mt-4 space-y-2 border-t border-tec-border/20 pt-3">{detail.finance.payments.slice(-3).reverse().map((payment) => <div className="flex items-center justify-between gap-3 text-xs" key={payment.name}><span className="truncate text-tec-muted">{payment.kind} · {payment.payment_mode || "não monetário"}</span><strong className={payment.direction === "Saída" ? "text-tec-red" : "text-tec-success"}>{payment.direction === "Saída" ? "−" : "+"}{formatCurrency(payment.amount)}</strong></div>)}</div> : null}
			{directorFinance ? <div className="mt-4 border-t border-tec-border/20 pt-3"><p className="text-xs font-bold uppercase text-tec-muted">Diretoria · resultado bruto operacional</p><dl className="mt-2 grid gap-2 text-xs sm:grid-cols-2">{[["Custo de peças usadas", directorFinance.part_cost], ["Mão de obra provisionada", directorFinance.labor_cost_provisioned], ["Custo operacional", directorFinance.total_cost], ["Resultado bruto", directorFinance.gross_profit]].map(([label, value]) => <div className="rounded-control bg-tec-field/45 px-3 py-2" key={String(label)}><dt className="text-tec-muted">{label}</dt><dd className="mt-1 font-bold text-tec-subtle">{formatCurrency(Number(value))}</dd></div>)}</dl><p className="mt-2 text-[11px] text-tec-muted">Não inclui despesas fixas, impostos ou resultado líquido.</p></div> : null}
			{directorFinanceError ? <p className="mt-3 text-xs text-tec-red">{directorFinanceError}</p> : null}
			{!hasOptions ? <p className="mt-4 rounded-control border border-tec-border/20 bg-tec-field/45 p-3 text-xs text-tec-muted">Gere a nota para receber o saldo. As modalidades desligadas pela configuração da loja não aparecem aqui.</p> : null}
			<Modal className="max-w-lg" onClose={() => setOpen(false)} open={open} title={`Receber ${detail.name}`}>
				<div className="space-y-4">
					<label className="block"><span className="mb-1 block text-xs font-bold uppercase text-tec-muted">Natureza</span><select className="tp-input" onChange={(event) => setKind(event.target.value as PaymentKind)} value={kind}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
					{kind === "tradein" ? <label className="block"><span className="mb-1 block text-xs font-bold uppercase text-tec-muted">Avaliação do aparelho</span><select className="tp-input" disabled={loadingTradeins} onChange={(event) => setTradein(event.target.value)} value={tradein}><option value="">{loadingTradeins ? "Carregando..." : "Selecione uma avaliação"}</option>{tradeins.map((item) => <option key={item.name} value={item.name}>{item.label} · {formatCurrency(item.amount)}</option>)}</select><p className="mt-2 text-xs text-tec-muted">Abate o saldo pela avaliação aprovada; não adiciona dinheiro à gaveta.</p></label> : <><label className="block"><span className="mb-1 block text-xs font-bold uppercase text-tec-muted">Forma de pagamento</span><select className="tp-input" onChange={(event) => setMode(event.target.value)} value={mode}>{["Dinheiro", "Pix", "Débito", "Crédito à vista", "Crédito parcelado"].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>{isCancellation ? <label className="block"><span className="mb-1 block text-xs font-bold uppercase text-tec-muted">Direção do ajuste</span><select className="tp-input" onChange={(event) => setDirection(event.target.value as "Entrada" | "Saída")} value={direction}><option value="Saída">Devolver ao cliente</option><option value="Entrada">Receber ajuste</option></select></label> : null}</>}
					<label className="block"><span className="mb-1 block text-xs font-bold uppercase text-tec-muted">Valor</span><input className="tp-input" inputMode="decimal" onChange={(event) => setAmount(event.target.value)} value={amount} /></label>
					<label className="block"><span className="mb-1 block text-xs font-bold uppercase text-tec-muted">Observação{requiresReason ? " *" : ""}</span><textarea className="tp-input min-h-24" onChange={(event) => setReason(event.target.value)} placeholder={requiresReason ? "Explique o ajuste de cancelamento." : "Opcional"} value={reason} /></label>
					{error ? <p className="rounded-control border border-tec-red/35 bg-tec-red/10 p-3 text-sm text-tec-red">{error}</p> : null}
					<Button className="w-full" disabled={!canSubmit || submitting} icon={<CreditCard size={17} />} onClick={() => void submit()} variant="primary">{submitting ? "Registrando..." : "Registrar pagamento"}</Button>
				</div>
			</Modal>
		</Card>
	);
}

function IdentityCard({
  action,
  icon,
  lines,
  title,
}: {
  action?: ReactNode;
  icon: ReactNode;
  lines: Array<[string, string]>;
  title: string;
}) {
  return (
    <Card className="p-5">
      <div className="mb-5 flex items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-card bg-tec-orange/10 text-tec-orange">{icon}</span>
        <h3 className="text-lg font-bold text-white">{title}</h3>
      </div>
      <dl className="space-y-3.5 text-sm">
        {lines.map(([label, value]) => (
          <DetailLine key={label} label={label} value={value} />
        ))}
      </dl>
      {action}
    </Card>
  );
}

function BudgetCard({
  detail,
  onOpenBudgetEditor,
  onToast,
  onUpdated,
}: {
  detail: ServiceOrderDetailResponse;
  onOpenBudgetEditor: (type: BudgetLineType) => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  onUpdated: (detail: ServiceOrderDetailResponse) => void;
}) {
	const [discriminated, setDiscriminated] = useState(detail.budget.presentation === "Discriminado");
	const [updatingPresentation, setUpdatingPresentation] = useState(false);

	const togglePresentation = async () => {
		const nextPresentation = discriminated ? "Fechado" : "Discriminado";
		setUpdatingPresentation(true);
		try {
			const updated = await serviceOrders.updateBudgetPresentation(detail.name, nextPresentation);
			onUpdated(updated);
			setDiscriminated(nextPresentation === "Discriminado");
			onToast(`Formato do orçamento alterado para ${nextPresentation}.`);
		} catch (err) {
			onToast(err instanceof Error ? err.message : "Falha ao alterar formato de apresentação.", "error");
		} finally {
			setUpdatingPresentation(false);
		}
	};

	const handleRemoveLine = async (lineName: string, type: BudgetLineType) => {
		try {
			const updated = await serviceOrders.removeBudgetLine(detail.name, lineName, type);
			onUpdated(updated);
			onToast("Item removido do orçamento.");
		} catch (err) {
			onToast(err instanceof Error ? err.message : "Falha ao remover item do orçamento.", "error");
		}
	};

  return (
    <Card className="p-5">
      <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">Orçamento Comercial</h3>
          <p className="text-xs text-tec-muted">
            Versão {detail.totals.budget_version} · {detail.totals.quote_locked ? "travado para envio" : "em edição de bancada"}
          </p>
        </div>
        <div className="text-left md:text-right">
          <p className="text-xs font-semibold uppercase text-tec-muted">Total do orçamento</p>
          <span className="tp-metric-value text-3xl font-bold text-tec-orange">{formatCurrency(detail.totals.grand_total)}</span>
        </div>
			<button
				className="self-start rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 text-xs font-bold text-tec-subtle hover:border-tec-orange/50 hover:text-white"
				disabled={updatingPresentation || detail.totals.quote_locked}
				onClick={togglePresentation}
				type="button"
			>
				{updatingPresentation ? "Atualizando..." : discriminated ? "Mudar para Orçamento Fechado" : "Mudar para Orçamento Discriminado"}
			</button>
      </div>

		{discriminated ? <>
        <BudgetLines
					lines={detail.services}
					onOpenBudgetEditor={onOpenBudgetEditor}
					onRemoveLine={handleRemoveLine}
					quoteLocked={detail.totals.quote_locked}
					title="Mão de obra / Serviços"
					type="service"
				/>
        <div className="mt-4">
					<BudgetLines
						lines={detail.parts}
						onOpenBudgetEditor={onOpenBudgetEditor}
						onRemoveLine={handleRemoveLine}
						quoteLocked={detail.totals.quote_locked}
						title="Peças e Insumos"
						type="part"
					/>
				</div>
			<p className="mt-3 text-xs text-tec-muted">Composição exibida a preço de venda comercial. Custos e margens internas não trafegam para este perfil.</p>
		</> : <div className="overflow-hidden rounded-card border border-tec-border/20">
			{detail.budget.closed_lines.map((line, index) => <div className="flex items-center justify-between gap-4 border-b border-tec-border/15 bg-tec-field/40 px-4 py-3 text-sm last:border-0" key={`${line.description}-${index}`}><span className="font-semibold text-white">{line.description}</span><span className="shrink-0 font-bold text-tec-orange">{formatCurrency(line.amount)}</span></div>)}
			{detail.budget.customer_supplied_part_term_required ? <p className="border-t border-tec-amber/20 bg-tec-amber/10 px-4 py-3 text-xs font-semibold text-tec-amber">Peça fornecida pelo cliente: cobra-se apenas o serviço; a garantia não cobre a peça do cliente.</p> : null}
		</div>}
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
  onOpenBudgetEditor,
  onRemoveLine,
  title,
  type,
  quoteLocked,
}: {
  lines: ServiceOrderBudgetLine[];
  onOpenBudgetEditor: (type: BudgetLineType) => void;
  onRemoveLine: (lineName: string, type: BudgetLineType) => Promise<void>;
  title: string;
  type: BudgetLineType;
  quoteLocked?: boolean;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h4 className="text-sm font-bold text-white">{title}</h4>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-tec-field px-2 py-1 text-xs text-tec-muted">{lines.length}</span>
          {!quoteLocked ? (
            <button
              className="rounded-full border border-tec-border/15 bg-tec-field px-3 py-1 text-xs font-bold text-tec-subtle transition hover:border-tec-orange/50 hover:text-white"
              onClick={() => onOpenBudgetEditor(type)}
              type="button"
            >
              + Adicionar
            </button>
          ) : null}
        </div>
      </div>
      <div className="overflow-hidden rounded-card border border-tec-border/20">
        {lines.length ? (
          lines.map((line, index) => (
            <div
              className="grid gap-3 border-b border-tec-border/15 bg-tec-field/40 p-3 text-sm last:border-0 md:grid-cols-[minmax(0,1fr)_90px_120px_140px]"
              key={`${line.name ?? line.item_code ?? title}-${index}`}
            >
              <div className="min-w-0">
                <p className="truncate font-semibold text-white">{line.description || line.item_code || "Item sem descrição"}</p>
                <p className="mt-1 text-xs text-tec-muted">
                  {line.item_code ?? "Sem item de catálogo"}
                  {type === "service" && line.service_duration ? ` · Prazo: ${line.service_duration} ${(line.duration_unit ?? "Horas").toLowerCase()}` : ""}
                  {type === "service" && line.technician ? ` · ${line.technician}` : ""}
                  {type === "part" && line.outcome ? ` · ${line.outcome}` : ""}
                  {type === "part" && line.part_source ? ` · Origem: ${line.part_source}` : ""}
                </p>
              </div>
              <span className="text-tec-subtle">Qtd. {line.qty.toLocaleString("pt-BR")}</span>
              <span className="text-tec-subtle">{formatCurrency(line.unit_price ?? 0)}</span>
              <div className="flex items-center justify-between md:justify-end gap-3">
                <span className="font-semibold text-white">{formatCurrency(line.amount ?? 0)}</span>
                {!quoteLocked && line.name ? (
                  <button
                    aria-label="Remover linha"
                    className="p-1 text-tec-muted transition hover:text-tec-red"
                    onClick={() => {
                      const name = line.name;
                      if (name) void onRemoveLine(name, type);
                    }}
                    title="Remover do orçamento"
                    type="button"
                  >
                    <Trash2 size={15} />
                  </button>
                ) : null}
              </div>
            </div>
          ))
        ) : (
          <BudgetEmptyState onOpenBudgetEditor={onOpenBudgetEditor} quoteLocked={quoteLocked} type={type} />
        )}
      </div>
    </div>
  );
}

function BudgetEmptyState({
  onOpenBudgetEditor,
  quoteLocked,
  type,
}: {
  onOpenBudgetEditor: (type: BudgetLineType) => void;
  quoteLocked?: boolean;
  type: BudgetLineType;
}) {
  const isService = type === "service";
  const Icon = isService ? Wrench : Box;
  const title = isService ? "Nenhum serviço adicionado." : "Nenhuma peça adicionada.";
  const description = isService ? "Adicione serviços para compor o orçamento." : "Adicione peças para compor o orçamento.";
  const action = isService ? "Adicionar serviço" : "Adicionar peça";

  return (
    <div className="flex flex-col gap-4 bg-tec-field/35 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-card bg-tec-orange/10 text-tec-orange">
          <Icon size={20} />
        </span>
        <div>
          <p className="font-bold text-white">{title}</p>
          <p className="mt-1 text-sm text-tec-muted">{description}</p>
        </div>
      </div>
      {!quoteLocked ? (
        <Button icon={<Plus size={16} />} onClick={() => onOpenBudgetEditor(type)} variant="secondary">
          {action}
        </Button>
      ) : null}
    </div>
  );
}

function BudgetLineModal({
  detail,
  lineType,
  onClose,
  onToast,
  onUpdated,
}: {
  detail: ServiceOrderDetailResponse;
  lineType: BudgetLineType | null;
  onClose: () => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  onUpdated: (detail: ServiceOrderDetailResponse) => void;
}) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<BudgetItemSummary[]>([]);
  const [catalogItems, setCatalogItems] = useState<ServiceCatalogService[]>([]);
  const [selectedItem, setSelectedItem] = useState<BudgetItemSummary | null>(null);
  const [selectedCatalogService, setSelectedCatalogService] = useState<ServiceCatalogService | null>(null);
  const [serviceEntryMode, setServiceEntryMode] = useState<"catalog" | "manual">("catalog");
  const [warehouses, setWarehouses] = useState<BudgetWarehouseSummary[]>([]);
  const [warehouse, setWarehouse] = useState("");
  const [description, setDescription] = useState("");
  const [qty, setQty] = useState("1");
  const [rate, setRate] = useState("");
  const [duration, setDuration] = useState("");
	const [durationUnit, setDurationUnit] = useState<"Horas" | "Dias úteis">("Horas");
	const [customerSuppliedPart, setCustomerSuppliedPart] = useState(false);
	const [serviceRow, setServiceRow] = useState("");
  const [loadingItems, setLoadingItems] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!lineType) {
      return;
    }
    setQuery("");
    setItems([]);
    setCatalogItems([]);
    setSelectedItem(null);
    setSelectedCatalogService(null);
    setServiceEntryMode(lineType === "service" ? "catalog" : "manual");
    setDescription("");
    setQty("1");
    setRate("");
    setDuration("");
    setDurationUnit("Horas");
    setWarehouse("");
		setCustomerSuppliedPart(false);
		setServiceRow("");
    setError(null);
    setSubmitting(false);
  }, [lineType, detail.name]);

  useEffect(() => {
    if (!lineType) {
      return;
    }
    let cancelled = false;
    setLoadingItems(true);
    if (lineType === "service" && serviceEntryMode === "manual") {
      setLoadingItems(false);
      setItems([]);
      setCatalogItems([]);
      return;
    }
    const request = lineType === "service" && serviceEntryMode === "catalog"
      ? serviceCatalog.list(query).then((response) => ({ catalog: response.items, items: [] as BudgetItemSummary[] }))
      : serviceOrders.searchBudgetItems(query, lineType).then((response) => ({ catalog: [] as ServiceCatalogService[], items: response.items }));
    request
      .then((response) => {
        if (!cancelled) {
          setItems(response.items);
          setCatalogItems(response.catalog);
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Falha ao buscar itens.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingItems(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [query, lineType, serviceEntryMode]);

  useEffect(() => {
    if (lineType !== "part") {
      return;
    }
    let cancelled = false;
    serviceOrders
      .listBudgetWarehouses()
      .then((response) => {
        if (cancelled) {
          return;
        }
        setWarehouses(response.items);
        const repairWarehouse =
          response.items.find((item) => /reparo|peças|pecas/i.test(`${item.name} ${item.warehouse_name ?? ""}`)) ?? response.items[0];
        setWarehouse(repairWarehouse?.name ?? "");
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Falha ao carregar estoques.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [lineType]);

  if (!lineType) {
    return null;
  }

  const activeLineType = lineType;
  const isService = activeLineType === "service";
  const isWarrantyLabor = isService && detail.warranty.is_warranty;
  const title = isService ? `Adicionar serviço em ${detail.name}` : `Adicionar peça em ${detail.name}`;
  const parsedQty = Number(qty.replace(",", "."));
  const parsedRate = Number(rate.replace(",", "."));
  const parsedDuration = Number(duration.replace(",", "."));
  const canSubmit = (isService ? (serviceEntryMode === "catalog" ? Boolean(selectedCatalogService) : Boolean(description.trim())) : customerSuppliedPart ? Boolean(description.trim()) : Boolean(selectedItem)) && parsedQty > 0 && parsedRate >= 0 && (serviceEntryMode !== "catalog" || !duration || parsedDuration >= 0) && (isService || customerSuppliedPart || Boolean(warehouse));

  function selectItem(item: BudgetItemSummary) {
    setSelectedItem(item);
    setSelectedCatalogService(null);
    setDescription(item.item_name ?? item.item_code);
    setRate(isWarrantyLabor ? "0" : String(item.standard_rate || 0));
  }

  function selectCatalogService(service: ServiceCatalogService) {
    setSelectedCatalogService(service);
    setSelectedItem(null);
    setDescription(service.service_name);
    setRate(isWarrantyLabor ? "0" : String(service.default_labor_price || 0));
    setDuration(String(service.default_duration || 0));
    setDurationUnit(service.duration_unit);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (isService && serviceEntryMode === "catalog" && !selectedCatalogService) {
      setError("Selecione um serviço do catálogo ou use Serviço avulso.");
      return;
    }
    if (!isService && !selectedItem && !customerSuppliedPart) {
      setError("Selecione um item para o orçamento.");
      return;
    }
    if (!canSubmit) {
      setError("Confira item, quantidade, valor e estoque antes de salvar.");
      return;
    }

    setSubmitting(true);
    try {
      const updated = isService && serviceEntryMode === "catalog"
        ? await serviceOrders.addCatalogService(detail.name, selectedCatalogService!.name, {
            description: description.trim(),
            duration: Number.isFinite(parsedDuration) ? parsedDuration : 0,
            duration_unit: durationUnit,
            qty: parsedQty,
            rate: parsedRate,
          })
        : await serviceOrders.addBudgetLine(detail.name, {
            description: description.trim(),
						item_code: isService || customerSuppliedPart ? undefined : selectedItem!.item_code,
            qty: parsedQty,
            rate: parsedRate,
            type: activeLineType,
			warehouse: isService ? undefined : warehouse,
			part_source: customerSuppliedPart ? "Cliente" : "Loja",
			service_row: !isService ? serviceRow || undefined : undefined,
			customer_part_note: customerSuppliedPart ? description.trim() : undefined,
          });
      onUpdated(updated);
      onToast(`${isService ? "Serviço" : "Peça"} adicionado ao orçamento.`);
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao salvar a linha do orçamento.");
      onToast("Não foi possível salvar o orçamento. Confira as regras do motor.", "error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal className="max-w-5xl" onClose={onClose} open={Boolean(lineType)} title={title}>
      <form className="grid max-h-[78vh] gap-4 overflow-y-auto pr-1 lg:grid-cols-[minmax(0,1fr)_320px]" onSubmit={submit}>
        <section className="space-y-4">
          {isWarrantyLabor ? (
            <div className="rounded-card border border-tec-success/25 bg-tec-success/10 p-3 text-sm leading-6 text-tec-success">
              Esta Ã© uma OS de garantia vinculada Ã  {detail.warranty.original_service_order}. O serviÃ§o fica registrado para qualidade, mas a mÃ£o de obra Ã© sempre R$ 0,00. PeÃ§as seguem a baixa normal de estoque.
            </div>
          ) : null}
          {isService ? (
            <div className="flex rounded-control border border-tec-border/20 bg-tec-field/55 p-1">
              <button className={cx("flex-1 rounded-control px-3 py-2 text-sm font-bold transition", serviceEntryMode === "catalog" ? "bg-tec-orange text-tec-ink" : "text-tec-subtle hover:text-white")} onClick={() => setServiceEntryMode("catalog")} type="button">Catálogo</button>
              <button className={cx("flex-1 rounded-control px-3 py-2 text-sm font-bold transition", serviceEntryMode === "manual" ? "bg-tec-orange text-tec-ink" : "text-tec-subtle hover:text-white")} onClick={() => setServiceEntryMode("manual")} type="button">Serviço avulso</button>
            </div>
          ) : null}
          {!(isService && serviceEntryMode === "manual") ? <><label className="block">
            <span className="mb-2 block text-xs font-bold uppercase text-tec-muted">{isService && serviceEntryMode === "catalog" ? "Buscar no catálogo" : "Buscar item"}</span>
            <input
              autoFocus
              className="h-11 w-full rounded-control border border-tec-border/20 bg-tec-field px-4 text-sm font-semibold text-tec-text outline-none transition focus:border-tec-orange/70"
              onChange={(event) => setQuery(event.target.value)}
              placeholder={isService && serviceEntryMode === "catalog" ? "Buscar serviço por nome, tipo ou categoria..." : isService ? "Buscar serviço por nome ou código..." : "Buscar peça por nome, código ou grupo..."}
              value={query}
            />
          </label>

          <div className="rounded-card border border-tec-border/15 bg-tec-field/45">
            {loadingItems ? (
              <p className="p-4 text-sm font-semibold text-tec-subtle">Buscando itens...</p>
            ) : isService && serviceEntryMode === "catalog" && catalogItems.length ? (
              <div className="divide-y divide-tec-border/10">
                {catalogItems.map((service) => {
                  const selected = selectedCatalogService?.name === service.name;
                  return <button className={cx("flex w-full items-center justify-between gap-3 p-3 text-left transition hover:bg-tec-orange/10", selected ? "bg-tec-orange/15" : "")} key={service.name} onClick={() => selectCatalogService(service)} type="button"><span className="min-w-0"><span className="block truncate text-sm font-bold text-white">{service.service_name}</span><span className="mt-1 block truncate text-xs text-tec-muted">{service.device_type_label ?? service.device_type} · {service.category_label ?? service.category}</span></span><span className="shrink-0 text-right"><span className="block text-sm font-bold text-tec-orange">{service.default_labor_price > 0 ? formatCurrency(service.default_labor_price) : "Não definido"}</span><span className="block text-xs text-tec-muted">{service.default_duration ? `${service.default_duration} ${service.duration_unit.toLowerCase()}` : "Sem prazo"}</span></span></button>;
                })}
              </div>
            ) : items.length ? (
              <div className="divide-y divide-tec-border/10">
                {items.map((item) => {
                  const selected = selectedItem?.item_code === item.item_code;
                  return (
                    <button
                      className={cx(
                        "flex w-full items-center justify-between gap-3 p-3 text-left transition hover:bg-tec-orange/10",
                        selected ? "bg-tec-orange/15" : "",
                      )}
                      key={item.item_code}
                      onClick={() => selectItem(item)}
                      type="button"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-bold text-white">{item.item_name ?? item.item_code}</span>
                        <span className="mt-1 block truncate text-xs text-tec-muted">
                          {item.item_code} · {item.item_group ?? "Sem grupo"}
                        </span>
                      </span>
                      <span className="shrink-0 text-sm font-bold text-tec-orange">{formatCurrency(item.standard_rate)}</span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="p-4 text-sm font-semibold text-tec-subtle">{isService && serviceEntryMode === "catalog" ? "Nenhum serviço no catálogo. Use Serviço avulso para não interromper o atendimento." : "Nenhum item encontrado para esse tipo."}</p>
            )}
          </div></> : <div className="rounded-card border border-tec-blue/25 bg-tec-blue/10 p-4 text-sm text-tec-subtle">Digite a descrição e o valor ao lado. O motor usa o item interno de mão de obra automaticamente.</div>}
        </section>

        <aside className="space-y-4 rounded-card border border-tec-border/15 bg-tec-panel-strong p-4">
          <div>
            <p className="text-xs font-bold uppercase text-tec-muted">Linha selecionada</p>
            <p className="mt-1 text-lg font-bold text-white">{selectedCatalogService?.service_name ?? selectedItem?.item_name ?? (isService && serviceEntryMode === "manual" ? description || "Serviço avulso" : "Nenhum item")}</p>
      <p className="mt-1 text-xs text-tec-muted">{budgetLineTypeDescription(activeLineType)}</p>
          </div>

          <label className="block">
            <span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Descrição</span>
            <textarea
              className="min-h-20 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 text-sm font-semibold text-tec-text outline-none transition focus:border-tec-orange/70"
              onChange={(event) => setDescription(event.target.value)}
              value={description}
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <label className="block">
              <span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Quantidade</span>
              <input
                className="h-11 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-tec-text outline-none transition focus:border-tec-orange/70"
                min="0.01"
                onChange={(event) => setQty(event.target.value)}
                step="0.01"
                type="number"
                value={qty}
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Valor unitário</span>
              <input
                className="h-11 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-tec-text outline-none transition focus:border-tec-orange/70 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isWarrantyLabor || customerSuppliedPart}
                min="0"
                onChange={(event) => setRate(event.target.value)}
                step="0.01"
                type="number"
                value={rate}
              />
            </label>
            {isService && serviceEntryMode === "catalog" ? <><label className="block"><span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Prazo sugerido</span><input className="h-11 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-tec-text outline-none transition focus:border-tec-orange/70" min="0" onChange={(event) => setDuration(event.target.value)} step="0.5" type="number" value={duration} /></label><label className="block"><span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Unidade do prazo</span><select className="h-11 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-tec-text outline-none transition focus:border-tec-orange/70" onChange={(event) => setDurationUnit(event.target.value as "Horas" | "Dias úteis")} value={durationUnit}><option>Horas</option><option>Dias úteis</option></select></label></> : null}
          </div>

          {!isService ? (
				<div className="rounded-card border border-tec-amber/25 bg-tec-amber/10 p-3">
					<label className="flex cursor-pointer items-start gap-2 text-sm font-semibold text-tec-amber"><input checked={customerSuppliedPart} className="mt-1" onChange={(event) => { setCustomerSuppliedPart(event.target.checked); if (event.target.checked) setRate("0"); }} type="checkbox" />Cliente trouxe a própria peça</label>
					<p className="mt-2 text-xs leading-5 text-tec-muted">Não há baixa de estoque e o orçamento cobra apenas mão de obra. O aceite incluirá o termo específico.</p>
				</div>
			) : null}

			{!isService && !customerSuppliedPart ? (
            <label className="block">
              <span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Estoque da peça</span>
              <select
                className="h-11 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-tec-text outline-none transition focus:border-tec-orange/70"
                onChange={(event) => setWarehouse(event.target.value)}
                value={warehouse}
              >
                {warehouses.map((item) => (
                  <option key={item.name} value={item.name}>
                    {item.warehouse_name ?? item.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {!isService && detail.services.length ? (
            <label className="block">
              <span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Vincular ao serviço</span>
              <select className="h-11 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-tec-text outline-none transition focus:border-tec-orange/70" onChange={(event) => setServiceRow(event.target.value)} value={serviceRow}>
                <option value="">Peça avulsa no orçamento</option>
                {detail.services.map((service) => <option key={service.name ?? service.description} value={service.name ?? ""}>{service.description || service.item_code || "Serviço"}</option>)}
              </select>
            </label>
          ) : null}

          <div className="rounded-card border border-tec-border/10 bg-tec-field/55 p-3">
            <p className="text-xs font-bold uppercase text-tec-muted">Subtotal</p>
            <p className="tp-metric-value mt-1 text-2xl font-bold text-tec-orange">
              {formatCurrency(Number.isFinite(parsedQty * parsedRate) ? parsedQty * parsedRate : 0)}
            </p>
          </div>

          {error ? (
            <p className="rounded-card border border-tec-red/25 bg-tec-red/10 p-3 text-sm font-semibold text-tec-red">{error}</p>
          ) : null}

          <Button className="w-full" disabled={!canSubmit || submitting} icon={<Plus size={17} />} type="submit" variant="primary">
            {submitting ? "Salvando..." : `Salvar ${isService ? "serviço" : "peça"}`}
          </Button>
        </aside>
      </form>
    </Modal>
  );
}

const QUOTE_SEND_CHANNELS: QuoteSendPayload["channel"][] = ["WhatsApp", "Telefone", "Presencial", "E-mail"];

function QuoteSendModal({
  detail,
  onClose,
  onToast,
  onUpdated,
  open,
}: {
  detail: ServiceOrderDetailResponse;
  onClose: () => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  onUpdated: (detail: ServiceOrderDetailResponse) => void;
  open: boolean;
}) {
  const [channel, setChannel] = useState<QuoteSendPayload["channel"]>("WhatsApp");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    setChannel("WhatsApp");
    setNotes("");
    setSubmitting(false);
    setError(null);
  }, [open, detail.name]);

  const quoteLink = detail.print_links.find((link) => link.label.toLowerCase().includes("orçamento"));
  const customerPhone = detail.customer?.mobile_no ?? "Sem telefone";
  const customerEmail = detail.customer?.email_id ?? "Sem e-mail";
  const canSubmit = detail.services.length + detail.parts.length > 0 && !submitting;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!canSubmit) {
      setError("Inclua ao menos um serviço ou peça antes de enviar.");
      return;
    }
    setSubmitting(true);
    try {
      const updated = await serviceOrders.sendQuote(detail.name, {
        channel,
        notes: notes.trim(),
      });
      onUpdated(updated);
      onToast(`Envio do orçamento registrado por ${channel}.`);
      onClose();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao registrar envio do orçamento.");
      onToast("Não foi possível registrar o envio do orçamento.", "error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal className="max-w-4xl" onClose={onClose} open={open} title={`Enviar orçamento ${detail.name}`}>
      <form className="grid max-h-[78vh] gap-4 overflow-y-auto pr-1 lg:grid-cols-[minmax(0,1fr)_300px]" onSubmit={submit}>
        <section className="space-y-4">
          <div className="rounded-card border border-tec-border/15 bg-tec-panel-strong p-4">
            <p className="text-xs font-bold uppercase text-tec-muted">Canal de envio</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {QUOTE_SEND_CHANNELS.map((nextChannel) => {
                const selected = channel === nextChannel;
                return (
                  <button
                    className={cx(
                      "rounded-control border px-3 py-2 text-sm font-bold transition",
                      selected
                        ? "border-tec-orange bg-tec-orange text-tec-ink shadow-glow"
                        : "border-tec-border/20 bg-tec-field text-tec-subtle hover:border-tec-orange/50 hover:text-white",
                    )}
                    key={nextChannel}
                    onClick={() => setChannel(nextChannel)}
                    type="button"
                  >
                    {nextChannel}
                  </button>
                );
              })}
            </div>
          </div>

          <label className="block">
            <span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Observação para o histórico</span>
            <textarea
              className="min-h-28 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 text-sm font-semibold text-tec-text outline-none transition focus:border-tec-orange/70"
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Ex.: enviado pelo WhatsApp do balcão, cliente pediu retorno até amanhã."
              value={notes}
            />
          </label>

          <div className="rounded-card border border-tec-border/15 bg-tec-field/45 p-4">
            <h3 className="text-sm font-bold text-white">Mensagem registrada</h3>
            <p className="mt-2 text-sm text-tec-subtle">
              O sistema vai registrar o envio no histórico da OS com canal, atendente, data, total e validade do orçamento.
            </p>
            {quoteLink ? (
              <a
                className="mt-4 inline-flex min-h-10 items-center justify-center gap-2 rounded-control border border-tec-border/20 bg-tec-field px-4 text-sm font-bold text-tec-text transition hover:border-tec-orange/50"
                href={quoteLink.url}
                rel="noreferrer"
                target="_blank"
              >
                <Printer size={17} />
                Abrir PDF do orçamento
              </a>
            ) : null}
          </div>

          {error ? (
            <p className="rounded-card border border-tec-red/25 bg-tec-red/10 p-3 text-sm font-semibold text-tec-red">{error}</p>
          ) : null}
        </section>

        <aside className="space-y-4 rounded-card border border-tec-border/15 bg-tec-panel-strong p-4">
          <div>
            <p className="text-xs font-bold uppercase text-tec-muted">Resumo</p>
            <p className="tp-metric-value mt-1 text-3xl font-bold text-tec-orange">{formatCurrency(detail.totals.grand_total)}</p>
          </div>
          <dl className="space-y-3 text-sm">
            <DetailLine label="Cliente" value={detail.customer?.customer_name ?? detail.customer?.name ?? "Não informado"} />
            <DetailLine label="Telefone" value={customerPhone} />
            <DetailLine label="E-mail" value={customerEmail} />
            <DetailLine label="Validade" value={detail.approval_deadline ? formatDate(detail.approval_deadline) : "Não definida"} />
            <DetailLine label="Versão" value={`Orçamento v${detail.totals.budget_version}`} />
          </dl>
          <Button className="w-full" disabled={!canSubmit} icon={<Send size={17} />} type="submit" variant="primary">
            {submitting ? "Registrando..." : "Registrar envio"}
          </Button>
        </aside>
      </form>
    </Modal>
  );
}

function budgetLineTypeDescription(lineType: BudgetLineType) {
  return lineType === "service"
    ? "Mão de obra entra no orçamento e pode gerar comissão quando a OS for fechada."
    : "Peça entra só no orçamento; reserva e baixa continuam acontecendo no uso da peça.";
}

function WorkflowCard({
  actions,
  detail,
  onOpenFlow,
  onOpenHistory,
  onSimpleMove,
}: {
  actions: ServiceOrderWorkflowAction[];
  detail: ServiceOrderDetailResponse;
  onOpenFlow: (flow: "approve" | "reject" | "pickup") => void;
  onOpenHistory: () => void;
  onSimpleMove: (nextState: string) => Promise<void>;
}) {
  const [movingTo, setMovingTo] = useState<string | null>(null);

  async function handleAction(action: ServiceOrderWorkflowAction) {
    if (action.next_state === "Aprovado") {
      onOpenFlow("approve");
      return;
    }
    if (action.next_state === "Reprovado") {
      onOpenFlow("reject");
      return;
    }
    if (action.next_state === "Entregue") {
      onOpenFlow("pickup");
      return;
    }

    setMovingTo(action.next_state);
    try {
      await onSimpleMove(action.next_state);
    } finally {
      setMovingTo(null);
    }
  }

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-white">Mover etapa</h3>
          <p className="mt-1 text-xs text-tec-muted">Escolha a próxima etapa permitida pelo workflow.</p>
        </div>
        <BadgeStatus status={detail.workflow_state} />
      </div>
	  <WorkflowMoveMenu actions={actions} blockedTransitions={detail.workflow_blockers} busy={Boolean(movingTo)} className="mt-4" onSelect={(action) => void handleAction(action)} />
      <div className="mt-4 space-y-3">
        {actions.length ? (
          actions.map((action) => (
            <button
              className="group flex w-full items-center justify-between gap-3 rounded-card border border-tec-border/15 bg-tec-field/75 p-3 text-left transition hover:border-tec-orange/50 hover:bg-tec-orange/10"
              disabled={Boolean(movingTo)}
              key={`${action.action}-${action.next_state}`}
              onClick={() => void handleAction(action)}
              title={workflowActionTitle(action)}
              type="button"
            >
              <span className="flex min-w-0 items-center gap-3">
                <span className={cx("grid h-9 w-9 shrink-0 place-items-center rounded-control", workflowActionIconTone(action))}>
                  {workflowActionIcon(action)}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-bold text-white">
                    {movingTo === action.next_state ? "Atualizando..." : workflowActionLabel(action)}
                  </span>
                  <span className="mt-1 block text-xs text-tec-muted">{workflowActionDescription(action)}</span>
                </span>
              </span>
              <ArrowRight className="shrink-0 text-tec-orange transition group-hover:translate-x-0.5" size={17} />
            </button>
          ))
        ) : (
          <div className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4 text-sm text-tec-muted">
            Nenhuma ação disponível para este papel neste estado.
          </div>
        )}
        <button
          className="flex w-full items-center justify-between gap-3 rounded-card border border-tec-border/10 bg-tec-panel-strong/70 p-3 text-left transition hover:border-tec-orange/40 hover:bg-tec-field"
          onClick={onOpenHistory}
          type="button"
        >
          <span className="flex min-w-0 items-center gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-control bg-tec-blue/15 text-tec-blue">
              <History size={18} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-bold text-white">Ver todo o histórico da OS</span>
              <span className="mt-1 block text-xs text-tec-muted">Linha do tempo completa e eventos técnicos</span>
            </span>
          </span>
          <ArrowRight className="text-tec-orange" size={17} />
        </button>
      </div>
    </Card>
  );
}

function workflowActionLabel(action: ServiceOrderWorkflowAction) {
  if (action.next_state === "Aprovado") {
    return "Aprovar orçamento";
  }
  if (action.next_state === "Reprovado") {
    return "Reprovar orçamento";
  }
  if (action.next_state === "Entregue") {
    return "Entregar aparelho";
  }
  return action.action;
}

function workflowActionDescription(action: ServiceOrderWorkflowAction) {
  if (action.next_state === "Aprovado") {
    return "Aprovar e seguir para execução";
  }
  if (action.next_state === "Reprovado") {
    return "Devolver para revisão";
  }
  if (action.next_state === "Entregue") {
    return "Coletar assinatura e finalizar entrega";
  }
  return `Vai para ${action.next_state}`;
}

function workflowActionIcon(action: ServiceOrderWorkflowAction) {
  if (action.next_state === "Aprovado") {
    return <CheckCircle2 size={18} />;
  }
  if (action.next_state === "Reprovado") {
    return <XCircle size={18} />;
  }
  if (action.next_state === "Entregue") {
    return <Package size={18} />;
  }
  return <ArrowRight size={18} />;
}

function workflowActionIconTone(action: ServiceOrderWorkflowAction) {
  if (action.next_state === "Aprovado") {
    return "bg-tec-success/15 text-tec-success";
  }
  if (action.next_state === "Reprovado") {
    return "bg-tec-red/15 text-tec-red";
  }
  return "bg-tec-orange/10 text-tec-orange";
}

function workflowActionTitle(action: ServiceOrderWorkflowAction) {
  if (["Aprovado", "Reprovado", "Entregue"].includes(action.next_state)) {
    return `Abrir fluxo para ${workflowActionLabel(action).toLowerCase()}`;
  }
  return `Mover OS para ${action.next_state}`;
}

function TimelineCard({
  events,
  onOpenHistory,
}: {
  events: ServiceOrderTimelineEvent[];
  onOpenHistory?: () => void;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-xl font-bold text-white">Histórico da OS</h3>
        {onOpenHistory ? (
          <button
            className="text-sm font-bold text-tec-orange transition hover:text-tec-digital-orange"
            onClick={onOpenHistory}
            type="button"
          >
            Ver todos os eventos
          </button>
        ) : null}
      </div>
      <div className="mt-5 space-y-0">
        {events.map((event, index) => (
          <div className="relative flex gap-3 pb-5 last:pb-0" key={`${event.title}-${index}`}>
            {index < events.length - 1 ? <span className="absolute left-4 top-9 h-[calc(100%-2.25rem)] w-px bg-tec-border/15" /> : null}
            <span className={`mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full ${timelineToneClass(event.tone)}`}>
              <Clock3 size={15} />
            </span>
            <div className="min-w-0 rounded-card bg-tec-field/35 px-4 py-3">
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

function ServiceOrderHistoryModal({
  detail,
  onClose,
  open,
}: {
  detail: ServiceOrderDetailResponse;
  onClose: () => void;
  open: boolean;
}) {
  const customerLabel = detail.customer?.customer_name ?? detail.customer?.name ?? "Cliente não informado";
  const deviceLabel =
    [detail.device?.brand, detail.device?.model, detail.device?.color].filter(Boolean).join(" ") ||
    detail.device?.name ||
    "Aparelho não vinculado";

  return (
    <Modal className="max-w-5xl" onClose={onClose} open={open} title={`Histórico completo ${detail.name}`}>
      <div className="grid max-h-[78vh] gap-4 overflow-y-auto pr-1 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="space-y-3">
          {detail.timeline.length ? (
            detail.timeline.map((event, index) => (
              <div className="relative flex gap-3 pb-4 last:pb-0" key={`${event.title}-${event.date}-${index}`}>
                {index < detail.timeline.length - 1 ? (
                  <span className="absolute left-5 top-11 h-[calc(100%-2.5rem)] w-px bg-tec-border/15" />
                ) : null}
                <span className={`mt-1 grid h-10 w-10 shrink-0 place-items-center rounded-full ${timelineToneClass(event.tone)}`}>
                  {timelineIcon(event.tone)}
                </span>
                <div className="min-w-0 flex-1 rounded-card border border-tec-border/15 bg-tec-field/50 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-base font-bold text-white">{event.title}</p>
                      <p className="mt-1 text-sm text-tec-subtle">{event.detail ?? "Sem detalhe"}</p>
                    </div>
                    <span className="rounded-full bg-tec-panel-strong px-3 py-1 text-xs font-bold text-tec-muted">
                      {event.date ? formatDate(event.date) : "Sem data"}
                    </span>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="rounded-card border border-tec-border/15 bg-tec-field/50 p-4 text-sm font-semibold text-tec-subtle">
              Nenhum evento registrado para esta OS.
            </div>
          )}
        </section>

        <aside className="space-y-4">
          <div className="rounded-card border border-tec-border/15 bg-tec-panel-strong p-4">
            <h3 className="text-sm font-bold text-white">Resumo da OS</h3>
            <dl className="mt-4 space-y-3 text-sm">
              <DetailLine label="Status atual" value={detail.workflow_state ?? "Sem status"} />
              <DetailLine label="Cliente" value={customerLabel} />
              <DetailLine label="Aparelho" value={deviceLabel} />
              <DetailLine label="Entrada" value={formatDate(detail.entry_date)} />
              <DetailLine label="Atualização" value={formatDate(detail.modified)} />
            </dl>
          </div>

          <div className="rounded-card border border-tec-border/15 bg-tec-panel-strong p-4">
            <h3 className="text-sm font-bold text-white">Orçamento</h3>
            <dl className="mt-4 space-y-3 text-sm">
              <DetailLine label="Versão" value={`v${detail.totals.budget_version}`} />
              <DetailLine label="Trava" value={detail.totals.quote_locked ? "Travado" : "Em edição"} />
              <DetailLine label="Total" value={formatCurrency(detail.totals.grand_total)} />
              <DetailLine label="Prazo" value={detail.approval_deadline ? formatDate(detail.approval_deadline) : "Não definido"} />
            </dl>
          </div>

          <div className="rounded-card border border-tec-border/15 bg-tec-panel-strong p-4">
            <h3 className="text-sm font-bold text-white">Impressos</h3>
            <div className="mt-3 space-y-2">
              {detail.print_links.map((link) => (
                <a
                  className="flex min-h-10 items-center justify-between gap-3 rounded-control border border-tec-border/15 bg-tec-field px-3 text-sm font-bold text-tec-text transition hover:border-tec-orange/50"
                  href={link.url}
                  key={link.label}
                  rel="noreferrer"
                  target="_blank"
                >
                  {link.label}
                  <Printer size={16} />
                </a>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </Modal>
  );
}

function timelineIcon(tone: ServiceOrderTimelineEvent["tone"]) {
  if (tone === "green") {
    return <CheckCircle2 size={16} />;
  }
  if (tone === "red") {
    return <XCircle size={16} />;
  }
  if (tone === "amber" || tone === "orange") {
    return <Clock3 size={16} />;
  }
  return <History size={16} />;
}

function CourtesyWarrantyRequestModal({
  detail,
  onClose,
  onToast,
  open,
}: {
  detail: ServiceOrderDetailResponse;
  onClose: () => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  open: boolean;
}) {
  const [originalServiceOrder, setOriginalServiceOrder] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setOriginalServiceOrder("");
      setReason("");
    }
  }, [open]);

  async function submit() {
    if (!originalServiceOrder.trim() || !reason.trim()) {
      return;
    }
    setBusy(true);
    try {
      await approvalRequests.create(
        "courtesy_warranty",
        detail.name,
        reason.trim(),
        { original_service_order: originalServiceOrder.trim() },
      );
      onToast("Solicitacao de garantia-cortesia enviada, aguardando o Gestor.", "success");
      onClose();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Nao foi possivel solicitar a garantia-cortesia.", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal className="max-w-lg" onClose={onClose} open={open} title="Solicitar garantia-cortesia">
      <p className="text-sm leading-6 text-tec-subtle">
        O Gestor decide individualmente e o motor valida de novo se a OS original esta entregue e pertence ao mesmo cliente e aparelho.
      </p>
      <label className="mt-5 block text-sm font-bold text-white">
        OS original entregue
        <input
          className="mt-2 w-full rounded-control border border-tec-border/25 bg-tec-field p-3 text-white outline-none focus:border-tec-orange/70"
          onChange={(event) => setOriginalServiceOrder(event.target.value)}
          placeholder="Ex.: OS-2026-00001"
          value={originalServiceOrder}
        />
      </label>
      <label className="mt-4 block text-sm font-bold text-white">
        Motivo obrigatorio
        <textarea
          className="mt-2 min-h-28 w-full rounded-control border border-tec-border/25 bg-tec-field p-3 text-white outline-none focus:border-tec-orange/70"
          onChange={(event) => setReason(event.target.value)}
          placeholder="Explique por que a cobertura excepcional e necessaria."
          value={reason}
        />
      </label>
      <div className="mt-5 flex justify-end gap-2">
        <Button onClick={onClose} variant="ghost">Cancelar</Button>
        <Button disabled={!originalServiceOrder.trim() || !reason.trim() || busy} onClick={() => void submit()} variant="primary">
          {busy ? "Enviando..." : "Solicitar ao Gestor"}
        </Button>
      </div>
    </Modal>
  );
}

function ServiceOrderActionsModal({
  detail,
  onClose,
	onOpenAcceptance,
	onOpenCourtesyWarranty,
  onOpenBudgetEditor,
  onOpenHistory,
  onOpenQuoteSend,
  onRefresh,
  open,
}: {
  detail: ServiceOrderDetailResponse;
  onClose: () => void;
	onOpenAcceptance: (type: "Entrada" | "Retirada") => void;
  onOpenCourtesyWarranty: () => void;
  onOpenBudgetEditor: (type: BudgetLineType) => void;
  onOpenHistory: () => void;
  onOpenQuoteSend: () => void;
  onRefresh: () => void;
  open: boolean;
}) {
  const hasBudget = detail.services.length + detail.parts.length > 0;
  const canSendQuote = detail.workflow_state === "Aguardando aprovação" && hasBudget;

  return (
    <Modal className="max-w-3xl" onClose={onClose} open={open} title={`Ações da OS ${detail.name}`}>
      <div className="grid gap-4 md:grid-cols-2">
        <button
          className="rounded-card border border-tec-border/15 bg-tec-field/65 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-orange/10"
          onClick={() => onOpenBudgetEditor("service")}
          type="button"
        >
          <span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
            <Wrench size={20} />
          </span>
          <span className="mt-4 block text-base font-bold text-white">Adicionar serviço</span>
          <span className="mt-1 block text-sm text-tec-muted">Inclui mão de obra no orçamento desta OS.</span>
        </button>

		<button
			className="rounded-card border border-tec-border/15 bg-tec-field/65 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-orange/10"
			onClick={() => onOpenAcceptance("Entrada")}
			type="button"
		>
			<span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
				<QrCode size={20} />
			</span>
			<span className="mt-4 block text-base font-bold text-white">Gerar aceite de entrada</span>
			<span className="mt-1 block text-sm text-tec-muted">Exibe link e QR somente-leitura para o cliente confirmar o check-in.</span>
		</button>

		<button
			className="rounded-card border border-tec-border/15 bg-tec-field/65 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-orange/10"
			onClick={() => onOpenAcceptance("Retirada")}
			type="button"
		>
			<span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
				<QrCode size={20} />
			</span>
			<span className="mt-4 block text-base font-bold text-white">Gerar aceite de retirada</span>
			<span className="mt-1 block text-sm text-tec-muted">Prepara o link seguro para a confirmação de retirada.</span>
		</button>

        <button
          className="rounded-card border border-tec-border/15 bg-tec-field/65 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-orange/10"
          onClick={() => onOpenBudgetEditor("part")}
          type="button"
        >
          <span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
            <Package size={20} />
          </span>
          <span className="mt-4 block text-base font-bold text-white">Adicionar peça</span>
          <span className="mt-1 block text-sm text-tec-muted">Inclui peça do estoque de reparo no orçamento.</span>
        </button>

        {!detail.warranty.is_warranty ? (
          <button
            className="rounded-card border border-tec-amber/25 bg-tec-amber/5 p-4 text-left transition hover:border-tec-amber/55 hover:bg-tec-amber/10"
            onClick={onOpenCourtesyWarranty}
            type="button"
          >
            <span className="grid h-10 w-10 place-items-center rounded-control bg-tec-amber/15 text-tec-amber">
              <BadgeInfo size={20} />
            </span>
            <span className="mt-4 block text-base font-bold text-white">Solicitar garantia-cortesia</span>
            <span className="mt-1 block text-sm text-tec-muted">Encaminha a excecao ao Gestor com motivo e OS original.</span>
          </button>
        ) : null}

        <button
          className="rounded-card border border-tec-border/15 bg-tec-field/65 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-orange/10 disabled:cursor-not-allowed disabled:opacity-55"
          disabled={!canSendQuote}
          onClick={onOpenQuoteSend}
          title={canSendQuote ? "Enviar orçamento ao cliente" : "Disponível quando a OS estiver aguardando aprovação com orçamento cadastrado"}
          type="button"
        >
          <span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
            <Send size={20} />
          </span>
          <span className="mt-4 block text-base font-bold text-white">Enviar orçamento</span>
          <span className="mt-1 block text-sm text-tec-muted">Registra o envio por WhatsApp, telefone, presencial ou e-mail.</span>
        </button>

        <button
          className="rounded-card border border-tec-border/15 bg-tec-field/65 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-orange/10"
          onClick={onOpenHistory}
          type="button"
        >
          <span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
            <History size={20} />
          </span>
          <span className="mt-4 block text-base font-bold text-white">Ver histórico completo</span>
          <span className="mt-1 block text-sm text-tec-muted">Abre a linha do tempo, orçamento, status e impressos da OS.</span>
        </button>
      </div>

      <div className="mt-5 rounded-card border border-tec-border/15 bg-tec-panel-strong p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-base font-bold text-white">Impressos da OS</h3>
            <p className="mt-1 text-sm text-tec-muted">Documentos oficiais gerados pelo motor de impressão.</p>
          </div>
          <Button icon={<RefreshCw size={16} />} onClick={onRefresh}>
            Atualizar OS
          </Button>
        </div>
        <div className="mt-4">
          <PrintLinks links={detail.print_links} />
        </div>
      </div>
    </Modal>
  );
}

function AcceptanceLinkModal({
	acceptanceType,
	onClose,
	onToast,
	serviceOrder,
}: {
	acceptanceType: "Entrada" | "Retirada" | null;
	onClose: () => void;
	onToast: (message: string, tone?: ToastState["tone"]) => void;
	serviceOrder: string;
}) {
	const [result, setResult] = useState<AcceptanceIssueResponse | null>(null);
	const [busy, setBusy] = useState(false);
	const [physicalFile, setPhysicalFile] = useState<File | null>(null);
	const [physicalConfirmed, setPhysicalConfirmed] = useState(false);

	useEffect(() => {
		setResult(null);
		setBusy(false);
		setPhysicalFile(null);
		setPhysicalConfirmed(false);
	}, [acceptanceType, serviceOrder]);

	const issue = async () => {
		if (!acceptanceType) return;
		setBusy(true);
		try {
			const response = await balcao.issueAcceptance(serviceOrder, acceptanceType);
			setResult(response);
			onToast("Link de aceite gerado. Ele expira em 24 horas.");
		} catch (error) {
			onToast(error instanceof Error ? error.message : "Não foi possível gerar o link de aceite.", "error");
		} finally {
			setBusy(false);
		}
	};

	const archivePhysical = async () => {
		if (!acceptanceType || !physicalFile) return;
		setBusy(true);
		try {
			const fileData = await new Promise<string>((resolve, reject) => {
				const reader = new FileReader();
				reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Arquivo inválido."));
				reader.onerror = () => reject(new Error("Não foi possível ler o arquivo."));
				reader.readAsDataURL(physicalFile);
			});
			await balcao.recordPhysicalAcceptance({
				service_order: serviceOrder,
				acceptance_type: acceptanceType,
				file_data: fileData,
				file_name: physicalFile.name,
				term_confirmed: physicalConfirmed,
			});
			onToast("Aceite físico arquivado como evidência privada da OS.");
			onClose();
		} catch (error) {
			onToast(error instanceof Error ? error.message : "Não foi possível arquivar a via física.", "error");
		} finally {
			setBusy(false);
		}
	};

	const copyLink = async () => {
		if (!result) return;
		try {
			await navigator.clipboard.writeText(result.link);
			onToast("Link copiado para a área de transferência.");
		} catch {
			onToast("Copie o link manualmente.", "error");
		}
	};

	return (
		<Modal className="max-w-xl" onClose={onClose} open={Boolean(acceptanceType)} title={`Aceite por link — ${acceptanceType ?? ""}`}>
			{result ? (
				<div className="space-y-4">
					<p className="text-sm text-tec-subtle">Entregue este QR ao cliente. O link é de uso único e expira em {formatDate(result.expires_on)}.</p>
					<div className="flex justify-center rounded-card bg-white p-4"><img alt="QR Code do aceite" className="h-56 w-56" src={result.qr_svg} /></div>
					<label className="block text-sm font-bold text-tec-text">Link seguro
						<input className="tp-input mt-2 w-full" readOnly value={result.link} />
					</label>
					<div className="flex justify-end gap-2"><Button onClick={copyLink} variant="secondary">Copiar link</Button><Button onClick={onClose} variant="primary">Concluir</Button></div>
				</div>
			) : (
				<div className="space-y-5">
					<p className="text-sm leading-6 text-tec-subtle">Escolha como a evidência será coletada. O link digital exige selfie, assinatura e consentimento; a via física preserva somente a folha realmente assinada pelo cliente.</p>
					<div className="rounded-card border border-tec-border/20 bg-tec-field p-4"><h3 className="text-sm font-bold text-tec-text">Aceite digital</h3><p className="mt-1 text-xs text-tec-subtle">QR de uso único para captura ao vivo e assinatura.</p><Button className="mt-3" disabled={busy} icon={<QrCode size={17} />} onClick={() => void issue()} variant="primary">{busy ? "Gerando..." : "Gerar link e QR"}</Button></div>
					<div className="rounded-card border border-tec-border/20 bg-tec-field p-4"><h3 className="text-sm font-bold text-tec-text">Aceite físico arquivado</h3><p className="mt-1 text-xs text-tec-subtle">Envie a foto ou PDF da folha impressa e assinada. O arquivo fica privado e recebe hash de integridade.</p><input accept="image/jpeg,image/png,application/pdf" className="tp-input mt-3 w-full" onChange={(event) => setPhysicalFile(event.target.files?.[0] ?? null)} type="file" /><label className="mt-3 flex items-start gap-2 text-xs leading-5 text-tec-subtle"><input checked={physicalConfirmed} className="mt-1" onChange={(event) => setPhysicalConfirmed(event.target.checked)} type="checkbox" />Confirmo que esta é a via física assinada pelo cliente e que os termos aplicáveis foram apresentados.</label><Button className="mt-3" disabled={busy || !physicalFile || !physicalConfirmed} icon={<FileText size={17} />} onClick={() => void archivePhysical()} variant="secondary">Arquivar via física</Button></div>
				</div>
			)}
		</Modal>
	);
}

function PrintPrimaryLink({ links }: { links: ServiceOrderPrintLink[] }) {
  const primary = links.find((link) => link.label.toLowerCase().includes("orçamento")) ?? links[0];
  if (!primary) {
    return (
      <button
        className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control border border-tec-border/20 bg-tec-field px-4 text-sm font-semibold text-tec-text transition hover:border-tec-orange/50"
        disabled
        type="button"
      >
        <Printer size={17} />
        Imprimir
      </button>
    );
  }

  return (
    <a
      className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control border border-tec-border/20 bg-tec-field px-4 text-sm font-semibold text-tec-text transition hover:border-tec-orange/50 hover:text-white"
      href={primary.url}
      rel="noreferrer"
      target="_blank"
      title={`Abrir ${primary.label}`}
    >
      <Printer size={17} />
      Imprimir
    </a>
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
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control border border-tec-border/20 bg-tec-panel-strong/70 px-4 text-sm font-semibold text-tec-text transition hover:border-tec-orange/50"
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
    <div className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-3">
      <p className="text-xs text-tec-muted">{label}</p>
      <p className={strong ? "tp-metric-value mt-1 text-lg font-bold text-tec-orange" : "mt-1 font-semibold text-tec-subtle"}>{value}</p>
    </div>
  );
}

function CustomerLookup({ canEdit, onToast }: { canEdit: boolean; onToast: (message: string, tone?: ToastState["tone"]) => void }) {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<CustomerSummary[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerSummary | null>(null);
	const [editingCustomer, setEditingCustomer] = useState<CustomerSummary | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [registrationOpen, setRegistrationOpen] = useState(false);
  const [presentation, setPresentation] = useState<ListPresentation>(() => getStoredListPresentation("tecponto.customers.presentation"));
  const [quickFilter, setQuickFilter] = useState("all");
  const [advancedFilter, setAdvancedFilter] = useState("all");

  const [statItems, setStatItems] = useState<Array<{ key: string; label: string; value: number }>>([]);
	const [suggestionsOpen, setSuggestionsOpen] = useState(false);
	const [selectedSuggestion, setSelectedSuggestion] = useState(0);

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
    void balcao.getListStatBar("customers").then((result) => setStatItems(result.items)).catch(() => setStatItems([]));
  }, [search]);

  useEffect(() => {
    window.localStorage.setItem("tecponto.customers.presentation", presentation);
  }, [presentation]);

  const filteredRows = useMemo(() => rows.filter((row) => {
    if (quickFilter === "whatsapp") return Boolean(row.custom_whatsapp || row.mobile_no);
    if (quickFilter === "email") return Boolean(row.email_id);
    if (advancedFilter === "no_contact") return !row.custom_whatsapp && !row.mobile_no && !row.email_id;
    if (advancedFilter === "no_document") return !row.custom_cpf && !row.custom_rg;
    return true;
  }), [advancedFilter, quickFilter, rows]);

	useEffect(() => {
		const term = query.trim();
		if (term.length < 2) {
			setSuggestionsOpen(false);
			return;
		}
		const timer = window.setTimeout(() => {
			void search(term);
			setSuggestionsOpen(true);
			setSelectedSuggestion(0);
		}, 220);
		return () => window.clearTimeout(timer);
	}, [query, search]);

	const chooseCustomer = useCallback((customer: CustomerSummary) => {
		setSelectedCustomer(customer);
		setSuggestionsOpen(false);
	}, []);

	const handleSearchKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
		if (event.key === "Escape") {
			setSuggestionsOpen(false);
			return;
		}
		if (!suggestionsOpen || !rows.length) return;
		if (event.key === "ArrowDown") {
			event.preventDefault();
			setSelectedSuggestion((current) => (current + 1) % rows.length);
		}
		if (event.key === "ArrowUp") {
			event.preventDefault();
			setSelectedSuggestion((current) => (current - 1 + rows.length) % rows.length);
		}
		if (event.key === "Enter") {
			event.preventDefault();
			chooseCustomer(rows[selectedSuggestion]);
		}
	};

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
    <>
      <LookupCard
        columns={columns}
        emptyLabel={status === "error" ? "Falha ao buscar clientes." : "Nenhum cliente encontrado."}
        headerAction={
          <Button icon={<Plus size={17} />} onClick={() => setRegistrationOpen(true)} variant="primary">
            Cadastrar cliente
          </Button>
        }
		onRowClick={chooseCustomer}
		getRowProps={(customer) => ({
			"data-tp-context": "customer",
			"data-tp-label": customer.customer_name ?? customer.name,
			"data-tp-name": customer.name,
		})}
		renderCardAction={canEdit ? (customer) => <button aria-label={`Editar ${customer.customer_name ?? customer.name}`} className="grid h-8 w-8 place-items-center rounded-control border border-tec-border/20 bg-tec-panel text-tec-muted transition hover:border-tec-orange/50 hover:text-white" onClick={(event) => { event.stopPropagation(); setEditingCustomer(customer); }} title="Editar cliente" type="button"><Edit3 size={15} /></button> : undefined}
        onSearch={(event) => {
          event.preventDefault();
          void search(query);
        }}
		onSearchFocus={() => setSuggestionsOpen(query.trim().length >= 2)}
		onSearchKeyDown={handleSearchKeyDown}
        placeholder="Buscar cliente por nome, telefone ou e-mail"
        query={query}
		searchSuggestions={
			suggestionsOpen ? (
				<div className="absolute left-0 right-0 top-[calc(100%+0.35rem)] z-30 overflow-hidden rounded-control border border-tec-border/25 bg-tec-panel-strong p-1.5 shadow-panel" role="listbox">
					{status === "loading" ? <p className="px-3 py-2 text-sm text-tec-muted">Buscando clientes...</p> : null}
					{status === "ready" && rows.length === 0 ? <p className="px-3 py-2 text-sm text-tec-muted">Nenhum cliente encontrado.</p> : null}
					{status === "ready" ? rows.slice(0, 6).map((customer, index) => (
						<button
							className={selectedSuggestion === index ? "flex w-full items-center justify-between gap-3 rounded-control bg-tec-orange/10 px-3 py-2.5 text-left ring-1 ring-tec-orange/55" : "flex w-full items-center justify-between gap-3 rounded-control px-3 py-2.5 text-left hover:bg-tec-field"}
							key={customer.name}
							onClick={() => chooseCustomer(customer)}
							role="option"
							type="button"
						>
							<span className="min-w-0"><span className="block truncate text-sm font-bold text-white">{customer.customer_name ?? customer.name}</span><span className="mt-0.5 block truncate text-xs text-tec-muted">{customer.custom_whatsapp || customer.mobile_no || customer.email_id || customer.name}</span></span>
							<ArrowRight className="shrink-0 text-tec-muted" size={16} />
						</button>
					)) : null}
				</div>
			) : null
		}
        setQuery={setQuery}
		statBar={<StatBar items={statItems.map((item) => ({ ...item, ...getStatBarVisual("customers", item.key) }))} />}
        status={status}
        title="Clientes"
        activeQuickFilter={quickFilter}
        advancedFilters={<label className="block text-xs font-bold text-tec-subtle">Dados cadastrais<select className="tp-input mt-1 w-full" onChange={(event) => setAdvancedFilter(event.target.value)} value={advancedFilter}><option value="all">Sem filtro adicional</option><option value="no_contact">Sem contato informado</option><option value="no_document">Sem CPF ou RG</option></select></label>}
        onClear={() => { setQuickFilter("all"); setAdvancedFilter("all"); }}
        onPresentationChange={setPresentation}
        onQuickFilterChange={setQuickFilter}
        presentation={presentation}
        quickFilters={[{ key: "all", label: "Todos" }, { key: "whatsapp", label: "Com WhatsApp" }, { key: "email", label: "Com e-mail" }]}
        rows={filteredRows}
      />
      <CustomerRegistrationModal
        onClose={() => setRegistrationOpen(false)}
        onCreated={(customer) => {
          setRows((current) => [customer, ...current.filter((row) => row.name !== customer.name)]);
          setSelectedCustomer(customer);
          onToast(`Cliente ${customer.customer_name || customer.name} cadastrado.`);
        }}
        open={registrationOpen}
      />
	  <CustomerDetailModal canEdit={canEdit} customer={selectedCustomer} onClose={() => setSelectedCustomer(null)} onEdit={() => selectedCustomer && setEditingCustomer(selectedCustomer)} />
	  <RegistryEditorModal
		kind="customer"
		name={editingCustomer?.name}
		onClose={() => setEditingCustomer(null)}
		onSaved={(updated) => {
			if (!("customer_name" in updated)) return;
			const customer = updated as CustomerSummary;
			setRows((current) => current.map((row) => row.name === customer.name ? customer : row));
			setSelectedCustomer(customer);
			onToast("Cliente atualizado.");
		}}
		open={Boolean(editingCustomer)}
	  />
    </>
  );
}

function CustomerRegistrationModal({
  onClose,
  onCreated,
  open,
}: {
  onClose: () => void;
  onCreated: (customer: CustomerSummary) => void;
  open: boolean;
}) {
  const [form, setForm] = useState<CreateCustomerPayload>({ customer_name: "", mobile_no: "", custom_cpf: "", email_id: "" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const noCpf = Boolean(form.custom_nao_possui_cpf);

  useEffect(() => {
    if (!open) {
      setForm({ customer_name: "", mobile_no: "", custom_cpf: "", email_id: "" });
      setError("");
      setSubmitting(false);
    }
  }, [open]);

  const update = (key: keyof CreateCustomerPayload, value: string | boolean) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const response = await balcao.createCustomer({
        ...form,
        custom_cpf: noCpf ? "" : form.custom_cpf,
        custom_rg: noCpf ? form.custom_rg : "",
        custom_whatsapp: form.mobile_no,
      });
      onCreated(response.item);
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível cadastrar o cliente.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal className="max-w-xl" onClose={onClose} open={open} title="Cadastrar cliente">
      <form className="space-y-4" onSubmit={submit}>
        <p className="text-sm text-tec-muted">Os campos marcados são conferidos pelo motor antes de salvar.</p>
        <CustomerFormField label="Nome completo" required>
          <input autoFocus className="tp-input" onChange={(event) => update("customer_name", event.target.value)} placeholder="Nome do cliente" value={form.customer_name} />
        </CustomerFormField>
        <CustomerFormField label="WhatsApp / telefone" required>
          <input className="tp-input" inputMode="tel" onChange={(event) => update("mobile_no", event.target.value)} placeholder="(11) 99999-9999" value={form.mobile_no} />
        </CustomerFormField>
        <label className="flex cursor-pointer items-center gap-3 rounded-control border border-tec-border/20 bg-tec-field/55 px-3 py-3 text-sm font-semibold text-tec-text">
          <input checked={noCpf} className="h-4 w-4 accent-tec-orange" onChange={(event) => update("custom_nao_possui_cpf", event.target.checked)} type="checkbox" />
          Cliente não possui CPF
        </label>
        {noCpf ? (
          <CustomerFormField label="RG" required>
            <input className="tp-input" onChange={(event) => update("custom_rg", event.target.value)} placeholder="Informe o RG" value={form.custom_rg || ""} />
          </CustomerFormField>
        ) : (
          <CustomerFormField label="CPF" required>
            <input className="tp-input" inputMode="numeric" onChange={(event) => update("custom_cpf", event.target.value)} placeholder="000.000.000-00" value={form.custom_cpf || ""} />
          </CustomerFormField>
        )}
        <CustomerFormField label="E-mail" optional>
          <input className="tp-input" inputMode="email" onChange={(event) => update("email_id", event.target.value)} placeholder="cliente@email.com" type="email" value={form.email_id || ""} />
        </CustomerFormField>
        {error ? <p className="rounded-control border border-red-500/25 bg-red-500/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</p> : null}
        <div className="flex justify-end gap-3 border-t border-tec-border/15 pt-4">
          <Button onClick={onClose} type="button" variant="secondary">Cancelar</Button>
          <Button disabled={submitting} icon={<Plus size={17} />} type="submit" variant="primary">{submitting ? "Salvando..." : "Cadastrar cliente"}</Button>
        </div>
      </form>
    </Modal>
  );
}

function CustomerFormField({ children, label, optional, required }: { children: ReactNode; label: string; optional?: boolean; required?: boolean }) {
  return (
    <label className="block space-y-2 text-sm font-bold text-tec-text">
      <span className="flex items-center justify-between gap-3">
        {label}
        <span className={required ? "text-xs uppercase text-tec-orange" : "text-xs uppercase text-tec-muted"}>{required ? "Obrigatório" : optional ? "Opcional" : ""}</span>
      </span>
      {children}
    </label>
  );
}

function DeviceLookup({ canEdit, onToast }: { canEdit: boolean; onToast: (message: string, tone?: ToastState["tone"]) => void }) {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<CustomerDeviceSummary[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<CustomerDeviceSummary | null>(null);
	const [editingDevice, setEditingDevice] = useState<CustomerDeviceSummary | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [registrationOpen, setRegistrationOpen] = useState(false);
  const [presentation, setPresentation] = useState<ListPresentation>(() => getStoredListPresentation("tecponto.devices.presentation"));
  const [quickFilter, setQuickFilter] = useState("all");
  const [advancedFilter, setAdvancedFilter] = useState("all");

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

  useEffect(() => {
    window.localStorage.setItem("tecponto.devices.presentation", presentation);
  }, [presentation]);

  const filteredRows = useMemo(() => rows.filter((row) => {
    if (quickFilter === "imei") return Boolean(row.imei_serial);
    if (quickFilter === "photo") return Boolean(row.photo_url);
    if (advancedFilter === "without_imei") return !row.imei_serial;
    if (advancedFilter === "without_photo") return !row.photo_url;
    return true;
  }), [advancedFilter, quickFilter, rows]);

  const columns = useMemo<Array<TableColumn<CustomerDeviceSummary>>>(
    () => [
      {
        key: "photo",
        label: "Foto",
        render: (row) =>
          row.photo_url ? (
            <img alt="" className="h-11 w-11 rounded-control object-cover" src={row.photo_url} />
          ) : (
            <span className="grid h-11 w-11 place-items-center rounded-control bg-tec-field text-tec-orange">
              <Smartphone size={18} />
            </span>
          ),
      },
      { key: "name", label: "Cadastro", render: (row) => <span className="font-semibold text-white">{row.name}</span> },
      { key: "customer", label: "Cliente", render: (row) => row.customer ?? "Sem cliente" },
      { key: "model", label: "Aparelho", render: (row) => [row.brand, row.model].filter(Boolean).join(" ") || "Sem modelo" },
      { key: "imei_serial", label: "IMEI / Serial", render: (row) => row.imei_serial ?? "Não informado" },
      { key: "capacity", label: "Capacidade", render: (row) => row.capacity ?? "Não informada" },
    ],
    [],
  );

  return (
    <>
      <LookupCard
        columns={columns}
        emptyLabel={status === "error" ? "Falha ao buscar aparelhos." : "Nenhum aparelho encontrado."}
        headerAction={
          <Button icon={<Plus size={17} />} onClick={() => setRegistrationOpen(true)} variant="primary">
            Cadastrar aparelho
          </Button>
        }
        onSearch={(event) => {
          event.preventDefault();
          void search(query);
        }}
        onRowClick={setSelectedDevice}
		renderCardAction={canEdit ? (device) => <button aria-label={`Editar ${device.name}`} className="grid h-8 w-8 place-items-center rounded-control border border-tec-border/20 bg-tec-panel text-tec-muted transition hover:border-tec-orange/50 hover:text-white" onClick={(event) => { event.stopPropagation(); setEditingDevice(device); }} title="Editar aparelho" type="button"><Edit3 size={15} /></button> : undefined}
        placeholder="Buscar por cliente, modelo ou IMEI"
        activeQuickFilter={quickFilter}
        advancedFilters={<label className="block text-xs font-bold text-tec-subtle">Complementos do cadastro<select className="tp-input mt-1 w-full" onChange={(event) => setAdvancedFilter(event.target.value)} value={advancedFilter}><option value="all">Sem filtro adicional</option><option value="without_imei">Sem IMEI ou serial</option><option value="without_photo">Sem foto</option></select></label>}
		onClear={() => { setQuickFilter("all"); setAdvancedFilter("all"); }}
        onPresentationChange={setPresentation}
        onQuickFilterChange={setQuickFilter}
        presentation={presentation}
        query={query}
        quickFilters={[{ key: "all", label: "Todos" }, { key: "imei", label: "Com IMEI" }, { key: "photo", label: "Com foto" }]}
        rows={filteredRows}
        setQuery={setQuery}
        status={status}
        title="Aparelhos"
      />
      <DeviceRegistrationModal
        onClose={() => setRegistrationOpen(false)}
        onCreated={(device) => {
          setRows((current) => [device, ...current.filter((row) => row.name !== device.name)]);
          onToast(`Aparelho ${device.name} cadastrado.`);
        }}
        open={registrationOpen}
      />
	  <DeviceDetailModal canEdit={canEdit} device={selectedDevice} onClose={() => setSelectedDevice(null)} onEdit={() => selectedDevice && setEditingDevice(selectedDevice)} />
	  <RegistryEditorModal
		kind="device"
		name={editingDevice?.name}
		onClose={() => setEditingDevice(null)}
		onSaved={(updated) => {
			if (!("imei_serial" in updated)) return;
			const device = updated as CustomerDeviceSummary;
			setRows((current) => current.map((row) => row.name === device.name ? device : row));
			setSelectedDevice(device);
			onToast("Aparelho atualizado.");
		}}
		open={Boolean(editingDevice)}
	  />
    </>
  );
}

function CustomerDetailModal({ canEdit, customer, onClose, onEdit }: { canEdit: boolean; customer: CustomerSummary | null; onClose: () => void; onEdit: () => void }) {
  const label = customer?.customer_name ?? customer?.name ?? "Cliente";
  const whatsappUrl = customer
    ? buildWhatsAppUrl(customer.custom_whatsapp || customer.mobile_no, `Olá, ${label}. Aqui é da ${commercialName()}. Podemos falar por aqui?`)
    : null;

  return (
    <Modal className="max-w-2xl" onClose={onClose} open={Boolean(customer)} title="Detalhe do cliente">
      {customer ? (
        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-2xl font-bold text-white">{label}</p>
                <p className="mt-1 text-sm text-tec-muted">{customer.name}</p>
              </div>
			  <div className="flex flex-wrap items-center justify-end gap-2">
			  {canEdit ? <Button icon={<Edit3 size={16} />} onClick={onEdit}>Editar</Button> : null}
              {whatsappUrl ? (
                <a
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control border border-tec-whatsapp/35 bg-tec-whatsapp/10 px-4 text-sm font-bold text-tec-whatsapp transition hover:bg-tec-whatsapp/20"
                  href={whatsappUrl}
                  rel="noreferrer"
                  target="_blank"
                >
                  <WhatsAppLogo size={17} />
                  WhatsApp
                </a>
			  ) : null}
			  </div>
            </div>
            <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
              <DetailPill label="Telefone" value={customer.custom_whatsapp || customer.mobile_no || "Não informado"} />
              <DetailPill label="E-mail" value={customer.email_id || "Não informado"} />
              <DetailPill label="CPF" value={customer.custom_nao_possui_cpf ? "Não possui" : customer.custom_cpf || "Não informado"} />
              <DetailPill label="RG" value={customer.custom_rg || "Não informado"} />
            </dl>
          </Card>
        </div>
      ) : null}
    </Modal>
  );
}

function DeviceDetailModal({ canEdit, device, onClose, onEdit }: { canEdit: boolean; device: CustomerDeviceSummary | null; onClose: () => void; onEdit: () => void }) {
  const deviceLabel = device ? [device.brand, device.model, device.color].filter(Boolean).join(" ") || device.name : "Aparelho";

  return (
    <Modal className="max-w-2xl" onClose={onClose} open={Boolean(device)} title="Detalhe do aparelho">
      {device ? (
        <Card className="p-5">
          <div className="flex flex-col gap-4 sm:flex-row">
            {device.photo_url ? (
              <img alt="" className="h-28 w-28 rounded-card object-cover" src={device.photo_url} />
            ) : (
              <span className="grid h-28 w-28 place-items-center rounded-card bg-tec-field text-tec-orange">
                <Smartphone size={34} />
              </span>
            )}
			<div className="min-w-0 flex-1">
				<div className="flex justify-end">{canEdit ? <Button icon={<Edit3 size={16} />} onClick={onEdit}>Editar</Button> : null}</div>
              <p className="text-2xl font-bold text-white">{deviceLabel}</p>
              <p className="mt-1 text-sm text-tec-muted">{device.name}</p>
              <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <DetailPill label="Cliente" value={device.customer || "Sem cliente"} />
                <DetailPill label="IMEI / Serial" value={device.imei_serial || "Não informado"} />
                <DetailPill label="Capacidade" value={device.capacity || "Não informada"} />
                <DetailPill label="Cadastro" value={formatDate(device.registration_date)} />
              </dl>
            </div>
          </div>
        </Card>
      ) : null}
    </Modal>
  );
}

function DetailPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-tec-border/15 bg-tec-field/55 p-3">
      <dt className="text-xs font-bold uppercase text-tec-muted">{label}</dt>
      <dd className="mt-1 break-words text-sm font-semibold text-tec-text">{value}</dd>
    </div>
  );
}

function TradeLookup({ onToast }: { onToast: (message: string, tone?: ToastState["tone"]) => void }) {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<TradeEvaluationSummary[]>([]);
  const [selectedTrade, setSelectedTrade] = useState<TradeEvaluationSummary | null>(null);
	const [createOpen, setCreateOpen] = useState(false);
	const [operationOpen, setOperationOpen] = useState(false);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [statItems, setStatItems] = useState<Array<{ key: string; label: string; value: number }>>([]);
  const [presentation, setPresentation] = useState<ListPresentation>(() => getStoredListPresentation("tecponto.trades.presentation"));
  const [quickFilter, setQuickFilter] = useState("open");
  const [advancedFilter, setAdvancedFilter] = useState("all");

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
    void balcao.getListStatBar("trades").then((result) => setStatItems(result.items)).catch(() => setStatItems([]));
  }, [search]);

  useEffect(() => {
    window.localStorage.setItem("tecponto.trades.presentation", presentation);
  }, [presentation]);

  const filteredRows = useMemo(() => rows.filter((row) => {
    if (quickFilter === "approval") return row.workflow_state === "Aguardando aprovação";
    if (quickFilter === "purchased") return row.workflow_state === "Comprado";
    if (quickFilter === "open") return !["Comprado", "Descartado"].includes(row.workflow_state ?? "");
    if (advancedFilter === "with_imei") return Boolean(row.imei);
    if (advancedFilter === "without_imei") return !row.imei;
    return true;
  }), [advancedFilter, quickFilter, rows]);

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
    <>
      <LookupCard
        columns={columns}
        emptyLabel={status === "error" ? "Falha ao buscar trocas." : "Nenhuma avaliação encontrada."}
        onRowClick={setSelectedTrade}
        onSearch={(event) => {
          event.preventDefault();
          void search(query);
        }}
        placeholder="Buscar por cliente, aparelho ou IMEI"
        query={query}
        rows={filteredRows}
        setQuery={setQuery}
        statBar={<StatBar items={statItems.map((item) => ({ ...item, ...getStatBarVisual("trades", item.key) }))} />}
        status={status}
        title="Trocas"
		headerAction={<Button icon={<Plus size={16} />} onClick={() => setCreateOpen(true)}>Nova avaliação</Button>}
        activeQuickFilter={quickFilter}
        advancedFilters={<label className="block text-xs font-bold text-tec-subtle">Identificação do aparelho<select className="tp-input mt-1 w-full" onChange={(event) => setAdvancedFilter(event.target.value)} value={advancedFilter}><option value="all">Todas</option><option value="with_imei">Com IMEI ou serial</option><option value="without_imei">Sem IMEI ou serial</option></select></label>}
        onClear={() => { setQuickFilter("open"); setAdvancedFilter("all"); }}
        onPresentationChange={setPresentation}
        onQuickFilterChange={setQuickFilter}
        presentation={presentation}
        quickFilters={[{ key: "open", label: "Em andamento" }, { key: "approval", label: "Aguardando aprovação" }, { key: "purchased", label: "Compradas" }, { key: "all", label: "Todas" }]}
      />
		<TradeEvaluationDetailModal
			evaluation={selectedTrade}
			onClose={() => setSelectedTrade(null)}
			onSaved={(updated) => {
				setRows((current) => current.map((row) => row.name === updated.name ? updated : row));
				setSelectedTrade(updated);
			}}
			onOpenOperation={() => setOperationOpen(true)}
			onToast={onToast}
		/>
		<TradeEvaluationCreateModal
			onClose={() => setCreateOpen(false)}
			onCreated={(created) => {
				setRows((current) => [created, ...current]);
				setCreateOpen(false);
				setSelectedTrade(created);
				onToast("Avaliação criada. Registre o valor aprovado para concluir a operação.", "success");
			}}
			onToast={onToast}
			open={createOpen}
		/>
		<TradeInOperationModal
			evaluation={selectedTrade}
			onClose={() => setOperationOpen(false)}
			onCompleted={(updated) => {
				setRows((current) => current.map((row) => row.name === updated.name ? updated : row));
				setSelectedTrade(updated);
				setOperationOpen(false);
			}}
			onToast={onToast}
			open={operationOpen}
		/>
    </>
  );
}

function TradeEvaluationDetailModal({
  evaluation,
  onClose,
	onSaved,
	onOpenOperation,
	onToast,
}: {
  evaluation: TradeEvaluationSummary | null;
  onClose: () => void;
	onSaved: (evaluation: TradeEvaluationSummary) => void;
	onOpenOperation: () => void;
	onToast: (message: string, tone?: ToastState["tone"]) => void;
}) {
	const [approvedValue, setApprovedValue] = useState("");
	const [saving, setSaving] = useState(false);
	const [approvalNeeded, setApprovalNeeded] = useState(false);
	const [buying, setBuying] = useState(false);

	useEffect(() => {
		setApprovedValue(evaluation?.approved_value ? String(evaluation.approved_value) : "");
		setApprovalNeeded(false);
	}, [evaluation?.name, evaluation?.approved_value]);

  const deviceLabel = evaluation
    ? evaluation.evaluated_device_desc || [evaluation.device_type, evaluation.model].filter(Boolean).join(" ") || "Aparelho avaliado"
    : "Aparelho avaliado";

	const saveApprovedValue = async () => {
		if (!evaluation) return;
		const value = Number(approvedValue.replace(",", "."));
		if (!Number.isFinite(value) || value <= 0) {
			onToast("Informe um valor de troca maior que zero.", "error");
			return;
		}
		setSaving(true);
		try {
			const response = await balcao.setTradeInApprovedValue(evaluation.name, value);
			onSaved(response.item);
			onToast("Valor da troca registrado.", "success");
		} catch (error) {
			const message = error instanceof Error ? error.message : "Não foi possível registrar o valor.";
			if (message.includes("acima do maximo") || message.includes("acima do máximo")) {
				setApprovalNeeded(true);
			} else {
				onToast(message, "error");
			}
		} finally {
			setSaving(false);
		}
	};

	const completeBuyback = async () => {
		if (!evaluation) return;
		setBuying(true);
		try {
			const response = await balcao.completeTradeBuyback(evaluation.name);
			onSaved(response.item);
			onToast(response.created_item ? `Compra concluída. Item ${response.created_item} entrou no estoque.` : "Compra concluída.", "success");
		} catch (error) {
			onToast(error instanceof Error ? error.message : "Não foi possível concluir a compra.", "error");
		} finally {
			setBuying(false);
		}
	};

  return (
    <Modal className="max-w-2xl" onClose={onClose} open={Boolean(evaluation)} title="Detalhe da avaliação">
      {evaluation ? (
        <Card className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-2xl font-bold text-white">{evaluation.name}</p>
              <p className="mt-1 text-sm text-tec-muted">{evaluation.customer || "Cliente não informado"}</p>
            </div>
            <BadgeStatus status={evaluation.workflow_state} />
          </div>
          <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
            <DetailPill label="Aparelho" value={deviceLabel} />
            <DetailPill label="IMEI / Serial" value={evaluation.imei || "Não informado"} />
            <DetailPill label="Estado físico" value={evaluation.physical_state || "Não informado"} />
            <DetailPill label="Destino" value={evaluation.destination || "Não definido"} />
            <DetailPill label="Tipo" value={evaluation.device_type || "Não definido"} />
			<DetailPill label="Faixa máxima" value={evaluation.table_max ? evaluation.table_max.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "Não definida"} />
            <DetailPill label="Atualização" value={formatDate(evaluation.modified)} />
          </dl>
			<div className="mt-5 rounded-card border border-tec-border/15 bg-tec-field/45 p-4">
				<p className="text-sm font-bold text-white">Valor aprovado na troca</p>
				<p className="mt-1 text-sm text-tec-muted">O valor acima da tabela exige autorização registrada do Gestor.</p>
				<div className="mt-3 flex flex-col gap-2 sm:flex-row">
					<input className="tp-input flex-1" inputMode="decimal" onChange={(event) => setApprovedValue(event.target.value)} placeholder="R$ 0,00" value={approvedValue} />
					<Button disabled={saving} onClick={() => void saveApprovedValue()} variant="primary">{saving ? "Validando..." : "Registrar valor"}</Button>
				</div>
			</div>
			{evaluation.approved_value > 0 && !evaluation.created_item && evaluation.destination !== "Descarte" ? <div className="mt-4 flex flex-wrap justify-end gap-2">
				<Button disabled={buying} onClick={() => void completeBuyback()} variant="secondary">{buying ? "Concluindo..." : "Concluir buyback"}</Button>
				<Button icon={<ArrowRightLeft size={16} />} onClick={onOpenOperation}>Confirmar troca</Button>
			</div> : null}
			{evaluation.created_item ? <div className="mt-4 rounded-control border border-tec-success/25 bg-tec-success/10 px-3 py-2 text-sm font-semibold text-tec-success">Aparelho recebido como item único: {evaluation.created_item}</div> : null}
        </Card>
      ) : null}
		<ApprovalRequestModal
			onClose={() => setApprovalNeeded(false)}
			onCreated={() => setApprovalNeeded(false)}
			onToast={onToast}
			open={approvalNeeded}
			payload={{ approved_value: Number(approvedValue.replace(",", ".")) }}
			referenceName={evaluation?.name ?? ""}
			requestType="tradein_over_max"
			title="Este valor supera a faixa da tabela. Deseja solicitar aprovação do Gestor?"
		/>
    </Modal>
  );
}

function TradeEvaluationCreateModal({
	onClose,
	onCreated,
	onToast,
	open,
}: {
	onClose: () => void;
	onCreated: (evaluation: TradeEvaluationSummary) => void;
	onToast: (message: string, tone?: ToastState["tone"]) => void;
	open: boolean;
}) {
	const [customerQuery, setCustomerQuery] = useState("");
	const [customers, setCustomers] = useState<CustomerSummary[]>([]);
	const [customer, setCustomer] = useState<CustomerSummary | null>(null);
	const [model, setModel] = useState("");
	const [imei, setImei] = useState("");
	const [deviceType, setDeviceType] = useState<"iPhone" | "Android">("iPhone");
	const [physicalState, setPhysicalState] = useState<"A" | "B" | "C" | "Sucata">("B");
	const [destination, setDestination] = useState<"Venda" | "Peças" | "Descarte">("Venda");
	const [suggestedValue, setSuggestedValue] = useState("");
	const [tableMax, setTableMax] = useState("");
	const [defects, setDefects] = useState("");
	const [saving, setSaving] = useState(false);

	useEffect(() => {
		if (!open) return;
		setCustomerQuery(""); setCustomers([]); setCustomer(null); setModel(""); setImei(""); setDeviceType("iPhone"); setPhysicalState("B"); setDestination("Venda"); setSuggestedValue(""); setTableMax(""); setDefects("");
	}, [open]);

	useEffect(() => {
		if (!open || customer) return;
		const normalized = customerQuery.trim();
		if (normalized.length < 2) { setCustomers([]); return; }
		const timer = window.setTimeout(() => {
			void balcao.searchCustomers(normalized, 8).then((response) => setCustomers(response.items)).catch(() => setCustomers([]));
		}, 220);
		return () => window.clearTimeout(timer);
	}, [customer, customerQuery, open]);

	const submit = async (event: FormEvent<HTMLFormElement>) => {
		event.preventDefault();
		const value = Number(suggestedValue.replace(",", "."));
		if (!customer || !model.trim() || !imei.trim() || !Number.isFinite(value) || value <= 0) {
			onToast("Selecione o cliente e informe modelo, IMEI/serial e valor avaliado.", "error");
			return;
		}
		setSaving(true);
		try {
			const payload: CreateTradeEvaluationPayload = {
				customer: customer.name,
				device_type: deviceType,
				model: model.trim(),
				evaluated_device_desc: `${deviceType} ${model.trim()}`,
				imei: imei.trim(),
				physical_state: physicalState,
				destination,
				suggested_value: value,
				table_max: Number(tableMax.replace(",", ".")) || undefined,
				defects: defects.trim() || undefined,
			};
			const response = await balcao.createTradeEvaluation(payload);
			onCreated(response.item);
		} catch (error) {
			onToast(error instanceof Error ? error.message : "Não foi possível criar a avaliação.", "error");
		} finally {
			setSaving(false);
		}
	};

	return <Modal className="max-w-3xl" onClose={onClose} open={open} title="Nova avaliação de troca">
		<form className="space-y-5" onSubmit={(event) => void submit(event)}>
			<section className="rounded-card border border-tec-border/15 bg-tec-field/40 p-4">
				<label className="block text-sm font-bold text-white">Cliente</label>
				{customer ? <div className="mt-2 flex items-center justify-between gap-3 rounded-control border border-tec-success/30 bg-tec-success/10 px-3 py-2"><span className="min-w-0 truncate text-sm font-semibold text-tec-text">{customer.customer_name || customer.name}</span><button className="text-xs font-bold text-tec-success" onClick={() => { setCustomer(null); setCustomerQuery(""); }} type="button">Trocar</button></div> : <div className="relative mt-2"><input className="tp-input w-full" onChange={(event) => setCustomerQuery(event.target.value)} placeholder="Buscar por nome, telefone, CPF ou RG" value={customerQuery} />{customers.length ? <div className="absolute z-20 mt-1 w-full overflow-hidden rounded-control border border-tec-border/25 bg-tec-panel shadow-xl">{customers.map((item) => <button className="block w-full border-b border-tec-border/15 px-3 py-2.5 text-left text-sm transition last:border-b-0 hover:bg-tec-orange/10" key={item.name} onClick={() => { setCustomer(item); setCustomers([]); }} type="button"><span className="block font-bold text-white">{item.customer_name || item.name}</span><span className="text-xs text-tec-muted">{item.mobile_no || item.custom_whatsapp || item.name}</span></button>)}</div> : null}</div>}
			</section>
			<div className="grid gap-4 sm:grid-cols-2">
				<label className="text-sm font-bold text-white">Tipo<select className="tp-input mt-2 w-full" onChange={(event) => setDeviceType(event.target.value as "iPhone" | "Android")} value={deviceType}><option value="iPhone">iPhone</option><option value="Android">Android</option></select></label>
				<label className="text-sm font-bold text-white">Estado físico<select className="tp-input mt-2 w-full" onChange={(event) => setPhysicalState(event.target.value as "A" | "B" | "C" | "Sucata")} value={physicalState}><option value="A">A</option><option value="B">B</option><option value="C">C</option><option value="Sucata">Sucata</option></select></label>
				<label className="text-sm font-bold text-white">Modelo<input className="tp-input mt-2 w-full" onChange={(event) => setModel(event.target.value)} placeholder="Ex.: iPhone 13 128GB" value={model} /></label>
				<label className="text-sm font-bold text-white">IMEI / Serial<input className="tp-input mt-2 w-full" onChange={(event) => setImei(event.target.value)} placeholder="Identificação do aparelho" value={imei} /></label>
				<label className="text-sm font-bold text-white">Destino<select className="tp-input mt-2 w-full" onChange={(event) => setDestination(event.target.value as "Venda" | "Peças" | "Descarte")} value={destination}><option value="Venda">Venda</option><option value="Peças">Peças</option><option value="Descarte">Descarte</option></select></label>
				<label className="text-sm font-bold text-white">Valor avaliado<input className="tp-input mt-2 w-full" inputMode="decimal" onChange={(event) => setSuggestedValue(event.target.value)} placeholder="R$ 0,00" value={suggestedValue} /></label>
				<label className="text-sm font-bold text-white">Teto da tabela <span className="font-medium text-tec-muted">(opcional)</span><input className="tp-input mt-2 w-full" inputMode="decimal" onChange={(event) => setTableMax(event.target.value)} placeholder="R$ 0,00" value={tableMax} /></label>
				<label className="text-sm font-bold text-white">Defeitos <span className="font-medium text-tec-muted">(opcional)</span><input className="tp-input mt-2 w-full" onChange={(event) => setDefects(event.target.value)} placeholder="Resumo do estado técnico" value={defects} /></label>
			</div>
			<div className="flex justify-end gap-2"><Button onClick={onClose} variant="ghost">Cancelar</Button><Button disabled={saving} type="submit">{saving ? "Criando..." : "Criar avaliação"}</Button></div>
		</form>
	</Modal>;
}

function TradeInOperationModal({
	evaluation,
	onClose,
	onCompleted,
	onToast,
	open,
}: {
	evaluation: TradeEvaluationSummary | null;
	onClose: () => void;
	onCompleted: (evaluation: TradeEvaluationSummary) => void;
	onToast: (message: string, tone?: ToastState["tone"]) => void;
	open: boolean;
}) {
	const [query, setQuery] = useState("");
	const [devices, setDevices] = useState<TradeOutputDevice[]>([]);
	const [device, setDevice] = useState<TradeOutputDevice | null>(null);
	const [difference, setDifference] = useState("");
	const [busy, setBusy] = useState(false);

	useEffect(() => { if (open) { setQuery(""); setDevices([]); setDevice(null); setDifference(""); } }, [open]);
	useEffect(() => {
		if (!open || device) return;
		const timer = window.setTimeout(() => { void balcao.listTradeInOutputDevices(query, 12).then((response) => setDevices(response.items)).catch(() => setDevices([])); }, 180);
		return () => window.clearTimeout(timer);
	}, [device, open, query]);

	const confirm = async () => {
		if (!evaluation || !device) { onToast("Selecione o aparelho que sairá da loja.", "error"); return; }
		const value = Number(difference.replace(",", ".") || "0");
		if (!Number.isFinite(value) || value < 0) { onToast("A diferença não pode ser negativa.", "error"); return; }
		setBusy(true);
		try {
			const response = await balcao.confirmTradeInOperation({ evaluation: evaluation.name, device_out: device.name, difference: value });
			onCompleted(response.evaluation);
			onToast(`Troca ${response.operation.name} concluída com segurança.`, "success");
		} catch (error) {
			onToast(error instanceof Error ? error.message : "Não foi possível confirmar a troca.", "error");
		} finally { setBusy(false); }
	};

	return <Modal className="max-w-2xl" onClose={onClose} open={open} title="Confirmar operação de troca">
		{evaluation ? <div className="space-y-5"><p className="text-sm leading-6 text-tec-subtle">O motor registra em uma única operação a entrada do usado, a saída do aparelho escolhido e a diferença. Se qualquer perna falhar, nada é gravado.</p><DetailPill label="Aparelho recebido" value={`${evaluation.evaluated_device_desc || evaluation.model || evaluation.name} · ${formatCurrency(evaluation.approved_value)}`} />
			<label className="block text-sm font-bold text-white">Aparelho que sai do Comercial<input className="tp-input mt-2 w-full" onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por serial, IMEI ou item" value={query} /></label>
			<div className="max-h-52 space-y-2 overflow-y-auto">{devices.map((item) => <button className={cx("flex w-full items-center justify-between gap-3 rounded-control border px-3 py-3 text-left transition", device?.name === item.name ? "border-tec-orange bg-tec-orange/10" : "border-tec-border/20 bg-tec-field/45 hover:border-tec-orange/45")} key={item.name} onClick={() => setDevice(item)} type="button"><span className="min-w-0"><span className="block truncate text-sm font-bold text-white">{item.item_name}</span><span className="block truncate text-xs text-tec-muted">{item.serial_no || item.item_code}</span></span><CheckCircle2 className={device?.name === item.name ? "text-tec-orange" : "text-tec-muted"} size={18} /></button>)}</div>
			<label className="block text-sm font-bold text-white">Diferença recebida do cliente<input className="tp-input mt-2 w-full" inputMode="decimal" onChange={(event) => setDifference(event.target.value)} placeholder="R$ 0,00" value={difference} /></label>
			<div className="flex justify-end gap-2"><Button onClick={onClose} variant="ghost">Cancelar</Button><Button disabled={busy || !device} icon={<ArrowRightLeft size={16} />} onClick={() => void confirm()}>{busy ? "Confirmando..." : "Confirmar troca"}</Button></div>
		</div> : null}
	</Modal>;
}

function StockLookup({
	canEditRepairParts,
	canManageVariantProducts,
  canReceiveStock,
  initialBarcode,
  onInitialBarcodeHandled,
  onToast,
  scope,
}: {
	canEditRepairParts: boolean;
	canManageVariantProducts: boolean;
  canReceiveStock: boolean;
  initialBarcode: PendingRetailBarcode | null;
  onInitialBarcodeHandled: () => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  scope: "parts-stock" | "repair-parts" | "commercial-products" | "used-devices";
}) {
  const isCommercialCatalog = scope === "commercial-products" || scope === "parts-stock";
  const scopeCopy = {
    "parts-stock": {
      title: "Produtos",
      description: "Estoque comercial disponível para venda no balcão.",
      searchPlaceholder: "Buscar produto, código ou depósito comercial",
    },
    "repair-parts": {
      title: "Peças de reparo",
      description: "Disponibilidade exclusiva do depósito de Reparo.",
      searchPlaceholder: "Buscar peça, código ou depósito de reparo",
    },
    "commercial-products": {
      title: "Produtos",
      description: "Estoque comercial disponível para venda no balcão.",
      searchPlaceholder: "Buscar produto, código ou depósito comercial",
    },
    "used-devices": {
      title: "Aparelhos usados",
      description: "Estoque de trade-in rastreado por IMEI/serial.",
      searchPlaceholder: "Buscar aparelho usado, IMEI ou depósito comercial",
    },
  }[scope];
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<StockItemSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [busyItem, setBusyItem] = useState<string | null>(null);
  const [registrationOpen, setRegistrationOpen] = useState(false);
	const [variantRegistrationOpen, setVariantRegistrationOpen] = useState(false);
  const [registrationBarcode, setRegistrationBarcode] = useState<string | null>(null);
	const [listingEntries, setListingEntries] = useState<CommercialCatalogItem[]>([]);
	const [listingItem, setListingItem] = useState<CommercialCatalogItem | null>(null);
	const [registryEditor, setRegistryEditor] = useState<{ kind: "repair_part" | "product"; name?: string } | null>(null);
	const [categoryFilter, setCategoryFilter] = useState("");
	const [categoryOptions, setCategoryOptions] = useState<Array<{ name: string; label: string }>>([]);

  const [statItems, setStatItems] = useState<Array<{ key: string; label: string; value: number }>>([]);
  const [presentation, setPresentation] = useState<ListPresentation>(() => getStoredListPresentation(`tecponto.stock.${scope}.presentation`));
  const [quickFilter, setQuickFilter] = useState("available");
  const [advancedFilter, setAdvancedFilter] = useState("all");
	const [transferItem, setTransferItem] = useState<StockItemSummary | null>(null);
	const [transferQty, setTransferQty] = useState("1");
	const [transferBusy, setTransferBusy] = useState(false);
	const [transferApproval, setTransferApproval] = useState<{ name: string; itemName: string } | null>(null);
  const canTransfer = scope === "repair-parts" || scope === "commercial-products";
  const transferDirection = scope === "repair-parts"
    ? { source: "Reparo", target: "Comercial" }
    : { source: "Comercial", target: "Reparo" };

  const search = useCallback(async (nextQuery: string) => {
    setStatus("loading");
    try {
      const response = await balcao.listStockItems(nextQuery, 12, scope, categoryFilter);
      setRows(response.items);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [categoryFilter, scope]);

  useEffect(() => {
    void search("");
    void balcao.getListStatBar(`stock:${scope}`).then((result) => setStatItems(result.items)).catch(() => setStatItems([]));
		if (scope === "commercial-products" || scope === "used-devices") {
			void catalogListings.list(scope === "used-devices" ? "unique" : "shelf").then((result) => setListingEntries(result.items)).catch(() => setListingEntries([]));
		} else {
			setListingEntries([]);
		}
		void productCategories.list().then((result) => {
			const flatten = (nodes: ProductCategoryNode[], depth = 0): Array<{ name: string; label: string }> => nodes.flatMap((node) => [
				{ name: node.name, label: `${"— ".repeat(depth)}${node.name}` },
				...flatten(node.children, depth + 1),
			]);
			setCategoryOptions(flatten(result.items));
		}).catch(() => setCategoryOptions([]));
  }, [search]);

  useEffect(() => {
    window.localStorage.setItem(`tecponto.stock.${scope}.presentation`, presentation);
  }, [presentation, scope]);

  const filteredRows = useMemo(() => rows.filter((row) => {
    if (quickFilter === "available") return row.available_qty > 0;
    if (quickFilter === "low") return row.available_qty > 0 && row.available_qty <= 2;
    if (quickFilter === "empty") return row.available_qty <= 0;
		if (advancedFilter === "with_barcode") return Boolean(row.barcode);
		if (advancedFilter === "without_barcode") return !row.barcode && !row.has_serial_no;
		if (advancedFilter === "serialized") return row.has_serial_no;
    return true;
  }), [advancedFilter, quickFilter, rows]);

  useEffect(() => {
    if (!initialBarcode || !isCommercialCatalog) return;
    setRegistrationBarcode(initialBarcode.code);
    setRegistrationOpen(true);
    onInitialBarcodeHandled();
  }, [initialBarcode, isCommercialCatalog, onInitialBarcodeHandled]);

  const generateBarcode = useCallback(async (row: StockItemSummary) => {
    setBusyItem(row.item_code);
    try {
      const response = await pos.generateBarcode(row.item_code);
      setRows((current) => current.map((item) => item.item_code === row.item_code ? { ...item, barcode: response.barcode } : item));
      onToast(response.created ? `Código ${response.barcode} gerado e salvo no Item.` : "O item já possuía código; nenhum dado foi alterado.");
      window.open(response.label.url, "_blank", "noopener,noreferrer");
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível gerar a etiqueta.", "error");
    } finally {
      setBusyItem(null);
    }
  }, [onToast]);

  const sendTransfer = async () => {
    if (!transferItem) return;
    const qty = Number(transferQty.replace(",", "."));
    if (!Number.isFinite(qty) || qty <= 0) {
      onToast("Informe uma quantidade maior que zero.", "error");
      return;
    }
    setTransferBusy(true);
    try {
      const prepared = await balcao.createStockTransfer(
        transferItem.item_code,
        qty,
		transferItem.warehouse ?? "",
		"",
      );
      try {
        await balcao.submitStockTransfer(prepared.item.name);
        onToast("Transferência concluída.");
        setTransferItem(null);
        void search("");
      } catch (error) {
        const message = error instanceof Error ? error.message : "A transferência exige aprovação.";
        if (message.includes("exige o Gestor")) {
          setTransferApproval({ name: prepared.item.name, itemName: transferItem.item_name ?? transferItem.item_code });
          setTransferItem(null);
        } else {
          onToast(message, "error");
        }
      }
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível preparar a transferência.", "error");
    } finally {
      setTransferBusy(false);
    }
  };

  const columns = useMemo<Array<TableColumn<StockItemSummary>>>(
    () => [
      { key: "item_code", label: "Item", render: (row) => <span className="font-semibold text-white">{row.item_code}</span> },
      { key: "item_name", label: "Descrição", render: (row) => row.item_name ?? row.item_code },
      { key: "item_group", label: "Grupo", render: (row) => row.item_group ?? "Sem grupo" },
      {
        key: "barcode",
        label: "Código de barras",
        render: (row) => row.barcode ? <span className="font-mono text-xs text-tec-subtle">{row.barcode}</span> : <span className="text-tec-amber">Sem código</span>,
      },
      { key: "warehouse", label: "Estoque", render: (row) => row.warehouse ?? "Sem depósito" },
      { key: "available_qty", label: "Disponível", render: (row) => row.available_qty.toLocaleString("pt-BR") },
      {
        key: "barcode_action",
        label: "Etiqueta",
        render: (row) => !isCommercialCatalog ? (
          <span className="text-xs text-tec-muted">{scope === "used-devices" || row.has_serial_no ? "Controlado por IMEI" : "Estoque de reparo"}</span>
        ) : !row.is_commercial_item ? (
          <span className="text-xs text-tec-muted">Não comercial</span>
        ) : row.has_serial_no ? (
          <span className="text-xs text-tec-muted">Controlado por IMEI</span>
        ) : row.barcode ? (
          <Button
            icon={<Printer size={15} />}
            onClick={() => window.open(pos.barcodeLabelUrl(row.item_code), "_blank", "noopener,noreferrer")}
            title="Imprimir etiqueta sem alterar o código existente"
          >
            Imprimir
          </Button>
        ) : (
          <Button
            disabled={busyItem === row.item_code}
            icon={<Barcode size={16} />}
            onClick={() => void generateBarcode(row)}
            variant="primary"
          >
            {busyItem === row.item_code ? "Gerando..." : "Gerar etiqueta"}
          </Button>
        ),
      },
		...(scope === "commercial-products" || scope === "used-devices" ? [{
			key: "listing",
			label: "Catálogo",
			render: (row: StockItemSummary) => {
				const listing = listingEntries.find((entry) => entry.item_code === row.item_code);
				if (!listing) return <span className="text-xs text-tec-muted">Sem dados de anúncio</span>;
				return <div className="flex flex-wrap items-center gap-2"><span className="text-xs text-tec-subtle">{listing.catalog_kind === "unique" ? `Único • IMEI ••••${listing.serial_suffix ?? "----"}` : "Prateleira • variação"}</span>{canManageVariantProducts ? <Button onClick={() => setListingItem(listing)}>Anúncio</Button> : null}</div>;
			},
		}] : []),
		...(canTransfer ? [{
			key: "transfer",
			label: "Transferir",
			render: (row: StockItemSummary) => (
				<Button icon={<ArrowRightLeft size={15} />} onClick={() => { setTransferItem(row); setTransferQty("1"); }}>
					Transferir
				</Button>
			),
		}] : []),
		...((scope === "repair-parts" && canEditRepairParts) || (scope === "commercial-products" && canManageVariantProducts) ? [{
			key: "edit",
			label: "Cadastro",
			render: (row: StockItemSummary) => <Button icon={<Edit3 size={15} />} onClick={() => setRegistryEditor({ kind: scope === "repair-parts" ? "repair_part" : "product", name: row.item_code })}>Editar</Button>,
		}] : []),
	],
	[busyItem, canEditRepairParts, canManageVariantProducts, canTransfer, generateBarcode, isCommercialCatalog, listingEntries, scope],
  );

  return (
    <div className="space-y-4">
      {isCommercialCatalog ? (
        <div className="flex flex-col gap-3 rounded-card bg-tec-field/35 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Cadastro e entrada por código</h2>
            <p className="mt-1 text-sm text-tec-subtle">Escaneie a embalagem; produto conhecido não cria cadastro duplicado.</p>
          </div>
		  <div className="flex flex-wrap gap-2">
			{canManageVariantProducts ? <Button icon={<Boxes size={16} />} onClick={() => setVariantRegistrationOpen(true)}>Produto com variações</Button> : null}
			{canManageVariantProducts ? <Button icon={<Plus size={16} />} onClick={() => {
			  setRegistrationBarcode(null);
			  setRegistrationOpen(true);
			}} variant="primary">Cadastrar produto</Button> : null}
		  </div>
        </div>
      ) : null}
		{scope === "commercial-products" || scope === "used-devices" ? <div className="rounded-control border border-tec-border/15 bg-tec-field/35 px-4 py-3 text-sm text-tec-subtle"><strong className="text-white">{scope === "used-devices" ? "Itens únicos do trade-in" : "Prateleira com variações"}</strong><span className="ml-2">{scope === "used-devices" ? "Cada aparelho usa o Item serializado já criado no trade-in; estoque unitário no Comercial." : "Cada linha é uma variação nativa, com SKU, GTIN e estoque próprios."}</span></div> : null}
		{scope === "repair-parts" && canEditRepairParts ? <div className="flex flex-wrap items-center justify-between gap-3 rounded-card bg-tec-field/35 p-4"><div><h2 className="text-lg font-bold text-white">Cadastro de peças</h2><p className="mt-1 text-sm text-tec-subtle">Modelo e compatibilidade ficam no cadastro; custo não é exposto nesta tela.</p></div><Button icon={<Plus size={16} />} onClick={() => setRegistryEditor({ kind: "repair_part" })} variant="primary">Cadastrar peça</Button></div> : null}
      <LookupCard
        columns={columns}
        emptyLabel={status === "error" ? "Falha ao consultar estoque." : "Nenhum item encontrado."}
		getRowProps={(item) => ({
			"data-tp-barcode": item.barcode ?? "",
			"data-tp-context": "product",
			"data-tp-label": item.item_name ?? item.item_code,
			"data-tp-name": item.item_code,
		})}
		renderCardAction={((scope === "repair-parts" && canEditRepairParts) || (scope === "commercial-products" && canManageVariantProducts)) ? (item) => <button aria-label={`Editar ${item.item_name ?? item.item_code}`} className="grid h-8 w-8 place-items-center rounded-control border border-tec-border/20 bg-tec-panel text-tec-muted transition hover:border-tec-orange/50 hover:text-white" onClick={(event) => { event.stopPropagation(); setRegistryEditor({ kind: scope === "repair-parts" ? "repair_part" : "product", name: item.item_code }); }} title="Editar cadastro" type="button"><Edit3 size={15} /></button> : undefined}
        onSearch={(event) => {
          event.preventDefault();
          void search(query);
        }}
        placeholder={scopeCopy.searchPlaceholder}
        query={query}
        rows={filteredRows}
        setQuery={setQuery}
        statBar={<StatBar items={statItems.map((item) => ({ ...item, ...getStatBarVisual("stock", item.key) }))} />}
        status={status}
        tableMinWidthClassName="min-w-[940px]"
        title={scopeCopy.title}
        activeQuickFilter={quickFilter}
        advancedFilters={<div className="grid gap-3 sm:grid-cols-2"><label className="block text-xs font-bold text-tec-subtle">Controle do item<select className="tp-input mt-1 w-full" onChange={(event) => setAdvancedFilter(event.target.value)} value={advancedFilter}><option value="all">Todos os itens</option><option value="with_barcode">Com código de barras</option><option value="without_barcode">Sem código de barras</option><option value="serialized">Controlados por IMEI/serial</option></select></label><label className="block text-xs font-bold text-tec-subtle">Categoria<select className="tp-input mt-1 w-full" onChange={(event) => setCategoryFilter(event.target.value)} value={categoryFilter}><option value="">Todas as categorias</option>{categoryOptions.map((category) => <option key={category.name} value={category.name}>{category.label}</option>)}</select></label></div>}
        onClear={() => { setQuickFilter("available"); setAdvancedFilter("all"); setCategoryFilter(""); }}
        onPresentationChange={setPresentation}
        onQuickFilterChange={setQuickFilter}
        presentation={presentation}
        quickFilters={[{ key: "available", label: "Disponíveis" }, { key: "low", label: "Baixo estoque" }, { key: "empty", label: "Sem estoque" }, { key: "all", label: "Todos" }]}
      />
      {isCommercialCatalog ? (
        <RetailProductModal
          canReceiveStock={canReceiveStock}
          initialBarcode={registrationBarcode}
          onClose={() => setRegistrationOpen(false)}
          onCreated={(message) => {
            onToast(message);
            void search("");
          }}
          open={registrationOpen}
        />
      ) : null}
		{isCommercialCatalog && canManageVariantProducts ? <VariantProductModal onClose={() => setVariantRegistrationOpen(false)} onCreated={(message) => { onToast(message); void search(""); }} open={variantRegistrationOpen} /> : null}
		<ListingMetadataModal item={listingItem} onClose={() => setListingItem(null)} onSaved={(item) => { setListingEntries((current) => current.map((entry) => entry.item_code === item.item_code ? item : entry)); onToast("Dados de anúncio atualizados."); }} open={Boolean(listingItem)} />
		<RegistryEditorModal
			kind={registryEditor?.kind ?? "repair_part"}
			name={registryEditor?.name}
			onClose={() => setRegistryEditor(null)}
			onSaved={(updated) => {
				if (!("item_code" in updated)) return;
				const item = updated;
				setRows((current) => current.map((row) => row.item_code === item.item_code ? { ...row, item_name: item.item_name, item_group: item.item_group, barcode: item.barcode } : row));
				void search("");
				onToast(registryEditor?.name ? "Cadastro do item atualizado." : "Peça cadastrada.");
			}}
			open={Boolean(registryEditor)}
		/>
		<Modal
			onClose={() => setTransferItem(null)}
			open={Boolean(transferItem)}
			title="Transferir entre estoques"
		>
			{transferItem ? (
				<div className="space-y-4">
					<p className="text-sm text-tec-subtle">{transferItem.item_name ?? transferItem.item_code}</p>
					<div className="rounded-card border border-tec-border/15 bg-tec-field/55 p-3 text-sm font-semibold text-tec-text">
						{transferDirection.source} para {transferDirection.target}. A movimentação só será efetivada após a validação do motor.
					</div>
					<label className="block text-sm font-bold text-tec-text">
						Quantidade
						<input className="tp-input mt-2 w-full" inputMode="decimal" min="0.001" onChange={(event) => setTransferQty(event.target.value)} type="number" value={transferQty} />
					</label>
					<div className="flex justify-end gap-2">
						<Button onClick={() => setTransferItem(null)} variant="secondary">Cancelar</Button>
						<Button disabled={transferBusy} icon={<ArrowRightLeft size={16} />} onClick={() => void sendTransfer()} variant="primary">{transferBusy ? "Validando..." : "Transferir"}</Button>
					</div>
				</div>
			) : null}

		</Modal>
		<ApprovalRequestModal
			onClose={() => setTransferApproval(null)}
			onCreated={() => setTransferApproval(null)}
			onToast={onToast}
			open={Boolean(transferApproval)}
			payload={{}}
			referenceName={transferApproval?.name ?? ""}
			requestType="stock_transfer"
			title={`A transferência de ${transferApproval?.itemName ?? "estoque"} entre Reparo e Comercial exige o Gestor. Deseja solicitar aprovação?`}
		/>
    </div>
  );
}

function SalesLookup({ onNavigate }: { onNavigate: (target: NavigationTarget) => void }) {
  const [statItems, setStatItems] = useState<Array<{ key: string; label: string; value: number; amount?: number }>>([]);
  const [query, setQuery] = useState("");
  const [period, setPeriod] = useState("today");
  const [rows, setRows] = useState<SaleSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [presentation, setPresentation] = useState<ListPresentation>(() => getStoredListPresentation("tecponto.sales.presentation"));
  const [advancedFilter, setAdvancedFilter] = useState("all");
  const [postSaleInvoice, setPostSaleInvoice] = useState<string | null>(null);
  useEffect(() => {
    void balcao.getListStatBar("sales").then((result) => setStatItems(result.items)).catch(() => setStatItems([]));
  }, []);

  const load = useCallback(async (nextQuery = query, nextPeriod = period) => {
    setStatus("loading");
    try {
      const response = await balcao.listSales(nextQuery, 50, nextPeriod);
      setRows(response.items);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [period, query]);

  useEffect(() => { void load("", period); }, [load, period]);
  useEffect(() => { window.localStorage.setItem("tecponto.sales.presentation", presentation); }, [presentation]);
	const filteredRows = useMemo(() => rows.filter((row) => {
		if (advancedFilter === "under_100") return row.grand_total < 100;
		if (advancedFilter === "100_to_500") return row.grand_total >= 100 && row.grand_total <= 500;
		if (advancedFilter === "above_500") return row.grand_total > 500;
		return true;
	}), [advancedFilter, rows]);

  const columns = useMemo<Array<TableColumn<SaleSummary>>>(() => [
    { key: "name", label: "Venda", render: (row) => <span className="font-semibold text-white">{row.name}</span> },
    { key: "customer", label: "Cliente", render: (row) => row.customer || "Consumidor final" },
    { key: "posting_date", label: "Data", render: (row) => formatDate(row.posting_date) },
    { key: "grand_total", label: "Total", render: (row) => row.grand_total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) },
    { key: "status", label: "Status", render: (row) => <BadgeStatus status={row.status || "Concluída"} /> },
  ], []);

  return (
    <div className="space-y-4">
      <StatBar items={statItems.map((item) => ({ ...item, ...getStatBarVisual("sales", item.key), displayValue: item.key === "amount" ? item.value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : undefined }))} />
      <LookupCard
        activeQuickFilter={period}
        advancedFilters={<label className="block text-xs font-bold text-tec-subtle">Faixa do total da venda<select className="tp-input mt-1 w-full" onChange={(event) => setAdvancedFilter(event.target.value)} value={advancedFilter}><option value="all">Todas as faixas</option><option value="under_100">Abaixo de R$ 100</option><option value="100_to_500">De R$ 100 a R$ 500</option><option value="above_500">Acima de R$ 500</option></select></label>}
        onClear={() => { setPeriod("today"); setAdvancedFilter("all"); void load(query, "today"); }}
        columns={columns}
        emptyLabel={status === "error" ? "Falha ao consultar vendas." : "Nenhuma venda neste recorte."}
        headerAction={<Button onClick={() => onNavigate("pos")} variant="primary">Abrir PDV</Button>}
        onPresentationChange={setPresentation}
		onRowClick={(row) => setPostSaleInvoice(row.name)}
        onSecondaryFilterChange={(nextPeriod) => { setPeriod(nextPeriod); void load(query, nextPeriod); }}
        onSearch={(event) => { event.preventDefault(); void load(); }}
        placeholder="Buscar número da venda ou cliente"
        presentation={presentation}
        query={query}
        rows={filteredRows}
        secondaryActiveFilter={period}
        secondaryFilters={[{ key: "today", label: "Hoje" }, { key: "7d", label: "Últimos 7 dias" }, { key: "all", label: "Todas" }]}
        setQuery={setQuery}
        status={status}
        title="Histórico de vendas"
      />
		<SalesReturnModal invoiceName={postSaleInvoice} onClose={() => setPostSaleInvoice(null)} />
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(300px,0.5fr)]">
      <Card className="overflow-hidden p-0">
        <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 gap-4">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-[18px] bg-tec-orange text-tec-ink shadow-glow">
              <ShoppingCart size={25} />
            </span>
            <div className="min-w-0">
              <h2 className="mt-1 text-2xl font-bold text-white">Vendas e acessórios</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-tec-subtle">
                Consulte o movimento do balcão e abra o PDV para iniciar uma nova venda.
              </p>
            </div>
          </div>
          <Button className="shrink-0" onClick={() => onNavigate("pos")} variant="primary">
            Abrir PDV
          </Button>
        </div>
        <div className="grid border-t border-tec-border/15 sm:grid-cols-3">
          <SalesRouteCard
            detail="Nova venda com estoque Comercial"
            icon={<CreditCard size={22} />}
			label={`PDV ${commercialName()}`}
            onClick={() => onNavigate("pos")}
          />
          <SalesRouteCard
            detail="Disponibilidade e depósito"
            icon={<Package size={22} />}
            label="Consultar item"
            onClick={() => onNavigate("parts-stock")}
          />
          <SalesRouteCard
            detail="Nome, telefone ou IMEI"
            icon={<SearchIcon size={22} />}
            label="Buscar cliente"
            onClick={() => onNavigate("customers")}
          />
        </div>
      </Card>
      <Card className="p-5">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-[15px] bg-tec-orange/15 text-tec-orange">
            <BadgeInfo size={21} />
          </span>
          <div>
            <h3 className="text-lg font-bold text-white">Fluxo recomendado</h3>
            <p className="text-sm text-tec-subtle">Use o POS para vender e esta tela para consultar antes de abrir a venda.</p>
          </div>
        </div>
        <div className="mt-5 space-y-3">
          <SalesChecklistItem icon={<Package size={16} />} label="Confirmar estoque Comercial" />
          <SalesChecklistItem icon={<UserRound size={16} />} label="Selecionar ou cadastrar cliente" />
          <SalesChecklistItem icon={<CreditCard size={16} />} label="Finalizar pagamento no PDV" />
        </div>
      </Card>
    </div></div>
  );
}

function SalesReturnModal({ invoiceName, onClose }: { invoiceName: string | null; onClose: () => void }) {
	const returnRequestKeyRef = useRef<string | null>(null);
	const [detail, setDetail] = useState<import("./api").SalePostSaleDetail | null>(null);
	const [quantities, setQuantities] = useState<Record<string, number>>({});
	const [state, setState] = useState<"loading" | "ready" | "saving" | "done" | "error">("loading");
	const [message, setMessage] = useState("");
	const [exchange, setExchange] = useState(false);
	const [replacement, setReplacement] = useState<{ item_code: string; item_name: string | null; standard_rate: number } | null>(null);
	const [replacementQuery, setReplacementQuery] = useState("");
	const [replacementResults, setReplacementResults] = useState<Array<{ item_code: string; item_name: string | null; standard_rate: number }>>([]);
	const [paymentMode, setPaymentMode] = useState("Pix");
	useEffect(() => {
		if (!invoiceName) return;
		setState("loading"); setDetail(null); setQuantities({}); setMessage(""); returnRequestKeyRef.current = null;
		void balcao.getSalePostSaleDetail(invoiceName).then((result) => {
			setDetail(result);
			setQuantities(Object.fromEntries(result.items.filter((item) => item.available_qty > 0).map((item) => [item.item_code, 0])));
			setState("ready");
		}).catch((error) => { setState("error"); setMessage(error instanceof Error ? error.message : "Não foi possível carregar a venda."); });
	}, [invoiceName]);
	useEffect(() => {
		if (!exchange || replacement) return;
		const timer = window.setTimeout(() => { void pos.searchItems({ query: replacementQuery, limit: 8 }).then((response) => setReplacementResults(response.items)).catch(() => setReplacementResults([])); }, 220);
		return () => window.clearTimeout(timer);
	}, [exchange, replacement, replacementQuery]);
	const submit = async () => {
		if (!detail) return;
		const items = detail.items.filter((item) => (quantities[item.item_code] || 0) > 0).map((item) => ({ item_code: item.item_code, qty: quantities[item.item_code] }));
		if (!items.length) { setMessage("Selecione ao menos um item para devolver."); return; }
		setState("saving");
		try {
			const requestKey = returnRequestKeyRef.current ?? `tp-return-${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`}`;
			returnRequestKeyRef.current = requestKey;
			if (exchange) {
				if (!replacement) { setMessage("Selecione o produto que o cliente está levando."); setState("ready"); return; }
				const result = await balcao.exchangeSalesProduct({ invoice: detail.name, items, idempotency_key: requestKey, new_sale: { customer: detail.customer || "CONSUMIDOR FINAL", items: [{ item_code: replacement.item_code, qty: 1 }], discount_amount: 0, payments: [{ mode_of_payment: paymentMode, amount: replacement.standard_rate, installments: 1 }], idempotency_key: `${requestKey}:sale` } });
				setMessage(`Troca registrada: devolução ${result.return_invoice} e nova venda concluída.`);
			} else {
				const result = await balcao.createSalesReturn({ invoice: detail.name, items, idempotency_key: requestKey });
				setMessage(`Devolução ${result.return_invoice} registrada. O ERPNext ajustou estoque e recebíveis pela forma original.`);
			}
			setState("done");
		} catch (error) { setState("error"); setMessage(error instanceof Error ? error.message : "Não foi possível registrar a devolução."); }
	};
	return <Modal className="max-w-3xl" onClose={onClose} open={Boolean(invoiceName)} title="Devolução de venda">
		{state === "loading" ? <p className="p-4 text-sm text-tec-muted">Carregando itens da venda...</p> : null}
		{detail ? <div className="space-y-4"><div className="rounded-card border border-tec-border/20 bg-tec-field/45 p-4"><p className="font-bold text-white">{detail.name} · {detail.customer || "Consumidor final"}</p><p className="mt-1 text-sm text-tec-muted">Pagamento original: {detail.payments.map((payment) => payment.mode_of_payment).join(", ") || "A definir"}. O estorno segue o fluxo nativo da nota de retorno.</p></div>
			<div className="space-y-2">{detail.items.map((item) => <div className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-tec-border/20 bg-tec-panel px-3 py-3" key={item.item_code}><div><p className="text-sm font-bold text-white">{item.item_name}</p><p className="text-xs text-tec-muted">Disponível para devolver: {item.available_qty} · {formatCurrency(item.unit_price)}</p></div><input className="tp-input w-24" disabled={state === "saving" || state === "done" || item.available_qty <= 0} inputMode="decimal" max={item.available_qty} min={0} onChange={(event) => setQuantities((current) => ({ ...current, [item.item_code]: Math.max(0, Math.min(item.available_qty, Number(event.target.value) || 0)) }))} type="number" value={quantities[item.item_code] || 0} /></div>)}</div>
			<label className="flex items-center gap-2 text-sm font-semibold text-white"><input checked={exchange} onChange={(event) => setExchange(event.target.checked)} type="checkbox" /> Trocar por outro produto</label>
			{exchange ? <div className="rounded-card border border-tec-border/20 bg-tec-field/35 p-3"><label className="text-sm font-bold text-white">Produto substituto<input className="tp-input mt-2 w-full" onChange={(event) => { setReplacementQuery(event.target.value); setReplacement(null); }} placeholder="Buscar item comercial" value={replacementQuery} /></label>{replacementResults.map((item) => <button className="mt-2 block w-full rounded-control border border-tec-border/20 px-3 py-2 text-left hover:border-tec-orange" key={item.item_code} onClick={() => { setReplacement(item); setReplacementResults([]); setReplacementQuery(item.item_name || item.item_code); }} type="button">{item.item_name} · {formatCurrency(item.standard_rate)}</button>)}{replacement ? <label className="mt-3 block text-sm font-bold text-white">Pagamento da nova venda<select className="tp-input mt-2 w-full" onChange={(event) => setPaymentMode(event.target.value)} value={paymentMode}><option>Pix</option><option>Débito</option><option>Crédito à vista</option><option>Dinheiro</option></select></label> : null}</div> : null}
			{message ? <p className={cx("rounded-control px-3 py-2 text-sm", state === "done" ? "bg-tec-success/10 text-tec-success" : "bg-tec-danger/10 text-tec-danger")}>{message}</p> : null}
			<div className="flex justify-end gap-2"><Button onClick={onClose} variant="ghost">Fechar</Button><Button disabled={state === "saving" || state === "done"} onClick={() => void submit()} variant="primary">{state === "saving" ? "Registrando..." : "Confirmar devolução"}</Button></div></div> : null}
	</Modal>;
}

function SalesRouteCard({
  disabled = false,
  detail,
  icon,
  label,
  onClick,
}: {
  disabled?: boolean;
  detail: string;
  icon: ReactNode;
  label: string;
  onClick?: () => void;
}) {
  return (
    <button
      className={cx(
        "group flex min-h-28 items-center gap-4 border-t border-tec-border/15 p-5 text-left transition sm:border-l sm:border-t-0 first:sm:border-l-0",
        disabled ? "cursor-not-allowed opacity-60" : "hover:bg-tec-field/75",
      )}
      disabled={disabled}
      onClick={onClick}
      title={disabled ? "Indisponível" : label}
      type="button"
    >
      <span
        className={cx(
          "grid h-12 w-12 shrink-0 place-items-center rounded-[16px] bg-tec-field text-tec-orange transition",
          !disabled && "group-hover:bg-tec-orange group-hover:text-tec-ink",
        )}
      >
        {icon}
      </span>
      <span className="min-w-0">
        <span className="block text-base font-bold text-white">{label}</span>
        <span className="mt-1 block text-sm text-tec-subtle">{detail}</span>
      </span>
      {disabled ? null : (
        <ArrowRight className="ml-auto shrink-0 text-tec-muted transition group-hover:translate-x-1 group-hover:text-tec-orange" size={18} />
      )}
    </button>
  );
}

function SalesChecklistItem({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-[16px] border border-tec-border/15 bg-tec-field/55 px-3 py-3 text-sm font-semibold text-tec-text">
      <span className="grid h-8 w-8 place-items-center rounded-[12px] bg-tec-orange/15 text-tec-orange">{icon}</span>
      {label}
    </div>
  );
}

function LookupCard<T>({
  activeQuickFilter,
  advancedFilters,
  columns,
  renderCardAction,
  emptyLabel,
  headerAction,
	getRowProps,
	 onClear,
  onSearch,

	onQuickFilterChange,
	onSecondaryFilterChange,
	onPresentationChange,
	onSearchFocus,
	onSearchKeyDown,
  onRowClick,
  placeholder,
  presentation,
  quickFilters,
	secondaryActiveFilter,
	secondaryFilters,
  query,
  rows,
  searchSuggestions,
  statBar,
  setQuery,
  status,
  tableMinWidthClassName,
  title,
}: {
  activeQuickFilter?: string;
  advancedFilters?: ReactNode;
  columns: Array<TableColumn<T>>;
  renderCardAction?: (row: T) => ReactNode;
  emptyLabel: string;
  headerAction?: ReactNode;
	getRowProps?: (row: T) => Record<`data-${string}`, string | undefined>;
	 onClear?: () => void;
  onSearch: (event: FormEvent<HTMLFormElement>) => void;
	onQuickFilterChange?: (key: string) => void;
	onSecondaryFilterChange?: (key: string) => void;
	onPresentationChange?: (value: ListPresentation) => void;
	onSearchFocus?: () => void;
	onSearchKeyDown?: (event: ReactKeyboardEvent<HTMLInputElement>) => void;
  onRowClick?: (row: T) => void;
  placeholder: string;
  presentation?: ListPresentation;
  quickFilters?: QuickFilter[];
	secondaryActiveFilter?: string;
	secondaryFilters?: QuickFilter[];
  query: string;
  rows: T[];
  searchSuggestions?: ReactNode;
  statBar?: ReactNode;
  setQuery: (query: string) => void;
  status: "loading" | "ready" | "error";
  tableMinWidthClassName?: string;
  title: string;
}) {
  const [visibleCount, setVisibleCount] = useState(LIST_PAGE_SIZE);
  useEffect(() => setVisibleCount(LIST_PAGE_SIZE), [rows]);
  const displayedRows = rows.slice(0, visibleCount);
  const searchForm = <form className="flex flex-col gap-3 md:flex-row" onSubmit={onSearch}>
    <div className="relative flex-1">
      <SearchIcon className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-tec-muted" size={18} />
      <input
        className="h-11 w-full rounded-control border border-tec-border/25 bg-tec-field pl-11 pr-4 text-sm text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70"
        onChange={(event) => setQuery(event.target.value)}
		onFocus={onSearchFocus}
		onKeyDown={onSearchKeyDown}
        placeholder={placeholder}
        type="search"
        value={query}
      />
		{searchSuggestions}
    </div>
    <Button icon={<SearchIcon size={17} />} type="submit" variant="primary">Buscar</Button>
  </form>;

  return (
    <Card className="p-4">
      {statBar ? <div className="mb-4">{statBar}</div> : null}
      <div className="mb-4">
        {(quickFilters?.length || secondaryFilters?.length || advancedFilters) ? <LayeredFilters active={activeQuickFilter} filters={quickFilters ?? []} onClear={onClear} onSecondarySelect={onSecondaryFilterChange} onSelect={onQuickFilterChange ?? (() => undefined)} primary={searchForm} secondaryActive={secondaryActiveFilter} secondaryFilters={secondaryFilters}>{advancedFilters}</LayeredFilters> : searchForm}
      </div>
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold text-white">{title}</h2>
          <span className="rounded-full bg-tec-orange/20 px-2 py-1 text-xs font-bold text-tec-orange">
            {status === "loading" ? "..." : rows.length}
          </span>
        </div>
        <div className="flex items-center gap-2">{presentation && onPresentationChange ? <ListGridToggle onChange={onPresentationChange} value={presentation} /> : null}{headerAction}</div>
      </div>
      {presentation === "grid" ? <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{displayedRows.map((row, rowIndex) => <div {...getRowProps?.(row)} className="relative rounded-card border border-tec-border/15 bg-tec-field/45 p-4 text-left transition hover:border-tec-orange/45 hover:bg-tec-field" key={rowIndex} onClick={() => onRowClick?.(row)} onKeyDown={(event) => { if ((event.key === "Enter" || event.key === " ") && onRowClick) { event.preventDefault(); onRowClick(row); } }} role={onRowClick ? "button" : undefined} tabIndex={onRowClick ? 0 : undefined}>{renderCardAction ? <span className="absolute right-3 top-3">{renderCardAction(row)}</span> : null}{columns.slice(0, 4).map((column) => <div className="mt-2 first:mt-0" key={column.key}><span className="block text-[11px] font-bold uppercase text-tec-muted">{column.label}</span><span className="mt-0.5 block text-sm text-tec-text">{column.render(row)}</span></div>)}</div>)}</div> : <DataTable columns={columns} emptyLabel={status === "loading" ? "Carregando..." : emptyLabel} getRowProps={getRowProps} onRowClick={onRowClick} rows={displayedRows} tableMinWidthClassName={tableMinWidthClassName} />}
      <ProgressiveListFooter shown={displayedRows.length} total={rows.length} onShowMore={() => setVisibleCount((current) => current + LIST_PAGE_SIZE)} />
    </Card>
  );
}

function ProgressiveListFooter({ onShowMore, shown, total }: { onShowMore: () => void; shown: number; total: number }) {
  const remaining = total - shown;
  if (remaining <= 0) return null;
  return (
    <div className="mt-4 flex justify-center">
      <Button onClick={onShowMore} variant="ghost">Mostrar mais (+{Math.min(remaining, LIST_PAGE_SIZE)})</Button>
    </div>
  );
}

function ServiceOrderViewToggle({
  onChange,
  value,
}: {
  onChange: (value: ServiceOrdersViewMode) => void;
  value: ServiceOrdersViewMode;
}) {
  const options: Array<{ label: string; value: ServiceOrdersViewMode }> = [
    { label: "Lista", value: "list" },
    { label: "Grid", value: "grid" },
    { label: "Kanban", value: "kanban" },
  ];

  return (
    <div className="inline-grid grid-cols-3 gap-1 rounded-control border border-tec-border/15 bg-tec-field/70 p-1">
      {options.map((option) => (
        <button
          aria-pressed={value === option.value}
          className={`min-h-10 rounded-[12px] px-4 text-sm font-bold transition ${
            value === option.value
              ? "bg-tec-orange text-tec-ink shadow-glow"
              : "text-tec-subtle hover:bg-tec-panel-strong/75 hover:text-white"
          }`}
          key={option.value}
          onClick={() => onChange(option.value)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function getStoredServiceOrdersView(): ServiceOrdersViewMode {
  try {
    const stored = window.localStorage.getItem(SERVICE_ORDERS_VIEW_KEY);
    return stored === "kanban" || stored === "grid" || stored === "list" ? stored : "kanban";
  } catch {
    return "kanban";
  }
}

function RightRail({
  actions,
  metrics,
  onNavigate,
  onOpenNotifications,
  onStartCheckin,
}: {
  actions: ActionDefinition[];
  metrics: DashboardMetrics;
  onNavigate: (target: NavigationTarget) => void;
  onOpenNotifications: () => void;
  onStartCheckin: () => void;
}) {
  return (
    <aside className="space-y-4">
      <ActionPanel
        actions={actions}
        onNavigate={onNavigate}
        onStartCheckin={onStartCheckin}
        title="Ações rápidas"
      />
      <Card className="p-5">
        <h2 className="text-xl font-bold text-white">Próximas ações</h2>
        <div className="mt-4 space-y-3 text-sm">
          <AlertLine
            count={metrics.service_orders.awaiting_approval}
            onClick={() => onNavigate("service-orders")}
            tone="orange"
            title="Aprovações pendentes"
          />
          <AlertLine
            count={metrics.service_orders.waiting_part}
            onClick={() => onNavigate("parts-stock")}
            tone="amber"
            title="Peças aguardando chegada"
          />
          <IntegrationPendingLine />
        </div>
        <button
          className="mx-auto mt-5 flex items-center gap-2 text-sm font-bold text-tec-orange hover:text-tec-digital-orange"
          onClick={onOpenNotifications}
          type="button"
        >
          Ver todas as ações
          <ArrowRight size={16} />
        </button>
      </Card>
    </aside>
  );
}

function IntegrationPendingLine() {
  return (
    <div
      className="flex items-center justify-between gap-3 rounded-control px-1 py-1.5 text-left"
      title="A centralização de mensagens chega na Fase 5a."
    >
      <span className="flex min-w-0 items-center gap-3 text-tec-muted">
        <span className="h-2.5 w-2.5 rounded-full bg-tec-muted/65" />
        <span className="truncate">Mensagens do WhatsApp</span>
      </span>
      <span className="shrink-0 rounded-full bg-tec-field px-2 py-1 text-[10px] font-bold uppercase text-tec-muted">Fase 5a</span>
    </div>
  );
}

function TechnicianWorkloadPanel() {
  const [items, setItems] = useState<TechnicianWorkloadItem[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const load = useCallback(async () => {
    setStatus("loading");
    try {
      const response = await balcao.getTechnicianWorkload();
      setItems(response.items);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white">Carga por técnico</h2>
          <p className="mt-1 text-xs text-tec-muted">OS ativas da loja, ordenadas por urgência.</p>
        </div>
        <Button icon={<RefreshCw className={status === "loading" ? "animate-spin" : ""} size={15} />} onClick={() => void load()} variant="ghost">
          Atualizar
        </Button>
      </div>
      {status === "error" ? <p className="mt-4 text-sm text-tec-red">Não foi possível carregar a carga da equipe.</p> : null}
      {status !== "error" && !items.length && status !== "loading" ? <p className="mt-4 rounded-control border border-dashed border-tec-border/20 p-3 text-sm text-tec-muted">Nenhuma OS ativa atribuída a técnico.</p> : null}
      <ul className="mt-4 grid gap-2 md:grid-cols-2 2xl:grid-cols-3">
        {items.slice(0, 8).map((item) => (
          <li className="rounded-control border border-tec-border/15 bg-tec-field/55 p-3" key={item.technician}>
            <div className="flex items-start justify-between gap-3">
              <span className="min-w-0">
                <span className="block truncate text-sm font-bold text-white" title={item.technician_name}>{item.technician_name}</span>
                <span className="mt-1 block text-xs text-tec-muted">{item.active_orders} OS ativas · {item.in_diagnosis} em diagnóstico</span>
              </span>
              {item.overdue ? <span className="shrink-0 rounded-full bg-tec-red/15 px-2 py-1 text-xs font-bold text-tec-red">{item.overdue} atrasada{item.overdue > 1 ? "s" : ""}</span> : null}
            </div>
            {item.waiting_part ? <p className="mt-2 text-xs font-semibold text-tec-amber">{item.waiting_part} aguardando peça</p> : null}
          </li>
        ))}
      </ul>
      {items.length > 8 ? <p className="mt-3 text-center text-xs font-semibold text-tec-muted">Exibindo 8 de {items.length} técnicos.</p> : null}
    </Card>
  );
}

function ActionPanel({
  actions,
  onNavigate,
  onStartCheckin,
  title,
}: {
  actions: ActionDefinition[];
  onNavigate: (target: NavigationTarget) => void;
  onStartCheckin?: () => void;
  title: string;
}) {
  return (
    <Card className="p-5">
      <h2 className="mb-4 text-xl font-bold text-white">{title}</h2>
      {actions.length ? (
        <div className="tp-action-grid">
          {actions.map((action, index) => {
            const opensCheckin = Boolean(action.opensCheckin && onStartCheckin);
            const disabled = Boolean(
              action.disabledReason ||
                (action.opensCheckin && !onStartCheckin) ||
                (!action.opensCheckin && !action.target && !action.externalHref),
            );
            const ActionIcon = action.label.includes("WhatsApp") ? WhatsAppLogo : action.icon;
            return (
              <button
                className="min-h-[112px] rounded-card border border-tec-border/20 bg-tec-field/75 p-4 text-left shadow-sm transition hover:border-tec-orange/50 hover:bg-tec-orange/10 disabled:cursor-not-allowed disabled:opacity-55"
                disabled={disabled}
                key={`${action.label}-${index}`}
                onClick={() => {
                  if (action.opensCheckin && onStartCheckin) {
                    onStartCheckin();
                  } else if (action.disabledReason) {
                    return;
                  } else if (action.externalHref) {
                    window.open(action.externalHref, "_blank", "noopener,noreferrer");
                  } else if (action.target) {
                    onNavigate(action.target);
                  }
                }}
                title={disabled ? action.disabledReason ?? "Ação sem destino configurado para este perfil" : action.label}
                type="button"
              >
                <span className="mb-4 grid h-11 w-11 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">
                  <ActionIcon size={26} />
                </span>
                <span className="block text-sm font-bold text-white">{action.label}</span>
                <span className="mt-1 block text-xs text-tec-muted">{action.detail}</span>
                {disabled ? (
                  <span className="mt-2 inline-flex rounded-full bg-tec-field px-2 py-1 text-[10px] font-bold uppercase text-tec-muted">
                    {action.pendingLabel ?? "Sem acesso"}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      ) : (
        <div className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-4 text-sm text-tec-muted">
          Selecione uma ação no painel principal.
        </div>
      )}
    </Card>
  );
}

type AgendaView = "list" | "week" | "month";

type AgendaRange = {
  start: string;
  end: string;
  days: string[];
  label: string;
};

function toIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return year + "-" + month + "-" + day;
}

function fromIsoDate(value: string): Date {
  const parts = value.split("-").map(Number);
  return new Date(parts[0], (parts[1] || 1) - 1, parts[2] || 1);
}

function addAgendaDays(value: string, days: number): string {
  const date = fromIsoDate(value);
  date.setDate(date.getDate() + days);
  return toIsoDate(date);
}

function addAgendaMonths(value: string, months: number): string {
  const date = fromIsoDate(value);
  date.setDate(1);
  date.setMonth(date.getMonth() + months);
  return toIsoDate(date);
}

function getAgendaRange(anchor: string, view: AgendaView): AgendaRange {
  const anchorDate = fromIsoDate(anchor);
  if (view === "week") {
    const mondayOffset = (anchorDate.getDay() + 6) % 7;
    anchorDate.setDate(anchorDate.getDate() - mondayOffset);
    const start = toIsoDate(anchorDate);
    return {
      start,
      end: addAgendaDays(start, 6),
      days: Array.from({ length: 7 }, (_, index) => addAgendaDays(start, index)),
      label: anchorDate.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }) + " - " + fromIsoDate(addAgendaDays(start, 6)).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }),
    };
  }
  if (view === "month") {
    const first = new Date(anchorDate.getFullYear(), anchorDate.getMonth(), 1);
    first.setDate(first.getDate() - ((first.getDay() + 6) % 7));
    const start = toIsoDate(first);
    return {
      start,
      end: addAgendaDays(start, 41),
      days: Array.from({ length: 42 }, (_, index) => addAgendaDays(start, index)),
      label: fromIsoDate(anchor).toLocaleDateString("pt-BR", { month: "long", year: "numeric" }),
    };
  }
  return { start: anchor, end: anchor, days: [anchor], label: anchor };
}

function formatAgendaDay(value: string, options: Intl.DateTimeFormatOptions): string {
  return fromIsoDate(value).toLocaleDateString("pt-BR", options);
}

function DailyActionsPanel({
  onOpenOrder,
  onToast,
  panel,
  storageKey,
}: {
  onOpenOrder: (name: string) => void;
  onToast: (message: string, tone?: ToastState["tone"]) => void;
  panel: RolePanel | "unified";
  storageKey: string;
}) {
  const [state, setState] = useState<DailyActionsResponse | null>(null);
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [saving, setSaving] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [agendaView, setAgendaView] = useState<AgendaView>(() => {
    try {
      // A versioned preference promotes the calendar for existing users too.
      const stored = window.localStorage.getItem("tecponto.agenda.v2.view." + storageKey);
      return stored === "list" || stored === "week" ? stored : "month";
    } catch {
      return "month";
    }
  });
  const [calendarAnchor, setCalendarAnchor] = useState(() => toIsoDate(new Date()));
  const [calendarItems, setCalendarItems] = useState<AgendaCalendarEvent[]>([]);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [calendarRefresh, setCalendarRefresh] = useState(0);

  const refresh = useCallback(async () => {
    try {
      setState(await dailyActions.list(panel));
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Falha ao carregar pendencias.", "error");
    }
  }, [onToast, panel]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    try {
      window.localStorage.setItem("tecponto.agenda.v2.view." + storageKey, agendaView);
    } catch {
      // Persisting a visual preference must never affect the agenda.
    }
  }, [agendaView, storageKey]);

  const calendarRange = useMemo(() => getAgendaRange(calendarAnchor, agendaView), [agendaView, calendarAnchor]);

  useEffect(() => {
    if (agendaView === "list") {
      return;
    }
    let cancelled = false;
    setCalendarLoading(true);
    void dailyActions.calendar(panel, calendarRange.start, calendarRange.end)
      .then((response) => {
        if (!cancelled) {
          setCalendarItems(response.items);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          onToast(error instanceof Error ? error.message : "Falha ao carregar o calendario.", "error");
          setCalendarItems([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setCalendarLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [agendaView, calendarRange.end, calendarRange.start, calendarRefresh, onToast, panel]);

  const addTask = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!title.trim()) {
      return;
    }
    setSaving(true);
    try {
      await dailyActions.create(title.trim(), dueDate || undefined);
      setTitle("");
      setDueDate("");
      await refresh();
      setCalendarRefresh((current) => current + 1);
      onToast("Tarefa adicionada para voce.");
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Nao foi possivel criar a tarefa.", "error");
    } finally {
      setSaving(false);
    }
  };

  const completeTask = async (task: TecpontoTask) => {
    try {
      await dailyActions.complete(task.name);
      await refresh();
      setCalendarRefresh((current) => current + 1);
      onToast("Tarefa concluida.");
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Nao foi possivel concluir a tarefa.", "error");
    }
  };

  const derived = state?.derived ?? [];
  const manual = state?.manual ?? [];
  const agendaItems = state?.items ?? [...derived, ...manual];
  const count = state?.count ?? 0;
  const groupedAgenda = useMemo(() => {
    return (["overdue", "due_today", "scheduled"] as const).map((urgency) => {
      const items = agendaItems.filter((item) => item.urgency === urgency);
      const groups = new Map<string, typeof items>();
      for (const item of items) {
        const key = item.group_key || ("key" in item ? item.key : item.name);
        groups.set(key, [...(groups.get(key) ?? []), item]);
      }
      return { urgency, groups: [...groups.entries()] };
    });
  }, [agendaItems]);

  return (
    <Card className="p-5" data-testid="daily-actions-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white">Precisa de voce hoje</h2>
            <span className="rounded-full bg-tec-orange/15 px-2 py-1 text-xs font-bold text-tec-orange">{count}</span>
          </div>
          <p className="mt-1 text-sm text-tec-muted">Atrasos, prazos de hoje e programados vêm do estado real; tarefas manuais entram na mesma agenda.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div aria-label="Visao da agenda" className="inline-flex rounded-control border border-tec-border/20 bg-tec-field/65 p-1" role="group">
            {([
              ["month", "Mes", CalendarClock],
              ["week", "Semana", CalendarDays],
              ["list", "Lista", ClipboardCheck],
            ] as const).map(([view, label, Icon]) => (
              <button
                className={cx("inline-flex items-center gap-1.5 rounded-control px-3 py-2 text-xs font-bold transition", agendaView === view ? "bg-tec-orange text-tec-graphite" : "text-tec-subtle hover:bg-tec-panel hover:text-white")}
                key={view}
                onClick={() => setAgendaView(view)}
                type="button"
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
          </div>
          <Button icon={<RefreshCw size={16} />} onClick={() => { void refresh(); setCalendarRefresh((current) => current + 1); }} variant="secondary">
            Atualizar
          </Button>
        </div>
      </div>

      {agendaView === "list" ? <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)]">
        <section>
          {groupedAgenda.map(({ urgency, groups }) => {
            const meta = urgency === "overdue" ? { label: "Atrasado", dot: "bg-tec-red" } : urgency === "due_today" ? { label: "Vence hoje", dot: "bg-tec-amber" } : { label: "Programado", dot: "bg-tec-success" };
            return (
              <section className="mb-4 last:mb-0" key={urgency}>
                <div className="mb-2 flex items-center gap-2"><span className={cx("h-2.5 w-2.5 rounded-full", meta.dot)} /><h3 className="text-sm font-bold text-white">{meta.label}</h3></div>
                <div className="space-y-2">
                  {groups.length ? groups.map(([groupKey, items]) => {
                    const groupLabel = items[0]?.group_label || items[0]?.title || "Itens";
                    const expanded = expandedGroups[groupKey] ?? false;
                    const multiple = items.length > 1;
                    return <div className="overflow-hidden rounded-control border border-tec-border/20 bg-tec-field/55" key={groupKey}>
                      {multiple ? <button aria-expanded={expanded} className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left transition hover:bg-tec-orange/10" onClick={() => setExpandedGroups((current) => ({ ...current, [groupKey]: !expanded }))} type="button"><span className="flex min-w-0 items-center gap-2"><span className="text-sm font-bold text-white">{items.length} {groupLabel}</span><span className="truncate text-xs text-tec-muted">Expandir detalhes</span></span>{expanded ? <ChevronDown className="shrink-0 text-tec-muted" size={17} /> : <ChevronRight className="shrink-0 text-tec-muted" size={17} />}</button> : null}
                      {(!multiple || expanded) ? <div className={multiple ? "border-t border-tec-border/15" : ""}>{items.map((item) => {
                        const derivedItem = "key" in item;
                        return <button className="flex w-full items-center justify-between gap-3 border-b border-tec-border/15 px-3 py-3 text-left last:border-b-0 transition hover:border-tec-orange/50 hover:bg-tec-orange/10" key={derivedItem ? item.key : item.name} onClick={() => item.reference_doctype === "Service Order" && item.reference_name ? onOpenOrder(item.reference_name) : undefined} title={item.reference_doctype === "Service Order" ? "Abrir ordem de servico" : item.title} type="button"><span className="min-w-0"><span className="block truncate text-sm font-bold text-white">{item.title}</span><span className="mt-1 block truncate text-xs text-tec-muted">{derivedItem ? item.description : item.due_date || "Tarefa sem prazo"}</span></span>{derivedItem ? <ArrowRight className="shrink-0 text-tec-muted" size={17} /> : <CheckCircle2 className="shrink-0 text-tec-success" size={17} />}</button>;
                      })}</div> : null}
                    </div>;
                  }) : <p className="rounded-control border border-dashed border-tec-border/20 px-3 py-3 text-sm text-tec-muted">Nenhum item.</p>}
                </div>
              </section>
            );
          })}
        </section>

        <section className="border-t border-tec-border/15 pt-5 xl:border-l xl:border-t-0 xl:pl-5 xl:pt-0">
          <div className="mb-3 flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-control bg-tec-blue/10 text-tec-blue"><Plus size={16} /></span>
            <h3 className="font-bold text-white">Minhas tarefas</h3>
          </div>
          <form className="flex flex-wrap gap-2" onSubmit={(event) => void addTask(event)}>
            <input aria-label="Nova tarefa" className="min-w-0 flex-1 rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 text-sm text-tec-text outline-none focus:border-tec-orange/70" maxLength={140} onChange={(event) => setTitle(event.target.value)} placeholder="Adicionar tarefa" value={title} />
            <input aria-label="Prazo da tarefa" className="rounded-control border border-tec-border/20 bg-tec-field px-2 py-2 text-xs text-tec-text outline-none focus:border-tec-orange/70" onChange={(event) => setDueDate(event.target.value)} type="date" value={dueDate} />
            <Button disabled={saving || !title.trim()} icon={<Plus size={16} />} type="submit">Adicionar</Button>
          </form>
          <div className="mt-3 space-y-2">
            {manual.length ? manual.map((task) => (
              <div className="flex items-center justify-between gap-3 rounded-control border border-tec-border/20 bg-tec-field/45 px-3 py-2.5" key={task.name}>
                <span className="min-w-0"><span className="block truncate text-sm font-semibold text-tec-text">{task.title}</span><span className="text-xs text-tec-muted">{task.due_date || "Sem prazo"}</span></span>
                <button className="rounded-control border border-tec-success/35 px-2 py-1 text-xs font-bold text-tec-success transition hover:bg-tec-success/10" onClick={() => void completeTask(task)} title="Concluir tarefa" type="button"><CheckCircle2 size={15} /></button>
              </div>
            )) : <p className="rounded-control bg-tec-field/45 px-3 py-4 text-sm text-tec-muted">Sem tarefas manuais.</p>}
          </div>
        </section>
      </div> : <AgendaCalendarView
        anchor={calendarAnchor}
        items={calendarItems}
        loading={calendarLoading}
        onChangeAnchor={setCalendarAnchor}
        onOpenOrder={onOpenOrder}
        range={calendarRange}
        view={agendaView}
      />}
    </Card>
  );
}

function AgendaCalendarView({
  anchor,
  items,
  loading,
  onChangeAnchor,
  onOpenOrder,
  range,
  view,
}: {
  anchor: string;
  items: AgendaCalendarEvent[];
  loading: boolean;
  onChangeAnchor: (value: string) => void;
  onOpenOrder: (name: string) => void;
  range: AgendaRange;
  view: Exclude<AgendaView, "list">;
}) {
  const [selectedDay, setSelectedDay] = useState(anchor);
  const itemsByDay = useMemo(() => {
    const result = new Map<string, AgendaCalendarEvent[]>();
    for (const item of items) {
      result.set(item.date, [...(result.get(item.date) ?? []), item]);
    }
    return result;
  }, [items]);
  const anchorMonth = anchor.slice(0, 7);
  const selectedItems = itemsByDay.get(selectedDay) ?? [];
  const move = (amount: number) => {
    const next = view === "week" ? addAgendaDays(anchor, amount * 7) : addAgendaMonths(anchor, amount);
    setSelectedDay(next);
    onChangeAnchor(next);
  };

  useEffect(() => {
    if (!range.days.includes(selectedDay)) {
      setSelectedDay(range.days[0]);
    }
  }, [range.days, selectedDay]);

  const dayWeight = (total: number) => total >= 5 ? "bg-tec-red" : total >= 3 ? "bg-tec-orange" : total ? "bg-tec-success" : "bg-transparent";

  return (
    <section className="mt-5" data-testid="agenda-calendar-view">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold capitalize text-white">{range.label}</h3>
          <p className="mt-1 text-sm text-tec-muted">Entregas prometidas, retiradas e tarefas com data. OS sem prazo continuam na Lista.</p>
        </div>
        <div className="flex items-center gap-2">
          <button aria-label="Periodo anterior" className="grid h-9 w-9 place-items-center rounded-control border border-tec-border/20 text-tec-subtle transition hover:border-tec-orange/45 hover:text-white" onClick={() => move(-1)} type="button"><ChevronLeft size={18} /></button>
          <button className="rounded-control border border-tec-border/20 px-3 py-2 text-xs font-bold text-tec-subtle transition hover:border-tec-orange/45 hover:text-white" onClick={() => { const todayValue = toIsoDate(new Date()); setSelectedDay(todayValue); onChangeAnchor(todayValue); }} type="button">Hoje</button>
          <button aria-label="Proximo periodo" className="grid h-9 w-9 place-items-center rounded-control border border-tec-border/20 text-tec-subtle transition hover:border-tec-orange/45 hover:text-white" onClick={() => move(1)} type="button"><ChevronRight size={18} /></button>
        </div>
      </div>

      {loading ? <div className="rounded-card border border-tec-border/20 bg-tec-field/45 px-4 py-10 text-center text-sm text-tec-muted">Carregando agenda...</div> : null}
      {!loading && view === "week" ? <div className="tp-responsive-scroll pb-2">
        <div className="grid min-w-[840px] grid-cols-7 gap-3">
          {range.days.map((day) => {
            const dayItems = itemsByDay.get(day) ?? [];
            return <article className="min-h-[230px] rounded-card border border-tec-border/20 bg-tec-panel-strong p-3" key={day}>
              <div className="mb-3 flex items-start justify-between gap-2 border-b border-tec-border/15 pb-2">
                <div><p className="text-xs font-bold uppercase text-tec-muted">{formatAgendaDay(day, { weekday: "short" })}</p><p className="mt-1 text-lg font-bold text-white">{formatAgendaDay(day, { day: "2-digit", month: "short" })}</p></div>
                <span className={cx("mt-1 h-2.5 w-2.5 rounded-full", dayWeight(dayItems.length))} title={dayItems.length + " itens"} />
              </div>
              <div className="space-y-2">
                {dayItems.length ? dayItems.map((item) => <AgendaCalendarItem item={item} key={item.key} onOpenOrder={onOpenOrder} />) : <p className="pt-4 text-xs text-tec-muted">Sem itens datados.</p>}
              </div>
            </article>;
          })}
        </div>
      </div> : null}

      {!loading && view === "month" ? <div>
        <div className="grid grid-cols-7 border-l border-t border-tec-border/20 rounded-card overflow-hidden">
          {["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"].map((label) => <div className="border-b border-r border-tec-border/20 bg-tec-field/55 px-2 py-2 text-center text-xs font-bold text-tec-muted" key={label}>{label}</div>)}
          {range.days.map((day) => {
            const dayItems = itemsByDay.get(day) ?? [];
            const selected = selectedDay === day;
            const currentMonth = day.startsWith(anchorMonth);
            return <button className={cx("relative min-h-[88px] border-b border-r border-tec-border/20 p-2 text-left transition hover:bg-tec-orange/10", selected && "bg-tec-orange/10 ring-1 ring-inset ring-tec-orange/60", !currentMonth && "bg-tec-field/25 text-tec-muted")} key={day} onClick={() => setSelectedDay(day)} type="button">
              <span className={cx("text-sm font-bold", currentMonth ? "text-white" : "text-tec-muted")}>{formatAgendaDay(day, { day: "2-digit" })}</span>
              {dayItems.length ? <span className={cx("ml-1 inline-flex min-w-5 items-center justify-center rounded-full px-1.5 py-0.5 text-[10px] font-bold text-tec-graphite", dayWeight(dayItems.length))}>{dayItems.length}</span> : null}
              {dayItems.length ? <span className="absolute bottom-2 left-2 right-2 flex gap-1">{dayItems.slice(0, 4).map((item) => <span className={cx("h-1.5 flex-1 rounded-full", item.kind === "delivery" ? "bg-tec-blue" : item.kind === "pickup" ? "bg-tec-success" : "bg-tec-amber")} key={item.key} />)}</span> : null}
            </button>;
          })}
        </div>
        <div className="mt-4 rounded-card border border-tec-border/20 bg-tec-panel-strong p-4">
          <div className="mb-3 flex items-center justify-between gap-2"><h4 className="font-bold text-white">{formatAgendaDay(selectedDay, { weekday: "long", day: "2-digit", month: "long" })}</h4><span className="text-xs text-tec-muted">{selectedItems.length} item(ns)</span></div>
          <div className="grid gap-2 md:grid-cols-2">{selectedItems.length ? selectedItems.map((item) => <AgendaCalendarItem item={item} key={item.key} onOpenOrder={onOpenOrder} />) : <p className="text-sm text-tec-muted">Nenhuma entrega, retirada ou tarefa nesta data.</p>}</div>
        </div>
      </div> : null}

      <div className="mt-4 flex flex-wrap gap-3 text-xs text-tec-muted"><span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-tec-blue" />Entrega prometida</span><span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-tec-success" />Retirada</span><span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-tec-amber" />Tarefa manual</span></div>
    </section>
  );
}

function AgendaCalendarItem({ item, onOpenOrder }: { item: AgendaCalendarEvent; onOpenOrder: (name: string) => void }) {
  const kindLabel = item.kind === "delivery" ? "Entrega" : item.kind === "pickup" ? "Retirada" : "Tarefa";
  const className = item.kind === "delivery" ? "border-tec-blue/35 bg-tec-blue/10 text-tec-blue" : item.kind === "pickup" ? "border-tec-success/35 bg-tec-success/10 text-tec-success" : "border-tec-amber/35 bg-tec-amber/10 text-tec-amber";
  const openable = item.reference_doctype === "Service Order" && item.reference_name;
  return <button className={cx("block w-full rounded-control border px-2.5 py-2 text-left transition hover:brightness-125", className)} onClick={() => openable ? onOpenOrder(item.reference_name as string) : undefined} title={openable ? "Abrir ordem de servico" : item.title} type="button"><span className="block text-[10px] font-bold uppercase opacity-80">{kindLabel}</span><span className="mt-0.5 block truncate text-xs font-bold">{item.title}</span><span className="mt-1 block truncate text-[11px] opacity-80">{item.description}</span></button>;
}

function AlertLine({
  count,
  href,
  onClick,
  title,
  tone,
}: {
  count: number;
  href?: string;
  onClick?: () => void;
  title: string;
  tone: "orange" | "amber" | "green";
}) {
  const toneClass = {
    orange: "bg-tec-orange",
    amber: "bg-tec-amber",
    green: "bg-tec-success",
  }[tone];

  const content = (
    <>
      <span className="flex min-w-0 items-center gap-3 text-tec-subtle">
        <span className={`h-2.5 w-2.5 rounded-full ${toneClass}`} />
        <span className="truncate">{title}</span>
      </span>
      <span className="flex items-center gap-3">
        <span className="rounded-full bg-tec-orange/20 px-2 py-1 text-xs font-bold text-tec-orange">{count}</span>
        <ArrowRight size={15} className="text-tec-muted" />
      </span>
    </>
  );

  const className = "flex w-full items-center justify-between gap-3 rounded-control px-1 py-1.5 text-left transition hover:bg-tec-field/55";

  if (href) {
    return (
      <a className={className} href={href} rel="noreferrer" target="_blank" title={`Abrir ${title}`}>
        {content}
      </a>
    );
  }

  return (
    <button className={className} onClick={onClick} title={`Abrir ${title}`} type="button">
      {content}
    </button>
  );
}

function LoadingShell() {
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <Card className="w-full max-w-md p-6 text-center">
        <div className="mx-auto h-12 w-12 animate-spin rounded-full border-2 border-tec-orange border-t-transparent" />
		<p className="mt-4 text-sm font-semibold text-tec-subtle">Carregando sistema</p>
      </Card>
    </main>
  );
}

function NoRoleScreen({ boot, onLogout, onRetry }: { boot: BootResponse; onLogout: () => void; onRetry: () => void }) {
  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden bg-tec-bg p-4">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_24%_20%,rgba(254,80,0,0.16),transparent_30%),radial-gradient(circle_at_78%_28%,rgba(245,164,0,0.1),transparent_25%)]" />
      <section className="relative w-full max-w-2xl rounded-[26px] border border-tec-border/20 bg-tec-panel p-6 text-center shadow-panel md:p-8">
        <span className="mx-auto grid h-16 w-16 place-items-center rounded-[20px] bg-tec-amber/15 text-tec-amber">
          <ShieldAlert size={28} />
        </span>
		<p className="mt-6 text-xs font-bold uppercase tracking-wide text-tec-orange">Acesso operacional</p>
        <h1 className="mt-2 text-3xl font-bold text-white">Usuário sem papel operacional</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-tec-subtle">
		  O login de {boot.user.full_name || boot.user.name} está ativo no Frappe, mas ainda não possui um papel operacional. Nenhum dado de operação foi carregado.
        </p>
        <div className="mt-6 rounded-card border border-tec-border/15 bg-tec-field p-4 text-left text-sm text-tec-subtle">
          <p className="font-bold text-white">Próximo passo</p>
		  <p className="mt-1">Peça ao gestor para vincular um papel operacional ao usuário {boot.user.name}.</p>
        </div>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Button onClick={onRetry} variant="primary">
            Tentar novamente
          </Button>
          <Button onClick={onLogout}>Sair</Button>
        </div>
      </section>
    </main>
  );
}

function formatDate(value: string) {
  const date = parseServerDate(value);
  if (!date) {
    return value ? value : "Sem data";
  }
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function compactServiceOrderDescription(value?: string | null) {
  const fallback = "Sem descricao";
  const text = (value ?? "").replace(/\s+/g, " ").trim();
  if (!text) {
    return fallback;
  }

  const firstSentence = text.split(/[.!?]\s+/)[0] || text;
  const summary = firstSentence
    .replace(/^Cliente relata\s+/i, "")
    .replace(/^Observações adicionais:\s*/i, "")
    .trim();
  const normalized = summary || text;
  return normalized.length > 88 ? `${normalized.slice(0, 85).trimEnd()}...` : normalized;
}

function filterOrdersByDashboardPeriod(orders: ServiceOrderSummary[], filter: DashboardPeriodFilter) {
  const bounds = getDashboardPeriodBounds(filter);
  if (!bounds) {
    return orders;
  }

  return orders.filter((order) => {
    const date = parseFrappeDate(order.modified);
    return date ? date >= bounds.start && date <= bounds.end : false;
  });
}

function filterOrdersForServiceOrderScreen(orders: ServiceOrderSummary[], filters: ServiceOrderFilterState) {
	const showingStoreInventory = filters.period.mode === "none";
	const periodFilteredOrders = showingStoreInventory ? orders : filterOrdersByDashboardPeriod(orders, filters.period);
  return periodFilteredOrders.filter((order) => {
	if (showingStoreInventory && order.pickup_date) {
		return false;
	}
    if (filters.status !== "all" && order.workflow_state !== filters.status) {
      return false;
    }
		if (filters.priority !== "all" && order.priority !== filters.priority) {
			return false;
		}
		if (filters.assignment === "assigned" && !order.technician) {
			return false;
		}
		if (filters.assignment === "unassigned" && order.technician) {
			return false;
		}
    return matchesServiceOrderSearch(order, filters.query);
  });
}

function toServiceOrderQueryParams(filters: ServiceOrderFilterState, limit: number): ServiceOrderQueryParams {
  const params: ServiceOrderQueryParams = { limit };
  const query = filters.query.trim();
  if (query) {
    params.query = query;
  }
  params.in_progress = filters.period.mode === "none";
  if (filters.status !== "all") {
    params.status = filters.status;
  }

  // Physical custody defines in-progress: no date window may hide an order
  // whose device has not been picked up.
  if (filters.period.mode !== "none") {
    if (filters.period.mode === "custom") {
      if (filters.period.fromDate) {
        params.from_date = filters.period.fromDate;
      }
      if (filters.period.toDate) {
        params.to_date = filters.period.toDate;
      }
    } else {
      const bounds = getDashboardPeriodBounds(filters.period);
      if (bounds) {
        params.from_date = formatDateInputValue(bounds.start);
        params.to_date = formatDateInputValue(bounds.end);
      }
    }
  }

  return params;
}

function matchesServiceOrderSearch(order: ServiceOrderSummary, query: string) {
  const normalizedQuery = normalizeSearchText(query);
  if (!normalizedQuery) {
    return true;
  }

  return normalizeSearchText(
    [
      order.name,
      order.customer,
      order.customer_device,
      order.reported_defect,
      order.workflow_state,
      order.technician,
      order.attendant,
      order.priority,
    ]
      .filter(Boolean)
      .join(" "),
  ).includes(normalizedQuery);
}

function normalizeSearchText(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function getDashboardPeriodBounds(filter: DashboardPeriodFilter) {
  if (filter.mode === "none") {
    return null;
  }
  const now = new Date();
  const end = endOfDay(filter.mode === "custom" && filter.toDate ? parseDateInput(filter.toDate) : now);
  let start: Date | null;

  if (filter.mode === "custom") {
    start = filter.fromDate ? startOfDay(parseDateInput(filter.fromDate)) : null;
  } else {
    start = startOfDay(addCalendarDays(now, filter.mode === "14d" ? -13 : -6));
  }

  if (!start && !filter.toDate) {
    return null;
  }

  return {
    end,
    start: start ?? startOfDay(new Date(0)),
  };
}

function parseFrappeDate(value: string) {
  if (!value) {
    return null;
  }
  const date = new Date(value.replace(" ", "T"));
  return Number.isNaN(date.getTime()) ? null : date;
}

function parseDateInput(value: string) {
  const [year, month, day] = value.split("-").map((part) => Number.parseInt(part, 10));
  return new Date(year, month - 1, day);
}

function formatDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function startOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
}

function endOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
}

function addCalendarDays(date: Date, days: number) {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    currency: "BRL",
    style: "currency",
  }).format(value || 0);
}

function buildWhatsAppUrl(phone: string | null | undefined, message: string) {
  const digits = (phone ?? "").replace(/\D/g, "");
  if (!digits) {
    return null;
  }
  const normalized = digits.startsWith("55") ? digits : `55${digits}`;
  return `https://wa.me/${normalized}?text=${encodeURIComponent(message)}`;
}

function timelineToneClass(tone: ServiceOrderTimelineEvent["tone"]) {
  return {
    amber: "bg-tec-amber/20 text-tec-amber",
    blue: "bg-tec-blue/20 text-tec-blue",
    green: "bg-tec-success/20 text-tec-success",
    orange: "bg-tec-orange/20 text-tec-orange",
    red: "bg-tec-red/20 text-tec-red",
  }[tone];
}
