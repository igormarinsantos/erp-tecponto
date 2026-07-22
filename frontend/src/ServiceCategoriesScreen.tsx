import { useCallback, useEffect, useMemo, useState } from "react";
import { Edit3, FolderTree, Plus, PowerOff, Search, Wrench } from "lucide-react";

import { serviceCatalog, type ServiceCatalogReference } from "./api";
import { Button, Card, getStatBarVisual, getStoredListPresentation, LayeredFilters, ListGridToggle, Modal, StatBar, type ListPresentation } from "./ui";

type ToastTone = "success" | "error";
type CategoryDraft = { name?: string; value: string; active: boolean };

const emptyDraft = (): CategoryDraft => ({ value: "", active: true });

export function ServiceCategoriesScreen({ canEdit, onToast }: { canEdit: boolean; onToast: (message: string, tone?: ToastTone) => void }) {
  const [items, setItems] = useState<ServiceCatalogReference[]>([]);
  const [query, setQuery] = useState("");
  const [quickFilter, setQuickFilter] = useState("active");
  const [presentation, setPresentation] = useState<ListPresentation>(() => getStoredListPresentation("tecponto.service-categories.presentation"));
  const [visibleCount, setVisibleCount] = useState(20);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState<CategoryDraft | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems((await serviceCatalog.references(true)).categories);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível carregar as categorias.", "error");
    } finally {
      setLoading(false);
    }
  }, [onToast]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { window.localStorage.setItem("tecponto.service-categories.presentation", presentation); }, [presentation]);

  const filteredItems = useMemo(() => items.filter((item) => {
    const normalizedQuery = query.trim().toLocaleLowerCase("pt-BR");
    const matchesQuery = !normalizedQuery || item.value.toLocaleLowerCase("pt-BR").includes(normalizedQuery);
    const matchesState = quickFilter === "all" || (quickFilter === "active" && item.active) || (quickFilter === "inactive" && !item.active);
    return matchesQuery && matchesState;
  }), [items, query, quickFilter]);
  const statItems = useMemo(() => [
    { key: "active", label: "Categorias ativas", value: items.filter((item) => item.active).length },
    { key: "all", label: "Total cadastrado", value: items.length },
    { key: "inactive", label: "Categorias inativas", value: items.filter((item) => !item.active).length },
  ], [items]);

  const save = async () => {
    if (!draft) return;
    try {
      await serviceCatalog.saveReference("category", draft);
      onToast(draft.name ? "Categoria atualizada." : "Categoria cadastrada.", "success");
      setDraft(null);
      await load();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível salvar a categoria.", "error");
    }
  };

  return <>
    <StatBar items={statItems.map((item) => ({ ...item, ...getStatBarVisual("service-categories", item.key) }))} onSelect={(key) => { setQuickFilter(key); setVisibleCount(20); }} />
    <Card className="mt-4 p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div><div className="flex items-center gap-2 text-tec-orange"><FolderTree size={20} /><span className="text-sm font-bold">Categorias de serviço</span></div><p className="mt-1 max-w-2xl text-sm text-tec-muted">Organize o catálogo de mão de obra. Inativar preserva o histórico e impede uso em novos serviços.</p></div>
        {canEdit ? <Button icon={<Plus size={16} />} onClick={() => setDraft(emptyDraft())} variant="primary">Nova categoria</Button> : <span className="rounded-control bg-tec-field px-3 py-2 text-xs font-semibold text-tec-muted">Consulta operacional</span>}
      </div>
    </Card>
    <Card className="mt-4 p-4"><LayeredFilters active={quickFilter} filters={[{ key: "active", label: "Ativas" }, { key: "inactive", label: "Inativas" }, { key: "all", label: "Todas" }]} onClear={() => { setQuery(""); setQuickFilter("active"); setVisibleCount(20); }} onSelect={(key) => { setQuickFilter(key); setVisibleCount(20); }} primary={<label className="relative block"><Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tec-muted" size={17} /><input className="tp-input w-full pl-10" onChange={(event) => { setQuery(event.target.value); setVisibleCount(20); }} placeholder="Buscar categoria de serviço" value={query} /></label>}><p className="text-xs text-tec-muted">A edição de nome acompanha os serviços já vinculados; não cria uma categoria paralela.</p></LayeredFilters></Card>
    <Card className="mt-4 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-tec-border/15 px-4 py-3"><div><h2 className="font-bold text-white">Categorias</h2><p className="mt-1 text-xs text-tec-muted">{filteredItems.length} categoria{filteredItems.length === 1 ? "" : "s"} encontrada{filteredItems.length === 1 ? "" : "s"}</p></div><ListGridToggle onChange={setPresentation} value={presentation} /></div>
      {loading ? <p className="p-5 text-sm text-tec-muted">Carregando categorias...</p> : null}
      {!loading && !filteredItems.length ? <p className="p-5 text-sm text-tec-muted">Nenhuma categoria encontrada com estes filtros.</p> : null}
      {!loading && filteredItems.length && presentation === "list" ? <div className="divide-y divide-tec-border/15">{filteredItems.slice(0, visibleCount).map((item) => <CategoryRow canEdit={canEdit} item={item} key={item.name} onEdit={() => setDraft({ name: item.name, value: item.value, active: item.active })} />)}</div> : null}
      {!loading && filteredItems.length && presentation === "grid" ? <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">{filteredItems.slice(0, visibleCount).map((item) => <CategoryRow canEdit={canEdit} grid item={item} key={item.name} onEdit={() => setDraft({ name: item.name, value: item.value, active: item.active })} />)}</div> : null}
      {!loading && filteredItems.length > visibleCount ? <div className="border-t border-tec-border/15 p-4 text-center"><Button onClick={() => setVisibleCount((count) => count + 20)}>Mostrar mais (+{Math.min(20, filteredItems.length - visibleCount)})</Button></div> : null}
    </Card>
    {draft ? <CategoryEditor canEdit={canEdit} draft={draft} onChange={setDraft} onClose={() => setDraft(null)} onSave={() => void save()} /> : null}
  </>;
}

function CategoryRow({ canEdit, grid = false, item, onEdit }: { canEdit: boolean; grid?: boolean; item: ServiceCatalogReference; onEdit: () => void }) {
  return <div className={grid ? "flex min-h-32 flex-col justify-between gap-4 rounded-card border border-tec-border/15 bg-tec-field/45 p-4" : "flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"}>
    <div className="flex min-w-0 items-center gap-3"><span className={item.active ? "grid size-9 shrink-0 place-items-center rounded-control bg-tec-success/15 text-tec-success" : "grid size-9 shrink-0 place-items-center rounded-control bg-tec-field text-tec-muted"}>{item.active ? <Wrench size={17} /> : <PowerOff size={17} />}</span><div><strong className={item.active ? "text-sm text-white" : "text-sm text-tec-muted line-through"}>{item.value}</strong><p className="mt-1 text-xs text-tec-muted">{item.active ? "Disponível para novos serviços" : "Preservada apenas no histórico"}</p></div></div>
    {canEdit ? <Button icon={<Edit3 size={15} />} onClick={onEdit}>Editar</Button> : null}
  </div>;
}

function CategoryEditor({ canEdit, draft, onChange, onClose, onSave }: { canEdit: boolean; draft: CategoryDraft; onChange: (draft: CategoryDraft) => void; onClose: () => void; onSave: () => void }) {
  return <Modal onClose={onClose} open title={draft.name ? `Editar ${draft.value}` : "Nova categoria de serviço"}><div className="space-y-4"><label className="grid gap-1.5 text-sm font-semibold text-tec-subtle">Nome da categoria<input autoFocus className="tp-input" onChange={(event) => onChange({ ...draft, value: event.target.value })} placeholder="Ex.: Diagnóstico avançado" value={draft.value} /></label><label className="flex items-center gap-2 rounded-control border border-tec-border/15 bg-tec-field/45 p-3 text-sm font-semibold text-tec-text"><input checked={draft.active} onChange={(event) => onChange({ ...draft, active: event.target.checked })} type="checkbox" /> Categoria ativa</label><p className="rounded-control bg-tec-field/65 p-3 text-xs text-tec-muted">Preço, prazo e peças permanecem no serviço. Esta tela só organiza a categoria do catálogo.</p><div className="flex justify-end gap-2"><Button onClick={onClose}>Cancelar</Button><Button disabled={!canEdit || !draft.value.trim()} onClick={onSave} variant="primary">Salvar categoria</Button></div></div></Modal>;
}
