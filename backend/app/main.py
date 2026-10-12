# backend/app/main.py
import os
import logging
from contextlib import asynccontextmanager
from typing import Any, NamedTuple
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.graph_setup import agent_graph
from app.career_tree import CHILD_TYPES, delete_tree_node, expand_tree, extract_interest_labels, initialize_tree, update_view_state, upgrade_tree_generation
from app.rate_limiter import RateLimitUnavailable, SupabaseRateLimiter
from app.state_manager import StatePersistenceUnavailable, get_account_graph_session, get_state, save_state
from app.utils.normalization import normalize_state
from app.career_chat import guide_message, apply_changes, explain_node, NodeExplanationNotAllowed
from app.live_jobs import search_jobs, JobSearchUnavailable
from typing import Literal

logger = logging.getLogger(__name__)

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
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
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


class CareerTreeInitializeInput(BaseModel):
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    root_label: str = Field(min_length=1, max_length=120)
    profile_context: dict[str, Any] = Field(default_factory=dict)
    user_input: str | None = Field(default=None, max_length=4000)


class CareerTreeExpandInput(BaseModel):
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    node_id: str = Field(min_length=1, max_length=160)


class CareerTreeViewInput(BaseModel):
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    selected_node_id: str | None = Field(default=None, max_length=160)
    expanded_node_ids: list[str] = Field(max_length=100)


class CareerTreeResetInput(BaseModel):
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


class CareerGuideInput(CareerTreeResetInput):
    message: str = Field(min_length=1, max_length=4000)
    selected_node_id: str | None = Field(default=None, max_length=160)


class CareerChangesInput(CareerTreeResetInput):
    proposal_id: str = Field(min_length=1, max_length=64)
    accept: bool


class CareerJobsInput(CareerTreeExpandInput):
    country: Literal["US"] = "US"
    location: str = Field(default="", max_length=120)
    workplace: Literal["remote", "local"]


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

    chat_history = state.get("chat_history")
    if not isinstance(chat_history, list):
        chat_history = []
        previous_input = state.get("user_input")
        previous_response = state.get("assistant_response")
        if isinstance(previous_input, str) and previous_input:
            chat_history.append({"role": "user", "content": previous_input})
        if isinstance(previous_response, str) and previous_response:
            chat_history.append({"role": "assistant", "content": previous_response})
    chat_history = [
        turn for turn in chat_history
        if isinstance(turn, dict)
        and turn.get("role") in ("user", "assistant")
        and isinstance(turn.get("content"), str)
    ]
    chat_history.append({"role": "user", "content": data.user_input})
    
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

    chat_history.append({"role": "assistant", "content": str(response)})
    updated_state["chat_history"] = chat_history
    updated_state["assistant_response"] = str(response)
    
    # Save updated state to Supabase
    save_state(data.session_id, updated_state, user_id=auth.id, access_token=auth.access_token)
    
    # Normalize state values so frontend receives structured JSON where possible
    normalized_state = normalize_state(updated_state)

    # Return response and normalized state
    return {
        "response": response,
        "state": normalized_state,
    }


def upgrade_saved_career_tree(session_id: str, state: dict[str, Any], auth: AuthenticatedUser) -> dict[str, Any]:
    tree = state.get("career_tree")
    if isinstance(tree, dict):
        upgraded = upgrade_tree_generation(tree)
        if upgraded is not tree:
            state = {**state, "career_tree": upgraded}
            save_state(session_id, state, user_id=auth.id, access_token=auth.access_token)
    return state


@app.get("/career-tree/session", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def get_account_career_session(auth: AuthenticatedUser = Depends(authenticated_user)):
    session_id, state = get_account_graph_session(auth.id, auth.access_token)
    state = upgrade_saved_career_tree(session_id, state, auth)
    return {"session_id": session_id, "state": normalize_state(state)}


@app.get("/session/{session_id}", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def get_session(session_id: str, auth: AuthenticatedUser = Depends(authenticated_user)):
    """Return the saved session state for a given session_id."""
    state = get_state(session_id, user_id=auth.id, access_token=auth.access_token)
    state = upgrade_saved_career_tree(session_id, state, auth)
    # ensure returned state is normalized
    normalized = normalize_state(state)
    return {"session_id": session_id, "state": normalized}


@app.post("/career-tree/initialize", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def initialize_career_tree(data: CareerTreeInitializeInput, auth: AuthenticatedUser = Depends(authenticated_user)):
    state = get_state(data.session_id, user_id=auth.id, access_token=auth.access_token)
    state = upgrade_saved_career_tree(data.session_id, state, auth)
    existing_tree = state.get("career_tree")
    if isinstance(existing_tree, dict):
        return {"tree": existing_tree, "response": state.get("assistant_response", "Your career map is ready to explore.")}

    if data.user_input:
        from app.config import client

        try:
            interests = extract_interest_labels(data.user_input, data.profile_context, client.chat)
        except ValueError as exc:
            logger.warning("Initial career interest extraction failed validation")
            raise HTTPException(502, "The guide could not identify your interests. Please describe your goal and try again.") from exc
        except Exception as exc:
            logger.exception("Initial career interest extraction failed")
            raise HTTPException(502, "The career guide is temporarily unavailable. Please try again.") from exc
        state["user_input"] = data.user_input
        response = "I found these interests to start your career map. Select one to explore connected industries."
        history = state.get("chat_history") if isinstance(state.get("chat_history"), list) else []
        history.extend([
            {"role": "user", "content": data.user_input},
            {"role": "assistant", "content": response},
        ])
        state["chat_history"] = history[-40:]
        state["assistant_response"] = response
    else:
        interests = state.get("interests", [])
        if not isinstance(interests, list) or not interests:
            interests = data.profile_context.get("interests", [])
        response = state.get("assistant_response", "Your career map is ready to explore.")
    if not isinstance(interests, list) or not interests:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Share your interests before creating your career tree")

    state["interests"] = interests[:12]
    profile_context = {
        "interests": interests[:12],
        "industries": state.get("industries", [])[:12] if isinstance(state.get("industries"), list) else [],
        "skills": state.get("skills", [])[:12] if isinstance(state.get("skills"), list) else [],
        "starting_input": data.user_input,
        **data.profile_context,
    }
    state["career_tree"] = initialize_tree(data.root_label, interests, profile_context)
    save_state(data.session_id, state, user_id=auth.id, access_token=auth.access_token)
    return {"tree": normalize_state(state["career_tree"]), "response": response}


@app.post("/career-tree/expand", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def expand_career_tree(data: CareerTreeExpandInput, auth: AuthenticatedUser = Depends(authenticated_user)):
    state = get_state(data.session_id, user_id=auth.id, access_token=auth.access_token)
    state = upgrade_saved_career_tree(data.session_id, state, auth)
    tree = state.get("career_tree")
    if not isinstance(tree, dict):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Create your career tree before expanding a branch")
    node = next((item for item in tree.get("nodes", []) if item.get("id") == data.node_id), None)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career node not found")
    if node.get("type") not in CHILD_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This node has no expandable branch")

    from app.config import client

    try:
        updated_tree = expand_tree(tree, data.node_id, client.chat)
    except ValueError as exc:
        logger.warning("Career branch generation failed validation for node %s", data.node_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not generate sufficiently relevant suggestions for this branch. Please try again.") from exc
    except Exception as exc:
        logger.exception("Career branch generation failed for node %s", data.node_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Career recommendations are temporarily unavailable") from exc
    state["career_tree"] = updated_tree
    save_state(data.session_id, state, user_id=auth.id, access_token=auth.access_token)
    return {"tree": normalize_state(updated_tree)}


@app.post("/career-tree/delete", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def delete_career_tree_node(data: CareerTreeExpandInput, auth: AuthenticatedUser = Depends(authenticated_user)):
    state = get_state(data.session_id, user_id=auth.id, access_token=auth.access_token)
    state = upgrade_saved_career_tree(data.session_id, state, auth)
    tree = state.get("career_tree")
    if not isinstance(tree, dict):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Create your career tree before deleting a node")
    try:
        updated_tree = delete_tree_node(tree, data.node_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career node not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    state["career_tree"] = updated_tree
    state["interests"] = [node["label"] for node in updated_tree["nodes"] if node["type"] == "interest"]
    save_state(data.session_id, state, user_id=auth.id, access_token=auth.access_token)
    return {"tree": normalize_state(updated_tree)}


@app.put("/career-tree/state", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def save_career_tree_view(data: CareerTreeViewInput, auth: AuthenticatedUser = Depends(authenticated_user)):
    state = get_state(data.session_id, user_id=auth.id, access_token=auth.access_token)
    state = upgrade_saved_career_tree(data.session_id, state, auth)
    tree = state.get("career_tree")
    if not isinstance(tree, dict):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Create your career tree before saving its view")
    state["career_tree"] = update_view_state(tree, data.selected_node_id, data.expanded_node_ids)
    save_state(data.session_id, state, user_id=auth.id, access_token=auth.access_token)
    return {"tree": normalize_state(state["career_tree"])}


@app.post("/career-tree/reset", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def reset_career_tree(data: CareerTreeResetInput, auth: AuthenticatedUser = Depends(authenticated_user)):
    state = get_state(data.session_id, user_id=auth.id, access_token=auth.access_token)
    for key in (
        "career_tree",
        "pending_career_changes",
        "interests",
        "industries",
        "career_paths",
        "selected_industry",
        "job_families",
        "selected_job_family",
        "jobs",
        "selected_job",
        "skills",
        "user_input",
        "assistant_response",
        "chat_history",
    ):
        state.pop(key, None)
    save_state(data.session_id, state, user_id=auth.id, access_token=auth.access_token)
    return {"status": "reset"}


@app.post("/career-tree/message", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def career_guide_message(data: CareerGuideInput, auth: AuthenticatedUser = Depends(authenticated_user)):
    state = upgrade_saved_career_tree(data.session_id, get_state(data.session_id, user_id=auth.id, access_token=auth.access_token), auth)
    if not isinstance(state.get("career_tree"), dict):
        raise HTTPException(409, "Create a career tree before continuing the conversation")
    from app.config import client
    try:
        updated = guide_message(state, data.message, data.selected_node_id, client.chat_json)
    except (ValueError, TypeError) as exc:
        logger.warning("Career guide response failed validation")
        raise HTTPException(502, "The guide could not prepare a usable response. Please try again.") from exc
    except Exception as exc:
        logger.exception("Career guide request failed")
        raise HTTPException(502, "The career guide is temporarily unavailable. Please try again.") from exc
    save_state(data.session_id, updated, user_id=auth.id, access_token=auth.access_token)
    return {"response": updated["assistant_response"], "state": normalize_state(updated)}


@app.post("/career-tree/explain", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def career_node_explanation(data: CareerTreeExpandInput, auth: AuthenticatedUser = Depends(authenticated_user)):
    state = get_state(data.session_id, user_id=auth.id, access_token=auth.access_token)
    if not isinstance(state.get("career_tree"), dict):
        raise HTTPException(409, "Create a career tree before explaining a node")
    from app.config import client
    try:
        updated = explain_node(state, data.node_id, client.chat_json)
    except NodeExplanationNotAllowed as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "Career node not found") from exc
    except (ValueError, TypeError) as exc:
        logger.warning("Career node explanation failed validation")
        raise HTTPException(502, "The guide could not prepare a usable explanation. Please try again.") from exc
    except Exception as exc:
        logger.exception("Career node explanation failed")
        raise HTTPException(502, "The career guide is temporarily unavailable. Please try again.") from exc
    save_state(data.session_id, updated, user_id=auth.id, access_token=auth.access_token)
    return {"response": updated["assistant_response"], "state": normalize_state(updated)}


@app.post("/career-tree/changes", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def career_guide_changes(data: CareerChangesInput, auth: AuthenticatedUser = Depends(authenticated_user)):
    state = get_state(data.session_id, user_id=auth.id, access_token=auth.access_token)
    try:
        updated = apply_changes(state, data.proposal_id, data.accept)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    save_state(data.session_id, updated, user_id=auth.id, access_token=auth.access_token)
    return {"state": normalize_state(updated)}


@app.post("/career-tree/jobs", dependencies=[Depends(enforce_ip_rate_limit), Depends(enforce_rate_limit)])
def career_job_search(data: CareerJobsInput, auth: AuthenticatedUser = Depends(authenticated_user)):
    state = get_state(data.session_id, user_id=auth.id, access_token=auth.access_token)
    tree = state.get("career_tree")
    if not isinstance(tree, dict):
        raise HTTPException(409, "Create a career tree before searching openings")
    try:
        jobs = search_jobs(tree, data.node_id, data.country, data.location, data.workplace)
    except KeyError as exc:
        raise HTTPException(404, "Career node not found") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except JobSearchUnavailable as exc:
        logger.warning("Live job search unavailable")
        raise HTTPException(503, str(exc)) from exc
    return {"jobs": jobs, "source": "TheirStack"}


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