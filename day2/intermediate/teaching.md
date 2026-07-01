# Day 2 — Intermediate: Production-Grade Docker
## Instructor Teaching Guide

**Time:** 60–75 minutes  
**Audience:** Students who completed the beginner session. They can build and run a container.  
**Goal:** Students understand layer caching, container security, health monitoring, docker-compose, and CI pipelines.

**Key shift in framing:**
> "The beginner Dockerfile worked. This session is about making it work *correctly* in production,
> where slow rebuilds cost developer time, running as root is a liability, and a crashed container
> that nobody notices is a production incident."

---

## 0. Opening: The Problems with the Beginner Dockerfile (5 minutes)

**Write these three problems on the board:**

```
Problem 1: SLOW    — Every code change rebuilds everything (pip install every time)
Problem 2: UNSAFE  — Container runs as root (biggest security mistake in Docker)
Problem 3: SILENT  — Nobody knows when the container crashes or hangs
```

**Then say:**
> "Today we fix all three. And we add docker-compose so you never have to remember a long docker run command again.
> And we add a CI pipeline so GitHub automatically tests your code before it reaches users."

---

## 1. Layer Caching — Fix the Speed Problem (15 minutes)

### What is a Docker layer?

Open [intermediate/Dockerfile](Dockerfile) alongside [beginner/Dockerfile](../beginner/Dockerfile).

**Say this:**
> "Docker builds images layer by layer. Every instruction in the Dockerfile creates a new layer.
> Docker caches each layer. If a layer hasn't changed, Docker skips it and uses the cache.
>
> The key insight: a layer is invalidated if *anything above it in the file changed*.
> So if your app code changes and `COPY . .` is above `pip install`, pip gets re-run every time."

### Show the wrong order (beginner version):

```dockerfile
# WRONG (what we had before):
COPY . .                           # ← changes whenever ANY file changes
RUN pip install -r requirements.txt  # ← always re-runs, even if packages didn't change
```

**Draw the cache invalidation:**

```
Layer 1: FROM python:3.11-slim   → CACHED (never changes)
Layer 2: WORKDIR /app            → CACHED
Layer 3: COPY . .                → INVALIDATED (code changed)
Layer 4: RUN pip install         → RUNS AGAIN (takes 60 seconds every time)
```

### Show the correct order (intermediate version):

```dockerfile
# CORRECT:
COPY requirements.txt .              # ← only changes when you add/remove packages
RUN pip install -r requirements.txt  # ← cached as long as requirements.txt is same
COPY . .                             # ← only this layer re-runs on code changes
```

**Draw the cache with correct order:**

```
Layer 1: FROM python:3.11-slim      → CACHED
Layer 2: WORKDIR /app               → CACHED
Layer 3: RUN apt-get install curl   → CACHED
Layer 4: COPY requirements.txt .    → CACHED (unless you added a package)
Layer 5: RUN pip install            → CACHED (< 1 second — Docker uses stored result)
Layer 6: COPY . .                   → Re-runs (your code changed)
```

**Total rebuild time: 2 seconds instead of 60 seconds.**

### LIVE DEMO: Prove it works

```bash
# Build fresh (cold)
docker build -t ai-coach:v2 .
# Note the time. pip install runs.

# Build again, no changes
docker build -t ai-coach:v2 .
# Every line says "CACHED". Takes < 1 second.

# Now change one line in main.py (add a comment), rebuild
docker build -t ai-coach:v2 .
# Lines 1-5: CACHED (including pip install)
# Line 6: re-runs COPY . .
# Takes < 2 seconds.
```

**Say this after the demo:**
> "In a team with 10 developers each pushing 10 times a day, this saves 10 × 10 × 58 seconds = 1.6 hours
> of CI time every day. At $0.008 per CI minute, that's real money."

---

## 2. Non-Root User — Fix the Security Problem (10 minutes)

### Why running as root is dangerous

**Say this:**
> "By default, everything inside a Docker container runs as the root user — the most powerful user in Linux.
> If an attacker finds a bug in your app (a dependency vulnerability, a code injection), they can escape
> the container and they'll be root on your server. Game over.
>
> The fix is one line: create a regular user and switch to it."

**Show the lines in the Dockerfile:**

```dockerfile
RUN useradd -m appuser && chown -R appuser /app
USER appuser
```

**Break it down:**
- `useradd -m appuser` — create user called `appuser` with a home directory
- `chown -R appuser /app` — give `appuser` ownership of the app folder
- `USER appuser` — from this point, all commands run as `appuser`, not root

### DEMO: Verify you're not root

```bash
# Run the container and open a shell
docker run --rm -it ai-coach:v2 /bin/sh

# Inside the container:
whoami          # should print: appuser
id              # should show non-zero UID
ls -la /        # cannot write to system folders
```

**Ask the class:** "What if we tried `rm -rf /` inside this container?"  
**Answer:** Permission denied. The user doesn't have access. Root would have succeeded.

### Common question: Does this break anything?

> "Sometimes. If your app tries to write to a folder it doesn't own, it'll fail.
> That's why we do `chown -R appuser /app` — we make sure appuser owns the app folder.
> For anything outside /app (like /tmp), use volumes or `/tmp` which is world-writable."

---

## 3. HEALTHCHECK — Fix the Silent Failure Problem (10 minutes)

### The problem without health checks

**Tell this story:**
> "Company X has a container running in production. At 3am, the LLM API returns a malformed response.
> The Python code throws an unhandled exception. The exception handler doesn't exist. uvicorn crashes.
> The container is still running (the process that crashed was a child process), so Docker thinks it's healthy.
> No alert fires. At 9am, users start complaining. The on-call engineer checks Docker — it says healthy.
> It takes 45 minutes to figure out the process inside is dead.
>
> A HEALTHCHECK would have caught this in 90 seconds."

### Show the HEALTHCHECK instruction:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

**Break down each flag:**

| Flag | Value | Meaning |
|------|-------|---------|
| `--interval` | 30s | Run the check every 30 seconds |
| `--timeout` | 10s | If no response in 10s, count as a failure |
| `--start-period` | 10s | Give the app 10s to start before checking |
| `--retries` | 3 | Mark UNHEALTHY only after 3 consecutive failures |

**What happens when unhealthy:**
- Docker marks the container as `unhealthy`
- Cloud load balancers (AWS ALB, GCP LB) stop sending traffic to it
- Kubernetes restarts it automatically
- Your monitoring dashboard turns red and pages you

### DEMO: Watch the health check

```bash
# Run container in background
docker run -d -p 8000:8000 --env-file .env --name test-coach ai-coach:v2

# Watch the health status update
docker ps  # shows "health: starting" then "healthy"

# Wait 30s, then check again
docker ps  # shows "healthy"

# Stop the app (simulate crash)
docker exec test-coach kill 1

# Check again
docker ps  # shows "unhealthy"

# Clean up
docker rm -f test-coach
```

**Connect to the /health endpoint in the code:**
> "The HEALTHCHECK only works because we wrote the `/health` endpoint in our FastAPI app.
> It always returns `{"status": "ok"}`. Docker curl-s it every 30 seconds.
> This is the contract between your code and your infrastructure."

---

## 4. Docker Compose — Stop Typing Long Commands (10 minutes)

**Show the pain without compose:**

```bash
docker run \
  -p 8000:8000 \
  -e GROQ_API_KEY=gsk_... \
  -e OTHER_KEY=xyz \
  --restart unless-stopped \
  --name ai-coach \
  ai-coach:v2
```

> "This is getting long. Now imagine your teammate needs to run this. Or you need to add another service.
> Docker Compose lets you write this once as a file and run it with `docker-compose up`."

### Walk through [docker-compose.yml](docker-compose.yml):

```yaml
services:
  app:
    build: .              # build from Dockerfile in this folder
    ports:
      - "8000:8000"       # same as -p
    env_file:
      - .env              # same as --env-file
    restart: unless-stopped
    healthcheck:          # same as HEALTHCHECK in Dockerfile (compose can override)
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
```

### DEMO: Run with compose

```bash
# Build and start
docker-compose up --build

# Start in background
docker-compose up -d --build

# Stream logs
docker-compose logs -f

# See status + health
docker-compose ps

# Stop everything
docker-compose down
```

**Key selling point:**
> "The whole team can run `docker-compose up` and get the exact same environment.
> No README that says 'install X, configure Y, set env Z.' Just one command."

---

## 5. GitHub Actions CI Pipeline (10 minutes)

**Opening question:** "What is CI?"

> "Continuous Integration. Every time someone pushes code, an automated system runs tests and checks.
> If anything breaks, the push is flagged before it reaches production.
> We're not setting this up for ourselves today — I want you to read the file and understand it."

Open [.github/workflows/ci.yml](.github/workflows/ci.yml).

### Walk through the structure:

```yaml
on: [push, pull_request]   # triggers
```
> "This workflow runs on every push to any branch, and on every pull request."

```yaml
runs-on: ubuntu-latest     # fresh machine each time
```
> "GitHub gives us a brand new Ubuntu machine for each run. Nothing from a previous run survives.
> That's why we install dependencies every time."

### Walk through each step:

**Step 3: Install dependencies**
> "pip install on a fresh machine."

**Step 4: Lint with ruff**
> "ruff is a linter — it finds syntax errors, unused imports, undefined variables.
> In under 1 second. If ruff fails, the CI stops here. No point running tests on broken code."

**Step 5: Run tests**
> "Tests that don't make real API calls — only validation logic.
> We don't need to spend Groq tokens in CI."

**Step 6: Build Docker image**
> "This proves the Dockerfile is syntactically valid and all packages install correctly.
> A passing build doesn't guarantee the app works, but a failing build guarantees it doesn't."

### Walk through [tests/test_main.py](tests/test_main.py):

```python
def test_health_returns_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

> "This test calls the /health endpoint using FastAPI's test client — no real server running.
> It checks the response is 200 and the body is correct.
> This test would have caught us if we accidentally broke the /health endpoint."

```python
def test_chat_requires_message_field():
    r = client.post("/chat", json={})
    assert r.status_code == 422
```

> "If someone posts to /chat without a `message` field, FastAPI returns 422.
> We test that this validation is working, not accidentally removed."

**Ask the class:** "Why don't we test the actual LLM response?"  
**Answer:** It costs money, it's slow (5-10 seconds), and the response changes every time. We test what we control — the shape of the request and response, not the LLM's content.

---

## 6. Common Student Questions

**Q: "What if I don't have Docker Desktop installed?"**  
A: `docker: command not found`. They need to install Docker Desktop from docker.com. It includes both the Docker engine and docker-compose.

**Q: "Why do we need `curl` installed inside the container?"**  
A: The HEALTHCHECK runs `curl -f http://localhost:8000/health`. If curl isn't in the image, the command fails and the container is immediately unhealthy. `python:3.11-slim` doesn't include curl by default.

**Q: "What does `-f` mean in `curl -f`?"**  
A: Fail silently with exit code 1 on HTTP errors (4xx, 5xx). Without `-f`, curl exits 0 even on a 500 response. Docker reads the exit code to determine health.

**Q: "Can I run docker-compose without building first?"**  
A: If the image already exists, `docker-compose up` (no `--build`) uses the cached image. Add `--build` to force a rebuild.

**Q: "What's the difference between `docker-compose down` and `docker-compose stop`?"**  
A: `stop` pauses containers (like Ctrl+C). `down` stops AND removes containers. `down -v` also removes volumes. Most of the time you want `down`.

**Q: "Does GitHub Actions cost money?"**  
A: GitHub gives free CI minutes for public repos. Private repos get 2,000 free minutes/month, then it costs ~$0.008/minute. Our pipeline takes about 2 minutes, so 1,000 runs/month is free.

---

## 7. Wrap-up (5 minutes)

**Write on board — what we fixed:**

```
Problem 1: SLOW    → Fixed with layer caching (2s vs 60s rebuilds)
Problem 2: UNSAFE  → Fixed with non-root user (useradd + USER appuser)
Problem 3: SILENT  → Fixed with HEALTHCHECK + /health endpoint
Bonus: MANUAL      → Fixed with docker-compose (one command to run everything)
Bonus: UNTESTED    → Fixed with GitHub Actions CI (automatic lint + test + build)
```

**Bridge to advanced:**
> "These are all single-container patterns. Most real apps have multiple containers — the API, a database,
> a cache, a background worker. And the images we've been building are quite large because we bundle
> build tools with the runtime. The advanced session covers multi-stage builds that cut image size in half,
> and a full CI/CD pipeline that deploys to Hugging Face Spaces automatically."

---

## Appendix: Docker Compose Commands

```bash
# Build image and start all services
docker-compose up --build

# Start in background
docker-compose up -d

# Stream logs for all services
docker-compose logs -f

# Stream logs for one service only
docker-compose logs -f app

# See status and health of all containers
docker-compose ps

# Run a one-off command in a service
docker-compose exec app /bin/sh

# Stop all containers (keeps volumes)
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild just one service
docker-compose build app
```

## Appendix: CI/CD Checklist (share with students)

Before pushing to main, a good pipeline checks:
- [ ] Linting (ruff/flake8) — catches syntax and style errors
- [ ] Unit tests (pytest) — catches logic regressions  
- [ ] Docker build — catches Dockerfile errors
- [ ] Integration tests (optional) — catches API contract breaks
- [ ] Deploy to staging (optional) — catches environment issues
