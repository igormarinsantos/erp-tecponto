import { rpc } from "./client";
import type { CheckinPayload, CheckinResponse } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const checkin = {
  createServiceOrder(payload: CheckinPayload) {
    return rpc<CheckinResponse>(`${API}.create_service_order_checkin`, {
      body: { payload },
    });
  },
};
