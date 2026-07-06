import { Bell, LogOut, MessageCircle, Search } from "lucide-react";

import type { LoggedUser } from "../api";
import { Button } from "./Button";

interface TopbarProps {
  user: LoggedUser;
  onLogout: () => void;
}

export function Topbar({ onLogout, user }: TopbarProps) {
  return (
    <header className="sticky top-0 z-20 flex h-[var(--tp-topbar-height)] items-center gap-4 border-b border-tec-border/20 bg-black/25 px-4 backdrop-blur-xl lg:pl-[calc(var(--tp-sidebar-width)+24px)]">
      <div className="relative mx-auto hidden w-full max-w-[580px] md:block">
        <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-tec-muted" size={18} />
        <input
          className="h-11 w-full rounded-control border border-tec-border/25 bg-white/[0.035] pl-11 pr-16 text-sm text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70"
          placeholder="Buscar atendimento, cliente, aparelho, OS, venda..."
          type="search"
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 rounded bg-white/5 px-2 py-1 text-xs text-tec-muted">
          Ctrl K
        </kbd>
      </div>

      <Button className="hidden text-tec-green md:inline-flex" icon={<MessageCircle size={18} />} variant="secondary">
        WhatsApp
      </Button>
      <button
        className="relative grid h-11 w-11 place-items-center rounded-control border border-tec-border/25 bg-white/[0.035] text-tec-subtle"
        title="Notificações"
        type="button"
      >
        <Bell size={18} />
        <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-tec-red px-1 text-[10px] font-bold text-white">
          8
        </span>
      </button>
      <div className="hidden min-w-[168px] items-center gap-3 rounded-control border border-tec-border/25 bg-white/[0.035] p-2 lg:flex">
        <div className="grid h-9 w-9 place-items-center rounded-full bg-tec-blue text-xs font-bold text-white">
          {user.initials}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-white">{user.role_label}</p>
          <p className="truncate text-xs text-tec-muted">{user.subtitle}</p>
        </div>
      </div>
      <button
        className="grid h-11 w-11 place-items-center rounded-control border border-tec-border/25 bg-white/[0.035] text-tec-subtle hover:text-white"
        onClick={onLogout}
        title="Sair"
        type="button"
      >
        <LogOut size={18} />
      </button>
    </header>
  );
}
