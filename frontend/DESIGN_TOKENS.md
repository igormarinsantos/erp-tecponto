# Tecponto Front-End Design Tokens

Fonte de verdade: `design-system.md` oficial do ERP TecPonto. Estes tokens substituem os valores extraídos das imagens na Etapa 3.0.

## Base
- Tipografia principal: `Space Grotesk` via `@fontsource/space-grotesk`, pesos 400/500/600/700.
- Títulos, números e logo textual usam `--tp-font-display`.
- Tabelas também usam `--tp-font-table` com Space Grotesk para manter a identidade visual em todas as telas.
- Cards usam `12px`; controles e botões usam `14px`; item ativo da lateral usa `16px`.
- Animações são curtas e respeitam `prefers-reduced-motion`.

## Tema Escuro
- Página: `#15181B` (`--tp-bg`).
- Cartões: `#1D2125` (`--tp-panel`).
- Superfícies elevadas e campos: `#24292E` (`--tp-panel-strong`, `--tp-field`).
- Lateral: `#101214` (`--tp-sidebar`).
- Texto primário: `#F5F6F7`; texto secundário: `#ADB4BA`.
- Bordas: grafite com baixa opacidade.

## Marca
- Laranja TecPonto: `#FE5000`.
- Laranja digital: `#FF4B00`.
- Grafite: `#25292C`.
- Texto sobre botão primário e item ativo: `#202428`.
- Névoa do tema claro futuro: `#EEEDF6`.
- Verde `#25D366` é exclusivo para ações relacionadas ao WhatsApp.

## Componentes
- Botão primário e item ativo: fundo laranja + texto grafite escuro, nunca texto branco pequeno sobre laranja.
- Campos de busca, inputs, textareas e selects usam `#24292E` no tema escuro.
- A lateral operacional segue a ordem: Visão geral, Ordens de serviço, Aparelhos, Trocas, Clientes, Peças e estoque, Financeiro quando permitido.
- A UI evita gradientes decorativos, fundos azulados e cartões sem função operacional.
