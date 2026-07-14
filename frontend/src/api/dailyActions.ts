import { rpc } from "./client";
import type { DailyActionsResponse, TecpontoTask } from "./types";

const API = "tecponto_app.tecponto.pending";

export const dailyActions = {
  list(panel: string) {
    return rpc<DailyActionsResponse>(`${API}.list_daily_actions`, { query: { panel } });
  },
  create(title: string, dueDate?: string) {
    return rpc<TecpontoTask>(`${API}.create_manual_task`, {
      body: dueDate ? { due_date: dueDate, title } : { title },
    });
  },
  complete(name: string) {
    return rpc<TecpontoTask>(`${API}.complete_manual_task`, { body: { name } });
  },
};
