# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is
A reference "ideal" Claude Code setup built around a small **Flask Auth API**
(register/login with hashed passwords, SQLite). The app is deliberately simple so
the focus stays on the *agentic workflow*: a team-lead agent that dispatches
specialized subagents, plus skills, slash commands, hooks, and a GitHub PR pipeline.

## How to work here (team-lead model)
- You are the **team lead**. For non-trivial work, dispatch the specialized subagents
  in `.claude/agents/` via the Task tool rather than doing everything yourself:
  `architect` → `builder` → `test-engineer` → `code-reviewer`, with `debugger` when
  tests fail. The `/feature` command runs this pipeline.
- Follow the repo conventions captured as skills in `.claude/skills/`
  (`flask-api`, `python-testing`, `git-pr-flow`).
- Definition of done: `pytest` green **and** `ruff check .` clean.

## Commands
| Slash command | Purpose |
|---------------|---------|
| `/feature <desc>` | Run the full team pipeline to build a feature. |
| `/test` | Run ruff + pytest, summarize. |
| `/review` | Review the local diff with the code-reviewer subagent. |
| `/ship "<msg>"` | Test → branch → commit → push → open PR. |
| `/review-pr <num>` | Review a GitHub PR. |

## Development
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                       # tests
ruff check .                 # lint
flask --app wsgi run -p 8765 # run the API locally
```

Example requests:
```bash
curl -X POST localhost:8765/register -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"supersecret"}'
curl -X POST localhost:8765/login -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"supersecret"}'
```

## Conventions (summary — full detail in `.claude/skills/`)
- App-factory pattern; routes in blueprints; DB access via `app/db.py`.
- **Always** parameterized SQL. Never store/log raw passwords.
- JSON responses: success `{"message": ...}`, error `{"error": ...}`.
- Branch `feat/<slug>`; Conventional Commits; never commit straight to `main`.

## Safety
A `PreToolUse` hook blocks destructive shell commands (e.g. `rm -rf /`, force-push to
`main`). A `PostToolUse` hook auto-formats edited Python with ruff. See `.claude/settings.json`.
