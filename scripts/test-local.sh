#!/usr/bin/env bash
set -euo pipefail

# Runs the complete foundation suite without rebuilding Frappe/ERPNext/HRMS.
# The first run bootstraps a persistent local-ci.local site; later runs migrate
# that site and execute the suite. Set TECPONTO_LOCAL_RESET=1 to discard it.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${TECPONTO_TEST_IMAGE:-ghcr.io/igormarinsantos/erp-tecponto:version-16}"
DB_NAME="tecponto-local-test-db"
REDIS_NAME="tecponto-local-test-redis"
DB_VOLUME="tecponto-local-test-db-data"
SITE_VOLUME="tecponto-local-test-site"
SITE_NAME="local-ci.local"
RUNNER_NAME="tecponto-local-test-runner"
APP_MOUNT="$ROOT:/home/frappe/frappe-bench/apps/tecponto_app:ro"

if [[ "${TECPONTO_EXPORT_FIXTURES:-0}" == "1" ]]; then
	# Native fixture export deliberately receives write access only when requested.
	APP_MOUNT="$ROOT:/home/frappe/frappe-bench/apps/tecponto_app"
fi

if [[ "${TECPONTO_LOCAL_RESET:-0}" == "1" ]]; then
	docker rm -f "$RUNNER_NAME" "$DB_NAME" "$REDIS_NAME" >/dev/null 2>&1 || true
	docker volume rm "$DB_VOLUME" "$SITE_VOLUME" >/dev/null 2>&1 || true
fi

if ! docker image inspect "$IMAGE" >/dev/null 2>&1 || [[ "${TECPONTO_TEST_PULL:-0}" == "1" ]]; then
	gh auth token | docker login ghcr.io -u "$(gh api user --jq .login)" --password-stdin >/dev/null
	docker pull "$IMAGE" >/dev/null
fi

if ! docker inspect "$DB_NAME" >/dev/null 2>&1; then
	docker run -d --name "$DB_NAME" -e MARIADB_ROOT_PASSWORD=local-test-password -v "$DB_VOLUME:/var/lib/mysql" -p 127.0.0.1::3306 mariadb:10.6 >/dev/null
else
	docker start "$DB_NAME" >/dev/null
fi
if ! docker inspect "$REDIS_NAME" >/dev/null 2>&1; then
	docker run -d --name "$REDIS_NAME" -p 127.0.0.1::6379 redis:6.2-alpine >/dev/null
else
	docker start "$REDIS_NAME" >/dev/null
fi

until docker exec "$DB_NAME" mariadb-admin ping -h 127.0.0.1 -uroot -plocal-test-password --silent; do sleep 1; done
DB_PORT="$(docker port "$DB_NAME" 3306/tcp | sed 's/.*://')"
REDIS_PORT="$(docker port "$REDIS_NAME" 6379/tcp | sed 's/.*://')"

# The persistent runner has no worker. Clear jobs left by Frappe hooks before migrate so queue backpressure cannot make tests nondeterministic.
docker exec "$REDIS_NAME" redis-cli FLUSHDB >/dev/null
SITE_EXISTS="$(docker run --rm --entrypoint test -v "$SITE_VOLUME:/home/frappe/frappe-bench/sites" "$IMAGE" -f "/home/frappe/frappe-bench/sites/$SITE_NAME/site_config.json" && echo 1 || true)"

RUNNER_LIFECYCLE=(--rm)
if [[ "${TECPONTO_LOCAL_DETACH:-0}" == "1" ]]; then
	docker rm -f "$RUNNER_NAME" >/dev/null 2>&1 || true
	RUNNER_LIFECYCLE=(--detach --name "$RUNNER_NAME")
	printf 'Runner iniciado: docker logs -f %s\n' "$RUNNER_NAME"
fi

docker run "${RUNNER_LIFECYCLE[@]}" --network host \
	-e DB_PORT="$DB_PORT" -e REDIS_PORT="$REDIS_PORT" -e SITE_EXISTS="$SITE_EXISTS" -e TECPONTO_EXPORT_FIXTURES="${TECPONTO_EXPORT_FIXTURES:-0}" \
	-v "$APP_MOUNT" \
	-v "$SITE_VOLUME:/home/frappe/frappe-bench/sites" \
	--entrypoint bash "$IMAGE" -lc '
set -euo pipefail
cd /home/frappe/frappe-bench
bench set-config -g db_host 127.0.0.1
bench set-config -g db_port "$DB_PORT"
bench set-config -g redis_cache "redis://127.0.0.1:$REDIS_PORT"
bench set-config -g redis_queue "redis://127.0.0.1:$REDIS_PORT"
bench set-config -g redis_socketio "redis://127.0.0.1:$REDIS_PORT"
bench set-config -g -p throttle_user_limit 1000000
if [[ "$SITE_EXISTS" != "1" ]]; then
  bench new-site local-ci.local --mariadb-root-password local-test-password --db-root-username root --admin-password local-admin-password --mariadb-user-host-login-scope "%" --install-app erpnext --set-default
  bench --site local-ci.local install-app hrms
  ./env/bin/python -c "import os, frappe; os.chdir(\"/home/frappe/frappe-bench/sites\"); frappe.init(site=\"local-ci.local\", sites_path=\"/home/frappe/frappe-bench/sites\"); frappe.connect(); frappe.set_user(\"Administrator\"); from frappe.desk.page.setup_wizard.setup_wizard import setup_complete; setup_complete(\"{\\\"country\\\":\\\"Brazil\\\",\\\"company_name\\\":\\\"CI Repair\\\",\\\"company_abbr\\\":\\\"CIR\\\",\\\"currency\\\":\\\"BRL\\\",\\\"timezone\\\":\\\"America/Sao_Paulo\\\",\\\"fy_start_date\\\":\\\"2026-01-01\\\",\\\"fy_end_date\\\":\\\"2026-12-31\\\",\\\"chart_of_accounts\\\":\\\"Standard\\\"}\"); from tecponto_app.install import bootstrap_erpnext_foundation; bootstrap_erpnext_foundation(); frappe.db.commit(); frappe.destroy()"
  bench --site local-ci.local install-app tecponto_app
fi
bench --site local-ci.local migrate
if [[ "${TECPONTO_EXPORT_FIXTURES:-0}" == "1" ]]; then
  bench --site local-ci.local export-fixtures
fi
bench --site local-ci.local execute tecponto_app.tecponto.frontend.test_frontend_api.run_foundation_checks
'
