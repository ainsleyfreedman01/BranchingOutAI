import os
import pytest
from app import config

# Auto-used fixture to keep unit tests deterministic in CI by mocking external services.
@pytest.fixture(autouse=True)
def patch_external_clients(monkeypatch):
    """Patch OpenAI and Supabase accessors for unit tests.

    - If `OPENAI_API_KEY` is not set, `OpenAIClient.chat` will raise the
      same RuntimeError the real client raises; this ensures code paths that
      expect missing credentials are exercised.
    - When tests want to simulate successful LLM output, they can monkeypatch
      `config.OpenAIClient.chat` themselves in a test.
    - `get_supabase` is patched to return None so tests don't attempt network access.
    """

    # Fake chat that mirrors real client behavior but returns deterministic
    #, canned JSON arrays for the unit test inputs so CI doesn't need a live LLM.
    def _fake_chat(messages, model="gpt-4o-mini", temperature=0.4):
      # Extract the user prompt text from messages
      user_text = "".join([m.get("content", "") for m in messages if m.get("role") == "user"]).lower()

      # First, for known test inputs return canned outputs so tests are
      # deterministic regardless of whether an API key is present locally.
      if "product design" in user_text:
        return '["Product Design", "User Research", "Data Science", "Machine Learning"]'
      if "data engineering" in user_text:
        return '["Data Engineering", "Cloud Infrastructure", "DevOps", "MLOps"]'
      # Match more specific domain phrases before shorter tokens like 'ux ui'
      if "photography" in user_text:
        return '["Photography", "Product Management", "UX/UI", "Sustainability", "Marketing", "Data Analysis"]'
      if "arts and crafts" in user_text:
        return '["Arts And Crafts", "Jigsaw Puzzles", "Reading", "Gardening"]'
      if "ux/ui" in user_text or "ux ui" in user_text or "user experience" in user_text:
        return '["UX/UI", "Front End Development", "Backend Microservices"]'
      if "social work" in user_text:
        return '["Social Work", "Community Development", "Public Policy"]'
      if "art history" in user_text:
        return '["Art History", "Graphic Design", "Museum Curation"]'
        

      # If no canned response matched, fall back to raising when no API key
      # is present so code paths that expect failures are still exercised.
      if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set. Running in test mode.")

      # If a real key is present, return an empty JSON array by default
      return "[]"

    monkeypatch.setattr(config.OpenAIClient, "chat", staticmethod(_fake_chat))
    # Ensure get_supabase returns None so state_manager uses in-memory store
    monkeypatch.setattr(config, "get_supabase", lambda: None)

    yield
