import { rpc } from "./client";
import type { NotificationListResponse, TecpontoNotification } from "./types";

const METHOD = "tecponto_app.tecponto.notify";

export const notifications = {
  list: (limit = 20) => rpc<NotificationListResponse>(`${METHOD}.list_notifications`, { query: { limit } }),
  markRead: (name: string) => rpc<TecpontoNotification>(`${METHOD}.mark_notification_read`, { body: { name } }),
  markAllRead: () => rpc<number>(`${METHOD}.mark_all_notifications_read`, { body: {} }),
};
