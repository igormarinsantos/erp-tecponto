import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Edit3, FolderTree, Globe2, Plus, Power, PowerOff } from "lucide-react";

import { productCategories, type ProductCategoryNode } from "./api";
import { Button, Card, Modal } from "./ui";

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

  const parents = useMemo(() => flatten(items).filter((item) => item.is_group && item.active), [items]);
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

      <Card className="overflow-hidden">
        <div className="border-b border-tec-border/15 px-5 py-4"><h2 className="font-bold text-white">Árvore de categorias</h2><p className="mt-1 text-xs text-tec-muted">Criar, mover ou inativar não altera itens, estoque, preço ou custo.</p></div>
        {loading ? <p className="p-5 text-sm text-tec-muted">Carregando categorias...</p> : <div className="p-3">{items.map((item) => <CategoryRow canEdit={canEdit} depth={0} item={item} key={item.name} onEdit={openEditor} onToggle={(name) => setOpenNodes((current) => { const next = new Set(current); if (next.has(name)) next.delete(name); else next.add(name); return next; })} openNodes={openNodes} />)}</div>}
      </Card>

      <Modal onClose={() => setDraft(null)} open={Boolean(draft)} title={draft?.original_name ? "Editar categoria" : "Nova categoria"}>
        {draft ? <CategoryEditor draft={draft} onChange={setDraft} onClose={() => setDraft(null)} onSave={() => void save()} parents={parents} /> : null}
      </Modal>
    </div>
  );
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
function isChildOf(candidate: ProductCategoryNode, ancestor: string | undefined, all: ProductCategoryNode[]): boolean { if (!ancestor) return false; const map = new Map(flatten(all).map((item) => [item.name, item])); let current = candidate; while (current.parent && map.has(current.parent)) { if (current.parent === ancestor) return true; current = map.get(current.parent)!; } return false; }
