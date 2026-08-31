# TECPONTO ERP — Regras Permanentes do Projeto (GEMINI.md)

Este documento define as regras inegociáveis de segurança, o rito de trabalho, os princípios de design e o mapa do ambiente do Tecponto ERP. Estas diretrizes devem ser seguidas rigorosamente em todas as sessões e tarefas.

---

## 1. 🛡️ REGRAS INEGOCIÁVEIS DE SEGURANÇA (NUNCA FURAR)

1. **Guard de Custo (Proteção Estrita de Custo/Margem/Lucro):**
   - Papéis **Atendente**, **Gestor** e **Técnico** **NUNCA** veem custo de aquisição, margem ou lucro de peças e serviços.
   - Apenas o **Diretor** possui acesso a esses dados, através de endpoints dedicados e protegidos por permissão de papel (ex.: `get_director_financial_summary`, `get_service_order_director_financial`).
   - **Regra de ouro do backend:** O servidor Python **NUNCA** serializa nem trafega campos de custo para os outros papéis. Não basta ocultar visualmente no frontend; o payload da API não pode conter a informação.

2. **Senha do Aparelho (Dado Sensível e Protegido):**
   - Senha / PIN / Padrão de desenho do aparelho do cliente é dado sensível com armazenamento criptografado.
   - No frontend e em consultas internas, a credencial aparece sempre **mascarada**, sendo revelada somente sob ação intencional e autorizada, com **registro de auditoria**.
   - **Teste de Sentinela Obrigatório:** Testada continuamente com valores-sentinela únicos para garantir que não vaza em nenhum canal: listas de OS, detalhe público, orçamentos, impressões térmicas/A4, links de rastreio, comunicações de WhatsApp ou respostas a usuários não autorizados.

3. **Travas no Motor (Python Backend, Nunca Apenas no React):**
   - As 6 travas de ciclo de vida da OS, gates de papéis e validações de aceite biométrico/físico são implementadas e validadas no motor Python (`tecponto_app`).
   - O React é apenas a superfície de apresentação; a autoridade de negócio e segurança é sempre do backend.
   - Nenhuma proteção de segurança pode ser ignorada ou desativada, nem mesmo para fazer testes passarem.

---

## 2. ⚙️ RITO DE TRABALHO (EFICIÊNCIA E ZERO RETRABALHO)

1. **Tarefas Pequenas e Atômicas:**
   - Trabalhar em tarefas focadas e fatiadas (uma coisa por vez, nunca múltiplas frentes simultâneas sem fechamento).
2. **Testar o Comportamento Real de Ponta a Ponta:**
   - Nunca declarar algo como "pronto" sem testar o fluxo real completo (proibido entregar botões que apenas aparecem na tela mas não executam a ação ou não persistem os dados).
3. **Commit Isolado por Tarefa:**
   - Cada entrega/bloco deve ter seu commit atômico, com mensagem descritiva e suite validada.
4. **Consulta Prévia de Segurança:**
   - Ao tocar em código relacionado a valores financeiros, senhas, transições de estado de OS ou permissões, consultar sempre as regras de segurança antes de alterar.
5. **Reinicialização do Servidor Local após Mudança Python:**
   - Após mudar código Python, reiniciar o servidor local (`bench serve`) antes de testar no navegador — senão o `--noreload` mantém a versão antiga em memória e a mudança não aparece, causando falsos "não funciona".

---

## 3. 🎨 DIRETRIZES DE DESIGN E UX

1. **Raciocinar Estrutura e Hierarquia Antes de Construir:**
   - Antes de implementar ou refazer qualquer tela, definir a estrutura visual, o que deve aparecer, a hierarquia da informação e a ação primária da etapa. Nunca construir de improviso.
2. **Polimento Visual em Passada Única no Fim:**
   - Não gastar ciclos polindo fontes, cores finas e detalhes cosméticos tela por tela durante a fase de engenharia funcional.
   - O refinamento estético e a harmonização visual final serão feitos em uma única passada dedicada após as etapas funcionais estarem concluídas e testadas.

---

## 4. 🗺️ MAPA DO AMBIENTE E COMANDOS

- **Stack Tecnológica:**
  - Backend: Frappe Framework / ERPNext v16 (Python)
  - Frontend: React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons
  - Banco de Dados: MariaDB 10.6, Redis

- **Ambiente de Desenvolvimento:**
  - Código fonte: `/home/usuario/frappe-bench/apps/tecponto_app` (no WSL Ubuntu, branch `version-16`).
  - Acesso no Windows: `\\wsl$\Ubuntu\home\usuario\frappe-bench\apps\tecponto_app`.

- **Comandos de Validação:**
  - **Frontend (Typecheck + Build + Guard de Tokens/Fontes):**
    ```bash
    wsl -d Ubuntu -e bash -c "cd /home/usuario/frappe-bench/apps/tecponto_app/frontend && npm run build"
    ```
  - **Backend (Suite Completa Local em Container):**
    ```bash
    wsl -d Ubuntu -e bash -c "cd /home/usuario/frappe-bench/apps/tecponto_app && ./scripts/test-local.sh"
    ```
  - **Validação Contínua (CI):**
    - O pipeline de CI em 3 estágios é a verdade final de integração.
