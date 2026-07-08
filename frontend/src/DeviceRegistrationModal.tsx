import { type FormEvent, type HTMLAttributes, useCallback, useState } from "react";
import { Camera, Plus, Search, Upload } from "lucide-react";

import { balcao, type CustomerDeviceSummary, type CustomerSummary } from "./api";
import { Button, Modal } from "./ui";

type DeviceForm = {
  brand: string;
  model: string;
  color: string;
  imei_serial: string;
  capacity: string;
  general_state: string;
};

interface DeviceRegistrationModalProps {
  onClose: () => void;
  onCreated: (device: CustomerDeviceSummary) => void;
  open: boolean;
}

export function DeviceRegistrationModal({ onClose, onCreated, open }: DeviceRegistrationModalProps) {
  const [customerQuery, setCustomerQuery] = useState("");
  const [customerRows, setCustomerRows] = useState<CustomerSummary[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerSummary | null>(null);
  const [form, setForm] = useState<DeviceForm>({
    brand: "",
    model: "",
    color: "",
    imei_serial: "",
    capacity: "",
    general_state: "",
  });
  const [photo, setPhoto] = useState<{ dataUrl: string; filename: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const reset = useCallback(() => {
    setCustomerQuery("");
    setCustomerRows([]);
    setSelectedCustomer(null);
    setForm({ brand: "", model: "", color: "", imei_serial: "", capacity: "", general_state: "" });
    setPhoto(null);
    setError(null);
    setSubmitting(false);
  }, []);

  const close = useCallback(() => {
    reset();
    onClose();
  }, [onClose, reset]);

  async function searchCustomers(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setError(null);
    const response = await balcao.searchCustomers(customerQuery, 8);
    setCustomerRows(response.items);
  }

  async function handleFile(file: File | undefined) {
    if (!file) {
      return;
    }
    setPhoto({
      dataUrl: await readFileAsDataUrl(file),
      filename: file.name || "aparelho.png",
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!selectedCustomer) {
      setError("Selecione o cliente do aparelho.");
      return;
    }
    if (!form.brand.trim() || !form.model.trim() || !form.imei_serial.trim()) {
      setError("Marca, modelo e IMEI/Serial são obrigatórios.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await balcao.createDevice({
        customer: selectedCustomer.name,
        brand: form.brand.trim(),
        model: form.model.trim(),
        color: form.color.trim(),
        imei_serial: form.imei_serial.trim(),
        capacity: form.capacity.trim(),
        general_state: form.general_state.trim(),
        photo: photo ? { data_url: photo.dataUrl, filename: photo.filename } : null,
      });
      onCreated(response.item);
      close();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao cadastrar aparelho.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal className="max-w-5xl" onClose={close} open={open} title="Cadastrar aparelho">
      <form className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_430px]" onSubmit={submit}>
        <section>
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-card bg-tec-orange/15 text-tec-orange">
              <Search size={18} />
            </span>
            <h3 className="text-base font-bold text-white">Cliente</h3>
          </div>
          <div className="mt-3 flex gap-2">
            <input
              className="h-11 min-w-0 flex-1 rounded-control border border-tec-border/25 bg-tec-field px-4 text-sm text-white outline-none focus:border-tec-orange/70"
              onChange={(event) => setCustomerQuery(event.target.value)}
              placeholder="Nome, telefone, CPF ou RG"
              value={customerQuery}
            />
            <Button icon={<Search size={17} />} onClick={() => void searchCustomers()} type="button" variant="primary">
              Buscar
            </Button>
          </div>
          <div className="mt-3 space-y-2">
            {customerRows.map((customer) => (
              <button
                className={`w-full rounded-card border p-3 text-left text-sm transition ${
                  selectedCustomer?.name === customer.name
                    ? "border-tec-orange bg-tec-orange/10"
                    : "border-tec-border/20 bg-tec-panel-strong hover:border-tec-orange/50"
                }`}
                key={customer.name}
                onClick={() => setSelectedCustomer(customer)}
                type="button"
              >
                <span className="block font-bold text-white">{customer.customer_name ?? customer.name}</span>
                <span className="mt-1 block text-xs text-tec-muted">
                  {[customer.mobile_no, customer.custom_cpf || customer.custom_rg, customer.email_id].filter(Boolean).join(" · ") || customer.name}
                </span>
              </button>
            ))}
          </div>
          {selectedCustomer ? (
            <div className="mt-3 rounded-card border border-tec-orange/35 bg-tec-orange/10 p-3 text-sm">
              <p className="font-bold text-white">{selectedCustomer.customer_name ?? selectedCustomer.name}</p>
              <p className="text-tec-subtle">{selectedCustomer.mobile_no}</p>
            </div>
          ) : null}
        </section>

        <section>
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-card bg-tec-orange/15 text-tec-orange">
              <Camera size={18} />
            </span>
            <h3 className="text-base font-bold text-white">Aparelho</h3>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Field label="Marca" onChange={(value) => setForm({ ...form, brand: value })} required value={form.brand} />
            <Field label="Modelo" onChange={(value) => setForm({ ...form, model: value })} required value={form.model} />
            <Field label="Cor" onChange={(value) => setForm({ ...form, color: value })} value={form.color} />
            <Field label="Capacidade" onChange={(value) => setForm({ ...form, capacity: value })} value={form.capacity} />
            <div className="sm:col-span-2">
              <Field
                inputMode="numeric"
                label="IMEI / Serial"
                maxLength={18}
                onChange={(value) => setForm({ ...form, imei_serial: value })}
                placeholder="15 dígitos do IMEI ou serial"
                required
                value={form.imei_serial}
              />
            </div>
            <label className="sm:col-span-2 block">
              <span className="mb-1 flex items-center justify-between gap-2 text-xs font-bold uppercase text-tec-muted">
                <span>Estado geral</span>
                <span className="text-tec-muted/70">Opcional</span>
              </span>
              <textarea
                className="min-h-[110px] w-full resize-none rounded-control border border-tec-border/25 bg-tec-field p-3 text-sm text-white outline-none focus:border-tec-orange/70"
                onChange={(event) => setForm({ ...form, general_state: event.target.value })}
                value={form.general_state}
              />
            </label>
          </div>

          <label className="mt-3 flex min-h-[120px] cursor-pointer flex-col items-center justify-center rounded-card border border-dashed border-tec-border/35 bg-tec-field p-4 text-center text-sm text-tec-subtle transition hover:border-tec-orange/60">
            {photo ? (
              <img alt="Foto do aparelho" className="max-h-44 w-full rounded-card object-cover" src={photo.dataUrl} />
            ) : (
              <>
                <Upload className="mb-2 text-tec-orange" size={22} />
                <span className="font-bold text-white">Adicionar foto</span>
                <span className="mt-1 text-xs text-tec-muted">Opcional, usada como thumbnail na lista</span>
              </>
            )}
            <input accept="image/*" className="sr-only" onChange={(event) => void handleFile(event.currentTarget.files?.[0])} type="file" />
          </label>

          {error ? <div className="mt-3 rounded-card border border-tec-red/30 bg-tec-red/10 p-3 text-sm text-tec-red">{error}</div> : null}

          <div className="mt-4 flex justify-end gap-2">
            <Button disabled={submitting} onClick={close} type="button">
              Cancelar
            </Button>
            <Button disabled={submitting} icon={<Plus size={17} />} type="submit" variant="primary">
              {submitting ? "Cadastrando..." : "Cadastrar aparelho"}
            </Button>
          </div>
        </section>
      </form>
    </Modal>
  );
}

function Field({
  inputMode,
  label,
  maxLength,
  onChange,
  placeholder,
  required,
  value,
}: {
  inputMode?: HTMLAttributes<HTMLInputElement>["inputMode"];
  label: string;
  maxLength?: number;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  value: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 flex items-center justify-between gap-2 text-xs font-bold uppercase text-tec-muted">
        <span>{label}</span>
        <span className={required ? "text-tec-orange" : "text-tec-muted/70"}>{required ? "Obrigatório" : "Opcional"}</span>
      </span>
      <input
        aria-required={required || undefined}
        className="h-11 w-full rounded-control border border-tec-border/25 bg-tec-field px-3 text-sm text-white outline-none focus:border-tec-orange/70"
        inputMode={inputMode}
        maxLength={maxLength}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
        value={value}
      />
    </label>
  );
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Falha ao ler a foto."));
    reader.onload = () => resolve(String(reader.result));
    reader.readAsDataURL(file);
  });
}
