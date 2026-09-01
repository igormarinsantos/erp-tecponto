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
	UnassignedServiceOrderResponse,
	ServiceOrderPaymentPayload,
	ServiceOrderPaymentResponse,
	ServiceOrderTradeinCandidate,
  TrackingLinkResponse,
	TechnicalBudgetCatalogItem,
	TechnicalBudgetResponse,
  QuotesCrmResponse,
} from "./types";

const API = "tecponto_app.tecponto.frontend.api";
const TRACKING_API = "tecponto_app.tecponto.tracking";
const TECHNICAL_BUDGET_API = "tecponto_app.tecponto.technical_budget";

export interface ServiceOrderQueryParams extends Record<string, string | number | boolean | undefined> {
  from_date?: string;
  in_progress?: boolean;
  limit?: number;
  query?: string;
  status?: string;
  to_date?: string;
}

export const serviceOrders = {
	convertFast(name: string, reason: string, newValue: number, notes = "") {
		return rpc<ServiceOrderDetailResponse>(`${API}.convert_fast_service_order`, { body: { name, reason, new_value: newValue, notes } });
	},
	technicalBudget(name: string) {
		return rpc<TechnicalBudgetResponse>(`${TECHNICAL_BUDGET_API}.get_budget`, { query: { name } });
	},
	searchTechnicalBudgetServices(query = "") {
		return rpc<{ items: TechnicalBudgetCatalogItem[]; count: number }>(`${TECHNICAL_BUDGET_API}.search_services`, { query: { query } });
	},
	searchTechnicalBudgetParts(query = "") {
		return rpc<{ items: TechnicalBudgetCatalogItem[]; count: number; warehouse: string }>(`${TECHNICAL_BUDGET_API}.search_parts`, { query: { query } });
	},
	addTechnicalBudgetLine(name: string, payload: Record<string, unknown>) {
		return rpc<TechnicalBudgetResponse>(`${TECHNICAL_BUDGET_API}.add_line`, { body: { name, payload } });
	},
	updateTechnicalBudgetLine(name: string, lineType: BudgetLineType, lineName: string, payload: Record<string, unknown>) {
		return rpc<TechnicalBudgetResponse>(`${TECHNICAL_BUDGET_API}.update_line`, { body: { name, line_type: lineType, line_name: lineName, payload } });
	},
	removeTechnicalBudgetLine(name: string, lineType: BudgetLineType, lineName: string) {
		return rpc<TechnicalBudgetResponse>(`${TECHNICAL_BUDGET_API}.remove_line`, { body: { name, line_type: lineType, line_name: lineName } });
	},
	completeTechnicalBudget(name: string) {
		return rpc<TechnicalBudgetResponse>(`${TECHNICAL_BUDGET_API}.complete_budget`, { body: { name } });
	},
	technicalBudgetPrint(name: string) {
		return rpc<{ html: string }>(`${TECHNICAL_BUDGET_API}.get_print_html`, { query: { name } });
	},
	exportTechnicalBudget(name: string) {
		return rpc<{ filename: string; content: string }>(`${TECHNICAL_BUDGET_API}.export_budget`, { query: { name } });
	},
	listUnassigned(limit = 100) {
		return rpc<UnassignedServiceOrderResponse>(`${API}.list_unassigned_service_orders`, { query: { limit } });
	},
	claim(name: string) {
		return rpc<{ service_order: string; technician: string; event: string }>(`${API}.claim_service_order`, { body: { name } });
	},
	assign(name: string, technician: string, observation = "") {
		return rpc<{ service_order: string; technician: string; event: string }>(`${API}.assign_service_order`, { body: { name, technician, observation } });
	},
	transfer(name: string, technician: string, observation: string) {
		return rpc<{ service_order: string; technician: string; event: string }>(`${API}.transfer_service_order`, { body: { name, technician, observation } });
	},
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
	updateEntry(name: string, payload: Record<string, string>) {
		return rpc<ServiceOrderDetailResponse>(`${API}.update_service_order_entry`, { body: { name, payload } });
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
  removeBudgetLine(name: string, lineName: string, lineType: "service" | "part" = "service") {
    return rpc<ServiceOrderDetailResponse>(`${API}.remove_service_order_budget_line`, {
      body: { name, line_name: lineName, line_type: lineType },
    });
  },
  updateBudgetPresentation(name: string, presentation: "Discriminado" | "Fechado") {
    return rpc<ServiceOrderDetailResponse>(`${API}.update_service_order_budget_presentation`, {
      body: { name, presentation },
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
	completeDiagnosis(name: string, problemFound: string, pricingResponsibility: "Técnico" | "Balcão") {
		return rpc<ServiceOrderDetailResponse>(`${API}.complete_technical_diagnosis`, {
			body: { name, problem_found: problemFound, pricing_responsibility: pricingResponsibility },
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
  recordFollowUp(name: string, channel: string, result: string, notes = "") {
    return rpc<ServiceOrderDetailResponse>(`${API}.record_quote_follow_up`, {
      body: { name, channel, result, notes },
    });
  },
  quotesCrm(params: { status?: string; channel?: string; query?: string; limit?: number; in_progress?: boolean; from_date?: string; to_date?: string } = {}) {
    return rpc<QuotesCrmResponse>(`${API}.get_quotes_crm_panel`, {
      query: params,
    });
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
