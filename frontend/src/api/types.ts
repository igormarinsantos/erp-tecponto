export type RolePanel = "atendente" | "tecnico" | "gestor" | "diretor" | "sem_papel";
export type NavigationTarget =
  | "overview"
  | "service-orders"
  | "service-order-detail"
  | "customers"
  | "devices"
  | "trade-ins"
  | "parts-stock"
  | "pos"
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

export interface ServiceOrderKanbanColumn {
  state: string;
  count: number;
  items: ServiceOrderSummary[];
}

export interface ServiceOrderKanbanResponse {
  columns: ServiceOrderKanbanColumn[];
  fields: string[];
}

export interface ServiceOrderMoveResponse {
  item: ServiceOrderSummary;
  changed: boolean;
}

export interface ServiceOrderDetailResponse {
  name: string;
  workflow_state: string | null;
  approval_status: string | null;
  approval_deadline: string;
  approval: {
    channel: string | null;
    approved_by: string | null;
    approved_by_attendant: string | null;
    approval_date: string;
    notes: string | null;
  };
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
    pickup_notes: string | null;
    has_signature: boolean;
  };
  finance: {
    sales_invoice: string | null;
    sales_invoice_status: string | null;
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

export type BudgetLineType = "service" | "part";

export interface BudgetItemSummary {
  has_price: boolean;
  item_code: string;
  item_name: string | null;
  item_group: string | null;
  is_stock_item: boolean;
  standard_rate: number;
}

export interface BudgetItemSearchResponse {
  items: BudgetItemSummary[];
}

export interface PosItemSummary {
  available_qty: number;
  barcode: string | null;
  description: string | null;
  has_price: boolean;
  image: string | null;
  item_code: string;
  item_group: string | null;
  item_name: string | null;
  standard_rate: number;
  warehouse: string;
}

export interface PosItemSearchResponse {
  count: number;
  fields: string[];
  items: PosItemSummary[];
}

export type PosPaymentMode = "Pix" | "Dinheiro" | "Débito" | "Crédito à vista" | "Crédito parcelado";

export interface PosSalePaymentPayload {
  amount: number;
  installments?: number;
  mode_of_payment: PosPaymentMode;
}

export interface PosSalePayload {
  customer: string;
  discount_amount: number;
  idempotency_key: string;
  items: Array<{
    item_code: string;
    qty: number;
    serial_no?: string | null;
  }>;
  payments: PosSalePaymentPayload[];
}

export interface PosSaleResponse {
  customer: string;
  customer_name: string | null;
  grand_total: number;
  idempotent_replay: boolean;
  items: Array<{
    amount: number;
    item_code: string;
    item_name: string | null;
    qty: number;
    unit_price: number;
  }>;
  paid_amount: number;
  payments: Array<{
    amount: number;
    mode_of_payment: PosPaymentMode;
  }>;
  posting_date: string;
  receipt: {
    format: string;
    url: string;
  };
  sale: string;
  status: string;
}

export interface BudgetWarehouseSummary {
  name: string;
  warehouse_name: string | null;
}

export interface BudgetWarehouseListResponse {
  items: BudgetWarehouseSummary[];
}

export interface BudgetLinePayload {
  type: BudgetLineType;
  item_code: string;
  description?: string;
  qty: number;
  rate: number;
  warehouse?: string;
}

export interface QuoteSendPayload {
  channel: "WhatsApp" | "Telefone" | "Presencial" | "E-mail";
  notes?: string;
}

export interface ServiceOrderCustomerDetail {
  name: string;
  customer_name: string | null;
  mobile_no: string | null;
  custom_whatsapp: string | null;
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

export interface CheckinPayload {
  customer: {
    existing_name?: string;
    customer_name?: string;
    mobile_no?: string;
    custom_whatsapp?: string;
    custom_cpf?: string;
    custom_rg?: string;
    custom_nao_possui_cpf?: boolean;
    email_id?: string;
  };
  device: {
    existing_name?: string;
    brand?: string;
    model?: string;
    color?: string;
    imei_serial?: string;
    capacity?: string;
    general_state?: string;
  };
  service_order: {
    reported_defect: string;
    physical_state: string;
    accessories_received?: string;
  };
  entry_photo: {
    data_url: string;
    filename: string;
  };
  entry_signature: string;
}

export interface CheckinResponse {
  service_order: Pick<ServiceOrderDetailResponse, "name" | "workflow_state" | "customer" | "device" | "print_links">;
  entry_photo_url: string;
}

export interface BudgetDecisionPayload {
  decision: "approve" | "reject";
  channel: "Presencial" | "Telefone" | "WhatsApp";
  notes?: string;
}

export interface PickupPayload {
  customer_signature: string;
  third_party: boolean;
  picked_up_by?: string;
  picked_up_doc?: string;
  third_party_auth?: string;
  pickup_notes?: string;
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
  custom_whatsapp: string | null;
  custom_cpf: string | null;
  custom_rg: string | null;
  custom_nao_possui_cpf: boolean;
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
  photo_url: string | null;
  registration_date: string;
  modified: string;
}

export interface CustomerDeviceListResponse {
  items: CustomerDeviceSummary[];
  count: number;
  fields: string[];
}

export interface CreateCustomerDevicePayload {
  customer: string;
  brand: string;
  model: string;
  color?: string;
  imei_serial: string;
  capacity?: string;
  general_state?: string;
  photo?: {
    data_url: string;
    filename: string;
  } | null;
}

export interface CreateCustomerDeviceResponse {
  item: CustomerDeviceSummary;
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
