import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cx } from "./utils";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode;
  variant?: ButtonVariant;
}

const variants: Record<ButtonVariant, string> = {
  primary: "bg-tec-orange text-white shadow-glow hover:bg-[rgb(var(--tp-orange-strong))]",
  secondary: "border border-tec-border/30 bg-tec-panel-strong/70 text-tec-text hover:border-tec-orange/50",
  ghost: "text-tec-subtle hover:bg-white/5 hover:text-tec-text",
  danger: "bg-tec-red/20 text-red-100 ring-1 ring-tec-red/40 hover:bg-tec-red/30",
};

export function Button({ children, className, icon, type = "button", variant = "secondary", ...props }: ButtonProps) {
  return (
    <button
      className={cx(
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-control px-4 text-sm font-semibold transition",
        "focus:outline-none focus:ring-2 focus:ring-tec-orange/70 disabled:cursor-not-allowed disabled:opacity-55",
        variants[variant],
        className,
      )}
      type={type}
      {...props}
    >
      {icon}
      <span>{children}</span>
    </button>
  );
}
