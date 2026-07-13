import { useEffect, useRef, useState } from "react";
import { Bell, ChevronDown, LogOut, Moon, Search, Sun } from "lucide-react";

import type { BootResponse, LoggedUser, RolePanel } from "../api";
import { WhatsAppLogo } from "./WhatsAppLogo";

interface TopbarProps {
  contextOptions: BootResponse["panels"];
  onOpenNotifications: () => void;
  onOpenSearch: () => void;
  onContextChange: (panel: RolePanel) => void;
  onToggleTheme: () => void;
  selectedContextPanel: RolePanel;
  theme: "dark" | "light";
  user: LoggedUser;
  onLogout: () => void;
}

export function Topbar({
  contextOptions,
  onContextChange,
  onLogout,
  onOpenNotifications,
  onOpenSearch,
  onToggleTheme,
  selectedContextPanel,
  theme,
  user,
}: TopbarProps) {
  const nextThemeLabel = theme === "dark" ? "tema claro" : "tema escuro";
  const [contextOpen, setContextOpen] = useState(false);
  const contextSelectorRef = useRef<HTMLDivElement | null>(null);

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

  useEffect(() => {
    if (!contextOpen) {
      return;
    }
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!contextSelectorRef.current?.contains(event.target as Node)) {
        setContextOpen(false);
      }
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setContextOpen(false);
      }
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [contextOpen]);

  return (
    <header className="tp-topbar-shell sticky top-0 z-20 flex h-[var(--tp-topbar-height)] items-center gap-4 border-b border-tec-border/20">
      <div className="tp-topbar-search relative mr-auto w-full max-w-[620px]">
        <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-tec-muted" size={17} />
        <input
          className="h-10 w-full rounded-control border border-tec-border/25 bg-tec-field pl-10 pr-16 text-sm text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70"
          onClick={onOpenSearch}
          onFocus={onOpenSearch}
          placeholder="Buscar atendimento, cliente, aparelho, OS, venda..."
          readOnly
          title="Abrir busca global"
          type="search"
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 rounded bg-tec-panel px-2 py-1 text-[11px] text-tec-muted">
          Ctrl K
        </kbd>
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
        <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-tec-red px-1 text-[9px] font-bold text-white">
          8
        </span>
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
      {contextOptions.length > 1 ? (
        <div className="relative shrink-0" ref={contextSelectorRef}>
          <button
            aria-expanded={contextOpen}
            aria-haspopup="menu"
            className="tp-role-context flex h-10 items-center gap-2 rounded-control border border-tec-border/25 bg-tec-field px-3 text-left transition hover:border-tec-orange/50"
            data-testid="role-context-trigger"
            onClick={() => setContextOpen((current) => !current)}
            title="Trocar contexto visual"
            type="button"
          >
            <span className="hidden text-[11px] font-semibold text-tec-muted xl:inline">Operando como:</span>
            <span className="text-sm font-bold text-white">{user.role_label}</span>
            <ChevronDown aria-hidden="true" className={contextOpen ? "text-tec-orange transition rotate-180" : "text-tec-muted transition"} size={15} />
          </button>
          {contextOpen ? (
            <div className="absolute right-0 top-[calc(100%+0.5rem)] z-50 min-w-[216px] overflow-hidden rounded-card border border-tec-border/25 bg-tec-panel-strong p-1.5 shadow-panel" data-testid="role-context-menu" role="menu">
              <p className="px-2.5 py-2 text-[11px] font-bold uppercase text-tec-muted">Operando como</p>
              {contextOptions.map((context) => (
                <button
                  className={context.panel === selectedContextPanel ? "flex w-full items-center justify-between gap-4 rounded-control bg-tec-orange px-2.5 py-2.5 text-left text-tec-ink" : "flex w-full items-center justify-between gap-4 rounded-control px-2.5 py-2.5 text-left text-tec-subtle transition hover:bg-tec-field hover:text-white"}
                  key={context.panel}
                  onClick={() => {
                    setContextOpen(false);
                    onContextChange(context.panel);
                  }}
                  role="menuitemradio"
                  aria-checked={context.panel === selectedContextPanel}
                  type="button"
                >
                  <span>
                    <span className="block text-sm font-bold">{context.label}</span>
                    <span className={context.panel === selectedContextPanel ? "mt-0.5 block text-xs text-tec-ink/75" : "mt-0.5 block text-xs text-tec-muted"}>{context.subtitle}</span>
                  </span>
                  {context.panel === selectedContextPanel ? <span className="text-xs font-bold">Ativo</span> : null}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
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
