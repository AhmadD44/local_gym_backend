FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Only `curl` is needed (for the HEALTHCHECK below). No compiler toolchain
# or libpq-dev: this project uses asyncpg (not psycopg2), which implements
# the PostgreSQL wire protocol itself and doesn't link against system
# libpq; every dependency here (asyncpg, argon2-cffi, cryptography via
# pyjwt[crypto], pydantic-core, orjson, uvicorn[standard]'s httptools/
# uvloop) ships prebuilt manylinux wheels for linux/amd64 + Python 3.12, so
# nothing needs to compile from source. Pulling in gcc/libpq-dev here only
# added ~150MB of unused packages and a much slower build.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts

# --timeout/--retries: pip's default 15s read timeout is too aggressive on
# slow/high-latency networks and causes a hard failure mid-download instead
# of just taking longer; this only affects the build, not the running app.
RUN pip install --no-cache-dir --timeout 120 --retries 5 .

RUN useradd --create-home --uid 1000 appuser
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# --proxy-headers makes uvicorn trust X-Forwarded-For/X-Forwarded-Proto from
# FORWARDED_ALLOW_IPS (default: only localhost, i.e. effectively untrusted)
# and rewrite the request's client IP accordingly. This matters for rate
# limiting and audit-log IPs (app/core/rate_limit.py, RefreshSession) which
# key off request.client.host: without it, every request behind the
# documented reverse-proxy/load-balancer topology (see README) would look
# like it came from the proxy's IP, collapsing all per-client rate limits
# into one shared bucket. Set FORWARDED_ALLOW_IPS to your proxy/LB's
# address (or CIDR, or "*" if the container network itself is trusted).
ENV FORWARDED_ALLOW_IPS=127.0.0.1
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=$FORWARDED_ALLOW_IPS"]
