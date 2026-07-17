import { type FormEvent, type KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, ExternalLink, Percent, RefreshCw, UserRound } from "lucide-react";

import { pos, type CashierOperatorIdentity, type CustomerSummary, type PosItemSummary, type PosSalePaymentPayload, type PosSaleResponse } from "./api";
import { ApprovalRequestModal } from "./ApprovalRequestModal";
import { Button, Modal } from "./ui";
import { AddProductPanel } from "./pos/AddProductPanel";
import { CheckoutModal } from "./pos/CheckoutModal";
import { CustomerPickerModal } from "./pos/CustomerPickerModal";
import { KeyboardShortcuts } from "./pos/KeyboardShortcuts";
import { ProductSearchResults } from "./pos/ProductSearchResults";
import { SaleItems } from "./pos/SaleItems";
import { SaleSummary } from "./pos/SaleSummary";
import type { PosCartLine, PosScanFeedback, PosScanStatus, PosSearchStatus, PosToast } from "./pos/types";

interface PosScreenProps {
	 cashierMode?: boolean;
	 cashierOperator?: CashierOperatorIdentity | null;
  initialBarcode?: { code: string; id: number } | null;
	 onCashierSaleCompleted?: (sale: PosSaleResponse) => void;
  onInitialBarcodeHandled?: () => void;
  onRegisterUnknownBarcode?: (barcode: string) => void;
  onToast: PosToast;
}

const INITIAL_SCAN_FEEDBACK: PosScanFeedback = {
  detail: "Bipe o produto; o leitor envia o código e confirma com Enter.",
  title: "Leitor aguardando",
};

export function PosScreen({ cashierMode = false, cashierOperator = null, initialBarcode, onCashierSaleCompleted, onInitialBarcodeHandled, onRegisterUnknownBarcode, onToast }: PosScreenProps) {
  const barcodeRef = useRef<HTMLInputElement>(null);
  const manualRef = useRef<HTMLInputElement>(null);
  const discountRef = useRef<HTMLInputElement>(null);
  const searchRequestRef = useRef(0);
  const idempotencyRef = useRef<{ fingerprint: string; key: string } | null>(null);
  const initialBarcodeRef = useRef<number | null>(null);
  const [barcode, setBarcode] = useState("");
  const [scanFeedback, setScanFeedback] = useState<PosScanFeedback>(INITIAL_SCAN_FEEDBACK);
  const [scanStatus, setScanStatus] = useState<PosScanStatus>("idle");
  const [query, setQuery] = useState("");
  const [searchStatus, setSearchStatus] = useState<PosSearchStatus>("idle");
  const [results, setResults] = useState<PosItemSummary[]>([]);
  const [selectedResult, setSelectedResult] = useState(0);
  const [searchLimit, setSearchLimit] = useState(12);
  const [searchRefresh, setSearchRefresh] = useState(0);
  const [cart, setCart] = useState<PosCartLine[]>([]);
  const [discount, setDiscount] = useState(0);
  const [customer, setCustomer] = useState<CustomerSummary | null>(null);
  const [customerOpen, setCustomerOpen] = useState(false);
  const [clearConfirmOpen, setClearConfirmOpen] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [completedSale, setCompletedSale] = useState<PosSaleResponse | null>(null);
  const [saleApproval, setSaleApproval] = useState<{
    payload: Record<string, unknown>;
    referenceName: string;
		requestType: "pos_discount" | "pos_price_floor";
		title: string;
  } | null>(null);

  const subtotal = useMemo(() => cart.reduce((sum, line) => sum + line.standard_rate * line.qty, 0), [cart]);
  const total = Math.max(subtotal - discount, 0);

  const focusScanner = useCallback((force = false) => {
    window.requestAnimationFrame(() => {
      const active = document.activeElement;
      const editing = active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement || active instanceof HTMLSelectElement;
      if (force || !editing) {
        barcodeRef.current?.focus();
      }
    });
  }, []);

  useEffect(() => {
    focusScanner(true);
  }, [focusScanner]);

  useEffect(() => {
    const normalized = query.trim();
    if (normalized.length < 2) {
      setResults([]);
      setSearchStatus("idle");
      setSelectedResult(0);
      return;
    }

    const requestId = ++searchRequestRef.current;
    setSearchStatus("loading");
    const timer = window.setTimeout(() => {
      pos.searchItems({ limit: searchLimit, query: normalized })
        .then((response) => {
          if (requestId !== searchRequestRef.current) {
            return;
          }
          setResults(response.items);
          setSelectedResult(0);
          setSearchStatus("ready");
        })
        .catch((error) => {
          if (requestId !== searchRequestRef.current) {
            return;
          }
          setResults([]);
          setSearchStatus("error");
          onToast(error instanceof Error ? error.message : "Falha ao consultar produtos.", "error");
        });
    }, 280);

    return () => window.clearTimeout(timer);
  }, [onToast, query, searchLimit, searchRefresh]);

  useEffect(() => {
    if (discount > subtotal) {
      setDiscount(subtotal);
    }
  }, [discount, subtotal]);

  const addItem = useCallback((item: PosItemSummary, source: "scanner" | "click" | "keyboard") => {
    if (!item.has_price || item.standard_rate <= 0) {
      onToast("Produto sem preço de venda cadastrado.", "error");
      return false;
    }

    const currentQty = cart.find((line) => line.item_code === item.item_code)?.qty ?? 0;
    if (currentQty + 1 > item.available_qty) {
      onToast("Estoque Comercial insuficiente para adicionar este produto.", "error");
      return false;
    }

    setCart((current) => {
      const existing = current.find((line) => line.item_code === item.item_code);
      return existing
        ? current.map((line) => line.item_code === item.item_code ? { ...line, qty: line.qty + 1 } : line)
        : [...current, { ...item, qty: 1 }];
    });
    onToast(`${item.item_name ?? item.item_code} adicionado à venda.`);
    if (source === "click") {
      focusScanner();
    }
    return true;
  }, [cart, focusScanner, onToast]);

  const lookupBarcode = async (barcodeValue?: string) => {
    const scanned = (barcodeValue ?? barcode).trim();
    if (!scanned) {
      setScanStatus("error");
      setScanFeedback({ detail: "Digite ou bipe um código válido para continuar.", title: "Código não informado" });
      focusScanner(true);
      return;
    }

    setScanStatus("loading");
    setScanFeedback({ detail: "Consultando preço de venda e saldo no Comercial...", title: "Localizando produto" });
    try {
      const response = await pos.searchItems({ barcode: scanned, limit: 1 });
      const item = response.items[0];
      if (!item) {
        setScanStatus("error");
        setScanFeedback({
          detail: "Nenhum produto cadastrado com este código. Abra o cadastro com o código já preenchido.",
          title: "Código não encontrado",
        });
        onRegisterUnknownBarcode?.(scanned);
        return;
      }
      if (addItem(item, "scanner")) {
        setScanStatus("success");
        setScanFeedback({ detail: `${item.item_name ?? item.item_code} adicionado ao carrinho.`, title: "Código lido com sucesso" });
      } else {
        setScanStatus("error");
        setScanFeedback({ detail: "Confira preço e saldo do estoque Comercial.", title: "Produto não pôde ser adicionado" });
      }
    } catch (error) {
      setScanStatus("error");
      setScanFeedback({
        detail: error instanceof Error ? error.message : "Verifique a conexão e tente novamente.",
        title: "Falha ao consultar o produto",
      });
    } finally {
      setBarcode("");
      focusScanner(true);
    }
  };

  useEffect(() => {
    if (!initialBarcode || initialBarcodeRef.current === initialBarcode.id) {
      return;
    }
    initialBarcodeRef.current = initialBarcode.id;
    setBarcode(initialBarcode.code);
    void lookupBarcode(initialBarcode.code).finally(() => onInitialBarcodeHandled?.());
  }, [initialBarcode, onInitialBarcodeHandled]);

  const changeBarcode = (value: string) => {
    setBarcode(value);
    if (scanStatus === "error") {
      setScanStatus("idle");
      setScanFeedback(INITIAL_SCAN_FEEDBACK);
    }
  };

  const submitBarcode = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void lookupBarcode();
  };

  const handleBarcodeKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void lookupBarcode();
    }
  };

  const clearManualSearch = () => {
    searchRequestRef.current += 1;
    setQuery("");
    setResults([]);
    setSearchStatus("idle");
    setSelectedResult(0);
  };

  const changeQuery = (value: string) => {
    setQuery(value);
    setSearchLimit(12);
    if (scanStatus === "error") {
      setScanStatus("idle");
      setScanFeedback(INITIAL_SCAN_FEEDBACK);
    }
  };

  const handleManualKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      clearManualSearch();
      focusScanner(true);
      return;
    }
    if (!results.length) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setSelectedResult((current) => Math.min(current + 1, results.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setSelectedResult((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      addItem(results[selectedResult], "keyboard");
    }
  };

  const changeQty = (itemCode: string, nextQty: number) => {
    const line = cart.find((item) => item.item_code === itemCode);
    if (!line) {
      return;
    }
    if (nextQty > line.available_qty) {
      onToast(`Saldo disponível no Comercial: ${line.available_qty.toLocaleString("pt-BR")} unidade(s).`, "error");
      return;
    }
    setCart((current) => current.map((item) => item.item_code === itemCode ? { ...item, qty: Math.max(1, Math.floor(nextQty)) } : item));
  };

  const changeDiscount = (value: number) => {
    const normalized = Math.max(0, value);
    if (normalized > subtotal) {
      setDiscount(subtotal);
      onToast("O desconto não pode superar o subtotal da venda.", "error");
      return;
    }
    setDiscount(normalized);
  };

  const resetForNextSale = useCallback(() => {
    clearManualSearch();
    setBarcode("");
    setCart([]);
    setCustomer(null);
    setDiscount(0);
    setScanStatus("idle");
    setScanFeedback(INITIAL_SCAN_FEEDBACK);
    idempotencyRef.current = null;
    focusScanner(true);
  }, [focusScanner]);

  const handleFinalize = useCallback(() => {
    if (!cart.length) {
      return;
    }
    if (!customer) {
      onToast("Selecione o cliente antes de finalizar a venda.", "error");
      setCustomerOpen(true);
      return;
    }

    if (cashierMode && !cashierOperator?.token) {
      onToast("Identifique o operador pelo cracha ou PIN antes de finalizar.", "error");
      return;
    }
    setCheckoutOpen(true);
  }, [cart.length, cashierMode, cashierOperator?.token, customer, onToast]);

  const submitSale = async (payments: PosSalePaymentPayload[]) => {
    if (!customer || !cart.length || checkoutLoading) {
      return;
    }
    const requestWithoutKey = {
		cashier_operator_token: cashierOperator?.token,
      customer: customer.name,
      discount_amount: discount,
      items: cart.map((item) => ({ item_code: item.item_code, qty: item.qty })),
      payments,
    };
    const fingerprint = JSON.stringify(requestWithoutKey);
    if (!idempotencyRef.current || idempotencyRef.current.fingerprint !== fingerprint) {
      const random = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      idempotencyRef.current = { fingerprint, key: `tp-pos-${random}` };
    }
    const idempotencyKey = idempotencyRef.current.key;

    setCheckoutLoading(true);
    try {
      const response = await pos.createSale({ ...requestWithoutKey, idempotency_key: idempotencyKey });
      setCheckoutOpen(false);
		if (cashierMode) {
			resetForNextSale();
			onCashierSaleCompleted?.(response);
		} else {
			setCompletedSale(response);
			setCart([]);
			setDiscount(0);
			idempotencyRef.current = null;
			onToast(`Venda ${response.sale} concluída e cupom gerado.`, "success");
		}
    } catch (error) {
      const message = error instanceof Error ? error.message : "Não foi possível finalizar a venda.";
		if (message.includes("Desconto acima do limite") || message.includes("piso comercial")) {
        setCheckoutOpen(false);
		const isPriceFloor = message.includes("piso comercial");
		setSaleApproval({
          payload: { sale_payload: { ...requestWithoutKey, idempotency_key: idempotencyKey } },
          referenceName: customer.name,
			requestType: isPriceFloor ? "pos_price_floor" : "pos_discount",
			title: isPriceFloor
				? "Este preco nao atende ao piso comercial. Deseja solicitar aprovacao do Gestor?"
				: "Este desconto ultrapassa seu limite. Deseja solicitar aprovação do Gestor?",
        });
      } else {
        onToast(message, "error");
      }
    } finally {
      setCheckoutLoading(false);
    }
  };

  useEffect(() => {
    const handleShortcut = (event: globalThis.KeyboardEvent) => {
      if (event.key === "F2") {
        event.preventDefault();
        setCustomerOpen(true);
      } else if (event.key === "F3") {
        event.preventDefault();
        discountRef.current?.focus();
      } else if (event.key === "F5") {
        event.preventDefault();
        handleFinalize();
      }
    };
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, [handleFinalize]);

  return (
    <div className="space-y-4" data-testid="pos-screen">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white md:text-4xl">{cashierMode ? "Venda no caixa" : "PDV do balcão"}</h1>
          <p className="mt-1 text-sm text-tec-subtle">{cashierMode ? "Bipe os produtos e finalize. Ao concluir, o caixa volta pronto para a proxima venda." : "Venda rápida por código de barras ou busca de produto."}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button icon={<UserRound size={16} />} onClick={() => setCustomerOpen(true)}><kbd className="rounded-[6px] bg-tec-panel px-1.5 py-0.5 text-[10px]">F2</kbd> Cliente</Button>
          <Button icon={<Percent size={16} />} onClick={() => discountRef.current?.focus()}><kbd className="rounded-[6px] bg-tec-panel px-1.5 py-0.5 text-[10px]">F3</kbd> Desconto</Button>
          <Button icon={<RefreshCw size={17} />} onClick={() => {
            setSearchRefresh((current) => current + 1);
            setScanStatus("idle");
            setScanFeedback(INITIAL_SCAN_FEEDBACK);
            focusScanner(true);
          }}>Atualizar</Button>
        </div>
      </header>

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_294px]">
        <main className="min-w-0 space-y-4">
          <AddProductPanel
            barcode={barcode}
            barcodeRef={barcodeRef}
            manualRef={manualRef}
            onBarcodeChange={changeBarcode}
            onBarcodeKeyDown={handleBarcodeKeyDown}
            onBarcodeSubmit={submitBarcode}
            onManualFocus={() => {
              if (scanStatus === "error") {
                setScanStatus("idle");
                setScanFeedback(INITIAL_SCAN_FEEDBACK);
              }
            }}
            onManualKeyDown={handleManualKeyDown}
            onQueryChange={changeQuery}
            onSwitchToManual={() => {
              setScanStatus("idle");
              setScanFeedback(INITIAL_SCAN_FEEDBACK);
              manualRef.current?.focus();
            }}
            query={query}
            scanFeedback={scanFeedback}
            scanStatus={scanStatus}
            searchStatus={searchStatus}
          />
          <ProductSearchResults
            cart={cart}
            onAdd={(item, source) => addItem(item, source)}
            onSelect={setSelectedResult}
            onShowAll={() => setSearchLimit(30)}
            query={query}
            results={results}
            selectedIndex={selectedResult}
            status={searchStatus}
          />
          <SaleItems
            cart={cart}
            onChangeQty={changeQty}
            onRemove={(itemCode) => setCart((current) => current.filter((item) => item.item_code !== itemCode))}
            onRequestClear={() => setClearConfirmOpen(true)}
          />
        </main>

        <aside className="space-y-4 xl:sticky xl:top-[calc(var(--tp-topbar-height)+1rem)]">
          <SaleSummary
            customer={customer}
            discount={discount}
            discountRef={discountRef}
            onClearDiscount={() => setDiscount(0)}
            onDiscountChange={changeDiscount}
            onFinalize={handleFinalize}
            onPercentDiscount={(percent) => setDiscount(Number((subtotal * percent / 100).toFixed(2)))}
            subtotal={subtotal}
            total={total}
          />
          <KeyboardShortcuts />
        </aside>
      </div>

      <CustomerPickerModal
        onClose={() => setCustomerOpen(false)}
        onSelect={(selected) => {
          setCustomer(selected);
          setCustomerOpen(false);
          focusScanner(true);
        }}
        open={customerOpen}
      />
      <ApprovalRequestModal
		onClose={() => setSaleApproval(null)}
		onCreated={() => setSaleApproval(null)}
        onToast={onToast}
		open={Boolean(saleApproval)}
		payload={saleApproval?.payload ?? {}}
		referenceName={saleApproval?.referenceName ?? ""}
		requestType={saleApproval?.requestType ?? "pos_price_floor"}
		title={saleApproval?.title ?? "Esta venda exige aprovação do Gestor."}
      />
      <CheckoutModal
        customerName={customer?.customer_name ?? customer?.name ?? "Cliente"}
        loading={checkoutLoading}
        onClose={() => setCheckoutOpen(false)}
        onConfirm={(payments) => void submitSale(payments)}
        open={checkoutOpen}
        total={total}
      />
      <Modal
        className="max-w-lg"
        onClose={() => setCompletedSale(null)}
        open={Boolean(completedSale)}
        title="Venda concluída"
      >
        {completedSale ? (
          <div className="text-center">
            <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-tec-green/15 text-tec-green"><CheckCircle2 size={30} /></span>
            <p className="mt-4 text-sm text-tec-muted">Venda registrada, estoque baixado e pagamento contabilizado.</p>
            <p className="mt-2 text-2xl font-bold text-white">{completedSale.sale}</p>
            <p className="mt-1 text-lg font-bold text-tec-orange">{completedSale.grand_total.toLocaleString("pt-BR", { currency: "BRL", style: "currency" })}</p>
            <div className="mt-5 flex flex-col justify-center gap-2 sm:flex-row">
              <Button onClick={() => setCompletedSale(null)}>Nova venda</Button>
              <Button
                icon={<ExternalLink size={17} />}
                onClick={() => window.open(completedSale.receipt.url, "_blank", "noopener,noreferrer")}
                variant="primary"
              >
                Abrir cupom
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
      <Modal className="max-w-md" onClose={() => setClearConfirmOpen(false)} open={clearConfirmOpen} title="Limpar venda">
        <p className="text-sm leading-6 text-tec-subtle">Remover todos os produtos e o desconto desta venda?</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button onClick={() => setClearConfirmOpen(false)}>Cancelar</Button>
          <Button onClick={() => {
            setCart([]);
            setDiscount(0);
            setClearConfirmOpen(false);
            focusScanner(true);
          }} variant="danger">Limpar venda</Button>
        </div>
      </Modal>
    </div>
  );
}
