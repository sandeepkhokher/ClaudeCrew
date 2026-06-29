#!/usr/bin/env bash
# A tmux dashboard for watching the agentic workflow:
#   pane 0 (left)        : interactive Claude Code   (run /feature, /test, /ship ...)
#   pane 1 (top-right)   : a shell for running pytest on demand
#   pane 2 (bottom-right): live git status + recent commits
#
# Usage:  ./scripts/agent-dashboard.sh
# Detach with Ctrl-b then d. Re-running re-attaches the existing session.

set -euo pipefail

SESSION="ensemble"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is not installed. Run: brew install tmux" >&2
  exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  exec tmux attach -t "$SESSION"
fi

tmux new-session -d -s "$SESSION" -n main -c "$ROOT"

# Pane 0: Claude Code (falls back to a shell if the CLI isn't on PATH).
tmux send-keys -t "$SESSION":main.0 \
  'command -v claude >/dev/null && claude || echo "claude CLI not found on PATH — open a shell here"' C-m

# Pane 1: test shell.
tmux split-window -h -t "$SESSION":main -c "$ROOT"
tmux send-keys -t "$SESSION":main.1 \
  '. .venv/bin/activate 2>/dev/null; echo "TEST PANE — run: pytest   (or: ruff check .)"' C-m

# Pane 2: live git status loop (uses watch if available, else a simple loop).
tmux split-window -v -t "$SESSION":main.1 -c "$ROOT"
tmux send-keys -t "$SESSION":main.2 \
  'if command -v watch >/dev/null 2>&1; then watch -c -n 5 "git -c color.ui=always status -s; echo; git -c color.ui=always log --oneline -8"; else while true; do clear; git status -s; echo; git log --oneline -8; sleep 5; done; fi' C-m

tmux select-pane -t "$SESSION":main.0
exec tmux attach -t "$SESSION"
