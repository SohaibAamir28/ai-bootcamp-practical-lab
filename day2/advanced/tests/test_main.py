"""
Advanced tests — mock LLM calls so CI runs fast and free.
Tests cover: validation, error simulation, response shape, LLM-judge parsing.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Provide a dummy key so the app doesn't crash on import
os.environ.setdefault("GROQ_API_KEY", "test-key")

from unittest.mock import MagicMock, patch
import json
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "models" in data


# ── Chat endpoint validation ──────────────────────────────────────────────────

def test_chat_missing_field():
    r = client.post("/chat", json={})
    assert r.status_code == 422

def test_chat_empty_body():
    r = client.post("/chat")
    assert r.status_code == 422


# ── Chat with mocked LLM ──────────────────────────────────────────────────────

def _make_mock_response(content: str, input_tokens=10, output_tokens=20):
    """Build a minimal OpenAI-style response mock."""
    choice  = MagicMock()
    choice.message.content = content

    usage = MagicMock()
    usage.prompt_tokens     = input_tokens
    usage.completion_tokens = output_tokens

    response = MagicMock()
    response.choices = [choice]
    response.usage   = usage
    return response


@patch("main.client.chat.completions.create")
def test_chat_returns_reply_and_request_id(mock_create):
    mock_create.return_value = _make_mock_response("Here is your improved writing.")
    r = client.post("/chat", json={"message": "Fix my essay."})
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data
    assert "request_id" in data
    assert len(data["request_id"]) == 8


@patch("main.client.chat.completions.create")
def test_chat_llm_failure_returns_502(mock_create):
    """When the LLM throws, we should get 502 not 500."""
    mock_create.side_effect = Exception("Groq timeout")
    r = client.post("/chat", json={"message": "Hello"})
    assert r.status_code == 502


# ── Judge endpoint ────────────────────────────────────────────────────────────

def test_judge_missing_fields():
    r = client.post("/judge", json={"question": "What is Python?"})
    assert r.status_code == 422


@patch("main.client.chat.completions.create")
def test_judge_parses_json_response(mock_create):
    verdict = {"score": 8, "reason": "Clear and accurate.", "pass": True}
    mock_create.return_value = _make_mock_response(json.dumps(verdict))
    r = client.post("/judge", json={"question": "What is Python?", "answer": "A programming language."})
    assert r.status_code == 200
    data = r.json()
    assert data["score"] == 8
    assert data["pass"] is True
    assert "reason" in data


@patch("main.client.chat.completions.create")
def test_judge_bad_json_returns_502(mock_create):
    """If the judge returns non-JSON, we should get a clean 502."""
    mock_create.return_value = _make_mock_response("Sorry I cannot score this.")
    r = client.post("/judge", json={"question": "Q", "answer": "A"})
    assert r.status_code == 502
