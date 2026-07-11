import { type FormEvent, useEffect, useState } from "react";
import { Search, UserRound } from "lucide-react";

import { balcao, type CustomerSummary } from "../api";
import { Button, Modal } from "../ui";

interface CustomerPickerModalProps {
  onClose: () => void;
  onSelect: (customer: CustomerSummary) => void;
  open: boolean;
}

export function CustomerPickerModal({ onClose, onSelect, open }: CustomerPickerModalProps) {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState<CustomerSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  const search = async (value: string) => {
    setStatus("loading");
    try {
      const response = await balcao.searchCustomers(value, 12);
      setRows(response.items);
      setStatus("ready");
    } catch {
      setRows([]);
      setStatus("error");
    }
  };

  useEffect(() => {
    if (open) {
      setQuery("");
      void search("");
    }
  }, [open]);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void search(query.trim());
  };

  return (
    <Modal className="max-w-xl" onClose={onClose} open={open} title="Cliente da venda">
      <form className="flex gap-2" onSubmit={submit}>
        <label className="relative min-w-0 flex-1">
          <span className="sr-only">Buscar cliente</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tec-muted" size={17} />
          <input
            autoFocus
            className="h-11 w-full rounded-control border border-tec-border/20 bg-tec-field pl-10 pr-3 text-sm text-white outline-none focus:border-tec-orange/70"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Nome, telefone, CPF ou RG"
            value={query}
          />
        </label>
        <Button disabled={status === "loading"} type="submit">Buscar</Button>
      </form>
      <div className="mt-4 max-h-80 space-y-2 overflow-y-auto">
        {status === "loading" ? (
          <p className="rounded-control bg-tec-field/60 p-4 text-sm text-tec-muted">Carregando clientes...</p>
        ) : status === "error" ? (
          <p className="rounded-control bg-tec-red/10 p-4 text-sm font-semibold text-tec-red">Falha ao consultar clientes.</p>
        ) : rows.length ? (
          rows.map((customer) => (
            <button
              className="flex min-h-14 w-full items-center gap-3 rounded-control border border-tec-border/15 bg-tec-field/55 p-3 text-left transition hover:border-tec-orange/45"
              key={customer.name}
              onClick={() => onSelect(customer)}
              type="button"
            >
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-tec-blue/20 text-tec-blue"><UserRound size={17} /></span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-bold text-white">{customer.customer_name ?? customer.name}</span>
                <span className="mt-1 block truncate text-xs text-tec-muted">{customer.mobile_no || customer.custom_whatsapp || customer.email_id || customer.name}</span>
              </span>
            </button>
          ))
        ) : (
          <p className="rounded-control bg-tec-field/60 p-4 text-sm text-tec-muted">Nenhum cliente encontrado.</p>
        )}
      </div>
    </Modal>
  );
}
