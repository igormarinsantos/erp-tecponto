import { ChevronDown, LoaderCircle, MoveRight } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { ServiceOrderWorkflowAction } from "./api";
import { cx } from "./ui/utils";

export function WorkflowMoveMenu({
  actions,
  busy = false,
  className,
  onSelect,
}: {
  actions: ServiceOrderWorkflowAction[];
  busy?: boolean;
  className?: string;
  onSelect: (action: ServiceOrderWorkflowAction) => void;
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
        className="inline-flex min-h-8 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-control border border-tec-border/20 bg-tec-field px-2.5 text-xs font-bold text-tec-subtle transition hover:border-tec-orange/55 hover:text-white disabled:opacity-55"
        disabled={busy}
        onClick={(event) => { event.stopPropagation(); setOpen((value) => !value); }}
        type="button"
      >
        {busy ? <LoaderCircle className="animate-spin" size={14} /> : <MoveRight size={14} />}
        Mover
        <ChevronDown size={14} />
      </button>
      {open ? (
        <div className="absolute right-0 z-30 mt-2 w-56 rounded-card border border-tec-border/25 bg-tec-panel p-1.5 shadow-xl">
          {actions.map((action) => (
            <button
              className="flex min-h-10 w-full items-center justify-between gap-3 rounded-control px-3 text-left text-sm font-semibold text-tec-subtle transition hover:bg-tec-field hover:text-white"
              key={`${action.action}-${action.next_state}-${action.role}`}
              onClick={(event) => { event.stopPropagation(); setOpen(false); onSelect(action); }}
              type="button"
            >
              <span>{action.next_state}</span>
              <MoveRight className="shrink-0 text-tec-orange" size={15} />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
