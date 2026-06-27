#!/usr/bin/env bash
# PostToolUse hook (matcher: Edit|Write).
# Auto-formats and auto-fixes the Python file that was just edited, using ruff.
# Reads the hook payload as JSON on stdin; never blocks (always exits 0).

input=$(cat)
file=$(printf '%s' "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('tool_input', {}).get('file_path', ''))" 2>/dev/null)

case "$file" in
  *.py)
    if command -v ruff >/dev/null 2>&1 && [ -f "$file" ]; then
      ruff format "$file" >/dev/null 2>&1
      ruff check --fix "$file" >/dev/null 2>&1
    fi
    ;;
esac

exit 0
