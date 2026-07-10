const API_PREFIX = "/api/method/";

type RpcOptions = {
  body?: Record<string, unknown>;
  query?: Record<string, string | number | boolean | undefined>;
};

interface FrappeRpcResponse<T> {
  message?: T;
  exc?: string;
  exception?: string;
  _server_messages?: string;
}

export class AuthRequiredError extends Error {
  constructor(message = "Faça login para acessar a Tecponto.") {
    super(message);
    this.name = "AuthRequiredError";
  }
}

export class NoOperationalRoleError extends Error {
  constructor(message = "Usuário sem papel operacional Tecponto.") {
    super(message);
    this.name = "NoOperationalRoleError";
  }
}

export async function rpc<T>(method: string, options: RpcOptions = {}): Promise<T> {
  const url = new URL(`${API_PREFIX}${method}`, window.location.origin);
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined) {
      url.searchParams.set(key, String(value));
    }
  }

  const init: RequestInit = {
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "X-Frappe-CSRF-Token": window.tecpontoBoot?.csrfToken ?? "",
    },
  };

  if (options.body) {
    const formData = new FormData();
    for (const [key, value] of Object.entries(options.body)) {
      formData.set(key, typeof value === "string" ? value : JSON.stringify(value));
    }
    init.method = "POST";
    init.body = formData;
  }

  const response = await fetch(url, init);
  const payload = (await response.json().catch(() => ({}))) as FrappeRpcResponse<T>;

  if (!response.ok || payload.exc || payload.exception) {
    const message = extractFrappeErrorMessage(payload) ?? `Falha na API (${response.status})`;
    if (isAuthRequiredMessage(message) || response.status === 401) {
      window.dispatchEvent(new CustomEvent("tecponto:session-expired"));
      throw new AuthRequiredError(message);
    }
    if (isNoOperationalRoleMessage(message)) {
      throw new NoOperationalRoleError(message);
    }
    throw new Error(message);
  }

  return payload.message as T;
}

export function extractFrappeErrorMessage<T>(payload: FrappeRpcResponse<T>) {
  if (payload._server_messages) {
    try {
      const messages = JSON.parse(payload._server_messages) as string[];
      const first = messages
        .map((message) => JSON.parse(message) as { message?: string })
        .map((message) => message.message)
        .find(Boolean);
      if (first) {
        return first;
      }
    } catch {
      return payload._server_messages;
    }
  }
  if (payload.exception && !payload.exception.includes("Traceback")) {
    return payload.exception.split(":").pop()?.trim() || payload.exception;
  }
  if (payload.exc && !payload.exc.includes("Traceback")) {
    return payload.exc;
  }
  return null;
}

export function isAuthRequiredError(error: unknown): error is AuthRequiredError {
  return error instanceof AuthRequiredError || (error instanceof Error && isAuthRequiredMessage(error.message));
}

export function isNoOperationalRoleError(error: unknown): error is NoOperationalRoleError {
  return error instanceof NoOperationalRoleError || (error instanceof Error && isNoOperationalRoleMessage(error.message));
}

function isAuthRequiredMessage(message: string) {
  const normalized = normalizeMessage(message);
  return (
    normalized.includes("faca login") ||
    normalized.includes("login required") ||
    normalized.includes("login to access") ||
    normalized.includes("not permitted for guest")
  );
}

function isNoOperationalRoleMessage(message: string) {
  return normalizeMessage(message).includes("sem papel operacional tecponto");
}

function normalizeMessage(message: string) {
  return message
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}
