import { rpc } from "./client";
import type { ProductCategorySavePayload, ProductCategoryTreeResponse } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const productCategories = {
  list() {
    return rpc<ProductCategoryTreeResponse>(`${API}.list_product_categories`);
  },
  save(payload: ProductCategorySavePayload) {
    return rpc<{ item: unknown }>(`${API}.save_product_category`, { body: { ...payload } });
  },
};
