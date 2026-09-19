# Phase 4: Design System (Single Pass) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-19
**Phase:** 4-design-system-single-pass
**Areas discussed:** Escopo da passada única, etapa "Dados" do check-in, consistência OS-vs-PDV, formato da documentação

---

## Escopo da passada única (DESIGN-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Documentar + polir o que já existe | Documento formal em cima de `tokens.css`/`src/ui/`, corrigir os 2 desvios achados, passada leve de consistência visual | ✓ |
| Reformular mais a fundo | Revisão mais profunda de espaçamento, hierarquia, sombra/elevação, variantes de componente | |

**User's choice:** Documentar + polir o que já existe.
**Notes:** Scouting achou que o sistema de tokens já é quase 100% consistente (2.875 usos de classes `tec-*` vs. só 2 usos de cor Tailwind crua em ~11 mil linhas) — não é greenfield.

---

## Etapa "Dados" do check-in (item carregado da Fase 1)

| Option | Description | Selected |
|--------|-------------|----------|
| Reorganizar dentro da mesma etapa | Manter 5 etapas, agrupar campos com disclosure progressivo | |
| Quebrar em mais sub-etapas (microtelas) | Aumentar o número de passos do assistente | ✓ |

**User's choice:** Quebrar em mais sub-etapas.

**Follow-up — divisão concreta:**

| Option | Description | Selected |
|--------|-------------|----------|
| 3 sub-etapas: Defeito / Estado físico / Acessórios | Assistente vai de 5 pra 7 passos (Cliente, Aparelho, Defeito, Estado físico, Acessórios, Fotos, Revisão) | ✓ |
| Outra divisão | — | |

**User's choice:** 3 sub-etapas conforme descrito.

---

## Consistência OS vs PDV

| Option | Description | Selected |
|--------|-------------|----------|
| Sim, só visual | Alinhar aparência (cores/espaçamento/componentes) sem mudar fluxo/lógica | ✓ |
| Sim, visual e estrutural | Também permitir consolidar componentes entre OS e PDV | |
| Não, fora do escopo | Deixar pra depois | |

**User's choice:** Sim, só visual.

---

## Formato da documentação (DESIGN-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown no repositório | Arquivo tipo DESIGN_SYSTEM.md documentando tokens.css e src/ui/ | ✓ |
| Página de estilo viva dentro do app | Tela de referência renderizando os componentes de verdade | |

**User's choice:** Markdown no repositório.

---

## Claude's Discretion

- Caminho/nome exato do arquivo de documentação.
- Estrutura exata do documento além das duas seções obrigatórias (tokens, componentes).
- Se `verify-foundation.mjs` ganha um guard novo contra cor Tailwind crua.
- Ajustes exatos de espaçamento/tipografia na passada de consistência leve.

## Deferred Ideas

- Split de `App.tsx`/`api.py` (TECH-03, v2, não relacionado a design).
- Nova escala de espaçamento, sistema de sombra/elevação, ou redesign de variantes de componente.
- Qualquer divergência OS-vs-PDV que seja funcional (não visual) — fica registrada para fase futura.
- Consolidação estrutural de componentes entre OS e PDV — opção rejeitada pelo usuário.
