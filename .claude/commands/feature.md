---
description: Orchestrate the agent team to build a feature end-to-end (architect → builder → test-engineer → code-reviewer).
argument-hint: <feature description>
allowed-tools: Task, Read, Edit, Write, Bash, Grep, Glob
---

You are the **team lead**. Deliver this feature: **$ARGUMENTS**

Run the team as a pipeline, dispatching each specialist with the **Task tool** (subagents). Watch the progress tree as they work.

1. **Design** — dispatch the `architect` subagent with the feature description. Get back a plan (files, steps, test plan, risks).
2. **Build** — dispatch the `builder` subagent with the architect's plan. It implements the change.
3. **Test** — dispatch the `test-engineer` subagent to add tests and run `pytest` + `ruff check .`.
   - If tests fail, dispatch the `debugger` subagent to root-cause and fix, then re-run.
4. **Review** — dispatch the `code-reviewer` subagent on the diff (`git --no-pager diff HEAD`).
   - If it raises 🔴 Critical issues, loop back to `builder`/`debugger` to fix them.

Then summarize for me: what changed (files), test status, and the reviewer's verdict. **Do not commit or push** — that's the `/ship` command's job. Stop and ask me if requirements are ambiguous.
