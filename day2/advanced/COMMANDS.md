# Advanced — Commands & Run Guide
## Multi-Stage Builds, Mocked Tests, Full CI/CD

**Goal:** Ship a production AI app with the full pipeline — multi-stage Docker image, mocked tests, GitHub Actions with caching, and automated deploy to Hugging Face Spaces.

---

## What's New vs Intermediate

| Feature | Intermediate | Advanced |
|---------|-------------|---------|
| Endpoints | /health, /chat | /health, /chat, /judge, /evaluate |
| Dockerfile | Single stage | Multi-stage (smaller image) |
| Image size | ~850 MB | ~420 MB |
| Tests | Validation only | Mocked LLM tests + error simulation |
| CI | Basic | Pip cache + matrix builds + Docker cache |
| Deploy | Manual | Auto-deploy to Hugging Face Spaces |

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `main.py` | Full app: chat + LLM judge + RAGAS evaluate |
| `requirements.txt` | All dependencies including ragas, langchain |
| `Dockerfile` | Multi-stage build |
| `.dockerignore` | Extended exclusion list |
| `.env` | API key |
| `docker-compose.yml` | Compose with volumes + memory limits |
| `tests/test_main.py` | Mocked tests — no real API calls |
| `.github/workflows/ci.yml` | CI with pip cache + matrix + Docker cache |
| `.github/workflows/deploy.yml` | Auto-deploy to Hugging Face Spaces |

---

## Step 0 — Open Terminal Here

```powershell
cd "c:\Users\Sohaib Aamir\Downloads\ai_bootcamp_practical_lab\day2\advanced"
```

---

## Step 1 — Explore the Full App

Open `main.py`. Three endpoints beyond /health:

### /chat — Writing coach
```powershell
# Start app first (Step 4), then test:
Invoke-RestMethod -Uri "http://localhost:8000/chat" `
  -Method Post -ContentType "application/json" `
  -Body '{"message": "How can I make my emails more concise?"}'
```

### /judge — LLM quality score (0-10)
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/judge" `
  -Method Post -ContentType "application/json" `
  -Body '{
    "question": "What is Python?",
    "answer": "Python is a high-level programming language known for its simplicity."
  }'
```

Expected response:
```json
{
  "score": 8,
  "reason": "Clear and accurate, though could mention key use cases.",
  "pass": true,
  "request_id": "a1b2c3d4"
}
```

### /evaluate — RAGAS faithfulness score
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/evaluate" `
  -Method Post -ContentType "application/json" `
  -Body '{
    "question": "What does Python support?",
    "answer": "Python supports object-oriented and functional programming.",
    "context": "Python is a high-level language that supports multiple programming paradigms including object-oriented, functional, and procedural programming."
  }'
```

Expected response:
```json
{
  "faithfulness": {
    "score": 0.95,
    "threshold": 0.9,
    "pass": true
  }
}
```

---

## Step 2 — Understand Multi-Stage Builds

Open `Dockerfile`. Two `FROM` statements = two stages.

**Stage 1 (builder):** installs everything, including build tools
```dockerfile
FROM python:3.11-slim AS builder
RUN python -m venv /venv
RUN pip install -r requirements.txt    # build tools used here
```

**Stage 2 (runtime):** starts clean, copies only the result
```dockerfile
FROM python:3.11-slim AS runtime
COPY --from=builder /venv /venv        # just the installed packages
# gcc, make, headers are NOT copied
```

**Why it matters:**
```
Single-stage image:  ~850 MB  (packages + build tools)
Multi-stage image:   ~420 MB  (packages only)
```

---

## Step 3 — Build and Compare Image Sizes

```powershell
# Build the advanced (multi-stage) image
docker build -t ai-coach:advanced .

# If you still have the intermediate image, compare:
docker images ai-coach
```

Expected:
```
REPOSITORY   TAG        SIZE
ai-coach     advanced   ~420MB
ai-coach     v2         ~850MB
```

### Verify build tools are NOT in the final image:
```powershell
docker run --rm ai-coach:advanced which gcc
# Output: (empty — gcc is not there)

docker run --rm ai-coach:advanced which python
# Output: /venv/bin/python  (packages are there)
```

---

## Step 4 — Run the App

```powershell
# With docker-compose
docker-compose up --build -d

# Or directly
docker run -d -p 8000:8000 --env-file .env --name coach-adv ai-coach:advanced
```

Test all endpoints:
```powershell
# Health
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get

# Chat
Invoke-RestMethod -Uri "http://localhost:8000/chat" -Method Post `
  -ContentType "application/json" `
  -Body '{"message": "Improve this: The meeting was not unproductive."}'

# Judge
Invoke-RestMethod -Uri "http://localhost:8000/judge" -Method Post `
  -ContentType "application/json" `
  -Body '{"question": "What is recursion?", "answer": "A function that calls itself."}'

# Evaluate (takes 10-15 seconds — RAGAS calls the LLM multiple times)
Invoke-RestMethod -Uri "http://localhost:8000/evaluate" -Method Post `
  -ContentType "application/json" `
  -Body '{
    "question": "What is recursion?",
    "answer": "Recursion is when a function calls itself to solve smaller subproblems.",
    "context": "Recursion is a programming technique where a function solves a problem by calling itself with a smaller version of the same problem until it reaches a base case."
  }'
```

---

## Step 5 — Run Mocked Tests

Open `tests/test_main.py` and read how `@patch` works:

```python
@patch("main.client.chat.completions.create")    # replaces real API call
def test_chat_returns_reply_and_request_id(mock_create):
    mock_create.return_value = _make_mock_response("Here is improved writing.")
    # Now calling /chat uses the fake response — no API call, no cost, instant
```

Run the tests:
```powershell
..\..\..\venv\Scripts\activate
pytest tests/ -v
```

Expected:
```
PASSED tests/test_main.py::test_health_ok
PASSED tests/test_main.py::test_chat_missing_field
PASSED tests/test_main.py::test_chat_empty_body
PASSED tests/test_main.py::test_chat_returns_reply_and_request_id
PASSED tests/test_main.py::test_chat_llm_failure_returns_502
PASSED tests/test_main.py::test_judge_missing_fields
PASSED tests/test_main.py::test_judge_parses_json_response
PASSED tests/test_main.py::test_judge_bad_json_returns_502
8 passed in 0.61s
```

**8 tests, under 1 second, zero API calls, zero cost.**

### What each test proves:

| Test | What it protects against |
|------|-------------------------|
| `test_health_ok` | Someone accidentally breaking the /health endpoint |
| `test_chat_missing_field` | Pydantic validation being removed |
| `test_chat_returns_reply_and_request_id` | Response shape changing |
| `test_chat_llm_failure_returns_502` | LLM error returning 500 instead of 502 |
| `test_judge_parses_json_response` | Judge returning correct structure |
| `test_judge_bad_json_returns_502` | Non-JSON from LLM handled cleanly |

---

## Step 6 — Advanced CI Pipeline

Open `.github/workflows/ci.yml`.

**Three improvements over intermediate CI:**

### Matrix builds (test on two Python versions simultaneously):
```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
```
Both jobs run in parallel — no extra time.

### Pip download cache:
```yaml
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```
Second run: pip is restored from cache. Saves ~40 seconds per CI run.

### Docker layer cache:
```yaml
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```
Second run: pip install inside Docker is also cached. Saves another ~60 seconds.

### Job dependency:
```yaml
docker:
  needs: test    # Docker build only runs if tests pass
```

---

## Step 7 — Auto Deploy to Hugging Face Spaces

Open `.github/workflows/deploy.yml`. This workflow:

1. Runs only on push to `main`
2. Clones your Hugging Face Space (it's a git repo)
3. Copies your app files into it
4. Patches the port from 8000 → 7860 (HF requirement)
5. Pushes — HF automatically builds and deploys

### Setup checklist (do once):

```
1. Create Hugging Face account: huggingface.co
2. Go to: huggingface.co/settings/tokens → New token → Write access
3. Create a Space: huggingface.co/new-space
   - SDK: Docker
   - Name: ai-writing-coach
   - Visibility: Public
4. In GitHub repo: Settings → Secrets → Actions → New repository secret
   - Name: HF_TOKEN   Value: (paste your HF token)
   - Name: HF_USERNAME  Value: (your HF username)
5. In deploy.yml, change HF_SPACE to match your Space name
6. Push to main → watch Actions tab → your app is live at:
   https://your-username-ai-writing-coach.hf.space
```

---

## Step 8 — Full Demo Sequence (for live class)

```powershell
# 1. Build multi-stage image and compare size
docker build -t ai-coach:advanced .
docker images ai-coach

# 2. Prove build tools are gone
docker run --rm ai-coach:advanced which gcc
docker run --rm ai-coach:advanced which python

# 3. Start the app
docker-compose up -d

# 4. Hit all four endpoints
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get

Invoke-RestMethod -Uri "http://localhost:8000/chat" -Method Post `
  -ContentType "application/json" `
  -Body '{"message": "Improve: The report was not well received."}'

Invoke-RestMethod -Uri "http://localhost:8000/judge" -Method Post `
  -ContentType "application/json" `
  -Body '{"question": "What is Python?", "answer": "A snake."}'

Invoke-RestMethod -Uri "http://localhost:8000/evaluate" -Method Post `
  -ContentType "application/json" `
  -Body '{
    "question": "What is Python?",
    "answer": "Python is a snake found in tropical regions.",
    "context": "Python is a high-level programming language created by Guido van Rossum."
  }'
# This should FAIL faithfulness (0.0) — the answer contradicts the context

# 5. Run mocked tests
pytest tests/ -v

# 6. Show compose with logs
docker-compose logs

# 7. Tear down
docker-compose down
```

---

## Understanding Check

- [ ] What are the two stages in our Dockerfile and what does each do?
- [ ] Why does `COPY --from=builder /venv /venv` not copy gcc?
- [ ] What does `@patch("main.client.chat.completions.create")` replace?
- [ ] What is `side_effect` vs `return_value` in a mock?
- [ ] Why does the deploy workflow patch the port from 8000 to 7860?
- [ ] What is `needs: test` in the CI workflow?

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `/evaluate` is very slow | RAGAS makes multiple LLM calls | Normal — wait 15-30 seconds |
| `RuntimeError: GROQ_API_KEY is not set` | Missing .env file | Check `.env` exists and has the key |
| `JSONDecodeError` on /judge | LLM returned prose instead of JSON | Check judge prompt — temperature must be low (0.1) |
| `ragas ImportError` | Packages not installed | `pip install ragas datasets langchain-openai` |
| Multi-stage build fails | Dockerfile syntax error | Check both `FROM` lines have `AS name` |
| Tests fail with `ModuleNotFoundError` | Wrong working directory | Must run pytest from `day2/advanced/` |
| HF deploy fails | Missing secrets | Add HF_TOKEN and HF_USERNAME in GitHub Secrets |

---

## Congratulations

You have built:

```
✓ Full AI app: /chat + /judge + /evaluate
✓ Multi-stage Docker image (~420 MB instead of ~850 MB)
✓ Secure container (non-root, secrets not baked in)
✓ Mocked tests that run in <1 second
✓ CI pipeline with matrix builds and caching
✓ Auto-deploy to Hugging Face Spaces
```

This is the workflow professional AI engineers use every day.
