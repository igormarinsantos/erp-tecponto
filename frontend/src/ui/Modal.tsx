import type { ReactNode } from "react";
import { X } from "lucide-react";

import { Button } from "./Button";

interface ModalProps {
  children: ReactNode;
  className?: string;
  open: boolean;
  title: string;
  onClose: () => void;
}

export function Modal({ children, className, onClose, open, title }: ModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-tec-bg p-4">
      <section
        aria-label={title}
        aria-modal="true"
        className={`tp-panel my-4 w-full rounded-card bg-tec-panel ${className ?? "max-w-2xl"}`}
        role="dialog"
      >
        <header className="flex items-center justify-between border-b border-tec-border/20 p-4">
          <h2 className="text-lg font-bold text-white">{title}</h2>
          <Button icon={<X size={18} />} onClick={onClose} variant="ghost">
            Fechar
          </Button>
        </header>
        <div className="p-4">{children}</div>
      </section>
    </div>
  );
}
