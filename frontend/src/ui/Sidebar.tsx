import type { LucideIcon } from "lucide-react";
import { Grid2X2, HelpCircle } from "lucide-react";

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
  onComingSoon: (label: string, block?: string) => void;
  onNavigate: (target: NavigationTarget) => void;
  sections: NavSection[];
  user: LoggedUser;
}

export function Sidebar({ activeItemId, onComingSoon, onNavigate, sections, user }: SidebarProps) {
  return (
    <aside className="tp-sidebar-desktop fixed inset-y-0 left-0 z-30 w-[var(--tp-sidebar-width)] border-r border-tec-border/20 bg-black/25 p-4 backdrop-blur-xl">
      <div className="rounded-card border border-tec-border/25 bg-white/[0.025] p-5">
        <div className="text-2xl font-black leading-none tracking-normal text-white">TECPONTO</div>
        <div className="mt-2 text-xs font-semibold uppercase text-tec-subtle">Central de operação</div>
      </div>

      <nav className="mt-5 space-y-5">
        {sections.map((section) => (
          <div key={section.label}>
            <p className="mb-2 px-2 text-xs font-bold uppercase text-tec-muted">{section.label}</p>
            <div className="space-y-1">
              {section.items.map((item) => (
                <button
                  aria-current={item.id === activeItemId ? "page" : undefined}
                  className={cx(
                    "flex min-h-[56px] w-full items-center gap-3 rounded-card px-3 py-2 text-left transition",
                    item.id === activeItemId
                      ? "bg-tec-orange text-white shadow-glow"
                      : "text-tec-subtle hover:bg-white/[0.04] hover:text-white",
                  )}
                  key={item.label}
                  onClick={() => onNavigate(item.id)}
                  title={item.label}
                  type="button"
                >
                  <span
                    className={cx(
                      "grid h-9 w-9 shrink-0 place-items-center rounded-card",
                      item.id === activeItemId ? "bg-black/15" : "bg-white/[0.055] text-tec-orange",
                    )}
                  >
                    <item.icon size={18} />
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-bold">{item.label}</span>
                    <span
                      className={cx(
                        "block truncate text-xs",
                        item.id === activeItemId ? "text-white/75" : "text-tec-muted",
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
          className="flex min-h-[44px] w-full items-center gap-3 rounded-card border border-tec-border/25 bg-white/[0.025] px-4 text-sm font-semibold text-tec-subtle"
          onClick={() => onComingSoon("Ajuda rápida", "bloco 3.1x")}
          title="Em breve — bloco 3.1x"
          type="button"
        >
          <HelpCircle size={18} />
          Ajuda rápida
        </button>
        <div className="rounded-card border border-tec-border/25 bg-white/[0.035] p-4">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-full bg-tec-blue text-sm font-bold text-white">
              {user.initials}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-white">{user.full_name}</p>
              <p className="truncate text-xs text-tec-muted">{user.name}</p>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs text-tec-subtle">
            <Grid2X2 size={14} className="text-tec-green" />
            Online
          </div>
        </div>
      </div>
    </aside>
  );
}
