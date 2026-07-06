import type { ReactNode } from "react";

import { cx } from "./utils";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return <section className={cx("tp-panel rounded-card", className)}>{children}</section>;
}

interface MetricCardProps {
  icon: ReactNode;
  label: string;
  value: string | number;
  detail?: string;
  tone?: "orange" | "green" | "blue" | "purple" | "amber" | "red";
}

const toneClasses = {
  orange: "bg-tec-orange/20 text-tec-orange",
  green: "bg-tec-green/20 text-tec-green",
  blue: "bg-tec-blue/20 text-tec-blue",
  purple: "bg-tec-purple/20 text-tec-purple",
  amber: "bg-tec-amber/20 text-tec-amber",
  red: "bg-tec-red/20 text-tec-red",
};

export function MetricCard({ detail, icon, label, tone = "orange", value }: MetricCardProps) {
  return (
    <Card className="flex min-h-[104px] items-center gap-4 p-4">
      <div className={cx("grid h-11 w-11 shrink-0 place-items-center rounded-card", toneClasses[tone])}>{icon}</div>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-tec-subtle">{label}</p>
        <p className="mt-1 text-2xl font-bold text-tec-text">{value}</p>
        {detail ? <p className="mt-1 text-xs text-tec-muted">{detail}</p> : null}
      </div>
    </Card>
  );
}
