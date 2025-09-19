# Repository Guidelines

## Project Structure & Module Organization
- `api/` exposes FastAPI routes such as chat, embeddings, tools, and health checks.
- `core/` configures the app factory, middleware, schemas, and logging; `main.py` bootstraps uvicorn.
- `services/` orchestrates business flows and dispatches tools defined under `tools/` with their maps.
- Database models reside in `core/models.py`; Alembic migrations live under `dbmig/versions/`.
- Tests live in `tests/` or co-located `test_*.py` files; configs and helpers sit under `config/` and `utils/`.

## Build, Test, and Development Commands
- `./run.sh` provisions a venv, installs deps via `uv`, runs migrations, and starts the API on `:8000`.
- `APP_ENV=development PORT=8000 python main.py` launches the server with hot reload.
- `pytest -q` runs the full test suite; use `-k` to target specific tests.
- `alembic upgrade head` applies pending database migrations.
- `docker build -t coe-backend .` then `docker run --env-file .env -p 8000:8000 coe-backend` runs the service in a container.

## Coding Style & Naming Conventions
- Target Python 3.11 with 4-space indentation and type hints on public APIs.
- Follow snake_case for modules/functions, PascalCase for classes, and `name_tool.py`/`name_map.py` for tools.
- Keep imports ordered with `isort .`; lint and format using `ruff check .` and `ruff format .`.

## Testing Guidelines
- Prefer focused unit tests using `pytest`/`pytest-asyncio`; mock external services (RAG, DB) when feasible.
- Name test files `test_*.py`; mirror function behavior in test names.
- Run `pytest -q` before opening a PR and ensure new features include regression coverage.

## Commit & Pull Request Guidelines
- Use Conventional Commits (e.g., `feat: add embeddings cache`).
- PRs should reference issues, explain behavior changes, list validation (tests, curl logs), and note config updates.
- Seek review for cross-cutting changes (services, tools, migrations) and update docs like `tools/README.md` when behavior shifts.

## Security & Configuration Tips
- Copy `.env.example` to `.env`, populate keys such as `OPENAI_API_KEY`, `JWT_SECRET_KEY`, and DB settings; never commit secrets.
- Set `RUN_MIGRATIONS=true` to apply Alembic migrations on startup; reserve `APP_ENV=development` for local work.
- Validate inputs in services and tools, and avoid logging sensitive payloads under `logs/`.
