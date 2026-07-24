# Produção no Coolify

## Imagem

O workflow publica a imagem privada `ghcr.io/igormarinsantos/erp-tecponto` com
as tags `version-16` e `sha-<commit>`. O build usa o Containerfile em camadas do
`frappe_docker`, instala ERPNext e `tecponto_app`, e executa o build Vite antes
de criar a camada final.

`apps.production.json` não inclui Frappe propositalmente: o framework é instalado
por `FRAPPE_PATH` e `FRAPPE_BRANCH` durante `bench init`. Incluir Frappe também
no arquivo duplicaria o clone.

## Segredos de build

O GitHub Actions usa o `GITHUB_TOKEN` efêmero do próprio workflow para clonar o
repositório privado. Ele é escrito somente em um `gitconfig` temporário e entregue
ao Docker por `--secret`; não entra no histórico, no `apps.json` ou em camadas.

Para build manual, crie um fine-grained PAT restrito ao repositório
`igormarinsantos/erp-tecponto` com **Contents: Read**. Gere um gitconfig temporário:

```ini
[url "https://x-access-token:SEU_TOKEN@github.com/"]
    insteadOf = https://github.com/
```

e passe-o como `--secret id=git_config,src=/caminho/gitconfig`, junto com
`--secret id=apps_json,src=deployment/apps.production.json`.

## Compose no Coolify

Cole `deployment/docker-compose.coolify.yaml` em **Docker Compose Empty**.
O Coolify gera o domínio público automaticamente com a variável mágica
`SERVICE_FQDN_FRONTEND_8080`. Ela também é usada como nome do site Frappe, então
não há domínio, `SITE_NAME` ou label Traefik para preencher manualmente.

O `create-site` instala `erpnext` e `tecponto_app` na criação. Não há terminal
manual pós-deploy. Em deploys seguintes, `migrate` roda antes do backend.

## Variáveis do Coolify

Preencha:

- `FRAPPE_IMAGE=ghcr.io/igormarinsantos/erp-tecponto:version-16`
- `DB_PASSWORD` (gere uma senha longa no Coolify)
- `SITE_ADMIN_PASSWORD` (senha inicial do Administrator, longa e exclusiva)
- Opcional: `GUNICORN_WORKERS=2`, `GUNICORN_THREADS=4`, `GUNICORN_TIMEOUT=120`

O Coolify gera certificados TLS pelo proxy. Ele não deve gerar automaticamente
as duas senhas acima: use o botão de geração de secret e marque-as como secret.

## GHCR privado no Coolify

Crie um PAT clássico dedicado ao deploy com `read:packages`; se o pacote privado
não herdar acesso do repositório, inclua também `repo`. No Coolify, cadastre um
Docker Registry: URL `ghcr.io`, usuário `igormarinsantos`, token esse PAT. Vincule
o registry ao serviço/ambiente antes do primeiro deploy.

## Produção versus desenvolvimento

- `developer_mode` fica desligado: a imagem inicializa bench sem essa flag.
- Não reutilize senhas `Tecponto@123` ou credenciais locais; use as duas secrets
  acima e crie usuários operacionais reais após o primeiro acesso.
- O banco, sites, logs e fila Redis usam volumes próprios. Nenhum dado do WSL é
  levado por este compose.
- O Coolify fornece o domínio público automaticamente. Dados/migração e backup
  automático ficam deliberadamente fora deste artefato.
