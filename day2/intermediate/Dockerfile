# =============================================================================
# INTERMEDIATE DOCKERFILE
# Adds three things the beginner version was missing:
#   1. Layer caching optimisation   (faster rebuilds)
#   2. Non-root user                (security hardening)
#   3. HEALTHCHECK                  (container liveness monitoring)
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# ── SECURITY: install curl for the HEALTHCHECK below ─────────────────────────
# curl is not in python:3.11-slim by default.
# We clean up the apt cache immediately to keep the image small.
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# ── LAYER CACHING TRICK ───────────────────────────────────────────────────────
# Docker builds images layer by layer and caches each layer.
# If a layer has not changed, Docker reuses the cached version (instant).
#
# WRONG order (never do this):
#   COPY . .                          <- changes every time you edit code
#   RUN pip install -r requirements.txt  <- re-runs on EVERY code change = slow
#
# CORRECT order (always do this):
#   COPY requirements.txt .           <- only changes when you add/remove packages
#   RUN pip install ...               <- cached as long as requirements.txt is same
#   COPY . .                          <- code changes don't trigger pip install
#
# Proof: change one line in main.py and rebuild. pip install is SKIPPED.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ── SECURITY: non-root user ───────────────────────────────────────────────────
# By default containers run as root. If someone exploits a bug in your app
# and escapes the container, they have ROOT on the host. Very bad.
# Creating a non-root user limits the blast radius.
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# ── HEALTHCHECK ───────────────────────────────────────────────────────────────
# Docker runs this command every 30 seconds.
# If it fails 3 times → container marked unhealthy → load balancer stops sending traffic.
# This requires the /health endpoint to exist in your FastAPI app.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


# =============================================================================
# DEMO: LAYER CACHING
#
# Run 1 (cold build):
#   docker build -t ai-coach:v2 .
#   Watch every step run from scratch. pip install takes ~60 seconds.
#
# Run 2 (no changes):
#   docker build -t ai-coach:v2 .
#   Every step says "CACHED". Build takes <1 second.
#
# Run 3 (change a line in main.py, then rebuild):
#   docker build -t ai-coach:v2 .
#   Steps 1-5 (including pip install) say "CACHED".
#   Only step 6 (COPY . .) re-runs. Build takes <2 seconds.
#
# This is the difference between a 60-second and a 2-second CI build.
# =============================================================================
