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

