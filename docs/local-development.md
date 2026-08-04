# Testes locais

O runner local usa a imagem publicada `ghcr.io/igormarinsantos/erp-tecponto:version-16` e um site Frappe persistente chamado `local-ci.local`. Ele nao reconstrói Frappe, ERPNext ou HRMS a cada execucao.

## Rotina diaria

No WSL, dentro do repositorio:

```bash
cd /home/usuario/frappe-bench/apps/tecponto_app
./scripts/test-local.sh
```

O comando reutiliza o site existente, executa `bench migrate` e roda a suite completa de fundacao, gates e guards.

## Recriar o site local

Quando houver uma mudanca de schema que exija uma base limpa:

```bash
TECPONTO_LOCAL_RESET=1 ./scripts/test-local.sh
```

A primeira criacao instala Frappe, ERPNext, HRMS e Tecponto e pode levar cerca de 10 a 15 minutos. As execucoes seguintes reaproveitam banco e site. Para forcar um novo pull da imagem publicada, use `TECPONTO_TEST_PULL=1`.

## Frontend rapido

```bash
cd frontend
npm ci --include=dev
npm run build
```

