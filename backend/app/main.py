from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import route modules from the package-local `app.routes`. Because this
# `main.py` lives at `backend/app/main.py`, package-relative imports work
# consistently whether you run `uvicorn app.main:app` from inside
# `backend/` or `uvicorn backend.app.main:app` from the repository root.
from .langgraph_agent import chat, jobs, user


app = FastAPI(title="BranchingOutAI Backend")

# CORS setup (allow frontend to talk to backend)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # for dev; restrict in prod
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Include route modules
app.include_router(chat.router, prefix="/chatbot")
app.include_router(jobs.router, prefix="/jobs")
app.include_router(user.router, prefix="/user")


@app.get("/", tags=["health"])
async def root():
	"""Simple health check so the root path returns a friendly JSON."""
	return {"status": "ok", "service": "BranchingOutAI Backend"}


@chat.router.post("/")
async def get_chat_reply(request: chat.ChatRequest):
	return chat.ChatResponse(reply=f"You said: {request.message}")
