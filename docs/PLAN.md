# Ideal Claude Code Setup — Agentic Team + CI/PR Pipeline

## Context

You want a reference-quality Claude Code project in `ClaudeCrew/` that shows off the full
agentic workflow: a **main agent acting as team lead** that dispatches **specialized subagents**
(architect, builder, tester, reviewer, debugger) which you can watch run in parallel, plus
**custom skills**, **slash commands**, **hooks**, a **GitHub PR + auto-review pipeline**, and a
**tmux dashboard** to visualize everything. It should be a working demo you can extend into
production projects.

Decisions locked in (via clarifying questions):
- **Use case:** Flask Auth API (register/login, hashed passwords, SQLite) — ties into the existing
  `../login.html`, has real logic to test and security to review.
- **Tooling:** install `gh` + `tmux` via Homebrew.
- **GitHub:** init git here and create a new repo via `gh`, then run the real PR pipeline.
- **Visualization:** both Claude Code's built-in subagent progress (`/workflows`) and a tmux dashboard.

Environment facts discovered: `ClaudeCrew/` is empty and not a git repo; `gh`, `tmux`, `node` are
NOT installed; Python 3.12.6 IS installed.

---

## Phase 0 — Install missing tooling (run first)

```bash
brew install gh tmux ruff
gh auth login        # interactive: choose GitHub.com → HTTPS → login via browser
python3 -m venv .venv && source .venv/bin/activate
```

(If Homebrew itself is missing we install it first via the official script.)

---

## Phase 1 — Demo app (the thing the agents work on)

A minimal but realistic Flask auth service so tests/reviews/CI have something real to chew on.

```
ClaudeCrew/
├── app/
│   ├── __init__.py        # Flask app factory: create_app()
│   ├── db.py              # sqlite3 connection + init_db() schema (users table)
│   ├── security.py        # password hashing via werkzeug.security
│   └── auth.py            # Blueprint: POST /register, POST /login
├── tests/
│   ├── conftest.py        # pytest fixture: app + test client + temp sqlite
│   └── test_auth.py       # register, login success, bad password, dup user
├── requirements.txt       # flask, werkzeug, pytest, ruff
├── pyproject.toml         # [tool.ruff] + [tool.pytest.ini_options]
└── wsgi.py                # entrypoint for `flask run` / gunicorn later
```

Run locally: `flask --app wsgi run -p 8765` then exercise `/register` and `/login`.

---

## Phase 2 — The agentic team (`.claude/agents/*.md`)

Each is a Markdown file with YAML frontmatter (`name`, `description`, `tools`, `model`) + a system
prompt body. The **main agent stays the team lead**: it reads your request and dispatches these via
the Agent tool; their progress shows live in the subagent tree / `/workflows`.

| Agent | Role | Tools (least-privilege) |
|-------|------|--------------------------|
| `architect.md` | Designs the approach, lists files to change, trade-offs. No edits. | Read, Grep, Glob, Bash(read-only) |
| `builder.md` | Implements the code per the architect's plan. | Read, Edit, Write, Bash |
| `test-engineer.md` | Writes + runs pytest, reports failures. | Read, Edit, Write, Bash |
| `code-reviewer.md` | Reviews the diff for bugs/security/quality. Read-only. | Read, Grep, Glob, Bash(git diff) |
| `debugger.md` | Root-causes failing tests/stack traces, proposes fix. | Read, Edit, Bash |

`description` fields are written so the lead auto-selects the right specialist (e.g. "Use PROACTIVELY
after code changes to review the diff").

---

## Phase 3 — Skills (`.claude/skills/<name>/SKILL.md`)

Reusable, model-invoked knowledge packs (frontmatter `name` + `description`; loaded on demand):
- **`flask-api`** — project conventions: app-factory pattern, blueprint layout, error/JSON response shape.
- **`python-testing`** — how we write pytest (fixtures, naming, coverage expectations, run commands).
- **`git-pr-flow`** — commit message convention, branch naming, how to open/maintain a PR with `gh`.

---

## Phase 4 — Slash commands (`.claude/commands/*.md`)

Prompt templates with frontmatter (`description`, `argument-hint`, `allowed-tools`). Support
`$ARGUMENTS`, `!`bash`` injection, `@file` refs.

| Command | What it does |
|---------|--------------|
| `/feature <desc>` | **Orchestrator** — lead dispatches architect → builder → test-engineer → code-reviewer in sequence, parallelizing where safe. The flagship "watch the team work" command. |
| `/test` | Runs `ruff check` + `pytest` and summarizes failures. |
| `/review` | Runs `code-reviewer` on the current local diff. |
| `/ship "<msg>"` | Full pipeline: run tests → create branch → commit → push → `gh pr create`. |
| `/review-pr <num>` | `gh pr checkout/diff` → `code-reviewer` → posts review comments via `gh`. |

---

## Phase 5 — Hooks (`.claude/hooks/` wired in `.claude/settings.json`)

- **PostToolUse** on `Edit|Write` → `format_python.sh`: auto-`ruff format` + `ruff check --fix` edited `.py`.
- **PreToolUse** on `Bash` → `guard_bash.sh`: block dangerous commands (`rm -rf /`, force-push to main, etc.).
- **SessionStart** → `session_start.sh`: print branch, git status, last test result as a banner.

`.claude/settings.json` also pins shared `permissions` (allow ruff/pytest/git/gh; deny destructive),
`env`, and the hooks map. `.claude/settings.local.json` (gitignored) holds personal overrides.

---

## Phase 6 — GitHub automation (`.github/workflows/`)

- **`ci.yml`** — on push/PR: setup Python → install → `ruff check` → `pytest`.
- **`claude-code-review.yml`** — on `pull_request`: uses `anthropics/claude-code-action@v1` to auto-review
  every PR (inline comments).
- **`claude.yml`** — on `@claude` mentions in issues/PR comments: lets you ask Claude to make changes from GitHub.

**Required once:** add repo secret `ANTHROPIC_API_KEY` (`gh secret set ANTHROPIC_API_KEY`) or install the
Claude GitHub app. The plan documents the exact tag to confirm against the latest action release.

---

## Phase 7 — Visualizing the agents

1. **Built-in:** the subagent progress tree shows each dispatched agent live; `/workflows` shows
   structured multi-agent runs. This is the primary, zero-setup view.
2. **tmux dashboard** — `scripts/agent-dashboard.sh` opens a session with panes:
   - pane 1: interactive `claude`
   - pane 2: `pytest` watch / last results
   - pane 3: `git status` + Flask dev server log
   Run with `./scripts/agent-dashboard.sh`.

---

## Phase 8 — Project memory & hygiene

- `CLAUDE.md` — conventions, run commands, agent/command/skill index, "lead dispatches subagents" rule.
- `.gitignore` — `.venv`, `__pycache__`, `*.db`, `.claude/settings.local.json`.
- `README.md` — quickstart + a "how the agentic setup works" tour you can reuse for prod projects.

---

## End-to-end flow you'll run after build

```
1. ./scripts/agent-dashboard.sh        # open the tmux view
2. /feature "add password reset endpoint"   # watch architect→builder→tester→reviewer
3. /test                                # confirm green
4. /ship "feat: password reset"         # branch, commit, push, open PR
5. → GitHub Actions runs ci.yml + claude-code-review.yml auto-review on the PR
6. /review-pr <num>                     # optional second-opinion review from your terminal
```

---

## Verification

- `source .venv/bin/activate && pytest -q` → tests pass.
- `ruff check .` → clean.
- `flask --app wsgi run -p 8765` → `curl` register/login returns expected JSON.
- `claude` → run `/test`, `/review`, and `/feature "..."`; confirm subagents appear in the progress tree.
- `gh repo view --web` → repo exists; open a test PR and confirm `ci.yml` runs and the Claude review bot comments.
- `./scripts/agent-dashboard.sh` → tmux session opens with all panes.

## Notes / things to confirm during build
- Exact latest tag of `anthropics/claude-code-action` will be verified against its repo at build time.
- New repo visibility (public vs private) — will default to **private** unless you say otherwise.
