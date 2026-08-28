import { FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { Plus, Save } from "lucide-react";

import { balcao, type RegistryCustomerRecord, type RegistryDeviceRecord, type RegistryItemRecord, type RegistryKind, type RegistryRecord } from "./api";
import { Button, Modal } from "./ui";

type RegistryEditorModalProps = {
  kind: RegistryKind;
  name?: string | null;
  onClose: () => void;
  onSaved: (item: RegistryRecord) => void;
  open: boolean;
};

const PART_TYPES = ["", "Tela", "Bateria", "Conector", "Flex", "Placa", "Câmera", "Botão", "Insumo", "Acessório"];

function isCustomer(item: RegistryRecord): item is RegistryCustomerRecord {
  return "customer_name" in item;
}

function isDevice(item: RegistryRecord): item is RegistryDeviceRecord {
  return "imei_serial" in item;
}

function toMoney(value: number) {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function RegistryEditorModal({ kind, name, onClose, onSaved, open }: RegistryEditorModalProps) {
  const [record, setRecord] = useState<RegistryRecord | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const isNewRepairPart = kind === "repair_part" && !name;

  useEffect(() => {
    if (!open) return;
    setError("");
    setRecord(null);
    if (isNewRepairPart) {
      setForm({ item_code: "", item_name: "", item_group: "Peças de Reparo", description: "", custom_compatible_models: "", custom_part_type: "" });
      return;
    }
    if (!name) return;
    let cancelled = false;
    setLoading(true);
    void balcao.getRegistryRecord(kind, name)
      .then((response) => {
        if (cancelled) return;
        const item = response.item;
        setRecord(item);
        if (isCustomer(item)) {
          setForm({
            customer_name: item.customer_name ?? "",
            mobile_no: item.mobile_no ?? item.custom_whatsapp ?? "",
            custom_whatsapp: item.custom_whatsapp ?? item.mobile_no ?? "",
            custom_cpf: item.custom_cpf ?? "",
            custom_rg: item.custom_rg ?? "",
            custom_nao_possui_cpf: item.custom_nao_possui_cpf,
            email_id: item.email_id ?? "",
            address: item.address ?? {},
          });
        } else if (isDevice(item)) {
          setForm({ brand: item.brand ?? "", model: item.model ?? "", color: item.color ?? "", imei_serial: item.imei_serial ?? "", capacity: item.capacity ?? "", general_state: item.general_state ?? "" });
        } else {
          setForm({ item_name: item.item_name ?? "", description: item.model ?? "", custom_compatible_models: item.compatible_models ?? "", custom_part_type: item.part_type ?? "", standard_rate: item.selling_rate ?? 0 });
        }
      })
      .catch((reason) => !cancelled && setError(reason instanceof Error ? reason.message : "Não foi possível abrir o cadastro."))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [isNewRepairPart, kind, name, open]);

  const title = useMemo(() => {
    if (isNewRepairPart) return "Cadastrar peça de reparo";
    return kind === "customer" ? "Editar cliente" : kind === "device" ? "Editar aparelho" : kind === "repair_part" ? "Editar peça de reparo" : "Editar produto";
  }, [isNewRepairPart, kind]);

  const set = (key: string, value: unknown) => setForm((current) => ({ ...current, [key]: value }));
  const setAddress = (key: string, value: string) => setForm((current) => ({ ...current, address: { ...(current.address as Record<string, string> | undefined), [key]: value } }));

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const response = await balcao.saveRegistryRecord(kind, name ?? "", form);
      onSaved(response.item);
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível salvar o cadastro.");
    } finally {
      setSaving(false);
    }
  };

  const itemRecord = record && !isCustomer(record) && !isDevice(record) ? record as RegistryItemRecord : null;
  const noCpf = Boolean(form.custom_nao_possui_cpf);

  return (
    <Modal className="max-w-2xl" onClose={onClose} open={open} title={title}>
      {loading ? <p className="py-8 text-center text-sm text-tec-muted">Carregando cadastro...</p> : null}
      {!loading ? (
        <form className="space-y-4" onSubmit={submit}>
          {kind === "customer" ? <>
            <Field label="Nome completo"><input autoFocus className="tp-input" onChange={(event) => set("customer_name", event.target.value)} value={String(form.customer_name ?? "")} /></Field>
            <div className="grid gap-4 sm:grid-cols-2"><Field label="WhatsApp / telefone"><input className="tp-input" inputMode="tel" onChange={(event) => { set("mobile_no", event.target.value); set("custom_whatsapp", event.target.value); }} value={String(form.mobile_no ?? "")} /></Field><Field label="E-mail"><input className="tp-input" inputMode="email" onChange={(event) => set("email_id", event.target.value)} type="email" value={String(form.email_id ?? "")} /></Field></div>
            <label className="flex items-center gap-2 text-sm font-semibold text-tec-subtle"><input checked={noCpf} onChange={(event) => set("custom_nao_possui_cpf", event.target.checked)} type="checkbox" /> Cliente não possui CPF</label>
            {noCpf ? <Field label="RG"><input className="tp-input" onChange={(event) => set("custom_rg", event.target.value)} value={String(form.custom_rg ?? "")} /></Field> : <Field label="CPF"><input className="tp-input" inputMode="numeric" onChange={(event) => set("custom_cpf", event.target.value)} value={String(form.custom_cpf ?? "")} /></Field>}
            <div className="rounded-card border border-tec-border/15 bg-tec-field/35 p-4"><p className="mb-3 text-sm font-bold text-white">Endereço</p><div className="grid gap-3 sm:grid-cols-2"><Field label="Rua e número"><input className="tp-input" onChange={(event) => setAddress("address_line1", event.target.value)} value={String((form.address as Record<string, string> | undefined)?.address_line1 ?? "")} /></Field><Field label="Complemento"><input className="tp-input" onChange={(event) => setAddress("address_line2", event.target.value)} value={String((form.address as Record<string, string> | undefined)?.address_line2 ?? "")} /></Field><Field label="Cidade"><input className="tp-input" onChange={(event) => setAddress("city", event.target.value)} value={String((form.address as Record<string, string> | undefined)?.city ?? "")} /></Field><Field label="Estado"><input className="tp-input" onChange={(event) => setAddress("state", event.target.value)} value={String((form.address as Record<string, string> | undefined)?.state ?? "")} /></Field><Field label="CEP"><input className="tp-input" inputMode="numeric" onChange={(event) => setAddress("pincode", event.target.value)} value={String((form.address as Record<string, string> | undefined)?.pincode ?? "")} /></Field></div></div>
          </> : null}
          {kind === "device" ? <>
            <div className="grid gap-4 sm:grid-cols-2"><Field label="Marca"><input autoFocus className="tp-input" onChange={(event) => set("brand", event.target.value)} value={String(form.brand ?? "")} /></Field><Field label="Modelo"><input className="tp-input" onChange={(event) => set("model", event.target.value)} value={String(form.model ?? "")} /></Field><Field label="IMEI / serial"><input className="tp-input" onChange={(event) => set("imei_serial", event.target.value)} value={String(form.imei_serial ?? "")} /></Field><Field label="Cor"><input className="tp-input" onChange={(event) => set("color", event.target.value)} value={String(form.color ?? "")} /></Field><Field label="Capacidade"><input className="tp-input" onChange={(event) => set("capacity", event.target.value)} value={String(form.capacity ?? "")} /></Field></div><Field label="Estado declarado"><textarea className="tp-input min-h-24" onChange={(event) => set("general_state", event.target.value)} value={String(form.general_state ?? "")} /></Field>
          </> : null}
          {kind === "repair_part" || kind === "product" ? <>
            {isNewRepairPart ? <div className="grid gap-4 sm:grid-cols-2"><Field label="Código da peça"><input autoFocus className="tp-input" onChange={(event) => set("item_code", event.target.value.toUpperCase())} value={String(form.item_code ?? "")} /></Field><Field label="Grupo"><input className="tp-input" onChange={(event) => set("item_group", event.target.value)} value={String(form.item_group ?? "Peças de Reparo")} /></Field></div> : null}
            <Field label={kind === "repair_part" ? "Nome da peça" : "Nome do produto"}><input autoFocus className="tp-input" onChange={(event) => set("item_name", event.target.value)} value={String(form.item_name ?? "")} /></Field>
            <div className="grid gap-4 sm:grid-cols-2"><Field label="Modelo / descrição"><input className="tp-input" onChange={(event) => set("description", event.target.value)} value={String(form.description ?? "")} /></Field><Field label="Compatibilidade"><input className="tp-input" onChange={(event) => set("custom_compatible_models", event.target.value)} value={String(form.custom_compatible_models ?? "")} /></Field></div>
            {kind === "repair_part" ? <Field label="Tipo de peça"><select className="tp-input" onChange={(event) => set("custom_part_type", event.target.value)} value={String(form.custom_part_type ?? "")}>{PART_TYPES.map((type) => <option key={type} value={type}>{type || "Não definido"}</option>)}</select></Field> : <Field label="Preço de venda"><input className="tp-input" min="0" onChange={(event) => set("standard_rate", Number(event.target.value))} step="0.01" type="number" value={Number(form.standard_rate ?? 0)} /></Field>}
            {itemRecord && "valuation_rate" in itemRecord ? <div className="rounded-control border border-tec-orange/25 bg-tec-orange/10 px-3 py-3 text-sm"><span className="font-bold text-tec-orange">Custo interno atual:</span> <span className="font-semibold text-white">{toMoney(itemRecord.valuation_rate ?? 0)}</span><p className="mt-1 text-xs text-tec-muted">Visível somente para Diretor; a alteração de custo continua pelo recebimento de estoque.</p></div> : null}
          </> : null}
          {error ? <p className="rounded-control border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm font-semibold text-red-300">{error}</p> : null}
          <div className="flex justify-end gap-2 border-t border-tec-border/15 pt-4"><Button onClick={onClose} type="button" variant="secondary">Cancelar</Button><Button disabled={saving} icon={isNewRepairPart ? <Plus size={16} /> : <Save size={16} />} type="submit" variant="primary">{saving ? "Salvando..." : isNewRepairPart ? "Cadastrar peça" : "Salvar alterações"}</Button></div>
        </form>
      ) : null}
    </Modal>
  );
}

function Field({ children, label }: { children: ReactNode; label: string }) {
  return <label className="grid gap-1.5 text-sm font-semibold text-tec-subtle"><span>{label}</span>{children}</label>;
}
