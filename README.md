## Project Structure Overview — Updated September 26, 2026

BranchingOutAI is a career-exploration app. Its Next.js frontend displays an interactive career graph, and its FastAPI backend creates and saves career paths, provides AI guidance, and searches live job listings. Supabase handles sign-in and account-scoped data; OpenAI powers suggestions and guidance.

### Root
- `README.md`: This document. Project overview and file map.
- `requirements.txt`: Python dependencies for the backend if installing outside of `backend/requirements.txt`.
- `uvicorn.pid`: Process ID file used occasionally for server lifecycle management.

### Backend (`backend/`)
- `backend/requirements.txt`: Python dependencies specifically for the backend app.
- `backend/app/main.py`: FastAPI application entrypoint. Exposes:
- `POST /career-tree/initialize`, `/expand`, `/reset`, `/delete`, `/message`, `/explain`, `/changes`, and `/jobs`: API used by the current graph experience.
- `PUT /career-tree/state`: Saves the current graph state.
- `GET /career-tree/session`: Loads the signed-in user's account-level graph.
- `GET /health`: Liveness probe.
- `GET /ready`: Supabase reachability probe.
- `GET /session/{session_id}`: Retrieve persisted session state for debugging or legacy clients.
- `backend/app/career_workflow.py`: LangGraph orchestration for current career-tree operations; domain behavior remains in `career_tree.py`, `career_chat.py`, and `live_jobs.py`.
- `backend/app/config.py`: Backend configuration and client helpers (e.g., OpenAI and Supabase client wrappers).
- `backend/app/state_manager.py`: `get_state` / `save_state` helpers that persist session state under a globally unique `session_id`; authenticated requests are owner-scoped by Supabase RLS.
- `backend/app/utils/normalization.py`: Utilities to extract JSON from model responses and normalize values (lists, strings, casing).

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
- The graph page calls authenticated `/career-tree/*` endpoints. It starts with interest nodes, then generates industries and roles as the user expands branches.
- LangGraph routes the current initialize, expand, guide, explain, change, and job-search operations through `backend/app/career_workflow.py`. Existing validation, domain logic, persistence, and response shapes remain in place.
- Career suggestions are checked against their originating interest path before being saved. Job searches use the external TheirStack provider and return listings rather than generated placeholders.
- The backend persists signed-in users' graph/session state in Supabase with owner-scoped row-level security.

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
"root_label": "You",
"user_input": "UX/UI, front end dev, backend microservices"
}' \
http://127.0.0.1:8000/career-tree/initialize | python -m json.tool
```

## Quick Start (Frontend)
```bash
cd frontend
npm install
npm run dev
```

## Notes
- Keep the backend server running in a dedicated terminal. Execute curl requests in a separate terminal to avoid interrupting uvicorn.
- Backend tests can be run via:
```bash
PYTHONPATH=backend .venv/bin/pytest -q -m "not integration"
```

## Recent changes (Feb 2026)

- **Career workflow uses LangGraph:** `backend/app/career_workflow.py` routes current career-tree operations through a compiled LangGraph while preserving the existing API and domain behavior.
- **LangChain:** The application does not call LangChain chain or agent APIs; `langchain-core` remains present for LangGraph's dependency stack.
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
APP_ENV=development
API_RATE_LIMIT_REQUESTS=30
API_RATE_LIMIT_IP_REQUESTS=60
API_RATE_LIMIT_WINDOW_SECONDS=60
THEIRSTACK_API_KEY=ts-xxx
```

Never put the Supabase service-role key in a `NEXT_PUBLIC_*` variable or expose it to the browser.

### Health Check
After starting (detached or dev):
```
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
```

### Initialize a Career Tree

This authenticated request initializes the career graph through the same API used by the frontend.

```
curl -s -X POST http://127.0.0.1:8000/career-tree/initialize \
-H 'Authorization: Bearer <valid-supabase-access-token>' \
-H 'Content-Type: application/json' \
-d '{"session_id":"demo","root_label":"You","user_input":"I like design"}'
```

### Persistence & State Normalization
The backend persists authenticated session state to Supabase (table `session_states`). Session IDs are globally unique, and RLS restricts reads and writes to the owner identified by the bearer token. Authenticated database failures return `503`; they are not hidden by process-local memory fallback. Before persisting, the backend will automatically
normalize model outputs by parsing JSON strings (including JSON returned inside
triple-backtick code fences) into native JSON structures (lists/dicts). This
ensures the stored `state` field contains structured data that the frontend and
router can consume safely.

Key points:
- Live job searches are U.S.-only. Users choose Remote (nationwide, no location filter) or Hybrid / in-person (both settings, optional City, ST such as Boston, MA; blank searches nationwide). Supplied state abbreviations and the country/work-setting filters are validated server-side.
- Every purple role can be searched independently. Before the single TheirStack request, the guide translates its interest → sector → role path into up to five closely related employer title variants, searched alongside the original label. This avoids requiring niche career labels to match every word of an advertised title. User identity, profile, and chat history are not sent for title translation. Country, workplace, location, and 30-day recency filters remain unchanged; no listings are generated, and no results are guaranteed. Title-service failures are explicit errors, not empty successful searches.
- Interests surround the name node on one circular ring, evenly spaced when branches have equal sizes. Expanded branches claim angular space according to their visible subtree size. Titles have extra horizontal padding. Deeper nodes use compact outward lanes; collision clearance moves descendants outward without pulling individual interests off the ring. Shared saved nodes have linked visual copies in each path, eliminating cross-branch connector lines. Selecting, expanding, collapsing, or deleting a copy acts on the underlying saved node (deleting removes all copies). Expanding, collapsing, or deleting reflows all nodes (including manually dragged ones), with smooth transitions unless reduced motion is enabled. Generating branches show staggered pulsing dots.
- The same layout applies to every account: ring radius and spacing are calculated from the actual interest count and measured node sizes, not a fixed count or user identity. Larger interest sets require a larger ring; pan and zoom remain available. Regression tests cover 0, 1, 2, 3, 5, 8, 12, 20, 32, 64, and 100 interests, both collapsed and expanded, with varying node sizes and account root IDs.
- The graph workspace uses compact 14px interface text, 16px branch labels, and an 18px name label without overriding browser zoom. Nodes are at least 200-by-64 canvas units, widening to fit their titles; the chat drawer is at most 384px wide. Mobile toolbar controls retain 44px minimum heights, and the workspace follows the available viewport height.
- Select an interest, industry, or role and choose **Explain node** to open AI Chat with an overview, typical skills, typical qualifications, and practical learning/experience resources. Interests and industries are explained as fields. Explain node is disabled for the central name node; the API rejects name-node requests before calling AI. The authenticated, rate-limited `POST /career-tree/explain` endpoint saves the explanation in chat history without changing the tree, profile, or pending proposals. Resource suggestions include provider names/search terms, not unverified course links; users should confirm offerings and employer/jurisdiction-specific licensing requirements with official sources.
- AI Chat renders assistant Markdown with styled headings, lists, emphasis, and qualification notes; user messages remain plain text. Older saved explanations receive section-heading formatting when displayed, without rewriting saved history. Raw HTML and embedded images are not rendered.
- Reset view restores normal zoom and centers the name node in the current visible canvas, including after resizing or moving the node. It does not clear the saved graph.
- Each visible +/− has a transparent 48-by-64 canvas-unit tap target at the node's right edge (48-by-64 pixels at normal zoom). Titles still only select nodes; loading and non-expandable nodes have no active toggle target.
- The tree stops at purple role nodes: name → interests → sectors → roles. Roles remain clickable but have no expand control. Jobs can only be searched from this purple level: hovering a role makes the green Find openings button fully opaque without enabling it; selecting a role enables it. Selecting another level or clicking empty canvas/a connector disables it again. Specific titles, skills, and qualifications belong in Chat. Saved version-2 trees retain their interests, sectors, and roles; a one-time depth update removes only job/skill descendants and obsolete expansion state.
- Career suggestions retain the ordered originating-interest-to-parent path at every depth. Same-named sectors, roles, jobs, and skills under different parents have independent saved identities and caches; another interest's descendants cannot leak into the branch. Generation requires a concrete `why_fit` explanation, followed by a separate AI relevance review before saving. Rejected or malformed responses return an error without caching unrelated suggestions; AI relevance review is a safeguard, not a guarantee of accuracy.
- Saved graphs from the older generation logic are upgraded once when opened: names, interests, profile context, and chat history stay, while generated descendants are cleared. An on-screen notice explains the rebuild; expanding an interest regenerates its branch with the corrected logic. New graphs record `generationVersion: 2`, so reloads do not clear verified branches.
- The graph UI loads `GET /career-tree/session` using the signed-in account, rather than a browser-local session ID. IDE previews and external browsers signed into the same account load the same saved tree on refresh.
- On first account-level load, the backend adopts the legacy session with the most tree nodes (then populated interests/chat history, then session ID to break ties). Legacy saves remain untouched. Once created, the account graph is authoritative, including after a reset; concurrent first loads cannot overwrite it. This is shared persistence, not live collaborative editing.
- Set `SUPABASE_URL` and `SUPABASE_KEY` to the project URL and anon key. Set `SUPABASE_SERVICE_ROLE_KEY` separately for backend-only account deletion.
- Apply the SQL migrations in order, including `backend/migrations/20260926_harden_session_state_rls.sql` and `backend/migrations/20261001_add_shared_api_rate_limits.sql`, before deploying.
- Rate limits are shared through Postgres and survive API restarts: 30 requests per user and 60 per client IP per minute by default. Configure Uvicorn `FORWARDED_ALLOW_IPS` with trusted proxy addresses for accurate IP limits.
- For production, set `APP_ENV=production`. Backend startup requires Supabase URL/keys and exact HTTPS CORS origins; it rejects localhost or wildcard CORS. The Next.js frontend adds HSTS in production builds.
- Configure TLS at the host/proxy and set `FORWARDED_ALLOW_IPS` to only its trusted addresses. Apply both the session RLS and shared-rate-limit migrations, then verify them against a staging Supabase project.
- CAPTCHA/bot checks and WAF rules need provider-side configuration. No CAPTCHA provider is wired in because it requires provider setup and client/secret keys; per-user/IP quotas do not fully stop distributed account and IP rotation.
- There's a convenience endpoint to inspect saved state:
`GET /session/{session_id}` — returns the normalized saved state for debug.

Example: fetch a saved session for debugging:
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