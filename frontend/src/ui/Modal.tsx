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
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4">
      <section className={`tp-panel w-full rounded-card ${className ?? "max-w-2xl"}`}>
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
