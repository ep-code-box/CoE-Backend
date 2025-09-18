# Repository Guidelines

## Project Structure & Module Organization
- `api/` holds FastAPI route modules (chat, embeddings, tools, health) that surface service capabilities.
- `core/` wires the application factory, server runner, schemas, middleware, and shared logging; `main.py` bootstraps uvicorn.
- `services/` implements business flows and the tool dispatcher; individual tool implementations live in `tools/` alongside their maps.
- Database models sit in `core/models.py` with Alembic migrations under `dbmig/versions/`; configuration helpers live in `config/` and `utils/`.
- Tests belong in `tests/` or adjacent `test_*.py` files; container entrypoints are provided via `Dockerfile` and `run.sh`.

## Build, Test, and Development Commands
- `./run.sh` creates a virtualenv, installs dependencies with `uv`, runs migrations, and starts the API on `:8000`.
- `APP_ENV=development PORT=8000 python main.py` launches the server with hot reload.
- `pytest -q` executes the full test suite; async tests use `pytest-asyncio` automatically.
- `alembic upgrade head` applies pending migrations; `alembic revision -m "message" --autogenerate` scaffolds new ones.
- `docker build -t coe-backend .` then `docker run --env-file .env -p 8000:8000 coe-backend` runs the service in a container.

## Coding Style & Naming Conventions
- Code targets Python 3.11 with 4-space indentation and type hints for public APIs.
- Use snake_case for modules and functions, PascalCase for classes, and follow the `name_tool.py` / `name_map.py` pairing for tools.
- Run `ruff check .` for linting and `isort .` to maintain import order; format code with `ruff format .` if needed.

## Testing Guidelines
- Prefer focused unit tests in `tests/`; name files `test_*.py` and match function names to the behavior under test.
- Mock external systems (RAG, DB) when possible; integration tests should load environment variables from `.env`.
- Ensure new features include regression coverage and run `pytest -q` before opening a pull request.

## Commit & Pull Request Guidelines
- Write Conventional Commit messages (e.g., `feat:`, `fix:`, `chore:`) that describe scope and intent succinctly.
- PRs should explain the change, reference related issues, summarize tests (`pytest`, curl, or logs), and note any config updates.
- Request reviews for cross-cutting changes (services, tools, migrations) and update docs like `tools/README.md` when behavior shifts.

## Security & Configuration Tips
- Copy `.env.example` to `.env`, populate keys such as `OPENAI_API_KEY`, `JWT_SECRET_KEY`, and database settings, and keep secrets out of version control.
- Set `RUN_MIGRATIONS=true` to let the app apply Alembic migrations on startup; use `APP_ENV=development` only for local work.
- Validate inputs in tools and services, especially when dispatching to external APIs, and log sensitive data sparingly under `logs/`.
