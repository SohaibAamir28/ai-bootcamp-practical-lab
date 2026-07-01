# ─────────────────────────────────────────────────────────────────────────────
# DAY 1 — STEP 2: LLM-as-Judge
# Run as a standalone script: python day1/step2_llm_judge.py
#
# CONCEPT (explain this before showing code)
#   Problem: you have 10,000 AI responses — a human grading them takes weeks.
#   Solution: send each response to another LLM and ask it to score.
#             One API call per response. Same pattern scales to millions.
#
# RULES FROM THE SLIDES (point to each one as you write the prompt)
#   01  Define criteria   — never leave "quality" undefined
#   02  Require JSON      — free-text scoring is unreliable and hard to parse
#   03  Include context   — judge only what the AI could see
#   04  Use a DIFFERENT model  — avoids "I love my own output" bias
#   05  Calibrate first   — check 10–20 hand-scored examples before trusting it
# ─────────────────────────────────────────────────────────────────────────────
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Rule 04: use a smaller, different model for judging (faster + cheaper)
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# ── Rule 01 + 02: define criteria, require JSON ───────────────────────────────
JUDGE_SYSTEM = """You are an expert AI evaluator.

Score the AI response below from 0 to 10 using these three criteria:
- Accuracy: is the information factually correct?
- Completeness: does it fully answer the question?
- Faithfulness: does it stay within the provided context (no made-up facts)?

Return ONLY valid JSON — no extra text, no markdown fences:
{"score": 0-10, "reason": "one sentence", "pass": true/false}

A response "passes" when score >= 7.
"""


# ── Rule 03 + 04: include context, use a different (smaller) model ────────────
def judge(question: str, context: str, ai_answer: str) -> dict:
    """Score one AI response. Returns {"score": int, "reason": str, "pass": bool}."""
    result = client.chat.completions.create(
        model="llama-3.1-8b-instant",          # Rule 04: different, cheaper model
        max_tokens=256,
        temperature=0,                          # deterministic scoring
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": (
                f"Question: {question}\n\n"
                f"Context (what the AI was given): {context}\n\n"  # Rule 03
                f"AI Answer: {ai_answer}"
            )},
        ],
    )
    return json.loads(result.choices[0].message.content)


# ── Demo — run this file directly to see the judge in action ──────────────────
# TEACHING TIP: ask students to predict the score BEFORE you run it.

if __name__ == "__main__":
    CONTEXT = "Our return policy allows returns within 30 days of purchase with a valid receipt."

    print("-" * 60)
    print("Example 1 - GOOD answer (faithful to context)")
    print("-" * 60)
    good = judge(
        question="What is your return policy?",
        context=CONTEXT,
        ai_answer="You can return items within 30 days as long as you have your receipt.",
    )
    print(json.dumps(good, indent=2))

    print()

    print("-" * 60)
    print("Example 2 - BAD answer (makes up information)")
    print("-" * 60)
    bad = judge(
        question="What is your return policy?",
        context=CONTEXT,
        ai_answer="You can return anything at any time, no receipt needed, and get a full refund plus store credit.",
    )
    print(json.dumps(bad, indent=2))
