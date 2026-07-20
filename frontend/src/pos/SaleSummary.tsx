import type { Ref } from "react";
import { CreditCard, LockKeyhole, UserPlus, UserRound } from "lucide-react";

import type { CustomerSummary } from "../api";
import { Button, Card } from "../ui";
import { brl } from "./types";

interface SaleSummaryProps {
  customer: CustomerSummary | null;
  discount: number;
  discountRef: Ref<HTMLInputElement>;
  onClearDiscount: () => void;
  onDiscountChange: (value: number) => void;
  onFinalize: () => void;
  onIdentifyCustomer: () => void;
  onPercentDiscount: (percent: number) => void;
  subtotal: number;
  total: number;
}

export function SaleSummary({
  customer,
  discount,
  discountRef,
  onClearDiscount,
  onDiscountChange,
  onFinalize,
  onIdentifyCustomer,
  onPercentDiscount,
  subtotal,
  total,
}: SaleSummaryProps) {
  const cartEmpty = subtotal <= 0;
  return (
    <Card className="p-5">
      <div className="border-b border-tec-border/15 pb-4">
        <h2 className="text-xl font-bold text-white">Resumo da venda</h2>
        <p className="mt-1 text-xs text-tec-muted">Validação final feita pelo motor</p>
      </div>

      <div className="space-y-4 py-5">
        <div className="flex justify-between gap-3 text-sm text-tec-subtle">
          <span>Subtotal</span>
          <strong className="text-white">{brl.format(subtotal)}</strong>
        </div>
        <label className="block">
          <span className="mb-2 block text-xs font-semibold text-tec-subtle">Desconto <span className="text-tec-muted">(opcional)</span></span>
          <div className="flex h-11 items-center rounded-control border border-tec-border/20 bg-tec-field focus-within:border-tec-orange/70">
            <span className="grid h-full place-items-center border-r border-tec-border/15 px-3 text-sm font-bold text-tec-muted">R$</span>
            <input
              aria-label="Desconto da venda"
              className="min-w-0 flex-1 bg-transparent px-3 text-right text-sm font-bold text-white outline-none"
              data-testid="pos-discount-input"
              min="0"
              onChange={(event) => onDiscountChange(Number(event.target.value) || 0)}
              ref={discountRef}
              step="0.01"
              type="number"
              value={discount || ""}
            />
          </div>
          <div className="mt-2 grid grid-cols-4 gap-2">
            {[5, 10, 15].map((percent) => (
              <button className="min-h-9 rounded-[9px] border border-tec-border/20 bg-tec-field text-xs font-bold text-tec-subtle transition hover:border-tec-orange/50 hover:text-white" key={percent} onClick={() => onPercentDiscount(percent)} type="button">
                {percent}%
              </button>
            ))}
            <button className="min-h-9 rounded-[9px] border border-tec-border/20 bg-tec-field text-xs font-bold text-tec-muted transition hover:text-white" onClick={onClearDiscount} type="button">Limpar</button>
          </div>
        </label>
      </div>

      <div className="border-y border-tec-border/15 py-5 text-right">
        {discount > 0 ? <p className="text-xs text-tec-muted line-through">{brl.format(subtotal)}</p> : null}
        <p className="text-xs font-bold uppercase text-tec-muted">Total</p>
        <p className="mt-1 text-4xl font-bold text-tec-orange" data-testid="pos-cart-total">{brl.format(total)}</p>
      </div>

      <div className="mt-4 space-y-2">
        <div className="flex items-center gap-3 rounded-control border border-tec-border/15 bg-tec-field/65 p-3">
          <UserRound className="text-tec-muted" size={18} />
          <div className="min-w-0">
            <p className="text-xs font-bold text-white">{customer?.customer_name ?? "Consumidor final"}</p>
            <p className="truncate text-[11px] text-tec-muted">{customer ? customer.mobile_no || customer.custom_whatsapp || customer.name : "Venda avulsa, sem identificação"}</p>
          </div>
          {!customer ? (
            <button className="ml-auto inline-flex shrink-0 items-center gap-1 text-[11px] font-bold text-tec-orange transition hover:text-tec-orange/80" onClick={onIdentifyCustomer} type="button">
              <UserPlus size={13} /> Identificar <kbd className="rounded bg-tec-panel px-1 py-0.5 text-[9px] text-tec-muted">F2</kbd>
            </button>
          ) : null}
        </div>
        <div className="flex items-center gap-3 rounded-control border border-tec-border/15 bg-tec-field/65 p-3">
          <CreditCard className="text-tec-muted" size={18} />
          <div>
            <p className="text-xs font-bold text-white">Pagamento após finalizar</p>
            <p className="text-[11px] text-tec-muted">Dinheiro / Pix / Cartão</p>
          </div>
        </div>
      </div>

      <Button className="mt-4 w-full" disabled={cartEmpty} onClick={onFinalize} variant="primary">
        <span className="rounded-[7px] bg-tec-ink/10 px-1.5 py-0.5 text-[11px]">F5</span>
        Finalizar venda
      </Button>
      <p className="mt-3 flex items-start gap-2 text-xs leading-5 text-tec-muted">
        <LockKeyhole className="mt-0.5 shrink-0" size={14} />
        O piso de custo será validado no servidor ao finalizar.
      </p>
    </Card>
  );
}
