from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.langgraph_agent.graph_setup import setup_graph
from app.langgraph_agent.state_manager import StateManager

# Initialize FastAPI app
app = FastAPI(title="BranchingOutAI Backend")

# Allow frontend to call the backend (important for Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict to your frontend domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize graph and state
graph = setup_graph()
state_manager = StateManager()

@app.get("/")
def root():
    return {"message": "🌿 BranchingOutAI Backend Running!"}

@app.post("/chatbot/")
async def chatbot(request: Request):
    """
    Handles chat requests from the frontend.
    Passes input through the LangGraph agent.
    """
    data = await request.json()
    user_id = data.get("user_id", "default_user")
    user_input = data.get("message", "")

    # Retrieve user's state
    state = state_manager.get_state(user_id)

    # Determine current node (very simple logic for now)
    if "interests" not in state:
        current_node = graph.get_node("interests_node")
    elif "industry" not in state:
        current_node = graph.get_node("industry_node")
    elif "selected_job" not in state:
        current_node = graph.get_node("job_node")
    else:
        current_node = graph.get_node("skills_node")

    # Run the current node
    response = current_node.process(user_input, state)

    # Update user state
    updated_state = state_manager.update_state(user_id, state)

    return {
        "response": response,
        "state": updated_state
    }