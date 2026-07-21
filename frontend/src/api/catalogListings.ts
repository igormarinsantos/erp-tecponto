import { rpc } from "./client";
import type { CommercialCatalogItem, ListingMetadataPayload } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const catalogListings = {
  list(kind: "all" | "shelf" | "unique") {
    return rpc<{ items: CommercialCatalogItem[] }>(`${API}.list_commercial_catalog`, { query: { kind } });
  },
  save(itemCode: string, payload: ListingMetadataPayload) {
    return rpc<{ item: CommercialCatalogItem }>(`${API}.save_listing_metadata`, { body: { item_code: itemCode, payload: JSON.stringify(payload) } });
  },
};
