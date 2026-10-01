# backend/app/main.py
import os
from typing import NamedTuple

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.graph_setup import agent_graph
from app.rate_limiter import RateLimitUnavailable, SupabaseRateLimiter
from app.state_manager import StatePersistenceUnavailable, get_state, save_state
from app.utils.normalization import normalize_state

# FastAPI instance
app = FastAPI(title="BranchingOutAI Backend")
bearer_scheme = HTTPBearer(auto_error=False)

_allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


rate_limiter = SupabaseRateLimiter()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(StatePersistenceUnavailable)
async def state_persistence_unavailable_handler(request: Request, exc: StatePersistenceUnavailable):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Session storage is unavailable"},
    )

# Pydantic model for request validation
class ChatInput(BaseModel):
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    user_input: str = Field(min_length=1, max_length=4000)


class AuthenticatedUser(NamedTuple):
    """Server-verified identity plus the raw token, so downstream Supabase
    calls can authenticate as this user and satisfy Row Level Security."""

    id: str
    access_token: str


def authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """Validate the Supabase access token and return its server-trusted user ID."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    from app.config import get_supabase

    client = get_supabase()
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication is unavailable")
    try:
        user_response = client.auth.get_user(credentials.credentials)
        user = getattr(user_response, "user", None)
        user_id = getattr(user, "id", None)
    except Exception:
        user_id = None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")
    return AuthenticatedUser(id=str(user_id), access_token=credentials.credentials)


def enforce_rate_limit(
    request: Request,
    auth: AuthenticatedUser = Depends(authenticated_user),
) -> None:
    """Limit expensive authenticated calls before they reach the AI graph."""
    try:
        limit = max(1, int(os.getenv("API_RATE_LIMIT_REQUESTS", "30")))
        window_seconds = max(1, int(os.getenv("API_RATE_LIMIT_WINDOW_SECONDS", "60")))
        ip_limit = max(limit, int(os.getenv("API_RATE_LIMIT_IP_REQUESTS", str(limit * 2))))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rate limiting is unavailable") from exc
    if limit > 100000 or ip_limit > 100000 or window_seconds > 86400:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rate-limit settings are out of range")

    client_host = request.client.host if request.client else "unknown"
    try:
        user_allowed, retry_after = rate_limiter.allow(f"user:{auth.id}", limit, window_seconds)
        ip_allowed, ip_retry_after = rate_limiter.allow(f"ip:{client_host}", ip_limit, window_seconds)
    except RateLimitUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiting is unavailable",
        ) from exc
    if not user_allowed or not ip_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(max(retry_after, ip_retry_after))},
        )

# Endpoint to interact with the chatbot
@app.post("/chatbot/", dependencies=[Depends(enforce_rate_limit)])
def chatbot_endpoint(data: ChatInput, auth: AuthenticatedUser = Depends(authenticated_user)):
    """Handle chatbot interaction.
    
    Args:
        data (ChatInput): The input data containing session_id and user_input.
        
    Returns:
        dict: The chatbot's response and updated state.
    """
    # Load previous state from Supabase (or empty dict if new session)
    state = get_state(data.session_id, user_id=auth.id, access_token=auth.access_token)
    
    # Add user input to the state
    state["user_input"] = data.user_input

    # If new input arrives, reset dependent fields so the graph recomputes from interests
    for k in [
        "interests",
        "industries",
        "selected_industry",
        "job_families",
        "selected_job_family",
        "jobs",
        "selected_job",
        "skills",
    ]:
        if k in state:
            del state[k]
    
    # Run one step of the LangGraph agent
    # Run step without loading from storage inside nodes to avoid reusing stale fields
    response, updated_state = agent_graph.step(state, session_id=None)
    
    # Save updated state to Supabase
    save_state(data.session_id, updated_state, user_id=auth.id, access_token=auth.access_token)
    
    # Normalize state values so frontend receives structured JSON where possible
    normalized_state = normalize_state(updated_state)

    # Return response and normalized state
    return {
        "response": response,
        "state": normalized_state,
    }


@app.get("/session/{session_id}", dependencies=[Depends(enforce_rate_limit)])
def get_session(session_id: str, auth: AuthenticatedUser = Depends(authenticated_user)):
    """Return the saved session state for a given session_id."""
    state = get_state(session_id, user_id=auth.id, access_token=auth.access_token)
    # ensure returned state is normalized
    normalized = normalize_state(state)
    return {"session_id": session_id, "state": normalized}


@app.delete("/account", dependencies=[Depends(enforce_rate_limit)])
def delete_account(auth: AuthenticatedUser = Depends(authenticated_user)):
    """Delete the authenticated user's saved data and Supabase account."""
    from app.config import get_supabase_admin

    admin_client = get_supabase_admin()
    if admin_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Account deletion is unavailable")
    try:
        admin_client.auth.admin.delete_user(auth.id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to delete account") from exc
    return {"status": "deleted"}

# Optional: health check
@app.get("/health")
async def health():
    """Liveness check; dependency availability is reported by /ready."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Check that the service-role database endpoint and limiter table are ready."""
    from app.config import get_supabase_admin

    client = get_supabase_admin()
    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase is unavailable")
    try:
        client.table("api_rate_limits").select("rate_key").limit(1).execute()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase is unavailable") from exc
    return {"status": "ready"}


# Root route for quick checks / browser
@app.get("/")
async def root():
    """Root route for quick checks / browser."""
    return {"message": "🌿 BranchingOutAI Backend Running!"}