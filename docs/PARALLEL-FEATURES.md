# Building a Full App: Parallel Features, Many PRs, Conflict Resolution

How this repo scales from "one `/feature` at a time" to "build a whole application
with many features in flight at once." Driven by the `build-app` workflow
(`.claude/workflows/build-app.js`, triggered by `/build-app`).

## The hard constraint

A single working directory **cannot** hold two feature-edits at once — parallel
agents editing the same checkout clobber each other. The solution is **git
worktrees**: each parallel feature gets its own isolated checkout + branch, so they
never touch each other's files. Claude Code provides this via `isolation: "worktree"`
on each agent.

```
                ┌─ worktree ─ feat/A ─ build+test ─► PR #1
 build-app ─────┼─ worktree ─ feat/B ─ build+test ─► PR #2   (all concurrent)
                └─ worktree ─ feat/C ─ build+test ─► PR #3
                              then ▼ integrate serially
```

## The strategy that keeps conflicts rare

Conflicts come almost entirely from **shared files** (the app factory, DB schema,
route registry). So:

1. **Decompose first.** A planning agent maps each feature to the files it will touch
   and flags overlapping pairs.
2. **Foundation first.** Build shared scaffolding (app factory, schema, base models)
   as **one** PR and merge it *before* fanning out. This removes ~90% of conflicts.
3. **Parallelize the leaves.** Independent features fan out into worktrees/PRs,
   touching mostly disjoint files (prefer adding a *new* blueprint file over editing a
   shared one).
4. **Integrate serially.** Merge PRs one at a time in the planned order. After each
   merge, rebase the rest onto the new `main`, resolve any textual conflicts, and
   **re-run `pytest` + `ruff`** before the next merge. Green tests = trustworthy
   auto-resolution.

## What's reliable vs. what needs a human

| Outcome | Automated? |
|---|---|
| Parallel development in isolated worktrees | ✅ |
| One PR per feature, opened concurrently | ✅ |
| Conflicts on **different files** | ✅ (no conflict) |
| **Textual** conflicts (same lines, e.g. two blueprint registrations) | 🟡 rebase + resolve + retest; tests are the safety net |
| **Logical** clashes (two features redefine the same behavior) | 🔴 flagged as `needsHuman` — needs a design decision |

## Running it

```
/build-app add a GET /version endpoint; add a GET /stats user-count endpoint; add a DELETE /account endpoint
```

or directly:

```
Workflow({ scriptPath: ".claude/workflows/build-app.js",
           args: { features: [ {slug, description}, ... ], base: "main" } })
```

The workflow returns: the PRs opened, what merged, which conflicts were auto-resolved,
and anything left for a human. Watch live progress with `/workflows`.

## Tuning the scale

- **2–4 overlapping features:** parallel build + serial integrate works smoothly.
- **Many features over the same area:** foundation-first matters more; consider
  batching (build a few, merge, rebase, repeat) rather than 10-wide fan-out.
- The token cost scales with the number of features × pipeline depth — this is a
  deliberate, opt-in workflow for exactly that reason.
