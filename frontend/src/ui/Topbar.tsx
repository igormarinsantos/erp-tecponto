import { Bell, LogOut, MessageCircle, Search } from "lucide-react";

import type { LoggedUser } from "../api";
import { Button } from "./Button";

interface TopbarProps {
  onComingSoon: (label: string, block?: string) => void;
  user: LoggedUser;
  onLogout: () => void;
}

export function Topbar({ onComingSoon, onLogout, user }: TopbarProps) {
  return (
    <header className="tp-topbar-shell sticky top-0 z-20 flex h-[var(--tp-topbar-height)] items-center gap-3 border-b border-tec-border/20">
      <div className="tp-topbar-search relative mr-auto w-full max-w-[540px]">
        <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-tec-muted" size={17} />
        <input
          className="h-10 w-full rounded-control border border-tec-border/25 bg-tec-field pl-10 pr-16 text-sm text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70"
          onClick={() => onComingSoon("Busca global", "bloco 3.1x")}
          onFocus={() => onComingSoon("Busca global", "bloco 3.1x")}
          placeholder="Buscar atendimento, cliente, aparelho, OS, venda..."
          readOnly
          title="Em breve — bloco 3.1x"
          type="search"
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 rounded bg-tec-panel px-2 py-1 text-[11px] text-tec-muted">
          Ctrl K
        </kbd>
      </div>

      <Button
        className="tp-topbar-whatsapp min-h-10 shrink-0 px-3 text-tec-whatsapp"
        icon={<MessageCircle size={17} />}
        onClick={() => onComingSoon("WhatsApp", "bloco 3.1x")}
        title="Em breve — bloco 3.1x"
        variant="secondary"
      >
        WhatsApp
      </Button>
      <button
        className="relative grid h-10 w-10 shrink-0 place-items-center rounded-full border border-tec-border/25 bg-tec-field text-tec-subtle transition hover:border-tec-orange/50 hover:text-white"
        onClick={() => onComingSoon("Notificações", "bloco 3.1x")}
        title="Em breve — bloco 3.1x"
        type="button"
      >
        <Bell size={17} />
        <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-tec-red px-1 text-[9px] font-bold text-white">
          8
        </span>
      </button>
      <div className="tp-topbar-user min-w-[160px] shrink-0 items-center gap-2 rounded-control border border-tec-border/25 bg-tec-field px-2 py-1.5">
        <div className="grid h-8 w-8 place-items-center rounded-full bg-tec-blue text-xs font-bold text-white">
          {user.initials}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-white">{user.role_label}</p>
          <p className="truncate text-xs text-tec-muted">{user.subtitle}</p>
        </div>
      </div>
      <button
        className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-tec-border/25 bg-tec-field text-tec-subtle transition hover:border-tec-orange/50 hover:text-white"
        onClick={onLogout}
        title="Sair"
        type="button"
      >
        <LogOut size={17} />
      </button>
    </header>
  );
}
