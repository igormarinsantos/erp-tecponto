import { ChevronDown, LoaderCircle, MoveRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { ServiceOrderWorkflowAction } from "./api";
import { getBadgeStatusToneClass } from "./ui/BadgeStatus";
import { cx } from "./ui/utils";

export function WorkflowMoveMenu({
  actions,
	blockedTransitions = {},
  busy = false,
  className,
  onSelect,
  status,
  variant = "default",
}: {
  actions: ServiceOrderWorkflowAction[];
	blockedTransitions?: Record<string, string>;
  busy?: boolean;
  className?: string;
  onSelect: (action: ServiceOrderWorkflowAction) => void;
  status?: string | null;
  variant?: "default" | "status";
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!ref.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  if (!actions.length) return null;

  return (
    <div className={cx("relative", className)} ref={ref}>
      <button
        aria-expanded={open}
        aria-label={variant === "status" ? `Alterar status: ${status || "Sem status"}` : "Mover para outra etapa"}
        className={cx(
          variant === "status"
            ? `inline-flex h-6 max-w-full shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2.5 text-[11px] font-semibold leading-none ring-1 transition hover:ring-tec-orange/70 focus:outline-none focus:ring-2 focus:ring-tec-orange/70 disabled:opacity-55 ${getBadgeStatusToneClass(status)}`
            : "inline-flex min-h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-control border border-tec-border/20 bg-tec-field px-2.5 text-xs font-bold text-tec-subtle transition hover:border-tec-orange/55 hover:text-white disabled:opacity-55",
        )}
        disabled={busy}
        onClick={(event) => { event.stopPropagation(); setOpen((value) => !value); }}
        type="button"
      >
        {busy ? <LoaderCircle className="animate-spin" size={variant === "status" ? 12 : 14} /> : variant === "status" ? null : <MoveRight size={14} />}
        {variant === "status" ? <span className="truncate">{status || "Sem status"}</span> : "Mover"}
        <ChevronDown className="shrink-0" size={variant === "status" ? 12 : 14} />
      </button>
      {open ? (
        <div className={cx("absolute z-30 mt-2 w-56 rounded-card border border-tec-border/25 bg-tec-panel p-1.5 shadow-xl", variant === "status" ? "left-0" : "right-0")}>
          {actions.map((action) => (
            <button
				className="flex min-h-10 w-full items-center justify-between gap-3 rounded-control px-3 text-left text-sm font-semibold text-tec-subtle transition hover:bg-tec-field hover:text-white disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent"
				disabled={Boolean(blockedTransitions[action.next_state])}
              key={`${action.action}-${action.next_state}-${action.role}`}
              onClick={(event) => { event.stopPropagation(); setOpen(false); onSelect(action); }}
				title={blockedTransitions[action.next_state]}
              type="button"
            >
				<span><span className="block">{action.next_state}</span>{blockedTransitions[action.next_state] ? <span className="mt-0.5 block text-[11px] font-medium text-tec-amber">{blockedTransitions[action.next_state]}</span> : null}</span>
              <MoveRight className="shrink-0 text-tec-orange" size={15} />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
