import { useEffect, useMemo, useState } from "react";
import { CreditCard, Plus, ReceiptText, Trash2 } from "lucide-react";

import type { PosPaymentMode, PosSalePaymentPayload } from "../api";
import { Button, Modal } from "../ui";
import { brl } from "./types";

const PAYMENT_MODES: PosPaymentMode[] = ["Pix", "Dinheiro", "Débito", "Crédito à vista", "Crédito parcelado"];

interface CheckoutModalProps {
  customerName: string;
  loading: boolean;
  onClose: () => void;
  onConfirm: (payments: PosSalePaymentPayload[]) => void;
  open: boolean;
  total: number;
}

interface PaymentDraft extends PosSalePaymentPayload {
  id: number;
}

export function CheckoutModal({ customerName, loading, onClose, onConfirm, open, total }: CheckoutModalProps) {
  const [payments, setPayments] = useState<PaymentDraft[]>([]);
  const [nextId, setNextId] = useState(2);

  useEffect(() => {
    if (open) {
      setPayments([{ amount: total, id: 1, installments: 1, mode_of_payment: "Pix" }]);
      setNextId(2);
    }
  }, [open, total]);

  const paid = useMemo(() => payments.reduce((sum, payment) => sum + (Number(payment.amount) || 0), 0), [payments]);
  const remaining = Number((total - paid).toFixed(2));
  const balanced = Math.abs(remaining) <= 0.01 && payments.length > 0;

  const updatePayment = (id: number, patch: Partial<PaymentDraft>) => {
    setPayments((current) => current.map((payment) => payment.id === id ? { ...payment, ...patch } : payment));
  };

  const addPayment = () => {
    const amount = Math.max(remaining, 0);
    setPayments((current) => [...current, { amount, id: nextId, installments: 1, mode_of_payment: "Dinheiro" }]);
    setNextId((current) => current + 1);
  };

  return (
    <Modal className="max-w-2xl" onClose={loading ? () => undefined : onClose} open={open} title="Finalizar venda">
      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
        <section className="space-y-3">
          <div className="rounded-control border border-tec-border/15 bg-tec-field/60 p-3">
            <p className="text-xs font-semibold text-tec-muted">Cliente</p>
            <p className="mt-1 font-bold text-white">{customerName}</p>
          </div>

          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-white">Formas de pagamento</h3>
              <p className="text-xs text-tec-muted">Combine Pix, dinheiro e cartão na mesma venda.</p>
            </div>
            <Button disabled={loading} icon={<Plus size={16} />} onClick={addPayment}>Adicionar</Button>
          </div>

          <div className="space-y-2">
            {payments.map((payment, index) => (
              <div className="grid gap-2 rounded-control border border-tec-border/15 bg-tec-field/45 p-3 sm:grid-cols-[minmax(0,1fr)_130px_auto]" key={payment.id}>
                <label>
                  <span className="mb-1 block text-[11px] font-semibold text-tec-muted">Forma {index + 1}</span>
                  <select
                    className="h-11 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-white outline-none focus:border-tec-orange/70"
                    disabled={loading}
                    onChange={(event) => {
                      const mode = event.target.value as PosPaymentMode;
                      updatePayment(payment.id, { installments: mode === "Crédito parcelado" ? 2 : 1, mode_of_payment: mode });
                    }}
                    value={payment.mode_of_payment}
                  >
                    {PAYMENT_MODES.map((mode) => <option key={mode} value={mode}>{mode}</option>)}
                  </select>
                </label>
                <label>
                  <span className="mb-1 block text-[11px] font-semibold text-tec-muted">Valor</span>
                  <input
                    className="h-11 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 text-right text-sm font-bold text-white outline-none focus:border-tec-orange/70"
                    disabled={loading}
                    min="0.01"
                    onChange={(event) => updatePayment(payment.id, { amount: Number(event.target.value) || 0 })}
                    step="0.01"
                    type="number"
                    value={payment.amount}
                  />
                </label>
                <div className="flex items-end gap-2">
                  {payment.mode_of_payment === "Crédito parcelado" ? (
                    <label>
                      <span className="mb-1 block text-[11px] font-semibold text-tec-muted">Parcelas</span>
                      <input
                        className="h-11 w-16 rounded-control border border-tec-border/20 bg-tec-field px-2 text-center text-sm font-bold text-white outline-none focus:border-tec-orange/70"
                        disabled={loading}
                        max="24"
                        min="2"
                        onChange={(event) => updatePayment(payment.id, { installments: Math.max(2, Number(event.target.value) || 2) })}
                        type="number"
                        value={payment.installments}
                      />
                    </label>
                  ) : null}
                  <Button
                    disabled={loading || payments.length === 1}
                    icon={<Trash2 size={16} />}
                    onClick={() => setPayments((current) => current.filter((row) => row.id !== payment.id))}
                    title="Remover forma de pagamento"
                    variant="ghost"
                  >
                    <span className="sr-only">Remover</span>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>

        <aside className="rounded-card border border-tec-border/15 bg-tec-field/55 p-4">
          <CreditCard className="text-tec-orange" size={24} />
          <p className="mt-4 text-xs font-semibold uppercase text-tec-muted">Total da venda</p>
          <p className="mt-1 text-3xl font-bold text-white">{brl.format(total)}</p>
          <div className="mt-5 space-y-2 border-t border-tec-border/15 pt-4 text-sm">
            <p className="flex justify-between text-tec-subtle"><span>Informado</span><strong className="text-white">{brl.format(paid)}</strong></p>
            <p className={`flex justify-between font-bold ${balanced ? "text-tec-green" : "text-tec-amber"}`}>
              <span>{remaining >= 0 ? "Falta" : "Excedente"}</span>
              <span>{brl.format(Math.abs(remaining))}</span>
            </p>
          </div>
          <p className="mt-5 text-xs leading-5 text-tec-muted">Cartão é lançado em Recebíveis de Cartão; estoque e piso de custo são validados no servidor.</p>
        </aside>
      </div>

      <div className="mt-5 flex flex-col-reverse gap-2 border-t border-tec-border/15 pt-4 sm:flex-row sm:justify-end">
        <Button disabled={loading} onClick={onClose}>Voltar</Button>
        <Button
          disabled={!balanced || loading}
          icon={<ReceiptText size={17} />}
          onClick={() => onConfirm(payments.map(({ id: _id, ...payment }) => payment))}
          variant="primary"
        >
          {loading ? "Processando..." : "Confirmar e gerar cupom"}
        </Button>
      </div>
    </Modal>
  );
}
