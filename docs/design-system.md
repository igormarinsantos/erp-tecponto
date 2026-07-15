# Design system do ERP TecPonto

## Fonte de verdade

O ERP reutiliza o sistema visual do site TecPonto. Não deve criar uma marca paralela.

- logo oficial: `src/assets/brand/logo-horizontal.png`;
- ícone oficial: `public/favicon.svg`;
- tipografia: Space Grotesk;
- laranja TecPonto: `#FE5000`;
- laranja digital: `#FF4B00`;
- grafite: `#25292C`;
- névoa: `#EEEDF6`;
- branco: `#FFFFFF`;
- verde: `#25D366`, exclusivo para ações relacionadas ao WhatsApp.

## Princípios de interface

- a próxima ação precisa ser óbvia;
- a navegação usa linguagem da operação, não termos internos do ERPNext;
- laranja sinaliza ação, seleção e prioridade;
- grafite estrutura navegação e contraste;
- névoa cria respiro no tema claro;
- cantos arredondados organizam componentes interativos, sem decorar todas as superfícies;
- títulos usam peso 700;
- corpo usa pesos 400 e 500;
- botões e rótulos usam pesos 600 e 700;
- animações devem ser curtas e respeitar `prefers-reduced-motion`.

## Contraste

Combinações principais:

| Uso | Frente | Fundo | Contraste aproximado |
| --- | --- | --- | --- |
| item ativo e botão primário | `#202428` | `#FE5000` | 4,73:1 |
| texto da lateral | `#FFFFFF` | `#25292C` | 14,66:1 |
| texto no tema escuro | `#F5F6F7` | `#15181B` | 16,47:1 |
| texto secundário escuro | `#ADB4BA` | `#15181B` | 8,50:1 |
| texto no tema claro | `#25292C` | `#EEEDF6` | 12,62:1 |

Texto branco pequeno não deve ser usado sobre o laranja. No laranja, o texto operacional usa `#202428`. Branco sobre laranja fica reservado a títulos grandes ou elementos gráficos.

## Tema claro

- página: névoa;
- cartões e formulários: branco;
- campos: branco levemente acinzentado;
- texto: grafite;
- bordas: grafite com baixa opacidade;
- lateral: grafite;
- item ativo: laranja com texto grafite escuro.

## Tema escuro

- página: `#15181B`;
- cartões: `#1D2125`;
- superfícies elevadas: `#24292E`;
- campos: `#24292E`;
- texto: `#F5F6F7`;
- texto secundário: `#ADB4BA`;
- lateral: `#101214`;
- item ativo: laranja com texto grafite escuro.

O tema escuro não é uma inversão automática do tema claro. Cada superfície possui um token próprio.

## Navegação lateral

A lateral operacional deve mostrar:

1. Visão geral;
2. Ordens de serviço;
3. Aparelhos;
4. Trocas;
5. Clientes;
6. Peças e estoque;
7. Financeiro, quando permitido.

Cada item possui nome e descrição curta. O estado ativo usa fundo laranja, texto grafite e não pode usar fundo branco.

- usar ícones lineares reconhecíveis; não usar siglas como substituto de ícone;
- escrever os nomes conforme a tarefa real da equipe;
- manter a descrição curta apenas como apoio, sem competir com o nome;
- agrupar configurações e recursos técnicos fora da navegação operacional.

## Redução de carga mental

- a visão geral começa pelas três ações mais frequentes;
- alertas mostram somente situações que exigem decisão ou contato;
- o andamento da oficina é apresentado como um fluxo de etapas;
- listas recentes mostram cliente, aparelho e situação sem colunas administrativas;
- formulários usam divulgação progressiva: etapas futuras permanecem ocultas até serem necessárias;
- cada etapa de ordem de serviço e troca informa em uma frase qual é o próximo passo;
- a interface evita gradientes, animações decorativas e cartões sem função operacional.

## Login

- fundo névoa e painel laranja sólido, sem gradiente;
- assinatura horizontal oficial em grafite;
- mensagem principal “Seu celular resolvido.”;
- formulário branco, compacto e com uma única ação primária evidente.

## Logo

- usar o arquivo oficial sem redesenhar ou alterar proporção;
- no grafite, aplicar a versão oficial com filtro branco apenas por CSS;
- em superfícies claras, usar a versão grafite original;
- o favicon é apenas ícone; não substitui a assinatura horizontal no login, workspace ou lateral;
- tamanho mínimo recomendado da assinatura horizontal: 120 px.

## Linguagem

Os nomes devem corresponder ao trabalho da equipe:

- Ordem de Serviço;
- Aparelho;
- Avaliação de Troca;
- Peças e Estoque;
- Financeiro;
- Cliente;
- Diagnóstico;
- Orçamento;
- Garantia.

Termos do framework em inglês devem ser traduzidos quando aparecem para usuários operacionais. Valores internos de workflow podem permanecer sem acentos no banco, mas a apresentação deve estar em português correto.
