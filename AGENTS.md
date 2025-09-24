# Repository Guidelines

## Project Structure & Module Organization
`api/` serves FastAPI routers for chat, embeddings, tools, and health checks, while `services/` orchestrates business logic and dispatches tool maps under `tools/`. App configuration, middleware, schemas, and logging live in `core/`; `main.py` bootstraps uvicorn. Database tables are defined in `core/models.py`, with migrations under `dbmig/versions/`. Tests sit in `tests/` or local `test_*.py` files, and helper configs land in `config/` or `utils/`.

## Build, Test, and Development Commands
Run `./run.sh` to create the venv, install deps via `uv`, apply migrations, and start the API on port 8000. Use `APP_ENV=development PORT=8000 python main.py` for hot reload during local edits. Execute `pytest -q` for the full suite; narrow scope with `pytest -q -k "pattern"`. Apply migrations manually with `alembic upgrade head`, and use `docker build -t coe-backend .` plus `docker run --env-file .env -p 8000:8000 coe-backend` for containerized runs.

## Coding Style & Naming Conventions
Target Python 3.11 with 4-space indents and type hints on public APIs. Follow snake_case for modules and functions, PascalCase for classes, and `name_tool.py`/`name_map.py` for tools. Keep imports ordered using `isort .`, lint with `ruff check .`, and format using `ruff format .` before pushing.

## Testing Guidelines
Author focused pytest or `pytest-asyncio` tests that mirror function behavior in `test_*.py` files. Mock external services (RAG, DB) to keep runs deterministic. Ensure new features land with regression coverage and confirm everything passes via `pytest -q` ahead of any PR.

## Commit & Pull Request Guidelines
Write Conventional Commit messages such as `feat: add embeddings cache`. PRs should reference issues, explain behavior changes, summarize validation (tests, curl logs), and call out config updates or migration impacts. Seek review when touching cross-cutting services, tools, or database schema.

## Security & Configuration Tips
Copy `.env.example` to `.env` and populate secrets like `OPENAI_API_KEY`, `JWT_SECRET_KEY`, and database credentials—never commit them. Set `RUN_MIGRATIONS=true` for automated upgrades and reserve `APP_ENV=development` for local use. Avoid logging sensitive payloads; sanitized outputs should go under `logs/` only.
