import { Card } from "../ui";

const shortcuts = [
  ["F2", "Cliente"],
  ["F3", "Desconto"],
  ["F5", "Finalizar venda"],
  ["Ctrl K", "Busca rápida"],
  ["Esc", "Limpar busca"],
  ["Enter", "Adicionar produto"],
];

export function KeyboardShortcuts() {
  return (
    <Card className="p-4">
      <h3 className="text-sm font-bold text-white">Atalhos de teclado</h3>
      <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2">
        {shortcuts.map(([key, label]) => (
          <div className="flex items-center gap-2 text-[11px] text-tec-muted" key={key}>
            <kbd className="min-w-7 rounded-[6px] border border-tec-border/15 bg-tec-field px-1.5 py-1 text-center font-bold text-tec-subtle">{key}</kbd>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
