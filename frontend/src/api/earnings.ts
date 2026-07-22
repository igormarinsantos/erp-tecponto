import { rpc } from "./client";
import type { OwnEarningsResponse } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const earnings = {
  list(period = "month", fromDate = "", toDate = "") {
    return rpc<OwnEarningsResponse>(`${API}.list_my_commissions`, {
      query: { period, from_date: fromDate, to_date: toDate },
    });
  },
};
