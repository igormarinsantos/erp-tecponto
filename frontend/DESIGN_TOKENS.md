# Tecponto Front-End Design Tokens

Tokens extraídos das 5 referências anexadas para a Etapa 3.0.

## Base
- Fundo: preto frio quase naval, com profundidade sutil: `#070b0f`, `#0b1117`, `#0f171d`.
- Superfícies: cards densos e escuros: `#111a21`, `#17212a`, borda translúcida `rgba(148, 163, 184, 0.16)`.
- Texto: primário `#f8fafc`, secundário `#c4ccd6`, mutado `#8996a3`.
- Tipografia principal: `Space Grotesk` self-hosted via `@fontsource/space-grotesk`, pesos 400/500/600/700.
- Tipografia de tabela: pode usar `Inter`/sans neutra via `--tp-font-table` quando a densidade da tabela pedir leitura mais calma.
- Raio: `8px` para cards, painéis, botões e pills.
- Grid: sidebar fixa, topbar de 64px, conteúdo em 12 colunas, gaps de 16px.

## Marca e Status
- Laranja Tecponto: `#ff5b12`, ativo/CTA: `#ff3d00`.
- WhatsApp/sucesso: `#25d366` e `#22c55e`.
- Info/execução: `#2f8cff`.
- Peça/assinatura/pendente: `#b84cff`.
- Atenção/prazo: `#f5a400`.
- Crítico/bloqueio: `#ef3737`.

## Componentes
- Cards de métrica usam ícone em bloco escuro tingido, número grande e legenda compacta.
- Títulos, logotipo textual e números de cards usam `--tp-font-display` (`Space Grotesk`).
- Tabelas são densas, com linhas separadas por borda de baixa opacidade e badges coloridos.
- Sidebar e right rail mantêm a mesma gramática visual em todos os papéis.
