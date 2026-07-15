# Bloco 3.7 — Link de rastreio público (guia otimizado para Codex)

> **Contexto:** o cliente acompanha o reparo em tempo real por um link exclusivo — menos ligações, mais transparência. Reaproveita a **mesma fundação de página pública com token** do bloco 3.6 (aceite por selfie); fazer os dois na mesma base economiza trabalho.
>
> Pré-requisito: bloco 3.6 (página pública + token) implementado. Este bloco **estende** aquela fundação.

## PRINCÍPIOS (inegociáveis)
1. **Casca pura.** Nenhuma regra de negócio nova. A página lê o estado da OS (workflow, timestamps, orçamento, garantia) que o motor já mantém e exibe. As ações (aprovar/reprovar) chamam os endpoints do motor que já existem (Fase 2.1 / 3.1d).
2. **Token não-adivinhável.** A URL NUNCA pode ser `/rastreio/OS-2026-00021` — qualquer um trocaria o número e veria a OS de outro cliente (vazamento de dado pessoal, LGPD). Use token aleatório longo, único por OS.
3. **Exposição mínima.** A página mostra só o essencial ao cliente. **NUNCA:** senha do aparelho, custo/valuation, margem, comissão, dados de outro cliente, notas internas do técnico.
4. **Read-only, exceto o aceite.** O cliente não edita nada da OS. Só pode aprovar/reprovar o orçamento (quando nessa fase) — e isso passa pelo motor, com registro de canal = "Link".
5. Mesma disciplina: sub-bloco por vez → teste → prints → commit isolado.

---

## 3.7-1 — Página de rastreio (linha do tempo)
Rota pública `/tecponto/rastreio/<token>` (guest, sem login), no visual do design system.

**O que exibe:**
- **Linha do tempo visual** com as etapas do workflow (as mesmas do Kanban): Entrada → Diagnóstico → Aguardando aprovação → Aguardando peça → Em reparo → Teste final → Pronto para retirada → Entregue. **Etapa atual destacada**; etapas concluídas com data/hora; etapas futuras esmaecidas.
- **Aparelho:** modelo + **últimos dígitos do IMEI** (nunca o IMEI completo).
- **Defeito relatado** (o que o cliente declarou no check-in).
- **Prazo:** previsão/prazo de aprovação (`approval_deadline`) quando aplicável.
- **Contato:** botão "Falar no WhatsApp" com a loja.
- Se a OS está entregue: mostra **garantia até [data]** (`warranty_expiry`).

**Token inválido/expirado** → página de erro amigável (sem vazar se a OS existe).

**Teste:** abrir o link como guest → linha do tempo correta para OS em cada estado; IMEI parcial; nenhum dado sensível no payload (guard); token adulterado → erro. `git commit`.

---

## 3.7-2 — Orçamento detalhado + aprovação pelo link
Quando a OS está em **"Aguardando aprovação"**, a página mostra o orçamento e permite decidir.

- **Orçamento detalhado:** linhas de **mão de obra** (serviços) e de **peças**, com valores, e o **total**. Transparência = mesma informação do termo que ele assina.
- Botões **Aprovar** e **Reprovar** (reprovar exige motivo — regra do motor, Fase 3.1d).
- A decisão chama o endpoint existente do motor, registrando **canal = "Link"** + timestamp (o rastro jurídico do contrato R2.2). O motor continua dono das regras: prazo de 48h úteis, trava de versão do orçamento, etc.
- **Integração com o 3.6:** se a política exigir selfie+assinatura no aceite do orçamento, a aprovação pelo link passa pelo mesmo fluxo de aceite do bloco 3.6 (o cliente confirma com selfie + assinatura). Reusar aquele componente — não duplicar.
- Após decidir, a página atualiza (mostra "Orçamento aprovado em [data]") e a ação não pode ser refeita.

**Teste:** OS aguardando aprovação → orçamento detalhado visível → aprovar pelo link → motor registra `approval_channel = Link`, `approval_date`, e a OS avança; reprovar exige motivo; tentar aprovar de novo → bloqueado; prazo expirado → não permite aprovar. `git commit`.

---

## 3.7-3 — Ciclo de vida do link
- **Geração:** o link nasce no **check-in** (criação da OS) e fica disponível ao atendente (copiar / enviar por WhatsApp / QR).
- **Validade:** ativo durante todo o reparo e por **90 dias após a retirada** (casa com a garantia — o cliente consulta a garantia quando precisar). Depois disso, expira.
- **Revogação:** o Gestor pode invalidar um link (caso de vazamento).
- Preparado para a **Fase 4/5a (notificações/WhatsApp)**: o link é o que será disparado automaticamente nas mudanças de status ("orçamento pronto", "aparelho pronto"). Deixe o link acessível por API para o módulo de notificação consumir.

**Teste:** link gerado no check-in; acessível após entrega (dentro de 90 dias) mostrando garantia; após 90 dias da retirada → expirado; Gestor revoga → link morre. `git commit`.

---

## Critério de "pronto" do 3.7
- [ ] Link com token não-adivinhável; trocar caractere não dá acesso a outra OS.
- [ ] Linha do tempo reflete o workflow real, com etapa atual destacada.
- [ ] Orçamento detalhado (mão de obra + peças) visível ao cliente.
- [ ] Aprovar/reprovar pelo link funciona e registra canal = "Link" no motor.
- [ ] Guard: nenhum dado sensível (senha, custo, margem, comissão, IMEI completo) no payload público.
- [ ] Link vivo por 90 dias após a retirada, mostrando a garantia; expira depois.
- [ ] Gestor consegue revogar.
- [ ] Link exposto por API para a Fase 4/5a disparar por WhatsApp.

## Nota
O rastreio só entrega o valor prometido ("menos ligações") quando o link **chega sozinho** ao cliente — isso depende da **Fase 4 (notificações) + 5a (WhatsApp)**. Até lá, o atendente envia o link manualmente pelo WhatsApp.
