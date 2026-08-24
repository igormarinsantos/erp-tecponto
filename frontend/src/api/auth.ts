import { extractFrappeErrorMessage, rpc } from "./client";
import type { BootResponse, CompanyIdentity, LoggedUser } from "./types";

const API = "tecponto_app.tecponto.frontend.api";

interface FrappeLoginPayload {
  exc?: string;
  exception?: string;
  message?: string;
  _server_messages?: string;
}

export function getBoot() {
  return rpc<BootResponse>(`${API}.get_boot`);
}

export function getPublicCompanyIdentity() {
  return rpc<CompanyIdentity>("tecponto_app.tecponto.company_identity.get_public_company_identity");
}

export function getLoggedUser() {
  return rpc<LoggedUser>(`${API}.get_logged_user`);
}

export async function login(credentials: { password: string; user: string }) {
  const formData = new FormData();
  formData.set("usr", credentials.user);
  formData.set("pwd", credentials.password);

  const response = await fetch("/api/method/login", {
    body: formData,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
    },
    method: "POST",
  });
  const payload = (await response.json().catch(() => ({}))) as FrappeLoginPayload;

  if (!response.ok || payload.exc || payload.exception || payload.message === "Invalid login") {
    throw new Error(extractFrappeErrorMessage(payload) ?? "Usuário ou senha incorretos.");
  }

  return payload;
}

export async function logout() {
  await fetch("/api/method/logout", {
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "X-Frappe-CSRF-Token": window.tecpontoBoot?.csrfToken ?? "",
    },
    method: "POST",
  }).catch(() => undefined);
  window.location.assign("/tecponto");
}
