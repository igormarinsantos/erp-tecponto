---
status: blocked
phase: 01-os-6-closure-warranty-verification-deadline-wiring
source: [01-VERIFICATION.md]
started: 2026-09-03T00:00:00Z
updated: 2026-09-14T00:00:00Z
---

## Current Test

number: -
name: n/a — blocked at the environment level, not at the test level
expected: n/a
awaiting: local environment stability (out of scope of this project's code)

## Tests

### 1. Técnico deadline pre-fill / override / persist round-trip
expected: Como Técnico, abrir uma OS em "Diagnosticado — aguardando orçamento" com precificação técnica. O input de prazo chega desabilitado com "Calculando sugestão…", depois pré-preenche com uma data futura. Sobrescrever a data, clicar "Salvar prazo", recarregar a página, e confirmar que o valor salvo persistiu e não foi sobrescrito pela sugestão. O botão "Salvar prazo" deve ficar desabilitado enquanto o campo estiver vazio.
result: [blocked]

### 2. Public tracking portal + print format visual confirmation
expected: Abrir o link de rastreio público de uma OS com prazo salvo — o bloco "Previsão" deve mostrar a data. Imprimir o orçamento, o orçamento discriminado e o laudo técnico — "Prazo estimado" deve aparecer nos três.
result: [blocked]

### 3. Kanban card + OS detail overview visual confirmation
expected: Abrir o Kanban e confirmar que todo card mostra "Prazo estimado" (data real ou "Não definido"), tom neutro (muted), sem quebra de layout. Expandir "Ver mais" numa OS e confirmar que a linha de detalhe mostra a mesma data.
result: [blocked]

## Summary

total: 3
passed: 0
issues: 0
pending: 0
skipped: 0
blocked: 3

## Gaps

**Não é uma lacuna de comportamento — é um bloqueio de ambiente.** Em 2026-09-14, duas tentativas de rodar esses 3 testes visuais (uma no painel de navegador do Claude, uma na aba própria do usuário) falharam pela mesma causa: o container `tecponto-local-server` cai sozinho (`OOMKilled=false`, `ExitCode=255`, sem erro de aplicação nos logs — a última requisição antes da queda tinha respondido `200` normalmente) segundos depois de servir a página. Isso bate com o padrão de instabilidade do Docker Desktop no Windows/WSL2 já documentado em `AUDITORIA_SISTEMA.md` desde a sessão de auditoria original — suspensão de container por gerenciamento de energia do host, não um bug de código.

Como a queda acontece independente de quem está conectado (painel do Claude ou aba do próprio usuário), manter uma sessão de navegador viva não é uma estratégia confiável nesta máquina.

**Decisão (usuário + Claude, 2026-09-14):** aceitar a prova automatizada já existente (9/9 critérios de `01-VERIFICATION.md`, todos re-executados ao vivo contra o servidor local no momento da verificação) como suficiente pra seguir em frente, e deixar esses 3 itens formalmente como `blocked` — não `passed`, não escondido — até que uma janela de estabilidade do Docker permita confirmação visual real. Trabalho avança para a Fase 3, cujos testes rodam via `bench execute` (comandos curtos, muito mais resistentes a essa instabilidade do que uma sessão de navegador de longa duração).

**Retomar quando:** o ambiente Docker local ficar estável por tempo suficiente (alguns minutos seguidos sem queda) — aí sim rodar os 3 testes acima manualmente antes de marcar a Fase 1 como formalmente completa no roadmap.
