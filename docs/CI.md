# CI and Test Guide

This document explains the project's CI setup, how unit vs integration tests are run, and how to run tests locally.

## Workflows

- `.github/workflows/python-tests.yml` (unit):
  - Runs on push/PR to `main`.
  - Installs dependencies from `backend/requirements.txt` and runs pytest excluding tests marked `integration`.
  - Command used in CI: `pytest -q -m "not integration"` with `PYTHONPATH=backend`.

- `.github/workflows/integration-tests.yml` (integration):
  - Trigger: `workflow_dispatch` (manual) and `push: main`.
  - Runs only when repository secrets `OPENAI_API_KEY`, `SUPABASE_URL`, and `SUPABASE_KEY` are present.
  - Command used in CI: `pytest -q -m integration` with `PYTHONPATH=backend`.

## Test categories

- Unit tests: fast, deterministic tests that do not require external services. They are marked by default (no marker) and executed in the unit workflow.
- Integration tests: tests that exercise external services or full node integration. They are explicitly marked with `@pytest.mark.integration` and included in the integration workflow only.

## Running tests locally

Prerequisites:

- Python 3.11 (recommended) and a virtual environment.
- Install project test dependencies in a virtualenv (we keep backend dependencies separate):

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r backend/requirements.txt
pip install pytest
```

- Run unit tests (fast):

```bash
PYTHONPATH=backend .venv/bin/pytest -q -m "not integration"
```

- Run integration tests (requires secrets):

Set environment variables for OpenAI and Supabase, then run:

```bash
export OPENAI_API_KEY="sk_..."
export SUPABASE_URL="https://..."
export SUPABASE_KEY="public-anon-..."
PYTHONPATH=backend .venv/bin/pytest -q -m integration
```

## Adding more integration tests

- Mark tests with `@pytest.mark.integration` and update `pytest.ini` (already present) if you add new categories.
- For tests that require the Supabase table schema or seeded data, prefer mocking or use a dedicated test Supabase project and keep credentials in GitHub secrets.

## CI notes

- The unit workflow avoids running integration tests to keep PR validation fast.
- The integration workflow runs only when the required secrets are configured; use the workflow dispatch UI to trigger it manually when needed.

If you'd like, I can:

- Add a small script `scripts/ci_local.sh` to automate the local setup and test runs.
- Create a short `docs/CI_SECRETS.md` describing how to create a Supabase test project and obtain keys.
