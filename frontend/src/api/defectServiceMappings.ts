import { rpc } from "./client";
import type { DefectServiceMapping } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const defectServiceMappings = {
  list(includeInactive = true) {
    return rpc<{ items: DefectServiceMapping[] }>(`${API}.list_defect_service_mappings`, { query: { include_inactive: includeInactive } });
  },
  save(payload: Partial<DefectServiceMapping>) {
    return rpc<{ item: DefectServiceMapping }>(`${API}.save_defect_service_mapping`, { body: { payload } });
  },
};
