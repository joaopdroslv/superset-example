# Minimal image for running the seeder. Source is mounted at runtime so code
# changes don't trigger rebuilds — only dependency changes do.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Install the seeder's Python deps. `requirements.txt` is the build-cache key:
# touching anything else in seed/ won't bust the layer.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r /tmp/requirements.txt \
 && rm /tmp/requirements.txt

# `seed/` is mounted at /workspace/seed at runtime; cwd here is its parent so
# `python -m seed.<...>` finds the package via the implicit cwd entry on sys.path.
WORKDIR /workspace
