import os
from typing import Optional
from dotenv import load_dotenv

# External libs are optional at import time; handle gracefully
try:
    import openai
except Exception:  # pragma: no cover - optional dependency at import
    openai = None  # type: ignore

try:
    from supabase import create_client, Client
except Exception:  # pragma: no cover - optional dependency at import
    create_client = None  # type: ignore
    Client = None  # type: ignore


load_dotenv()


# ---- OpenAI configuration ----
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


class OpenAIClient:
    """Thin wrapper around OpenAI chat API with lazy checks."""

    @staticmethod
    def chat(messages, model="gpt-4o-mini", temperature=0.4):
        """Thin wrapper around OpenAI chat API with lazy checks.
        Args:
            messages (list): List of message dicts for chat completion.
            model (str): OpenAI model to use.
            temperature (float): Sampling temperature.
        Returns:
            str: The content of the assistant's reply."""
        if openai is None:
            raise RuntimeError("openai package not installed. Run 'pip install openai'.")
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not set. Add it to your environment or .env file.")
        # Support both the new openai.OpenAI client (openai>=1.0) and the
        # older openai.ChatCompletion API. Prefer the new client when available.
        try:
            # New-style client
            OpenAIClass = getattr(openai, "OpenAI", None)
            if OpenAIClass is not None:
                client = OpenAIClass(api_key=OPENAI_API_KEY)
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )
                # resp.choices[0].message may be an object with .content
                msg = resp.choices[0].message
                if hasattr(msg, "content"):
                    return msg.content
                # If it's dict-like, try keyed access
                try:
                    return msg["content"]
                except Exception:
                    # As a last resort, try to stringify the choice
                    try:
                        return str(msg)
                    except Exception:
                        return ""

            # Fallback to legacy API
            openai.api_key = OPENAI_API_KEY
            resp = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content
        except Exception:
            # Re-raise with clearer message
            raise


client = OpenAIClient()


# ---- Supabase configuration (lazy) ----
def get_supabase() -> Optional[object]:
    """Create and return a Supabase client if env vars are set; else None.

    Avoids raising during module import so the app can boot without Supabase.
    """
    if create_client is None:
        return None
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)