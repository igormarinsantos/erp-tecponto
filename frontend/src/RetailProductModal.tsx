import { useEffect, useState } from "react";
import { Barcode, PackagePlus, ScanLine } from "lucide-react";

import { pos, type RetailBarcodeLookupResponse, type RetailBarcodeSource } from "./api";
import { Button, Modal } from "./ui";

interface RetailProductModalProps {
  canReceiveStock: boolean;
  initialBarcode?: string | null;
  onClose: () => void;
  onCreated: (message: string) => void;
  open: boolean;
}

const EMPTY_FORM = {
  barcode: "",
  barcodeSource: "Fabricante" as RetailBarcodeSource,
  itemCode: "",
  itemGroup: "",
  itemName: "",
  sellingRate: "",
  stockUom: "Nos",
};

export function RetailProductModal({ canReceiveStock, initialBarcode, onClose, onCreated, open }: RetailProductModalProps) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [groups, setGroups] = useState<string[]>([]);
  const [lookup, setLookup] = useState<RetailBarcodeLookupResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [receiptQty, setReceiptQty] = useState("");
  const [receiptRate, setReceiptRate] = useState("");

  useEffect(() => {
    if (!open) return;
    void pos.listRetailItemGroups().then((response) => {
      const nextGroups = response.items.map((entry) => entry.name);
      setGroups(nextGroups);
      setForm((current) => ({ ...current, itemGroup: current.itemGroup || nextGroups[0] || "Produtos de Varejo" }));
    }).catch(() => setMessage("Não foi possível carregar os grupos de varejo."));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const scanned = (initialBarcode ?? "").replace(/\s+/g, "");
    setForm({ ...EMPTY_FORM, barcode: scanned });
    setLookup(null);
    setMessage("");
    setReceiptQty("");
    setReceiptRate("");
    if (!scanned) return;

    setLoading(true);
    void pos.lookupRetailBarcode(scanned)
      .then((response) => {
        setLookup(response);
        if (response.state === "unknown") {
          setMessage("Código não encontrado. Complete o cadastro abaixo.");
        } else if (response.state === "disabled") {
          setMessage("Este código pertence a um produto desativado. Ele não será reutilizado.");
        } else {
          setMessage("Produto encontrado. Use a entrada de estoque, sem criar outro cadastro.");
        }
      })
      .catch((error) => setMessage(error instanceof Error ? error.message : "Falha ao consultar o código."))
      .finally(() => setLoading(false));
  }, [initialBarcode, open]);

  const isExisting = lookup?.state === "found";
  const isDisabled = lookup?.state === "disabled";
  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));

  const saveProduct = async () => {
    setLoading(true);
    setMessage("");
    try {
      const response = await pos.registerRetailProduct({
        barcode: form.barcode,
        barcode_source: form.barcodeSource,
        item_code: form.itemCode,
        item_group: form.itemGroup,
        item_name: form.itemName,
        selling_rate: Number(form.sellingRate || 0),
        stock_uom: form.stockUom,
      });
      onCreated(`Produto ${response.item.item_name} cadastrado com código ${response.barcode}.`);
      window.open(response.label.url, "_blank", "noopener,noreferrer");
      onClose();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível cadastrar o produto.");
    } finally {
      setLoading(false);
    }
  };

  const receiveStock = async () => {
    if (!lookup?.item) return;
    setLoading(true);
    setMessage("");
    try {
      const response = await pos.receiveRetailStock({
        incoming_rate: Number(receiptRate || 0),
        item_code: lookup.item.item_code,
        qty: Number(receiptQty || 0),
      });
      onCreated(`${response.qty_received} unidade(s) recebida(s). Saldo: ${response.qty_after}.`);
      onClose();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível registrar a entrada.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal className="max-w-3xl" onClose={onClose} open={open} title="Produto por código de barras">
      <div className="space-y-4">
        <div className="flex gap-3 rounded-control border border-tec-border/20 bg-tec-field/50 p-3 text-sm text-tec-subtle">
          <ScanLine className="shrink-0 text-tec-orange" size={20} />
          <p>{message || "Escaneie o código da embalagem ou cadastre um produto sem código."}</p>
        </div>

        {isExisting && lookup?.item ? (
          <section className="space-y-4">
            <div className="rounded-control border border-tec-success/30 bg-tec-success/10 p-4">
              <p className="font-bold text-white">{lookup.item.item_name}</p>
              <p className="mt-1 text-sm text-tec-subtle">{lookup.item.item_code} · {lookup.item.item_group} · código {lookup.barcode}</p>
            </div>
            {canReceiveStock ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="text-sm font-semibold text-white">Quantidade recebida
                  <input className="mt-1 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 text-white" min="0.001" onChange={(event) => setReceiptQty(event.target.value)} step="0.001" type="number" value={receiptQty} />
                </label>
                <label className="text-sm font-semibold text-white">Custo unitário
                  <input className="mt-1 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 text-white" min="0" onChange={(event) => setReceiptRate(event.target.value)} step="0.01" type="number" value={receiptRate} />
                </label>
              </div>
            ) : <p className="text-sm text-tec-muted">A entrada com custo é registrada pelo Gestor. O cadastro existente não será duplicado.</p>}
          </section>
        ) : !isDisabled ? (
          <section className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => update("barcodeSource", "Fabricante")} variant={form.barcodeSource === "Fabricante" ? "primary" : "secondary"}>Código da embalagem</Button>
              <Button onClick={() => update("barcodeSource", "Interno Tecponto")} variant={form.barcodeSource === "Interno Tecponto" ? "primary" : "secondary"}>Sem código: gerar interno</Button>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-sm font-semibold text-white">Código de barras
                <input className="mt-1 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 font-mono text-white disabled:opacity-60" disabled={form.barcodeSource === "Interno Tecponto"} onChange={(event) => update("barcode", event.target.value.replace(/\s+/g, ""))} placeholder="Escaneie a embalagem" value={form.barcodeSource === "Interno Tecponto" ? "Será gerado no servidor" : form.barcode} />
              </label>
              <label className="text-sm font-semibold text-white">Código do item
                <input className="mt-1 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 text-white" onChange={(event) => update("itemCode", event.target.value)} placeholder="CAP-IP13-TRANS" value={form.itemCode} />
              </label>
              <label className="text-sm font-semibold text-white sm:col-span-2">Nome do produto
                <input className="mt-1 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 text-white" onChange={(event) => update("itemName", event.target.value)} placeholder="Capinha transparente para iPhone 13" value={form.itemName} />
              </label>
              <label className="text-sm font-semibold text-white">Grupo de varejo
                <select className="mt-1 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 text-white" onChange={(event) => update("itemGroup", event.target.value)} value={form.itemGroup}>
                  {groups.map((group) => <option key={group} value={group}>{group}</option>)}
                </select>
              </label>
              <label className="text-sm font-semibold text-white">Preço de venda
                <input className="mt-1 w-full rounded-control border border-tec-border/20 bg-tec-field px-3 py-2 text-white" min="0" onChange={(event) => update("sellingRate", event.target.value)} step="0.01" type="number" value={form.sellingRate} />
              </label>
            </div>
            <p className="text-xs text-tec-muted">Acessórios são controlados por quantidade. Aparelhos com IMEI usam o fluxo próprio e não são cadastrados aqui.</p>
          </section>
        ) : null}

        <footer className="flex justify-end gap-2 border-t border-tec-border/15 pt-4">
          <Button onClick={onClose} variant="secondary">Cancelar</Button>
          {isExisting && canReceiveStock ? <Button disabled={loading} icon={<PackagePlus size={16} />} onClick={() => void receiveStock()} variant="primary">Registrar entrada</Button> : null}
          {!isExisting && !isDisabled ? <Button disabled={loading} icon={<Barcode size={16} />} onClick={() => void saveProduct()} variant="primary">Cadastrar e imprimir</Button> : null}
        </footer>
      </div>
    </Modal>
  );
}
