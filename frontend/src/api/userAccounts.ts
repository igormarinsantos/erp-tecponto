import { rpc } from "./client";
import type { UserAccountListResponse, UserAccountPayload } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export const userAccounts = {
  list(query = "", includeInactive = true) {
    return rpc<UserAccountListResponse>(`${API}.list_user_accounts`, {
      query: { query, include_inactive: includeInactive },
    });
  },
  save(payload: UserAccountPayload) {
    return rpc<{ item: UserAccountListResponse["items"][number] }>(`${API}.save_user_account`, { body: { payload } });
  },
  setPassword(user: string, newPassword: string) {
	return rpc<{ changed: boolean }>(`${API}.set_user_password`, { body: { user, new_password: newPassword } });
  },
};
