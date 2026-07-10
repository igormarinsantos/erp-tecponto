import { FormEvent, type ReactNode, useState } from "react";
import { AlertCircle, ArrowRight, KeyRound, Loader2, LockKeyhole, ShieldCheck, UserRound } from "lucide-react";

import { Button } from "./ui";

export type LoginReason = "guest" | "expired";

interface LoginScreenProps {
  message?: string;
  onLogin: (credentials: { password: string; user: string }) => Promise<void>;
  reason: LoginReason;
}

export function LoginScreen({ message, onLogin, reason }: LoginScreenProps) {
  const [user, setUser] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting">("idle");
  const [error, setError] = useState<string | null>(null);
  const isExpired = reason === "expired";

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!user.trim() || !password) {
      setError("Informe usuário e senha para entrar.");
      return;
    }

    setStatus("submitting");
    setError(null);
    try {
      await onLogin({ password, user: user.trim() });
    } catch (caught) {
      setStatus("idle");
      setError(caught instanceof Error ? normalizeLoginError(caught.message) : "Não foi possível entrar agora.");
    }
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-tec-bg text-tec-text">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_12%,rgba(254,80,0,0.18),transparent_32%),radial-gradient(circle_at_82%_20%,rgba(47,140,255,0.12),transparent_28%)]" />
      <div className="relative grid min-h-screen gap-6 p-4 md:grid-cols-[minmax(300px,0.85fr)_minmax(360px,1fr)] lg:p-6">
        <section className="flex min-h-[260px] flex-col justify-between rounded-[26px] border border-tec-border/20 bg-tec-sidebar p-6 shadow-panel lg:p-8">
          <div>
            <div className="tp-logo text-3xl font-bold tracking-normal text-white">TECPONTO</div>
            <p className="mt-2 text-xs font-bold uppercase tracking-wide text-tec-muted">Central de operação</p>
          </div>

          <div className="max-w-xl">
            <p className="text-xs font-bold uppercase tracking-wide text-tec-orange">ERP Tecponto</p>
            <h1 className="mt-3 text-4xl font-bold leading-tight text-white lg:text-5xl">Acesso seguro para o balcão.</h1>
            <p className="mt-4 max-w-lg text-base leading-7 text-tec-subtle">
              Entre com seu usuário do Frappe. A tela muda conforme seu papel operacional e todas as regras continuam no motor do ERPNext.
            </p>
          </div>

          <div className="grid gap-3 text-sm text-tec-subtle sm:grid-cols-3 md:grid-cols-1 xl:grid-cols-3">
            <LoginProof icon={<ShieldCheck size={18} />} label="Sessão Frappe" />
            <LoginProof icon={<LockKeyhole size={18} />} label="Sem auth paralelo" />
            <LoginProof icon={<UserRound size={18} />} label="Papel Tecponto" />
          </div>
        </section>

        <section className="grid place-items-center rounded-[26px] border border-tec-border/20 bg-tec-panel p-5 shadow-panel lg:p-8">
          <form className="w-full max-w-[460px]" onSubmit={submit}>
            <div className="mb-7">
              <span className="grid h-14 w-14 place-items-center rounded-[18px] bg-tec-orange text-tec-ink shadow-glow">
                <KeyRound size={24} />
              </span>
              <h2 className="mt-5 text-3xl font-bold text-white">Entrar na Tecponto</h2>
              <p className="mt-2 text-sm leading-6 text-tec-subtle">
                {isExpired ? "Confirme suas credenciais para retomar a operação com segurança." : "Use o mesmo login do ERPNext/Frappe."}
              </p>
            </div>

            {isExpired || message ? (
              <div className="mb-5 flex gap-3 rounded-card border border-tec-amber/25 bg-tec-amber/10 p-3 text-sm text-tec-subtle">
                <AlertCircle className="mt-0.5 shrink-0 text-tec-amber" size={18} />
                <span>{message ?? "Sessão expirada por segurança. Nenhum dado foi enviado sem autenticação."}</span>
              </div>
            ) : null}

            {error ? (
              <div className="mb-5 flex gap-3 rounded-card border border-tec-red/30 bg-tec-red/10 p-3 text-sm font-semibold text-red-100">
                <AlertCircle className="mt-0.5 shrink-0 text-tec-red" size={18} />
                <span>{error}</span>
              </div>
            ) : null}

            <div className="space-y-4">
              <label className="block">
                <span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Usuário</span>
                <input
                  autoComplete="username"
                  className="h-12 w-full rounded-control border border-tec-border/25 bg-tec-field px-4 text-base font-semibold text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70 focus:ring-2 focus:ring-tec-orange/15"
                  onChange={(event) => setUser(event.target.value)}
                  placeholder="usuario@tecponto.local"
                  value={user}
                />
              </label>
              <label className="block">
                <span className="mb-2 block text-xs font-bold uppercase text-tec-muted">Senha</span>
                <input
                  autoComplete="current-password"
                  className="h-12 w-full rounded-control border border-tec-border/25 bg-tec-field px-4 text-base font-semibold text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70 focus:ring-2 focus:ring-tec-orange/15"
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Digite sua senha"
                  type="password"
                  value={password}
                />
              </label>
            </div>

            <Button className="mt-6 w-full" disabled={status === "submitting"} icon={status === "submitting" ? <Loader2 className="animate-spin" size={18} /> : <ArrowRight size={18} />} type="submit" variant="primary">
              {status === "submitting" ? "Entrando..." : "Entrar"}
            </Button>

            <p className="mt-5 text-center text-xs font-medium text-tec-muted">
              Se o acesso não abrir, peça ao gestor para vincular um papel Tecponto ao seu usuário.
            </p>
          </form>
        </section>
      </div>
    </main>
  );
}

function LoginProof({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-3 rounded-card border border-tec-border/15 bg-tec-field/55 px-3 py-3">
      <span className="grid h-9 w-9 place-items-center rounded-control bg-tec-orange/10 text-tec-orange">{icon}</span>
      <span className="font-semibold">{label}</span>
    </div>
  );
}

function normalizeLoginError(message: string) {
  const normalized = message.toLowerCase();
  if (
    normalized.includes("authenticationerror") ||
    normalized.includes("invalid login") ||
    normalized.includes("senha") ||
    normalized.includes("password")
  ) {
    return "Usuário ou senha incorretos.";
  }
  return message || "Não foi possível entrar agora.";
}
