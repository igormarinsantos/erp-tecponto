import type { LucideIcon } from "lucide-react";
import { ChevronUp, HelpCircle, LogOut } from "lucide-react";
import { useState } from "react";

import type { LoggedUser, NavigationTarget } from "../api";
import { cx } from "./utils";

export interface NavItem {
  id: NavigationTarget;
  icon: LucideIcon;
  label: string;
  subtitle: string;
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

interface SidebarProps {
  activeItemId: NavigationTarget;
  onOpenHelp: () => void;
  onLogout: () => void;
  onNavigate: (target: NavigationTarget) => void;
  sections: NavSection[];
  user: LoggedUser;
}

export function Sidebar({ activeItemId, onLogout, onOpenHelp, onNavigate, sections, user }: SidebarProps) {
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <aside className="tp-sidebar-desktop fixed inset-y-0 left-0 z-30 w-[var(--tp-sidebar-width)] border-r border-tec-border/20 bg-tec-sidebar p-4">
      <div className="px-2 py-2">
        <div className="tp-logo text-2xl font-bold leading-none tracking-normal text-white">TECPONTO</div>
      </div>

      <nav className="mt-4 space-y-4">
        {sections.map((section) => (
          <div key={section.label}>
            <p className="mb-2 px-2 text-xs font-bold uppercase text-tec-muted">{section.label}</p>
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <button
                  aria-current={item.id === activeItemId ? "page" : undefined}
                  className={cx(
                    "relative flex min-h-[52px] w-full items-center gap-3 overflow-hidden rounded-nav px-3 py-2 text-left transition",
                    item.id === activeItemId
                      ? "bg-tec-field text-white before:absolute before:inset-y-2 before:left-0 before:w-0.5 before:rounded-full before:bg-tec-orange"
                      : "text-tec-subtle hover:bg-tec-field hover:text-white",
                  )}
                  key={item.label}
                  onClick={() => onNavigate(item.id)}
                  title={item.label}
                  type="button"
                >
                  <span
                    className={cx(
                      "grid h-9 w-9 shrink-0 place-items-center rounded-control",
                      item.id === activeItemId ? "bg-tec-orange/12 text-tec-orange" : "bg-tec-field text-tec-orange",
                    )}
                  >
                    <item.icon size={18} />
                  </span>
                  <span className="min-w-0">
                    <span className="tp-nav-label block truncate text-sm font-bold">{item.label}</span>
                    <span
                      className={cx(
                        "block truncate text-xs",
                        "text-tec-muted",
                      )}
                    >
                      {item.subtitle}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="absolute bottom-4 left-4 right-4 space-y-3">
        <button
          className="flex min-h-[48px] w-full items-center gap-3 rounded-control border border-tec-border/20 bg-tec-panel px-4 text-left text-sm font-semibold text-tec-subtle transition hover:bg-tec-field hover:text-white"
          onClick={onOpenHelp}
          title="Abrir ajuda rápida"
          type="button"
        >
          <HelpCircle size={18} />
          <span>
            <span className="block">Ajuda rápida</span>
            <span className="mt-0.5 block text-[10px] font-medium text-tec-muted">Atalhos, guias e suporte</span>
          </span>
        </button>
        {profileOpen ? (
          <div className="rounded-card border border-tec-border/20 bg-tec-panel-strong p-2 shadow-panel">
            <button
              className="flex min-h-10 w-full items-center gap-3 rounded-control px-3 text-sm font-bold text-tec-subtle transition hover:bg-tec-field hover:text-white"
              onClick={onLogout}
              type="button"
            >
              <LogOut size={17} />
              Sair do usuario
            </button>
          </div>
        ) : null}
        <button
          aria-expanded={profileOpen}
          className="w-full rounded-card border border-tec-border/25 bg-tec-panel p-4 text-left transition hover:border-tec-orange/35 hover:bg-tec-field"
          onClick={() => setProfileOpen((current) => !current)}
          title="Abrir opcoes do usuario"
          type="button"
        >
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-tec-blue text-sm font-bold leading-none text-white">
              {user.initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-bold text-white">{user.full_name}</p>
              <p className="truncate text-xs text-tec-muted">{user.name}</p>
            </div>
            <ChevronUp
              className={cx("shrink-0 text-tec-muted transition", profileOpen ? "rotate-180" : "")}
              size={16}
            />
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-tec-border/10 pt-3 text-[11px] text-tec-muted">
            <span>Balcão 01</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-tec-success" />Online</span>
          </div>
        </button>
      </div>
    </aside>
  );
}
