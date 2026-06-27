# idealClaude — an ideal Claude Code agentic setup

A self-contained, extensible example of getting the most out of Claude Code's agentic
capabilities. It pairs a small but real **Flask Auth API** with a full **agent team**,
**skills**, **slash commands**, **safety hooks**, a **GitHub PR + auto-review pipeline**,
and a **tmux dashboard** for watching the agents work.

Everything for this project — code, agent config, docs, and the original plan
(`docs/PLAN.md`) — lives in this directory so you can copy it into production projects.

---

## 1. Quick start

```bash
# from this directory
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest               # 8 tests should pass
ruff check .         # clean

# run the API
flask --app wsgi run -p 8765
```

Open Claude Code here (`claude`) and the agents, skills, commands, and hooks load automatically.

## 2. What's in the box

```
idealClaude/
├── app/                      # Flask Auth API (factory, db, security, auth blueprint)
├── tests/                    # pytest suite (isolated temp-SQLite per test)
├── .claude/
│   ├── agents/               # architect, builder, test-engineer, code-reviewer, debugger
│   ├── skills/               # flask-api, python-testing, git-pr-flow conventions
│   ├── commands/             # /feature /test /review /ship /review-pr
│   ├── hooks/                # guard_bash, format_python, session_start
│   └── settings.json         # permissions + hooks wiring
├── .github/workflows/        # ci.yml, claude-code-review.yml, claude.yml
├── scripts/agent-dashboard.sh# tmux multi-pane dashboard
├── docs/PLAN.md              # the original design plan
└── CLAUDE.md                 # project memory for Claude Code
```

## 3. The agent team (team-lead model)

The main Claude session acts as **team lead** and delegates to specialists via the Task tool.
Each agent has a focused role and least-privilege tools:

| Agent | Role |
|-------|------|
| **architect** | Designs the approach; read-only. |
| **builder** | Implements the code per the plan. |
| **test-engineer** | Writes & runs pytest. |
| **code-reviewer** | Reviews the diff (bugs/security/quality); read-only. |
| **debugger** | Root-causes failures and applies minimal fixes. |

Run the whole pipeline with one command:

```
/feature add a password-reset endpoint
```

You'll see each subagent appear in the live progress tree as it runs.

## 4. Watching the agents

- **Built-in (zero setup):** the subagent progress tree shows each delegated agent live.
  Use `/workflows` to inspect structured multi-agent runs.
- **tmux dashboard:** `./scripts/agent-dashboard.sh` opens three panes — Claude Code,
  a test shell, and a live `git status`/log. Detach with `Ctrl-b d`.

## 5. Ship → PR → automated review

```
/test                         # confirm green locally
/ship "feat: password reset"  # branch, commit, push, open PR
```

On the PR, GitHub Actions runs:
- **`ci.yml`** — ruff + pytest.
- **`claude-code-review.yml`** — Claude reviews the PR and leaves inline comments.
- **`claude.yml`** — mention `@claude` in a comment to ask for changes.

One-time GitHub setup (the build script does the repo creation; this is the secret):

```bash
gh secret set ANTHROPIC_API_KEY      # paste your Anthropic API key
```

(Or install the Claude GitHub App: https://github.com/apps/claude — verify the latest
action usage at https://github.com/anthropics/claude-code-action.)

## 6. Safety hooks

- **PreToolUse / Bash** → `guard_bash.sh` blocks destructive commands (`rm -rf /`,
  fork bombs, force-push to `main`).
- **PostToolUse / Edit|Write** → `format_python.sh` auto-formats edited Python with ruff.
- **SessionStart** → `session_start.sh` prints a status banner.

## 7. Extending this for production

- Add agents (e.g. `security-auditor`, `docs-writer`) as `.claude/agents/<name>.md`.
- Add skills for your domain conventions under `.claude/skills/<name>/SKILL.md`.
- Add commands for repeatable workflows under `.claude/commands/<name>.md`.
- Tighten `permissions` in `.claude/settings.json` and expand the hook guards.
- Swap SQLite for Postgres, add auth tokens/sessions, and grow the test suite.

See `docs/PLAN.md` for the full design rationale.
