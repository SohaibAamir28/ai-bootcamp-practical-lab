# =============================================================================
# DAY 2 — INTERMEDIATE LEVEL
# App with Structured Logging + Error Handling
#
# NEW vs Beginner:
#   + Structured JSON logging  (every request gets logged with full details)
#   + Error handling           (LLM failures return clean 502 responses)
#   + request_id               (trace any request through your logs)
#
# DOCKER CONNECTION:
#   Everything printed here is captured by Docker.
#   Run: docker logs <container-id>   to see the structured JSON lines.
#   This is how teams debug production issues without SSH-ing into servers.
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

app = FastAPI(title="AI Writing Coach")

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

COST_PER_INPUT_TOKEN  = 0.59 / 1_000_000
COST_PER_OUTPUT_TOKEN = 0.79 / 1_000_000


def log(data: dict) -> None:
    """
    One JSON object per line → stdout.
    Docker captures stdout automatically.
    Read it with: docker logs <container-id>
    Filter it with: docker logs <container-id> | grep '"latency_ms"'
    """
    print(json.dumps(data), flush=True)


class ChatRequest(BaseModel):
    message: str


@app.get("/health")
def health():
    """
    Docker HEALTHCHECK pings this every 30 seconds.
    If it fails 3 times in a row, Docker marks the container as unhealthy
    and removes it from the load balancer.
    """
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest):
    request_id = uuid.uuid4().hex[:8]
    start = time.time()

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=512,
            messages=[
                {"role": "system", "content": "You are a helpful writing coach. Improve the user's writing clearly and concisely."},
                {"role": "user",   "content": request.message},
            ],
        )
    except Exception as exc:
        # Log the error with the same request_id so you can trace it
        log({"request_id": request_id, "error": str(exc), "latency_ms": round((time.time() - start) * 1000)})
        raise HTTPException(status_code=502, detail="LLM service unavailable. Try again.")

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
