---
description: Review the current local diff using the code-reviewer subagent.
argument-hint: (no args — reviews uncommitted changes)
allowed-tools: Task, Bash, Read, Grep, Glob
---

Review my current uncommitted changes.

Diff under review:
!`git --no-pager diff HEAD 2>&1 | head -400`

Dispatch the **code-reviewer** subagent (Task tool) to review the diff above. Return its prioritized findings (🔴 Critical / 🟡 Warning / 🟢 Nit) with `file:line` references. Do not edit anything.
