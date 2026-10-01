## Project Structure Overview — Updated September 26, 2026

This repository contains a FastAPI backend that orchestrates a graph-based AI agent (LangChain + optional LangGraph adapters) for extracting user interests and suggesting industries, along with a Next.js + Tailwind frontend. Below is a concise walkthrough of the folders and key files, and what each does today.

### Root
- `README.md`: This document. Project overview and file map.
- `requirements.txt`: Python dependencies for the backend if installing outside of `backend/requirements.txt`.
- `uvicorn.pid`: Process ID file used occasionally for server lifecycle management.

### Backend (`backend/`)
- `backend/requirements.txt`: Python dependencies specifically for the backend app.
- `backend/app/main.py`: FastAPI application entrypoint. Exposes:
- `POST /chatbot/`: Main interaction. Loads/merges session state, runs the agent, and persists results.
- `GET /health`: Liveness probe.
- `GET /ready`: Supabase reachability probe.
- `GET /session/{session_id}`: Retrieve persisted session state.
- `backend/app/config.py`: Backend configuration and client helpers (e.g., OpenAI and Supabase client wrappers).
- `backend/app/state_manager.py`: `get_state` / `save_state` helpers that persist session state under a globally unique `session_id`; authenticated requests are owner-scoped by Supabase RLS.
- `backend/app/utils/normalization.py`: Utilities to extract JSON from model responses and normalize values (lists, strings, casing).
- `backend/app/utils/keywords.py`: Deterministic keyword extraction utilities leveraged by some nodes.

### Agent Nodes (`backend/app/nodes/`)
- `interests_node.py`: Extracts and normalizes user interests from `user_input`. Logic:
- Prefers AI parsing that returns a JSON array, with robust fallbacks (split, normalization, acronym casing).
- Canonicalizes common variants (e.g., `UX/UI`, `DevOps`, `MLOps`, `Front End Development`, `Backend Microservices`).
- Requests 2–3 industries and cleans responses into a list.
- `industry_node.py`: Suggests job families based on selected industries using structured prompts; updates `state["job_families"]`.
- `job_node.py`: Suggests job titles based on a selected job family; updates `state["jobs"]`.
- `skills_node.py`: Suggests hard and soft skills based on selected job; updates `state["skills"]`.

#### Tests (`backend/tests/`)
- `test_interests.py`: Pytest suite that invokes `InterestsNode` directly to validate interests extraction across:
- Technical inputs, DevOps/MLOps canonicalization, UX/UI + dev variants.
- No-commas inputs (social/policy, arts/museums).
- Mixed one-word and multi-word interests.

### Frontend (`frontend/`)
- `package.json`: Frontend dependencies and scripts.
- `next.config.ts`: Next.js configuration.
- `tsconfig.json`: TypeScript configuration.
- `eslint.config.mjs`: ESLint config.
- `tailwind.config.js` / `postcss.config.(js|mjs)`: Tailwind and PostCSS configuration.
- `next-env.d.ts`: Next.js TypeScript environment declarations.
- `public/`: Static assets served by Next.js.
- `src/app/layout.tsx`: App layout wrapper.
- `src/app/page.tsx`: Root page component.
- `src/app/globals.css`: Global styles (Tailwind base).
- `frontend/README.md`: Frontend-local README (setup, scripts).

## Current Behavior Summary
- Backend FastAPI server on `127.0.0.1:8000`; `/health` is liveness and `/ready` checks Supabase reachability.
- `POST /chatbot/` expects JSON with `session_id` and `user_input` plus a Supabase bearer token. It returns normalized interests and suggested industries. The current frontend does not yet call this endpoint.
- Interests normalization handles technical and non-technical phrases, commas and space-separated inputs, and acronym casing for `UX`, `UI`, `AI`, `ML`, `NLP`.

## Quick Start (Backend)
```bash
# From project root
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# Start server (no --factory)
PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --app-dir backend

# Liveness and dependency readiness
curl -sS http://127.0.0.1:8000/health | cat
curl -sS http://127.0.0.1:8000/ready | cat

# Example authenticated POST (set SUPABASE_ACCESS_TOKEN to a valid user token)
SESSION=$(uuidgen)
curl -sS -X POST \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
-d '{
"session_id": "'$SESSION'",
"user_input": "UX/UI, front end dev, backend microservices"
}' \
http://127.0.0.1:8000/chatbot/ | python -m json.tool
```

## Quick Start (Frontend)
```bash
cd frontend
npm install
npm run dev
```

## Notes
- Keep the backend server running in a dedicated terminal. Execute curl requests in a separate terminal to avoid interrupting uvicorn.
- The interests tests can be run via:
```bash
PYTHONPATH=backend .venv/bin/pytest -q backend/tests/test_interests.py
```

## Recent changes (Feb 2026)

- **Optional LangGraph runtime added:** New files `backend/app/langgraph_adapter.py` and `backend/app/langgraph_wrappers.py` provide optional adapters/wrappers so the project can run with or without LangGraph installed. `graph_setup.py` now prefers a LangGraph-compatible runner when the adapter is available but falls back to the existing LangChain runner.
- **CI dependency pins updated:** To keep the GitHub Actions unit job reproducible we updated `backend/requirements-ci.txt` to use `starlette==0.48.0` and `typing-extensions==4.14.1` to resolve compatibility between FastAPI, Starlette and Pydantic on the CI image.
- **Local CI reproduction command:** See the "Reproducing GitHub Actions unit job locally" section later in this README for the exact Docker command we used to verify the unit job locally.

## Setup Instructions

1. Clone repo
2. Frontend: `cd frontend` → `npm install` → `npm run dev`
3. Backend:
- Create venv & install deps: `cd backend` → `python3 -m venv .venv` → `source .venv/bin/activate` → `pip install -r requirements.txt`
- Dev (auto-reload): `make backend-dev`
- Detached: `make backend-up` (PID stored in `.backend.pid`)
- Stop: `make backend-down`
- Status: `make backend-status`
4. Create `.env` with API keys for OpenAI, Supabase, and TheirStack

### Environment Variables (.env example)
```
OPENAI_API_KEY=sk-xxx
SUPABASE_URL=https://your.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=server-only-service-role-key
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ALLOWED_ORIGINS=http://localhost:3000
OPENAI_TIMEOUT_SECONDS=30
THEIRSTACK_API_KEY=ts-xxx
```

Never put the Supabase service-role key in a `NEXT_PUBLIC_*` variable or expose it to the browser.

### Health Check
After starting (detached or dev):
```
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

### Chatbot Endpoint Example
```
curl -s -X POST http://127.0.0.1:8000/chatbot/ \
-H 'Authorization: Bearer <valid-supabase-access-token>' \
-H 'Content-Type: application/json' \
-d '{"session_id":"demo","user_input":"I like design"}'
```

### Persistence & State Normalization
The backend persists authenticated session state to Supabase (table `session_states`). Session IDs are globally unique, and RLS restricts reads and writes to the owner identified by the bearer token. Authenticated database failures return `503`; they are not hidden by process-local memory fallback. Before persisting, the backend will automatically
normalize model outputs by parsing JSON strings (including JSON returned inside
triple-backtick code fences) into native JSON structures (lists/dicts). This
ensures the stored `state` field contains structured data that the frontend and
router can consume safely.

Key points:
- Set `SUPABASE_URL` and `SUPABASE_KEY` to the project URL and anon key. Set `SUPABASE_SERVICE_ROLE_KEY` separately for backend-only account deletion.
- Apply the SQL migrations in order, including `backend/migrations/20260926_harden_session_state_rls.sql`, before deploying.
- There's a convenience endpoint to inspect saved state:
`GET /session/{session_id}` — returns the normalized saved state for debug.

Example: fetch a saved session after posting to `/chatbot/`:
```
curl -s -H 'Authorization: Bearer <valid-supabase-access-token>' \
  http://127.0.0.1:8000/session/test-live-1
```

## Reproducing GitHub Actions unit job locally (Linux container)

Use this command from the project root to reproduce the unit CI job in a disposable Python 3.11 Debian/Ubuntu container. It installs minimal build tools, installs the CI dependency list from `backend/requirements-ci.txt`, downloads the `en_core_web_sm` spaCy model, and runs the unit tests (non-integration):

```bash
docker run --rm -v "$PWD":/workspace -w /workspace -e DEBIAN_FRONTEND=noninteractive python:3.11-slim bash -lc \
  "apt-get update -qq && apt-get install -y -qq build-essential git curl && \
   python -m pip install --upgrade pip setuptools wheel && \
   pip install -r backend/requirements-ci.txt && \
   python -m spacy download en_core_web_sm || true && \
   PYTHONPATH=backend OPENAI_API_KEY= SUPABASE_URL= SUPABASE_KEY= pytest -q -m \"not integration\""
```

Notes:
- The CI requirements file used by Actions is `backend/requirements-ci.txt`. We intentionally pin a small set of packages there so the Actions job remains reproducible.
- If the container run succeeds locally (tests pass), the GitHub Actions unit job should also pass in most cases.

## Running unit tests locally

To run only the unit tests locally (skip integration tests) from the project root after activating your venv:

```bash
# from project root
source .venv/bin/activate
PYTHONPATH=backend OPENAI_API_KEY= SUPABASE_URL= SUPABASE_KEY= pytest -q -m "not integration"
```

If you don't want to set API keys for test runs that stub LLM/network calls, set them to empty values as shown above.