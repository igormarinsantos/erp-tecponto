import { type FormEvent, useEffect, useRef, useState } from "react";
import { Badge, KeyRound, LogOut, ScanBarcode, UserRound } from "lucide-react";

import { pos, type CashierOperatorIdentity, type PosSaleResponse } from "./api";
import { PosScreen } from "./PosScreen";
import { Button } from "./ui";
import type { PosToast } from "./pos/types";

interface CashierModeProps {
  onExit: () => void;
  onToast: PosToast;
}

export function CashierMode({ onExit, onToast }: CashierModeProps) {
  const badgeInputRef = useRef<HTMLInputElement>(null);
  const [badgeCode, setBadgeCode] = useState("");
  const [pin, setPin] = useState("");
  const [identifying, setIdentifying] = useState(false);
  const [operator, setOperator] = useState<CashierOperatorIdentity | null>(null);
  const [usePin, setUsePin] = useState(false);

  useEffect(() => {
    if (!operator) {
      window.requestAnimationFrame(() => badgeInputRef.current?.focus());
    }
  }, [operator, usePin]);

  const identify = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = usePin ? pin.trim() : badgeCode.trim();
    if (!value) {
      onToast(usePin ? "Digite o PIN de 4 digitos." : "Bipe ou digite o codigo do cracha.", "error");
      return;
    }
    setIdentifying(true);
    try {
      const identity = await pos.identifyCashierOperator(usePin ? { pin: value } : { badgeCode: value });
      setOperator(identity);
      setBadgeCode("");
      setPin("");
      onToast(`${identity.operator_name} identificado(a) no caixa.`);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Nao foi possivel identificar o operador.", "error");
    } finally {
      setIdentifying(false);
    }
  };

  const handleSaleCompleted = (sale: PosSaleResponse) => {
    onToast(`Venda ${sale.sale} concluida. Caixa pronto para o proximo bipe.`);
  };

  return (
    <main className="min-h-screen bg-tec-page p-4 text-tec-text md:p-6" data-testid="cashier-mode">
      <div className="mx-auto max-w-[1680px]">
        <header className="mb-5 flex items-center justify-between gap-4 border-b border-tec-border/15 pb-4">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-card bg-tec-orange/15 text-tec-orange"><ScanBarcode size={24} /></span>
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-tec-orange">Tecponto</p>
              <h1 className="text-2xl font-bold text-white">Modo Caixa</h1>
            </div>
          </div>
          <Button icon={<LogOut size={16} />} onClick={onExit} variant="ghost">Sair do caixa</Button>
        </header>

        {!operator ? (
          <section className="mx-auto grid min-h-[calc(100vh-11rem)] max-w-xl place-items-center">
            <div className="w-full rounded-card border border-tec-border/20 bg-tec-panel p-6 shadow-panel">
              <span className="grid h-14 w-14 place-items-center rounded-card bg-tec-orange/15 text-tec-orange">
                {usePin ? <KeyRound size={28} /> : <Badge size={28} />}
              </span>
              <h2 className="mt-5 text-2xl font-bold text-white">Identifique o operador</h2>
              <p className="mt-2 text-sm leading-6 text-tec-subtle">Bipe o cracha para atribuir as vendas. O cracha identifica quem vende, mas nao libera relatorios, aprovacoes ou configuracoes.</p>
              <form className="mt-6 space-y-3" onSubmit={(event) => void identify(event)}>
                {usePin ? (
                  <input
                    aria-label="PIN do operador"
                    className="h-14 w-full rounded-control border border-tec-border/25 bg-tec-field px-4 text-center text-2xl font-bold tracking-[0.4em] text-tec-text outline-none placeholder:text-tec-muted focus:border-tec-orange/70"
                    inputMode="numeric"
                    maxLength={4}
                    onChange={(event) => setPin(event.target.value.replace(/\D/g, ""))}
                    placeholder="----"
                    type="password"
                    value={pin}
                  />
                ) : (
                  <input
                    aria-label="Codigo do cracha"
                    className="h-14 w-full rounded-control border border-tec-border/25 bg-tec-field px-4 text-center font-mono text-lg font-bold text-tec-text outline-none placeholder:text-tec-muted focus:border-tec-orange/70"
                    onChange={(event) => setBadgeCode(event.target.value)}
                    placeholder="Bipe o cracha"
                    ref={badgeInputRef}
                    value={badgeCode}
                  />
                )}
                <Button className="w-full justify-center" disabled={identifying} icon={usePin ? <KeyRound size={18} /> : <ScanBarcode size={18} />} type="submit" variant="primary">
                  {identifying ? "Identificando..." : usePin ? "Entrar com PIN" : "Confirmar cracha"}
                </Button>
              </form>
              <button className="mt-4 w-full text-sm font-semibold text-tec-muted transition hover:text-tec-orange" onClick={() => setUsePin((current) => !current)} type="button">
                {usePin ? "Usar cracha com codigo de barras" : "Meu cracha falhou - usar PIN"}
              </button>
            </div>
          </section>
        ) : (
          <>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-control border border-tec-border/20 bg-tec-panel px-4 py-3">
              <span className="flex items-center gap-2 text-sm text-tec-subtle"><UserRound size={17} className="text-tec-success" /> Operando como <strong className="text-tec-text">{operator.operator_name}</strong><span className="rounded-full bg-tec-field px-2 py-1 text-[10px] font-bold uppercase text-tec-muted">{operator.via === "badge" ? "Cracha" : "PIN"}</span></span>
              <div className="flex items-center gap-2">
                <a className="text-xs font-bold text-tec-muted transition hover:text-tec-orange" href={pos.cashierBadgeUrl(operator.operator)} rel="noreferrer" target="_blank">Imprimir cracha</a>
                <Button onClick={() => setOperator(null)} variant="ghost">Trocar operador</Button>
              </div>
            </div>
            <PosScreen
              cashierOperator={operator}
              cashierMode
              onCashierSaleCompleted={handleSaleCompleted}
              onToast={onToast}
            />
          </>
        )}
      </div>
    </main>
  );
}
