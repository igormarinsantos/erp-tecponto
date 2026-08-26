import { rpc } from "./client";
import type {
	CashierOperatorIdentity,
	CashSessionSummary,
  PosBarcodeLabelResponse,
  PosItemSearchResponse,
  PosSalePayload,
  PosSaleResponse,
  RetailBarcodeLookupResponse,
  RetailItemGroupResponse,
  RetailProductRegistrationPayload,
  RetailProductRegistrationResponse,
  RetailStockReceiptPayload,
  RetailStockReceiptResponse,
} from "./types";

const API = "tecponto_app.tecponto.frontend.api";
const POS_API = "tecponto_app.tecponto.frontend.pos";

interface PosItemSearchParams {
  barcode?: string;
  limit?: number;
  query?: string;
}

export const pos = {
	getCashSession() {
		return rpc<{ session: CashSessionSummary | null }>(`${API}.get_store_cash_session`);
	},
	openCashSession(openingAmount: number, idempotencyKey: string) {
		return rpc<CashSessionSummary>(`${API}.open_store_cash_session`, {
			body: { opening_amount: openingAmount, idempotency_key: idempotencyKey },
		});
	},
  barcodeLabelUrl(itemCode: string) {
    return `/api/method/${POS_API}.pos_download_barcode_label?item_code=${encodeURIComponent(itemCode)}`;
  },
  createSale(payload: PosSalePayload) {
    return rpc<PosSaleResponse>(`${POS_API}.pos_create_sale`, {
      body: { payload: JSON.stringify(payload) },
    });
  },
  cashierBadgeUrl(operator: string) {
    return `/api/method/${POS_API}.pos_download_cashier_badge?operator=${encodeURIComponent(operator)}`;
  },
  identifyCashierOperator({ badgeCode = "", pin = "" }: { badgeCode?: string; pin?: string }) {
    return rpc<CashierOperatorIdentity>(`${POS_API}.pos_identify_cashier_operator`, {
      body: { badge_code: badgeCode, pin },
    });
  },
  generateBarcode(itemCode: string) {
    return rpc<PosBarcodeLabelResponse>(`${POS_API}.pos_generate_item_barcode`, {
      body: { item_code: itemCode },
    });
  },
  lookupRetailBarcode(barcode: string) {
    return rpc<RetailBarcodeLookupResponse>(`${POS_API}.pos_lookup_retail_barcode`, {
      query: { barcode },
    });
  },
  listRetailItemGroups() {
    return rpc<RetailItemGroupResponse>(`${POS_API}.pos_list_retail_item_groups`);
  },
  receiveRetailStock(payload: RetailStockReceiptPayload) {
    return rpc<RetailStockReceiptResponse>(`${POS_API}.pos_receive_retail_stock`, {
      body: { payload: JSON.stringify(payload) },
    });
  },
  registerRetailProduct(payload: RetailProductRegistrationPayload) {
    return rpc<RetailProductRegistrationResponse>(`${POS_API}.pos_register_retail_product`, {
      body: { payload: JSON.stringify(payload) },
    });
  },
  searchItems({ barcode = "", limit = 12, query = "" }: PosItemSearchParams) {
    return rpc<PosItemSearchResponse>(`${API}.search_pos_items`, {
      query: { barcode, limit, query },
    });
  },
};
