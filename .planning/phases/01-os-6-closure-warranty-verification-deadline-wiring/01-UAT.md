---
status: testing
phase: 01-os-6-closure-warranty-verification-deadline-wiring
source: [01-VERIFICATION.md]
started: 2026-09-03T00:00:00Z
updated: 2026-09-03T00:00:00Z
---

## Current Test

number: 1
name: Técnico deadline pre-fill / override / persist round-trip
expected: |
  Loading → pre-fill → override → save → reload → persisted value shown; "Salvar prazo" stays disabled while the field is empty.
awaiting: user response

## Tests

### 1. Técnico deadline pre-fill / override / persist round-trip
expected: Como Técnico, abrir uma OS em "Diagnosticado — aguardando orçamento" com precificação técnica. O input de prazo chega desabilitado com "Calculando sugestão…", depois pré-preenche com uma data futura. Sobrescrever a data, clicar "Salvar prazo", recarregar a página, e confirmar que o valor salvo persistiu e não foi sobrescrito pela sugestão. O botão "Salvar prazo" deve ficar desabilitado enquanto o campo estiver vazio.
result: [pending]

### 2. Public tracking portal + print format visual confirmation
expected: Abrir o link de rastreio público de uma OS com prazo salvo — o bloco "Previsão" deve mostrar a data. Imprimir o orçamento, o orçamento discriminado e o laudo técnico — "Prazo estimado" deve aparecer nos três.
result: [pending]

### 3. Kanban card + OS detail overview visual confirmation
expected: Abrir o Kanban e confirmar que todo card mostra "Prazo estimado" (data real ou "Não definido"), tom neutro (muted), sem quebra de layout. Expandir "Ver mais" numa OS e confirmar que a linha de detalhe mostra a mesma data.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
