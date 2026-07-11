import { Barcode, Package, Plus, SearchX } from "lucide-react";

import type { PosItemSummary } from "../api";
import { Card } from "../ui";
import { cx } from "../ui/utils";
import { brl, type PosCartLine, type PosSearchStatus } from "./types";

interface ProductSearchResultsProps {
  cart: PosCartLine[];
  onAdd: (item: PosItemSummary, source: "click" | "keyboard") => void;
  onSelect: (index: number) => void;
  onShowAll: () => void;
  query: string;
  results: PosItemSummary[];
  selectedIndex: number;
  status: PosSearchStatus;
}

export function ProductSearchResults({
  cart,
  onAdd,
  onSelect,
  onShowAll,
  query,
  results,
  selectedIndex,
  status,
}: ProductSearchResultsProps) {
  const message =
    status === "error"
      ? "Não foi possível consultar os produtos. Verifique a conexão e tente novamente."
      : query.trim().length < 2
        ? "Digite ao menos 2 caracteres para buscar por nome, SKU ou referência."
        : "Nenhum produto encontrado para esta busca.";

  return (
    <div id="pos-product-results">
    <Card className="overflow-hidden p-0">
      <header className="flex items-center justify-between gap-3 border-b border-tec-border/15 px-5 py-4">
        <h2 className="text-xl font-bold text-white">Resultados da busca</h2>
        <span className="rounded-[8px] border border-tec-border/15 bg-tec-field px-2.5 py-1 text-xs font-bold text-tec-muted">
          {results.length} resultado(s)
        </span>
      </header>

      {status === "loading" ? (
        <div className="space-y-2 p-4" aria-label="Carregando produtos">
          {[0, 1, 2].map((value) => (
            <div className="h-16 animate-pulse rounded-control bg-tec-field/70" key={value} />
          ))}
        </div>
      ) : results.length ? (
        <div role="listbox">
          <div className="hidden grid-cols-[minmax(0,1.45fr)_150px_100px_90px_106px] gap-3 border-b border-tec-border/10 px-5 py-2 text-[11px] font-bold uppercase text-tec-muted lg:grid">
            <span>Produto</span>
            <span>SKU / Referência</span>
            <span>Estoque</span>
            <span>Preço</span>
            <span className="text-right">Ação</span>
          </div>
          {results.map((item, index) => {
            const qtyInCart = cart.find((line) => line.item_code === item.item_code)?.qty ?? 0;
            const outOfStock = item.available_qty <= qtyInCart;
            const lowStock = !outOfStock && item.available_qty - qtyInCart <= 3;
            const disabled = !item.has_price || outOfStock;
            return (
              <div
                aria-selected={selectedIndex === index}
                className={cx(
                  "grid gap-3 border-b border-tec-border/10 px-5 py-3 transition last:border-b-0 lg:grid-cols-[minmax(0,1.45fr)_150px_100px_90px_106px] lg:items-center",
                  selectedIndex === index ? "bg-tec-orange/8" : "hover:bg-tec-field/45",
                )}
                data-testid={`pos-result-${item.item_code}`}
                key={item.item_code}
                onClick={() => onSelect(index)}
                onDoubleClick={() => !disabled && onAdd(item, "click")}
                role="option"
              >
                <div className="flex min-w-0 items-center gap-3">
                  {item.image ? (
                    <img alt="" className="h-11 w-11 shrink-0 rounded-[8px] border border-tec-border/15 bg-white object-contain" src={item.image} />
                  ) : (
                    <span className="grid h-11 w-11 shrink-0 place-items-center rounded-[8px] bg-tec-field text-tec-orange">
                      <Package size={19} />
                    </span>
                  )}
                  <div className="min-w-0">
                    <span className="block truncate text-sm font-bold text-white">{item.item_name ?? item.item_code}</span>
                    <div className="mt-1 flex min-w-0 items-center gap-2">
                      <span className="shrink-0 rounded-[6px] bg-tec-orange/10 px-1.5 py-0.5 text-[10px] font-bold text-tec-orange">{item.item_group ?? "Produto"}</span>
                      <p className="truncate text-xs text-tec-muted">{item.description || "Produto disponível para venda no balcão."}</p>
                    </div>
                  </div>
                </div>
                <div className="min-w-0 text-xs text-tec-subtle">
                  <span className="block truncate font-semibold text-white">{item.item_code}</span>
                  {item.barcode ? (
                    <span className="mt-1 flex items-center gap-1 text-tec-muted"><Barcode size={13} />{item.barcode}</span>
                  ) : null}
                </div>
                <div className="text-xs">
                  <span className="block font-bold text-white">{item.available_qty.toLocaleString("pt-BR")} un.</span>
                  <span className={cx("mt-1 block font-semibold", outOfStock ? "text-tec-red" : lowStock ? "text-tec-amber" : "text-tec-success")}> 
                    {outOfStock ? "Sem estoque" : lowStock ? "Estoque baixo" : "Disponível"}
                  </span>
                </div>
                <strong className="text-sm text-white">{item.has_price ? brl.format(item.standard_rate) : "Sem preço"}</strong>
                <button
                  className="inline-flex min-h-10 items-center justify-center gap-2 rounded-control border border-tec-orange px-3 text-xs font-bold text-tec-orange transition hover:bg-tec-orange hover:text-tec-ink disabled:cursor-not-allowed disabled:border-tec-border/20 disabled:text-tec-muted"
                  disabled={disabled}
                  onClick={(event) => {
                    event.stopPropagation();
                    onAdd(item, "click");
                  }}
                  title={disabled ? "Produto sem preço ou saldo no Comercial" : `Adicionar ${item.item_name ?? item.item_code}`}
                  type="button"
                >
                  <Plus size={16} />
                  Adicionar
                </button>
              </div>
            );
          })}
          {results.length >= 12 ? (
            <div className="border-t border-tec-border/10 p-3 text-center">
              <button className="min-h-10 rounded-control border border-tec-border/20 px-4 text-xs font-bold text-tec-subtle hover:border-tec-orange/40 hover:text-white" onClick={onShowAll} type="button">
                Ver todos os resultados
              </button>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="grid min-h-32 place-items-center p-6 text-center">
          <div>
            <SearchX className="mx-auto text-tec-muted" size={25} />
            <p className="mt-2 text-sm font-semibold text-tec-subtle">{message}</p>
          </div>
        </div>
      )}
    </Card>
    </div>
  );
}
