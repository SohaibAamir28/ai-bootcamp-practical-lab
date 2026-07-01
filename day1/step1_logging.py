# ─────────────────────────────────────────────────────────────────────────────
# DAY 1 — STEP 1: Structured JSON Logging
# Run: uvicorn day1.step1_logging:app --reload
#
# WHAT CHANGES from starter/main.py
#   BEFORE  →  no log at all (blind — you have no idea what happened)
#   AFTER   →  print(json.dumps({...}))   every field named, machine-readable
#
# HOW TO DEMO
#   Terminal 1: run this server
#   Terminal 2: curl -X POST http://localhost:8000/chat \
#               -H "Content-Type: application/json" \
#               -d '{"message":"Fix my grammer"}'
#   Show the JSON line in Terminal 1.
#   Ask: "Can you grep this for all requests over 2000ms? Yes. print('Done')? No."
# ─────────────────────────────────────────────────────────────────────────────

# Linux/macOS curl:
#   curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"Fix my grammer"}'
# Windows PowerShell command:
#   Invoke-RestMethod -Uri http://localhost:8000/chat -Method Post -ContentType "application/json" -Body '{"message":"Fix my grammer"}'
# Or Windows curl.exe:
#   curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"Fix my grammer\"}"
import json
import os
import time
import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Writing Coach")
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# Groq llama-3.3-70b-versatile approximate pricing
COST_PER_INPUT_TOKEN  = 0.59 / 1_000_000
COST_PER_OUTPUT_TOKEN = 0.79 / 1_000_000


# ── The only new code: one helper that prints a JSON line ─────────────────────

def log(data: dict) -> None:
    """Structured log — one JSON object per line to stdout."""
    print(json.dumps(data), flush=True)


# ── Same endpoints as starter, /chat now emits a structured log ───────────────

class ChatRequest(BaseModel):
    message: str


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

    # ── Structured log ─────────────────────────────────────────────────────────
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
