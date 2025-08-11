# Repository Guidelines

## Project Structure & Module Organization
- `main.py`: Entry point; fetches NewsBlur feeds, calls OpenAI, posts to Slack.
- `models.py`: Dataclasses for `Feed` and `Story`.
- `.github/workflows`: CI for Docker image build and Cloud Run deploy.
- `Dockerfile`: Python 3.13 slim image; installs `requirements.txt` and runs `main.py`.
- `requirements.txt`: Runtime deps (`openai`, `requests`, `beautifulsoup4`, `python-dotenv`).
- Suggested: place tests under `tests/` (e.g., `tests/test_main.py`).

## Build, Test, and Development Commands
- Create venv: `python -m venv .venv && source .venv/bin/activate`.
- Install deps: `pip install -r requirements.txt`.
- Dev deps (tests): `pip install -r requirements-dev.txt`.
- Run locally: `python main.py` (requires `.env`; see below).
- Type check (optional): `python -m mypy .` if `mypy` is installed.
- Docker build: `docker build -t newsblur-ai-agent .`.
- Docker run: `docker run --env-file .env newsblur-ai-agent`.

## Coding Style & Naming Conventions
- Python 3.13; follow PEP 8 (4-space indents) and PEP 257 docstrings.
- Naming: `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Prefer type hints; dataclasses are used for core models.
- Keep functions small and log at info/error where helpful.

## Testing Guidelines
- Framework: `pytest` recommended; place tests in `tests/` using `test_*.py`.
- Run tests: `pytest -q` (coverage enforced via `pytest.ini`, 80% minimum; XML artifact uploaded in CI).
- Cover feed parsing, HTML cleaning, and Slack payload formatting with unit tests.

## CI
- Tests run on PRs and pushes to `main` via `.github/workflows/python-tests.yaml`.
- Python `3.13` is used; coverage XML is uploaded as an artifact.

## Commit & Pull Request Guidelines
- Commits: concise, imperative mood (e.g., "update max tokens"). Group related changes.
- PRs: clear description, link issues, include run instructions and screenshots/logs if behavior changes.
- Keep diffs focused; update docs/config when env vars or behavior change.

## Security & Configuration Tips
- Configure via `.env` (not committed): `OPENAI_API_KEY`, `NEWSBLUR_USERNAME`, `NEWSBLUR_PASSWORD`, `SLACK_WEBHOOK_URL`, `MODEL_ID`, `MARK_STORIES_AS_READ=true|false`.
- Secrets for CI/CD are injected via GitHub Actions for Cloud Run jobs.
- Be mindful of PII in logs; avoid printing article contents unnecessarily.

## Agent-Specific Notes
- Tunables in `main.py`: `MAX_STORIES`, `MAX_CONTENT_LENGTH`, `MAX_TOKENS`, `TEMPERATURE`, `SYSTEM_PROMPT`.
- Network calls: NewsBlur REST, arbitrary article URLs, Slack webhook, and OpenAI API.
- When adding features, keep the request/response assembly isolated to ease testing and future retries.
