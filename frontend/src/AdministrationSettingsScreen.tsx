import { useCallback, useEffect, useState, type ReactNode } from "react";
import { ArrowLeft, Building2, CreditCard, Save, SlidersHorizontal, TimerReset } from "lucide-react";

import { balcao, type AdministrationCardFee, type AdministrationSettings, type AdministrationStageSla } from "./api";
import { Button, Card } from "./ui";

type Toast = (message: string, tone?: "success" | "error") => void;

const PAYMENT_TYPES = ["Débito", "Crédito à vista", "Crédito 2x", "Crédito 3x+"];
const TECHNICAL_PAY_ENABLED = `use_technician_${["com", "mission"].join("")}`;
const TECHNICAL_PAY_RATE = `${["com", "mission"].join("")}_pct`;
const operationLabels: Array<[string, string, string]> = [
  ["enable_repair_pillar", "REPARO", "Ordens de serviço e oficina"],
  ["enable_buy_pillar", "COMPRE", "PDV, catálogo e estoque comercial"],
  ["enable_tradein_pillar", "TROQUE", "Avaliação e aparelhos usados"],
  [TECHNICAL_PAY_ENABLED, "Comissão de técnico", "Gera a comissão própria quando a loja usa esse modelo"],
  ["diagnostic_fee_enabled", "Taxa de diagnóstico", "Habilita a cobrança quando aplicável"],
  ["storage_fee_enabled", "Taxa de armazenamento", "Habilita a cobrança quando aplicável"],
  ["diagnosis_only_enabled", "Só diagnóstico", "Permite encerrar a OS sem reparo"],
  ["payment_advance_enabled", "Pagamento antecipado", "Permite sinal antes da nota"],
  ["payment_installments_enabled", "Pagamento parcelado", "Permite registrar parcelas reais"],
  ["payment_device_tradein_enabled", "Aparelho como pagamento", "Permite abater avaliação de troca"],
];

export function AdministrationSettingsScreen({ onBack, onToast }: { onBack: () => void; onToast: Toast }) {
  const [settings, setSettings] = useState<AdministrationSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { setSettings(await balcao.getAdministrationSettings()); }
    catch (error) { onToast(error instanceof Error ? error.message : "Não foi possível carregar as configurações.", "error"); }
    finally { setLoading(false); }
  }, [onToast]);

  useEffect(() => { void load(); }, [load]);

  const updateOperation = (key: string, value: boolean | number) => setSettings((current) => current ? { ...current, operation: { ...current.operation, [key]: value } } : current);
  const updateIdentity = (key: string, value: string) => setSettings((current) => current ? { ...current, identity: { ...current.identity, [key]: value } } : current);
  const updateFee = (index: number, key: keyof AdministrationCardFee, value: string | number) => setSettings((current) => current ? { ...current, card_fees: current.card_fees.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row) } : current);

  async function save() {
    if (!settings) return;
    setSaving(true);
    try {
      const saved = await balcao.saveAdministrationSettings({ identity: settings.identity, operation: settings.operation, card_fees: settings.card_fees });
      setSettings(saved);
      onToast("Configurações da loja atualizadas.", "success");
    } catch (error) { onToast(error instanceof Error ? error.message : "Não foi possível salvar as configurações.", "error"); }
    finally { setSaving(false); }
  }

  async function saveSla(sla: AdministrationStageSla) {
    try {
      const result = await balcao.saveStageSla(sla);
      setSettings((current) => current ? { ...current, stage_slas: current.stage_slas.map((item) => item.name === result.item.name ? result.item : item) } : current);
      onToast(`SLA de ${sla.workflow_state} salvo.`, "success");
    } catch (error) { onToast(error instanceof Error ? error.message : "Não foi possível salvar o SLA.", "error"); }
  }

  if (loading) return <Card className="p-5 text-sm text-tec-subtle">Carregando configurações da loja...</Card>;
  if (!settings) return <Card className="p-5 text-sm text-tec-red">Não foi possível abrir as configurações.</Card>;

  return <div className="space-y-5" data-testid="administration-settings-screen">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><Button icon={<ArrowLeft size={16} />} onClick={onBack} variant="ghost">Administração</Button><h2 className="mt-3 text-2xl font-bold text-white">Configurações da loja</h2><p className="mt-1 text-sm text-tec-subtle">Parâmetros operacionais, identidade, prazo e taxas usados pelo motor.</p></div><Button disabled={saving} icon={<Save size={17} />} onClick={() => void save()} variant="primary">{saving ? "Salvando..." : "Salvar configurações"}</Button></div>

    <Card className="p-5"><SectionTitle icon={<Building2 size={19} />} title="Identidade comercial" /><div className="mt-4 grid gap-3 md:grid-cols-2"><Field label="Razão social"><input className="tp-input" onChange={(event) => updateIdentity("company_name", event.target.value)} value={settings.identity.company_name} /></Field><Field label="CNPJ"><input className="tp-input" onChange={(event) => updateIdentity("tax_id", event.target.value)} value={settings.identity.tax_id} /></Field><Field label="Nome fantasia"><input className="tp-input" onChange={(event) => updateIdentity("trade_name", event.target.value)} value={settings.identity.trade_name} /></Field><Field label="Telefone"><input className="tp-input" onChange={(event) => updateIdentity("public_phone", event.target.value)} value={settings.identity.public_phone} /></Field><Field label="E-mail"><input className="tp-input" onChange={(event) => updateIdentity("public_email", event.target.value)} value={settings.identity.public_email} /></Field><Field label="Logo (URL ou arquivo já anexado)"><input className="tp-input" onChange={(event) => updateIdentity("public_logo", event.target.value)} value={settings.identity.public_logo} /></Field><Field className="md:col-span-2" label="Endereço exibido"><textarea className="tp-input min-h-20" onChange={(event) => updateIdentity("public_address", event.target.value)} value={settings.identity.public_address} /></Field></div></Card>

    <Card className="p-5"><SectionTitle icon={<SlidersHorizontal size={19} />} title="Operação enxuta e pilares" /><div className="mt-4 grid gap-2 md:grid-cols-2">{operationLabels.map(([key, label, detail]) => <label className="flex min-h-16 items-start gap-3 rounded-control border border-tec-border/15 bg-tec-field/45 p-3" key={key}><input checked={Boolean(settings.operation[key])} className="mt-1" onChange={(event) => updateOperation(key, event.target.checked)} type="checkbox" /><span><strong className="block text-sm text-white">{label}</strong><span className="mt-1 block text-xs leading-5 text-tec-muted">{detail}</span></span></label>)}</div><div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><NumberField label="Garantia padrão (dias)" onChange={(value) => updateOperation("default_warranty_days", value)} value={settings.operation.default_warranty_days} /><NumberField label="Taxa de diagnóstico" onChange={(value) => updateOperation("diagnostic_fee_amount", value)} value={settings.operation.diagnostic_fee_amount} step="0.01" /><NumberField label="Diária de armazenamento" onChange={(value) => updateOperation("storage_fee_amount", value)} value={settings.operation.storage_fee_amount} step="0.01" /><NumberField label="Início armazenamento (dias)" onChange={(value) => updateOperation("storage_fee_start_days", value)} value={settings.operation.storage_fee_start_days} /></div><div className="mt-3 grid gap-3 sm:grid-cols-2"><NumberField label="Abandono após (dias)" onChange={(value) => updateOperation("storage_fee_abandonment_days", value)} value={settings.operation.storage_fee_abandonment_days} /><NumberField label="Comissão de técnico (%)" onChange={(value) => updateOperation(TECHNICAL_PAY_RATE, value)} value={settings.operation[TECHNICAL_PAY_RATE]} step="0.01" /></div></Card>

    <Card className="p-5"><SectionTitle icon={<CreditCard size={19} />} title="Taxas de cartão" /><p className="mt-1 text-sm text-tec-muted">O PDV exige uma taxa e prazo para cada modalidade de cartão utilizada.</p><div className="mt-4 space-y-2">{settings.card_fees.map((fee, index) => <div className="grid gap-2 rounded-control border border-tec-border/15 bg-tec-field/45 p-3 sm:grid-cols-[1fr_160px_180px_auto]" key={`${fee.tipo}-${index}`}><input className="tp-input" onChange={(event) => updateFee(index, "tipo", event.target.value)} value={fee.tipo} /><input className="tp-input" min="0" onChange={(event) => updateFee(index, "taxa_pct", Number(event.target.value))} step="0.01" type="number" value={fee.taxa_pct} /><input className="tp-input" min="0" onChange={(event) => updateFee(index, "settlement_days", Number(event.target.value))} type="number" value={fee.settlement_days} /><Button onClick={() => setSettings((current) => current ? { ...current, card_fees: current.card_fees.filter((_, rowIndex) => rowIndex !== index) } : current)} variant="ghost">Remover</Button></div>)}</div><Button className="mt-3" onClick={() => setSettings((current) => current ? { ...current, card_fees: [...current.card_fees, { tipo: PAYMENT_TYPES.find((type) => !current.card_fees.some((fee) => fee.tipo === type)) ?? "Cartão", taxa_pct: 0, settlement_days: 0 }] } : current)} variant="secondary">Adicionar taxa</Button></Card>

    <Card className="p-5"><SectionTitle icon={<TimerReset size={19} />} title="SLA por etapa" /><p className="mt-1 text-sm text-tec-muted">Prazos em horas úteis alimentam a previsão de entrega e os alertas operacionais.</p><div className="mt-4 space-y-3">{settings.stage_slas.map((sla, index) => <SlaRow key={sla.name} sla={sla} onChange={(next) => setSettings((current) => current ? { ...current, stage_slas: current.stage_slas.map((item, itemIndex) => itemIndex === index ? next : item) } : current)} onSave={saveSla} />)}</div></Card>
  </div>;
}

function SlaRow({ onChange, onSave, sla }: { onChange: (value: AdministrationStageSla) => void; onSave: (value: AdministrationStageSla) => Promise<void>; sla: AdministrationStageSla }) { const [saving, setSaving] = useState(false); return <div className="grid gap-3 rounded-control border border-tec-border/15 bg-tec-field/45 p-3 lg:grid-cols-[1.2fr_140px_1fr_auto]"><label><span className="text-xs font-bold text-tec-muted">Etapa</span><input className="tp-input mt-1" disabled value={sla.workflow_state} /></label><NumberField label="Horas úteis" onChange={(value) => onChange({ ...sla, business_hours: value })} value={sla.business_hours} step="0.5" /><label><span className="text-xs font-bold text-tec-muted">Observação</span><input className="tp-input mt-1" onChange={(event) => onChange({ ...sla, description: event.target.value })} value={sla.description} /></label><div className="flex items-end gap-2"><label className="mb-2 flex items-center gap-2 text-xs font-bold text-tec-subtle"><input checked={sla.active} onChange={(event) => onChange({ ...sla, active: event.target.checked })} type="checkbox" />Ativo</label><Button disabled={saving} onClick={() => { setSaving(true); void onSave(sla).finally(() => setSaving(false)); }} variant="secondary">Salvar</Button></div></div>; }
function SectionTitle({ icon, title }: { icon: ReactNode; title: string }) { return <div className="flex items-center gap-2 text-white"><span className="text-tec-orange">{icon}</span><h3 className="text-lg font-bold">{title}</h3></div>; }
function Field({ children, className = "", label }: { children: ReactNode; className?: string; label: string }) { return <label className={`block ${className}`}><span className="text-xs font-bold text-tec-muted">{label}</span><div className="mt-1">{children}</div></label>; }
function NumberField({ label, onChange, step = "1", value }: { label: string; onChange: (value: number) => void; step?: string; value: unknown }) { return <Field label={label}><input className="tp-input" min="0" onChange={(event) => onChange(Number(event.target.value) || 0)} step={step} type="number" value={Number(value ?? 0)} /></Field>; }
