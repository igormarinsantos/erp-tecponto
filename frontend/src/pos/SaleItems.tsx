import { Minus, Package, Plus, ShoppingCart, Trash2 } from "lucide-react";

import { Card } from "../ui";
import { brl, type PosCartLine } from "./types";

interface SaleItemsProps {
  cart: PosCartLine[];
  onChangeQty: (itemCode: string, nextQty: number) => void;
  onRemove: (itemCode: string) => void;
  onRequestClear: () => void;
}

export function SaleItems({ cart, onChangeQty, onRemove, onRequestClear }: SaleItemsProps) {
  return (
    <Card className="overflow-hidden p-0">
      <header className="flex items-center justify-between gap-3 border-b border-tec-border/15 px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-control bg-tec-orange/12 text-tec-orange">
            <ShoppingCart size={18} />
          </span>
          <h2 className="text-xl font-bold text-white">Itens da venda</h2>
          <span className="rounded-[8px] bg-tec-field px-2 py-1 text-xs font-bold text-tec-muted">{cart.length} item(ns)</span>
        </div>
        {cart.length ? (
          <button
            className="inline-flex min-h-10 items-center gap-2 rounded-control border border-tec-border/20 px-3 text-xs font-bold text-tec-subtle transition hover:border-tec-red/40 hover:text-tec-red"
            onClick={onRequestClear}
            type="button"
          >
            <Trash2 size={16} />
            Limpar venda
          </button>
        ) : null}
      </header>

      {cart.length ? (
        <div data-testid="pos-cart-lines">
          <div className="hidden grid-cols-[minmax(0,1fr)_100px_118px_100px_42px] gap-3 border-b border-tec-border/10 px-5 py-2 text-[11px] font-bold uppercase text-tec-muted md:grid">
            <span>Produto</span>
            <span>Preço unit.</span>
            <span className="text-center">Qtde</span>
            <span className="text-right">Subtotal</span>
            <span />
          </div>
          {cart.map((line) => (
            <div className="grid gap-3 border-b border-tec-border/10 px-5 py-3 last:border-b-0 md:grid-cols-[minmax(0,1fr)_100px_118px_100px_42px] md:items-center" key={line.item_code}>
              <div className="flex min-w-0 items-center gap-3">
                {line.image ? (
                  <img alt="" className="h-11 w-11 shrink-0 rounded-[8px] border border-tec-border/15 bg-white object-contain" src={line.image} />
                ) : (
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-[8px] bg-tec-field text-tec-orange"><Package size={18} /></span>
                )}
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-white">{line.item_name ?? line.item_code}</p>
                  <p className="mt-1 truncate text-xs text-tec-muted">{line.item_code} · {line.item_group ?? "Produto"} · Comercial</p>
                </div>
              </div>
              <span className="text-sm font-semibold text-white">{brl.format(line.standard_rate)}</span>
              <div className="flex items-center rounded-control border border-tec-border/15 bg-tec-field p-1">
                <button
                  aria-label={`Diminuir quantidade de ${line.item_name ?? line.item_code}`}
                  className="grid h-8 w-8 place-items-center rounded-[8px] text-tec-muted transition hover:bg-tec-panel hover:text-white"
                  onClick={() => onChangeQty(line.item_code, line.qty - 1)}
                  type="button"
                >
                  <Minus size={15} />
                </button>
                <input
                  aria-label={`Quantidade de ${line.item_name ?? line.item_code}`}
                  className="h-8 min-w-0 flex-1 bg-transparent text-center text-sm font-bold text-white outline-none"
                  max={Math.floor(line.available_qty)}
                  min="1"
                  onChange={(event) => onChangeQty(line.item_code, Number(event.target.value) || 1)}
                  type="number"
                  value={line.qty}
                />
                <button
                  aria-label={`Aumentar quantidade de ${line.item_name ?? line.item_code}`}
                  className="grid h-8 w-8 place-items-center rounded-[8px] text-tec-muted transition hover:bg-tec-panel hover:text-white"
                  onClick={() => onChangeQty(line.item_code, line.qty + 1)}
                  type="button"
                >
                  <Plus size={15} />
                </button>
              </div>
              <strong className="text-right text-sm text-white">{brl.format(line.standard_rate * line.qty)}</strong>
              <button
                aria-label={`Excluir ${line.item_name ?? line.item_code} da venda`}
                className="grid h-10 w-10 place-items-center rounded-control text-tec-muted transition hover:bg-tec-red/15 hover:text-tec-red"
                onClick={() => onRemove(line.item_code)}
                title="Excluir item"
                type="button"
              >
                <Trash2 size={17} />
              </button>
            </div>
          ))}
          <div className="m-4 flex min-h-12 items-center justify-center gap-2 rounded-control border border-dashed border-tec-border/25 text-xs font-medium text-tec-muted">
            <ShoppingCart size={16} />
            Bipe outro produto ou use a busca acima para adicionar.
          </div>
        </div>
      ) : (
        <div className="grid min-h-48 place-items-center p-8 text-center">
          <div>
            <ShoppingCart className="mx-auto text-tec-muted" size={31} />
            <p className="mt-3 font-bold text-white">Nenhum item adicionado</p>
            <p className="mt-1 text-sm text-tec-muted">Bipe um código ou busque um produto para iniciar a venda.</p>
          </div>
        </div>
      )}
    </Card>
  );
}
