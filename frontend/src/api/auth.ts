import { rpc } from "./client";
import type { BootResponse, LoggedUser } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

export function getBoot() {
  return rpc<BootResponse>(`${API}.get_boot`);
}

export function getLoggedUser() {
  return rpc<LoggedUser>(`${API}.get_logged_user`);
}

export function logout() {
  window.location.href = "/?cmd=web_logout";
}
