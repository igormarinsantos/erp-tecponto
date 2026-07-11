import { rpc } from "./client";
import type { PosItemSearchResponse } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

interface PosItemSearchParams {
  barcode?: string;
  limit?: number;
  query?: string;
}

export const pos = {
  searchItems({ barcode = "", limit = 12, query = "" }: PosItemSearchParams) {
    return rpc<PosItemSearchResponse>(`${API}.search_pos_items`, {
      query: { barcode, limit, query },
    });
  },
};
