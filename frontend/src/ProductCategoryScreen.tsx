import { useCallback, useEffect, useMemo, useState } from "react";
import { Archive, ChevronDown, ChevronRight, Edit3, FolderTree, Globe2, PackageCheck, Plus, Power, PowerOff, Search, Shapes } from "lucide-react";

import { productCategories, type ProductCategoryNode } from "./api";
import { Button, Card, getStatBarVisual, getStoredListPresentation, LayeredFilters, ListGridToggle, Modal, StatBar, type ListPresentation } from "./ui";

type ToastTone = "success" | "error";
type CategoryDraft = {
  name: string;
  original_name?: string;
  parent: string;
  is_group: boolean;
  sell_online: boolean;
  active: boolean;
};

const EMPTY_DRAFT: CategoryDraft = {
  name: "",
  parent: "Produtos de Varejo",
  is_group: false,
  sell_online: true,
  active: true,
};

export function ProductCategoryScreen({ canEdit, onToast }: { canEdit: boolean; onToast: (message: string, tone?: ToastTone) => void }) {
  const [items, setItems] = useState<ProductCategoryNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [openNodes, setOpenNodes] = useState<Set<string>>(new Set(["Produtos de Varejo", "Acessórios", "Aparelhos", "Peças de Reparo"]));
  const [draft, setDraft] = useState<CategoryDraft | null>(null);
  const [presentation, setPresentation] = useState<ListPresentation>(() => getStoredListPresentation("tecponto.product-categories.presentation"));
  const [query, setQuery] = useState("");
  const [quickFilter, setQuickFilter] = useState("active");
  const [visibleCount, setVisibleCount] = useState(20);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await productCategories.list();
      setItems(response.items);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível carregar as categorias.", "error");
    } finally {
      setLoading(false);
    }
  }, [onToast]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    window.localStorage.setItem("tecponto.product-categories.presentation", presentation);
  }, [presentation]);

  const parents = useMemo(() => flatten(items).filter((item) => item.is_group && item.active), [items]);
  const allItems = useMemo(() => flatten(items), [items]);
  const filteredItems = useMemo(() => allItems.filter((item) => {
    const normalizedQuery = query.trim().toLocaleLowerCase("pt-BR");
    const textMatches = !normalizedQuery || `${item.name} ${item.parent ?? ""}`.toLocaleLowerCase("pt-BR").includes(normalizedQuery);
    const quickMatches = quickFilter === "all"
      || (quickFilter === "active" && item.active)
      || (quickFilter === "online" && item.sell_online)
      || (quickFilter === "internal" && !item.sell_online)
      || (quickFilter === "inactive" && !item.active);
    return textMatches && quickMatches;
  }), [allItems, query, quickFilter]);
  const filteredTree = useMemo(() => filterTree(items, new Set(filteredItems.map((item) => item.name))), [items, filteredItems]);
  const statItems = useMemo(() => [
    { key: "active", label: "Ativas", value: allItems.filter((item) => item.active).length, icon: <PackageCheck size={19} />, tone: "green" as const },
    { key: "online", label: "Vendáveis online", value: allItems.filter((item) => item.sell_online && item.active).length, icon: <Globe2 size={19} />, tone: "blue" as const },
    { key: "internal", label: "Uso interno", value: allItems.filter((item) => !item.sell_online && item.active).length, icon: <Archive size={19} />, tone: "amber" as const },
    { key: "inactive", label: "Inativas", value: allItems.filter((item) => !item.active).length, icon: <PowerOff size={19} />, tone: "orange" as const },
  ], [allItems]);
  const visibleGridItems = filteredItems.slice(0, visibleCount);
  const openEditor = (item?: ProductCategoryNode) => setDraft(item ? {
    name: item.name,
    original_name: item.name,
    parent: item.parent || "All Item Groups",
    is_group: item.is_group,
    sell_online: item.sell_online,
    active: item.active,
  } : EMPTY_DRAFT);

  const save = async () => {
    if (!draft) return;
    try {
      await productCategories.save(draft);
      onToast(draft.original_name ? "Categoria atualizada." : "Categoria criada.", "success");
      setDraft(null);
      await load();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível salvar a categoria.", "error");
    }
  };

  return (
    <div className="space-y-4">
      <StatBar items={statItems.map((item) => ({ ...item, ...getStatBarVisual("product-categories", item.key) }))} onSelect={(key) => { setQuickFilter(key); setVisibleCount(20); }} />
      <Card className="p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-tec-orange"><FolderTree size={21} /><span className="text-sm font-bold">Categorias de produtos</span></div>
            <h1 className="mt-2 text-2xl font-bold text-white">Estrutura comercial</h1>
            <p className="mt-1 max-w-2xl text-sm text-tec-muted">Árvore nativa do ERPNext. A venda online é controlada por categoria; Peças de Reparo ficam fora dos canais de venda.</p>
          </div>
          {canEdit ? <Button icon={<Plus size={17} />} onClick={() => openEditor()} variant="primary">Nova categoria</Button> : <span className="rounded-control bg-tec-field px-3 py-2 text-xs font-semibold text-tec-muted">Consulta operacional</span>}
        </div>
      </Card>

      <Card className="p-4">
        <LayeredFilters active={quickFilter} filters={[{ key: "active", label: "Ativas" }, { key: "online", label: "Vendáveis online" }, { key: "internal", label: "Uso interno" }, { key: "inactive", label: "Inativas" }, { key: "all", label: "Todas" }]} onClear={() => { setQuery(""); setQuickFilter("active"); setVisibleCount(20); }} onSelect={(key) => { setQuickFilter(key); setVisibleCount(20); }} primary={<label className="relative block"><Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tec-muted" size={17} /><input className="tp-input w-full pl-10" onChange={(event) => { setQuery(event.target.value); setVisibleCount(20); }} placeholder="Buscar categoria ou categoria pai" value={query} /></label>}>
          <p className="text-xs text-tec-muted">A árvore é nativa do ERPNext. Criar, mover ou inativar não altera itens, estoque, preço ou custo.</p>
        </LayeredFilters>
      </Card>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-tec-border/15 px-5 py-4"><div><h2 className="font-bold text-white">Categorias</h2><p className="mt-1 text-xs text-tec-muted">{filteredItems.length} categoria{filteredItems.length === 1 ? "" : "s"} encontrada{filteredItems.length === 1 ? "" : "s"}</p></div><ListGridToggle onChange={setPresentation} value={presentation} /></div>
        {loading ? <p className="p-5 text-sm text-tec-muted">Carregando categorias...</p> : null}
        {!loading && filteredItems.length === 0 ? <p className="p-5 text-sm text-tec-muted">Nenhuma categoria encontrada com estes filtros.</p> : null}
        {!loading && filteredItems.length > 0 && presentation === "list" ? <div className="p-3">{filteredTree.map((item) => <CategoryRow canEdit={canEdit} depth={0} item={item} key={item.name} onEdit={openEditor} onToggle={(name) => setOpenNodes((current) => { const next = new Set(current); if (next.has(name)) next.delete(name); else next.add(name); return next; })} openNodes={openNodes} />)}</div> : null}
        {!loading && filteredItems.length > 0 && presentation === "grid" ? <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">{visibleGridItems.map((item) => <CategoryCard canEdit={canEdit} item={item} key={item.name} onEdit={openEditor} />)}</div> : null}
        {!loading && presentation === "grid" && filteredItems.length > visibleCount ? <div className="border-t border-tec-border/15 p-4 text-center"><Button onClick={() => setVisibleCount((count) => count + 20)}>Mostrar mais (+{Math.min(20, filteredItems.length - visibleCount)})</Button></div> : null}
      </Card>

      <Modal onClose={() => setDraft(null)} open={Boolean(draft)} title={draft?.original_name ? "Editar categoria" : "Nova categoria"}>
        {draft ? <CategoryEditor draft={draft} onChange={setDraft} onClose={() => setDraft(null)} onSave={() => void save()} parents={parents} /> : null}
      </Modal>
    </div>
  );
}

function CategoryCard({ canEdit, item, onEdit }: { canEdit: boolean; item: ProductCategoryNode; onEdit: (item: ProductCategoryNode) => void }) {
  return <div className="flex min-h-40 flex-col rounded-card border border-tec-border/15 bg-tec-field/45 p-4"><div className="flex items-start justify-between gap-3"><span className="grid h-10 w-10 place-items-center rounded-control bg-tec-orange/10 text-tec-orange"><Shapes size={20} /></span>{canEdit && item.name !== "All Item Groups" ? <Button icon={<Edit3 size={15} />} onClick={() => onEdit(item)} title={`Editar ${item.name}`}>Editar</Button> : null}</div><strong className={item.active ? "mt-4 text-sm text-white" : "mt-4 text-sm text-tec-muted line-through"}>{item.name}</strong><p className="mt-1 text-xs text-tec-muted">{item.parent || "Raiz do catálogo"}</p><div className="mt-auto flex flex-wrap gap-2 pt-4">{item.is_group ? <span className="rounded-full bg-tec-panel px-2 py-1 text-[10px] font-bold text-tec-subtle">GRUPO</span> : null}{item.sell_online ? <span className="inline-flex items-center gap-1 rounded-full bg-tec-success/10 px-2 py-1 text-[10px] font-bold text-tec-success"><Globe2 size={12} /> Online</span> : <span className="rounded-full bg-tec-panel px-2 py-1 text-[10px] font-bold text-tec-muted">Interno</span>}</div></div>;
}

function CategoryRow({ canEdit, depth, item, onEdit, onToggle, openNodes }: { canEdit: boolean; depth: number; item: ProductCategoryNode; onEdit: (item: ProductCategoryNode) => void; onToggle: (name: string) => void; openNodes: Set<string> }) {
  const hasChildren = item.children.length > 0;
  const expanded = openNodes.has(item.name);
  return <div>
    <div className="flex min-h-12 items-center gap-2 rounded-control px-3 py-2 hover:bg-tec-field/55" style={{ paddingLeft: `${12 + depth * 22}px` }}>
      {hasChildren ? <button aria-label={`${expanded ? "Recolher" : "Expandir"} ${item.name}`} className="grid h-7 w-7 place-items-center rounded-control text-tec-muted hover:bg-tec-field hover:text-white" onClick={() => onToggle(item.name)} type="button">{expanded ? <ChevronDown size={17} /> : <ChevronRight size={17} />}</button> : <span className="w-7" />}
      <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className={item.active ? "truncate text-sm font-semibold text-white" : "truncate text-sm font-semibold text-tec-muted line-through"}>{item.name}</span>{item.is_group ? <span className="rounded-full bg-tec-field px-2 py-0.5 text-[10px] font-bold text-tec-subtle">GRUPO</span> : null}{!item.active ? <span className="rounded-full bg-tec-field px-2 py-0.5 text-[10px] font-bold text-tec-muted">INATIVA</span> : null}</div><p className="mt-0.5 text-xs text-tec-muted">{item.parent || "Raiz do catálogo"}</p></div>
      {item.sell_online ? <span className="inline-flex items-center gap-1 rounded-full bg-tec-success/10 px-2 py-1 text-[11px] font-bold text-tec-success"><Globe2 size={13} /> Online</span> : <span className="inline-flex items-center gap-1 rounded-full bg-tec-field px-2 py-1 text-[11px] font-bold text-tec-muted"><PowerOff size={13} /> Interno</span>}
      {canEdit && item.name !== "All Item Groups" ? <Button icon={<Edit3 size={15} />} onClick={() => onEdit(item)} title={`Editar ${item.name}`}>Editar</Button> : null}
    </div>
    {hasChildren && expanded ? item.children.map((child) => <CategoryRow canEdit={canEdit} depth={depth + 1} item={child} key={child.name} onEdit={onEdit} onToggle={onToggle} openNodes={openNodes} />) : null}
  </div>;
}

function CategoryEditor({ draft, onChange, onClose, onSave, parents }: { draft: CategoryDraft; onChange: (draft: CategoryDraft) => void; onClose: () => void; onSave: () => void; parents: ProductCategoryNode[] }) {
  const set = <K extends keyof CategoryDraft>(key: K, value: CategoryDraft[K]) => onChange({ ...draft, [key]: value });
  const isRepair = draft.original_name === "Peças de Reparo" || draft.name === "Peças de Reparo";
  const parentOptions = parents.filter((item) => item.name !== draft.original_name && !isChildOf(item, draft.original_name, parents));
  return <div className="space-y-4"><p className="rounded-control bg-tec-field/65 p-3 text-xs text-tec-muted">A categoria é um Item Group nativo. Mover a categoria preserva seus itens; inativar impede novos cadastros nela.</p><label className="grid gap-1.5 text-sm font-semibold text-tec-subtle">Nome<input autoFocus className="tp-input" onChange={(event) => set("name", event.target.value)} value={draft.name} /></label><label className="grid gap-1.5 text-sm font-semibold text-tec-subtle">Categoria pai<select className="tp-input" onChange={(event) => set("parent", event.target.value)} value={draft.parent}>{parentOptions.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}</select></label><div className="grid gap-3 sm:grid-cols-2"><label className="flex items-center gap-2 rounded-control border border-tec-border/15 bg-tec-field/45 p-3 text-sm font-semibold text-tec-text"><input checked={draft.is_group} onChange={(event) => set("is_group", event.target.checked)} type="checkbox" /> Aceita subcategorias</label><label className="flex items-center gap-2 rounded-control border border-tec-border/15 bg-tec-field/45 p-3 text-sm font-semibold text-tec-text"><input checked={draft.active} onChange={(event) => set("active", event.target.checked)} type="checkbox" /> Categoria ativa</label></div><label className="flex items-center gap-2 rounded-control border border-tec-border/15 bg-tec-field/45 p-3 text-sm font-semibold text-tec-text"><input checked={isRepair ? false : draft.sell_online} disabled={isRepair} onChange={(event) => set("sell_online", event.target.checked)} type="checkbox" /> Vendável online{isRepair ? <span className="text-xs text-tec-muted">Peças de reparo são sempre internas.</span> : null}</label><div className="flex justify-end gap-2"><Button onClick={onClose}>Cancelar</Button><Button disabled={!draft.name.trim() || !draft.parent} icon={<Power size={16} />} onClick={onSave} variant="primary">Salvar categoria</Button></div></div>;
}

function flatten(items: ProductCategoryNode[]): ProductCategoryNode[] { return items.flatMap((item) => [item, ...flatten(item.children)]); }
function filterTree(items: ProductCategoryNode[], matchedNames: Set<string>): ProductCategoryNode[] {
  return items.flatMap((item) => {
    const children = filterTree(item.children, matchedNames);
    return matchedNames.has(item.name) || children.length ? [{ ...item, children }] : [];
  });
}
function isChildOf(candidate: ProductCategoryNode, ancestor: string | undefined, all: ProductCategoryNode[]): boolean { if (!ancestor) return false; const map = new Map(flatten(all).map((item) => [item.name, item])); let current = candidate; while (current.parent && map.has(current.parent)) { if (current.parent === ancestor) return true; current = map.get(current.parent)!; } return false; }
