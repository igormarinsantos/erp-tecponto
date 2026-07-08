import { rpc } from "./client";
import type {
  CreateCustomerDevicePayload,
  CreateCustomerDeviceResponse,
  CustomerDeviceListResponse,
  CustomerSearchResponse,
  DashboardMetrics,
  StockItemListResponse,
  TradeEvaluationListResponse,
} from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const balcao = {
  getDashboardMetrics() {
    return rpc<DashboardMetrics>(`${API}.get_dashboard_metrics`);
  },
  searchCustomers(query = "", limit = 12) {
    return rpc<CustomerSearchResponse>(`${API}.search_customers`, {
      query: { query, limit },
    });
  },
  listDevices(query = "", limit = 12) {
    return rpc<CustomerDeviceListResponse>(`${API}.list_customer_devices`, {
      query: { query, limit },
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
  listStockItems(query = "", limit = 12) {
    return rpc<StockItemListResponse>(`${API}.list_stock_items`, {
      query: { query, limit },
    });
  },
};
