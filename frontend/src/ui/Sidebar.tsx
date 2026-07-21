import type { LucideIcon } from "lucide-react";
import { ChevronDown, ChevronUp, HelpCircle, LogOut } from "lucide-react";
import { useEffect, useState } from "react";

import tecpontoLogoDark from "../assets/tecponto-logo-dark.png";
import type { LoggedUser, NavigationTarget } from "../api";
import { cx } from "./utils";

export interface NavItem {
  id: NavigationTarget;
  icon: LucideIcon;
  label: string;
  subtitle: string;
  children?: NavItem[];
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
  const storageKey = `tecponto.sidebar.expanded.${user.name}`;
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    try {
      const saved = JSON.parse(window.localStorage.getItem(storageKey) || "{}") as Record<string, boolean>;
      const activeParents = Object.fromEntries(sections.flatMap((section) => section.items.filter((item) => item.children?.some((child) => child.id === activeItemId)).map((item) => [item.label, true])));
      setExpanded({ ...saved, ...activeParents });
    } catch {
      setExpanded(Object.fromEntries(sections.flatMap((section) => section.items.filter((item) => item.children?.some((child) => child.id === activeItemId)).map((item) => [item.label, true]))));
    }
  }, [activeItemId, storageKey]);

  const toggle = (label: string) => {
    setExpanded((current) => {
      const next = { ...current, [label]: !current[label] };
      try { window.localStorage.setItem(storageKey, JSON.stringify(next)); } catch { /* Persistence is a convenience only. */ }
      return next;
    });
  };

  return (
    <aside className="tp-sidebar-desktop fixed inset-y-0 left-0 z-30 flex w-[var(--tp-sidebar-width)] flex-col border-r border-tec-border/20 bg-tec-sidebar p-4">
      <div className="shrink-0 px-2 py-2">
        <img alt="Tecponto" className="tp-logo-image tp-logo-on-dark h-auto w-full max-w-[184px]" src={tecpontoLogoDark} />
      </div>

      <nav className="tp-sidebar-nav-scroll mt-4 min-h-0 flex-1 space-y-4 overflow-y-auto pr-2 pb-3">
        {sections.map((section) => (
          <div key={section.label}>
            <p className="mb-2 px-2 text-xs font-bold uppercase text-tec-muted">{section.label}</p>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const hasChildren = Boolean(item.children?.length);
                const open = Boolean(expanded[item.label]);
                const active = item.id === activeItemId;
                return <div key={item.label}>
                  <button
                    aria-current={active && !hasChildren ? "page" : undefined}
                    aria-expanded={hasChildren ? open : undefined}
                    className={cx("flex min-h-[52px] w-full items-center gap-3 overflow-hidden rounded-nav px-3 py-2 text-left transition", active && !hasChildren ? "bg-tec-field text-white" : "text-tec-subtle hover:bg-tec-field hover:text-white")}
                    onClick={() => hasChildren ? toggle(item.label) : onNavigate(item.id)}
                    title={item.label}
                    type="button"
                  >
                    <span className={cx("grid h-9 w-9 shrink-0 place-items-center rounded-control", active && !hasChildren ? "bg-tec-orange/12 text-tec-orange" : "bg-tec-field text-tec-orange")}><item.icon size={18} /></span>
                    <span className="min-w-0 flex-1"><span className="tp-nav-label block truncate text-sm font-bold">{item.label}</span><span className="block truncate text-xs text-tec-muted">{item.subtitle}</span></span>
                    {hasChildren ? <ChevronDown className={cx("shrink-0 text-tec-muted transition", open ? "rotate-180" : "")} size={16} /> : null}
                  </button>
                  {hasChildren && open ? <div className="ml-[30px] mt-1 space-y-0.5 border-l border-tec-border/20 pl-3">{item.children?.map((child) => {
                    const childActive = child.id === activeItemId;
                    return <button aria-current={childActive ? "page" : undefined} className={cx("flex min-h-9 w-full items-center gap-2 rounded-control px-2.5 py-1.5 text-left transition", childActive ? "bg-tec-field text-white" : "text-tec-muted hover:bg-tec-field hover:text-tec-text")} key={`${item.label}-${child.label}`} onClick={() => onNavigate(child.id)} title={child.label} type="button"><child.icon className={childActive ? "text-tec-orange" : "text-tec-muted"} size={15} /><span className="min-w-0 flex-1"><span className="block truncate text-[13px] font-semibold">{child.label}</span><span className="block truncate text-[11px] text-tec-muted">{child.subtitle}</span></span></button>;
                  })}</div> : null}
                </div>;
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="mt-auto shrink-0 space-y-3 pt-3">
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
