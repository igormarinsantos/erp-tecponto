import { type ReactNode, useEffect } from "react";
import { Bell, LogOut, Moon, Search, Sun } from "lucide-react";

import type { LoggedUser } from "../api";
import { WhatsAppLogo } from "./WhatsAppLogo";

interface TopbarProps {
  onOpenNotifications: () => void;
  onOpenSearch: () => void;
	globalSearchOpen: boolean;
	globalSearchQuery: string;
	onGlobalSearchChange: (value: string) => void;
	searchDropdown?: ReactNode;
  onToggleTheme: () => void;
  theme: "dark" | "light";
  user: LoggedUser;
  onLogout: () => void;
  unreadNotificationCount: number;
}

export function Topbar({
  onLogout,
  onOpenNotifications,
  onOpenSearch,
	globalSearchOpen,
	globalSearchQuery,
	onGlobalSearchChange,
	searchDropdown,
  onToggleTheme,
  theme,
  user,
  unreadNotificationCount,
}: TopbarProps) {
  const nextThemeLabel = theme === "dark" ? "tema claro" : "tema escuro";

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenSearch();
      }
    };

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [onOpenSearch]);

  return (
    <header className="tp-topbar-shell sticky top-0 z-20 flex h-[var(--tp-topbar-height)] items-center gap-4 border-b border-tec-border/20">
      <div className="tp-topbar-search relative mr-auto w-full max-w-[620px]">
        <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-tec-muted" size={17} />
        <input
          className="h-10 w-full rounded-control border border-tec-border/25 bg-tec-field pl-10 pr-16 text-sm text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70"
          onChange={(event) => onGlobalSearchChange(event.target.value)}
          onClick={onOpenSearch}
          onFocus={onOpenSearch}
          placeholder="Buscar atendimento, cliente, aparelho, OS, venda..."
          title="Abrir busca global"
          type="search"
          value={globalSearchQuery}
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 rounded bg-tec-panel px-2 py-1 text-[11px] text-tec-muted">
          Ctrl K
        </kbd>
		{globalSearchOpen ? searchDropdown : null}
      </div>

      <a
        className="tp-topbar-whatsapp inline-flex min-h-10 shrink-0 items-center justify-center gap-2 rounded-control border border-tec-border/20 bg-tec-field px-4 text-sm font-semibold text-tec-whatsapp transition hover:border-tec-whatsapp/50"
        href="https://web.whatsapp.com/"
        rel="noreferrer"
        target="_blank"
        title="Abrir WhatsApp Web"
      >
        <WhatsAppLogo size={18} />
        WhatsApp
      </a>
      <button
        className="relative grid h-10 w-10 shrink-0 place-items-center rounded-control border border-tec-border/25 bg-tec-field text-tec-subtle transition hover:border-tec-orange/50 hover:text-tec-text"
        data-tp-notifications="trigger"
        onClick={onOpenNotifications}
        title="Abrir notificações"
        type="button"
      >
        <Bell size={17} />
        {unreadNotificationCount > 0 ? (
          <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-tec-red px-1 text-[9px] font-bold text-white">
            {unreadNotificationCount > 99 ? "99+" : unreadNotificationCount}
          </span>
        ) : null}
      </button>
      <button
        aria-label={`Alternar para ${nextThemeLabel}`}
        className="grid h-10 w-10 shrink-0 place-items-center rounded-control border border-tec-border/25 bg-tec-field text-tec-subtle transition hover:border-tec-orange/50 hover:text-tec-text"
        onClick={onToggleTheme}
        title={`Alternar para ${nextThemeLabel}`}
        type="button"
      >
        {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
      </button>
      <div className="tp-topbar-user min-w-[172px] shrink-0 items-center gap-2 rounded-control border border-tec-border/25 bg-tec-field px-2 py-1.5">
        <div className="grid h-8 w-8 place-items-center rounded-full bg-tec-blue text-xs font-bold text-white">
          {user.initials}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-white">{user.role_label}</p>
          <p className="truncate text-xs text-tec-muted">{user.subtitle}</p>
        </div>
      </div>
      <button
        className="grid h-10 w-10 shrink-0 place-items-center rounded-control border border-tec-border/25 bg-tec-field text-tec-subtle transition hover:border-tec-orange/50 hover:text-tec-text"
        onClick={onLogout}
        title="Sair"
        type="button"
      >
        <LogOut size={17} />
      </button>
    </header>
  );
}
