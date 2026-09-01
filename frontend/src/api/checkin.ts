import { rpc } from "./client";
import type { CheckinPayload, CheckinResponse, ServiceWarrantySearchResponse, WarrantyCandidateResponse } from "./types";

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
	searchWarranties(query: string, searchBy: "os" | "imei" | "customer") {
		return rpc<ServiceWarrantySearchResponse>(`${API}.search_service_order_warranties`, { query: { query, search_by: searchBy } });
	},
};
