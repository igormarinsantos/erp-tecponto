import { rpc } from "./client";
import type { RepairPartOptionsResponse, TechnicalPartRequest, TechnicalPartRequestResponse } from "./types";

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
};
