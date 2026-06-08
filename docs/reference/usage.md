# Usage

Each standalone has its own entry script. Both resolve their own location, so
they can be called from any working directory.

## Superset stack (`./superset/scripts/run.sh`)

```bash
./superset/scripts/run.sh              # pull images, start the stack, tail init logs
./superset/scripts/run.sh ps           # container status
./superset/scripts/run.sh logs [svc]   # tail logs (default: superset)
./superset/scripts/run.sh shell        # Superset Python REPL inside the app container
./superset/scripts/run.sh down         # stop, keep volumes
./superset/scripts/run.sh nuke         # stop AND drop volumes (data loss; confirms)
./superset/scripts/run.sh <anything>   # forwarded to `docker compose`
```

`NO_TESTS=1` skips `docker-compose.tests.yml` even if it exists. The script
refuses to start if `.env` is missing or still contains any `change-me-...`
placeholder.

## Seeder (`./seed/scripts/run.sh`) — fully containerized, no host venv

```bash
./seed/scripts/run.sh                  # seed (additive; skips populated tables)
./seed/scripts/run.sh --reset          # wipe schema + reseed (DESTRUCTIVE)
./seed/scripts/run.sh init             # create the tables only
./seed/scripts/run.sh shell            # interactive bash in the seeder container
./seed/scripts/run.sh build            # rebuild the seeder image
```

The seeder container reaches the test MySQL via `host.docker.internal` on the
host-exposed port (`$MYSQL_PORT`, default 3307), so it doesn't need to share a
Docker network with the Superset stack. Run `./superset/scripts/run.sh` first
to bring up MySQL.

See [reference/seeder.md](./seeder.md) for the full seeder documentation.

## Connecting Superset to the test MySQL

After `./scripts/run.sh`, in the Superset UI:

1. **Settings → Database Connections → + Database**
2. Either pick MySQL from the wizard or paste the SQLAlchemy URI directly:
   ```
   mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@mysql-test:3306/${MYSQL_DATABASE}
   ```

The hostname is **`mysql-test`** (the Compose service name on the internal
Docker network), *not* `localhost`. From the host machine, use `127.0.0.1` and
`${MYSQL_PORT}` (default `3307`, picked to avoid clashing with any local MySQL
on 3306).
