# ─────────────────────────────────────────────────────────────────────────────
# STARTER APP — what students receive at the beginning of Day 1
# Run: uvicorn starter.main:app --reload
#
# Two endpoints:
#   GET  /health  →  liveness check (no AI call)
#   POST /chat    →  send a message, get a writing suggestion back
# ─────────────────────────────────────────────────────────────────────────────
import os
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Writing Coach")

# Groq uses the OpenAI SDK — same interface, faster and free tier available
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)


class ChatRequest(BaseModel):
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=512,
        messages=[
            {"role": "system", "content": "You are a helpful writing coach. Improve the user's writing clearly and concisely."},
            {"role": "user",   "content": request.message},
        ],
    )
    return {"reply": response.choices[0].message.content}
