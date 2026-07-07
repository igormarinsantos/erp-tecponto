import { rpc } from "./client";
import type { BudgetDecisionPayload, PickupPayload, ServiceOrderDetailResponse, ServiceOrderListResponse } from "./types";

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
};
