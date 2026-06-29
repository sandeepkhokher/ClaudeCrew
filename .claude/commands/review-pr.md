---
description: Fetch a GitHub PR's diff and review it with the code-reviewer subagent.
argument-hint: <PR number>
allowed-tools: Task, Bash, Read, Grep, Glob
---

Review GitHub PR #$ARGUMENTS.

PR metadata:
!`gh pr view $ARGUMENTS 2>&1 | head -20`

Diff:
!`gh pr diff $ARGUMENTS 2>&1 | head -500`

Dispatch the **code-reviewer** subagent (Task tool) on the diff above. Present its prioritized findings (🔴/🟡/🟢) with `file:line`. Then ask me whether to post the review to GitHub — only after I confirm, run `gh pr comment $ARGUMENTS --body "..."`.
