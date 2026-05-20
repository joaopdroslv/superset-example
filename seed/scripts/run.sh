#!/usr/bin/env bash
# Run the seeder fully inside Docker — no host Python venv required.
# The seeder container reaches the test MySQL through `host.docker.internal`
# on the host-exposed port (default: $MYSQL_PORT, fallback 3307).
#
# Usage (run from anywhere — script resolves paths relative to the project root):
#   ./seed/scripts/run.sh                 -> seed (additive; skips populated tables)
#   ./seed/scripts/run.sh --reset         -> wipe schema + reseed (DESTRUCTIVE)
#   ./seed/scripts/run.sh init            -> only create the tables, don't seed
#   ./seed/scripts/run.sh validate        -> post-seed integrity/coverage/reliability report
#   ./seed/scripts/run.sh shell           -> interactive bash inside the container
#   ./seed/scripts/run.sh build           -> rebuild the seeder image
#   ./seed/scripts/run.sh <compose-cmd>   -> forwarded to docker compose
#
# Requires the test MySQL to be running. Easiest:
#   ./superset/scripts/run.sh             # also brings up mysql-test
#
# Env overrides:
#   SEED_DB_HOST          target host (default: host.docker.internal)
#   SEED_DB_PORT          target port (default: $MYSQL_PORT or 3307)
#   SEED_DATABASE_URL     fully-formed SQLAlchemy URL — overrides everything else
#   SEED_CONFIG_PATH      alternate config.yml path (inside the container)
set -euo pipefail

# Resolve project root: scripts/ → seed/ → project root (two levels up).
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

COMPOSE_FILE="seed/docker/docker-compose.yml"
# Intentionally no --project-directory: on Windows it breaks `build.context: ..`
# resolution. Compose defaults the project dir to the compose file's own dir,
# which is what we want for build/mount paths to stay relative-to-file.
COMPOSE=(docker compose -f "$COMPOSE_FILE" --env-file .env)

ensure_env() {
  if [ ! -f .env ]; then
    echo "!! .env not found at project root. Copy from .env.example first." >&2
    exit 1
  fi
}

first="${1:-}"
case "$first" in
  init)
    shift
    ensure_env
    "${COMPOSE[@]}" build --quiet seed
    "${COMPOSE[@]}" run --rm seed python -m seed.init "$@"
    ;;
  validate)
    shift
    ensure_env
    "${COMPOSE[@]}" build --quiet seed
    "${COMPOSE[@]}" run --rm seed python -m seed.core.validate "$@"
    ;;
  shell)
    ensure_env
    "${COMPOSE[@]}" build --quiet seed
    "${COMPOSE[@]}" run --rm --entrypoint bash seed
    ;;
  build)
    "${COMPOSE[@]}" build seed
    ;;
  run|"")
    shift || true
    ensure_env
    "${COMPOSE[@]}" build --quiet seed
    "${COMPOSE[@]}" run --rm seed python -m seed.core.run "$@"
    ;;
  -*)
    # First arg is a flag — treat the whole arg list as flags for seed.core.run.
    ensure_env
    "${COMPOSE[@]}" build --quiet seed
    "${COMPOSE[@]}" run --rm seed python -m seed.core.run "$@"
    ;;
  *)
    # Anything else is a docker-compose subcommand (ps, logs, down, ...).
    ensure_env
    "${COMPOSE[@]}" "$@"
    ;;
esac
