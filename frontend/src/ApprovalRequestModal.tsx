import { useEffect, useState } from "react";

import { approvalRequests } from "./api";
import { Button, Modal } from "./ui";

type Toast = (message: string, tone?: "success" | "error") => void;

interface ApprovalRequestModalProps {
  approver?: string;
  onClose: () => void;
  onCreated: () => void;
  onToast: Toast;
  open: boolean;
  payload: Record<string, unknown>;
  referenceName: string;
  requestType: string;
  title: string;
}

export function ApprovalRequestModal({
  approver = "Gestor",
  onClose,
  onCreated,
  onToast,
  open,
  payload,
  referenceName,
  requestType,
  title,
}: ApprovalRequestModalProps) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setReason("");
    }
  }, [open]);

  const submit = async () => {
    if (!reason.trim()) {
      return;
    }

    setBusy(true);
    try {
      await approvalRequests.create(requestType, referenceName, reason.trim(), payload);
      onToast("Solicitação enviada, aguardando o Gestor.", "success");
      onCreated();
      onClose();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível enviar a solicitação.", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal className="max-w-lg" onClose={onClose} open={open} title="Solicitar aprovação">
      <p className="text-sm leading-6 text-tec-subtle">{title}</p>
      <p className="mt-2 text-sm text-tec-muted">Quem pode aprovar: <strong className="text-white">{approver}</strong></p>
      <label className="mt-5 block text-sm font-bold text-white">
        Motivo obrigatório
        <textarea
          className="mt-2 min-h-28 w-full rounded-control border border-tec-border/25 bg-tec-field p-3 text-white outline-none focus:border-tec-orange/70"
          onChange={(event) => setReason(event.target.value)}
          placeholder="Explique por que esta exceção é necessária."
          value={reason}
        />
      </label>
      <div className="mt-5 flex justify-end gap-2">
        <Button onClick={onClose} variant="ghost">Cancelar</Button>
        <Button disabled={!reason.trim() || busy} onClick={() => void submit()} variant="primary">
          {busy ? "Enviando..." : "Solicitar aprovação"}
        </Button>
      </div>
    </Modal>
  );
}
