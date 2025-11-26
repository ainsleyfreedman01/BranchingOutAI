PYTHON := /Users/ainsleyfreedman/projects/branchingoutai/.venv/bin/python
BACKEND_DIR := backend
APP_MODULE := app.main:app
HOST := 127.0.0.1
PORT := 8000
PID_FILE := .backend.pid

.PHONY: backend-up backend-dev backend-down backend-status

backend-up: ## Start backend (FastAPI) detached on $(PORT)
	@echo "Starting backend on $(HOST):$(PORT)"
	@if [ -f $(PID_FILE) ]; then echo "PID file exists ($(PID_FILE)); run 'make backend-down' first"; exit 1; fi
	@PYTHONPATH=$(BACKEND_DIR) nohup $(PYTHON) -m uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT) > backend_server.log 2>&1 & echo $$! > $(PID_FILE)
	@echo "Backend started. PID=$$(cat $(PID_FILE))"

backend-dev: ## Start backend with --reload in foreground (Ctrl+C to stop)
	@echo "Starting backend in dev mode (reload) on $(HOST):$(PORT)"
	@PYTHONPATH=$(BACKEND_DIR) $(PYTHON) -m uvicorn $(APP_MODULE) --host $(HOST) --port $(PORT) --reload

backend-status: ## Show backend process listening on $(PORT)
	@lsof -i :$(PORT) -sTCP:LISTEN -n -P || echo "No process listening on $(PORT)"
	@if [ -f $(PID_FILE) ]; then echo "Recorded PID: $$(cat $(PID_FILE))"; fi

backend-down: ## Stop detached backend started via backend-up
	@if [ ! -f $(PID_FILE) ]; then echo "No PID file; nothing to stop"; exit 0; fi
	@PID=$$(cat $(PID_FILE)); echo "Stopping backend PID $$PID"; kill $$PID 2>/dev/null || echo "Process not running"; rm -f $(PID_FILE)
	@echo "Backend stopped"

help: ## Show available Make targets
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | sed 's/:.*##/: /'
