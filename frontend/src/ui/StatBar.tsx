import type { ReactNode } from "react";

export interface StatBarItem {
  key: string;
  label: string;
  value: number;
  detail?: string;
  icon?: ReactNode;
  tone?: "orange" | "blue" | "amber" | "green";
}

export function StatBar({ items, onSelect }: { items: StatBarItem[]; onSelect?: (key: string) => void }) {
  const tones = {
    orange: "text-tec-orange bg-tec-orange/10",
    blue: "text-tec-blue bg-tec-blue/10",
    amber: "text-tec-amber bg-tec-amber/10",
    green: "text-tec-success bg-tec-success/10",
  };
  const baseClass = "flex min-h-20 items-center gap-3 rounded-card border border-tec-border/15 bg-tec-panel p-4 text-left";

  return (
    <section aria-label="Resumo da lista" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => {
        const content = <><span className={`grid h-10 w-10 shrink-0 place-items-center rounded-control ${tones[item.tone ?? "orange"]}`}>{item.icon}</span><span><span className="block text-xs font-semibold text-tec-muted">{item.label}</span><strong className="tp-metric-value mt-1 block text-2xl text-white">{item.value}</strong>{item.detail ? <span className="mt-0.5 block text-xs font-medium text-tec-muted">{item.detail}</span> : null}</span></>;

        return onSelect ? (
          <button className={`${baseClass} cursor-pointer transition hover:border-tec-orange/50 hover:bg-tec-field`} key={item.key} onClick={() => onSelect(item.key)} type="button">
            {content}
          </button>
        ) : (
          <div className={baseClass} key={item.key}>{content}</div>
        );
      })}
    </section>
  );
}
