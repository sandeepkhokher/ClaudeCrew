---
name: git-pr-flow
description: Git branch/commit/PR conventions for this repo, including how to open and review PRs with the gh CLI. Use when committing, pushing, or opening/reviewing pull requests.
---

# Git & PR flow

## Branches
- Never commit feature work directly to `main`.
- Branch names: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`.

## Commits (Conventional Commits)
```
<type>: <imperative summary>

<optional body explaining the why>
```
Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.

## Opening a PR
```bash
git checkout -b feat/<slug>
git add -A && git commit -m "feat: ..."
git push -u origin feat/<slug>
gh pr create --fill            # or --title "..." --body "..."
```
Before pushing: `pytest` green and `ruff check .` clean.

## Reviewing a PR
```bash
gh pr diff <num>               # inspect the change
gh pr checkout <num>           # check it out locally to run it
gh pr comment <num> --body ".."  # leave a review comment
gh pr review <num> --approve|--request-changes --body ".."
```

## After merge
```bash
git checkout main && git pull && git branch -d feat/<slug>
```
