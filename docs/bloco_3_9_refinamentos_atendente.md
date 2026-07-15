# Bloco 3.9 — Refinamentos de operação do Atendente (guia otimizado para Codex)

> **Contexto:** quatro melhorias de uso diário que saíram da observação do dono operando o sistema. Pré-requisito: Central de Ação (3.8) completa.
>
> Todos entram no **molde** — quando os papéis Técnico/Gestor/Diretor forem construídos, herdam esses padrões.

## INSTRUÇÕES
- Um item por vez → teste → prints em artifacts → OK do dono → **commit imediato**. Zero acúmulo.
- Regra permanente: **regra de negócio no motor, front é casca**. Nenhuma validação de permissão decidida em JS.
- Guard de sensíveis verde em tudo.

---

## 3.9-1 — Modo Caixa (PDV dedicado)

**Problema:** hoje o PDV é uma tela dentro do sistema; o atendente precisa navegar até ela. No balcão real, um computador fica **só pra vender** — a tela tem que estar sempre lá, pronta pra bipar.

**Construir:**
- **URL própria** (`/tecponto/caixa`) que abre **somente o PDV** — sem sidebar, sem painel, sem distração. Feita para rodar em **tela cheia** o dia todo.
- Após finalizar uma venda: volta ao **estado limpo** com **foco automático no campo de bipe**. Sem cliques, pronta para a próxima.
- Botão discreto para **sair do modo caixa** e voltar ao sistema completo.

**Identificação do operador (crachá bipável):**
- O funcionário **bipa um crachá com código de barras** e as vendas passam a registrar **quem vendeu**.
- Reusar o **mesmo leitor USB** do PDV e o **mesmo gerador de etiquetas** do PDV-3 para imprimir os crachás.
- **Fallback:** PIN de 4 dígitos digitado, caso o crachá falhe/suma.
- Trocar de operador = bipar outro crachá.

**⚠️ SEGURANÇA (inegociável):**
- O crachá **identifica** o operador **apenas dentro do modo caixa** (que só vende). Ele **não é senha forte** — quem vê o código pode copiá-lo.
- Qualquer ação sensível (relatórios, aprovações, configuração, custo) continua exigindo **login completo**. O crachá **não pode dar acesso a nada além de vender**.
- A venda continua sendo criada pelo **endpoint cirúrgico** (`pos_create_sale`) — sem `Sales User`, preços/estoque/piso resolvidos no servidor.

**Testes:** (a) `/tecponto/caixa` abre só o PDV, sem sidebar; (b) finalizar venda → tela limpa com foco no bipe; (c) bipar crachá identifica o operador e a venda registra quem vendeu; (d) PIN funciona como fallback; (e) operador identificado por crachá **não** consegue acessar relatório/aprovação/custo; (f) guard verde.

---

## 3.9-2 — Mudar etapa da OS: fácil e em todo lugar

**Problema:** mudar etapa é a ação mais frequente do dia, mas hoje só dá pra arrastar no Kanban (ruim em tela pequena) ou abrir a OS. Na lista não tem nada.

**Construir — controle rápido de etapa em três lugares:**
1. **Detalhe da OS** — botão/dropdown proeminente "Mover para…"
2. **Card do Kanban** — menu no card (o arrastar continua funcionando)
3. **Linha da lista de OS** — ação rápida, sem abrir a OS

**Comportamento unificado (o ponto principal):**
- O controle mostra as etapas para as quais a OS **pode** ir (só as transições que o **workflow do motor** permite — não inventar transição no front).
- Ao escolher:
  - Usuário **tem permissão** → **move na hora**.
  - Usuário **não tem** → abre o **modal de solicitação** (do 3.8-1b), com motivo obrigatório, e avisa que foi enviado ao aprovador.
- O usuário **não precisa saber de antemão** se pode ou não. Ele clica; o sistema **faz ou pede**. Nada de esconder a opção nem de mostrar erro seco.

**Testes:** (a) os três lugares oferecem o controle; (b) com permissão → move; (c) sem permissão → vira solicitação (e o gestor a vê); (d) transições oferecidas batem com o workflow.

---

## 3.9-3 — Cadastro de cliente na tela de Clientes

**Problema:** a tela de Clientes só lista. Cadastrar exige entrar no wizard de OS.

**Construir:**
- Botão **"Cadastrar cliente"** na própria tela de Clientes.
- **Obrigatórios, validados no MOTOR** (não só no form): **nome** · **CPF** (com opção explícita "não possui" → cai para **RG**) · **WhatsApp/telefone**. E-mail **opcional**.
- Formulário enxuto, rápido de preencher no balcão.

**Testes:** cadastrar cliente pela tela; motor rejeita sem CPF **e** sem RG; "não possui CPF" habilita RG; cliente aparece na lista e fica disponível no wizard de OS.

---

## 3.9-4 — Busca compacta

**Problema:** a busca abre um **modal gigante** que ocupa a tela. É a ação mais repetida do balcão — tem que ser leve.

**Construir:**
- Resultados num **dropdown compacto logo abaixo do campo** (não modal).
- **Navegação por teclado:** ↑/↓ percorre, **Enter** seleciona, **Esc** fecha. Resultados aparecem conforme digita (**debounce**).
- Vale para a **busca de cliente** e para a **busca global (Ctrl+K)**.

**Testes:** buscar cliente → dropdown abaixo do campo; teclado funciona; Ctrl+K com o mesmo comportamento; nenhum dado sensível no payload.

---

## Critério de "pronto" do 3.9
- [ ] Modo caixa abre só o PDV, fica pronto pra bipar, identifica operador por crachá (com PIN de fallback) e **não** dá acesso a nada sensível.
- [ ] Mudar etapa disponível nos três lugares, com o comportamento "faz ou pede".
- [ ] Cadastro de cliente na tela, com obrigatoriedade no motor.
- [ ] Busca compacta em dropdown, com teclado.
- [ ] Guard verde em tudo; commits isolados.

## Itens de go-live que este bloco cria
- **Imprimir os crachás** dos funcionários (usar o gerador de etiquetas de barcode do PDV-3).
- **Definir os PINs** de cada funcionário (fallback do crachá).
- Computador dedicado ao **modo caixa** no balcão (tela cheia).
