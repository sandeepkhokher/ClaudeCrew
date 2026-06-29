---
description: Build several features in parallel — each its own worktree, branch, and PR — then integrate with conflict resolution. Runs the build-app workflow (multi-agent, token-heavy).
argument-hint: feature one; feature two; feature three
allowed-tools: Workflow, Bash, Read
---

The user wants to build multiple features in parallel: **$ARGUMENTS**

Do this:

1. Parse `$ARGUMENTS` into a list of features (split on `;` or newlines). For each,
   derive a short kebab-case `slug` and keep the full text as `description`.
2. Run the **build-app workflow** via the Workflow tool, passing the features as args:

   `Workflow({ scriptPath: ".claude/workflows/build-app.js", args: { features: [ { slug, description }, ... ], base: "main" } })`

   This is an explicit multi-agent orchestration opt-in. It will:
   - **Plan** — predict each feature's files and which pairs will collide.
   - **Build** — fan out one isolated worktree per feature → branch → tests → PR.
   - **Integrate** — merge serially, rebasing/resolving conflicts with the test suite as the gate.
3. When the workflow returns, summarize for the user: the PRs opened, what merged,
   which conflicts were auto-resolved, and anything left needing a human.

Note: building the **shared foundation first** (app factory, DB schema) as a single
merged PR before fanning out dramatically reduces conflicts — see
`docs/PARALLEL-FEATURES.md`.
