from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from app.state_manager import state_manager
from app.graph_setup import graph_manager

app = FastAPI()

# Allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class ChatRequest(BaseModel):
    session_id: str # Unique session identifier
    user_input: str # User's input text

@app.post("/chatbot/") # Endpoint for chatbot interaction
def chatbot(req: ChatRequest):
    """Handles chatbot requests and routes through graph nodes based on session state.
    
    Args:
        req (ChatRequest): The incoming request with session ID and user input.
    """
    state = state_manager.get_state(req.session_id)

    # Determine which node to run next
    if "interests" not in state:
        node = graph_manager.get_node("interests_node")
    elif "industry" not in state:
        node = graph_manager.get_node("industry_node")
    elif "selected_job" not in state:
        node = graph_manager.get_node("job_node")
    else: # All info gathered, suggest skills
        node = graph_manager.get_node("skills_node")

    # Run the node (process input and update state)
    output, updated_state = node.process(req.user_input, state)

    # Save the state for the next request
    state_manager.save_state(req.session_id, updated_state)

    return { # Return chatbot response and updated state
        "response": output,
        "state": updated_state
    }