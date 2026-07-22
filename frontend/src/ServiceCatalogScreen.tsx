import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { BookOpenCheck, Edit3, Plus, Settings2, ToggleLeft, ToggleRight, Wrench } from "lucide-react";

import { balcao, serviceCatalog, type ServiceCatalogReference, type ServiceCatalogReferenceResponse, type ServiceCatalogService } from "./api";
import { Button, Card, getStatBarVisual, getStoredListPresentation, LayeredFilters, ListGridToggle, Modal, StatBar, type ListPresentation } from "./ui";

type ToastTone = "success" | "error";
type ServiceDraft = Partial<ServiceCatalogService>;

const emptyService: ServiceDraft = {
  active: true,
  category: "",
  complexity: null,
  default_duration: 0,
  default_labor_price: 0,
  device_type: "",
  duration_unit: "Horas",
  requires_part: false,
  service_name: "",
};

export function ServiceCatalogScreen({ canEdit, onToast }: { canEdit: boolean; onToast: (message: string, tone?: ToastTone) => void }) {
  const [query, setQuery] = useState("");
  const [deviceType, setDeviceType] = useState("");
  const [category, setCategory] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [items, setItems] = useState<ServiceCatalogService[]>([]);
  const [references, setReferences] = useState<ServiceCatalogReferenceResponse>({ categories: [], device_types: [] });
  const [loading, setLoading] = useState(true);
  const [editorOpen, setEditorOpen] = useState(false);
  const [referencesOpen, setReferencesOpen] = useState(false);
  const [editing, setEditing] = useState<ServiceDraft>(emptyService);
  const [statItems, setStatItems] = useState<Array<{ key: string; label: string; value: number }>>([]);
  const [presentation, setPresentation] = useState<ListPresentation>(() => getStoredListPresentation("tecponto.catalog.presentation"));
  const [quickFilter, setQuickFilter] = useState("active");
  const [advancedFilter, setAdvancedFilter] = useState("all");

  useEffect(() => {
    window.localStorage.setItem("tecponto.catalog.presentation", presentation);
  }, [presentation]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [services, nextReferences, statBar] = await Promise.all([
        serviceCatalog.list(query, deviceType, category, includeInactive),
        serviceCatalog.references(true),
        balcao.getListStatBar("catalog"),
      ]);
      setItems(services.items);
      setReferences(nextReferences);
      setStatItems(statBar.items);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível carregar o catálogo.", "error");
    } finally {
      setLoading(false);
    }
  }, [category, deviceType, includeInactive, onToast, query]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), query ? 220 : 0);
    return () => window.clearTimeout(timer);
  }, [load, query]);

  const activeDeviceTypes = useMemo(() => references.device_types.filter((item) => item.active), [references]);
  const activeCategories = useMemo(() => references.categories.filter((item) => item.active), [references]);

  const openNew = () => {
    setEditing({ ...emptyService, device_type: activeDeviceTypes[0]?.name ?? "", category: activeCategories[0]?.name ?? "" });
    setEditorOpen(true);
  };

  const saveService = async () => {
    try {
      await serviceCatalog.save(editing);
      onToast(editing.name ? "Serviço atualizado." : "Serviço cadastrado.", "success");
      setEditorOpen(false);
      await load();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível salvar o serviço.", "error");
    }
  };

  return (
    <>
      <StatBar items={statItems.map((item) => ({ ...item, ...getStatBarVisual("catalog", item.key) }))} />
      <Card className="p-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="flex items-center gap-2 text-tec-orange"><BookOpenCheck size={20} /><span className="text-sm font-bold">Catálogo de mão de obra</span></div>
            <p className="mt-1 text-sm text-tec-muted">Preço e prazo são sugestões. Nenhum item desta tela bloqueia uma OS.</p>
          </div>
          {canEdit ? <div className="flex flex-wrap gap-2"><Button icon={<Settings2 size={17} />} onClick={() => setReferencesOpen(true)}>Tipos de aparelho</Button><Button icon={<Plus size={17} />} onClick={openNew} variant="primary">Novo serviço</Button></div> : <span className="rounded-control bg-tec-field px-3 py-2 text-xs font-semibold text-tec-muted">Consulta operacional</span>}
        </div>
        <LayeredFilters active={quickFilter} filters={[{ key: "active", label: "Ativos" }, { key: "all", label: "Todos" }, { key: "parts", label: "Com peça" }]} onSelect={(key) => {
          setQuickFilter(key);
          if (key === "active") setIncludeInactive(false);
          if (key === "all") setIncludeInactive(true);
        }} primary={
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <input className="h-11 rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm text-tec-text outline-none focus:border-tec-orange/70" onChange={(event) => setQuery(event.target.value)} placeholder="Buscar serviço" value={query} />
          <select className="h-11 rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm text-tec-text outline-none focus:border-tec-orange/70" onChange={(event) => setDeviceType(event.target.value)} value={deviceType}><option value="">Todos os tipos</option>{references.device_types.map((item) => <option key={item.name} value={item.name}>{item.value}{item.active ? "" : " (inativo)"}</option>)}</select>
          <select className="h-11 rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm text-tec-text outline-none focus:border-tec-orange/70" onChange={(event) => setCategory(event.target.value)} value={category}><option value="">Todas as categorias</option>{references.categories.map((item) => <option key={item.name} value={item.name}>{item.value}{item.active ? "" : " (inativa)"}</option>)}</select>
          <label className="flex h-11 items-center gap-2 rounded-control border border-tec-border/20 bg-tec-field px-3 text-sm font-semibold text-tec-subtle"><input checked={includeInactive} onChange={(event) => setIncludeInactive(event.target.checked)} type="checkbox" /> Mostrar inativos</label>
        </div>
        } onClear={() => { setQuickFilter("active"); setAdvancedFilter("all"); setQuery(""); setDeviceType(""); setCategory(""); setIncludeInactive(false); }}><label className="block text-xs font-bold text-tec-subtle">Preço e prazo sugeridos<select className="tp-input mt-1 w-full" onChange={(event) => setAdvancedFilter(event.target.value)} value={advancedFilter}><option value="all">Sem filtro adicional</option><option value="priced">Com preço sugerido</option><option value="unpriced">Sem preço sugerido</option><option value="with_duration">Com prazo sugerido</option></select></label></LayeredFilters>
      </Card>
      <Card className="mt-4 overflow-hidden">
        <div className="flex items-center justify-between border-b border-tec-border/15 px-4 py-3"><div className="flex items-center gap-2"><Wrench className="text-tec-orange" size={18} /><h2 className="font-bold text-white">Serviços</h2></div><div className="flex items-center gap-3"><span className="text-sm text-tec-muted">{items.length} item{items.length === 1 ? "" : "s"}</span><ListGridToggle onChange={setPresentation} value={presentation} /></div></div>
        {loading ? <p className="p-5 text-sm text-tec-muted">Carregando catálogo...</p> : null}
        {!loading && items.length === 0 ? <p className="p-5 text-sm text-tec-muted">Nenhum serviço encontrado com estes filtros.</p> : null}
        {!loading && items.length > 0 ? <div className={presentation === "grid" ? "grid gap-3 p-4 md:grid-cols-2" : "divide-y divide-tec-border/15"}>{items.filter((item) => (quickFilter !== "parts" || item.requires_part) && (advancedFilter !== "priced" || item.default_labor_price > 0) && (advancedFilter !== "unpriced" || item.default_labor_price <= 0) && (advancedFilter !== "with_duration" || item.default_duration > 0)).map((item) => <ServiceRow canEdit={canEdit} grid={presentation === "grid"} item={item} key={item.name} onEdit={() => { setEditing(item); setEditorOpen(true); }} />)}</div> : null}
      </Card>
      <ServiceEditor activeCategories={activeCategories} activeDeviceTypes={activeDeviceTypes} canEdit={canEdit} draft={editing} onChange={setEditing} onClose={() => setEditorOpen(false)} onSave={() => void saveService()} open={editorOpen} />
      <ReferenceManager onChanged={() => void load()} onClose={() => setReferencesOpen(false)} onToast={onToast} open={referencesOpen} references={references} />
    </>
  );
}

function ServiceRow({ canEdit, grid, item, onEdit }: { canEdit: boolean; grid: boolean; item: ServiceCatalogService; onEdit: () => void }) {
  const price = item.default_labor_price > 0 ? item.default_labor_price.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "Não definido";
  const duration = item.default_duration > 0 ? `${item.default_duration} ${item.duration_unit.toLowerCase()}` : "Não definido";
  return <div className={grid ? "flex flex-col gap-4 rounded-card border border-tec-border/15 bg-tec-field/45 p-4" : "flex flex-col gap-3 px-4 py-3 lg:flex-row lg:items-center lg:justify-between"}><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><strong className="text-sm text-white">{item.service_name}</strong>{!item.active ? <span className="rounded-full bg-tec-field px-2 py-0.5 text-[11px] font-bold text-tec-muted">Inativo</span> : null}</div><p className="mt-1 text-xs text-tec-muted">{item.device_type_label ?? item.device_type} · {item.category_label ?? item.category}{item.complexity ? ` · ${item.complexity}` : ""}{item.requires_part ? " · Normalmente requer peça" : ""}</p></div><div className={grid ? "flex flex-wrap items-center gap-4" : "flex items-center gap-4"}><div className={grid ? "" : "text-right"}><p className="text-xs text-tec-muted">Mão de obra sugerida</p><p className="text-sm font-bold text-white">{price}</p></div><div className={grid ? "" : "text-right"}><p className="text-xs text-tec-muted">Prazo sugerido</p><p className="text-sm font-bold text-white">{duration}</p></div>{canEdit ? <Button icon={<Edit3 size={16} />} onClick={onEdit}>Editar</Button> : null}</div></div>;
}

function ServiceEditor({ activeCategories, activeDeviceTypes, canEdit, draft, onChange, onClose, onSave, open }: { activeCategories: ServiceCatalogReference[]; activeDeviceTypes: ServiceCatalogReference[]; canEdit: boolean; draft: ServiceDraft; onChange: (value: ServiceDraft) => void; onClose: () => void; onSave: () => void; open: boolean }) {
  const set = <K extends keyof ServiceDraft>(key: K, value: ServiceDraft[K]) => onChange({ ...draft, [key]: value });
  return <Modal onClose={onClose} open={open} title={draft.name ? "Editar serviço" : "Cadastrar serviço"}><div className="grid gap-4 md:grid-cols-2"><CatalogField label="Nome do serviço"><input autoFocus className="tp-input" onChange={(event) => set("service_name", event.target.value)} value={draft.service_name ?? ""} /></CatalogField><CatalogField label="Preço base de mão de obra"><input className="tp-input" min="0" onChange={(event) => set("default_labor_price", Number(event.target.value))} type="number" value={draft.default_labor_price ?? 0} /></CatalogField><CatalogField label="Tipo de aparelho"><select className="tp-input" onChange={(event) => set("device_type", event.target.value)} value={draft.device_type ?? ""}>{activeDeviceTypes.map((item) => <option key={item.name} value={item.name}>{item.value}</option>)}</select></CatalogField><CatalogField label="Categoria"><select className="tp-input" onChange={(event) => set("category", event.target.value)} value={draft.category ?? ""}>{activeCategories.map((item) => <option key={item.name} value={item.name}>{item.value}</option>)}</select></CatalogField><CatalogField label="Prazo base"><input className="tp-input" min="0" onChange={(event) => set("default_duration", Number(event.target.value))} type="number" value={draft.default_duration ?? 0} /></CatalogField><CatalogField label="Unidade"><select className="tp-input" onChange={(event) => set("duration_unit", event.target.value as ServiceCatalogService["duration_unit"])} value={draft.duration_unit ?? "Horas"}><option>Horas</option><option>Dias úteis</option></select></CatalogField><CatalogField label="Complexidade"><select className="tp-input" onChange={(event) => set("complexity", (event.target.value || null) as ServiceCatalogService["complexity"])} value={draft.complexity ?? ""}><option value="">Não definida</option><option>Baixa</option><option>Média</option><option>Alta</option></select></CatalogField><label className="flex items-center gap-2 text-sm font-semibold text-tec-subtle"><input checked={Boolean(draft.requires_part)} onChange={(event) => set("requires_part", event.target.checked)} type="checkbox" /> Normalmente requer peça</label><label className="flex items-center gap-2 text-sm font-semibold text-tec-subtle"><input checked={draft.active !== false} onChange={(event) => set("active", event.target.checked)} type="checkbox" /> Serviço ativo</label></div><p className="mt-4 rounded-control bg-tec-field/65 p-3 text-xs text-tec-muted">Os valores são sugestões para o orçamento. Não bloqueiam a abertura nem o andamento de uma OS.</p><div className="mt-5 flex justify-end gap-2"><Button onClick={onClose}>Cancelar</Button><Button disabled={!canEdit || !draft.service_name || !draft.device_type || !draft.category} onClick={onSave} variant="primary">Salvar serviço</Button></div></Modal>;
}

function ReferenceManager({ onChanged, onClose, onToast, open, references }: { onChanged: () => void; onClose: () => void; onToast: (message: string, tone?: ToastTone) => void; open: boolean; references: ServiceCatalogReferenceResponse }) {
  return <Modal className="max-w-2xl" onClose={onClose} open={open} title="Tipos de aparelho"><ReferenceColumn items={references.device_types} kind="device_type" label="Tipos de aparelho" onChanged={onChanged} onToast={onToast} /></Modal>;
}

function ReferenceColumn({ items, kind, label, onChanged, onToast }: { items: ServiceCatalogReference[]; kind: "device_type" | "category"; label: string; onChanged: () => void; onToast: (message: string, tone?: ToastTone) => void }) {
  const [value, setValue] = useState("");
  const [editing, setEditing] = useState<ServiceCatalogReference | null>(null);
  const save = async (payload: { name?: string; value: string; active: boolean }) => { try { await serviceCatalog.saveReference(kind, payload); setValue(""); setEditing(null); onChanged(); onToast("Referência salva.", "success"); } catch (error) { onToast(error instanceof Error ? error.message : "Não foi possível salvar.", "error"); } };
  return <section><h3 className="font-bold text-white">{label}</h3><div className="mt-3 flex gap-2"><input className="tp-input min-w-0" onChange={(event) => setValue(event.target.value)} placeholder={`Novo ${label.toLowerCase().slice(0, -1)}`} value={value} /><Button disabled={!value.trim()} icon={<Plus size={16} />} onClick={() => void save({ value, active: true })}>Adicionar</Button></div>{editing ? <div className="mt-3 rounded-control border border-tec-orange/40 bg-tec-field/70 p-3"><label className="grid gap-1.5 text-xs font-semibold text-tec-subtle">Editar referência<input autoFocus className="tp-input" onChange={(event) => setEditing({ ...editing, value: event.target.value })} value={editing.value} /></label><div className="mt-2 flex justify-end gap-2"><Button onClick={() => setEditing(null)}>Cancelar</Button><Button disabled={!editing.value.trim()} onClick={() => void save(editing)} variant="primary">Salvar</Button></div></div> : null}<div className="mt-3 space-y-2">{items.map((item) => <div className="flex items-center justify-between rounded-control bg-tec-field/70 px-3 py-2" key={item.name}><span className={item.active ? "text-sm font-semibold text-white" : "text-sm font-semibold text-tec-muted line-through"}>{item.value}</span><div className="flex items-center gap-1"><button aria-label={`Editar ${item.value}`} className="text-tec-muted hover:text-white" onClick={() => setEditing(item)} type="button"><Edit3 size={17} /></button><button aria-label={`${item.active ? "Inativar" : "Ativar"} ${item.value}`} className="text-tec-orange" onClick={() => void save({ name: item.name, value: item.value, active: !item.active })} type="button">{item.active ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}</button></div></div>)}</div></section>;
}

function CatalogField({ children, label }: { children: ReactNode; label: string }) { return <label className="grid gap-1.5 text-sm font-semibold text-tec-subtle"><span>{label}</span>{children}</label>; }
