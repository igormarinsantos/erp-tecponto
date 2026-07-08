import { rpc } from "./client";
import type {
  BudgetDecisionPayload,
  PickupPayload,
  ServiceOrderDetailResponse,
  ServiceOrderKanbanResponse,
  ServiceOrderListResponse,
  ServiceOrderMoveResponse,
} from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const serviceOrders = {
  list(limit = 20) {
    return rpc<ServiceOrderListResponse>(`${API}.list_service_orders`, {
      query: { limit },
    });
  },
  kanban(limitPerColumn = 18) {
    return rpc<ServiceOrderKanbanResponse>(`${API}.get_service_order_kanban`, {
      query: { limit_per_column: limitPerColumn },
    });
  },
  detail(name: string) {
    return rpc<ServiceOrderDetailResponse>(`${API}.get_service_order_detail`, {
      query: { name },
    });
  },
  move(name: string, targetState: string) {
    return rpc<ServiceOrderMoveResponse>(`${API}.move_service_order`, {
      body: { name, target_state: targetState },
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
