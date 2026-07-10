import type { LucideIcon } from "lucide-react";
import { HelpCircle } from "lucide-react";

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
  onNavigate: (target: NavigationTarget) => void;
  sections: NavSection[];
  user: LoggedUser;
}

export function Sidebar({ activeItemId, onOpenHelp, onNavigate, sections, user }: SidebarProps) {
  return (
    <aside className="tp-sidebar-desktop fixed inset-y-0 left-0 z-30 w-[var(--tp-sidebar-width)] border-r border-tec-border/20 bg-tec-sidebar p-4">
      <div className="px-2 py-3">
        <div className="tp-logo text-2xl font-bold leading-none tracking-normal text-white">TECPONTO</div>
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
                    "flex min-h-[56px] w-full items-center gap-3 rounded-nav px-3 py-2 text-left transition",
                    item.id === activeItemId
                      ? "bg-tec-orange text-tec-ink shadow-glow"
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
                      item.id === activeItemId ? "bg-tec-ink/10 text-tec-ink" : "bg-tec-field text-tec-orange",
                    )}
                  >
                    <item.icon size={18} />
                  </span>
                  <span className="min-w-0">
                    <span className="tp-nav-label block truncate text-sm font-bold">{item.label}</span>
                    <span
                      className={cx(
                        "block truncate text-xs",
                        item.id === activeItemId ? "text-tec-ink/75" : "text-tec-muted",
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
          className="flex min-h-[44px] w-full items-center gap-3 rounded-control border border-tec-border/25 bg-tec-panel px-4 text-sm font-semibold text-tec-subtle transition hover:bg-tec-field hover:text-white"
          onClick={onOpenHelp}
          title="Abrir ajuda rápida"
          type="button"
        >
          <HelpCircle size={18} />
          Ajuda rápida
        </button>
        <div className="rounded-card border border-tec-border/25 bg-tec-panel p-4">
          <div className="flex items-center gap-3">
            <div className="grid aspect-square h-11 min-h-11 w-11 min-w-11 shrink-0 place-items-center overflow-hidden rounded-full bg-tec-blue text-sm font-bold leading-none text-white">
              {user.initials}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-bold text-white">{user.full_name}</p>
              <p className="truncate text-xs text-tec-muted">{user.name}</p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
