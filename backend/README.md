# Backend — File Reference

This document describes the contents of the `backend/` folder, the purpose of each file, and quick instructions for common development tasks (run server, run tests, reproduce CI).

If you need higher-level setup or frontend notes, see the project root `README.md`.

## Top-level files

- `requirements.txt`
  - Purpose: general developer dependency list for running the backend in local development (non-CI). Use this when iterating locally in a venv.

- `requirements-ci.txt`
  - Purpose: minimal, pinned dependency list used by the GitHub Actions unit job. Pins are intentionally conservative to keep the CI image reproducible (see the root README for the docker reproduction command).

## `app/` package

The `app/` package contains the FastAPI application and the agent wiring.

- `main.py`
  - Purpose: FastAPI ASGI entrypoint. It creates the application instance, mounts routes, and exposes the public API endpoints such as:
    - `POST /chatbot/` — run the agent for the given `session_id` and `user_input`.
    - `GET /health` — readiness probe.
    - `GET /session/{session_id}` — fetch persisted, normalized session state.
  - Usage: run with `PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000`.

- `config.py`
  - Purpose: central location for configuration and client factories (OpenAI client, Supabase client, environment-driven config). Keep secrets out of code; use environment variables.

- `state_manager.py`
  - Purpose: helpers to `get_state` and `save_state` (Supabase-backed persistence). These functions are used by nodes and the API to persist normalized session state.

- `graph_setup.py`
  - Purpose: wiring for the agent graph. Builds/instantiates nodes, configures the graph runner, and returns the graph entrypoints used by the API.
  - Notes: The graph setup was recently updated to prefer a LangGraph-compatible runner when the optional LangGraph adapter is present (see `langgraph_adapter.py` / `langgraph_wrappers.py`). If LangGraph is not available at runtime, `graph_setup.py` falls back to the LangChain-compatible runner.

- `langchain_adapter.py` (if present)
  - Purpose: compatibility helpers that wrap LangChain primitives so nodes and tests can be run consistently in LangChain-first environments.

- `langgraph_adapter.py` (optional)
  - Purpose: optional adapter that provides a LangGraph-compatible runner and thin wrappers around node execution. This file is intentionally optional — the app will still work without LangGraph installed.

- `langgraph_wrappers.py` (optional)
  - Purpose: helper wrappers that translate between the project's node interfaces and LangGraph's expected node/runner interfaces.

- `utils/` (utility modules)
  - `normalization.py`: parsing and normalization utilities to convert model outputs (often stringified JSON or code-block JSON) into structured Python objects (lists/dicts) and canonicalize values (e.g., `UX/UI` → `UX, UI`).
  - `keywords.py`: deterministic keyword and phrase extraction helpers used by interest extraction nodes.

## `langgraph_agent/` package

This package contains the graph nodes and orchestrator used by the backend agent.

- `graph_setup.py` (see above) — graph wiring.
- `state_manager.py` (thin compatibility shim referencing `app/state_manager.py`).

### `langgraph_agent/nodes/`
Contains the individual nodes used in the graph (each node is responsible for one transformation/step in the agent flow):

- `interests_node.py`
  - Purpose: Parse `user_input` and produce a canonical list of user interests. Uses AI parsing (preferably returning JSON) with deterministic fallbacks and normalization (acronyms, punctuation, spacing).

- `industry_node.py`
  - Purpose: Given one or more interests, suggest relevant industries and job families.

- `job_node.py`
  - Purpose: Given a job family or industry selection, suggest job titles and roles.

- `skills_node.py`
  - Purpose: Given a job title, produce a list of hard and soft skills relevant to that role.

## Tests

- `backend/tests/`
  - Contains unit tests for nodes and small integration tests for graph wiring. The unit tests are designed to run without external API keys by stubbing or mocking LLM and network calls (see `backend/tests/conftest.py` for the test fixtures).
  - Typical commands:
    - Run only unit tests (skip integration):

```bash
PYTHONPATH=backend .venv/bin/pytest -q -m "not integration"
```

## Development and CI notes

- To run locally:
  - Create and activate a venv: `python3 -m venv .venv && source .venv/bin/activate`.
  - Install dev dependencies: `pip install -r backend/requirements.txt`.
  - Start server: `PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000`

- Reproducing CI locally:
  - The project root `README.md` includes a Docker command that mirrors the GitHub Actions unit job. The CI uses `backend/requirements-ci.txt` (pinned list) to ensure reproducible installs on the CI image.

- Optional adapters:
  - `langgraph_adapter.py` and `langgraph_wrappers.py` are optional files; they enable running the graph using LangGraph if you have it installed. The codebase prefers LangGraph when present but remains LangChain-compatible.

## When to modify these files

- Add nodes under `langgraph_agent/nodes/` when you need a new transformation step in the agent flow.
- Update `requirements-ci.txt` only when CI proves it is necessary to pin or bump packages (aim for minimal, well-justified changes).
- Keep `config.py` free of secrets; use environment variables and `.env` files for local development.