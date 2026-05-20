#!/usr/bin/env bash
# Bring up the Superset stack (postgres + redis + app + worker + beat).
# Usage (run from anywhere — script resolves paths relative to the project root):
#   ./superset/scripts/run.sh              -> start everything and tail the init container
#   ./superset/scripts/run.sh down         -> stop containers, keep volumes
#   ./superset/scripts/run.sh nuke         -> stop containers AND drop volumes (DATA LOSS)
#   ./superset/scripts/run.sh logs [svc]   -> tail logs (default service: superset)
#   ./superset/scripts/run.sh ps           -> container status
#   ./superset/scripts/run.sh shell        -> superset python shell (REPL)
# Anything else is forwarded straight to `docker compose`.
#
# Env flags:
#   NO_TESTS=1   -> skip docker/docker-compose.tests.yml even if it exists
set -euo pipefail

# Resolve project root: scripts/ → superset/ → project root (two levels up).
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Superset stack lives in superset/docker/. The shared test MySQL stays at
# docker/docker-compose.tests.yml because it's used by the seeder too.
# Two env files: root .env (shared infra, MYSQL_*) + superset/.env (this domain).
#
# Note: intentionally NO --project-directory. On Windows it breaks --env-file
# resolution (`.env` becomes `D:\.env`). Without it, Compose defaults the
# project dir to the first compose file's dir, so we set --project-name
# explicitly to keep container names stable across runs.
COMPOSE_ARGS=(--project-name superset-example -f "superset/docker/docker-compose.yml")
if [ -f "docker/docker-compose.tests.yml" ] && [ "${NO_TESTS:-0}" != "1" ]; then
  COMPOSE_ARGS+=(-f "docker/docker-compose.tests.yml")
fi
COMPOSE_ARGS+=(--env-file .env --env-file superset/.env)
COMPOSE=(docker compose "${COMPOSE_ARGS[@]}")

cmd="${1:-up}"

ensure_env() {
  local missing=0
  for f in .env superset/.env; do
    if [ ! -f "$f" ]; then
      local example="${f}.example"
      if [ -f "$example" ]; then
        echo ">> $f not found — copying from $example."
        cp "$example" "$f"
      else
        echo "!! $f not found and no $example template available." >&2
      fi
      missing=1
    fi
  done
  if [ "$missing" = 1 ]; then
    echo "!! EDIT the .env file(s) and replace every 'change-me-...' value before starting." >&2
    exit 1
  fi
  if grep -qE '^[A-Z_]+=change-me' .env superset/.env; then
    echo "!! placeholder values ('change-me-...') still present. Edit them before starting." >&2
    grep -nHE '^[A-Z_]+=change-me' .env superset/.env >&2 || true
    exit 1
  fi
}

case "$cmd" in
  up|"")
    ensure_env
    echo ">> Pulling base images..."
    # --ignore-buildable skips services with a `build:` directive (the custom
    # superset-with-drivers image is built locally — Compose tried to pull it).
    "${COMPOSE[@]}" pull --ignore-buildable
    echo ">> Starting stack..."
    "${COMPOSE[@]}" up -d
    echo ">> Following init container (migrations + admin user + examples)..."
    init_cid="$("${COMPOSE[@]}" ps -q superset-init)"
    if [ -n "$init_cid" ]; then
      docker logs -f "$init_cid" || true
    fi
    port="$(grep -E '^SUPERSET_PORT=' .env | cut -d= -f2 || echo 8088)"
    echo ""
    echo ">> Ready! → http://localhost:${port:-8088}"
    if [ -f "docker/docker-compose.tests.yml" ] && [ "${NO_TESTS:-0}" != "1" ]; then
      mysql_db="$(grep -E '^MYSQL_DATABASE=' .env | cut -d= -f2 || echo testdb)"
      mysql_user="$(grep -E '^MYSQL_USER=' .env | cut -d= -f2 || echo tester)"
      echo ">> Test MySQL: mysql+pymysql://${mysql_user}:<password>@mysql-test:3306/${mysql_db}"
    fi
    echo ">> Logs:    ./superset/scripts/run.sh logs"
    echo ">> Status:  ./superset/scripts/run.sh ps"
    ;;
  down)
    "${COMPOSE[@]}" down
    ;;
  nuke)
    read -r -p "This will DROP every volume (postgres, redis, superset_home, mysql_test_data). Are you sure? [y/N] " ans
    [ "${ans:-N}" = "y" ] || [ "${ans:-N}" = "Y" ] || { echo "aborted."; exit 1; }
    "${COMPOSE[@]}" down -v
    ;;
  logs)
    # No forced -f so the command also works against exited containers.
    # Pass -f explicitly to follow: `./superset/scripts/run.sh logs -f superset`.
    shift
    "${COMPOSE[@]}" logs "${@:-superset}"
    ;;
  ps)
    "${COMPOSE[@]}" ps
    ;;
  shell)
    "${COMPOSE[@]}" exec superset superset shell
    ;;
  *)
    # Forward any other argument straight to docker compose (build, restart, exec, ...).
    "${COMPOSE[@]}" "$@"
    ;;
esac
