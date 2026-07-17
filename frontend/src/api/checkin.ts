import { rpc } from "./client";
import type { CheckinPayload, CheckinResponse, DeliverySuggestion, WarrantyCandidateResponse } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const checkin = {
  createServiceOrder(payload: CheckinPayload) {
    return rpc<CheckinResponse>(`${API}.create_service_order_checkin`, {
      body: { payload },
    });
  },
  listWarrantyCandidates(customer?: string, customerDevice?: string) {
    return rpc<WarrantyCandidateResponse>(`${API}.list_warranty_candidates`, {
      body: { customer: customer ?? "", customer_device: customerDevice ?? "" },
    });
  },
  getDeliverySuggestion(defects: string[] = [], leadTimeBusinessHours = 0) {
    return rpc<DeliverySuggestion>(`${API}.get_checkin_delivery_suggestion`, {
      body: { payload: { defects, lead_time_business_hours: leadTimeBusinessHours } },
    });
  },
};
