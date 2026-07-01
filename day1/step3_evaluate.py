# ─────────────────────────────────────────────────────────────────────────────
# DAY 1 — STEP 3: RAGAS /evaluate Endpoint
# Run: uvicorn day1.step3_evaluate:app --reload
#
# WHAT'S NEW vs step1_logging.py
#   + /evaluate  endpoint — runs the RAGAS faithfulness metric on any Q/A/context
#
# RAGAS METRIC USED
#   faithfulness ≥ 0.90  — did the answer make up anything not in the context?
#
# WHY EXPOSE /evaluate AS AN API?
#   QA teams can test documents without touching Python code.
#   Monitoring can call it on live responses to detect quality drops.
# ─────────────────────────────────────────────────────────────────────────────
import asyncio
import json
import os
import time
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Tell RAGAS to use Groq instead of OpenAI ──────────────────────────────────
# RAGAS talks to LLMs through LangChain, which reads these env vars.
os.environ["OPENAI_API_KEY"]  = os.getenv("GROQ_API_KEY", "")
os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"

from datasets import Dataset                          # noqa: E402
from ragas import evaluate as ragas_evaluate          # noqa: E402  renamed to avoid name clash
from ragas.metrics import faithfulness                # noqa: E402
from langchain_openai import ChatOpenAI               # noqa: E402
from ragas.llms import LangchainLLMWrapper            # noqa: E402

# Point RAGAS at Groq's llama model
_groq_llm = ChatOpenAI(
    model="llama-3.3-70b-versatile",
    openai_api_key=os.getenv("GROQ_API_KEY"),
    openai_api_base="https://api.groq.com/openai/v1",
    temperature=0,
)
faithfulness.llm = LangchainLLMWrapper(_groq_llm)

app = FastAPI(title="AI Writing Coach")
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

COST_PER_INPUT_TOKEN  = 0.59 / 1_000_000
COST_PER_OUTPUT_TOKEN = 0.79 / 1_000_000
FAITHFULNESS_THRESHOLD = 0.90


def log(data: dict) -> None:
    print(json.dumps(data))


# ── Request models ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class EvaluateRequest(BaseModel):
    question: str
    answer:   str
    contexts: list[str]   # the document chunks retrieved to produce the answer


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest):
    request_id = uuid.uuid4().hex[:8]
    start = time.time()

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=512,
        messages=[
            {"role": "system", "content": "You are a helpful writing coach. Improve the user's writing clearly and concisely."},
            {"role": "user",   "content": request.message},
        ],
    )

    input_tokens  = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    log({
        "request_id":    request_id,
        "endpoint":      "/chat",
        "model":         "llama-3.3-70b-versatile",
        "input_tokens":   input_tokens,
        "output_tokens":  output_tokens,
        "latency_ms":    round((time.time() - start) * 1000),
        "cost_usd":      round(
            input_tokens  * COST_PER_INPUT_TOKEN +
            output_tokens * COST_PER_OUTPUT_TOKEN,
            6,
        ),
    })

    return {"reply": response.choices[0].message.content, "request_id": request_id}


@app.post("/evaluate")
async def evaluate_endpoint(request: EvaluateRequest):
    """
    Run RAGAS faithfulness on a question/answer/context triple.

    faithfulness measures: did the answer make up anything not in the context?
    Score of 1.0 = fully faithful. Score of 0.0 = completely hallucinated.
    """
    # Build a single-row HuggingFace Dataset (RAGAS expects this format)
    dataset = Dataset.from_dict({
        "question": [request.question],
        "answer":   [request.answer],
        "contexts": [request.contexts],   # list of lists — one list of chunks per row
    })

    # ragas_evaluate() is synchronous — run it in a thread so FastAPI stays responsive
    loop = asyncio.get_running_loop()
    try:
        scores = await loop.run_in_executor(
            None,
            lambda: ragas_evaluate(dataset, metrics=[faithfulness]),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Cast to Python native types — numpy.bool_ and numpy.float64 are not JSON-serializable
    score = float(round(scores.to_pandas()["faithfulness"].iloc[0], 3))

    return {
        "faithfulness": {
            "score":     score,
            "threshold": FAITHFULNESS_THRESHOLD,
            "pass":      bool(score >= FAITHFULNESS_THRESHOLD),
        }
    }
