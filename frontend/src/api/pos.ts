import { rpc } from "./client";
import type { PosItemSearchResponse, PosSalePayload, PosSaleResponse } from "./types";

const API = "tecponto_app.tecponto.frontend.api";
const POS_API = "tecponto_app.tecponto.frontend.pos";

interface PosItemSearchParams {
  barcode?: string;
  limit?: number;
  query?: string;
}

export const pos = {
  createSale(payload: PosSalePayload) {
    return rpc<PosSaleResponse>(`${POS_API}.pos_create_sale`, {
      body: { payload: JSON.stringify(payload) },
    });
  },
  searchItems({ barcode = "", limit = 12, query = "" }: PosItemSearchParams) {
    return rpc<PosItemSearchResponse>(`${API}.search_pos_items`, {
      query: { barcode, limit, query },
    });
  },
};
