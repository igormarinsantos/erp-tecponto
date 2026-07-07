export type RolePanel = "atendente" | "tecnico" | "gestor" | "diretor" | "sem_papel";
export type NavigationTarget =
  | "overview"
  | "service-orders"
  | "service-order-detail"
  | "customers"
  | "devices"
  | "trade-ins"
  | "parts-stock"
  | "sales";

export interface LoggedUser {
  name: string;
  full_name: string;
  initials: string;
  roles: string[];
  panel: RolePanel;
  role_label: string;
  role_name: string;
  subtitle: string;
}

export interface BootResponse {
  user: LoggedUser;
  app: {
    name: string;
    route: string;
    version: string;
  };
  panels: Array<{
    panel: RolePanel;
    role: string;
    label: string;
    subtitle: string;
  }>;
}

export interface ServiceOrderSummary {
  name: string;
  customer: string | null;
  customer_device: string | null;
  entry_date: string;
  attendant: string | null;
  technician: string | null;
  priority: string | null;
  workflow_state: string | null;
  reported_defect: string | null;
  approval_status: string | null;
  approval_deadline: string;
  modified: string;
}

export interface ServiceOrderListResponse {
  items: ServiceOrderSummary[];
  count: number;
  fields: string[];
}

export interface ServiceOrderDetailResponse {
  name: string;
  workflow_state: string | null;
  approval_status: string | null;
  approval_deadline: string;
  entry_date: string;
  modified: string;
  attendant: string | null;
  technician: string | null;
  priority: string | null;
  customer: ServiceOrderCustomerDetail | null;
  device: ServiceOrderDeviceDetail | null;
  reported_defect: string | null;
  physical_state: string | null;
  accessories_received: string | null;
  diagnosis: {
    problem_found: string | null;
    diagnosis_date: string;
    diagnosis_deadline: string;
  };
  services: ServiceOrderBudgetLine[];
  parts: ServiceOrderBudgetLine[];
  totals: {
    service_total: number;
    parts_price_total: number;
    discount: number;
    grand_total: number;
    budget_version: number;
    quote_locked: boolean;
  };
  warranty: {
    is_warranty: boolean;
    original_service_order: string | null;
    warranty_expiry: string;
  };
  pickup: {
    pickup_by_third_party: boolean;
    pickup_person_name: string | null;
    pickup_person_document: string | null;
    pickup_date: string;
  };
  workflow_actions: ServiceOrderWorkflowAction[];
  timeline: ServiceOrderTimelineEvent[];
  print_links: ServiceOrderPrintLink[];
}

export interface ServiceOrderBudgetLine {
  item_code: string | null;
  description: string | null;
  qty: number;
  unit_price: number;
  amount: number;
  technician?: string | null;
  warehouse?: string | null;
  outcome?: string | null;
  loss_reason?: string | null;
}

export interface ServiceOrderCustomerDetail {
  name: string;
  customer_name: string | null;
  mobile_no: string | null;
  email_id: string | null;
}

export interface ServiceOrderDeviceDetail {
  name: string;
  customer: string | null;
  brand: string | null;
  model: string | null;
  color: string | null;
  imei_serial: string | null;
  capacity: string | null;
}

export interface ServiceOrderWorkflowAction {
  action: string;
  next_state: string;
  role: string;
}

export interface ServiceOrderTimelineEvent {
  title: string;
  detail: string | null;
  date: string;
  tone: "blue" | "amber" | "green" | "red" | "orange";
}

export interface ServiceOrderPrintLink {
  label: string;
  format: string;
  url: string;
}

export interface DashboardMetrics {
  sales_today_total: number;
  service_orders: {
    total: number;
    awaiting_approval: number;
    ready_for_pickup: number;
    waiting_part: number;
    new_today: number;
    overdue: number;
  };
}

export interface CustomerSummary {
  name: string;
  customer_name: string | null;
  mobile_no: string | null;
  email_id: string | null;
  modified: string;
}

export interface CustomerSearchResponse {
  items: CustomerSummary[];
  count: number;
  fields: string[];
}

export interface CustomerDeviceSummary {
  name: string;
  customer: string | null;
  brand: string | null;
  model: string | null;
  color: string | null;
  imei_serial: string | null;
  capacity: string | null;
  registration_date: string;
  modified: string;
}

export interface CustomerDeviceListResponse {
  items: CustomerDeviceSummary[];
  count: number;
  fields: string[];
}

export interface TradeEvaluationSummary {
  name: string;
  customer: string | null;
  device_type: string | null;
  evaluated_device_desc: string | null;
  model: string | null;
  imei: string | null;
  physical_state: string | null;
  destination: string | null;
  workflow_state: string | null;
  modified: string;
}

export interface TradeEvaluationListResponse {
  items: TradeEvaluationSummary[];
  count: number;
  fields: string[];
}

export interface StockItemSummary {
  item_code: string;
  item_name: string | null;
  item_group: string | null;
  warehouse: string | null;
  available_qty: number;
}

export interface StockItemListResponse {
  items: StockItemSummary[];
  count: number;
  fields: string[];
}
