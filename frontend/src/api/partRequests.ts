import { rpc } from "./client";
import type { PurchasePartRequest, PurchasePartRequestResponse, RepairPartOptionsResponse, TechnicalPartRequest, TechnicalPartRequestResponse } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const partRequests = {
  create(serviceOrder: string, payload: { item?: string; free_description?: string; qty: number; notes?: string }) {
    return rpc<TechnicalPartRequest>(`${API}.create_technical_part_request`, {
      body: { service_order: serviceOrder, ...payload },
    });
  },
  listMine(limit = 100) {
    return rpc<TechnicalPartRequestResponse>(`${API}.list_my_technical_part_requests`, { query: { limit } });
  },
  searchOptions(query = "") {
    return rpc<RepairPartOptionsResponse>(`${API}.search_repair_part_options`, { query: { query } });
  },
  listPurchase(status = "open", query = "", limit = 100) {
    return rpc<PurchasePartRequestResponse>(`${API}.list_purchase_part_requests`, { query: { status, query, limit } });
  },
  markOrdered(name: string, payload: { supplier: string; expected_arrival: string; estimated_cost?: number }) {
    return rpc<PurchasePartRequest>(`${API}.mark_part_request_ordered`, { body: { name, ...payload } });
  },
  markReceived(name: string) {
    return rpc<PurchasePartRequest>(`${API}.mark_part_request_received`, { body: { name } });
  },
  cancel(name: string, reason: string) {
    return rpc<PurchasePartRequest>(`${API}.cancel_part_request`, { body: { name, reason } });
  },
};
