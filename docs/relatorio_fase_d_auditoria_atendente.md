# Relatório Final — Fase D: Auditoria do Atendente

**Data:** 20 de julho de 2026  
**Escopo:** front Tecponto, APIs do módulo, telas públicas de rastreio/aceite e os fluxos de balcão.  
**Status:** aprovado tecnicamente; os cinco bloqueadores identificados foram corrigidos e publicados.

## Bloqueadores Corrigidos

| # | Achado | Risco | Correção | Commit |
|---|---|---|---|---|
| 1 | A página pública de aceite devolvia o IMEI completo. | P1: identificação de aparelho exposta por link público. | A projeção pública passou a devolver apenas os quatro últimos dígitos; o teste rejeita chaves e valores de IMEI completos. | `53ef428` |
| 2 | A mensagem de piso de custo podia interpolar o valuation no erro. | P1: custo poderia vazar por texto, mesmo sem campo de custo no payload. | A mensagem ficou neutra; o guard agora compara também valores sentinela em números e strings. | `7f4cc75` |
| 3 | Contadores e agregados do Técnico usavam consultas globais. | P1: Kanban, StatBar e dashboard podiam revelar volume de OS, vendas, trocas ou estoque Comercial fora da atribuição. | Escopo explícito por `technician` em agregados; vendas/trocas/comercial retornam 403 para Técnico exclusivo; multipapel continua aditivo. | `f29aa89` |
| 4 | Consulta de garantia de usado respondia sem gate específico. | P1: conhecer Serial/IMEI poderia revelar cliente, nota e validade. | Consulta limitada a Atendente/Gestor/System Manager, com `check_permission("read")`; Técnico e Guest recebem 403. | `9b5d178` |
| 5 | Busca de clientes/aparelhos e detalhe de OS técnica podiam expor carteira e dados fiscais fora da atribuição. | P2/LGPD: CPF, RG, e-mail e aparelhos de outros clientes acessíveis por APIs auxiliares. | Técnico exclusivo consulta somente clientes/aparelhos de suas OS; CPF/RG/e-mail são omitidos também no detalhe da OS. | `bc0a6fc` |

## Resultado Consolidado da Auditoria

### Gate de papel

- Todo endpoint operacional auditado exige login e papel Tecponto no servidor.
- Regras específicas existem para balcão, PDV, catálogo, garantia e ações gerenciais.
- O recorte de Técnico exclusivo é explícito nos pontos que usam `get_all` ou `db.count`, pois essas APIs do Frappe não aplicam automaticamente o filtro de permissão de lista.
- Conta multipapel continua com a união das roles reais. A visão unificada é só apresentação; não cria nem remove autorização.

### Guard por valor e por payload

- O guard de campos bloqueia custo, margem e comissão por nome de chave.
- O guard de custo também procura o valor sentinela de valuation em números e textos, impedindo custo disfarçado de preço ou mensagem de erro.
- StatBars, agenda, home, busca de orçamento, PDV e páginas públicas foram cobertos pela suíte; resultado final: `leaked_fields: []`.

### Travas de negócio

- Piso de custo, desconto acima do limite, troca acima da tabela, transferência entre estoques, mudança de etapa fora do papel e cancelamento de OS faturada oferecem solicitação de aprovação.
- A aprovação não é bypass: a ação é reexecutada pelo motor sob o aprovador e passa novamente por todas as validações.
- Solicitação não pode ser autoaprovada e expira em 72 horas.
- Aceite obrigatório, garantia, reserva/baixa de peças, faturamento idempotente e comissão por serviço continuam cobertos pela suíte de fundação.

### Páginas públicas e endpoints Guest

- Rastreio e aceite usam tokens longos, hasheados, expirados e de uso único quando aplicável.
- Páginas públicas não expõem custo, margem, senha do aparelho ou IMEI completo; token adulterado recebe erro neutro.
- Selfie aceita somente captura JPEG de câmera e é anexo privado da OS. Assinatura também é privada.
- A elevação necessária para anexar selfie/assinatura de Guest é limitada ao token validado, à OS vinculada e ao arquivo privado; a sessão Guest é restaurada em seguida.
- Não há caminho público de upload de arquivo de imagem para o aceite.

## Evidências Finais

Executado no site `tecponto.localhost` após o commit `bc0a6fc`:

```text
bench --site tecponto.localhost execute \
  tecponto_app.tecponto.frontend.test_frontend_api.run_foundation_checks
```

Resultado: `status: ok`, incluindo guard de sensíveis, guard por valor de custo, escopo técnico, multipapel, PDV, Central de Ação, agenda, aceite e rastreio.

```text
npm run build
```

Resultado: `tsc --noEmit` verde, build Vite verde e verificação de fundação do front verde.

## Itens Não Bloqueantes Registrados

1. **Bundle do front:** `app.js` minificado tem aproximadamente 523 kB. É aviso de performance do Vite, não falha. Quando as telas de Técnico/Gestor/Diretor crescerem, dividir rotas por import dinâmico é recomendado.
2. **Massa de testes:** a suíte cria OS, solicitações, notificações, links de rastreio e registros de garantia para provar fluxos. O procedimento versionado em `docs/procedimento_limpeza_massa_teste.md` cobre também `Service Order Tracking` órfão e registros `File` sem arquivo físico, com auditoria prévia das evidências privadas de aceite.
3. **Valor de troca dentro da faixa:** o fluxo atual permite registrar valor dentro da tabela e exige Gestor apenas acima do máximo, conforme T2/F6 do contrato. Futuramente, pode-se separar semanticamente `valor sugerido` e `valor aprovado` na interface, sem alterar essa regra.

## Conclusão

O Atendente está apto a ser congelado como molde de segurança e operação. A próxima frente de produto é a superfície completa do Técnico, herdando o mesmo princípio: interface mostra somente o que a role permite e o motor continua a autoridade final.
