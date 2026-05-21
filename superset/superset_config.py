import os

# Register PyMySQL as a stand-in for the C-based MySQLdb. Some internal
# Superset code paths do `import MySQLdb` directly (instead of going through
# the SQLAlchemy dialect specified on the URI), so without this shim chart
# previews against MySQL data sources fail with "No module named 'MySQLdb'".
# Must run before any DB connection is attempted.
import pymysql  # noqa: E402
pymysql.install_as_MySQLdb()

from cachelib.redis import RedisCache  # noqa: E402
from celery.schedules import crontab  # noqa: E402

# ---------- Core ----------
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

# ---------- Metadata DB (Postgres) ----------
SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:"
    f"{os.environ['POSTGRES_PASSWORD']}@postgres:5432/"
    f"{os.environ['POSTGRES_DB']}"
)
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}

# ---------- Redis (cache + Celery broker/results) ----------
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))


def _redis_cache(db: int, prefix: str) -> dict:
    return {
        "CACHE_TYPE": "RedisCache",
        "CACHE_DEFAULT_TIMEOUT": 60 * 60 * 24,
        "CACHE_KEY_PREFIX": prefix,
        "CACHE_REDIS_HOST": REDIS_HOST,
        "CACHE_REDIS_PORT": REDIS_PORT,
        "CACHE_REDIS_DB": db,
    }


CACHE_CONFIG = _redis_cache(1, "superset_meta_")
DATA_CACHE_CONFIG = _redis_cache(2, "superset_data_")
FILTER_STATE_CACHE_CONFIG = _redis_cache(3, "superset_filter_")
EXPLORE_FORM_DATA_CACHE_CONFIG = _redis_cache(4, "superset_explore_")

RESULTS_BACKEND = RedisCache(
    host=REDIS_HOST,
    port=REDIS_PORT,
    key_prefix="superset_results_",
    db=5,
)


# ---------- Celery (async SQL Lab, alerts, reports) ----------
class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
    imports = ("superset.sql_lab", "superset.tasks.scheduler")
    worker_prefetch_multiplier = 1
    task_acks_late = True
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

# ---------- Feature flags ----------
FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "EMBEDDED_SUPERSET": True,
    "ESCAPE_MARKDOWN_HTML": True,
    "DASHBOARD_RBAC": True,
    "HORIZONTAL_FILTER_BAR": True,
    "DRILL_TO_DETAIL": True,
    "DRILL_BY": True,
}

# ---------- SQL Lab ----------
SQLLAB_CTAS_NO_LIMIT = True
SQL_MAX_ROW = 100_000
SQLLAB_TIMEOUT = 300
SUPERSET_WEBSERVER_TIMEOUT = 300
ROW_LIMIT = 5000

# ---------- Security / hardening ----------
TALISMAN_ENABLED = True
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24 * 7
# Internal endpoints called via XHR that should not require a CSRF token.
WTF_CSRF_EXEMPT_LIST = [
    "superset.views.core.log",
    "superset.charts.data.api.data",
]

# When running behind a TLS-terminating proxy (nginx, traefik, ALB),
# this makes Flask honor X-Forwarded-* headers — enables HTTPS-aware redirects.
ENABLE_PROXY_FIX = True

# Maximum upload size for CSV/Excel ingestion — 100 MB.
MAX_CONTENT_LENGTH = 100 * 1024 * 1024

# Blocks risky connection strings on databases added through the UI.
PREVENT_UNSAFE_DB_CONNECTIONS = True
