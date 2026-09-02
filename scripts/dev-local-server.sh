#!/usr/bin/env bash
set -euo pipefail

# Sobe/reinicia um servidor Frappe local persistente pra navegar e testar
# em http://localhost:8000, reaproveitando a mesma infra (rede/site) do
# scripts/test-local.sh (mesmo banco/site, containers com nomes diferentes
# do runner de teste pra não conflitar).
#
# Uso:
#   ./scripts/dev-local-server.sh up        # cria (se não existir) e sobe
#   ./scripts/dev-local-server.sh restart   # reinicia: relê Python + roda migrate
#   ./scripts/dev-local-server.sh down      # para o servidor (db/redis ficam)
#   ./scripts/dev-local-server.sh logs      # segue os logs
#
# Regra do rito (GEMINI.md 2.5): depois de mudar código Python, rodar
# `restart` antes de testar no navegador — o bench roda com --noreload.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${TECPONTO_TEST_IMAGE:-ghcr.io/igormarinsantos/erp-tecponto:version-16}"
DB_NAME="tecponto-local-test-db"
REDIS_NAME="tecponto-local-test-redis"
DB_VOLUME="tecponto-local-test-db-data"
SITE_VOLUME="tecponto-local-test-site"
SITE_NAME="local-ci.local"
SERVER_NAME="tecponto-local-server"
NETWORK_NAME="tecponto-local-test-net"

ACTION="${1:-up}"

case "$ACTION" in
	down)
		docker rm -f "$SERVER_NAME" >/dev/null 2>&1 || true
		echo "Servidor parado (db/redis continuam rodando)."
		exit 0
		;;
	logs)
		exec docker logs -f "$SERVER_NAME"
		;;
	restart)
		if docker inspect "$SERVER_NAME" >/dev/null 2>&1; then
			# db/redis podem ter caído sozinhos (ex.: Docker Desktop reiniciou o
			# daemon) — religa antes de reiniciar o server, senão ele sobe sem
			# conseguir falar com o banco.
			docker start "$DB_NAME" >/dev/null 2>&1 || true
			docker start "$REDIS_NAME" >/dev/null 2>&1 || true
			if docker inspect "$DB_NAME" >/dev/null 2>&1; then
				until docker exec "$DB_NAME" mariadb-admin ping -h 127.0.0.1 -uroot -plocal-test-password --silent >/dev/null 2>&1; do sleep 1; done
			fi
			docker restart "$SERVER_NAME" >/dev/null
			echo "Servidor reiniciado (Python recarregado + migrate rodado). http://localhost:8000"
			exit 0
		fi
		;;
	up) ;;
	*)
		echo "Uso: $0 [up|restart|down|logs]" >&2
		exit 1
		;;
esac

docker network inspect "$NETWORK_NAME" >/dev/null 2>&1 || docker network create "$NETWORK_NAME" >/dev/null

if ! docker inspect "$DB_NAME" >/dev/null 2>&1; then
	docker run -d --name "$DB_NAME" --network "$NETWORK_NAME" -e MARIADB_ROOT_PASSWORD=local-test-password -v "$DB_VOLUME:/var/lib/mysql" mariadb:10.6 >/dev/null
else
	docker start "$DB_NAME" >/dev/null
fi
if ! docker inspect "$REDIS_NAME" >/dev/null 2>&1; then
	docker run -d --name "$REDIS_NAME" --network "$NETWORK_NAME" redis:6.2-alpine >/dev/null
else
	docker start "$REDIS_NAME" >/dev/null
fi

echo "Aguardando o banco..."
until docker exec "$DB_NAME" mariadb-admin ping -h 127.0.0.1 -uroot -plocal-test-password --silent >/dev/null 2>&1; do sleep 1; done

if docker inspect "$SERVER_NAME" >/dev/null 2>&1; then
	docker start "$SERVER_NAME" >/dev/null
	echo "Servidor reiniciado. http://localhost:8000"
	exit 0
fi

docker run -d --name "$SERVER_NAME" --network "$NETWORK_NAME" \
	-p 8000:8000 \
	-e DB_HOST="$DB_NAME" -e REDIS_HOST="$REDIS_NAME" \
	-v "$ROOT:/home/frappe/frappe-bench/apps/tecponto_app" \
	-v "$SITE_VOLUME:/home/frappe/frappe-bench/sites" \
	"$IMAGE" bash -lc '
set -euo pipefail
cd /home/frappe/frappe-bench
bench set-config -g db_host "$DB_HOST"
bench set-config -g db_port 3306
bench set-config -g redis_cache "redis://$REDIS_HOST:6379"
bench set-config -g redis_queue "redis://$REDIS_HOST:6379"
bench set-config -g redis_socketio "redis://$REDIS_HOST:6379"
bench --site local-ci.local migrate
exec bench serve --port 8000 --noreload
' >/dev/null

echo "Servidor criado e migrado. http://localhost:8000"
echo "Depois de mudar Python: ./scripts/dev-local-server.sh restart"
