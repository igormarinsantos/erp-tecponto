import { useCallback, useEffect, useMemo, useState } from "react";
import { Edit3, ListPlus, Plus, Search, Tag } from "lucide-react";

import { productVariants, type ProductVariantAttribute } from "./api";
import {
  Button,
  Card,
  getStatBarVisual,
  getStoredListPresentation,
  LayeredFilters,
  ListGridToggle,
  Modal,
  StatBar,
  type ListPresentation,
} from "./ui";

type ToastTone = "success" | "error";
type AttributeDraft = {
  name: string;
  originalName?: string;
  values: Array<{ value: string; abbreviation: string }>;
  disabled: boolean;
};

const blankDraft = (): AttributeDraft => ({ name: "", values: [], disabled: false });

export function ProductVariantAttributesScreen({ canEdit, onToast }: {
  canEdit: boolean;
  onToast: (message: string, tone?: ToastTone) => void;
}) {
  const [items, setItems] = useState<ProductVariantAttribute[]>([]);
  const [draft, setDraft] = useState<AttributeDraft>(blankDraft);
  const [editorOpen, setEditorOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [quickFilter, setQuickFilter] = useState("active");
  const [presentation, setPresentation] = useState<ListPresentation>(() => getStoredListPresentation("tecponto.product-attributes.presentation"));
  const [visibleCount, setVisibleCount] = useState(20);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems((await productVariants.listAttributes()).items);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível carregar os atributos.", "error");
    } finally {
      setLoading(false);
    }
  }, [onToast]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { window.localStorage.setItem("tecponto.product-attributes.presentation", presentation); }, [presentation]);

  const filteredItems = useMemo(() => items.filter((item) => {
    const needle = query.trim().toLocaleLowerCase("pt-BR");
    const matchesText = !needle || `${item.name} ${item.values.map((value) => value.value).join(" ")}`.toLocaleLowerCase("pt-BR").includes(needle);
    const matchesState = quickFilter === "all" || (quickFilter === "active" && !item.disabled) || (quickFilter === "inactive" && item.disabled);
    return matchesText && matchesState;
  }), [items, query, quickFilter]);

  const statItems = useMemo(() => [
    { key: "active", label: "Atributos ativos", value: items.filter((item) => !item.disabled).length },
    { key: "values", label: "Valores cadastrados", value: items.reduce((sum, item) => sum + item.values.length, 0) },
    { key: "inactive", label: "Atributos inativos", value: items.filter((item) => item.disabled).length },
  ], [items]);

  const openEditor = (item?: ProductVariantAttribute) => {
    setDraft(item ? {
      name: item.name,
      originalName: item.name,
      disabled: item.disabled,
      values: item.values.map((value) => ({ value: value.value, abbreviation: value.abbreviation })),
    } : blankDraft());
    setEditorOpen(true);
  };

  const save = async () => {
    try {
      await productVariants.saveAttribute(draft.originalName ?? draft.name, draft.values, draft.disabled, true);
      onToast("Atributo salvo.", "success");
      setEditorOpen(false);
      await load();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível salvar o atributo.", "error");
    }
  };

  return <>
    <StatBar
      items={statItems.map((item) => ({ ...item, ...getStatBarVisual("product-attributes", item.key) }))}
      onSelect={(key) => { if (key !== "values") setQuickFilter(key); setVisibleCount(20); }}
    />
    <Card className="mt-4 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-tec-orange"><Tag size={20} /><span className="text-sm font-bold">Atributos e variações</span></div>
          <p className="mt-1 max-w-2xl text-sm text-tec-muted">Atributos nativos do ERPNext usados para montar SKU, GTIN e estoque por variação. Remover um valor já usado por produto não é permitido.</p>
        </div>
        {canEdit
          ? <Button icon={<Plus size={16} />} onClick={() => openEditor()} variant="primary">Novo atributo</Button>
          : <span className="rounded-control bg-tec-field px-3 py-2 text-xs font-semibold text-tec-muted">Consulta operacional</span>}
      </div>
    </Card>
    <Card className="mt-4 p-4">
      <LayeredFilters
        active={quickFilter}
        filters={[{ key: "active", label: "Ativos" }, { key: "inactive", label: "Inativos" }, { key: "all", label: "Todos" }]}
        onClear={() => { setQuery(""); setQuickFilter("active"); setVisibleCount(20); }}
        onSelect={(key) => { setQuickFilter(key); setVisibleCount(20); }}
        primary={<label className="relative block"><Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tec-muted" size={17} /><input className="tp-input w-full pl-10" onChange={(event) => { setQuery(event.target.value); setVisibleCount(20); }} placeholder="Buscar atributo ou valor" value={query} /></label>}
      >
        <p className="text-xs text-tec-muted">Valores inativados deixam de ser sugeridos em novos produtos; variações existentes preservam sua combinação.</p>
      </LayeredFilters>
    </Card>
    <Card className="mt-4 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-tec-border/15 px-4 py-3">
        <div><h2 className="font-bold text-white">Atributos nativos</h2><p className="mt-1 text-xs text-tec-muted">{filteredItems.length} atributo{filteredItems.length === 1 ? "" : "s"} encontrado{filteredItems.length === 1 ? "" : "s"}</p></div>
        <ListGridToggle onChange={setPresentation} value={presentation} />
      </div>
      {loading ? <p className="p-5 text-sm text-tec-muted">Carregando atributos...</p> : null}
      {!loading && !filteredItems.length ? <p className="p-5 text-sm text-tec-muted">Nenhum atributo encontrado com estes filtros.</p> : null}
      {!loading && filteredItems.length && presentation === "list" ? <div className="divide-y divide-tec-border/15">{filteredItems.slice(0, visibleCount).map((item) => <AttributeRow canEdit={canEdit} item={item} key={item.name} onEdit={() => openEditor(item)} />)}</div> : null}
      {!loading && filteredItems.length && presentation === "grid" ? <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">{filteredItems.slice(0, visibleCount).map((item) => <AttributeRow canEdit={canEdit} grid item={item} key={item.name} onEdit={() => openEditor(item)} />)}</div> : null}
      {!loading && filteredItems.length > visibleCount ? <div className="border-t border-tec-border/15 p-4 text-center"><Button onClick={() => setVisibleCount((count) => count + 20)}>Mostrar mais (+{Math.min(20, filteredItems.length - visibleCount)})</Button></div> : null}
    </Card>
    <AttributeEditor canEdit={canEdit} draft={draft} onChange={setDraft} onClose={() => setEditorOpen(false)} onSave={() => void save()} open={editorOpen} />
  </>;
}

function AttributeRow({ canEdit, grid = false, item, onEdit }: { canEdit: boolean; grid?: boolean; item: ProductVariantAttribute; onEdit: () => void }) {
  return <div className={grid ? "flex min-h-40 flex-col gap-4 rounded-card border border-tec-border/15 bg-tec-field/45 p-4" : "flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"}>
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-2"><strong className={item.disabled ? "text-sm text-tec-muted line-through" : "text-sm text-white"}>{item.name}</strong>{item.disabled ? <span className="rounded-full bg-tec-field px-2 py-1 text-[11px] font-bold text-tec-muted">Inativo</span> : <span className="rounded-full bg-tec-success/15 px-2 py-1 text-[11px] font-bold text-tec-success">Ativo</span>}</div>
      <div className="mt-3 flex flex-wrap gap-1.5">{item.values.length ? item.values.map((value) => <span className="rounded-full bg-tec-panel px-2 py-1 text-xs text-tec-subtle" key={value.value}>{value.value}<span className="ml-1 text-tec-muted">{value.abbreviation}</span></span>) : <span className="text-xs text-tec-muted">Sem valores cadastrados.</span>}</div>
    </div>
    {canEdit ? <Button icon={<Edit3 size={15} />} onClick={onEdit}>Editar</Button> : null}
  </div>;
}

function AttributeEditor({ canEdit, draft, onChange, onClose, onSave, open }: { canEdit: boolean; draft: AttributeDraft; onChange: (draft: AttributeDraft) => void; onClose: () => void; onSave: () => void; open: boolean }) {
  const updateValue = (index: number, key: "value" | "abbreviation", value: string) => onChange({ ...draft, values: draft.values.map((current, currentIndex) => currentIndex === index ? { ...current, [key]: value } : current) });
  const addValue = () => onChange({ ...draft, values: [...draft.values, { value: "", abbreviation: "" }] });
  const removeValue = (index: number) => onChange({ ...draft, values: draft.values.filter((_, currentIndex) => currentIndex !== index) });

  return <Modal className="max-w-3xl" onClose={onClose} open={open} title={draft.name ? `Editar ${draft.name}` : "Novo atributo"}>
    <div className="space-y-4">
      <label className="grid gap-1.5 text-sm font-semibold text-tec-subtle">Nome do atributo<input autoFocus className="tp-input" disabled={Boolean(draft.originalName)} onChange={(event) => onChange({ ...draft, name: event.target.value })} placeholder="Ex.: Material" value={draft.name} /></label>
      <div>
        <div className="flex items-center justify-between gap-3"><label className="text-sm font-semibold text-tec-subtle">Valores e abreviações</label><Button icon={<ListPlus size={15} />} onClick={addValue}>Adicionar valor</Button></div>
        <div className="mt-2 space-y-2">{draft.values.map((value, index) => <div className="grid gap-2 sm:grid-cols-[1fr_140px_auto]" key={`${value.value}-${index}`}><input className="tp-input" onChange={(event) => updateValue(index, "value", event.target.value)} placeholder="Valor" value={value.value} /><input className="tp-input" onChange={(event) => updateValue(index, "abbreviation", event.target.value.toUpperCase())} placeholder="Abrev." value={value.abbreviation} /><Button onClick={() => removeValue(index)} title="Remover valor" variant="secondary">Remover</Button></div>)}</div>
      </div>
      <label className="flex items-center gap-2 rounded-control border border-tec-border/15 bg-tec-field/45 p-3 text-sm font-semibold text-tec-text"><input checked={draft.disabled} onChange={(event) => onChange({ ...draft, disabled: event.target.checked })} type="checkbox" /> Inativar atributo</label>
      <p className="rounded-control bg-tec-field/65 p-3 text-xs text-tec-muted">Um valor ligado a uma variação existente é preservado pelo motor mesmo que seja removido desta lista.</p>
      <div className="flex justify-end gap-2"><Button onClick={onClose}>Cancelar</Button><Button disabled={!canEdit || !draft.name.trim()} onClick={onSave} variant="primary">Salvar atributo</Button></div>
    </div>
  </Modal>;
}
