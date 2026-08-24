import { rpc } from "./client";
import type {
	AcceptanceIssueResponse,
	CreateCustomerPayload,
	CreateCustomerResponse,
  CreateCustomerDevicePayload,
  CreateCustomerDeviceResponse,
  CustomerDeviceListResponse,
  CustomerSearchResponse,
  DashboardMetrics,
  DirectorFinancialSummary,
  DirectorStrategicReport,
	DirectorRiskAgenda,
  ListStatBarResponse,
	TechnicianWorkloadResponse,
	SaleListResponse,
	SalePostSaleDetail,
	SalesReturnResponse,
  StockItemListResponse,
	StockTransferResponse,
	TradeEvaluationListResponse,
	TradeEvaluationSummary,
	SetTradeInApprovedValueResponse,
	CreateTradeEvaluationPayload,
	CompleteTradeBuybackResponse,
	ConfirmTradeInOperationResponse,
	TradeOutputDeviceListResponse,
} from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const balcao = {
  getListStatBar(scope: string) {
    return rpc<ListStatBarResponse>(`${API}.get_list_statbar`, { query: { scope } });
  },
	listSales(query = "", limit = 50, period = "today") {
		return rpc<SaleListResponse>(`${API}.list_sales`, { query: { query, limit, period } });
	},
	getSalePostSaleDetail(name: string) {
		return rpc<SalePostSaleDetail>(`${API}.get_sale_post_sale_detail`, { query: { name } });
	},
	createSalesReturn(payload: { invoice: string; items: Array<{ item_code: string; qty: number }> }) {
		return rpc<SalesReturnResponse>(`${API}.create_sales_return`, { body: { payload } });
	},
	exchangeSalesProduct(payload: { invoice: string; items: Array<{ item_code: string; qty: number }>; new_sale: unknown }) {
		return rpc<{ return_invoice: string; new_sale: unknown }>(`${API}.exchange_sales_product`, { body: { payload } });
	},
  getDashboardMetrics() {
    return rpc<DashboardMetrics>(`${API}.get_dashboard_metrics`);
  },

  getDirectorFinancialSummary() {
    return rpc<DirectorFinancialSummary>(`${API}.get_director_financial_summary`);
  },

  getDirectorStrategicReport(period: "7d" | "month" = "month") {
    return rpc<DirectorStrategicReport>(`${API}.get_director_strategic_report`, { query: { period } });
  },

  getDirectorRiskAgenda() {
    return rpc<DirectorRiskAgenda>(`${API}.get_director_risk_agenda`);
  },
	getTechnicianWorkload() {
		return rpc<TechnicianWorkloadResponse>(`${API}.get_technician_workload`);
	},
	issueAcceptance(serviceOrder: string, acceptanceType: "Entrada" | "Retirada", signerRole = "Dono") {
		return rpc<AcceptanceIssueResponse>(`${API}.issue_os_acceptance`, {
			body: { service_order: serviceOrder, acceptance_type: acceptanceType, signer_role: signerRole },
		});
	},
  searchCustomers(query = "", limit = 12) {
    return rpc<CustomerSearchResponse>(`${API}.search_customers`, {
      query: { query, limit },
    });
  },
  createCustomer(payload: CreateCustomerPayload) {
    return rpc<CreateCustomerResponse>(`${API}.create_customer`, {
      body: { payload },
    });
  },
  listDevices(query = "", limit = 12, customer = "") {
    return rpc<CustomerDeviceListResponse>(`${API}.list_customer_devices`, {
      query: { query, limit, customer },
    });
  },
  createDevice(payload: CreateCustomerDevicePayload) {
    return rpc<CreateCustomerDeviceResponse>(`${API}.create_customer_device`, {
      body: { payload },
    });
  },
  listTradeEvaluations(query = "", limit = 12) {
    return rpc<TradeEvaluationListResponse>(`${API}.list_trade_evaluations`, {
      query: { query, limit },
    });
  },
	setTradeInApprovedValue(name: string, approvedValue: number) {
		return rpc<SetTradeInApprovedValueResponse>(`${API}.set_tradein_approved_value`, {
			body: { name, approved_value: approvedValue },
		});
	},
	createTradeEvaluation(payload: CreateTradeEvaluationPayload) {
		return rpc<{ item: TradeEvaluationSummary }>(`${API}.create_trade_evaluation`, { body: { payload } });
	},
	completeTradeBuyback(name: string) {
		return rpc<CompleteTradeBuybackResponse>(`${API}.complete_trade_buyback`, { body: { name } });
	},
	listTradeInOutputDevices(query = "", limit = 20) {
		return rpc<TradeOutputDeviceListResponse>(`${API}.list_tradein_output_devices`, { query: { query, limit } });
	},
	confirmTradeInOperation(payload: { evaluation: string; device_out: string; difference: number; payment_mode?: string; notes?: string }) {
		return rpc<ConfirmTradeInOperationResponse>(`${API}.confirm_tradein_operation`, { body: { payload } });
	},
  listStockItems(query = "", limit = 12, scope = "parts-stock", category = "") {
    return rpc<StockItemListResponse>(`${API}.list_stock_items`, {
      query: { query, limit, scope, category },
    });
  },
	createStockTransfer(itemCode: string, qty: number, sourceWarehouse: string, targetWarehouse: string) {
		return rpc<StockTransferResponse>(`${API}.create_stock_transfer`, {
			body: { item_code: itemCode, qty, source_warehouse: sourceWarehouse, target_warehouse: targetWarehouse },
		});
	},
	submitStockTransfer(name: string) {
		return rpc<StockTransferResponse>(`${API}.submit_stock_transfer`, { body: { name } });
	},
};
