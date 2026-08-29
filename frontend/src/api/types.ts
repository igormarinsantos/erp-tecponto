export type RolePanel = "atendente" | "tecnico" | "gestor" | "diretor" | "sem_papel";
export type NavigationTarget =
  | "overview"
  | "mesa-flow"
  | "service-orders"
  | "service-order-detail"
  | "customers"
  | "devices"
  | "services"
  | "service-categories"
  | "defect-service-mapping"
  | "trade-ins"
  | "parts-stock"
  | "repair-parts"
  | "part-requests"
  | "my-earnings"
  | "commercial-products"
  | "product-attributes"
  | "product-categories"
  | "used-devices"
  | "pos"
  | "cash-statement"
  | "sales"
  | "approval-requests"
  | "notifications"
  | "user-management"
  | "administration"
  | "administration-settings";

export interface ProductCategoryNode {
  name: string;
  parent: string;
  is_group: boolean;
  active: boolean;
  sell_online: boolean;
  children: ProductCategoryNode[];
}

export interface DefectServiceMapping {
  name: string;
  defect: string;
  catalog_service: string;
  catalog_service_label: string;
  active: boolean;
  modified: string;
}

export interface OwnEarningItem {
  service_order: string;
  service_name: string;
  value: number;
  date: string;
  payment_status: string;
}

export interface OwnEarningsResponse {
  items: OwnEarningItem[];
  count: number;
  total: number;
  period: string;
}

export interface TechnicalPartRequest {
  name: string;
  service_order: string;
  item: string | null;
  free_description: string | null;
  qty: number;
  notes: string | null;
  requested_by: string;
  requested_at: string;
  status: "Solicitada" | "Pedida" | "Recebida" | "Cancelada";
  modified: string;
}

export interface TechnicalPartRequestResponse {
  items: TechnicalPartRequest[];
  count: number;
}

export interface PurchasePartRequest extends TechnicalPartRequest {
  supplier: string | null;
  expected_arrival: string;
  received_at: string;
  received_item: string | null;
  stock_entry: string | null;
  reservation: string | null;
  estimated_cost: number;
  cancellation_reason: string | null;
  customer: string | null;
  technician: string | null;
  service_order_state: string | null;
  service_order_deadline: string;
  is_late: boolean;
}

export interface PurchasePartRequestResponse {
  items: PurchasePartRequest[];
  count: number;
  statbar: Array<{ key: string; label: string; value: number }>;
}

export interface RepairPartOption {
  item_code: string;
  item_name: string;
  item_group: string;
}

export interface RepairPartOptionsResponse {
  items: RepairPartOption[];
  count: number;
}

export interface ProductCategoryTreeResponse {
  items: ProductCategoryNode[];
}

export interface ProductCategorySavePayload {
  name: string;
  original_name?: string;
  parent: string;
  is_group: boolean;
  sell_online: boolean;
  active: boolean;
}

export interface ProductVariantAttributeValue {
  abbreviation: string;
  value: string;
}

export interface ProductVariantAttribute {
  disabled: boolean;
  name: string;
  values: ProductVariantAttributeValue[];
}

export interface ProductVariantSummary {
  attributes: Record<string, string>;
  available_qty: number;
  gtin: string | null;
  item_code: string;
  item_name: string;
  price: number;
  sku: string;
}

export interface ProductVariantTemplate {
  attributes: string[];
  disabled: boolean;
  item_code: string;
  item_group: string;
  item_name: string;
  variants?: ProductVariantSummary[];
}

export interface ProductVariantCreatePayload {
  attributes: Array<{ name: string }>;
  item_group: string;
  stock_uom?: string;
  template_code: string;
  template_name: string;
  variants: Array<{
    attributes: Record<string, string>;
    gtin: string;
    price: number;
    sku: string;
  }>;
}

export interface ListingImage {
  image: string;
  caption: string;
}

export interface CommercialCatalogItem {
  item_code: string;
  item_name: string;
  catalog_kind: "shelf" | "unique" | null;
  variant_of: string | null;
  sku: string;
  gtin: string | null;
  public_price: number;
  available_qty: number | null;
  serial_suffix: string | null;
  online_sellable: boolean;
  listing_title: string;
  listing_description: string;
  condition: string;
  grade: string;
  weight_per_unit: number;
  package_length_cm: number;
  package_width_cm: number;
  package_height_cm: number;
  images: ListingImage[];
}

export interface ListingMetadataPayload {
  online_sellable: boolean;
  listing_title: string;
  listing_description: string;
  condition: string;
  grade: string;
  public_price: number;
  weight_per_unit: number;
  package_length_cm: number;
  package_width_cm: number;
  package_height_cm: number;
  images: ListingImage[];
}

export interface LoggedUser {
  name: string;
  full_name: string;
  initials: string;
  roles: string[];
  panel: RolePanel;
  role_label: string;
  role_name: string;
  subtitle: string;
  can_manage_users: boolean;
}

export interface UserRoleOption {
  role: string;
  allowed: boolean;
  reason: string;
}

export interface ManagedUserAccount {
  name: string;
  full_name: string;
  email: string;
  enabled: boolean;
  last_login: string;
  roles: string[];
  business_roles: string[];
  account_level: string;
  discount_limit: number;
  cashier: {
    enabled: boolean;
    badge_code: string;
    has_pin: boolean;
  };
}

export interface UserAccountListResponse {
  items: ManagedUserAccount[];
  stats: { total: number; active: number; administrators: number; operational: number };
  role_options: UserRoleOption[];
  actor: { name: string; account_level: string };
}

export interface UserAccountPayload {
  name?: string;
  email?: string;
  full_name: string;
  enabled: boolean;
  roles: string[];
  discount_limit: number;
  cashier?: { enabled: boolean; badge_code: string; pin?: string };
}

export interface AdministrativeSalesReport {
  period: { key: "today" | "7d" | "month"; label: string; from_date: string; to_date: string };
  totals: {
    invoices: number;
    gross_sales: number;
    returns: number;
    net_sales: number;
    payment_entries: number;
    cash_movements: number;
  };
  categories: Array<{ category: string; revenue: number; quantity: number }>;
  payment_methods: Array<{ payment_mode: string; amount: number; affects_drawer: boolean }>;
}

export interface AdministrationStageSla { name: string; workflow_state: string; business_hours: number; description: string; active: boolean; }
export interface AdministrationCardFee { tipo: string; taxa_pct: number; settlement_days: number; }
export interface AdministrationSettings {
  identity: CompanyIdentity & { company_name: string; tax_id: string; trade_name: string; public_phone: string; public_email: string; public_address: string; public_logo: string; };
  operation: Record<string, boolean | number | string | null>;
  card_fees: AdministrationCardFee[];
  stage_slas: AdministrationStageSla[];
}

export interface BootResponse {
  user: LoggedUser;
  identity: CompanyIdentity;
  features: {
		pillars: {
			repair: boolean;
			buy: boolean;
			tradein: boolean;
		};
		technician_assignment: { mode: "Pull" | "Dispatch"; alert_hours: number };
    technician_commissions_enabled: boolean;
		diagnostic_fee: { enabled: boolean; amount: number };
		storage_fee: { enabled: boolean; amount: number; start_days: number; abandonment_days: number };
		diagnosis_only_enabled: boolean;
		payments: { advance_enabled: boolean; installments_enabled: boolean; device_tradein_enabled: boolean };
		default_warranty_days: number;
    active_operational_users: number;
    active_technicians: number;
    single_operator: boolean;
    single_technician: boolean;
  };
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

export interface CompanyIdentity {
  company: string;
  legal_name: string;
  display_name: string;
  cnpj: string;
  address: string;
  phone: string;
  email: string;
  logo_url: string;
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

export interface NotificationHistoryResponse extends NotificationListResponse {
  has_more: boolean;
  total: number;
}

export interface NotificationHistoryFilters {
  from_date?: string;
  limit?: number;
  notification_type?: string;
  period?: "all" | "today" | "7d" | "30d" | "custom";
  read_state?: "all" | "unread" | "read";
  start?: number;
  to_date?: string;
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

export interface AgendaCalendarEvent {
  key: string;
  date: string;
  kind: "delivery" | "pickup" | "task";
  title: string;
  description: string;
  reference_doctype: string | null;
  reference_name: string | null;
}

export interface AgendaCalendarResponse {
  items: AgendaCalendarEvent[];
  start_date: string;
  end_date: string;
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
  workflow_blockers: Record<string, string>;
  workflow_requestable_transitions: string[];
  has_sales_invoice: boolean;
  next_action?: { label: string; tone: "orange" | "amber" | "blue" | "green" | "muted" };
  reported_defect: string | null;
  approval_status: string | null;
  approval_deadline: string;
  modified: string;
	unassigned_waiting_hours?: number;
	unassigned_overdue?: boolean;
}

export interface UnassignedServiceOrderResponse {
	items: ServiceOrderSummary[];
	count: number;
	mode: "Pull" | "Dispatch";
	alert_hours: number;
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
    expired: boolean;
  };
  entry_date: string;
  modified: string;
  attendant: string | null;
  technician: string | null;
  priority: string | null;
  technical_view: boolean;
  customer: ServiceOrderCustomerDetail | null;
  device: ServiceOrderDeviceDetail | null;
  reported_defect: string | null;
  physical_state: string | null;
  entry_operating_condition: string | null;
  accessories_received: string | null;
  diagnosis: {
    problem_found: string | null;
    diagnosis_date: string;
    diagnosis_deadline: string;
  };
  services: ServiceOrderBudgetLine[];
  parts: ServiceOrderBudgetLine[];
	budget: {
		presentation: "Fechado" | "Discriminado";
		closed_lines: Array<{ description: string; amount: number }>;
		customer_supplied_part_term_required: boolean;
	};
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
		without_repair: boolean;
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
		total_due: number;
		paid_total: number;
		remaining_total: number;
		payments: ServiceOrderPayment[];
		options: { advance: boolean; installments: boolean; tradein: boolean; diagnostic_fee: boolean; storage_fee: boolean };
  };
  workflow_actions: ServiceOrderWorkflowAction[];
  workflow_transitions: ServiceOrderWorkflowAction[];
  workflow_blockers: Record<string, string>;
  workflow_requestable_transitions: string[];
  timeline: ServiceOrderTimelineEvent[];
  print_links: ServiceOrderPrintLink[];
}

export interface ServiceOrderPayment {
	name: string;
	kind: string;
	direction: "Entrada" | "Saída";
	amount: number;
	payment_mode: string | null;
	affects_drawer: boolean;
	payment_entry: string | null;
	cash_movement: string | null;
	source_doctype: string | null;
	source_name: string | null;
	reason: string | null;
	created_at: string;
}

export interface ServiceOrderPaymentPayload {
	kind: "regular" | "advance" | "installment" | "diagnostic_fee" | "storage_fee" | "tradein" | "cancellation_adjustment";
	amount: number;
	mode_of_payment?: string;
	direction?: "Entrada" | "Saída";
	reason?: string;
	trade_evaluation?: string;
	idempotency_key: string;
}

export interface ServiceOrderPaymentResponse {
	payment: ServiceOrderPayment & { idempotent_replay: boolean };
	detail: ServiceOrderDetailResponse;
}

/** Confidential projection returned only by the Director-gated endpoint. */
export interface ServiceOrderDirectorFinancialSummary {
	service_order: string;
	revenue: number;
	part_cost: number;
	labor_cost_provisioned: number;
	total_cost: number;
	gross_profit: number;
	gross_margin_pct: number;
	net_profit_available: boolean;
}

export interface ServiceOrderTradeinCandidate {
	name: string;
	label: string;
	amount: number;
	status: string | null;
}

export interface ServiceOrderBudgetLine {
	name?: string | null;
	item_code: string | null;
  description: string | null;
  qty: number;
  unit_price?: number;
  amount?: number;
  catalog_service?: string | null;
  service_duration?: number;
  duration_unit?: "Horas" | "Dias úteis";
  technician?: string | null;
  warehouse?: string | null;
  outcome?: string | null;
	loss_reason?: string | null;
	reservation?: string | null;
	stock_entry?: string | null;
	used_date?: string | null;
	part_source?: "Loja" | "Cliente";
	service_row?: string | null;
	customer_part_note?: string | null;
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
  customer?: string;
  discount_amount: number;
  idempotency_key: string;
  items: Array<{
    item_code: string;
    qty: number;
    serial_no?: string | null;
  }>;
  payments: PosSalePaymentPayload[];
}

export interface CashSessionSummary {
	business_date: string;
	cash_point: string;
	drawer_balance: number;
	movement_count: number;
	opened_at: string;
	opened_by: string;
	opening_amount: number;
	session: string;
	status: "Aberto" | "Fechado";
	closed_at?: string | null;
	closed_by?: string | null;
	closing_counted_drawer?: number;
	closing_drawer_difference?: number;
	closing_expected_drawer?: number;
	closing_reason?: string | null;
}

export interface CashPaymentTotal {
  payment_mode: string;
  expected_amount: number;
  affects_drawer: boolean;
}

export interface CashStatementMovement {
  movement: string;
  movement_type: string;
  direction: "Entrada" | "Saída";
  amount: number;
  payment_mode: string;
  affects_drawer: boolean;
  occurred_on: string;
  registered_by: string;
  reason: string | null;
  reference_doctype: string | null;
  reference_name: string | null;
}

export interface CashStatementResponse {
  session: CashSessionSummary | null;
  drawer_balance: number;
  payment_totals: CashPaymentTotal[];
  movements: CashStatementMovement[];
}

export interface CashSessionHistoryEntry {
  session: string;
  business_date: string;
  status: "Aberto" | "Fechado";
  opened_by: string;
  opened_at: string;
  closed_by?: string | null;
  closed_at?: string | null;
  opening_amount: number;
  drawer_balance: number;
  turnover: number;
  net_flow: number;
  closing_expected_drawer: number;
  closing_counted_drawer: number;
  closing_drawer_difference: number;
}

export interface CashSessionHistoryResponse {
  sessions: CashSessionHistoryEntry[];
}

export interface CashClosingCount {
  payment_mode: string;
  expected_amount: number;
  counted_amount: number;
  difference: number;
}

export interface CashClosingResponse extends CashSessionSummary {
  closing: {
    closed_by: string | null;
    closed_at: string | null;
    reason: string | null;
    counts: CashClosingCount[];
  };
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
  item_code?: string;
  description?: string;
	part_source?: "Loja" | "Cliente";
	service_row?: string;
	customer_part_note?: string;
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
    defects?: string[];
    physical_state: string;
    attendance_notes?: string;
    entry_operating_condition?: "Liga e permite teste" | "Liga parcialmente" | "Não liga / sem condições de teste";
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
  mapped_services: Array<{
    name: string;
    service_name: string;
    default_labor_price: number;
    default_duration: number;
    duration_unit: "Horas" | "Dias úteis";
  }>;
  has_estimate: boolean;
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
  sales_tickets: {
    retail: { count: number; total: number; average: number | null };
    service_order: { count: number; total: number; average: number | null };
  };
	/** False when the backend intentionally withholds sales for a technical-only account. */
	sales_visible: boolean;
  service_orders: {
    total: number;
    in_diagnosis: number;
    awaiting_approval: number;
    ready_for_pickup: number;
    waiting_part: number;
    ready_for_test: number;
    new_today: number;
    overdue: number;
  };
}

export interface DirectorFinancialSummary {
  period: { key: "today"; label: string; date: string };
  revenue: number;
  operational_cost: number;
  retail_cost: number;
  service_part_cost: number;
  gross_operating_profit: number;
  gross_margin_pct: number;
  team_earnings_accrued: number;
	technician_commissions_enabled: boolean;
  net_profit_available: false;
}

export interface DirectorStrategicReport {
  period: { key: "7d" | "month"; label: string; from_date: string; to_date: string };
  technician_commissions_enabled: boolean;
  categories: Array<{ category: string; revenue: number }>;
  technicians: Array<{ technician: string; service_orders: number; labor_revenue: number; team_earnings: number }>;
  item_costs: Array<{ item_code: string; item_name: string; cost: number }>;
  service_order_costs: Array<{ service_order: string; cost: number }>;
  trend: Array<{ date: string; revenue: number }>;
}

export interface DirectorRiskAgenda {
  items: DailyAction[];
  count: number;
  risk_count: number;
}

export interface TechnicianWorkloadItem {
  technician: string;
  technician_name: string;
  active_orders: number;
  in_diagnosis: number;
  waiting_part: number;
  overdue: number;
}

export interface TechnicianWorkloadResponse {
  items: TechnicianWorkloadItem[];
  count: number;
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

export interface SaleReturnLine {
	item_code: string;
	item_name: string;
	qty: number;
	returned_qty: number;
	available_qty: number;
	unit_price: number;
}

export interface SalePostSaleDetail {
	name: string;
	customer: string | null;
	posting_date: string;
	grand_total: number;
	payments: Array<{ mode_of_payment: string; amount: number }>;
	items: SaleReturnLine[];
}

export interface SalesReturnResponse {
	return_invoice: string;
	return_against: string;
	grand_total: number;
	idempotent_replay: boolean;
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

export type RegistryKind = "customer" | "device" | "repair_part" | "product";

export interface RegistryAddress {
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  pincode?: string;
}

export interface RegistryCustomerRecord extends CustomerSummary {
  address: RegistryAddress;
}

export interface RegistryDeviceRecord extends CustomerDeviceSummary {
  general_state: string;
}

export interface RegistryItemRecord {
  item_code: string;
  item_name: string | null;
  item_group: string | null;
  model: string;
  compatible_models: string;
  part_type: string;
  selling_rate: number;
  barcode: string | null;
  valuation_rate?: number;
  kind: "repair_part" | "product";
}

export type RegistryRecord = RegistryCustomerRecord | RegistryDeviceRecord | RegistryItemRecord;

export interface RegistryRecordResponse {
  item: RegistryRecord;
  can_edit?: boolean;
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
	suggested_value: number;
	approved_value: number;
	table_max: number;
	workflow_state: string | null;
	created_item: string | null;
	trade_category: string | null;
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

export interface CreateTradeEvaluationPayload {
	customer: string;
	device_type: "iPhone" | "Android";
	evaluated_device_desc?: string;
	model: string;
	imei: string;
	capacity?: string;
	physical_state: "A" | "B" | "C" | "Sucata";
	destination: "Venda" | "Peças" | "Descarte";
	suggested_value: number;
	table_min?: number;
	table_max?: number;
	icloud_google_lock?: boolean;
	has_invoice?: boolean;
	defects?: string;
}

export interface TradeOutputDevice {
	name: string;
	serial_no: string;
	item_code: string;
	item_name: string;
}

export interface TradeOutputDeviceListResponse {
	items: TradeOutputDevice[];
	count: number;
}

export interface TradeInOperationSummary {
	name: string;
	evaluation: string;
	device_out: string;
	difference: number;
	atomic_status: string;
	used_device_fiscal_ref: string | null;
	sale_fiscal_ref: string | null;
}

export interface CompleteTradeBuybackResponse {
	item: TradeEvaluationSummary;
	created_item: string | null;
}

export interface ConfirmTradeInOperationResponse {
	operation: TradeInOperationSummary;
	evaluation: TradeEvaluationSummary;
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
