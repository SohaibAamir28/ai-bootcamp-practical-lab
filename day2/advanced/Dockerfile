# =============================================================================
# ADVANCED DOCKERFILE — Multi-Stage Build
#
# WHAT IS MULTI-STAGE BUILD?
#
#   A standard pip install pulls down build tools (gcc, headers, compilers).
#   Those are needed to BUILD packages but not to RUN them.
#   Multi-stage builds use two FROM images:
#
#     Stage 1 (builder):  has all build tools → installs packages into /venv
#     Stage 2 (runtime):  starts clean → copies only /venv, no build tools
#
#   Result: final image is 300-500 MB smaller. Less to download, less attack surface.
#
# COMPARE:
#   Single-stage image:  ~900 MB
#   Multi-stage image:   ~400 MB
# =============================================================================

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
# We call this stage "builder" so we can reference it in Stage 2.
FROM python:3.11-slim AS builder

WORKDIR /build

# Install packages into an isolated virtual environment inside the container.
# This makes it easy to copy the whole /venv into Stage 2.
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
# Start completely fresh — no build tools, no cache, no intermediate files.
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install curl for the HEALTHCHECK
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy ONLY the installed packages from Stage 1.
# The build tools that installed them are NOT copied.
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy application code
COPY . .

# Security: non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


# =============================================================================
# BUILD AND RUN
#
#   docker build -t ai-coach:advanced .
#   docker run -p 8000:8000 --env-file .env ai-coach:advanced
#
# CHECK IMAGE SIZE (compare single vs multi-stage):
#   docker images ai-coach
#
# INSPECT WHAT'S INSIDE THE IMAGE:
#   docker run --rm -it ai-coach:advanced /bin/sh
#   ls /venv/lib/python3.11/site-packages/   # packages are here
#   which gcc                                 # not here — not copied from builder
# =============================================================================
