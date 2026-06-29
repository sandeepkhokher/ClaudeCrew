---
description: Run tests, then branch, commit, push, and open a PR.
argument-hint: "<commit / PR title>"
allowed-tools: Bash, Read
---

Ship the current changes. Title/message: **$ARGUMENTS**

Execute these steps in order and **stop immediately if any step fails**, reporting the failure:

1. **Gate** — `. .venv/bin/activate 2>/dev/null; ruff check . && pytest`. Abort if red.
2. **Branch** — if on `main`/`master`, create `git checkout -b feat/<short-slug-from-title>`. Otherwise stay on the current feature branch.
3. **Commit** — `git add -A && git commit -m "$ARGUMENTS"` (use a Conventional Commit type per the `git-pr-flow` skill).
4. **Push** — `git push -u origin HEAD`.
5. **PR** — `gh pr create --fill --title "$ARGUMENTS"`.

Report the PR URL at the end. Note: GitHub Actions will then run CI and the Claude PR review automatically.
