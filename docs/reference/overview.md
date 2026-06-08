# Overview & Stack

## What this is

A minimalist, "production-shaped" Apache Superset deployment running entirely in
Docker Compose. Built for learning and local exploration — *not* a real prod
deployment (Superset officially recommends Kubernetes for prod), but every
choice here mirrors what a small prod setup would look like: Postgres metadata
DB, Redis cache + Celery broker, separate worker / beat / app containers,
healthchecks, secrets via `.env`, Talisman + CSRF on.

A second, optional Compose file spins up a sandbox **MySQL 8** instance so the
user has something to connect Superset *to* (datasource), in addition to its
metadata DB.

## Stack

| Piece                | Image / version           | Role                                                          |
| -------------------- | ------------------------- | ------------------------------------------------------------- |
| `superset`           | `apache/superset:4.1.1`   | Gunicorn web app on port 8088                                 |
| `superset-worker`    | same                      | Celery worker (async SQL Lab, alerts & reports)               |
| `superset-worker-beat` | same                    | Celery beat scheduler                                         |
| `superset-init`      | same                      | One-shot: migrations + admin user + (optional) demo dashboards |
| `postgres`           | `postgres:16-alpine`      | Superset metadata DB                                          |
| `redis`              | `redis:7-alpine`          | Cache (DBs 1–4), results backend (DB 5), Celery broker (DB 0) |
| `mysql-test` *(opt)* | `mysql:8.4`               | Sandbox datasource. Only present when tests compose is loaded |
