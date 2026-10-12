# BranchingOutAI Architecture

This document describes the current career-graph application and the separate legacy chatbot API. For setup instructions, see the project root `README.md`.

## Overview

BranchingOutAI is a Next.js frontend backed by a FastAPI service. The frontend renders the career graph and sends authenticated requests to the backend. The backend validates Supabase access tokens, asks OpenAI for career suggestions and guidance, and stores user-owned graph state in Supabase. Live job searches use TheirStack.

```text
Browser
  ├── Supabase Auth: sign-in and session token
  └── FastAPI
       ├── OpenAI: interest extraction, branch suggestions, chat, explanations
       ├── Supabase: account-owned session state and shared rate limits
       └── TheirStack: live job listings
```

## Current career-graph flow

The graph page is `frontend/src/app/graph/page.tsx`. Its API calls are collected in `frontend/src/lib/graphApi.mjs`.

1. The browser gets the signed-in user's Supabase access token.
2. `GET /career-tree/session` loads or creates the account's graph session.
3. `POST /career-tree/initialize` creates the root user node and starting interests.
4. When a branch is expanded, `POST /career-tree/expand` generates its children. The graph currently progresses from user to interests, interests to industries, and industries to roles.
5. The UI saves selection and expansion state with `PUT /career-tree/state`. Reset, deletion, chat, explanations, change proposals, and job searches use their corresponding `/career-tree/*` routes.
6. The backend validates and normalizes data, saves it under the authenticated account, and returns JSON for the frontend to display.

The graph-generation rules are in `backend/app/career_tree.py`. Each generated suggestion is associated with its exact originating-interest path and checked for relevance before it is saved. `backend/app/career_chat.py` handles guide responses, explanations, and proposed changes; proposals require user confirmation. `backend/app/live_jobs.py` validates the selected role and filters, translates the role into search titles, and queries TheirStack. Listings come from that provider; the application does not fabricate job openings.

Frontend helpers divide display work: `branchTree.mjs` creates a visual copy of shared nodes per path; `radialTreeLayout.mjs` calculates graph positions; and `graphAnimation.mjs` handles animation. These are separate from the backend's saved tree structure.

## Legacy chatbot API

`POST /chatbot/` is a separate, still-implemented API. It loads session state, clears derived fields for a new message, and uses `backend/app/graph_setup.py` with `backend/app/nodes/` to process the request. `RouterNode` selects one agent node based on the state. This older state-routed flow is not used by the current graph page; do not treat its nodes or `/chatbot/` as the graph-generation implementation.

The adapters in `langchain_adapter.py`, `langgraph_adapter.py`, and their wrappers support compatibility with agent runners. The career-tree endpoints use the dedicated logic in `career_tree.py` and `career_chat.py`.

## Backend responsibilities

- `backend/app/main.py` creates the FastAPI app, validates requests, authenticates users, applies rate limits, maps service errors to HTTP responses, and defines the API routes.
- `backend/app/config.py` reads environment configuration and creates OpenAI and Supabase clients.
- `backend/app/state_manager.py` reads and writes session state. Authenticated requests use the caller's token so Supabase row-level security can enforce ownership. Storage failures do not silently fall back to memory for authenticated requests.
- `backend/app/utils/normalization.py` converts JSON-like strings into structured Python values before returning or persisting state.
- `backend/app/rate_limiter.py` calls the shared Postgres rate-limit function; the identifiers stored by that function are keyed hashes.
- `backend/migrations/` contains the SQL schema/security changes that must be applied to the Supabase project.

## Data model

The backend stores an account graph as state associated with a session ID. The state can include the career tree, conversation history, previous responses, and profile context. The tree contains:

- **Nodes:** objects with an ID, type, label, and optional details.
- **Edges:** links from a parent node to a child node.
- **View state:** selected and expanded node IDs.
- **Generation metadata:** version markers used to upgrade older saved trees.

The tree is generated incrementally rather than creating every possible branch at initialization. This keeps initial setup small and generates recommendations only when a user expands a branch.

## Authentication, persistence, and limits

The frontend uses Supabase's public anon key for authentication. Protected API calls send the Supabase bearer token; the backend validates it and uses the caller identity for owner-scoped persistence under row-level security. The service-role key is reserved for backend administrative operations such as account deletion.

Protected routes have shared per-user and per-IP rate limits. The request body and selected text fields also have size limits. Production requires Supabase configuration and exact HTTPS CORS origins. Configure trusted proxy addresses for client IP handling, and keep service-role and provider API keys in the backend environment only.

`GET /health` reports whether the process is alive. `GET /ready` checks whether required Supabase storage for rate limiting is reachable; it does not require OpenAI to be available.

Raw user input and profile context may be sent to OpenAI to fulfill AI features. Review the product privacy policy and provider terms when changing what data is sent.

## Tests and local development

Backend tests live in `backend/tests/`; frontend helper tests live next to their `.mjs` modules in `frontend/src/lib/`. Run the backend and frontend using the instructions in the root `README.md`. Backend unit tests can be run with:

```bash
PYTHONPATH=backend .venv/bin/pytest -q -m "not integration"
```

Frontend tests and linting can be run from `frontend/` with `npm test` and `npm run lint`.
