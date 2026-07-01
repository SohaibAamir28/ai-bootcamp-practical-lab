# Day 2 — Beginner: Docker Fundamentals
## Instructor Teaching Guide

**Time:** 45–60 minutes  
**Audience:** Students who completed Day 1 (FastAPI + LLM basics). No Docker experience assumed.  
**Goal:** Students can build a Docker image, run a container, and understand *why* Docker exists.

---

## 0. Opening Hook (5 minutes)

Start with this story — it's real, students relate to it immediately.

> "Raise your hand if you've ever sent code to someone and they said 'it doesn't work on my machine.'
> Keep your hand up if it worked perfectly on yours."
>
> (pause — everyone's hand stays up)
>
> "This is called the 'works on my machine' problem. It's been the #1 frustration in software for 30 years.
> The reason it happens: your machine has different Python versions, different OS, different packages,
> different environment variables. Docker solves this by shipping the environment *with* the code."

Then show this mental model on the whiteboard:

```
WITHOUT Docker:                    WITH Docker:
  Your laptop  → code file         Your laptop  → [ code + Python + packages + config ]
  Their laptop → different Python                   Their laptop → same box, guaranteed identical
                 different OS      
                 missing packages  
```

**Key message:** Docker is not about code. It's about *packaging the environment*.

---

## 1. What Is Docker? (10 minutes)

### Analogy: Shipping Containers

> "Before the 1950s, shipping cargo was chaos. Every ship had a different hold, every port had different
> cranes, every cargo had a different shape. Loading a ship took weeks.
>
> Then someone invented the standardised metal shipping container. Same size, same corners, same locks.
> Any crane could lift any container. Any ship could carry any container.
> Loading time dropped from weeks to hours.
>
> Docker does the same thing for software. Your app goes inside a container. Any computer with Docker
> installed can run any container, regardless of the OS underneath."

### Three concepts to define (write them on the board):

| Term | One-line definition | Real-world analogy |
|------|--------------------|--------------------|
| **Dockerfile** | Recipe for building an image | Recipe card |
| **Image** | Frozen snapshot of your app + environment | Frozen meal, ready to heat |
| **Container** | Running instance of an image | The heated meal, being eaten |

**Point to make:** You can build one image and run 1000 containers from it simultaneously. That's how Netflix handles 200 million users.

### Show the workflow diagram:

```
Dockerfile  ──(docker build)──>  Image  ──(docker run)──>  Container
(recipe)                         (snapshot)                 (running app)
```

---

## 2. Walk Through the Dockerfile Line by Line (15 minutes)

Open [beginner/Dockerfile](Dockerfile). Read it together as a class.

### Line 1: FROM

```dockerfile
FROM python:3.11-slim
```

**Say this:**
> "Every Docker image starts from another image. `python:3.11-slim` is an official image from Docker Hub —
> a public registry with 10 million images. It's basically 'Ubuntu with Python 3.11 already installed.'
> The `-slim` means it's the minimal version, no extras. We use slim to keep our image small."

**Ask the class:** "What would happen if we wrote `FROM ubuntu` here?"  
**Answer:** We'd need to install Python ourselves with `RUN apt-get install python3`.

---

### Line 2: WORKDIR

```dockerfile
WORKDIR /app
```

**Say this:**
> "Inside the container, all our files will live in `/app`. Think of it as `mkdir /app && cd /app`.
> Everything we COPY and every command we RUN will happen in this folder."

---

### Lines 3-4: COPY and RUN pip install

```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
```

**Say this:**
> "We copy requirements.txt from our laptop into the container, then install the packages.
> Notice we only copy requirements.txt here, not all our code. This is intentional — I'll explain why
> in the intermediate session. For now, just follow the pattern."

---

### Line 5: COPY the app

```dockerfile
COPY . .
```

**Say this:**
> "Now we copy everything else — our main.py and any other files.
> The first `.` means 'from current folder on my laptop'.
> The second `.` means 'into /app inside the container' (our WORKDIR)."

**STOP HERE for the .dockerignore discussion (see Section 4).**

---

### Lines 6-7: EXPOSE and CMD

```dockerfile
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Say this on EXPOSE:**
> "EXPOSE documents which port the app listens on. It doesn't actually open the port — it's like a
> sticky note saying 'this app uses 8000.' The real port mapping happens when you run the container."

**Say this on CMD:**
> "CMD is what runs when the container starts. Compare it to you typing `uvicorn main:app --host 0.0.0.0`
> in your terminal. The `--host 0.0.0.0` part is critical — it means 'listen on all network interfaces.'
> Without it, uvicorn only listens on localhost *inside* the container and you can't reach it from outside."

**Draw this on the board:**

```
Without --host 0.0.0.0:          With --host 0.0.0.0:
  Container [ uvicorn ]            Container [ uvicorn ]
       ↑ only talks to itself          ↑ listens everywhere
  Your laptop can't reach it      Your laptop CAN reach it
                                  (via port mapping)
```

---

## 3. The .dockerignore File (5 minutes)

Open [beginner/.dockerignore](.dockerignore).

> "When we write `COPY . .`, Docker copies *everything* from our folder. That includes:
> - `.env` with our API key
> - `__pycache__` folders
> - Our entire git history
>
> The `.dockerignore` file tells Docker what to skip, like `.gitignore` for git.
> The most important line is `.env` — without it, your API key gets baked into the image.
> If you push that image to Docker Hub, your key is public. You'll get a bill."

**Ask the class:** "What's worse — forgetting .env in .gitignore or in .dockerignore?"  
**Answer:** .dockerignore, because Docker images are often pushed to public registries.

---

## 4. LIVE DEMO — Build and Run (15 minutes)

### Step 1: Show the project files

```
day2/beginner/
├── main.py
├── requirements.txt
├── Dockerfile
└── .dockerignore
```

Make sure a `.env` file exists in this folder with `GROQ_API_KEY=your_key_here`.

---

### Step 2: Build the image

Run this in the terminal (from the `day2/beginner/` folder):

```bash
docker build -t ai-coach:v1 .
```

**Narrate as it builds:**
- `FROM python:3.11-slim` → "Docker downloads the base image. First time is slow, cached after that."
- `COPY requirements.txt` → "Copies requirements.txt into the container."
- `RUN pip install` → "Installs packages inside the container. This takes 20-30 seconds."
- `COPY . .` → "Copies our app code."
- "Build complete. The image exists now. Nothing is running yet."

---

### Step 3: Look at the image

```bash
docker images
```

Show output:
```
REPOSITORY   TAG       IMAGE ID       SIZE
ai-coach     v1        abc123def456   180MB
```

> "180 MB — that's our app, Python, and all packages bundled together."

---

### Step 4: Run the container

```bash
docker run -p 8000:8000 --env-file .env ai-coach:v1
```

**Explain the flags:**

```
docker run
  -p 8000:8000      # map port 8000 on my laptop → port 8000 inside container
  --env-file .env   # load env variables (API key) — file stays on your machine, not in image
  ai-coach:v1       # which image to run
```

**Draw the port mapping:**

```
Your laptop        Container
:8000    ←───────  :8000 (uvicorn)
```

---

### Step 5: Test it

Open a new terminal (container is running in the first one):

```bash
# Windows PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get

# Or in browser:
# http://localhost:8000/health
# http://localhost:8000/docs
```

Send a chat request:
```bash
Invoke-RestMethod -Uri "http://localhost:8000/chat" -Method Post `
  -ContentType "application/json" `
  -Body '{"message": "How do I make my writing more concise?"}'
```

---

### Step 6: Stop the container

Press `Ctrl+C` in the running terminal, then:

```bash
# List all containers (including stopped)
docker ps -a

# Remove stopped containers
docker container prune
```

---

## 5. Common Student Questions

**Q: "Why can't I just use a virtual environment?"**  
A: A venv only isolates Python packages. It doesn't isolate the Python version, the OS, system libraries (like libssl), or environment variables. Docker isolates everything. Ship the venv AND the OS underneath it.

**Q: "How is Docker different from a Virtual Machine?"**  
A: A VM runs a full OS (2-4 GB). Docker shares the host OS kernel and only packages the app layer (50-500 MB). Docker starts in milliseconds; VMs take minutes.

```
VM:       [ App | Python | Ubuntu | Linux kernel | Hardware emulation ]   ~4GB
Docker:   [ App | Python | Ubuntu ]                                        ~180MB
             └── shares host OS kernel
```

**Q: "What happens to data when I stop the container?"**  
A: It disappears. Containers are stateless by default. For persistent data (databases, logs), you use volumes — covered in the advanced session.

**Q: "Can I run Docker on a server?"**  
A: Yes — that's the whole point. You build the image once on your laptop, push it to a registry (Docker Hub, GitHub Container Registry), and the server pulls and runs it. Same image, guaranteed to work.

**Q: "What is Docker Hub?"**  
A: Public registry (like PyPI but for Docker images). You can pull any image with `docker pull <name>`. The `python:3.11-slim` we used came from there.

---

## 6. Wrap-up (5 minutes)

**What we learned today (write on board):**
1. Docker packages your app + environment into a portable container
2. `Dockerfile` = recipe, `image` = built package, `container` = running instance
3. `.dockerignore` keeps secrets out of images
4. Port mapping connects your laptop to the container's ports
5. `--env-file` passes secrets at runtime without baking them into the image

**Bridge to intermediate:**
> "The Dockerfile we just wrote works, but it has one big problem — it's slow to rebuild.
> Every time you change one line of code, it reinstalls all packages from scratch.
> In the intermediate session, we'll fix that with layer caching, add security hardening,
> and wire up automatic health monitoring."

---

## Appendix: Quick Command Reference

```bash
# Build image
docker build -t <name>:<tag> .

# Run container
docker run -p 8000:8000 --env-file .env <name>:<tag>

# Run in background (detached)
docker run -d -p 8000:8000 --env-file .env <name>:<tag>

# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# View logs of a container
docker logs <container-id>

# Stop a running container
docker stop <container-id>

# Remove a container
docker rm <container-id>

# List images
docker images

# Remove an image
docker rmi <name>:<tag>

# Open a shell inside a running container
docker exec -it <container-id> /bin/sh
```
