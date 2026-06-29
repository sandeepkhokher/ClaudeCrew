---
name: python-testing
description: How we write and run pytest tests in this repo — fixtures, structure, naming, and coverage expectations. Use when adding tests or running the suite.
---

# Testing conventions

## Running
```bash
. .venv/bin/activate
pytest            # full suite (quiet, configured in pyproject.toml)
pytest -k login   # single area
ruff check .      # lint must also be clean
```

## Fixtures
- Use the fixtures in `tests/conftest.py`:
  - `app` — a fresh app with a temporary SQLite DB (isolated per test).
  - `client` — `app.test_client()` for issuing requests.
- Never hit the real database; the fixture guarantees isolation.

## Writing tests
- One behavior per test; name it `test_<thing>_<condition>` (e.g. `test_login_wrong_password`).
- For every endpoint cover: **success**, **bad input (400)**, and the relevant **failure path** (401/409).
- Assert on both `resp.status_code` and the JSON body where it matters.
- Don't weaken a test to make it green — if the code is wrong, fix the code (or escalate to the debugger).

## Definition of done
A change is done when `pytest` is green **and** `ruff check .` is clean.
