import { CheckCircle2, XCircle } from "lucide-react";

interface ToastProps {
  message: string;
  tone?: "success" | "error";
}

export function Toast({ message, tone = "success" }: ToastProps) {
  const Icon = tone === "success" ? CheckCircle2 : XCircle;
  const color = tone === "success" ? "text-tec-green" : "text-tec-red";

  return (
    <div className="fixed bottom-4 right-4 z-50 flex min-h-12 items-center gap-3 rounded-card border border-tec-border/25 bg-tec-panel-strong px-4 text-sm font-semibold text-white shadow-panel">
      <Icon className={color} size={18} />
      {message}
    </div>
  );
}
