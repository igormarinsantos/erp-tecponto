const API_PREFIX = "/api/method/";

type RpcOptions = {
  body?: Record<string, unknown>;
  query?: Record<string, string | number | boolean | undefined>;
};

interface FrappeRpcResponse<T> {
  message: T;
  exc?: string;
  exception?: string;
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
    throw new Error(payload.exception ?? payload.exc ?? `Falha na API (${response.status})`);
  }

  return payload.message;
}
