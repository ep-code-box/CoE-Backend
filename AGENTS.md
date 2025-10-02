# Repository Guidelines

## Project Structure & Module Organization
`api/` serves FastAPI routers for chat, embeddings, tools, and health checks, while `services/` orchestrates business logic and dispatches tool maps under `tools/`. App configuration, middleware, schemas, and logging live in `core/`; `main.py` bootstraps uvicorn. Database tables are defined in `core/models.py`, with migrations under `dbmig/versions/`. Tests sit in `tests/` or local `test_*.py` files, and helper configs land in `config/` or `utils/`.

- **Guide Agent 경로**
  - `core/guide_agent/`: LangGraph 기반 가이드 에이전트 그래프와 노드, RAG 클라이언트, 결과 포매터가 포함됩니다.
  - `api/chat_api.py`: `context="guide"` 또는 `tool_input.guide_mode=true` 요청 시 가이드 에이전트가 실행되고 Markdown 요약/권장 도구를 제공합니다.
  - `GUIDE_AGENT_RAG_URL` 환경 변수로 RAG 파이프라인 엔드포인트를 지정할 수 있으며, 미설정 시 `http://coe-ragpipeline-dev:8001`를 기본값으로 사용합니다.
  - 가이드가 제안한 도구는 세션에 보관되며 `tool_input.guide_confirm=true`로 실행, `tool_input.guide_cancel=true`로 취소할 수 있습니다. 인자가 필요하면 `tool_input.guide_tool_args={...}`로 전달하세요.

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
