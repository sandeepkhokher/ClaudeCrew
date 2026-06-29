#!/usr/bin/env bash
# SessionStart hook. Prints a short project status banner; its stdout is added
# to the session context so Claude starts oriented.

echo "=== ensemble • Flask Auth API ==="
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "branch : $(git branch --show-current 2>/dev/null)"
  changed=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  echo "dirty  : ${changed} uncommitted file(s)"
fi
echo "agents : architect · builder · test-engineer · code-reviewer · debugger"
echo "cmds   : /feature · /test · /review · /ship · /review-pr"
echo "run    : source .venv/bin/activate && pytest"
echo "===================================="
exit 0
