import { rpc } from "./client";
import type {
  BudgetItemSearchResponse,
  CatalogServiceBudgetPayload,
  BudgetLinePayload,
  BudgetLineType,
  BudgetWarehouseListResponse,
  BudgetDecisionPayload,
  PickupPayload,
  QuoteSendPayload,
	ServiceOrderDetailResponse,
	ServiceOrderDirectorFinancialSummary,
  ServiceOrderKanbanResponse,
  ServiceOrderListResponse,
  ServiceOrderStatBarResponse,
  ServiceOrderMoveResponse,
	ServiceOrderPaymentPayload,
	ServiceOrderPaymentResponse,
	ServiceOrderTradeinCandidate,
  TrackingLinkResponse,
} from "./types";

const API = "tecponto_app.tecponto.frontend.api";
const TRACKING_API = "tecponto_app.tecponto.tracking";

export interface ServiceOrderQueryParams extends Record<string, string | number | boolean | undefined> {
  from_date?: string;
  limit?: number;
  query?: string;
  status?: string;
  to_date?: string;
}

export const serviceOrders = {
  statBar() {
    return rpc<ServiceOrderStatBarResponse>(`${API}.get_service_order_statbar`);
  },
  list(params: number | ServiceOrderQueryParams = 20) {
    const query = typeof params === "number" ? { limit: params } : params;
    return rpc<ServiceOrderListResponse>(`${API}.list_service_orders`, {
      query,
    });
  },
  kanban(limitPerColumn = 18, filters: ServiceOrderQueryParams = {}) {
    return rpc<ServiceOrderKanbanResponse>(`${API}.get_service_order_kanban`, {
      query: { ...filters, limit_per_column: limitPerColumn },
    });
  },
  detail(name: string) {
    return rpc<ServiceOrderDetailResponse>(`${API}.get_service_order_detail`, {
      query: { name },
    });
  },
	directorFinancialSummary(name: string) {
		return rpc<ServiceOrderDirectorFinancialSummary>(`${API}.get_service_order_director_financial_summary`, {
			query: { name },
		});
	},
  searchBudgetItems(query: string, lineType: BudgetLineType) {
    return rpc<BudgetItemSearchResponse>(`${API}.search_budget_items`, {
      query: { line_type: lineType, query },
    });
  },
  listBudgetWarehouses(query = "") {
    return rpc<BudgetWarehouseListResponse>(`${API}.list_budget_warehouses`, {
      query: { query },
    });
  },
  addBudgetLine(name: string, payload: BudgetLinePayload) {
    return rpc<ServiceOrderDetailResponse>(`${API}.add_service_order_budget_line`, {
      body: { name, payload },
    });
  },
  addCatalogService(name: string, catalogService: string, payload: CatalogServiceBudgetPayload) {
    return rpc<ServiceOrderDetailResponse>(`${API}.add_catalog_service_to_service_order`, {
      body: { name, catalog_service: catalogService, payload },
    });
  },
  sendQuote(name: string, payload: QuoteSendPayload) {
    return rpc<ServiceOrderDetailResponse>(`${API}.send_service_order_quote`, {
      body: { name, payload },
    });
  },
  move(name: string, targetState: string) {
    return rpc<ServiceOrderMoveResponse>(`${API}.move_service_order`, {
      body: { name, target_state: targetState },
    });
  },
  saveDiagnosis(name: string, problemFound: string) {
    return rpc<ServiceOrderDetailResponse>(`${API}.save_technical_diagnosis`, {
      body: { name, problem_found: problemFound },
    });
  },
  setPartOutcome(name: string, partName: string, outcome: "Usada no reparo" | "Perdida", lossReason = "") {
    return rpc<ServiceOrderDetailResponse>(`${API}.set_service_order_part_outcome`, {
      body: { name, part_name: partName, outcome, loss_reason: lossReason },
    });
  },
  decideBudget(name: string, payload: BudgetDecisionPayload) {
    return rpc<ServiceOrderDetailResponse>(`${API}.decide_service_order_budget`, {
      body: { name, payload },
    });
  },
  completePickup(name: string, payload: PickupPayload) {
    return rpc<ServiceOrderDetailResponse>(`${API}.complete_service_order_pickup`, {
      body: { name, payload },
    });
  },
  preparePickup(name: string, payload: PickupPayload) {
    return rpc<ServiceOrderDetailResponse>(`${API}.prepare_service_order_pickup`, {
      body: { name, payload },
    });
  },
	collectPayment(name: string, payload: ServiceOrderPaymentPayload) {
		return rpc<ServiceOrderPaymentResponse>(`${API}.receive_service_order_payment`, { body: { name, payload } });
	},
	tradeinCandidates(name: string) {
		return rpc<{ items: ServiceOrderTradeinCandidate[] }>(`${API}.list_service_order_tradein_candidates`, { query: { name } });
	},
  issueTrackingLink(name: string) {
    return rpc<TrackingLinkResponse>(`${TRACKING_API}.issue_service_order_tracking_link`, {
      body: { service_order: name },
    });
  },
};
