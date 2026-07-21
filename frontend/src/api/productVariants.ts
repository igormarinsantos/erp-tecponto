import { rpc } from "./client";
import type { ProductVariantAttribute, ProductVariantCreatePayload, ProductVariantSummary, ProductVariantTemplate } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const productVariants = {
  create(payload: ProductVariantCreatePayload) {
    return rpc<{ template: ProductVariantTemplate; variants: ProductVariantSummary[] }>(`${API}.create_product_with_variants`, {
      body: { payload: JSON.stringify(payload) },
    });
  },
  listAttributes() {
    return rpc<{ items: ProductVariantAttribute[] }>(`${API}.list_product_variant_attributes`);
  },
  listProducts() {
    return rpc<{ items: ProductVariantTemplate[] }>(`${API}.list_variant_products`);
  },
  saveAttribute(name: string, values: Array<{ value: string; abbreviation?: string }>, disabled = false) {
    return rpc<{ item: ProductVariantAttribute }>(`${API}.save_product_variant_attribute`, {
      body: { disabled: disabled ? 1 : 0, name, values: JSON.stringify(values) },
    });
  },
};
