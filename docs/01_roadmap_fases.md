# 01 — Roadmap de Fases (plano de construção)

> A ordem de construção do sistema, do zero até a implementação final. Cada fase é **auto-contida, testável e commitável** antes da próxima — construir de baixo pra cima evita retrabalho.
>
> Pré-requisitos de leitura: `00 — Contexto` e o contrato `Regras de Negócio Travadas`. O contrato é a **fonte da verdade** de campos e regras; este roadmap diz **o que fazer e em que ordem**; os guias de fase dão o **passo a passo**.

---

## Princípio

```
FUNDAÇÃO → MODELO DE DADOS → LÓGICA POR PILAR → SUPERFÍCIES (MVP)
   → NOTIFICAÇÃO → INTEGRAÇÕES → CRESCIMENTO
```

Regra de cada fase: **só começa quando a anterior está "pronta" (critério testável)** e termina com `bench migrate` + `bench export-fixtures` (se mexeu em config) + `git commit` limpos.

---

## Fase 0 — Fundação de infraestrutura
**Objetivo:** ambiente reproduzível + ERPNext rodando + app criado.
**Por que primeiro:** sem ambiente, nada existe.
**Construir:** Ubuntu 24.04 → bench → Frappe v16 → ERPNext v16 → Frappe HR (`hrms`) → site → `tecponto_app` instalado → `developer_mode=1` → Git. Config base: empresa, contas, os **dois depósitos** (Reparo, Comercial) + Usados/Sucata, grupos de item, formas de pagamento, item de mão de obra.
**Pronto quando:** abre no navegador, loga como Administrator, cria Customer/Sales Invoice de teste, `git log` mostra o scaffold.
**Guia:** `Fase 0 — Fundação`.

## Fase 1 — Modelo de dados (todos os DocTypes)
**Objetivo:** todas as entidades e relações existem — **sem lógica ainda**.
**Por que agora:** a lógica (Fase 2) precisa da estrutura 100% fechada.
**Construir (fonte: seção "Deltas para a Fase 1" do contrato):**
- Custom Fields em `Customer` (WhatsApp, CPF/CNPJ, IE, IM, RG) e `Item` (NCM/CFOP/origem/CEST, LC116/NBS/CNAE, gaveta, tipo, compatibilidade). Custo/valuation em **perm level 1**.
- DocTypes novos: `Customer Device` · `Service Order` (+ child tables `Service Order Part`, `Service Order Service`) · `Device Trade Evaluation` (+ checklist por tipo) · `Trade-In Operation` · `Tecponto Settings` (Single, completo).
- Roles: `Tecponto Atendente`, `Tecponto Tecnico`, `Tecponto Gestor`.
**Pronto quando:** cria a cadeia Cliente→Aparelho→OS por tela com links certos; `bench migrate` sem erro; fixtures exportadas.
**Guia:** `Fase 1 — Modelo de dados` (usar a lista de campos do contrato como fonte da verdade).

## Fase 2 — Lógica de negócio (subdividida por pilar)

### 2.0 — Fundação de negócio
**Objetivo:** a base transversal que os três pilares usam.
**Construir:** matriz de visibilidade (perm levels — contrato F6); os **dois estoques operacionais** (consumo automático OS→Reparo, POS→Comercial; transferência exige Gestor — F2); `Tecponto Settings` preenchido; **contas de recebíveis de cartão** + taxas por tipo de pagamento (F4); travas de preço (piso de custo + desconto — F5).
**Pronto quando:** cada papel vê só o que pode; cartão posta em recebíveis; piso de custo bloqueia venda abaixo do custo sem Gestor.

### 2.1 — Pilar REPARE (o mais complexo)
**Objetivo:** a Ordem de Serviço funciona de ponta a ponta.
**Construir (contrato Parte IV):** Workflow da OS + os **3 aceites** (R2); prazo de 48h úteis (R5); **peça com reserva na aprovação → baixa no uso → 3 classes de perda** + reversão (R6); **fechamento: 1 Sales Invoice idempotente, sem re-baixar** (R7); garantia 90d + cortesia (R8); sinal (R9); taxa de diagnóstico (R4); **comissão 20% por linha de serviço** → Frappe HR (R10); estadia (R11); cancelamento faturado só Gestor (R12).
**Vigia (auditoria):** liberação de reserva ao reprovar tem que ser confiável.
**Pronto quando:** ciclo entrada→diagnóstico→aprovação→reparo→pronto→entregue roda; estoque baixa 1x; nota fecha idempotente; comissão cai no HR.

### 2.2 — Pilar TROQUE
**Objetivo:** trade-in e compra de usado funcionam.
**Construir (contrato Parte III):** avaliação com **checklist por tipo** (iPhone/Android) + tabela com faixa mín–máx; **acima do máximo exige Gestor**; bloqueio iCloud/Google barrado; **`Trade-In Operation` atômica** (2 pernas, sem melhor-por-pior, diferença ≥ 0); **destinação** (venda/peças/descarte); **canibalização via Stock Entry "Repack"** com custo rateado e destino por peça.
**Vigia (auditoria):** atomicidade = transação de banco com rollback.
**Pronto quando:** troca fecha as duas pernas juntas; usado vira estoque; desmanche distribui custo e alimenta os estoques certos.

### 2.3 — Pilar COMPRE (o mais simples)
**Objetivo:** varejo e compras funcionam.
**Construir (contrato Parte II):** venda no POS (baixa do Comercial); **sem comissão de venda**; troca/devolução de acessório → nota de crédito; usado vendido com Serial/IMEI + garantia 90d só de fábrica; **compras** (à vista + opção a prazo, aprovação por teto).
**Pronto quando:** vende acessório no PDV, faz devolução, e dá entrada de compra.

## Fase 3 — Superfícies de balcão = MVP operacional
**Objetivo:** a loja consegue operar de verdade.
**Construir:** Print Formats (termo de entrada, termo de retirada, OS, **etiqueta + QR Code**); **assinatura** (entrada e retirada) + termo LGPD; **Dashboard** (todas as visões: faturamento bruto, recebido líquido, OS por status, estoque crítico por estoque…) + relatórios; Workspace/menu.
**Pronto quando:** atendente abre OS, técnico executa, cliente paga/assina/retira sem sair do sistema.

## Fase 4 — Espinha de notificação (sem provedor real)
**Objetivo:** os gatilhos de comunicação existem antes de plugar API.
**Construir:** módulo `notify.send(to, template_key, context)` agnóstico; gatilhos nos estados via `doc_events` → `frappe.enqueue`; backend inicial "log" (grava, não envia); scheduler diário (OS atrasada, abandono, lembrete).
**Pronto quando:** mudar estado da OS gera log da mensagem que seria enviada, sem travar a operação.

## Fase 5 — Integrações (na ordem de prioridade)

### 5a — WhatsApp
Backend oficial (`frappe_whatsapp`/Meta Cloud API) **e** Evolution, escolhível por config em Settings. Templates por `template_key`.

### 5b — Fiscal
Módulo `fiscal` → middleware (PlugNotas/Focus/NFe.io). **Duas notas** (NFC-e produto + NFS-e serviço), Simples/CSOSN, Padrão Nacional NFS-e Guarulhos, Certificado A1.
**Vigia (auditoria):** job diário reprocessa notas pendentes/contingência.

### 5c — Maquininha
Cobrança iniciada pelo ERP → confirmação por webhook → Payment Entry. Sincroniza taxas/liquidação com o gateway.

## Fase 6 — Crescimento
Marketplace (estoque único + reserva por canal + preço por canal); relatórios avançados; e filiais **como instância replicada** deste mesmo sistema (não multi-loja compartilhada).

---

## Mapa de dependências

```
0 ─► 1 ─► 2.0 ─► 2.1 REPARE ─► 3 (MVP) ─► 4 ─► 5a ─► 5b ─► 5c ─► 6
              └─► 2.2 TROQUE ─┘
              └─► 2.3 COMPRE ─┘
```
2.1 / 2.2 / 2.3 dependem todas de 2.0; podem ser construídas em sequência (recomendado REPARE → TROQUE → COMPRE, complexidade decrescente). A Fase 3 (MVP) precisa dos três pilares com o mínimo funcionando.

## Marcos

- **Fim da Fase 1:** esqueleto de dados completo.
- **Fim da Fase 2.1:** o conserto já funciona internamente.
- **Fim da Fase 3:** MVP — a loja opera.
- **Fim da Fase 5b:** operação fiscal legal.
- **Fim da Fase 6:** pronto pra escalar/filial.
