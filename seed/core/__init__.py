"""Per-table seeders + orchestrator.

Each `<entity>.py` exposes a `seed(session) -> int` function that:
- queries the dependencies it needs (FKs to already-seeded tables),
- creates rows on the given session,
- commits, and
- returns the number of rows inserted.

`run.py` is the master entry point that calls every seeder in FK-safe order.
"""
