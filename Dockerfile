# ── Step 1: Base image ─────────────────────────────────────────────────────────
# python:3.11-slim = Python 3.11 on a minimal Debian image (~130MB vs ~900MB full)
FROM python:3.11-slim

# ── Step 2: Working directory inside the container ─────────────────────────────
# All subsequent commands run from /app
WORKDIR /app

# ── Step 3: Install curl (needed for the HEALTHCHECK below) ───────────────────
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# ── Step 4: Copy requirements FIRST — Docker layer caching trick ───────────────
# If only app code changes (not requirements.txt), Docker skips pip install.
# Flip the order and every code edit re-installs all packages — very slow.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Step 5: Copy the rest of the application code ─────────────────────────────
COPY . .

# ── Step 6: Security — never run as root inside a container ───────────────────
# Root inside a container = root on the host if someone escapes the sandbox.
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# ── Step 7: Health check — container is "healthy" only when /health returns 200
# Docker (and Kubernetes) use this to decide if the container is ready for traffic.
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1

# ── Step 8: Expose port and start the server ───────────────────────────────────
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
