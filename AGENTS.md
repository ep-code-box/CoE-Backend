# Repository Guidelines

## Project Structure & Module Organization
- `api/`: FastAPI routes (chat, embeddings, tools, health, etc.).
- `core/`: app factory, server runner, schemas, logging, middleware, agent graph.
- `services/`: business logic (tool dispatcher, DB, flows, chat orchestration).
- `tools/`: tool implementations and maps (`*_tool.py`, `*_map.py`). See `tools/README.md`.
- `routers/`, `config/`, `utils/`: routing, config models, helpers.
- `dbmig/`: Alembic migrations; `alembic.ini` at root.
- Entrypoint: `main.py`; container: `Dockerfile`; logs under `logs/`.

## Architecture Overview
- Flow: Client → `api/*_api.py` → `core.app_factory` wiring → `services/*` orchestrate → `services/tool_dispatcher.py` selects and calls `tools/*_tool.py` via `tools/core/registry.py` → external systems (RAG, DB) → response.
- Server: `core/server.py` wraps uvicorn; hot‑reload when `APP_ENV=development`.
- Data: SQLAlchemy models/migrations in `core/models.py` and `dbmig/versions/*`.

## Build, Test, and Development Commands
- Local run: `./run.sh` (creates venv, installs via uv, waits for DB, applies Alembic, starts on `:8000`).
- Dev hot‑reload: `APP_ENV=development PORT=8000 python main.py`.
- Alembic: `alembic upgrade head` (apply), `alembic revision -m "msg" --autogenerate` (create).
- Docker: `docker build -t coe-backend .` then `docker run --env-file .env -p 8000:8000 coe-backend`.
- Tests: `pytest -q`; async tests supported via `pytest-asyncio`.

## Coding Style & Naming Conventions
- Language: Python 3.11, 4‑space indent, type hints for public functions.
- Names: modules/functions `snake_case`, classes `PascalCase`; keep tools as `name_tool.py` with a paired `name_map.py`.
- Lint/format: `ruff check .` (and optionally `ruff format .`), import order: `isort .`.
- API paths live in `api/…_api.py`; keep responses pydantic‑validated where applicable.

## Testing Guidelines
- Place tests under `tests/` or alongside modules as `test_*.py`.
- Use `pytest` with clear unit tests for `core/` and `services/`; mark async tests with `@pytest.mark.asyncio`.
- Prefer isolated tests; for DB‑dependent cases ensure `.env` and DB are available, then run `pytest -q`.

## Change Impact Workflow
- Identify entrypoints: find affected routes or tools. Examples: `rg -n "@app\.get|@router" api/` or `rg -n "my_tool_name" tools/ services/`.
- Trace dependencies: follow calls across layers. Examples: `rg -n "ToolDispatcher|AgentState"`, `rg -n "ClassName|function_name"`. Review `tools/core/registry.py` and `services/tool_dispatcher.py` for selection paths.
- DB changes: if touching `core/models.py`, create a migration and test: `alembic revision -m "update" --autogenerate && alembic upgrade head`.
- Contract changes: update pydantic schemas in `core/schemas.py` and all call sites; add/adjust tests and example cURL in docs.
- Tool changes: update both `*_tool.py` and `*_map.py`; ensure contexts/endpoints are correct; validate via `/api/tools` routes if exposed.
- Verify: run `./run.sh`, check `logs/` outputs, hit `/health` or Swagger (`/docs`), and run `pytest -q`.

## Commit & Pull Request Guidelines
- Commits: concise, imperative; prefer Conventional Commit prefixes (e.g., `feat:`, `fix:`, `chore:`). Example: `feat(tools): add visualize_flow tool`.
- PRs: include what/why, scope of changes, test evidence (logs or curl), and linked issues. Update docs (e.g., `tools/README.md`) when extending tools.

## Security & Configuration Tips
- Copy `.env.example` to `.env`; never commit secrets (`.env` is git‑ignored). Required keys include `SKAX_API_KEY`, `OPENAI_API_KEY`, `JWT_SECRET_KEY`, DB settings (`DB_HOST`, `DB_PORT`).
- `RUN_MIGRATIONS=true|false` controls Alembic on startup; `APP_ENV=development` enables hot‑reload.
- Validate external calls and sanitize user inputs in tools and services.
