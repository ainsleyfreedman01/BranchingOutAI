# backend/app/main.py
from fastapi import FastAPI, Header
from pydantic import BaseModel
from app.graph_setup import agent_graph
from app.state_manager import get_state, save_state
from app.utils.normalization import normalize_state

# FastAPI instance
app = FastAPI(title="BranchingOutAI Backend")

# Pydantic model for request validation
class ChatInput(BaseModel):
    session_id: str      # unique per user
    user_input: str      # text input from user

# Endpoint to interact with the chatbot
@app.post("/chatbot/")
async def chatbot_endpoint(data: ChatInput, x_user_id: str | None = Header(None)):
    """Handle chatbot interaction.
    
    Args:
        data (ChatInput): The input data containing session_id and user_input.
        
    Returns:
        dict: The chatbot's response and updated state.
    """
    # Load previous state from Supabase (or empty dict if new session)
    state = get_state(data.session_id, user_id=x_user_id)
    
    # Add user input to the state
    state["user_input"] = data.user_input
    
    # Run one step of the LangGraph agent
    response, updated_state = agent_graph.step(state, session_id=data.session_id)
    
    # Save updated state to Supabase
    save_state(data.session_id, updated_state, user_id=x_user_id)
    
    # Normalize state values so frontend receives structured JSON where possible
    normalized_state = normalize_state(updated_state)

    # 5️⃣ Return response and normalized state
    return {
        "response": response,
        "state": normalized_state,
    }


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Return the saved session state for a given session_id."""
    state = get_state(session_id)
    # ensure returned state is normalized
    normalized = normalize_state(state)
    return {"session_id": session_id, "state": normalized}

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