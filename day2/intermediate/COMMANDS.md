# Intermediate — Commands & Run Guide
## Production Docker: Caching, Security, Health, Compose, CI

**Goal:** Fix the three problems with the beginner Dockerfile — slow rebuilds, running as root, and silent failures.

---

## What's New vs Beginner

| Feature | Beginner | Intermediate |
|---------|----------|--------------|
| Layer caching | No (pip re-runs every build) | Yes (pip cached when code changes) |
| User | root (dangerous) | `appuser` (non-root) |
| Health monitoring | None | HEALTHCHECK every 30s |
| Startup command | long `docker run` | `docker-compose up` |
| Automated testing | None | GitHub Actions CI |

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `main.py` | App with structured JSON logging + error handling |
| `requirements.txt` | Dependencies |
| `Dockerfile` | Improved: layer caching + non-root + healthcheck |
| `.dockerignore` | Files excluded from image |
| `.env` | API key |
| `docker-compose.yml` | One-command startup + config |
| `tests/test_main.py` | Automated tests (no API calls) |
| `.github/workflows/ci.yml` | GitHub Actions CI pipeline |

---

## Step 0 — Open Terminal Here

```powershell
cd "c:\Users\Sohaib Aamir\Downloads\ai_bootcamp_practical_lab\day2\intermediate"
```

---

## Step 1 — Understand Layer Caching (Read First)

Open `Dockerfile`. Compare these two orderings:

**Wrong (slow):**
```dockerfile
COPY . .                          # changes every time you edit code
RUN pip install -r requirements.txt  # runs every single time = 60 seconds
```

**Correct (fast):**
```dockerfile
COPY requirements.txt .           # only changes when you add/remove packages
RUN pip install -r requirements.txt  # cached unless requirements.txt changes
COPY . .                          # only THIS layer re-runs on code changes
```

---

## Step 2 — Build the Image

```powershell
docker build -t ai-coach:v2 .
```

**Watch for:** pip install running (first build is slow ~60 seconds, cached builds are <2 seconds).

---

## Step 3 — Prove Layer Caching Works

**Build again immediately (no changes):**
```powershell
docker build -t ai-coach:v2 .
```

Every line shows `CACHED`. Build takes under 1 second.

**Now edit one line in main.py (add a comment), then rebuild:**
```powershell
docker build -t ai-coach:v2 .
```

Watch the output:
```
 => CACHED [2/6] RUN apt-get update && apt-get install -y curl ...
 => CACHED [3/6] COPY requirements.txt .
 => CACHED [4/6] RUN pip install --no-cache-dir -r requirements.txt   ← CACHED, skipped!
 => [5/6] COPY . .                                                     ← re-runs (code changed)
```

**Result: 2 seconds instead of 60 seconds.**

---

## Step 4 — Verify Non-Root User

```powershell
# Run the container and open a shell
docker run --rm -it ai-coach:v2 /bin/sh
```

Inside the container:
```sh
whoami        # should print: appuser   (NOT root)
id            # shows: uid=1000(appuser) gid=1000(appuser)
exit
```

> In the beginner version, `whoami` would print `root`. Running as root is a security risk.

---

## Step 5 — Run and Watch the Health Check

```powershell
# Start in background
docker run -d -p 8000:8000 --env-file .env --name coach-v2 ai-coach:v2

# Watch the health status (run this a few times over 30 seconds)
docker ps
```

Status progression:
```
STATUS
starting    ← first 10 seconds (start_period)
healthy     ← after Docker curls /health and gets 200
```

If the app crashes, status becomes `unhealthy` after 3 failed checks.

---

## Step 6 — See Structured JSON Logs

```powershell
# In a new terminal, send a chat request
Invoke-RestMethod -Uri "http://localhost:8000/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"message": "How do I write better?"}'

# Now check the logs
docker logs coach-v2
```

Expected log output (one JSON line per request):
```json
{"request_id": "a3f1b2c4", "endpoint": "/chat", "model": "llama-3.3-70b-versatile", "input_tokens": 23, "output_tokens": 87, "latency_ms": 1842, "cost_usd": 0.000082}
```

> This is structured logging. Every request is a machine-readable JSON object.
> In production, tools like Datadog, Grafana, or CloudWatch ingest these lines automatically.

```powershell
# Stop the container
docker stop coach-v2 && docker rm coach-v2
```

---

## Step 7 — Use Docker Compose

Instead of typing `docker run -p 8000:8000 --env-file .env ...`, use:

```powershell
# Build image and start container
docker-compose up --build

# Output looks the same as docker run, but config comes from docker-compose.yml
```

**In a new terminal:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
```

**Other compose commands:**
```powershell
# Start in background
docker-compose up -d --build

# Stream logs
docker-compose logs -f

# See container status and health
docker-compose ps

# Stop and remove containers
docker-compose down
```

---

## Step 8 — Run the Automated Tests

The tests in `tests/test_main.py` run without starting a server and without calling the real API.

```powershell
# Make sure venv is active
..\..\..\venv\Scripts\activate

# Run all tests
pytest tests/ -v
```

Expected output:
```
PASSED tests/test_main.py::test_health_returns_ok
PASSED tests/test_main.py::test_chat_requires_message_field
PASSED tests/test_main.py::test_chat_rejects_empty_body
PASSED tests/test_main.py::test_health_is_fast
4 passed in 0.45s
```

> 4 tests, under 1 second, zero API calls.

---

## Step 9 — Read the CI Pipeline

Open `.github/workflows/ci.yml`.

This file runs automatically on GitHub on every push. Walk through each step:

```yaml
steps:
  - Checkout code         # download code onto CI machine
  - Set up Python 3.11    # install Python
  - Install dependencies  # pip install
  - Lint with ruff        # check for syntax errors (takes <1 second)
  - Run tests             # pytest (no API calls needed)
  - Build Docker image    # prove the Dockerfile works
```

> **Key point:** ruff and pytest run *before* building the Docker image.
> If tests fail, the Docker build is skipped — no point building broken code.

---

## Step 10 — Full Demo Sequence (for live class)

```powershell
# 1. Show layer caching
docker build -t ai-coach:v2 .           # slow (cold)
docker build -t ai-coach:v2 .           # instant (all cached)

# 2. Start with compose
docker-compose up -d --build

# 3. Send requests and watch logs
Invoke-RestMethod -Uri "http://localhost:8000/chat" -Method Post `
  -ContentType "application/json" -Body '{"message": "Fix my writing"}'
docker-compose logs

# 4. Check health
docker-compose ps

# 5. Show non-root
docker exec -it $(docker ps -q) /bin/sh -c "whoami"

# 6. Run tests
pytest tests/ -v

# 7. Tear down
docker-compose down
```

---

## Understanding Check

- [ ] Why do we copy `requirements.txt` before `COPY . .`?
- [ ] What does `USER appuser` do and why does it matter?
- [ ] What happens to traffic when a container becomes unhealthy?
- [ ] What is the difference between `docker-compose up` and `docker-compose up --build`?
- [ ] Why do the CI tests not need the real `GROQ_API_KEY`?

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `curl: not found` in healthcheck | curl not installed in image | `RUN apt-get install -y curl` in Dockerfile |
| `permission denied` writing files | appuser doesn't own the folder | Add `chown -R appuser /app` before `USER appuser` |
| `docker-compose: command not found` | Old Docker install | Use `docker compose` (space, not hyphen) |
| Tests fail with `ImportError` | Running tests from wrong folder | `cd` into `day2/intermediate/` first |
| Health shows `starting` forever | App is crashing on startup | `docker logs <id>` to see the error |
