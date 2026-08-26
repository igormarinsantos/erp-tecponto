import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowDownToLine, ArrowUpFromLine, CircleDollarSign, ReceiptText, WalletCards } from "lucide-react";

import { pos, type CashStatementResponse } from "./api";
import { Button, Card, Modal } from "./ui";

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function operationKey(prefix: string) {
  return `${prefix}-${crypto.randomUUID()}`;
}

export function CashStatementScreen({ onToast }: { onToast: (message: string, tone?: "success" | "error") => void }) {
  const [statement, setStatement] = useState<CashStatementResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [movementType, setMovementType] = useState<"Sangria" | "Suprimento" | null>(null);
  const [movementAmount, setMovementAmount] = useState(0);
  const [movementReason, setMovementReason] = useState("");
  const [savingMovement, setSavingMovement] = useState(false);
  const [closingOpen, setClosingOpen] = useState(false);
  const [counted, setCounted] = useState<Record<string, number>>({});
  const [closingReason, setClosingReason] = useState("");
  const [closing, setClosing] = useState(false);
	const [visibleMovements, setVisibleMovements] = useState(30);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await pos.getCashStatement();
      setStatement(next);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível carregar o extrato.", "error");
    } finally {
      setLoading(false);
    }
  }, [onToast]);

  useEffect(() => { void refresh(); }, [refresh]);

	useEffect(() => { setVisibleMovements(30); }, [statement?.session?.session]);

  const totals = statement?.payment_totals ?? [];
  const differences = useMemo(() => totals.map((total) => ({
    ...total,
    counted_amount: Number(counted[total.payment_mode] ?? total.expected_amount),
    difference: Number((Number(counted[total.payment_mode] ?? total.expected_amount) - total.expected_amount).toFixed(2)),
  })), [counted, totals]);
  const hasDifference = differences.some((item) => item.difference !== 0);

  const openClosing = () => {
    setCounted(Object.fromEntries(totals.map((item) => [item.payment_mode, item.expected_amount])));
    setClosingReason("");
    setClosingOpen(true);
  };

  const saveMovement = async () => {
    if (!movementType || movementAmount <= 0 || !movementReason.trim()) return;
    setSavingMovement(true);
    try {
      await pos.registerDrawerMovement(movementType, movementAmount, movementReason.trim(), operationKey("drawer"));
      onToast(`${movementType} registrada no extrato.`, "success");
      setMovementType(null);
      setMovementAmount(0);
      setMovementReason("");
      await refresh();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível registrar o movimento.", "error");
    } finally {
      setSavingMovement(false);
    }
  };

  const closeSession = async () => {
    if (hasDifference && !closingReason.trim()) {
      onToast("Informe o motivo da divergência antes de fechar.", "error");
      return;
    }
    setClosing(true);
    try {
      await pos.closeCashSession(Object.fromEntries(differences.map((item) => [item.payment_mode, item.counted_amount])), closingReason.trim(), operationKey("closing"));
      onToast("Caixa fechado e conferência auditada.", "success");
      setClosingOpen(false);
      await refresh();
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível fechar o caixa.", "error");
    } finally {
      setClosing(false);
    }
  };

  if (loading) return <Card className="p-5 text-sm text-tec-subtle">Carregando extrato de caixa...</Card>;
  if (!statement?.session) return <Card className="p-5 text-sm text-tec-subtle">Nenhuma sessão de caixa foi aberta ainda.</Card>;
  const session = statement.session;

  return (
    <div className="space-y-5" data-testid="cash-statement-screen">
      <section className="grid gap-3 md:grid-cols-3">
        <Card className="p-5"><p className="text-xs font-bold uppercase text-tec-muted">Gaveta agora</p><p className="mt-2 text-3xl font-bold text-white">{brl.format(statement.drawer_balance)}</p><p className="mt-1 text-xs text-tec-subtle">Saldo físico derivado</p></Card>
        {totals.filter((item) => !item.affects_drawer).slice(0, 2).map((item) => <Card className="p-5" key={item.payment_mode}><p className="text-xs font-bold uppercase text-tec-muted">{item.payment_mode}</p><p className="mt-2 text-2xl font-bold text-white">{brl.format(item.expected_amount)}</p><p className="mt-1 text-xs text-tec-subtle">Registrado na sessão</p></Card>)}
      </section>

      <Card className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center lg:justify-between">
        <div><div className="flex items-center gap-2 text-white"><WalletCards size={18} className="text-tec-orange" /><h2 className="font-bold">{session.status === "Aberto" ? "Caixa aberto" : "Caixa fechado"}</h2></div><p className="mt-1 text-sm text-tec-subtle">{session.cash_point} · aberto por {session.opened_by} em {session.opened_at}</p>{session.status === "Fechado" ? <p className="mt-2 text-sm text-tec-subtle">Fechado por {session.closed_by} em {session.closed_at}{session.closing_reason ? ` · ${session.closing_reason}` : ""}</p> : null}</div>
        {session.status === "Aberto" ? <div className="flex flex-wrap gap-2"><Button icon={<ArrowUpFromLine size={16} />} onClick={() => setMovementType("Suprimento")}>Suprimento</Button><Button icon={<ArrowDownToLine size={16} />} onClick={() => setMovementType("Sangria")}>Sangria</Button><Button icon={<CircleDollarSign size={16} />} onClick={openClosing} variant="primary">Fechar caixa</Button></div> : null}
      </Card>

      <Card className="overflow-hidden">
        <div className="flex items-center justify-between border-b border-tec-border/20 p-5"><div><h2 className="font-bold text-white">Extrato da sessão</h2><p className="mt-1 text-sm text-tec-subtle">Entradas e saídas vinculadas aos documentos de origem.</p></div><ReceiptText className="text-tec-orange" size={20} /></div>
        <div className="divide-y divide-tec-border/15">
          {statement.movements.slice(0, visibleMovements).map((movement) => <div className="grid gap-2 p-4 text-sm md:grid-cols-[1.2fr_.8fr_.7fr_1fr] md:items-center" key={movement.movement}><div><p className="font-semibold text-white">{movement.movement_type}</p><p className="mt-1 text-xs text-tec-muted">{movement.occurred_on}{movement.reason ? ` · ${movement.reason}` : ""}</p></div><span className="text-tec-subtle">{movement.payment_mode}{movement.affects_drawer ? " · Gaveta" : ""}</span><span className={movement.direction === "Entrada" ? "font-bold text-tec-success" : "font-bold text-tec-red"}>{movement.direction === "Entrada" ? "+" : "−"}{brl.format(movement.amount)}</span><span className="text-xs text-tec-muted">{movement.reference_name ? `${movement.reference_doctype}: ${movement.reference_name}` : "Movimento manual"}</span></div>)}
          {!statement.movements.length ? <p className="p-5 text-sm text-tec-subtle">Ainda não há movimentos nesta sessão.</p> : null}
        </div>
			{statement.movements.length > visibleMovements ? <div className="border-t border-tec-border/15 p-3 text-center"><Button onClick={() => setVisibleMovements((current) => current + 30)}>Mostrar mais ({statement.movements.length - visibleMovements})</Button></div> : null}
      </Card>

      <Modal className="max-w-md" onClose={() => !savingMovement && setMovementType(null)} open={Boolean(movementType)} title={movementType ?? "Movimento de gaveta"}>
        <div className="space-y-4"><p className="text-sm text-tec-subtle">{movementType === "Sangria" ? "Registre a retirada física de dinheiro da gaveta." : "Registre a entrada física de troco na gaveta."}</p><label className="block text-sm font-semibold text-white">Valor<input className="tp-input mt-2 w-full" inputMode="decimal" min="0" onChange={(event) => setMovementAmount(Math.max(0, Number(event.target.value) || 0))} step="0.01" type="number" value={movementAmount || ""} /></label><label className="block text-sm font-semibold text-white">Motivo<textarea className="tp-input mt-2 min-h-24 w-full" onChange={(event) => setMovementReason(event.target.value)} value={movementReason} /></label><div className="flex justify-end gap-2"><Button disabled={savingMovement} onClick={() => setMovementType(null)}>Cancelar</Button><Button disabled={savingMovement || movementAmount <= 0 || !movementReason.trim()} onClick={() => void saveMovement()} variant="primary">{savingMovement ? "Registrando..." : "Confirmar"}</Button></div></div>
      </Modal>

      <Modal className="max-w-2xl" onClose={() => !closing && setClosingOpen(false)} open={closingOpen} title="Fechar caixa">
        <div className="space-y-4"><p className="text-sm text-tec-subtle">Confira os valores da sessão. Divergências ficam registradas e não impedem o fechamento.</p><div className="overflow-hidden rounded-control border border-tec-border/20"><div className="grid grid-cols-[1fr_.9fr_.9fr_.7fr] gap-2 border-b border-tec-border/20 bg-tec-field px-3 py-2 text-xs font-bold uppercase text-tec-muted"><span>Forma</span><span>Esperado</span><span>Contado</span><span>Diferença</span></div>{differences.map((item) => <div className="grid grid-cols-[1fr_.9fr_.9fr_.7fr] items-center gap-2 px-3 py-3 text-sm" key={item.payment_mode}><span className="font-semibold text-white">{item.payment_mode}</span><span>{brl.format(item.expected_amount)}</span><input className="tp-input min-w-0 py-2" inputMode="decimal" onChange={(event) => setCounted((current) => ({ ...current, [item.payment_mode]: Number(event.target.value) || 0 }))} step="0.01" type="number" value={item.counted_amount} /><span className={item.difference === 0 ? "text-tec-success" : "font-bold text-tec-red"}>{brl.format(item.difference)}</span></div>)}</div>{hasDifference ? <label className="block text-sm font-semibold text-white">Motivo da divergência<textarea className="tp-input mt-2 min-h-20 w-full" onChange={(event) => setClosingReason(event.target.value)} value={closingReason} /></label> : null}<div className="flex justify-end gap-2"><Button disabled={closing} onClick={() => setClosingOpen(false)}>Cancelar</Button><Button disabled={closing || (hasDifference && !closingReason.trim())} onClick={() => void closeSession()} variant="primary">{closing ? "Fechando..." : "Fechar caixa"}</Button></div></div>
      </Modal>
    </div>
  );
}
