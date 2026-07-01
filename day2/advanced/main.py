# =============================================================================
# DAY 2 — ADVANCED LEVEL
# Full Production App: Logging + Error Handling + LLM-as-Judge + RAGAS
#
# NEW vs Intermediate:
#   + /evaluate endpoint    (RAGAS faithfulness scoring)
#   + /judge   endpoint    (LLM-as-Judge for writing quality)
#   + env var validation    (fail fast with a clear message if key is missing)
#   + typed constants       (no magic numbers scattered through the code)
#
# THIS IS THE FULL APP. It combines everything from Day 1 into one container.
# =============================================================================
import json
import os
import time
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Fail fast on missing config ───────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")

MAIN_MODEL  = "llama-3.3-70b-versatile"
JUDGE_MODEL = "llama-3.1-8b-instant"
FAITHFULNESS_THRESHOLD = 0.90

COST_PER_INPUT_TOKEN  = 0.59 / 1_000_000
COST_PER_OUTPUT_TOKEN = 0.79 / 1_000_000

app = FastAPI(title="AI Writing Coach (Advanced)")

client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")


def log(data: dict) -> None:
    print(json.dumps(data), flush=True)


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

class JudgeRequest(BaseModel):
    question: str
    answer: str

class EvaluateRequest(BaseModel):
    question: str
    answer: str
    context: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "models": {"main": MAIN_MODEL, "judge": JUDGE_MODEL}}


@app.post("/chat")
async def chat(request: ChatRequest):
    request_id = uuid.uuid4().hex[:8]
    start = time.time()

    try:
        response = client.chat.completions.create(
            model=MAIN_MODEL,
            max_tokens=512,
            messages=[
                {"role": "system", "content": "You are a helpful writing coach."},
                {"role": "user",   "content": request.message},
            ],
        )
    except Exception as exc:
        log({"request_id": request_id, "endpoint": "/chat", "error": str(exc)})
        raise HTTPException(status_code=502, detail="LLM service unavailable.")

    in_tok  = response.usage.prompt_tokens
    out_tok = response.usage.completion_tokens

    log({
        "request_id":   request_id,
        "endpoint":     "/chat",
        "model":        MAIN_MODEL,
        "input_tokens":  in_tok,
        "output_tokens": out_tok,
        "latency_ms":   round((time.time() - start) * 1000),
        "cost_usd":     round(in_tok * COST_PER_INPUT_TOKEN + out_tok * COST_PER_OUTPUT_TOKEN, 6),
    })

    return {"reply": response.choices[0].message.content, "request_id": request_id}


@app.post("/judge")
async def judge(request: JudgeRequest):
    """
    LLM-as-Judge: score the answer on a 0-10 scale.
    Uses a cheaper, faster model (8b) as the judge.
    Rule: different model for judge than for generation.
    """
    request_id = uuid.uuid4().hex[:8]
    start = time.time()

    JUDGE_SYSTEM = """You are an expert writing evaluator. Score the answer 0-10.
Return ONLY valid JSON with no extra text:
{"score": <integer 0-10>, "reason": "<one sentence>", "pass": <true if score >= 7>}"""

    try:
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            max_tokens=200,
            temperature=0.1,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user",   "content": f"Question: {request.question}\n\nAnswer: {request.answer}"},
            ],
        )
        verdict = json.loads(response.choices[0].message.content.strip())
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Judge returned non-JSON response.")
    except Exception as exc:
        log({"request_id": request_id, "endpoint": "/judge", "error": str(exc)})
        raise HTTPException(status_code=502, detail="Judge service unavailable.")

    log({
        "request_id": request_id,
        "endpoint":   "/judge",
        "model":      JUDGE_MODEL,
        "latency_ms": round((time.time() - start) * 1000),
    })

    return {
        "score":      verdict.get("score"),
        "reason":     verdict.get("reason"),
        "pass":       verdict.get("pass"),
        "request_id": request_id,
    }


@app.post("/evaluate")
async def evaluate(request: EvaluateRequest):
    """
    RAGAS faithfulness evaluation.
    Checks: does the answer stay faithful to the provided context?
    Score >= 0.90 is considered passing.
    """
    # Import here so the app starts even if ragas is not installed
    # (students can see the other endpoints while troubleshooting RAGAS)
    try:
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import faithfulness
        from datasets import Dataset
        from langchain_openai import ChatOpenAI
        from ragas.llms import LangchainLLMWrapper
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"RAGAS not installed: {exc}")

    # Point RAGAS to Groq
    os.environ["OPENAI_API_KEY"]  = GROQ_API_KEY
    os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"

    faithfulness.llm = LangchainLLMWrapper(
        ChatOpenAI(
            model=MAIN_MODEL,
            openai_api_key=GROQ_API_KEY,
            openai_api_base="https://api.groq.com/openai/v1",
        )
    )

    dataset = Dataset.from_dict({
        "question":  [request.question],
        "answer":    [request.answer],
        "contexts":  [[request.context]],
    })

    try:
        scores = ragas_evaluate(dataset, metrics=[faithfulness])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"RAGAS evaluation failed: {exc}")

    score = float(round(scores.to_pandas()["faithfulness"].iloc[0], 3))

    return {
        "faithfulness": {
            "score":     score,
            "threshold": FAITHFULNESS_THRESHOLD,
            "pass":      bool(score >= FAITHFULNESS_THRESHOLD),
        }
    }
