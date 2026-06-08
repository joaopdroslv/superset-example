# Common edits — what to remember

- **Bumping the Superset version**: change the `x-superset-image` anchor at
  the top of `superset/docker/docker-compose.yml`. Then
  `./scripts/run.sh pull && ./scripts/run.sh up -d` — the `superset-init`
  container will run any pending migrations on boot.

- **Adding a new DB driver**: uncomment it in `superset/requirements-local.txt`,
  then `./scripts/run.sh restart superset superset-worker`. The bootstrap
  script re-installs the file on every start, no rebuild needed.

- **Regenerating the secret key**: change `SUPERSET_SECRET_KEY` in `.env`. This
  will invalidate existing user sessions and any encrypted-at-rest secrets in
  the metadata DB (DB connection passwords). For a learning environment that's
  fine; in real prod, Superset has a key-rotation CLI (`superset re-encrypt-secrets`).

- **First boot is slow**: the bootstrap pip-installs `pymysql` + `cryptography`
  on every container start. For real prod this should be baked into a custom
  Dockerfile that `FROM apache/superset:4.1.1` and pre-installs the extras.
