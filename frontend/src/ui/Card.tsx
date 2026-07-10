import type { ReactNode } from "react";

import { cx } from "./utils";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return <section className={cx("tp-panel rounded-card shadow-panel", className)}>{children}</section>;
}

interface MetricCardProps {
  icon: ReactNode;
  label: string;
  value: string | number;
  detail?: string;
  tone?: "orange" | "green" | "blue" | "purple" | "amber" | "red";
}

const toneClasses = {
  orange: "bg-tec-orange text-tec-ink shadow-glow",
  green: "bg-tec-success/25 text-tec-success",
  blue: "bg-tec-blue/25 text-tec-blue",
  purple: "bg-tec-purple/25 text-tec-purple",
  amber: "bg-tec-amber/25 text-tec-amber",
  red: "bg-tec-red/25 text-tec-red",
};

export function MetricCard({ detail, icon, label, tone = "orange", value }: MetricCardProps) {
  return (
    <Card className="flex min-h-[112px] items-center gap-5 p-5">
      <div className={cx("grid h-14 w-14 shrink-0 place-items-center rounded-card", toneClasses[tone])}>{icon}</div>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-tec-subtle">{label}</p>
        <p className="tp-metric-value mt-1 text-3xl font-bold leading-none text-tec-text">{value}</p>
        {detail ? <p className="mt-1 text-xs text-tec-muted">{detail}</p> : null}
      </div>
    </Card>
  );
}
