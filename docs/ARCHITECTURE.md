# Backend Architecture — BranchingOutAI

Date: September 26, 2026

This document describes the backend architecture, responsibilities of each file, how components connect, the request flow, and developer run/test notes.

## High-level overview
- The backend is a FastAPI service with authenticated session APIs and a small state-routed career exploration agent.
- Key design choices:
  - LLM-first extraction with deterministic fallbacks for resilience.
  - Canonicalization and normalization (acronyms, multi-word phrases, deduplication).
  - Persisted session state in Supabase keyed by globally unique `session_id`; ownership is enforced with the verified Supabase user ID and row-level security.

## Top-level layout (backend/)
- `backend/app/main.py` — FastAPI entrypoint and HTTP routes. Handles request validation, state initialization/cleanup, runs the agent graph, persists final state, and returns a response + state JSON.
- `backend/app/config.py` — Creates and exposes external clients (LLM/chat client, Supabase client). Central location for API keys, timeouts, and request defaults.
- `backend/app/state_manager.py` — Persistence layer. Authenticated requests use atomic Supabase upserts and fail with service unavailable when storage fails. Calls without an access token can use process memory for local development only.
- `backend/app/utils/normalization.py` — Helpers for parsing model outputs (strip fences, JSON extraction), recursive normalization, type conversions.
- `backend/app/utils/keywords.py` — Deterministic keyword extraction fallback using spaCy when available, otherwise heuristic splitting.

### Agent nodes (`backend/app/nodes/`)
- `interests_node.py`
  - Input: `user_input` string (from the POST body)
  - Responsibilities:
    - Prefer an LLM response that returns a JSON array of interest phrases.
    - Robustly parse the LLM output (strip code fences, extract bracketed lists, JSON-load, or fallback text splitting).
    - Deterministically fallback to `keywords.extract_keywords()` if LLM output is unusable.
    - Canonicalize/case interests: acronym casing (UX, UI, AI, ML, NLP), mapped phrases (Front End Development, Backend Microservices), DevOps/MLOps consolidation.
    - Set `state["interests"]` and call the LLM to suggest 2–3 industries; set `state["industries"]` after robust parsing.
    - Save state via `state_manager.save_state()` when `session_id` is provided.

- `industry_node.py` — Suggests job families or narrow industries based on `state["interests"]` and writes `state["job_families"]`.
- `job_node.py` — Suggests job titles for a selected job family and writes `state["jobs"]`.
- `skills_node.py` — Suggests hard and soft skills for the selected job(s) and writes `state["skills"]`.

Each node reads/writes shared keys on a `state` dict. Nodes may call `client.chat(...)` (LLM) via `config.client` and persist state mid-flow if needed.

## Request flow (end-to-end)
1. An authenticated client sends `POST /chatbot/` with `{ "session_id": "<globally-unique-id>", "user_input": "<text>" }` and `Authorization: Bearer <Supabase access token>`.
2. FastAPI validates the token with Supabase. Blocking authentication, model, and database calls run in FastAPI's worker thread pool.
3. The route loads the user's session state, clears derived fields, and asks `AgentGraph` to select one node. The current request processes interests and industries; it does not run the entire industry → job → skills flow in one request.
4. The interests node makes up to two sequential OpenAI calls and uses deterministic fallbacks when model output is unavailable or unusable.
5. The route upserts the state and returns normalized JSON. An authenticated persistence failure returns HTTP 503 rather than reporting an in-memory write as durable.

The current Next.js graph page is a local interactive canvas and does not call `/chatbot/` or `/session/{session_id}`. The profile page calls `DELETE /account`; deleting the Supabase Auth user cascades to owned session rows through the database foreign key.

## Security and failure boundaries
- The browser uses Supabase's public anon key for Auth. The backend validates bearer tokens and passes the caller token to PostgREST so RLS evaluates the caller's identity.
- The service-role key is backend-only and used for account deletion. The RLS migration adds owner policies plus a restrictive owner guard, preventing older permissive policies from widening access.
- Raw user input is included in prompts sent to OpenAI; disclose this in product privacy terms and avoid logging prompt bodies or access tokens.
- `/health` is a liveness endpoint. `/ready` checks Supabase table reachability. OpenAI is not required for readiness because the interest flow has deterministic fallbacks.
- `APP_ENV=production` requires Supabase URL/keys and exact HTTPS CORS origins at startup. The backend and production frontend set HSTS only on HTTPS/production responses.
- Rate limiting uses an atomic Postgres RPC, so quotas are shared across workers and survive API restarts. User and client-IP identifiers are HMACed before storage; the database prunes old buckets opportunistically. Limiting fails closed with HTTP 503 if the RPC is unavailable.
- The client-IP quota runs before bearer-token verification, which also throttles invalid-token attempts. JSON bodies are capped at 64 KiB before route handling; chat text is limited to 4,000 characters.
- Session state is replaced as a JSON document; concurrent updates to one session are last-write-wins. A database error is logged and surfaced as 503; authenticated requests do not fall back to memory.

## State schema (typical keys)
- `user_input`: raw string from request
- `interests`: list[str] — canonical interest phrases
- `industries`: list[str] — suggested industries (2–3)
- `job_families`: list[str]
- `jobs`: list[str]
- `skills`: { "hard": list[str], "soft": list[str] }

Not every key will be present for every request; nodes add keys as the graph progresses.

## Prompting patterns (examples)
- Interests extraction (LLM-first):
  - System: "You identify the user's interests."
  - User: "What are the user's interests based on this input? Return ONLY a JSON array of interest phrases. Input: <user_input>"
- Industries suggestion:
  - System: "You are a career exploration AI."
  - User: "The user is interested in: <list>. Suggest 2-3 broad industries. Return ONLY a JSON array (no code fences)."

Prompts request JSON arrays explicitly. The code implements defensive parsing in case the model returns explanatory text, fences, or partial JSON.

## Robustness & normalization
- Strip code fences (```json) before parsing.
- Attempt JSON loads; if that fails, extract bracketed content and try again.
- Fallback to separator-based splitting (`and`, comma, `/`, `;`, whitespace) with spaCy noun-chunk support when available.
- Canonical mappings include `UX/UI`, `DevOps`, `MLOps`, `Front End Development`, `Backend Microservices` and an acronym map (`UX`, `UI`, `AI`, `ML`, `NLP`).
- Deduplicate while preserving input order and consolidate split fragments (e.g., `Devops Ml` + `Ops` -> `DevOps`, `MLOps`).

## Tests
- `backend/tests/test_interests.py` invokes `InterestsNode.process()` directly and asserts presence of canonical interest phrases across diverse inputs (comma-separated, space-separated, mixed, hobby inputs).

## Developer run & quick checks
1. Create / activate venv and install backend deps:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```
2. Start server (keep running in a dedicated terminal):
```bash
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --app-dir backend
```
3. Check liveness/readiness and send a sample authenticated POST (use a valid Supabase access token):
```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/ready
SESSION=$(uuidgen)
curl -sS -X POST -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" -H "Content-Type: application/json" -d '{"session_id":"'$SESSION'","user_input":"ux ui front end dev"}' http://127.0.0.1:8000/chatbot/ | .venv/bin/python -m json.tool
```

## Where to modify behavior
- Interests parsing & canonical rules: `backend/app/nodes/interests_node.py` and `backend/app/utils/keywords.py`.
- Prompt text, system messages, and client config: `backend/app/config.py` and individual node files.
- Persistence/upsert behavior: `backend/app/state_manager.py`.

## Operational notes
- Apply migrations in order, including `20260926_harden_session_state_rls.sql` and `20261001_add_shared_api_rate_limits.sql`, before deploying the updated backend.
- Set `CORS_ALLOWED_ORIGINS` to the deployed frontend origin and keep `SUPABASE_SERVICE_ROLE_KEY` server-side only.
- Set `FORWARDED_ALLOW_IPS` to the exact trusted reverse-proxy addresses so Uvicorn can safely resolve client IPs for the secondary IP quota. Do not trust arbitrary forwarded headers.
- CAPTCHA/bot protection, signup throttles, TLS termination, and WAF rules must be configured in Supabase Auth and the hosting edge; they are not represented by local app code.
- `OPENAI_TIMEOUT_SECONDS` controls model request timeouts (default 30 seconds). Rate defaults are 30 requests/user/minute and 60 requests/IP/minute; use `API_RATE_LIMIT_REQUESTS`, `API_RATE_LIMIT_IP_REQUESTS`, and `API_RATE_LIMIT_WINDOW_SECONDS` to tune them.

---

If you'd like, I can also produce a sequence diagram (Mermaid) showing the node ordering and the main HTTP request/response lifecycle. Which would you like next?
