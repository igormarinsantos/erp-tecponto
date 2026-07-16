# Bloco 3.12 — Motor de prazos + Agenda processual (guia otimizado para Codex)

> **Contexto:** transforma o sistema em processual de verdade — cada OS tem prazos por etapa, e a agenda emerge do estado real, mostrando o que precisa de ação hoje/está atrasando. É o coração do "nada fica pra depois". Pré-requisito: cadastro de serviços (3.10, com `default_duration`) e pendências derivadas (3.8-3).
>
> **PRINCÍPIO CENTRAL (repetido do 3.10):** o motor de prazos **sugere e alerta, nunca bloqueia**. Nenhum prazo trava a abertura ou o andamento de uma OS. Prazo estourado gera **alerta/pendência**, não impedimento.

## CONCEITO: relógio por etapa

Cada OS, em cada etapa do funil, tem um **prazo interno** para avançar. Se o tempo na etapa excede o previsto, a OS entra em **alerta** (atrasada naquela etapa) — mesmo que o prazo final ainda não tenha chegado. Isso pega o gargalo cedo.

**Prazos por etapa (configuráveis pelo Gestor, com defaults):**
| Etapa | Prazo interno (default, editável) | Fonte |
|---|---|---|
| Entrada criada | 4h úteis para ir a diagnóstico | fixo configurável |
| Em diagnóstico | 48h úteis (regra existente) | já no motor |
| Aguardando aprovação | 48h úteis (cliente decide) | já no motor |
| Aguardando peça | prazo por peça/fornecedor (opcional; se vazio, sem alerta) | lead time (opcional) |
| Em reparo | vem do `default_duration` do serviço (3.10) | catálogo |
| Pronto para retirada | 2 dias → lembrete; 7 dias → alerta de abandono | fixo configurável |

> Os prazos por etapa ficam num **cadastro editável** (`Tecponto Stage SLA`), com defaults. O Gestor ajusta. Se um prazo está em branco (ex.: aguardando peça sem lead time), aquela etapa simplesmente não gera alerta — **nunca trava**.

## DATA DE ENTREGA PROMETIDA

- No check-in, o sistema **sugere** a data de entrega = soma dos prazos das etapas previstas do serviço (+ lead time da peça, se houver e se informado). O atendente **ajusta** livremente (híbrido C).
- A data prometida é o prazo final visível ao cliente (no rastreio) e a referência de "atrasado" no nível da OS.
- **Nunca bloqueia:** OS pode ser aberta sem data (o atendente preenche depois).

## SUB-BLOCOS

### 3.12-1 — Cadastro de SLA por etapa + cálculo de prazo
- DocType `Tecponto Stage SLA`: etapa → prazo interno (horas/dias úteis) → editável pelo Gestor. Carga de defaults.
- Serviço de cálculo: dado o serviço/estado, calcula o prazo previsto de cada etapa e a **data de entrega sugerida**.
- Considerar **dias úteis** e horário comercial (não contar domingo/fora de expediente) — reusar a lógica de 48h úteis que já existe.
- Integração no check-in: sugere a data de entrega; atendente ajusta.
**Teste:** cálculo respeita dias úteis; data sugerida aparece no check-in e é editável; abrir OS sem data não bloqueia; Gestor edita um SLA e o cálculo muda. `git commit` + push.

### 3.12-2 — Relógios e estado de atraso (derivado)
- Serviço que, para cada OS ativa, calcula: há quanto tempo está na etapa atual, se excedeu o SLA da etapa (→ **atrasada na etapa**), e se passou da data de entrega prometida (→ **atrasada no total**).
- Tudo **derivado do estado + timestamps** (que já existem) — nada de campo manual "está atrasado". Fonte única de verdade.
- Alimenta: o contador "Atrasadas" da StatBar (3.11), a cor/flag de urgência nas listas/kanban, e a agenda (3.12-3).
**Teste:** OS parada além do SLB da etapa aparece como atrasada-na-etapa; OS além da data prometida aparece como atrasada-no-total; resolver/avançar a OS limpa o alerta sozinho; guard verde. `git commit` + push.

### 3.12-3 — Agenda processual ("Precisa de você hoje")
- Bloco de agenda (na home e/ou tela própria) que lista, **derivado do estado**, o que precisa de ação, ordenado por urgência:
  - 🔴 **Atrasado** (etapa ou entrega estourada) — age agora
  - 🟡 **Vence hoje/próximas horas** (SLA da etapa ou entrega hoje)
  - 🟢 **Programado** (entregas/prazos dos próximos dias)
- Cada item mostra: OS, cliente, o que fazer (a "próxima ação" do 3.8-3), e link.
- **+ tarefas manuais** (3.8-3) integradas na mesma lista.
- Filtrada pelo papel/contexto (Atendente vê as suas; Gestor vê a loja).
- Opcional: mini-calendário do mês marcando dias com entregas prometidas (se o dono quiser depois — não obrigatório neste bloco).
**Teste:** agenda lista os itens certos por urgência; avançar uma OS remove o item; tarefa manual aparece junto; cada papel vê só o seu; guard verde. `git commit` + push.

## PREPARA A FASE 5a (follow-ups)
O mesmo mecanismo de "relógio" (tempo desde um evento/estado) que gera os alertas internos vai gerar os **follow-ups ao cliente** na Fase 5a:
- Pronto +2d / +7d sem retirada → lembrete de retirada
- Retirada +3d → pós-venda/garantia
- Garantia -7d → aviso de vencimento
- +3-6 meses → reengajamento
Construir os relógios agora adianta a 5a — os gatilhos de tempo já existirão; só faltará plugar o canal (WhatsApp).

## CRITÉRIO DE PRONTO
- [ ] SLA por etapa editável pelo Gestor, com defaults; cálculo respeita dias úteis.
- [ ] Data de entrega sugerida no check-in, editável, nunca bloqueia.
- [ ] Estado de atraso (etapa e total) 100% derivado de timestamps — sem campo manual.
- [ ] Agenda por urgência (atrasado/hoje/programado) + tarefas manuais, por papel.
- [ ] Contador "Atrasadas" e flags de urgência nas listas alimentados pela mesma fonte.
- [ ] Nada bloqueia abertura/andamento de OS. Guard de sensíveis verde.
