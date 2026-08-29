import { useCallback, useEffect, useMemo, useState } from "react";
import { BadgeDollarSign, KeyRound, Plus, Power, ShieldCheck, UserCog, Users } from "lucide-react";

import { userAccounts, type ManagedUserAccount, type UserAccountPayload, type UserRoleOption } from "./api";
import { Button, Card, DataTable, LayeredFilters, ListGridToggle, Modal, StatBar, type ListPresentation, type TableColumn } from "./ui";

type Toast = (message: string, tone?: "success" | "error") => void;

const accountLevelTone: Record<string, string> = {
  "Proprietário": "bg-tec-orange/15 text-tec-orange",
  "Administrador do Sistema": "bg-tec-purple/15 text-tec-purple",
  "Usuário comum": "bg-tec-field text-tec-muted",
};

function formatLogin(value: string) {
  if (!value) return "Nunca acessou";
  const date = new Date(value.replace(" ", "T"));
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(date);
}

const emptyDraft = (): UserAccountPayload => ({ full_name: "", email: "", enabled: true, roles: [], discount_limit: 0, cashier: { enabled: false, badge_code: "", pin: "" } });

export function UserManagementScreen({ onToast }: { onToast: Toast }) {
  const [items, setItems] = useState<ManagedUserAccount[]>([]);
  const [roleOptions, setRoleOptions] = useState<UserRoleOption[]>([]);
  const [stats, setStats] = useState({ total: 0, active: 0, administrators: 0, operational: 0 });
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "active" | "inactive" | "admin">("all");
  const [presentation, setPresentation] = useState<ListPresentation>(() => window.localStorage.getItem("tecponto.user-management.presentation") === "grid" ? "grid" : "list");
  const [selected, setSelected] = useState<ManagedUserAccount | null>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState<string | null>(null);
	const [resetTarget, setResetTarget] = useState<ManagedUserAccount | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await userAccounts.list(query, true);
      setItems(response.items);
      setStats(response.stats);
      setRoleOptions(response.role_options);
    } catch (error) {
      onToast(error instanceof Error ? error.message : "Não foi possível carregar as pessoas.", "error");
    }
  }, [onToast, query]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { window.localStorage.setItem("tecponto.user-management.presentation", presentation); }, [presentation]);

  const visibleItems = useMemo(() => items.filter((item) => (
    filter === "active" ? item.enabled : filter === "inactive" ? !item.enabled : filter === "admin" ? item.account_level !== "Usuário comum" : true
  )), [filter, items]);

  const openCreate = () => { setSelected(null); setOpen(true); };
  const openEdit = (item: ManagedUserAccount) => { setSelected(item); setOpen(true); };

  const columns = useMemo<Array<TableColumn<ManagedUserAccount>>>(() => [
    { key: "person", label: "Pessoa", render: (row) => <span><strong className="block text-white">{row.full_name}</strong><span className="text-xs text-tec-muted">{row.email}</span></span> },
    { key: "roles", label: "Papéis", render: (row) => <RolePills roles={row.roles} /> },
    { key: "level", label: "Nível da conta", render: (row) => <LevelPill level={row.account_level} /> },
    { key: "status", label: "Acesso", render: (row) => <span className={row.enabled ? "font-bold text-tec-success" : "font-bold text-tec-red"}>{row.enabled ? "Ativo" : "Inativo"}</span> },
    { key: "last_login", label: "Último acesso", render: (row) => formatLogin(row.last_login) },
    { key: "actions", label: "Ações", render: (row) => <div className="flex justify-end gap-2"><button className="rounded-control border border-tec-border/20 px-2 py-1 text-xs font-bold text-tec-subtle hover:border-tec-orange/50 hover:text-white" onClick={(event) => { event.stopPropagation(); openEdit(row); }} type="button">Editar</button><button className="grid h-8 w-8 place-items-center rounded-control border border-tec-border/20 text-tec-muted hover:border-tec-orange/50 hover:text-white" disabled={resetting === row.name} onClick={(event) => { event.stopPropagation(); setResetTarget(row); }} title="Redefinir senha manualmente" type="button"><KeyRound size={15} /></button></div> },
  ], [resetting]);

  return <div className="space-y-4">
    <div className="flex flex-wrap items-center justify-end gap-2"><ListGridToggle onChange={setPresentation} value={presentation} /><Button icon={<Plus size={17} />} onClick={openCreate} variant="primary">Cadastrar pessoa</Button></div>
    <StatBar items={[
      { key: "total", label: "Pessoas", value: stats.total, detail: "Contas cadastradas", icon: <Users size={19} />, tone: "blue" },
      { key: "active", label: "Ativas", value: stats.active, detail: "Com acesso liberado", icon: <Power size={19} />, tone: "green" },
      { key: "admins", label: "Administradores", value: stats.administrators, detail: "Nível de conta", icon: <ShieldCheck size={19} />, tone: "blue" },
      { key: "operational", label: "Operacionais", value: stats.operational, detail: "Com papel de negócio", icon: <UserCog size={19} />, tone: "orange" },
    ]} />
    <LayeredFilters active={filter} filters={[{ key: "all", label: "Todas" }, { key: "active", label: "Ativas" }, { key: "inactive", label: "Inativas" }, { key: "admin", label: "Administração" }]} onClear={() => { setFilter("all"); setQuery(""); }} onSelect={(value) => setFilter(value as typeof filter)}>
      <label className="block text-xs font-bold text-tec-subtle">Buscar pessoa<input className="tp-input mt-1 w-full" onChange={(event) => setQuery(event.target.value)} placeholder="Nome ou e-mail" value={query} /></label>
    </LayeredFilters>
    {presentation === "grid" ? <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{visibleItems.map((item) => <Card className="p-4" key={item.name}><div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="truncate font-bold text-white">{item.full_name}</p><p className="truncate text-xs text-tec-muted">{item.email}</p></div><LevelPill level={item.account_level} /></div><div className="mt-4"><RolePills roles={item.roles} /></div><div className="mt-4 flex items-center justify-between text-xs"><span className={item.enabled ? "font-bold text-tec-success" : "font-bold text-tec-red"}>{item.enabled ? "Acesso ativo" : "Conta inativa"}</span><span className="text-tec-muted">{formatLogin(item.last_login)}</span></div><div className="mt-4 flex gap-2"><Button className="flex-1" onClick={() => openEdit(item)} variant="secondary">Editar</Button><button className="grid h-10 w-10 place-items-center rounded-control border border-tec-border/20 text-tec-muted hover:border-tec-orange/50 hover:text-white" disabled={resetting === item.name} onClick={() => setResetTarget(item)} title="Redefinir senha manualmente" type="button"><KeyRound size={16} /></button></div></Card>)}{!visibleItems.length ? <Card className="p-6 text-sm text-tec-muted sm:col-span-2 xl:col-span-3">Nenhuma pessoa encontrada.</Card> : null}</section> : <DataTable columns={columns} emptyLabel="Nenhuma pessoa encontrada." onRowClick={openEdit} rows={visibleItems} tableMinWidthClassName="min-w-[980px]" />}
    <UserEditorModal item={selected} onClose={() => setOpen(false)} onSaved={() => { setOpen(false); void load(); }} onToast={onToast} open={open} roleOptions={roleOptions} setSaving={setSaving} saving={saving} />
	<PasswordResetModal item={resetTarget} onClose={() => setResetTarget(null)} onToast={onToast} resetting={resetting} setResetting={setResetting} />
  </div>;
}

function UserEditorModal({ item, onClose, onSaved, onToast, open, roleOptions, saving, setSaving }: { item: ManagedUserAccount | null; onClose: () => void; onSaved: () => void; onToast: Toast; open: boolean; roleOptions: UserRoleOption[]; saving: boolean; setSaving: (value: boolean) => void }) {
  const [draft, setDraft] = useState<UserAccountPayload>(emptyDraft());
  const [error, setError] = useState("");
	const [passwordConfirm, setPasswordConfirm] = useState("");
  useEffect(() => {
    if (!open) return;
    setError("");
	setPasswordConfirm("");
    setDraft(item ? { name: item.name, full_name: item.full_name, email: item.email, enabled: item.enabled, roles: item.roles, discount_limit: item.discount_limit, cashier: { enabled: item.cashier.enabled, badge_code: item.cashier.badge_code, pin: "" } } : emptyDraft());
  }, [item, open]);
  const toggleRole = (option: UserRoleOption) => {
    if (!option.allowed) return;
    setDraft((current) => ({ ...current, roles: current.roles.includes(option.role) ? current.roles.filter((role) => role !== option.role) : [...current.roles, option.role] }));
  };
  const save = async () => {
	if (draft.password && draft.password !== passwordConfirm) { setError("As senhas não coincidem."); return; }
	if (!item && (!draft.password || draft.password.length < 8)) { setError("Defina uma senha inicial com pelo menos 8 caracteres."); return; }
    setError(""); setSaving(true);
    try { await userAccounts.save(draft); onToast(item ? "Pessoa atualizada." : "Pessoa cadastrada."); onSaved(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Não foi possível salvar a pessoa."); }
    finally { setSaving(false); }
  };
  const cashier = draft.cashier ?? { enabled: false, badge_code: "", pin: "" };
  return <Modal className="max-w-3xl" onClose={onClose} open={open} title={item ? `Editar ${item.full_name}` : "Cadastrar pessoa"}>
    <div className="max-h-[75vh] space-y-5 overflow-y-auto pr-1">
      <section className="grid gap-3 sm:grid-cols-2"><label className="text-sm font-bold text-white">Nome completo<input className="tp-input mt-1 w-full" onChange={(event) => setDraft({ ...draft, full_name: event.target.value })} value={draft.full_name} /></label><label className="text-sm font-bold text-white">E-mail{item ? <input className="tp-input mt-1 w-full opacity-65" disabled value={draft.email ?? ""} /> : <input className="tp-input mt-1 w-full" onChange={(event) => setDraft({ ...draft, email: event.target.value })} placeholder="pessoa@empresa.com" type="email" value={draft.email ?? ""} />}</label></section>
	  <section className="grid gap-3 rounded-card border border-tec-border/20 bg-tec-panel-strong p-4 sm:grid-cols-2"><label className="text-sm font-bold text-white">{item ? "Nova senha (opcional)" : "Senha inicial"}<input autoComplete="new-password" className="tp-input mt-1 w-full" minLength={8} onChange={(event) => setDraft({ ...draft, password: event.target.value })} placeholder="Mínimo de 8 caracteres" type="password" value={draft.password ?? ""} /></label><label className="text-sm font-bold text-white">Confirmar senha<input autoComplete="new-password" className="tp-input mt-1 w-full" minLength={8} onChange={(event) => setPasswordConfirm(event.target.value)} type="password" value={passwordConfirm} /></label><p className="text-xs text-tec-muted sm:col-span-2">A senha é definida diretamente, não é enviada por e-mail e nunca volta na resposta da API.</p></section>
      <label className="flex items-center gap-3 rounded-control border border-tec-border/20 bg-tec-field/55 px-3 py-3 text-sm font-semibold text-white"><input checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} type="checkbox" /> Conta ativa <span className="ml-auto text-xs font-normal text-tec-muted">Desativar preserva o histórico e bloqueia o acesso.</span></label>
      <section><div className="mb-2"><h3 className="font-bold text-white">Papéis de negócio e nível de conta</h3><p className="mt-1 text-xs text-tec-muted">Os papéis se somam na mesma conta. As permissões finais continuam validadas no motor.</p></div><div className="grid gap-2 sm:grid-cols-2">{roleOptions.map((option) => <label className={`rounded-control border p-3 ${option.allowed ? "border-tec-border/20 bg-tec-field/55" : "cursor-not-allowed border-tec-border/10 bg-tec-field/25 opacity-65"}`} key={option.role} title={option.reason || option.role}><span className="flex items-center gap-2"><input checked={draft.roles.includes(option.role)} disabled={!option.allowed} onChange={() => toggleRole(option)} type="checkbox" /><strong className="text-sm text-white">{roleLabel(option.role)}</strong></span>{!option.allowed ? <span className="mt-2 block text-xs leading-5 text-tec-amber">{option.reason}</span> : null}</label>)}</div></section>
      <section className="grid gap-3 rounded-card border border-tec-border/20 bg-tec-panel-strong p-4 sm:grid-cols-2"><label className="text-sm font-bold text-white">Limite individual de desconto<input className="tp-input mt-1 w-full" min="0" onChange={(event) => setDraft({ ...draft, discount_limit: Number(event.target.value) || 0 })} step="0.01" type="number" value={draft.discount_limit || ""} /><span className="mt-1 block text-xs font-normal text-tec-muted">Em branco/zero usa o limite geral. O motor aplica este valor na venda.</span></label><div className="text-sm"><span className="font-bold text-white">Modo caixa</span><label className="mt-2 flex items-center gap-2 text-tec-subtle"><input checked={cashier.enabled} onChange={(event) => setDraft({ ...draft, cashier: { ...cashier, enabled: event.target.checked } })} type="checkbox" /> Ativar crachá e PIN</label>{cashier.enabled ? <div className="mt-3 grid gap-2"><input className="tp-input" onChange={(event) => setDraft({ ...draft, cashier: { ...cashier, badge_code: event.target.value } })} placeholder="Código do crachá" value={cashier.badge_code} /><input className="tp-input" inputMode="numeric" maxLength={4} onChange={(event) => setDraft({ ...draft, cashier: { ...cashier, pin: event.target.value } })} placeholder={item?.cashier.has_pin ? "Novo PIN (opcional)" : "PIN de 4 dígitos"} type="password" value={cashier.pin ?? ""} /></div> : null}</div></section>
      {error ? <p className="rounded-control border border-tec-red/35 bg-tec-red/10 px-3 py-2 text-sm text-tec-red">{error}</p> : null}
    </div><div className="mt-5 flex justify-end gap-2"><Button onClick={onClose} variant="ghost">Cancelar</Button><Button disabled={saving || !draft.full_name.trim() || (!item && !draft.email?.trim())} icon={<UserCog size={17} />} onClick={() => void save()} variant="primary">{saving ? "Salvando..." : item ? "Salvar alterações" : "Criar pessoa"}</Button></div>
  </Modal>;
}

function PasswordResetModal({ item, onClose, onToast, resetting, setResetting }: { item: ManagedUserAccount | null; onClose: () => void; onToast: Toast; resetting: string | null; setResetting: (value: string | null) => void }) {
	const [password, setPassword] = useState("");
	const [confirmation, setConfirmation] = useState("");
	const [error, setError] = useState("");
	useEffect(() => { if (item) { setPassword(""); setConfirmation(""); setError(""); } }, [item]);
	const save = async () => {
		if (password.length < 8) { setError("A senha precisa ter pelo menos 8 caracteres."); return; }
		if (password !== confirmation) { setError("As senhas não coincidem."); return; }
		setResetting(item?.name ?? null); setError("");
		try {
			if (!item) return;
			await userAccounts.setPassword(item.name, password);
			onToast(`Senha de ${item.full_name} redefinida sem envio de e-mail.`);
			onClose();
		} catch (caught) {
			setError(caught instanceof Error ? caught.message : "Não foi possível redefinir a senha.");
		} finally { setResetting(null); }
	};
	return <Modal className="max-w-lg" onClose={onClose} open={Boolean(item)} title="Redefinir senha manualmente"><div className="space-y-4"><p className="text-sm text-tec-subtle">Defina uma nova senha para <strong className="text-white">{item?.full_name}</strong>. Nenhuma notificação será enviada.</p><label className="block text-sm font-bold text-white">Nova senha<input autoComplete="new-password" className="tp-input mt-1 w-full" minLength={8} onChange={(event) => setPassword(event.target.value)} type="password" value={password} /></label><label className="block text-sm font-bold text-white">Confirmar nova senha<input autoComplete="new-password" className="tp-input mt-1 w-full" minLength={8} onChange={(event) => setConfirmation(event.target.value)} type="password" value={confirmation} /></label>{error ? <p className="rounded-control border border-tec-red/35 bg-tec-red/10 px-3 py-2 text-sm text-tec-red">{error}</p> : null}</div><div className="mt-5 flex justify-end gap-2"><Button onClick={onClose} variant="ghost">Cancelar</Button><Button disabled={!item || resetting === item.name} icon={<KeyRound size={17} />} onClick={() => void save()} variant="primary">{resetting ? "Redefinindo..." : "Redefinir senha"}</Button></div></Modal>;
}

function RolePills({ roles }: { roles: string[] }) { return <div className="flex flex-wrap gap-1">{roles.length ? roles.map((role) => <span className="rounded-full bg-tec-field px-2 py-1 text-[10px] font-bold text-tec-subtle" key={role}>{roleLabel(role)}</span>) : <span className="text-xs text-tec-muted">Sem papel</span>}</div>; }
function LevelPill({ level }: { level: string }) { return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${accountLevelTone[level] ?? accountLevelTone["Usuário comum"]}`}>{level}</span>; }
function roleLabel(role: string) { return role.replace("Tecponto ", "").replace("System Manager", "Administrador do Sistema"); }
