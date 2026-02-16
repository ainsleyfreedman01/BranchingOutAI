# Backend Architecture — BranchingOutAI

Date: December 16, 2025

This document describes the backend architecture, responsibilities of each file, how components connect, the request flow, and developer run/test notes.

## High-level overview
- The backend is a FastAPI service that runs a small agent/graph to extract user interests from free-form input and suggest related industries, job families, job titles, and skills.
- Key design choices:
  - LLM-first extraction with deterministic fallbacks for resilience.
  - Canonicalization and normalization (acronyms, multi-word phrases, deduplication).
  - Persisted session state (Supabase) keyed by `session_id` and `X-User-ID`.

## Top-level layout (backend/)
- `backend/app/main.py` — FastAPI entrypoint and HTTP routes. Handles request validation, state initialization/cleanup, runs the agent graph, persists final state, and returns a response + state JSON.
- `backend/app/config.py` — Creates and exposes external clients (LLM/chat client, Supabase client). Central location for API keys, timeouts, and request defaults.
- `backend/app/state_manager.py` — Persistence layer. `get_state(session_id)` and `save_state(session_id, state)` implement Supabase interactions and light normalization/upsert logic.
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
1. Client POSTs to `/chatbot/` with body `{ "session_id": "<uuid>", "user_input": "<text>" }` and header `X-User-ID: <uuid>`.
2. `main.py` loads the current persisted state (if any) and merges incoming state, clears computed/derived fields to force recomputation, and runs the agent graph.
3. The graph runs nodes in order (commonly: Interests → Industry → Job → Skills). Each node updates the shared `state` dict.
4. Nodes use an LLM-first strategy and fall back to deterministic extraction when necessary. After node execution, `state` contains canonical `interests`, `industries`, and further artifacts depending on the path.
5. `main.py` persists the final state (`state_manager.save_state`) and returns `{ "response": "<message>", "state": <state> }` to the caller.

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
3. Health check and a sample POST (use separate terminal):
```bash
curl -sS http://127.0.0.1:8000/health | cat
UUID=$(uuidgen); SESSION=$(uuidgen)
curl -sS -X POST -H "Content-Type: application/json" -H "X-User-ID: $UUID" -d '{"session_id":"'$SESSION'","user_input":"ux ui front end dev"}' http://127.0.0.1:8000/chatbot/ | .venv/bin/python -m json.tool
```

## Where to modify behavior
- Interests parsing & canonical rules: `backend/app/nodes/interests_node.py` and `backend/app/utils/keywords.py`.
- Prompt text, system messages, and client config: `backend/app/config.py` and individual node files.
- Persistence/upsert behavior: `backend/app/state_manager.py`.

## Next docs or improvements (suggested)
- Add a Mermaid sequence diagram to illustrate node order and data flow.
- Expand acronym map (AR/VR, IoT) and add tests for those cases.

---

If you'd like, I can also produce a sequence diagram (Mermaid) showing the node ordering and the main HTTP request/response lifecycle. Which would you like next?
