# Day 2 — Advanced: Production Deployment
## Instructor Teaching Guide

**Time:** 75–90 minutes  
**Audience:** Students who completed beginner + intermediate sessions.  
**Goal:** Students understand multi-stage Docker builds, mocking in tests, CI with caching, and deploying to Hugging Face Spaces. This is the last session of the bootcamp — tie everything together.

**Opening frame:**
> "This is the last session of the bootcamp. By the end of today, you will have:
> - A full AI app with logging, error handling, LLM-as-Judge, and RAGAS evaluation
> - A production Docker image half the size of what we had before
> - A CI pipeline that runs in under 2 minutes using caching
> - An automated deploy that ships your code to the internet on every push to main
>
> This is what a real team's workflow looks like. Let's build it."

---

## 0. Recap Bridge (5 minutes)

Quick summary of what we've built so far:

```
Day 1:
  Step 1: FastAPI + LLM chat                 (/chat endpoint)
  Step 2: LLM-as-Judge                       (standalone script)
  Step 3: RAGAS faithfulness evaluation      (/evaluate endpoint)

Day 2 Beginner:
  Dockerfile basics                           (build, run, expose, cmd)
  .dockerignore                              (keep secrets out)

Day 2 Intermediate:
  Layer caching                              (2s rebuilds)
  Non-root user                              (security)
  HEALTHCHECK                                (liveness monitoring)
  docker-compose                             (one-command startup)
  GitHub Actions CI                          (automated testing)

Day 2 Advanced (today):
  Combined app                               (chat + judge + evaluate in one)
  Multi-stage builds                         (smaller, cleaner images)
  Mocked tests                               (fast, free CI tests)
  CI with caching                            (even faster CI)
  Deploy to Hugging Face Spaces              (real users, real URL)
```

---

## 1. The Full App: Combining Everything (10 minutes)

Open [advanced/main.py](main.py). This combines all Day 1 work into one deployable service.

### New things compared to intermediate:

**Fail fast on missing config:**
```python
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
```

> "The app refuses to start if the API key is missing. This is called 'fail fast.'
> Without this, the app starts fine, the first request hits the LLM, gets an auth error,
> and you spend 20 minutes debugging why the LLM isn't working.
> With this, the error is immediate and the message is clear."

**Named constants:**
```python
MAIN_MODEL  = "llama-3.3-70b-versatile"
JUDGE_MODEL = "llama-3.1-8b-instant"
FAITHFULNESS_THRESHOLD = 0.90
```

> "No magic numbers scattered through the code. If we want to change the threshold or switch models,
> we change one line at the top. If these were hardcoded in three functions, we'd change three lines
> and risk missing one."

**Three endpoints:**
```
GET  /health    → uptime monitoring
POST /chat      → writing coach response
POST /judge     → LLM-as-Judge quality score
POST /evaluate  → RAGAS faithfulness score
```

### Walk through /judge:

```python
JUDGE_SYSTEM = """You are an expert writing evaluator. Score the answer 0-10.
Return ONLY valid JSON: {"score": ..., "reason": "...", "pass": true/false}"""
```

> "This uses a different model (8b) than the main app (70b). The 5 rules for LLM-as-Judge:
> 1. Define your scoring criteria explicitly
> 2. Require JSON output — no prose
> 3. Include context in the prompt (question + answer)
> 4. Use a different model for judging than for generating
> 5. Set a threshold (we use 7/10 for pass)"

### Walk through /evaluate:

```python
os.environ["OPENAI_API_KEY"]  = GROQ_API_KEY
os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"

faithfulness.llm = LangchainLLMWrapper(
    ChatOpenAI(model=MAIN_MODEL, ...)
)
```

> "RAGAS is designed for OpenAI. We trick it into using Groq by pointing it at Groq's API,
> which uses the same interface. The LangchainLLMWrapper bridges RAGAS to the langchain_openai client.
>
> We only use `faithfulness`, not `answer_relevancy`, because faithfulness only needs an LLM.
> `answer_relevancy` needs an embedding model, and Groq doesn't provide embeddings."

---

## 2. Multi-Stage Builds — Smaller, Cleaner Images (20 minutes)

### The problem: build tools bloat images

Open [advanced/Dockerfile](Dockerfile).

> "When pip installs packages like numpy, ragas, or langchain, it downloads binary packages.
> But some packages (like numpy) must be COMPILED from source if a pre-built binary isn't available.
> This requires gcc, make, header files — tools that are 200-400 MB.
>
> Once the compilation is done, you never need those tools again.
> But in a single-stage Dockerfile, they stay in the final image forever.
>
> Multi-stage builds solve this."

### The mental model:

```
Stage 1 (builder):    Downloads build tools → compiles packages → installs into /venv
Stage 2 (runtime):    Starts clean → copies only /venv → no build tools

Final image contains:  your app + Python + packages (/venv)
Final image lacks:     gcc, make, headers, pip cache, apt lists
```

### Walk through the Dockerfile:

**Stage 1 — Builder:**

```dockerfile
FROM python:3.11-slim AS builder

WORKDIR /build

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

**Explain each line:**

- `AS builder` — names this stage so Stage 2 can reference it
- `python -m venv /venv` — install into an isolated virtual env inside the container
- `ENV PATH="/venv/bin:$PATH"` — makes `pip` and `python` point to /venv versions
- `--no-cache-dir` — don't cache downloads (saves space in this stage too)

**Stage 2 — Runtime:**

```dockerfile
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

COPY . .

RUN useradd -m appuser && chown -R appuser /app
USER appuser
```

**Key line:**
```dockerfile
COPY --from=builder /venv /venv
```

> "`--from=builder` means 'copy from the stage named builder.'
> We copy the entire /venv directory (all installed packages) into the runtime image.
> The build tools that installed them are NOT copied. They existed in Stage 1 and disappeared."

### DEMO: Compare image sizes

```bash
# Build the advanced (multi-stage) image
docker build -t ai-coach:advanced .

# Compare sizes
docker images ai-coach

# You'll see something like:
# ai-coach    advanced    abc123    ~420MB
# ai-coach    v2          def456    ~850MB
```

> "420 MB vs 850 MB. For a team pulling this image every time CI runs:
> 430 MB × 100 CI runs/day × $0.09/GB egress = ~$4/day just in image transfer costs.
> Multi-stage builds pay for themselves."

### Ask the class to guess:

"What would happen if we ran `which gcc` inside the advanced container?"

```bash
docker run --rm ai-coach:advanced which gcc
# Output: (nothing — not found)
```

> "gcc isn't there. It was only in Stage 1, which we threw away after building.
> This also means attackers can't use gcc to compile exploit code inside your container."

---

## 3. Testing with Mocks — Fast, Free, and Reliable (15 minutes)

Open [advanced/tests/test_main.py](tests/test_main.py).

### The problem with testing LLM apps

> "Testing AI apps has a unique challenge: calling the LLM in tests means:
> - Slow (5-10 seconds per test)
> - Costs money (tokens add up across 1000 CI runs)
> - Non-deterministic (the LLM doesn't return the same thing every time)
>
> The solution: mock the LLM call. Replace the real API call with a fake one that returns
> what you tell it to return."

### Walk through the mock setup:

```python
from unittest.mock import MagicMock, patch

def _make_mock_response(content: str, input_tokens=10, output_tokens=20):
    choice  = MagicMock()
    choice.message.content = content

    usage = MagicMock()
    usage.prompt_tokens     = input_tokens
    usage.completion_tokens = output_tokens

    response = MagicMock()
    response.choices = [choice]
    response.usage   = usage
    return response
```

> "MagicMock creates a fake object that looks like an OpenAI response.
> We set `.choices[0].message.content` to whatever we want the LLM to say.
> This is the same structure the real OpenAI SDK returns."

### Walk through a mocked test:

```python
@patch("main.client.chat.completions.create")
def test_chat_returns_reply_and_request_id(mock_create):
    mock_create.return_value = _make_mock_response("Here is your improved writing.")
    r = client.post("/chat", json={"message": "Fix my essay."})
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data
    assert "request_id" in data
    assert len(data["request_id"]) == 8
```

**Break it down:**

- `@patch("main.client.chat.completions.create")` — replaces the real Groq API call with a mock
- `mock_create.return_value = ...` — when called, return our fake response
- The rest of the test runs the real FastAPI endpoint — just with a fake LLM underneath

**Ask the class:** "What are we actually testing here? Not the LLM. So what?"  
**Answer:** We're testing:
1. The endpoint exists and returns 200
2. The response has the right shape (`reply`, `request_id`)
3. `request_id` is 8 characters

> "These are guarantees we can verify without an LLM. If someone refactors the code and accidentally
> removes `request_id` from the response, this test fails. That's the value."

### Test error handling:

```python
@patch("main.client.chat.completions.create")
def test_chat_llm_failure_returns_502(mock_create):
    mock_create.side_effect = Exception("Groq timeout")
    r = client.post("/chat", json={"message": "Hello"})
    assert r.status_code == 502
```

> "`side_effect` makes the mock throw an exception instead of returning a value.
> We simulate a Groq timeout. The test verifies we return 502, not 500.
> This is the only way to test error handling — you can't make Groq timeout on purpose."

### Test the judge's JSON parsing:

```python
@patch("main.client.chat.completions.create")
def test_judge_bad_json_returns_502(mock_create):
    mock_create.return_value = _make_mock_response("Sorry I cannot score this.")
    r = client.post("/judge", json={"question": "Q", "answer": "A"})
    assert r.status_code == 502
```

> "The judge is supposed to return JSON. What if it returns prose instead?
> This test verifies our error handling works for that case.
> Without this test, you'd only find this bug when a real user triggers it in production."

### DEMO: Run the tests

```bash
# From day2/advanced/
pytest tests/ -v

# Expected output:
# PASSED tests/test_main.py::test_health_ok
# PASSED tests/test_main.py::test_chat_missing_field
# PASSED tests/test_main.py::test_chat_returns_reply_and_request_id
# PASSED tests/test_main.py::test_chat_llm_failure_returns_502
# PASSED tests/test_main.py::test_judge_parses_json_response
# PASSED tests/test_main.py::test_judge_bad_json_returns_502
```

> "8 tests, under 1 second, zero API calls, zero cost. This is what CI runs on every push."

---

## 4. Advanced CI Pipeline (10 minutes)

Open [.github/workflows/ci.yml](.github/workflows/ci.yml).

### Matrix builds:

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
```

> "This runs the entire job twice — once on Python 3.11, once on 3.12.
> If a package only works on 3.11 and not 3.12, the matrix catches it.
> GitHub runs both jobs in parallel, so it doesn't cost extra time."

### Pip caching in CI:

```yaml
- name: Cache pip packages
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

> "Same idea as Docker layer caching, but for the CI machine.
> If requirements.txt hasn't changed, GitHub restores the pip cache instead of downloading.
> This saves 30-60 seconds per run.
> The cache key includes a hash of requirements.txt — change the file, invalidate the cache."

### Docker layer caching in CI:

```yaml
- name: Build Docker image with cache
  uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

> "GitHub Actions can cache Docker layers between CI runs.
> `cache-from: type=gha` means 'read layers from GitHub Actions cache.'
> `cache-to: type=gha,mode=max` means 'write all layers to cache.'
> First CI run: slow. Every run after: pip install is cached."

### Job dependency:

```yaml
jobs:
  test:
    ...
  docker:
    needs: test   # only runs if 'test' passed
```

> "No point building a Docker image if tests are failing.
> `needs: test` makes the docker job wait for the test job to succeed.
> This saves CI minutes and gives you a cleaner failure signal."

---

## 5. Deploying to Hugging Face Spaces (15 minutes)

Open [.github/workflows/deploy.yml](.github/workflows/deploy.yml).

### What is Hugging Face Spaces?

> "Hugging Face is the GitHub of AI. Spaces is their hosting platform — you push a Docker image
> or Gradio app and they host it for free (with GPU options for paid plans).
> Every Space gets a public URL like `https://your-username-ai-writing-coach.hf.space`.
>
> The deployment workflow we wrote automates this: push to main → CI passes → code ships to HF Spaces."

### Walk through the workflow:

**Trigger:**
```yaml
on:
  push:
    branches: ["main"]
```
> "Only deploys from main. Pushes to feature branches only run tests, not deploy."

**The deployment script:**
```yaml
run: |
  git clone https://$HF_USERNAME:$HF_TOKEN@huggingface.co/spaces/$HF_USERNAME/$HF_SPACE hf_space
  rsync -av --exclude='.git' --exclude='.env' --exclude='.github' . hf_space/
  sed -i 's/--port 8000/--port 7860/' hf_space/Dockerfile
  cd hf_space && git add -A && git commit -m "Deploy ${{ github.sha }}" && git push
```

**Break it down:**

1. Clone the HF Space repo (it's just a git repo on HF's servers)
2. Copy our app files into it (exclude secrets and CI files)
3. Patch the Dockerfile to use port 7860 (HF Spaces requirement)
4. Push — HF automatically builds the Docker image and deploys it

**The port 7860 detail:**
> "Hugging Face Spaces listens on port 7860 by default. Our Dockerfile uses 8000.
> We use `sed` to patch the Dockerfile in CI before pushing.
> This is a common pattern — environment-specific config injected at deploy time."

### Setup instructions (give students this checklist):

```
To set up your own deployment:

1. Create a Hugging Face account: huggingface.co
2. Get a HF write token: huggingface.co/settings/tokens
3. Create a new Space: huggingface.co/new-space
   - SDK: Docker
   - Visibility: Public
4. In your GitHub repo: Settings → Secrets → Actions
   - Add HF_TOKEN: your token
   - Add HF_USERNAME: your HF username
5. Update the HF_SPACE name in deploy.yml to match your Space name
6. Push to main → watch the Actions tab → your app is live
```

### DEMO: Show a live Space

Open a HF Space in the browser (use an example you've deployed before).

> "This is what you're building toward. Your app, running in a container, accessible to anyone
> on the internet, automatically updated every time you push to main. No servers to manage.
> No SSH. No manual deploys. Just push and it ships."

---

## 6. Bootcamp Wrap-up (10 minutes)

### Full journey on the board:

```
Week 1:  Python basics, APIs
Week 2:  Prompting, Anthropic SDK, few-shot learning
Week 3:  RAG, vector databases, embeddings
Week 4 Day 1:
  - FastAPI + LLM integration (Groq)
  - Structured JSON logging
  - LLM-as-Judge (5 rules)
  - RAGAS faithfulness evaluation
Week 4 Day 2:
  - Docker fundamentals (Dockerfile, images, containers)
  - Production Docker (caching, security, healthchecks)
  - docker-compose (one-command ops)
  - GitHub Actions CI (automated testing)
  - Multi-stage builds (smaller images)
  - Mocked tests (fast, free CI)
  - Hugging Face Spaces deployment (auto-ship)
```

### Key principles to internalize:

**1. Evaluate before you trust**
> "LLMs hallucinate. LLM-as-Judge and RAGAS are not optional niceties — they're how you catch
> problems before users do. Build evaluation in from day one."

**2. Observe everything**
> "If it isn't logged, it didn't happen. Structured JSON logs let you grep, filter, alert,
> and build dashboards. `print('error occurred')` is not observability."

**3. Containerize from the start**
> "If your app works on your laptop but not in the container, the container is the truth.
> Build the Dockerfile on day one of the project, not the day you need to deploy."

**4. Automate the boring parts**
> "CI pipelines are not DevOps magic — they're 50 lines of YAML that save hours every week.
> Write them early, your future self will thank you."

**5. Security is not optional**
> ".env in .dockerignore. Non-root user. No hardcoded secrets. These take 5 minutes and prevent disasters."

### Final challenge (optional homework):

> "Take the advanced app and add one more endpoint: `/summarize`. It takes a long document and returns
> a 3-sentence summary. Add a RAGAS evaluation for the summary. Add a test with a mock. Ship it to HF Spaces."

---

## Common Student Questions

**Q: "Multi-stage builds look complex. Is it worth it?"**  
A: For simple apps with pure-Python deps, maybe not. For apps with compiled packages (numpy, ragas, langchain), yes — images routinely go from 1.5GB to 500MB.

**Q: "Why use rsync in the deploy script instead of just `cp -r`?"**  
A: rsync is better at handling dotfiles, preserving permissions, and its `--exclude` flag is reliable. `cp -r` has quirks with hidden files and directories.

**Q: "Can we deploy to AWS/GCP instead of HF Spaces?"**  
A: Yes. AWS ECS, GCP Cloud Run, and Azure Container Apps all accept Docker images. The deploy workflow would use their CLI tools instead of git push, but the Dockerfile is the same.

**Q: "What if CI fails after I already pushed to main?"**  
A: The workflow doesn't deploy. The old version keeps running. You fix the code, push again, CI passes, deployment happens. This is the contract: main is always deployable.

**Q: "Is `unittest.mock` the only way to mock?"**  
A: No. `pytest-mock` (a popular plugin) provides a `mocker` fixture that does the same thing with slightly cleaner syntax. `responses` is another library for mocking HTTP calls specifically. `unittest.mock` works without extra dependencies.

**Q: "What is `side_effect` vs `return_value` in a mock?"**  
A: `return_value` makes the mock return a value when called. `side_effect` makes it raise an exception, or can be a function that gets called instead. Use `side_effect = Exception(...)` to simulate failures.

---

## Appendix: What Students Now Know How To Build

```
A complete AI application:
  ✓ FastAPI backend with multiple endpoints
  ✓ LLM integration (Groq/OpenAI-compatible)
  ✓ Structured observability logging
  ✓ LLM-as-Judge quality evaluation
  ✓ RAGAS faithfulness scoring
  ✓ Docker container (secure, cached, health-monitored)
  ✓ docker-compose for local development
  ✓ GitHub Actions CI (lint + test + build)
  ✓ Mocked tests that run fast and free
  ✓ Automated deployment to Hugging Face Spaces
```

This is a production-grade AI application workflow. Most junior developers take 6-12 months on the job to learn these patterns. The students now have them.
