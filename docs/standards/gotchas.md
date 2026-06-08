# Gotchas

- **Don't use `localhost` from inside containers** to reach other services. Use
  the service names: `postgres`, `redis`, `mysql-test`.

- **`./scripts/run.sh nuke` deletes datasource data too** — `mysql_test_data`
  is one of the named volumes it drops. There is no separate "drop only metadata"
  command; reach for `docker volume rm` directly if you need finer control.

- **YAML merge keys (`<<: *anchor`)** are a YAML 1.1 feature. Docker Compose v2
  supports them, but some linters / IDEs flag them as deprecated. They are
  intentional here — keep them.

- **Windows line endings**: this repo is being developed on Windows. The shell
  script (`scripts/run.sh`) needs LF line endings to run under Git Bash / WSL.
  If git is configured to convert to CRLF, add a `.gitattributes` with
  `*.sh text eol=lf` to prevent that. (Not added yet; flag it if it becomes a
  problem.)

- **The `WTF_CSRF_EXEMPT_LIST`** in `superset_config.py` lists endpoints that
  internal Superset XHRs hit without a CSRF token. If you upgrade Superset and
  routes get renamed, these will silently start 400ing — re-check against the
  official `superset_config.py` reference for the version you're on.

- **Don't rewrite reports to join through `products.price` / `products.seller_id`**
  — `OrderItem` snapshots `unit_price`, `unit_cost`, and `seller_id` at sale
  time. The `products` table reflects *current* values and will break
  historical margin and seller-attribution numbers. See
  [reference/seeder.md](../reference/seeder.md) for the full data-model
  rationale.
