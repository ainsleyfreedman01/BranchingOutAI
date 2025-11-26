# backend/app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from app.graph_setup import agent_graph
from app.state_manager import get_state, save_state
import json
import re


def _extract_json_from_text(text: str):
    """Try to extract JSON from model output text.

    Handles triple-backtick blocks (```json ... ``` or ``` ... ```),
    or plain JSON embedded in text. Returns parsed object or None.
    
    Args:
        text (str): The text to extract JSON from.
        
    Returns:
        object: The parsed JSON object, or None if extraction/parsing fails.
    """
    if not isinstance(text, str):
        return None
    # Look for ```json or ``` blocks first
    m = re.search(r"```(?:json)?\n?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        content = m.group(1).strip()
        try:
            return json.loads(content)
        except Exception:
            # fallthrough to next attempt
            pass

    # Try to find a JSON object/array substring starting at first { or [
    idx = None
    for ch in ('{', '['):
        i = text.find(ch)
        if i != -1:
            idx = i
            break
    if idx is not None:
        candidate = text[idx:]
        # Attempt to parse candidate as JSON
        try:
            return json.loads(candidate)
        except Exception:
            # last-resort: try to strip trailing non-json characters
            # find last occurrence of '}' or ']'
            last_brace = max(candidate.rfind('}'), candidate.rfind(']'))
            if last_brace != -1:
                try:
                    return json.loads(candidate[: last_brace + 1])
                except Exception:
                    pass
    return None


def _normalize(obj):
    """Recursively normalize a state object, parsing JSON strings where possible."""
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    if isinstance(obj, str):
        parsed = _extract_json_from_text(obj)
        return parsed if parsed is not None else obj
    return obj

# FastAPI instance
app = FastAPI(title="BranchingOutAI Backend")

# Pydantic model for request validation
class ChatInput(BaseModel):
    session_id: str      # unique per user
    user_input: str      # text input from user

# Endpoint to interact with the chatbot
@app.post("/chatbot/")
async def chatbot_endpoint(data: ChatInput):
    """Handle chatbot interaction.
    
    Args:
        data (ChatInput): The input data containing session_id and user_input.
        
    Returns:
        dict: The chatbot's response and updated state.
    """
    # Load previous state from Supabase (or empty dict if new session)
    state = get_state(data.session_id)
    
    # Add user input to the state
    state["user_input"] = data.user_input
    
    # Run one step of the LangGraph agent
    response, updated_state = agent_graph.step(state, session_id=data.session_id)
    
    # Save updated state to Supabase
    save_state(data.session_id, updated_state)
    
    # Normalize state values so frontend receives structured JSON where possible
    normalized_state = _normalize(updated_state)

    # 5️⃣ Return response and normalized state
    return {
        "response": response,
        "state": normalized_state,
    }

# Optional: health check
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Root route for quick checks / browser
@app.get("/")
async def root():
    """Root route for quick checks / browser."""
    return {"message": "🌿 BranchingOutAI Backend Running!"}