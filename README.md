# AI Bootcamp — Week 4 Practical Lab
**Evaluation, Observability + Docker**
*iCodeGuru × DigiTech Transformation*

> You cannot improve what you cannot measure.
> You cannot ship what you cannot containerise.

---

## What You Will Build

By the end of this two-day lab you will have a **production-ready AI Writing Coach** that:

| Feature | Day |
|---|---|
| Responds to writing requests using an LLM | Day 1 (Starter) |
| Logs every request as structured JSON | Day 1 – Step 1 |
| Grades its own responses using another LLM | Day 1 – Step 2 |
| Exposes a `/evaluate` endpoint powered by RAGAS | Day 1 – Step 3 |
| Runs inside a secure Docker container | Day 2 |
| Gets automatically tested on every code push | Day 2 |

---

## Project Structure

```
ai_bootcamp_practical_lab/
│
├── starter/
│   └── main.py              ← Day 1 start point (students receive this)
│
├── day1/
│   ├── step1_logging.py     ← Add structured JSON logging
│   ├── step2_llm_judge.py   ← LLM-as-Judge standalone script
│   └── step3_evaluate.py    ← Add RAGAS /evaluate endpoint
│
├── main.py                  ← Final complete app (Dockerfile uses this)
├── Dockerfile               ← Day 2: package the app into a container
├── .dockerignore            ← Day 2: keep secrets out of the image
├── .github/
│   └── workflows/
│       └── ci.yml           ← Day 2: GitHub Actions CI pipeline
│
├── tests/
│   └── test_main.py         ← pytest tests (run by CI)
│
├── requirements.txt         ← All Python dependencies
├── .env                     ← Your secret API keys (never commit this)
├── .env.example             ← Template showing which keys are needed
└── pyproject.toml           ← ruff + pytest config
```

---

## Prerequisites

Before the lab, make sure you have:

- [ ] Python 3.12 installed — check with `py -3.12 --version`
- [ ] A Groq API key — get one free at [console.groq.com](https://console.groq.com)
- [ ] Git installed — check with `git --version`
- [ ] Docker Desktop installed — needed for Day 2 only
- [ ] A GitHub account — needed for Day 2 only

---

## One-Time Setup

Run these commands **once** at the start of the lab. You only need to do this once.

### Step 1 — Create a virtual environment with Python 3.12

```bash
cd "c:\Users\YourName\Downloads\ai_bootcamp_practical_lab"
py -3.12 -m venv venv
```

> **What is a virtual environment?**
> A virtual environment is an isolated Python installation just for this project.
> It prevents your packages from clashing with other projects on your computer.

### Step 2 — Activate the virtual environment

```bash
# Windows
.\venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

You will see `(venv)` appear at the start of your terminal prompt. This means it is active.

> **Important:** You must activate the venv in **every new terminal window** you open.

### Step 3 — Install all dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, Groq/OpenAI SDK, RAGAS, pytest, and everything else needed. It takes 2–3 minutes on first run.

### Step 4 — Create your `.env` file

```bash
# Copy the example file
copy .env.example .env
```

Open `.env` in any text editor and fill in your key:

```
GROQ_API_KEY=gsk_your_key_here
```

> **Why `.env`?**
> Hard-coding API keys in your Python files is dangerous — anyone who reads your code
> gets your key. Keeping keys in `.env` (which is never committed to git) is the safe pattern.

### Step 5 — Verify setup

```bash
python -c "from openai import OpenAI; print('All imports OK')"
```

---

## Day 1 — Make Your AI Measurable (1.5 Hours)

**Goal:** Add logging, automated scoring, and a live evaluation API to the app.

---

### Starter App — What Students Begin With

**File:** `starter/main.py`

This is the base application. It has two endpoints:
- `GET /health` — returns `{"status": "ok"}` (no AI call)
- `POST /chat` — sends a message to the LLM and returns a reply

#### Run the starter app

Open **two terminal windows**. Activate the venv in both.

**Terminal 1 — Start the server:**
```bash
uvicorn starter.main:app --reload
```

You will see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

**Terminal 2 — Send a request:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Fix my grammer in this sentance\"}"
```

**Expected response:**
```json
{"reply": "Fix the grammar in this sentence."}
```

#### Test the health endpoint
```bash
curl http://localhost:8000/health
```
```json
{"status": "ok"}
```

#### What the code does — line by line

```python
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),         # reads from .env file
    base_url="https://api.groq.com/openai/v1", # points to Groq instead of OpenAI
)
```

Groq uses the same OpenAI SDK — you just change the `base_url`. This is how you switch AI providers without rewriting your code.

```python
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",   # the LLM model running on Groq
    max_tokens=512,                     # maximum length of the reply
    messages=[
        {"role": "system", "content": "..."},  # instructions to the model
        {"role": "user",   "content": "..."},  # the user's message
    ],
)
```

---

### Step 1 — Structured JSON Logging

**File:** `day1/step1_logging.py`

**The problem with no logging:**
When your app is running in production and something goes wrong, you have no way to investigate. You cannot answer:
- How long did each request take?
- How many tokens did we use?
- How much did this request cost?
- Which request ID failed?

**The wrong solution — plain text logs:**
```
INFO: Got request
INFO: Calling LLM
INFO: Done
```
You cannot filter this, search it, or alert on it.

**The right solution — structured JSON logs:**
```json
{
  "request_id": "a1b2c3d4",
  "endpoint": "/chat",
  "model": "llama-3.3-70b-versatile",
  "input_tokens": 42,
  "output_tokens": 18,
  "latency_ms": 843,
  "cost_usd": 0.000039
}
```
Every field has a name. You can search `latency_ms > 2000` or `cost_usd > 0.01` instantly.

#### Run step 1

Stop the previous server (`Ctrl+C` in Terminal 1), then:

```bash
uvicorn day1.step1_logging:app --reload
```

Send the same request from Terminal 2:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Fix my grammer in this sentance\"}"
```

**What you will see in Terminal 1 (the JSON log):**
```json
{"request_id": "3f8a21bc", "endpoint": "/chat", "model": "llama-3.3-70b-versatile", "input_tokens": 42, "output_tokens": 18, "latency_ms": 843, "cost_usd": 0.000039}
```

#### The code that was added — only 2 things

**1. A helper function (5 lines):**
```python
def log(data: dict) -> None:
    print(json.dumps(data))
```

**2. One `log()` call inside `/chat` (after the LLM responds):**
```python
log({
    "request_id":   request_id,
    "endpoint":     "/chat",
    "model":        "llama-3.3-70b-versatile",
    "input_tokens":  response.usage.prompt_tokens,
    "output_tokens": response.usage.completion_tokens,
    "latency_ms":   round((time.time() - start) * 1000),
    "cost_usd":     round(input_tokens * COST_PER_INPUT_TOKEN + ..., 6),
})
```

That is the entire change. Everything else is identical to the starter.

---

### Step 2 — LLM-as-Judge

**File:** `day1/step2_llm_judge.py`

**The problem:** You cannot manually read 10,000 AI responses to check quality. It takes weeks and is inconsistent between reviewers.

**The solution:** Use another LLM as the reviewer. One API call per response. The same pattern scales to millions of responses and costs a few dollars.

```
Your Question          →
Your AI's Answer       →   Judge LLM   →   {"score": 8, "reason": "...", "pass": true}
Retrieved Context      →
```

#### The 5 rules for a good judge prompt

| # | Rule | Why |
|---|------|-----|
| 01 | Define your criteria | "Quality" means different things to different people |
| 02 | Require JSON output | Free-text scoring is inconsistent and impossible to parse |
| 03 | Include the context | The judge must only score what the AI could see |
| 04 | Use a DIFFERENT model | Avoids "I think my own output is great" bias |
| 05 | Calibrate with examples | Check 10–20 hand-scored examples before trusting the judge |

#### Run step 2 — no server needed, just a script

```bash
python day1/step2_llm_judge.py
```

**Expected output:**
```
────────────────────────────────────────────────────────────
Example 1 — GOOD answer (faithful to context)
────────────────────────────────────────────────────────────
{
  "score": 9,
  "reason": "The answer accurately reflects the 30-day return policy with receipt requirement.",
  "pass": true
}

────────────────────────────────────────────────────────────
Example 2 — BAD answer (makes up information)
────────────────────────────────────────────────────────────
{
  "score": 2,
  "reason": "The answer invents policies not mentioned in the context.",
  "pass": false
}
```

> **Teaching tip:** Ask students to predict the score for each example BEFORE running the script. This makes the concept stick.

#### The judge prompt — explained

```python
JUDGE_SYSTEM = """You are an expert AI evaluator.

Score the AI response below from 0 to 10 using these three criteria:
- Accuracy: is the information factually correct?
- Completeness: does it fully answer the question?
- Faithfulness: does it stay within the provided context (no made-up facts)?

Return ONLY valid JSON — no extra text, no markdown fences:
{"score": 0-10, "reason": "one sentence", "pass": true/false}

A response "passes" when score >= 7.
"""
```

Notice: the criteria are explicit (Rule 01), JSON is required (Rule 02), context is passed as input (Rule 03).

#### Using the judge in your own code

```python
from day1.step2_llm_judge import judge

result = judge(
    question="What is the return policy?",
    context="Returns allowed within 30 days with receipt.",
    ai_answer="You can return items within 30 days with your receipt.",
)
# result = {"score": 9, "reason": "...", "pass": True}
```

---

### Step 3 — RAGAS /evaluate Endpoint

**File:** `day1/step3_evaluate.py`

**What is RAGAS?**
RAGAS (Retrieval Augmented Generation Assessment) is a framework for measuring the quality of RAG (Retrieval Augmented Generation) systems. It runs LLM-powered metrics automatically.

**Why expose `/evaluate` as an API endpoint?**
- QA teams can test new documents without touching Python code
- Monitoring systems can call it on live responses to detect quality drops over time
- Non-engineers can trigger evaluations from Postman or a simple UI

**Metric used — Faithfulness (≥ 0.90)**

Faithfulness measures whether the AI answer is supported by the retrieved context, or whether it made things up.

```
Score = (statements in answer supported by context) / (total statements in answer)

Score 1.0 = fully faithful — every statement has evidence in the context
Score 0.0 = completely hallucinated — nothing in the answer is supported
```

#### Run step 3

Stop the previous server, then:

```bash
uvicorn day1.step3_evaluate:app --reload
```

**Test `/evaluate` — a faithful answer (should PASS):**
```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is the return policy?\", \"answer\": \"Returns within 30 days with receipt.\", \"contexts\": [\"Our return policy allows returns within 30 days with a valid receipt.\"]}"
```

**Expected response:**
```json
{
  "faithfulness": {
    "score": 1.0,
    "threshold": 0.9,
    "pass": true
  }
}
```

**Test `/evaluate` — a hallucinated answer (should FAIL):**
```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is the return policy?\", \"answer\": \"You can return anything forever, no receipt needed, and get double your money back.\", \"contexts\": [\"Our return policy allows returns within 30 days with a valid receipt.\"]}"
```

**Expected response:**
```json
{
  "faithfulness": {
    "score": 0.0,
    "threshold": 0.9,
    "pass": false
  }
}
```

#### How the `contexts` field works

The `contexts` field is a **list of strings**. Each string is one retrieved document chunk.
If your RAG system retrieves 3 chunks to answer a question, pass all 3:

```json
{
  "question": "What is the refund timeline?",
  "answer": "Refunds take 5-7 business days.",
  "contexts": [
    "Refunds are processed within 5-7 business days.",
    "You will receive a confirmation email when the refund is issued.",
    "Original payment method will be credited."
  ]
}
```

#### The FastAPI interactive docs

While the server is running, open your browser at:
```
http://localhost:8000/docs
```

FastAPI automatically generates an interactive UI where you can test every endpoint without writing curl commands. Show this to students — it is very useful.

---

## Day 2 — Package and Ship (1.5 Hours)

**Goal:** Put the app in a Docker container, add security hardening, and automate testing with GitHub Actions.

---

### The Dockerfile — Line by Line

**File:** `Dockerfile`

```dockerfile
FROM python:3.11-slim
```
**What it does:** Start from a minimal Python 3.11 image (~130MB vs 900MB for the full image).
**Why slim?** Smaller images are faster to download, have fewer attack surfaces, and cost less to store.

```dockerfile
WORKDIR /app
```
**What it does:** All subsequent commands run inside `/app` inside the container.

```dockerfile
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
```
**What it does:** Installs `curl` so the HEALTHCHECK below can ping `/health`.
**Why `rm -rf /var/lib/apt/lists/*`?** Removes the package list cache to keep the image small.

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
**This is the layer caching trick — the most important Docker optimisation for beginners.**

Docker builds images in layers. Each `COPY` and `RUN` is one layer. Docker caches each layer.
If nothing in a layer changed, Docker **skips it entirely** and uses the cached version.

```
requirements.txt unchanged → pip install SKIPPED (uses cache) → build takes 5 seconds
requirements.txt changed   → pip install RUNS AGAIN           → build takes 3 minutes
```

By copying `requirements.txt` FIRST (before the rest of the code), changing a prompt file or fixing a typo in `main.py` does not re-run pip install.

**Demonstration:** Run `docker build` twice and show the second build says "CACHED" on the pip step.

```dockerfile
COPY . .
```
**What it does:** Copy all application code into the container.

```dockerfile
RUN useradd -m appuser && chown -R appuser /app
USER appuser
```
**What it does:** Creates a non-root user and switches to it.
**Why?** If someone exploits a bug in your app and escapes the container, running as root means they have root access on the host machine. Running as a non-root user limits the damage.

```dockerfile
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
```
**What it does:** Docker (and Kubernetes) periodically runs this command. If it fails, the container is marked as unhealthy and removed from the load balancer.
**Why you need `/health` in your FastAPI app:** The HEALTHCHECK needs something to ping. That is why we added `GET /health` to the app.

```dockerfile
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
**What it does:** Documents that port 8000 is used, then starts the FastAPI server.
**Why `--host 0.0.0.0`?** Without this, the server only listens on `localhost` inside the container and is unreachable from outside.

#### Build and run commands

```bash
# Build the image
docker build -t ai-writing-coach:v1 .

# Run the container (inject API key from your local environment)
docker run -p 8000:8000 \
  -e GROQ_API_KEY=$env:GROQ_API_KEY \
  ai-writing-coach:v1

# Test it
curl http://localhost:8000/health
```

**Show layer caching — change one line in main.py, rebuild:**
```bash
# Edit any line in main.py (e.g., change the system prompt)
# Then rebuild:
docker build -t ai-writing-coach:v1 .
```
You will see:
```
 => CACHED [3/7] RUN apt-get install -y curl         (skipped)
 => CACHED [4/7] COPY requirements.txt .              (skipped)
 => CACHED [5/7] RUN pip install -r requirements.txt  (skipped — this is the point)
 => [6/7] COPY . .                                    (re-runs — only app code)
```

---

### The `.dockerignore` File — Keep Secrets Out

**File:** `.dockerignore`

This file tells Docker which files to **exclude** from the image when you run `COPY . .`

```
.env          ← your API keys — NEVER include these
*.pyc         ← compiled Python files — not needed at runtime
__pycache__/  ← Python cache — not needed at runtime
.git/         ← full git history — not needed at runtime
notebooks/    ← Jupyter notebooks — not needed at runtime
```

**The critical one is `.env`.**

Without `.dockerignore`, when you run `docker push` to Docker Hub, your API keys go with the image. Anyone who pulls your image from Docker Hub gets your keys.

**Always verify your `.dockerignore` is working:**
```bash
docker build -t test-image .
docker run --rm test-image ls -la /app/.env
# Should say: ls: /app/.env: No such file or directory
```

---

### GitHub Actions CI Pipeline

**File:** `.github/workflows/ci.yml`

CI stands for **Continuous Integration**. The idea: every time anyone pushes code to GitHub, a set of automated checks run automatically. If any check fails, the push is blocked.

This means bugs are caught before they reach users.

#### What each step does

```yaml
- uses: actions/checkout@v4
```
Downloads your code onto the GitHub runner (a fresh Ubuntu machine).

```yaml
- uses: actions/setup-python@v4
  with:
    python-version: "3.11"
```
Installs Python 3.11 on the runner.

```yaml
- run: pip install -r requirements.txt
```
Installs all your dependencies on the runner.

```yaml
- run: ruff check .
```
**Lint check.** Ruff scans your code for syntax errors, unused imports, and style issues in under 1 second. If ruff fails, the next steps do not run.

```yaml
- run: pytest tests/ -v
```
**Run your tests.** If any test fails, the build is marked red and the Docker build does not run.

```yaml
- run: docker build -t ai-writing-coach:test .
```
**Build the Docker image.** Proves the Dockerfile is valid, all required files are present, and the image can actually be built.

#### How secrets work in GitHub Actions

Your API key cannot be written in the YAML file (that would be public).
GitHub lets you store secrets securely:

1. Go to your repo on GitHub
2. Click **Settings → Secrets and variables → Actions**
3. Click **New repository secret**
4. Name: `GROQ_API_KEY`, Value: your key
5. Click **Add secret**

Then in your YAML:
```yaml
env:
  GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
```

GitHub automatically **masks** your secret in all log output. If the key ever appears in a log, GitHub replaces it with `***`.

#### Set up CI for your project

```bash
# Initialise git (if you haven't already)
git init
git add .
git commit -m "Initial commit: AI Writing Coach with eval and Docker"

# Create a repo on github.com, then:
git remote add origin https://github.com/your-username/ai-writing-coach.git
git push -u origin main
```

Go to your GitHub repo and click the **Actions** tab. You will see the CI pipeline running.

---

## Quick Command Reference

### Development

| Command | What it does |
|---|---|
| `.\venv\Scripts\activate` | Activate virtual environment (Windows) |
| `source venv/bin/activate` | Activate virtual environment (Mac/Linux) |
| `uvicorn starter.main:app --reload` | Run starter app |
| `uvicorn day1.step1_logging:app --reload` | Run app with logging |
| `python day1/step2_llm_judge.py` | Run LLM judge demo |
| `uvicorn day1.step3_evaluate:app --reload` | Run app with /evaluate |
| `uvicorn main:app --reload` | Run final complete app |

### Testing

| Command | What it does |
|---|---|
| `pytest tests/ -v` | Run all tests |
| `ruff check .` | Lint all Python files |
| `curl http://localhost:8000/health` | Check server is running |
| `curl http://localhost:8000/docs` | Open interactive API docs (in browser) |

### Docker

| Command | What it does |
|---|---|
| `docker build -t ai-writing-coach:v1 .` | Build the image |
| `docker run -p 8000:8000 -e GROQ_API_KEY=... ai-writing-coach:v1` | Run the container |
| `docker ps` | List running containers |
| `docker logs <container-id>` | View container logs |
| `docker stop <container-id>` | Stop a running container |

---

## Test Payloads — Copy and Paste

### /chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Fix my grammer in this sentance\"}"
```

### /evaluate — faithful answer (should PASS)
```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is the return policy?\", \"answer\": \"Returns within 30 days with receipt.\", \"contexts\": [\"Our return policy allows returns within 30 days with a valid receipt.\"]}"
```

### /evaluate — hallucinated answer (should FAIL)
```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is the return policy?\", \"answer\": \"You can return anything forever with no receipt for double your money back.\", \"contexts\": [\"Our return policy allows returns within 30 days with a valid receipt.\"]}"
```

---

## Models Used

| Model | Provider | Used For |
|---|---|---|
| `llama-3.3-70b-versatile` | Groq | Main chat and evaluation |
| `llama-3.1-8b-instant` | Groq | LLM-as-Judge (cheaper, faster) |

**Why Groq?**
Groq runs open-source models (Meta's Llama) on custom hardware. It is significantly faster than most alternatives and has a free tier for learning.

---

## Key Concepts Summary

### Evaluation
| Term | Meaning |
|---|---|
| **RAGAS** | Framework for measuring RAG quality with LLM-powered metrics |
| **Faithfulness** | Does the answer stick to what the context says? (no hallucination) |
| **LLM-as-Judge** | Using one LLM to grade the output of another LLM |
| **Context Precision** | Are the retrieved chunks relevant to the question? |
| **Context Recall** | Were any important chunks missed during retrieval? |

### Observability
| Term | Meaning |
|---|---|
| **Structured logging** | Logs written as JSON — searchable, filterable, alertable |
| **Monitoring** | Watching known metrics and alerting on thresholds |
| **Observability** | The ability to understand *any* failure — including ones you didn't predict |
| **Latency p95** | The response time that 95% of users experience or better |

### Docker
| Term | Meaning |
|---|---|
| **Image** | A snapshot of the app, its code, and all its dependencies |
| **Container** | A running instance of an image |
| **Layer caching** | Docker reuses unchanged layers to make rebuilds fast |
| **Non-root user** | Running as a non-root user limits damage if the container is compromised |
| **HEALTHCHECK** | A command Docker runs periodically to verify the container is alive |

### CI/CD
| Term | Meaning |
|---|---|
| **CI** | Continuous Integration — automatically test every code push |
| **CD** | Continuous Deployment — automatically deploy code that passes CI |
| **GitHub Actions** | GitHub's built-in CI/CD runner |
| **Lint** | Static analysis that catches style errors and bugs without running the code |

---

## Troubleshooting

### `ModuleNotFoundError`
The virtual environment is not active. Run:
```bash
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux
```

### `Error: 401 Unauthorized`
Your GROQ_API_KEY in `.env` is wrong or missing. Double-check the key at [console.groq.com](https://console.groq.com).

### `Address already in use`
Another server is already running on port 8000. Either stop it with `Ctrl+C` or run on a different port:
```bash
uvicorn starter.main:app --reload --port 8001
```

### `docker: command not found`
Docker Desktop is not installed or not running. Install it from [docker.com](https://www.docker.com/products/docker-desktop/) and start the application.

### RAGAS takes a long time
RAGAS makes multiple LLM calls internally (it decomposes the answer into statements, then checks each one). This is normal. A single evaluation typically takes 10–30 seconds.

### curl does not work on Windows
Use Git Bash, or replace `curl` with `Invoke-RestMethod` in PowerShell:
```powershell
Invoke-RestMethod -Uri http://localhost:8000/health -Method GET
```

---

*Week 4, Day 3 — iCodeGuru × DigiTech Transformation*
