import type { FormEvent, KeyboardEvent, Ref } from "react";
import { AlertCircle, Barcode, LoaderCircle, Search } from "lucide-react";

import { Card } from "../ui";
import { cx } from "../ui/utils";
import type { PosScanFeedback, PosScanStatus, PosSearchStatus } from "./types";

interface AddProductPanelProps {
  barcode: string;
  barcodeRef: Ref<HTMLInputElement>;
  manualRef: Ref<HTMLInputElement>;
  onBarcodeChange: (value: string) => void;
  onBarcodeKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
  onBarcodeSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onManualFocus: () => void;
  onManualKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
  onQueryChange: (value: string) => void;
  onSwitchToManual: () => void;
  query: string;
  scanFeedback: PosScanFeedback;
  scanStatus: PosScanStatus;
  searchStatus: PosSearchStatus;
}

export function AddProductPanel({
  barcode,
  barcodeRef,
  manualRef,
  onBarcodeChange,
  onBarcodeKeyDown,
  onBarcodeSubmit,
  onManualFocus,
  onManualKeyDown,
  onQueryChange,
  onSwitchToManual,
  query,
  scanFeedback,
  scanStatus,
  searchStatus,
}: AddProductPanelProps) {
  return (
    <Card className="overflow-hidden p-0">
      <div className="border-b border-tec-border/15 px-5 py-4">
        <h2 className="text-xl font-bold text-white">Adicionar produto</h2>
      </div>
      <div className="grid xl:grid-cols-2">
        <section className="border-b border-tec-border/15 xl:border-b-0 xl:border-r">
          <div className="flex min-h-12 items-center gap-3 border-b-2 border-tec-orange px-4 text-sm font-bold text-white">
            <Barcode className="text-tec-orange" size={19} />
            Bipe (código de barras)
          </div>
          <form className="p-4" onSubmit={onBarcodeSubmit}>
            <label className="relative block">
              <span className="sr-only">Código de barras</span>
              <Barcode className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-tec-muted" size={19} />
              <input
                aria-describedby="pos-barcode-feedback"
                autoComplete="off"
                className="h-12 w-full rounded-control border border-tec-border/25 bg-tec-field pl-11 pr-36 text-base font-semibold text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange focus:ring-2 focus:ring-tec-orange/15"
                data-testid="pos-barcode-input"
                onChange={(event) => onBarcodeChange(event.target.value)}
                onKeyDown={onBarcodeKeyDown}
                placeholder="Aguardando bipe..."
                ref={barcodeRef}
                type="text"
                value={barcode}
              />
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[11px] font-semibold text-tec-muted">
                Enter para adicionar
              </span>
            </label>

            {scanStatus === "error" ? (
              <div
                className="mt-3 flex items-start gap-3 rounded-control border border-tec-red/30 bg-tec-red/10 p-3"
                data-testid="pos-scan-feedback"
                id="pos-barcode-feedback"
                role="alert"
              >
                <AlertCircle className="mt-0.5 shrink-0 text-tec-red" size={18} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-bold text-white">{scanFeedback.title}</p>
                  <p className="mt-1 text-xs leading-5 text-tec-subtle">{scanFeedback.detail}</p>
                  <button
                    className="mt-2 text-xs font-bold text-tec-orange hover:text-tec-digital-orange"
                    onClick={onSwitchToManual}
                    type="button"
                  >
                    Buscar manualmente
                  </button>
                </div>
              </div>
            ) : (
              <div
                className={cx(
                  "mt-3 flex min-h-10 items-center gap-2 text-xs font-medium",
                  scanStatus === "success" ? "text-tec-success" : "text-tec-muted",
                )}
                data-testid="pos-scan-feedback"
                id="pos-barcode-feedback"
                role="status"
              >
                {scanStatus === "loading" ? <LoaderCircle className="animate-spin" size={15} /> : null}
                <span>
                  {scanStatus === "success" ? `${scanFeedback.title} — ${scanFeedback.detail}` : scanFeedback.detail}
                </span>
              </div>
            )}
          </form>
        </section>

        <section>
          <div className="flex min-h-12 items-center gap-3 border-b border-tec-border/15 px-4 text-sm font-bold text-tec-subtle">
            <Search size={19} />
            Busca manual
          </div>
          <div className="p-4">
            <label className="relative block">
              <span className="sr-only">Buscar produto por nome, SKU ou referência</span>
              <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-tec-muted" size={18} />
              <input
                aria-controls="pos-product-results"
                aria-expanded={query.trim().length >= 2}
                className="h-12 w-full rounded-control border border-tec-border/25 bg-tec-field pl-11 pr-11 text-sm font-medium text-tec-text outline-none transition placeholder:text-tec-muted focus:border-tec-orange/70 focus:ring-2 focus:ring-tec-orange/10"
                data-testid="pos-name-input"
                onChange={(event) => onQueryChange(event.target.value)}
                onFocus={onManualFocus}
                onKeyDown={onManualKeyDown}
                placeholder="Buscar por nome, SKU ou referência"
                ref={manualRef}
                type="search"
                value={query}
              />
              {searchStatus === "loading" ? (
                <LoaderCircle className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 animate-spin text-tec-orange" size={17} />
              ) : null}
            </label>
            <p className="mt-3 text-xs text-tec-muted">Ex.: Película 3D, Cabo USB-C, TP-PDV-001...</p>
            <p className="mt-1 text-[11px] text-tec-muted">↑ ↓ navegam · Enter adiciona · Esc limpa</p>
          </div>
        </section>
      </div>
    </Card>
  );
}
