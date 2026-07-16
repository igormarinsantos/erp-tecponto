export type RolePanel = "atendente" | "tecnico" | "gestor" | "diretor" | "sem_papel";
export type NavigationTarget =
  | "overview"
  | "service-orders"
  | "service-order-detail"
  | "customers"
  | "devices"
	| "services"
  | "trade-ins"
  | "parts-stock"
  | "repair-parts"
  | "commercial-products"
  | "used-devices"
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

export interface TecpontoNotification {
  name: string;
  type: string;
  title: string;
  body: string;
  link: string;
  reference_doctype: string | null;
  reference_name: string | null;
  is_read: boolean;
  read_at: string;
  creation: string;
}

export interface NotificationListResponse {
  items: TecpontoNotification[];
  unread_count: number;
}

export interface DailyAction {
  key: string;
  kind: "derived";
  title: string;
  description: string;
  urgency: "overdue" | "due_today" | "scheduled" | "high" | "normal" | "low";
  urgency_sort_at?: string;
  group_key?: string;
  group_label?: string;
  link: string;
  reference_doctype: string | null;
  reference_name: string | null;
  tone: "orange" | "amber" | "blue" | "green" | "muted";
}

export interface TecpontoTask {
  name: string;
  title: string;
  due_date: string;
  reference_doctype: string | null;
  reference_name: string | null;
  status: "Aberta" | "Concluida";
  kind?: "manual";
  urgency?: "overdue" | "due_today" | "scheduled" | "high" | "normal" | "low";
  urgency_sort_at?: string;
  group_key?: string;
  group_label?: string;
}

export interface DailyActionsResponse {
  derived: DailyAction[];
  manual: TecpontoTask[];
  items: Array<DailyAction | TecpontoTask>;
  count: number;
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
  stage_clock?: {
    stage_entered_at: string;
    stage_sla_business_hours: number;
    stage_deadline: string;
    estimated_deadline: string;
    is_stage_overdue: boolean;
    is_total_overdue: boolean;
    is_overdue: boolean;
    urgency: "overdue" | "normal";
  };
  workflow_transitions: ServiceOrderWorkflowAction[];
  next_action?: { label: string; tone: "orange" | "amber" | "blue" | "green" | "muted" };
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

export interface AcceptanceIssueResponse {
  acceptance: string;
  acceptance_type: "Entrada" | "Retirada";
  expires_on: string;
  link: string;
  qr_svg: string;
}

export interface StockTransferSummary {
  name: string;
  item_code: string | null;
  qty: number;
  source_warehouse: string;
  target_warehouse: string;
  docstatus: number;
}

export interface StockTransferResponse {
  item: StockTransferSummary;
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
  workflow_transitions: ServiceOrderWorkflowAction[];
  timeline: ServiceOrderTimelineEvent[];
  print_links: ServiceOrderPrintLink[];
}

export interface ServiceOrderBudgetLine {
  item_code: string | null;
  description: string | null;
  qty: number;
  unit_price: number;
  amount: number;
  catalog_service?: string | null;
  service_duration?: number;
  duration_unit?: "Horas" | "Dias úteis";
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
	 cashier_operator_token?: string;
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

export interface CashierOperatorIdentity {
  operator: string;
  operator_name: string;
  token: string;
  via: "badge" | "pin";
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

export interface CatalogServiceBudgetPayload {
  description?: string;
  duration?: number;
  duration_unit?: "Horas" | "Dias úteis";
  qty?: number;
  rate?: number;
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
    is_warranty?: boolean;
    original_service_order?: string;
    estimated_deadline?: string;
    lead_time_business_hours?: number;
  };
  entry_photo: {
    data_url: string;
    filename: string;
  };
  entry_signature?: string;
}

export interface ServiceOrderStatBarResponse {
  items: Array<{ key: string; label: string; value: number }>;
}

export interface WarrantyCandidate {
  name: string;
  reported_defect: string | null;
  pickup_date: string;
  warranty_expiry: string;
}

export interface WarrantyCandidateResponse {
  items: WarrantyCandidate[];
}

export interface CheckinResponse {
  service_order: Pick<ServiceOrderDetailResponse, "name" | "workflow_state" | "customer" | "device" | "print_links">;
  entry_photo_url: string;
  tracking: TrackingLinkResponse;
}

export interface DeliverySuggestion {
  suggested_delivery_date: string;
  total_business_hours: number;
  stage_business_hours: number;
  service_business_hours: number;
  lead_time_business_hours: number;
}

export interface TrackingLinkResponse {
  tracking: string;
  link: string;
  qr_svg: string;
  expires_on: string;
}

export interface BudgetDecisionPayload {
  decision: "approve" | "reject";
  channel: "Presencial" | "Telefone" | "WhatsApp";
  notes?: string;
}

export interface PickupPayload {
  third_party: boolean;
  picked_up_by?: string;
  picked_up_doc?: string;
  third_party_auth?: string;
  pickup_notes?: string;
  acceptance_name?: string;
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

export interface ListStatBarResponse { items: Array<{ key: string; label: string; value: number; amount?: number }>; }

export interface SaleSummary {
  name: string;
  customer: string | null;
  posting_date: string;
  grand_total: number;
  status: string | null;
  modified: string;
}

export interface SaleListResponse {
  items: SaleSummary[];
  count: number;
  fields: string[];
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

export interface CreateCustomerPayload {
  customer_name: string;
  mobile_no: string;
  custom_whatsapp?: string;
  custom_cpf?: string;
  custom_rg?: string;
  custom_nao_possui_cpf?: boolean;
  email_id?: string;
}

export interface CreateCustomerResponse {
  item: CustomerSummary;
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

export interface ServiceCatalogReference {
  name: string;
  value: string;
  active: boolean;
  modified: string;
}

export interface ServiceCatalogReferenceResponse {
  device_types: ServiceCatalogReference[];
  categories: ServiceCatalogReference[];
}

export interface ServiceCatalogService {
  name: string;
  service_name: string;
  device_type: string;
  device_type_label?: string;
  category: string;
  category_label?: string;
  default_labor_price: number;
  default_duration: number;
  duration_unit: "Horas" | "Dias úteis";
  requires_part: boolean;
  complexity: "Baixa" | "Média" | "Alta" | null;
  active: boolean;
  modified: string;
}

export interface ServiceCatalogServicesResponse {
  items: ServiceCatalogService[];
  count: number;
}

export interface ServiceCatalogServiceResponse {
  item: ServiceCatalogService;
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
	approved_value: number;
	table_max: number;
  workflow_state: string | null;
  modified: string;
}

export interface SetTradeInApprovedValueResponse {
  item: TradeEvaluationSummary;
}

export interface TradeEvaluationListResponse {
  items: TradeEvaluationSummary[];
  count: number;
  fields: string[];
}

export interface StockItemSummary {
	barcode: string | null;
	has_serial_no: boolean;
	is_commercial_item: boolean;
  item_code: string;
  item_name: string | null;
  item_group: string | null;
  warehouse: string | null;
  available_qty: number;
}

export interface PosBarcodeLabelResponse {
  barcode: string;
  created: boolean;
  item_code: string;
  item_name: string;
  label: {
    format: string;
    url: string;
  };
}

export type RetailBarcodeSource = "Fabricante" | "Interno Tecponto";

export interface RetailBarcodeLookupResponse {
  barcode: string;
  barcode_source?: RetailBarcodeSource | null;
  state: "found" | "unknown" | "disabled";
  item?: {
    has_serial_no: boolean;
    item_code: string;
    item_group: string;
    item_name: string;
    standard_rate: number;
    stock_uom: string;
  };
}

export interface RetailItemGroupResponse {
  items: Array<{ name: string }>;
}

export interface RetailProductRegistrationPayload {
  barcode?: string;
  barcode_source: RetailBarcodeSource;
  item_code: string;
  item_group: string;
  item_name: string;
  selling_rate: number;
  stock_uom: string;
}

export interface RetailProductRegistrationResponse {
  barcode: string;
  barcode_source: RetailBarcodeSource;
  item: {
    has_serial_no: boolean;
    item_code: string;
    item_group: string;
    item_name: string;
    standard_rate: number;
    stock_uom: string;
  };
  label: {
    format: string;
    url: string;
  };
}

export interface RetailStockReceiptPayload {
  incoming_rate: number;
  item_code: string;
  qty: number;
}

export interface RetailStockReceiptResponse {
  item_code: string;
  qty_after: number;
  qty_before: number;
  qty_received: number;
  stock_entry: string;
  warehouse: string;
}

export interface StockItemListResponse {
  items: StockItemSummary[];
  count: number;
  fields: string[];
}
