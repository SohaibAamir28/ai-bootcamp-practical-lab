# Beginner — Commands & Run Guide
## Docker Fundamentals

**Goal:** Build your first Docker image, run it as a container, and talk to your AI app through it.

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `main.py` | Simple FastAPI app with `/health` and `/chat` |
| `requirements.txt` | Python packages the app needs |
| `Dockerfile` | Recipe for building the Docker image |
| `.dockerignore` | Files to exclude from the image |
| `.env` | Your API key (never commit this) |

---

## Step 0 — Open a Terminal Here

```powershell
cd "c:\Users\Sohaib Aamir\Downloads\ai_bootcamp_practical_lab\day2\beginner"
```

Confirm your files are here:
```powershell
ls
# Should show: main.py  requirements.txt  Dockerfile  .dockerignore  .env
```

---

## Step 1 — Read the Dockerfile (Understand Before Running)

Open `Dockerfile` in your editor. Read every line — each one has a comment explaining it.

The structure is:
```
FROM   → which base image to start from
WORKDIR → where inside the container files will live
COPY   → copy files from your laptop into the container
RUN    → run a command while building (e.g. pip install)
EXPOSE → document which port the app uses
CMD    → what to run when the container starts
```

---

## Step 2 — Build the Image

```powershell
docker build -t ai-coach:v1 .
```

**What each part means:**
- `docker build` — build an image
- `-t ai-coach:v1` — name it `ai-coach`, tag it `v1`
- `.` — use the Dockerfile in the current folder

**Expected output** (first build, takes ~60 seconds):
```
[+] Building 45.2s
 => [1/5] FROM docker.io/library/python:3.11-slim
 => [2/5] WORKDIR /app
 => [3/5] COPY requirements.txt .
 => [4/5] RUN pip install --no-cache-dir -r requirements.txt
 => [5/5] COPY . .
 => exporting to image
 => writing image sha256:abc123...
 => naming to docker.io/library/ai-coach:v1
```

---

## Step 3 — Verify the Image Was Created

```powershell
docker images
```

Expected output:
```
REPOSITORY   TAG   IMAGE ID       CREATED          SIZE
ai-coach     v1    abc123def456   10 seconds ago   180MB
```

> The image is now stored on your machine. Nothing is running yet.

---

## Step 4 — Run the Container

```powershell
docker run -p 8000:8000 --env-file .env ai-coach:v1
```

**What each flag means:**
- `-p 8000:8000` — map port 8000 on your laptop to port 8000 inside the container
- `--env-file .env` — pass your API key to the container at runtime (key stays on your machine, not in the image)
- `ai-coach:v1` — which image to run

**Expected output:**
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

> Leave this terminal running. Open a NEW terminal for the next steps.

---

## Step 5 — Test the App

Open a new PowerShell terminal.

### Test /health
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
```

Expected:
```
status
------
ok
```

### Test /chat
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/chat" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"message": "Give me one tip to improve my writing."}'
```

Expected:
```
reply
-----
Use short sentences. They are easier to read and...
```

### Open in browser
Go to: **http://localhost:8000/docs**

This is FastAPI's auto-generated interactive documentation. You can test any endpoint here.

---

## Step 6 — Look Inside the Container (Optional Deep Dive)

```powershell
# Get the container ID
docker ps

# Open a shell inside the running container
docker exec -it <container-id> /bin/sh

# Once inside:
ls              # see your files at /app
python --version
whoami          # shows: root  (we fix this in intermediate)
exit            # leave the container shell
```

---

## Step 7 — Stop the Container

Go back to the terminal where the container is running and press `Ctrl+C`.

Or from another terminal:
```powershell
docker ps                    # get the container ID
docker stop <container-id>   # stop it gracefully
```

---

## Step 8 — Run in Background (Detached Mode)

```powershell
docker run -d -p 8000:8000 --env-file .env --name my-coach ai-coach:v1
```

**What's new:**
- `-d` — run in background (detached), your terminal is free
- `--name my-coach` — give it a memorable name instead of a random ID

```powershell
docker ps          # see it running
docker logs my-coach         # see the output
docker logs -f my-coach      # stream live output (Ctrl+C to stop streaming)
docker stop my-coach         # stop it
docker rm my-coach           # delete the stopped container
```

---

## Step 9 — Rebuild and Notice the Speed

Make a small change to `main.py` (add a comment or change the welcome message).

```powershell
docker build -t ai-coach:v1 .
```

**Notice:** pip install runs again (~45 seconds). Every code change triggers a full reinstall.

This is the problem we fix in the **intermediate** session with layer caching.

---

## Understanding Check

Before moving to intermediate, make sure you can answer:

- [ ] What is the difference between an image and a container?
- [ ] What does `-p 8000:8000` do?
- [ ] Why do we use `--env-file .env` instead of putting the API key in the Dockerfile?
- [ ] What does `WORKDIR /app` do?
- [ ] Why does `--host 0.0.0.0` matter in the CMD?

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `port is already allocated` | Something else is on port 8000 | `docker ps` → stop that container, or use `-p 8001:8000` |
| `Cannot connect to Docker daemon` | Docker Desktop not running | Open Docker Desktop, wait 30s |
| `no such file or directory: .env` | Missing .env file | Check `.env` exists in this folder |
| `ModuleNotFoundError` | Package not in requirements.txt | Add it and rebuild |
| `connection refused` on curl | Container not started or wrong port | Check `docker ps` and port mapping |
