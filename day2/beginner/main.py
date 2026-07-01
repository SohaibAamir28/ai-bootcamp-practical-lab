# =============================================================================
# DAY 2 — BEGINNER LEVEL
# The App We Will Put Inside Docker
#
# CONCEPT: "Works on my machine" is not enough.
#   Your app works locally. Your teammate's machine has Python 3.9.
#   The server has Python 3.8 and a different OS.
#   The API keys are missing. The library versions differ.
#   Docker solves all of this by packaging EVERYTHING together.
#
# This file is identical to the Day 1 starter. Today we focus on
# how to wrap it in a container — not change the app itself.
# =============================================================================
import os
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


class ChatRequest(BaseModel):
    message: str


# Docker will call this endpoint every 30s to check the app is alive
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
