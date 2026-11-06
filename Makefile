# Developer commands. `make check` is the commit gate (lint + format + typecheck + tests).
.PHONY: install dev check lint fmt type test seed eval docker up down

install:
	cd backend && python3 -m pip install -e '.[dev]'

dev:
	cd backend && uvicorn app.main:app --reload --port 8000

lint:
	cd backend && ruff check .

fmt:
	cd backend && ruff format --check .

type:
	cd backend && mypy app

test:
	cd backend && pytest -q

frontend-check:
	cd frontend && npx oxlint && npx tsc -b

# Commit gate: a branch-size check runs in the pre-commit hook ahead of this chain.
check: lint fmt type test frontend-check

seed:
	cd backend && python -m app.db.seed

eval:
	cd backend && python -m app.eval.run

up:
	docker compose -f docker/compose.yaml up -d

down:
	docker compose -f docker/compose.yaml down
