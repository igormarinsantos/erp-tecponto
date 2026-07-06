import { cx } from "./utils";

type BadgeTone = "orange" | "green" | "blue" | "purple" | "amber" | "red" | "slate";

const statusTone: Record<string, BadgeTone> = {
  "Entrada criada": "blue",
  "Em diagnóstico": "orange",
  "Aguardando aprovação": "amber",
  Aprovado: "green",
  Reprovado: "red",
  "Orçamento expirado": "red",
  "Aguardando peça": "purple",
  "Em reparo": "blue",
  "Teste final": "green",
  "Pronto para retirada": "green",
  Entregue: "green",
  "Sem conserto": "slate",
  Cancelado: "slate",
};

const toneClasses: Record<BadgeTone, string> = {
  orange: "bg-tec-orange/20 text-tec-orange ring-tec-orange/25",
  green: "bg-tec-green/20 text-tec-green ring-tec-green/25",
  blue: "bg-tec-blue/20 text-tec-blue ring-tec-blue/25",
  purple: "bg-tec-purple/20 text-tec-purple ring-tec-purple/25",
  amber: "bg-tec-amber/20 text-tec-amber ring-tec-amber/25",
  red: "bg-tec-red/20 text-tec-red ring-tec-red/25",
  slate: "bg-slate-400/10 text-slate-300 ring-slate-400/20",
};

export function BadgeStatus({ status }: { status?: string | null }) {
  const label = status || "Sem status";
  const tone = statusTone[label] ?? "slate";
  return (
    <span
      className={cx(
        "inline-flex min-h-7 max-w-full items-center rounded-full px-3 text-xs font-semibold ring-1",
        toneClasses[tone],
      )}
      title={label}
    >
      {label}
    </span>
  );
}
