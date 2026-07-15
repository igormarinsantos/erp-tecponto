# Fase 0 — Fundação (do zero até ERPNext rodando + app criado)

> Você não tem nada. No fim desta fase você terá: ERPNext v16 instalado e rodando, o app `tecponto_app` criado, instalado e versionado no Git, e a configuração de empresa/estoque/pagamentos pronta. **Nenhuma customização ainda** — só o solo.

---

## Objetivo
Ambiente reproduzível + configuração base da loja. É a fundação de tudo. Não pule, não improvise.

## O que você terá ao final
- ERPNext v16 acessível no navegador, com login de Administrator.
- App `tecponto_app` instalado e em repositório Git separado.
- `developer_mode` ligado (essencial para as próximas fases gerarem arquivos versionáveis).
- Empresa, contas, depósitos, grupos de item, formas de pagamento e numeração configurados.

---

## Pré-requisitos de máquina (v16)

| Componente | Versão | Observação |
|---|---|---|
| SO | **Ubuntu 24.04 LTS** | recomendado; em Windows use WSL2 com Ubuntu 24.04 |
| Python | **3.12+** | v16 não roda em 3.11 |
| Node.js | **22 LTS+** | se o build de assets falhar, suba a versão do Node |
| MariaDB | **10.6+** | banco padrão |
| Redis | atual | fila e cache |
| Yarn / wkhtmltopdf | atual | assets e PDF |

> **Atalho para começar rápido sem dor de dependência:** usar o `frappe_docker` (container de desenvolvimento). É a alternativa mais à prova de erro para iniciantes. Se preferir esse caminho, clone `https://github.com/frappe/frappe_docker`, siga o devcontainer e pule para o "Passo 4". O guia abaixo cobre a instalação nativa, que é o caminho clássico de desenvolvimento.

---

## Passo 1 — Preparar o servidor (Ubuntu 24.04)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-dev python3-pip python3-venv \
  redis-server mariadb-server mariadb-client \
  xvfb libfontconfig wkhtmltopdf curl

# Node 22 via nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 22 && nvm use 22
npm install -g yarn
```

Configurar o MariaDB (charset/collation que o Frappe exige):

```bash
sudo mysql_secure_installation   # defina senha root
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```
Adicione dentro das seções `[mysqld]` e `[mysql]`:
```ini
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[mysql]
default-character-set = utf8mb4
```
```bash
sudo systemctl restart mariadb
```

## Passo 2 — Instalar o Bench (CLI do Frappe)

```bash
pip3 install frappe-bench --break-system-packages
bench --version   # confirma instalação
```

## Passo 3 — Criar o bench com Frappe v16

```bash
bench init tecponto-bench --frappe-branch version-16
cd tecponto-bench
```

## Passo 4 — Baixar o ERPNext v16

```bash
bench get-app erpnext --branch version-16
```

## Passo 5 — Criar o site

```bash
bench new-site tecponto.local
# define a senha do Administrator e a senha root do MariaDB quando pedir
bench --site tecponto.local install-app erpnext
```

## Passo 6 — Criar e instalar o `tecponto_app`

```bash
bench new-app tecponto_app
# preencha título, descrição, etc. (pode aceitar os padrões)
bench --site tecponto.local install-app tecponto_app
```

## Passo 7 — Ligar developer_mode e versionar no Git

```bash
bench --site tecponto.local set-config developer_mode 1
bench --site tecponto.local clear-cache

cd apps/tecponto_app
git init
git add -A
git commit -m "chore: scaffold tecponto_app (Fase 0)"
# crie um repositório remoto (GitHub/GitLab privado) e:
# git remote add origin <git-url> && git push -u origin main
cd ../..
```

> **Por que `developer_mode`:** sem ele, DocTypes e personalizações criados pela interface ficam presos no banco. Com ele ligado, tudo que você criar com `module = "Tecponto"` vira **arquivo dentro do app** — versionável. Isto é a espinha de todo o projeto.

## Passo 8 — Subir e rodar o Setup Wizard

```bash
bench start
```
Abra `http://tecponto.local:8000` (ou `http://localhost:8000`), entre como **Administrator** e conclua o **Setup Wizard**:
- País: **Brasil** · Moeda: **BRL** · Fuso: America/Sao_Paulo.
- Nome da empresa: **Tecponto** (abreviação ex.: `TEC`).
- Crie o primeiro usuário admin real.

## Passo 9 — Configuração base da loja (tudo nativo)

Ainda **sem customização**. Crie pela interface:

**Depósitos (Warehouse)** — em Stock → Warehouse:
- `Peças - TEC`
- `Acessórios - TEC`
- `Aparelhos Usados - TEC`
- `Sucata - TEC`

**Grupos de Item (Item Group)** — em Stock → Item Group:
- `Peças de Reparo` (com subgrupos: Telas, Baterias, Conectores, Flex, Placas, Câmeras, Botões, Insumos)
- `Produtos de Varejo` (Capinhas, Películas, Carregadores, Cabos, Fones, Suportes)
- `Aparelhos Usados`
- `Serviços` (para mão de obra — item não-estocável)

**Formas de Pagamento (Mode of Payment)** — Accounting → Mode of Payment:
- Pix, Dinheiro, Cartão Débito, Cartão Crédito (ligadas à conta correta da empresa)

**Item de mão de obra** — crie um Item:
- Código: `MO-REPARO` · Grupo: `Serviços` · **Maintain Stock = desmarcado** (is_stock_item = 0)

**Numeração** — Settings → Naming Series (deixe preparado; a série da OS vem na Fase 1).

**Centro de Custo** — confirme que existe o Cost Center padrão da empresa.

---

## Critério de "pronto" (não avance sem isto)

- [ ] `http://localhost:8000` abre e você loga como Administrator.
- [ ] `bench --site tecponto.local console` abre sem erro.
- [ ] `developer_mode` retorna `1`:
      `bench --site tecponto.local execute "frappe.conf.developer_mode"` (ou veja em `sites/tecponto.local/site_config.json`).
- [ ] Os 4 depósitos, os grupos de item, as formas de pagamento e o item `MO-REPARO` existem.
- [ ] Consegue criar manualmente um Customer e uma Sales Invoice de teste (depois pode apagar).
- [ ] `git log` mostra o commit do scaffold.

## Erros comuns

- **Build de assets falha** → Node muito antigo. `nvm install 24 && nvm use 24` e `bench build`.
- **`SyntaxError` ao subir** → Python 3.11. Use 3.12+.
- **MariaDB recusa charset** → confirme o bloco utf8mb4 e reinicie o serviço.
- **`bench start` não abre o site** → confira `/etc/hosts` (mapear `tecponto.local 127.0.0.1`) ou use `localhost:8000`.

## Fechar a fase

```bash
cd apps/tecponto_app
git add -A && git commit -m "chore: base config done (Fase 0)"
```

➡️ **Próximo:** Fase 1 — criar todos os DocTypes e relações.
