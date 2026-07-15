import { rpc } from "./client";
import type {
  ServiceCatalogReferenceResponse,
  ServiceCatalogService,
  ServiceCatalogServiceResponse,
  ServiceCatalogServicesResponse,
} from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const serviceCatalog = {
  list(query = "", deviceType = "", category = "", includeInactive = false) {
    return rpc<ServiceCatalogServicesResponse>(`${API}.list_catalog_services`, {
      query: { query, device_type: deviceType, category, include_inactive: includeInactive },
    });
  },
  references(includeInactive = true) {
    return rpc<ServiceCatalogReferenceResponse>(`${API}.list_catalog_references`, {
      query: { include_inactive: includeInactive },
    });
  },
  save(payload: Partial<ServiceCatalogService>) {
    return rpc<ServiceCatalogServiceResponse>(`${API}.save_catalog_service`, { body: { payload } });
  },
  saveReference(kind: "device_type" | "category", payload: { name?: string; value: string; active: boolean }) {
    return rpc<{ item: ServiceCatalogReference }>(`${API}.save_catalog_reference`, { body: { kind, payload } });
  },
};

type ServiceCatalogReference = ServiceCatalogReferenceResponse["device_types"][number];
