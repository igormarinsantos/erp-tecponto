import { rpc } from "./client";
import type { ServiceOrderDetailResponse, ServiceOrderListResponse } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const serviceOrders = {
  list(limit = 20) {
    return rpc<ServiceOrderListResponse>(`${API}.list_service_orders`, {
      query: { limit },
    });
  },
  detail(name: string) {
    return rpc<ServiceOrderDetailResponse>(`${API}.get_service_order_detail`, {
      query: { name },
    });
  },
};
