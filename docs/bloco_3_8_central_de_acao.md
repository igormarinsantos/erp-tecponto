# Bloco 3.8 — Central de Ação (solicitações + notificações + pendências)

> **Contexto:** transforma o sistema de "painel que mostra números" em **operação viva que diz o que fazer**. É a **Fase 4 (espinha de notificação) antecipada e ampliada**. Pré-requisito: multipapel e sidebar por pilar concluídos.
>
> Três partes que se amarram: uma **solicitação** vira uma **notificação** para o aprovador e uma **pendência** na lista dele.

## PRINCÍPIOS
1. **Permissão não muda.** A solicitação NÃO é bypass. Quem aprova continua sendo só quem já podia. O que muda: em vez de o sistema dizer "não pode", ele diz "vou pedir para quem pode". **Melhora a auditoria** (hoje o gestor libera na boca; agora fica rastro).
2. **Fonte única de verdade.** As pendências são **derivadas do estado real** do sistema (não uma lista paralela que precisa sincronizar). A OS mudou de estado → a pendência some sozinha. Tarefas manuais são um complemento, não a base.
3. **Motor agnóstico de canal.** A notificação é disparada por evento e entregue por um **backend plugável**: hoje "in-app" (o sininho), depois WhatsApp (Fase 5a) — **sem mexer nos gatilhos**.
4. **Assíncrono.** Notificação nunca trava a operação: `doc_event` → `frappe.enqueue`. Se o canal externo cair, a loja não para.
5. Mesma disciplina: sub-bloco por vez → teste → prints → **commit imediato**. Zero acúmulo.

---

## 3.8-1 — Solicitações com aprovação

**DocType `Tecponto Request`:** tipo · documento de referência (OS, venda, avaliação…) · solicitante · motivo (obrigatório) · papel aprovador · status (Pendente/Aprovada/Reprovada/Expirada) · aprovador · data da decisão · **expira em 72h**.

**Travas que viram solicitação** (hoje só barram; passam a poder ser solicitadas):
| Trava | Quem pode aprovar |
|---|---|
| Mover OS para etapa fora do seu papel | quem tem o papel da transição |
| Desconto acima do limite | Gestor |
| Venda/serviço abaixo do custo (piso) | Gestor |
| Valor de troca acima do máximo da tabela | Gestor |
| Transferência entre estoques (Reparo ↔ Comercial) | Gestor |
| Cancelamento de OS faturada | Gestor |

**Comportamento:** quando o usuário esbarra numa trava, o erro deixa de ser só "não pode" e oferece **"Solicitar aprovação"** (com motivo obrigatório). Ao aprovar, o motor **executa a ação original** com a permissão do aprovador — não com a do solicitante.

**⚠️ Segurança:** a execução pós-aprovação roda server-side, validando de novo TODAS as regras. Uma solicitação aprovada não pula validação — ela apenas fornece a autorização que faltava.

**Expiração:** scheduler diário marca como **Expirada** o que passou de 72h sem decisão. Expirada não executa nada.

**Testes:** (a) Atendente tenta desconto acima do limite → oferece solicitar → cria `Tecponto Request` pendente; (b) Gestor aprova → ação executa; (c) Gestor reprova → não executa; (d) 72h sem decisão → expira e não executa; (e) solicitante NÃO consegue aprovar a própria solicitação. `git commit`.

---

## 3.8-2 — Motor de notificação (o sininho de verdade)

Hoje o sininho tem contagem decorativa. Passa a ser real.

**DocType `Tecponto Notification`:** destinatário · tipo · título · corpo · link (para onde leva) · lida/não lida · criada em.

**Módulo `notify.send(user, template_key, context)`** — agnóstico de canal. Backend inicial: **in-app**. A Fase 5a pluga WhatsApp no MESMO ponto, sem tocar nos gatilhos.

**Gatilhos (via `doc_events` → `frappe.enqueue`):**
- Solicitação criada → notifica quem pode aprovar
- Solicitação aprovada/reprovada → notifica o solicitante
- OS muda de estado → notifica o responsável (técnico atribuído / atendente da OS)
- Orçamento prestes a expirar (12h antes) → notifica o atendente
- OS pronta há X dias sem retirada → notifica o atendente
- Peça solicitada chegou → notifica o técnico

**UI:** sininho com contagem real de não lidas; dropdown com a lista; clicar leva ao documento; marcar como lida; "marcar todas".

**Teste:** criar solicitação → aprovador recebe notificação real; mudar estado da OS → responsável é notificado; contagem do sininho bate com o banco; clicar leva ao lugar certo; nada trava a operação (assíncrono). `git commit`.

---

## 3.8-3 — Pendências do dia (derivadas + manuais)

**Derivadas (a base — fonte única de verdade):** um serviço server-side calcula, **a partir do estado real**, o que precisa de ação, filtrado pelo papel/contexto do usuário. Cada item já traz a **próxima ação** e o link.

Exemplos por papel:
- **Atendente:** orçamentos aguardando envio ao cliente · OS aguardando aprovação (cliente não respondeu) · OS prontas há X dias sem retirada · solicitações minhas reprovadas · avaliações de troca aguardando fechamento
- **Técnico:** OS atribuídas aguardando diagnóstico · peças que chegaram (pode retomar) · OS em reparo há mais de X dias · retrabalho/garantia na fila
- **Gestor:** **solicitações aguardando sua aprovação** · OS atrasadas · estoque crítico · compras acima do teto

> A coluna "Próxima ação" já existente na tabela de OS é **a mesma lógica**: o estado gera a ação. A lista de pendências é a soma dessas ações, filtrada por papel. **Uma verdade só.**

**Manuais (complemento):** o usuário cria a própria tarefa (título, prazo, opcionalmente ligada a uma OS/cliente). Marca como feita. Não substitui as derivadas — convive.

**UI:** bloco "Precisa de você hoje" no painel, com as derivadas primeiro (ordenadas por urgência) e as manuais depois. Contagem no topo.

**Teste:** OS em estado que exige ação → aparece na lista do papel certo; resolver a OS → **a pendência some sozinha** (sem marcar nada); tarefa manual criada e concluída; cada papel vê só as suas. `git commit`.

---

## Critério de "pronto" do 3.8
- [ ] Travas oferecem "solicitar aprovação" em vez de só barrar; solicitação com motivo obrigatório.
- [ ] Aprovação executa a ação server-side revalidando tudo; reprovação e expiração (72h) não executam.
- [ ] Solicitante não aprova a própria solicitação.
- [ ] Sininho real: contagem, lista, marcar lida, link para o documento.
- [ ] Notificação assíncrona (não trava operação) e agnóstica de canal (WhatsApp pluga na 5a sem mexer em gatilho).
- [ ] Pendências derivadas do estado (somem sozinhas quando resolvidas) + tarefas manuais.
- [ ] Cada papel vê só as suas pendências/solicitações.
- [ ] Guard de sensíveis verde em tudo.

## Preparado para o futuro
- **Fase 5a (WhatsApp):** trocar/adicionar o backend de `notify.send` — os gatilhos já existem.
- **Bloco 3.7 (rastreio):** as notificações ao **cliente** usarão o mesmo motor, mandando o link de rastreio.
