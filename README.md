## Project Structure Overview — Written December 8, 2025

This repository contains a FastAPI backend that orchestrates a LangGraph-style agent for extracting user interests and suggesting industries, along with a Next.js + Tailwind frontend. Below is a concise walkthrough of the folders and key files, and what each does today.

### Root
- `README.md`: This document. Project overview and file map.
- `requirements.txt`: Python dependencies for the backend if installing outside of `backend/requirements.txt`.
- `uvicorn.pid`: Process ID file used occasionally for server lifecycle management.

### Backend (`backend/`)
- `backend/requirements.txt`: Python dependencies specifically for the backend app.
- `backend/app/main.py`: FastAPI application entrypoint. Exposes:
	- `POST /chatbot/`: Main interaction. Loads/merges session state, runs the agent, and persists results.
	- `GET /health`: Health/readiness probe.
	- `GET /session/{session_id}`: Retrieve persisted session state.
- `backend/app/config.py`: Backend configuration and client helpers (e.g., OpenAI and Supabase client wrappers).
- `backend/app/state_manager.py`: `get_state` / `save_state` helpers that persist and fetch session state (Supabase), keyed by `X-User-ID` and `session_id`.
- `backend/app/utils/normalization.py`: Utilities to extract JSON from model responses and normalize values (lists, strings, casing).
- `backend/app/utils/keywords.py`: Deterministic keyword extraction utilities leveraged by some nodes.

#### LangGraph Agent (`backend/app/langgraph_agent/`)
- `__init__.py`: Package marker.
- `graph_setup.py`: Wires the agent graph, router, and processing nodes. Defines execution flow.
- `state_manager.py`: Shared state utilities referenced by nodes (import path convenience for agent code).

#### Agent Nodes (`backend/app/langgraph_agent/nodes/`)
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
- Backend FastAPI server on `127.0.0.1:8000` with `/health` for readiness.
- `POST /chatbot/` expects JSON with `session_id` and `user_input` and an `X-User-ID` header. Returns a message and a `state` object including normalized `interests` and suggested `industries`.
- Interests normalization handles technical and non-technical phrases, commas and space-separated inputs, and acronym casing for `UX`, `UI`, `AI`, `ML`, `NLP`.

## Quick Start (Backend)
```bash
# From project root
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# Start server (no --factory)
PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --app-dir backend

# Health
curl -sS http://127.0.0.1:8000/health | cat

# Example POST
UUID=$(uuidgen); SESSION=$(uuidgen)
curl -sS -X POST \
	-H "Content-Type: application/json" \
	-H "X-User-ID: $UUID" \
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
# BranchingOutAI

[![CI](https://github.com/ainsleyfreedman01/BranchingOutAI/actions/workflows/ci.yml/badge.svg)](https://github.com/ainsleyfreedman01/BranchingOutAI/actions/workflows/ci.yml)

BranchingOutAI is an interactive career exploration tool that uses a graph-based AI agent
to help users explore industries, jobs, and skills. The frontend visualizes branching career paths 
using JointJS, and the backend handles AI reasoning, memory, and job data integration.

## Tech Stack

- Frontend: Next.js + Tailwind CSS
- Backend: FastAPI + LangGraph + OpenAI
- Database: Supabase
- Job Data: TheirStack API

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
SUPABASE_KEY=public-or-service-key
THEIRSTACK_API_KEY=ts-xxx
```

### Health Check
After starting (detached or dev):
```
curl -s http://127.0.0.1:8000/health
```

### Chatbot Endpoint Example
```
curl -s -X POST http://127.0.0.1:8000/chatbot/ \
	-H 'Content-Type: application/json' \
	-d '{"session_id":"demo","user_input":"I like design"}'
```

### Persistence & State Normalization
The backend persists session state to Supabase (table `session_states`) when a
`session_id` is provided. Before persisting, the backend will automatically
normalize model outputs by parsing JSON strings (including JSON returned inside
triple-backtick code fences) into native JSON structures (lists/dicts). This
ensures the stored `state` field contains structured data that the frontend and
router can consume safely.

Key points:
- To enable Supabase persistence, set `SUPABASE_URL` and `SUPABASE_KEY` in
	your `.env` (the code expects `SUPABASE_KEY`). If you only have a
	`SUPABASE_SERVICE_KEY`, set `SUPABASE_KEY` to that value as well.
- There's a convenience endpoint to inspect saved state:
	`GET /session/{session_id}` — returns the normalized saved state for debug.

Example: fetch a saved session after posting to `/chatbot/`:
```
curl -s http://127.0.0.1:8000/session/test-live-1
```

