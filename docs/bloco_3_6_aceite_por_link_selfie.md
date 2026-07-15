# Bloco 3.6 — Aceite por link (selfie + assinatura) — guia otimizado para Codex

> **Contexto:** substitui a assinatura presencial no canvas (blocos 3.1c/3.1d) por um **fluxo público por link**: o atendente preenche tudo; o cliente só **confirma** com selfie ao vivo + assinatura, sem editar a OS. Pré-requisito: Fase 3.1f (design system) concluída.
>
> Natureza: integração sensível (página pública, token, câmera, dado biométrico/LGPD). Trate com o mesmo rigor de segurança das integrações da Fase 5.

## PRINCÍPIOS (inegociáveis)
1. **Atendente preenche, cliente só confirma.** No link, todos os dados da OS são **read-only**. O cliente só escreve nos campos de aceite (selfie, assinatura, consentimento). Nunca dar ao token público permissão de escrita nos dados da OS.
2. **Selfie ao vivo, só câmera.** `getUserMedia` para captura ao vivo; **sem `<input type=file>`** (impede foto antiga/de terceiro). A selfie prova presença no momento.
3. **Segurança do token:** único por aceite, **expirável**, uso único (ou limitado), invalidado após o aceite. Vazou o link → não dá pra reusar.
4. **A regra do motor não muda:** a OS continua **não avançando** sem o aceite (as validações das Fases 2.1/3.1 permanecem). Muda só COMO o aceite é coletado — de canvas presencial para link+selfie.
5. **Mesma disciplina:** sub-bloco por vez → teste → commit. Windows/PowerShell sem `&&`.

## STACK
- Página pública servida pelo Frappe (rota `/tecponto/aceite/<token>`), **fora do login** (guest), isolada do app autenticado.
- `getUserMedia` para câmera; canvas para assinatura; upload do resultado via endpoint whitelisted que valida o token (não a sessão).
- Selfie + assinatura salvas como anexos da OS + metadados (IP, user-agent, timestamp, geolocalização se permitida).

---

## 3.6-1 — Emissão do token e página pública read-only
- Endpoint (atendente, autenticado) gera um **Aceite** (novo DocType `OS Acceptance`: os, tipo [entrada/retirada], token, status, expiry, signer_role [dono/terceiro]).
- Página `/tecponto/aceite/<token>`: valida token (existe, não expirado, não usado) → exibe **read-only** o resumo do que o cliente confirma (dados da OS pertinentes ao tipo de aceite) + o termo LGPD. Token inválido/expirado → tela de erro amigável.
- **QR na tela do atendente:** o link vira QR pra o dispositivo da loja escanear e entregar ao cliente.
**Teste:** gerar token → abrir a página como guest → dados aparecem read-only, tentativa de editar não persiste; token expirado/errado → erro. `git commit`.

## 3.6-2 — Captura de selfie (só câmera)
- Componente de câmera com `getUserMedia({video})`; botão capturar; **sem file picker**. Preview + refazer.
- Sem permissão de câmera → instrução clara (e é aqui que entra o escape do gestor, 3.6-4).
- Selfie salva como anexo da OS vinculada ao Aceite.
**Teste:** capturar selfie no fluxo → salva vinculada à OS; confirmar que não há caminho de upload de arquivo. `git commit`.

## 3.6-3 — Assinatura + consentimento + finalização
- Canvas de assinatura (o componente dos blocos 3.1c/d, reaproveitado) **dentro do fluxo do link**.
- **Consentimento LGPD explícito:** checkbox obrigatório com o termo (coleta de imagem biométrica, finalidade, prazo de guarda). Registrar o aceite do termo (versão do termo + timestamp).
- Ao finalizar: grava selfie + assinatura + metadados (IP, UA, hora); **invalida o token**; dispara para o motor o mesmo efeito do aceite presencial (a OS pode avançar).
- **Substituição do canvas presencial:** remover o canvas dos fluxos 3.1c (entrada) e 3.1d (retirada); no lugar, o atendente gera o link/QR. As validações do motor permanecem intactas.
**Teste:** fluxo completo (selfie → assinatura → consentimento → finaliza) → OS recebe o aceite e avança; token não reutilizável; termo registrado. Testar entrada E retirada. `git commit`.

## 3.6-4 — Escape do Gestor + terceiro
- **Escape:** aceite sem selfie **só o Gestor** libera, com **motivo obrigatório**, auditado (quem liberou, quando, por quê). Trava dura com válvula controlada.
- **Terceiro na retirada:** quando quem retira não é o dono, a selfie é **do terceiro** + nome + documento + autorização (o campo de terceiro já existe na OS). O aceite registra que foi terceiro.
**Teste:** Atendente tentando pular selfie → bloqueado; Gestor liberando com motivo → aceite marcado como exceção auditada; retirada por terceiro → selfie do terceiro + doc registrados. `git commit`.

---

## Critério de "pronto" do 3.6
- [ ] Link público read-only; cliente não edita a OS.
- [ ] Selfie só por câmera ao vivo (sem upload); guardada na OS.
- [ ] Assinatura + consentimento LGPD registrados com versão do termo e timestamp.
- [ ] Token único/expirável/uso único; invalidado após aceite.
- [ ] Canvas presencial substituído; validações do motor intactas (OS não avança sem aceite).
- [ ] Escape do Gestor auditado; terceiro com selfie própria + documento.
- [ ] QR na tela do atendente funcionando para o dispositivo da loja.
- [ ] Selfie e assinatura guardadas SEMPRE (entrada e retirada).

## ⚠️ Itens de go-live que este bloco cria
- **Revisão jurídica OBRIGATÓRIA do termo** (selfie = dado biométrico sensível; peso LGPD maior).
- **Dispositivo da loja** (tablet/celular) dedicado ao aceite do cliente sem aparelho próprio.
- **Política de retenção** da imagem (por quanto tempo guardar a selfie) definida com o advogado.
