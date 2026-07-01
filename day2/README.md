# Week 4 Day 2 — Docker & Deployment
## Student Guide

---

## What You Will Build Today

By the end of Day 2 you will have a containerised AI app that:
- Runs identically on any machine
- Automatically restarts if it crashes
- Ships to the internet when you push to GitHub

---

## Folder Structure

```
day2/
├── beginner/       Start here — Docker basics
├── intermediate/   Layer caching, security, healthcheck, CI
└── advanced/       Multi-stage builds, mocked tests, auto-deploy
```

Work through them in order. Each level builds on the previous one.

---

## Prerequisites — Check These First

Open a terminal and run each command. All must succeed before starting.

### 1. Python venv is activated

```powershell
# From the project root (ai_bootcamp_practical_lab/)
.\venv\Scripts\activate

# You should see (venv) at the start of your prompt
# Verify Python version
python --version    # should say Python 3.12.x
```

### 2. Docker Desktop is running

```powershell
docker --version
docker ps
```

Expected output for `docker ps`:
```
CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES
```
(empty table is fine — it means no containers are running yet)

If `docker ps` gives an error → open Docker Desktop from the Start menu and wait for the whale icon to stop animating (about 30 seconds).

### 3. API key is set

```powershell
# Each day2 folder has its own .env file already
# Verify it exists
Test-Path day2\beginner\.env      # should say True
Test-Path day2\intermediate\.env  # should say True
Test-Path day2\advanced\.env      # should say True
```

---

## Quick Reference — Docker Commands

| Command | What it does |
|---------|-------------|
| `docker build -t name:tag .` | Build an image from Dockerfile in current folder |
| `docker run -p 8000:8000 --env-file .env name:tag` | Run a container |
| `docker run -d ...` | Run in background (detached) |
| `docker ps` | List running containers |
| `docker ps -a` | List all containers (including stopped) |
| `docker logs <id>` | View container output |
| `docker logs -f <id>` | Stream live logs |
| `docker stop <id>` | Stop a container |
| `docker rm <id>` | Delete a container |
| `docker images` | List all images |
| `docker rmi name:tag` | Delete an image |
| `docker exec -it <id> /bin/sh` | Open shell inside container |
| `docker-compose up --build` | Build + start with compose |
| `docker-compose up -d` | Start in background |
| `docker-compose logs -f` | Stream compose logs |
| `docker-compose down` | Stop and remove containers |

---

## Session Order

| Session | Time | Folder | Key Concepts |
|---------|------|--------|--------------|
| Beginner | 45 min | `beginner/` | Dockerfile, image, container, port mapping |
| Intermediate | 60 min | `intermediate/` | Layer caching, non-root, healthcheck, compose, CI |
| Advanced | 75 min | `advanced/` | Multi-stage build, mocked tests, auto-deploy |

---

## If Something Goes Wrong

```powershell
# Port already in use
docker ps                          # find what's running
docker stop <container-id>         # stop it

# Kill everything Python-related
Get-Process python* | Stop-Process -Force

# Docker daemon not responding — restart Docker Desktop
Get-Process "Docker Desktop" | Stop-Process -Force
Start-Sleep -Seconds 5
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
# Wait 30 seconds, then try docker ps again

# Container not responding to curl
docker logs <container-id>         # check the error message
```
