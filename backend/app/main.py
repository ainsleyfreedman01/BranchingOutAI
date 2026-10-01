# backend/app/main.py
import os
from contextlib import asynccontextmanager
from typing import NamedTuple
from urllib.parse import urlsplit

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

def validate_runtime_settings() -> None:
    """Reject unsafe or incomplete configuration in production mode."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "test", "production"}:
        raise RuntimeError("APP_ENV must be development, test, or production")
    if app_env != "production":
        return

    required = ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "CORS_ALLOWED_ORIGINS")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        raise RuntimeError(f"Missing required production settings: {', '.join(missing)}")

    supabase_url = urlsplit(os.environ["SUPABASE_URL"])
    if supabase_url.scheme != "https" or not supabase_url.hostname:
        raise RuntimeError("SUPABASE_URL must use HTTPS in production")

    origins = [origin.strip() for origin in os.environ["CORS_ALLOWED_ORIGINS"].split(",") if origin.strip()]
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            origin == "*"
            or parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or parsed.hostname.lower() == "localhost"
            or parsed.hostname.lower().endswith(".localhost")
        ):
            raise RuntimeError("CORS_ALLOWED_ORIGINS must contain only exact HTTPS frontend origins")


@asynccontextmanager
async def lifespan(application):
    validate_runtime_settings()
    yield


# FastAPI instance
app = FastAPI(title="BranchingOutAI Backend", lifespan=lifespan)
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
        if os.getenv("APP_ENV", "development").strip().lower() == "production" and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response


app.add_middleware(SecurityHeadersMiddleware)


class RequestBodyLimitMiddleware:
    def __init__(self, app, max_bytes: int = 64 * 1024):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    await JSONResponse(
                        status_code=413,
                        content={"detail": "Request body is too large"},
                    )(scope, receive, send)
                    return
            except ValueError:
                await JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid Content-Length"},
                )(scope, receive, send)
                return

        bytes_received = 0

        async def receive_limited():
            nonlocal bytes_received
            message = await receive()
            if message["type"] == "http.request":
                bytes_received += len(message.get("body", b""))
                if bytes_received > self.max_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, receive_limited, send)
        except RequestBodyTooLarge:
            await JSONResponse(
                status_code=413,
                content={"detail": "Request body is too large"},
            )(scope, receive, send)


class RequestBodyTooLarge(Exception):
    pass


app.add_middleware(RequestBodyLimitMiddleware)


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


def _rate_limit_settings() -> tuple[int, int, int]:
    try:
        limit = max(1, int(os.getenv("API_RATE_LIMIT_REQUESTS", "30")))
        window_seconds = max(1, int(os.getenv("API_RATE_LIMIT_WINDOW_SECONDS", "60")))
        ip_limit = max(limit, int(os.getenv("API_RATE_LIMIT_IP_REQUESTS", str(limit * 2))))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rate limiting is unavailable") from exc
    if limit > 100000 or ip_limit > 100000 or window_seconds > 86400:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Rate-limit settings are out of range")
    return limit, window_seconds, ip_limit


def _check_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    try:
        allowed, retry_after = rate_limiter.allow(key, limit, window_seconds)
    except RateLimitUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiting is unavailable",
        ) from exc
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def enforce_ip_rate_limit(request: Request) -> None:
    """Apply the shared client-IP quota before bearer-token verification."""
    _, window_seconds, ip_limit = _rate_limit_settings()
    client_host = request.client.host if request.client else "unknown"
    _check_rate_limit(f"ip:{client_host}", ip_limit, window_seconds)


def enforce_rate_limit(auth: AuthenticatedUser = Depends(authenticated_user)) -> None:
    """Apply the shared authenticated-user quota before expensive operations."""
    limit, window_seconds, _ = _rate_limit_settings()
    _check_rate_limit(f"user:{auth.id}", limit, window_seconds)

# Endpoint to interact with the chatbot
@app.post("/chatbot/", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
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


@app.get("/session/{session_id}", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def get_session(session_id: str, auth: AuthenticatedUser = Depends(authenticated_user)):
    """Return the saved session state for a given session_id."""
    state = get_state(session_id, user_id=auth.id, access_token=auth.access_token)
    # ensure returned state is normalized
    normalized = normalize_state(state)
    return {"session_id": session_id, "state": normalized}


@app.delete("/account", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
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