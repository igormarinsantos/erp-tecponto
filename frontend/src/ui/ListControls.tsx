import { Grid2X2, List, SlidersHorizontal, X } from "lucide-react";
import { useState, type ReactNode } from "react";

export type ListPresentation = "list" | "grid";
export interface QuickFilter { key: string; label: string; }

export function ListGridToggle({ value, onChange }: { value: ListPresentation; onChange: (value: ListPresentation) => void }) {
  return <div aria-label="Modo de visualizacao" className="inline-flex rounded-control border border-tec-border/20 bg-tec-field/70 p-1"><button aria-pressed={value === "list"} className={value === "list" ? "grid h-9 w-10 place-items-center rounded-[10px] bg-tec-orange text-tec-ink" : "grid h-9 w-10 place-items-center rounded-[10px] text-tec-muted"} onClick={() => onChange("list")} title="Lista" type="button"><List size={17} /></button><button aria-pressed={value === "grid"} className={value === "grid" ? "grid h-9 w-10 place-items-center rounded-[10px] bg-tec-orange text-tec-ink" : "grid h-9 w-10 place-items-center rounded-[10px] text-tec-muted"} onClick={() => onChange("grid")} title="Cartoes" type="button"><Grid2X2 size={17} /></button></div>;
}

export function LayeredFilters({ active, children, filters, onSelect, onClear }: { active?: string; children: ReactNode; filters: QuickFilter[]; onSelect: (key: string) => void; onClear?: () => void }) {
  const [advancedOpen, setAdvancedOpen] = useState(false);
  return <section className="space-y-3 rounded-card bg-tec-field/35 p-3"><div className="flex flex-wrap items-center gap-2">{filters.map((filter) => <button aria-pressed={active === filter.key} className={active === filter.key ? "rounded-full bg-tec-orange px-3 py-2 text-xs font-bold text-tec-ink" : "rounded-full border border-tec-border/20 bg-tec-field px-3 py-2 text-xs font-bold text-tec-subtle"} key={filter.key} onClick={() => onSelect(filter.key)} type="button">{filter.label}</button>)}<button className="ml-auto inline-flex items-center gap-2 rounded-control border border-tec-border/20 px-3 py-2 text-xs font-bold text-tec-text" onClick={() => setAdvancedOpen((open) => !open)} type="button"><SlidersHorizontal size={15} />Filtros</button>{onClear ? <button className="inline-flex items-center gap-1 text-xs font-bold text-tec-muted" onClick={onClear} type="button"><X size={14} />Limpar</button> : null}</div>{advancedOpen ? <div className="border-t border-tec-border/15 pt-3">{children}</div> : null}</section>;
}
