import { rpc } from "./client";
import type { ServiceOrderListResponse } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const serviceOrders = {
  list(limit = 20) {
    return rpc<ServiceOrderListResponse>(`${API}.list_service_orders`, {
      query: { limit },
    });
  },
};
