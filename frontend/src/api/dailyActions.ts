import { rpc } from "./client";
import type { AgendaCalendarResponse, DailyActionsResponse, TecpontoTask } from "./types";

const API = "tecponto_app.tecponto.pending";

export const dailyActions = {
  list(panel: string) {
    return rpc<DailyActionsResponse>(`${API}.list_daily_actions`, { query: { panel } });
  },
  calendar(panel: string, startDate: string, endDate: string) {
    return rpc<AgendaCalendarResponse>(`${API}.list_agenda_calendar`, { query: { panel, start_date: startDate, end_date: endDate } });
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
