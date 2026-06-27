#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash).
# Blocks obviously destructive shell commands. Exit code 2 = block the tool call
# and surface stderr back to the model so it can adjust.

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))" 2>/dev/null)

block() {
  echo "BLOCKED by guard_bash hook: $1" >&2
  exit 2
}

case "$cmd" in
  *"rm -rf /"*|*"rm -rf ~"*|*"rm -rf /*"*) block "destructive recursive delete" ;;
  *":(){:|:&};:"*)                          block "fork bomb" ;;
  *"mkfs"*|*"> /dev/sda"*)                   block "disk-destroying command" ;;
esac

# Block force-push to a protected branch.
if printf '%s' "$cmd" | grep -Eq 'git +push.*(--force|-f)\b.*\b(main|master)\b'; then
  block "force-push to a protected branch"
fi

exit 0
