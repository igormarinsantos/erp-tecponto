import { useEffect, type ReactNode } from "react";

import { cx } from "./utils";

export interface ContextMenuItem {
  disabled?: boolean;
  detail?: string;
  icon?: ReactNode;
  label: string;
  onSelect: () => void;
  separatorBefore?: boolean;
}

interface ContextMenuProps {
  items: ContextMenuItem[];
  onClose: () => void;
  subtitle?: string;
  title: string;
  x: number;
  y: number;
}

export function ContextMenu({ items, onClose, subtitle, title, x, y }: ContextMenuProps) {
  useEffect(() => {
    const close = () => onClose();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);

  return (
    <div
      className="fixed z-[80] w-[292px] overflow-hidden rounded-card border border-tec-border/20 bg-tec-panel-strong shadow-[0_22px_56px_rgba(0,0,0,0.38)]"
      data-testid="tecponto-context-menu"
      onClick={(event) => event.stopPropagation()}
      role="menu"
      style={{ left: x, top: y }}
    >
      <div className="border-b border-tec-border/15 px-3 py-3">
        <p className="text-sm font-bold text-white">{title}</p>
        {subtitle ? <p className="mt-0.5 truncate text-xs text-tec-muted">{subtitle}</p> : null}
      </div>
      <div className="p-1.5">
        {items.map((item) => (
          <button
            className={cx(
              "flex min-h-11 w-full items-center gap-3 rounded-control px-3 py-2 text-left transition",
              item.separatorBefore && "mt-1 border-t border-tec-border/10 pt-3",
              item.disabled
                ? "cursor-not-allowed text-tec-muted opacity-55"
                : "text-tec-subtle hover:bg-tec-orange/10 hover:text-white",
            )}
            disabled={item.disabled}
            key={item.label}
            onClick={() => {
              if (item.disabled) {
                return;
              }
              item.onSelect();
              onClose();
            }}
            role="menuitem"
            type="button"
          >
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-control bg-tec-field text-tec-orange">
              {item.icon}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-bold">{item.label}</span>
              {item.detail ? <span className="mt-0.5 block truncate text-xs text-tec-muted">{item.detail}</span> : null}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
