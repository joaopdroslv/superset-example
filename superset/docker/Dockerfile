# Extends the official Superset image with the extra Python packages declared
# in `superset/requirements-local.txt`. The 4.x image no longer runs a
# bootstrap hook at container start, so we bake the deps in.
FROM apache/superset:4.1.1

USER root
COPY requirements-local.txt /tmp/requirements-local.txt
RUN pip install --no-cache-dir -r /tmp/requirements-local.txt \
 && rm /tmp/requirements-local.txt
USER superset
