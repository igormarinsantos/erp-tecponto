import { useCallback, useEffect, useMemo, useState } from "react";
import { Edit3, Link2, Plus, Search } from "lucide-react";

import { defectServiceMappings, serviceCatalog, type DefectServiceMapping, type ServiceCatalogService } from "./api";
import { Button, Card, getStatBarVisual, getStoredListPresentation, LayeredFilters, ListGridToggle, Modal, StatBar, type ListPresentation } from "./ui";

type ToastTone = "success" | "error";
type Draft = Partial<DefectServiceMapping>;

const blankDraft: Draft = { active: true, defect: "", catalog_service: "" };

export function DefectServiceMappingScreen({ canEdit, onToast }: { canEdit: boolean; onToast: (message: string, tone?: ToastTone) => void }) {
  const [items, setItems] = useState<DefectServiceMapping[]>([]);
  const [services, setServices] = useState<ServiceCatalogService[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState<Draft>(blankDraft);
  const [editorOpen, setEditorOpen] = useState(false);
  const [presentation, setPresentation] = useState<ListPresentation>(() => getStoredListPresentation("tecponto.defect-service-mapping.presentation"));
  const [query, setQuery] = useState("");
  const [quickFilter, setQuickFilter] = useState("active");
  const [visibleCount, setVisibleCount] = useState(20);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [mappings, catalog] = await Promise.all([defectServiceMappings.list(true), serviceCatalog.list("", "", "", false)]);
      setItems(mappings.items);
      setServices(catalog.items);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível carregar os mapeamentos.", "error");
    } finally {
      setLoading(false);
    }
  }, [onToast]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { window.localStorage.setItem("tecponto.defect-service-mapping.presentation", presentation); }, [presentation]);

  const filteredItems = useMemo(() => items.filter((item) => {
    const normalized = query.trim().toLocaleLowerCase("pt-BR");
    const textMatches = !normalized || `${item.defect} ${item.catalog_service_label}`.toLocaleLowerCase("pt-BR").includes(normalized);
    const stateMatches = quickFilter === "all" || (quickFilter === "active" && item.active) || (quickFilter === "inactive" && !item.active);
    return textMatches && stateMatches;
  }), [items, query, quickFilter]);
  const statItems = useMemo(() => [
    { key: "active", label: "Sugestões ativas", value: items.filter((item) => item.active).length },
    { key: "inactive", label: "Inativas", value: items.filter((item) => !item.active).length },
    { key: "services", label: "Serviços disponíveis", value: services.filter((item) => item.active).length },
  ], [items, services]);

  const save = async () => {
    try {
      await defectServiceMappings.save(draft);
      onToast(draft.name ? "Mapeamento atualizado." : "Mapeamento criado.", "success");
      setEditorOpen(false);
      await load();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível salvar o mapeamento.", "error");
    }
  };

  return <>
    <StatBar items={statItems.map((item) => ({ ...item, ...getStatBarVisual("defect-service-mapping", item.key) }))} onSelect={(key) => { if (key !== "services") setQuickFilter(key); setVisibleCount(20); }} />
    <Card className="p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div><div className="flex items-center gap-2 text-tec-orange"><Link2 size={20} /><span className="text-sm font-bold">Defeito → serviço sugerido</span></div><p className="mt-1 max-w-2xl text-sm text-tec-muted">Sugere o serviço e a previsão no check-in. Nunca fecha diagnóstico nem bloqueia a abertura da OS.</p></div>
        {canEdit ? <Button icon={<Plus size={16} />} onClick={() => { setDraft(blankDraft); setEditorOpen(true); }} variant="primary">Novo mapeamento</Button> : <span className="rounded-control bg-tec-field px-3 py-2 text-xs font-semibold text-tec-muted">Consulta operacional</span>}
      </div>
    </Card>
    <Card className="mt-4 p-4">
      <LayeredFilters active={quickFilter} filters={[{ key: "active", label: "Ativos" }, { key: "inactive", label: "Inativos" }, { key: "all", label: "Todos" }]} onClear={() => { setQuery(""); setQuickFilter("active"); setVisibleCount(20); }} onSelect={(key) => { setQuickFilter(key); setVisibleCount(20); }} primary={<label className="relative block"><Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-tec-muted" size={17} /><input className="tp-input w-full pl-10" onChange={(event) => { setQuery(event.target.value); setVisibleCount(20); }} placeholder="Buscar defeito ou serviço sugerido" value={query} /></label>}>
        <p className="text-xs text-tec-muted">O serviço é apenas uma sugestão. O atendente pode ajustar o orçamento e a previsão a qualquer momento.</p>
      </LayeredFilters>
    </Card>
    <Card className="mt-4 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-tec-border/15 px-4 py-3"><div><h2 className="font-bold text-white">Mapeamentos</h2><span className="text-sm text-tec-muted">{filteredItems.length} pares encontrados</span></div><ListGridToggle onChange={setPresentation} value={presentation} /></div>
      {loading ? <p className="p-5 text-sm text-tec-muted">Carregando mapeamentos...</p> : null}
      {!loading && !filteredItems.length ? <p className="p-5 text-sm text-tec-muted">Nenhum mapeamento encontrado com estes filtros.</p> : null}
      {!loading && filteredItems.length && presentation === "list" ? <div className="divide-y divide-tec-border/15">{filteredItems.slice(0, visibleCount).map((item) => <MappingRow canEdit={canEdit} item={item} key={item.name} onEdit={() => { setDraft(item); setEditorOpen(true); }} />)}</div> : null}
      {!loading && filteredItems.length && presentation === "grid" ? <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">{filteredItems.slice(0, visibleCount).map((item) => <MappingRow canEdit={canEdit} grid item={item} key={item.name} onEdit={() => { setDraft(item); setEditorOpen(true); }} />)}</div> : null}
      {!loading && filteredItems.length > visibleCount ? <div className="border-t border-tec-border/15 p-4 text-center"><Button onClick={() => setVisibleCount((count) => count + 20)}>Mostrar mais (+{Math.min(20, filteredItems.length - visibleCount)})</Button></div> : null}
    </Card>
    <Modal onClose={() => setEditorOpen(false)} open={editorOpen} title={draft.name ? "Editar mapeamento" : "Novo mapeamento"}><div className="grid gap-4"><label className="grid gap-1.5 text-sm font-semibold text-tec-subtle">Defeito relatado<input autoFocus className="tp-input" onChange={(event) => setDraft({ ...draft, defect: event.target.value })} placeholder="Ex.: Tela quebrada" value={draft.defect ?? ""} /></label><label className="grid gap-1.5 text-sm font-semibold text-tec-subtle">Serviço sugerido<select className="tp-input" onChange={(event) => setDraft({ ...draft, catalog_service: event.target.value })} value={draft.catalog_service ?? ""}><option value="">Selecione um serviço</option>{services.map((service) => <option key={service.name} value={service.name}>{service.service_name}</option>)}</select></label><label className="flex items-center gap-2 text-sm font-semibold text-tec-subtle"><input checked={draft.active !== false} onChange={(event) => setDraft({ ...draft, active: event.target.checked })} type="checkbox" /> Mapeamento ativo</label></div><div className="mt-5 flex justify-end gap-2"><Button onClick={() => setEditorOpen(false)}>Cancelar</Button><Button disabled={!canEdit || !draft.defect?.trim() || !draft.catalog_service} onClick={() => void save()} variant="primary">Salvar</Button></div></Modal>
  </>;
}

function MappingRow({ canEdit, grid = false, item, onEdit }: { canEdit: boolean; grid?: boolean; item: DefectServiceMapping; onEdit: () => void }) {
  return <div className={grid ? "flex min-h-36 flex-col gap-4 rounded-card border border-tec-border/15 bg-tec-field/45 p-4" : "flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"}><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><p className="text-sm font-bold text-white">{item.defect}</p>{item.active ? <span className="rounded-full bg-tec-success/15 px-2 py-1 text-[11px] font-bold text-tec-success">Ativo</span> : <span className="rounded-full bg-tec-field px-2 py-1 text-[11px] font-bold text-tec-muted">Inativo</span>}</div><p className="mt-2 text-xs text-tec-muted">Sugere <span className="font-semibold text-tec-subtle">{item.catalog_service_label}</span></p></div><div className="flex shrink-0 items-center gap-2">{canEdit ? <Button icon={<Edit3 size={15} />} onClick={onEdit}>Editar</Button> : null}</div></div>;
}
