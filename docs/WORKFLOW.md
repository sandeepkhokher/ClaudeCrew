# How the Agentic Workflow Actually Works

A detailed, step-by-step explanation of how the pieces in this repo fit together —
written to clear up the most common confusion: **how do the agents "talk" to each
other, and what really happened when `/feature` ran?**

> **The one idea to take away first:**
> The sub-agents do **not** talk to each other. They can't even see each other.
> There is one **team lead** (your main Claude session). It calls each specialist
> one at a time, reads what that specialist hands back, and then decides what to do
> next. All "collaboration" is the team lead carrying messages between isolated
> workers. Think of a manager phoning one consultant, hanging up, then phoning the
> next and repeating what the first one said.

---

## Part 1 — The four building blocks

Everything here is just **Markdown files and shell scripts** in the `.claude/`
folder. There is no magic; Claude Code reads these files and changes its behavior.

| Block | Lives in | What it is | Who triggers it |
|-------|----------|-----------|-----------------|
| **Slash command** | `.claude/commands/<name>.md` | A saved prompt template you fire with `/<name>` | **You** (by typing `/feature ...`) |
| **Sub-agent** | `.claude/agents/<name>.md` | A specialist worker with its own job, tools, and **its own separate memory** | **The team lead** (via the Task tool) |
| **Skill** | `.claude/skills/<name>/SKILL.md` | A reference card of conventions, loaded only when relevant | **Claude itself**, when it decides the topic is relevant |
| **Hook** | a script wired in `.claude/settings.json` | Automatic code that runs on an event (before a tool, after an edit, etc.) | **The harness** (Claude Code itself), automatically |

Let's go through each one properly.

---

## Part 2 — Sub-agents and the golden rule of communication

### What a sub-agent file looks like
Open `.claude/agents/architect.md`. The top part (between the `---` lines) is
**frontmatter** — settings:

```yaml
---
name: architect
description: Use PROACTIVELY at the start of any non-trivial feature... Read-only.
tools: Read, Grep, Glob, Bash      # the ONLY tools this agent may use
model: inherit                     # which model it runs on
---
You are the **Architect** on this team. You design; you do not implement...
```

- `name` — how the team lead refers to it.
- `description` — **this is critical**: the team lead reads these descriptions to
  decide *which* specialist to call for a given job. Good descriptions = the lead
  picks the right agent automatically.
- `tools` — a security fence. The `architect` and `code-reviewer` deliberately have
  **no Edit/Write**, so they physically cannot change your code — they can only read
  and report.
- The body below `---` is the agent's **system prompt** — its personality and rules.

### The golden rule: agents are isolated
This is the part that's confusing, so read slowly:

1. Each sub-agent runs in a **brand-new, empty conversation**. It does **not** see
   our chat, it does **not** see what other agents did, and it does **not** see the
   project history. It starts blind.
2. The **only** thing a sub-agent receives is **one prompt** — the instructions the
   team lead writes for it at the moment it's called.
3. The sub-agent does its work (reading files, running tests, etc.) in its own
   private scratch space, then returns **one final message** — its result.
4. The team lead receives **only that final message**. It does not see the agent's
   intermediate steps. That final message is the entire "hand-off."

So the communication channel is dead simple:

```
        team lead  ──(writes a prompt)──►  sub-agent
        team lead  ◄──(one final report)──  sub-agent
```

That's it. No agent-to-agent channel exists. If the `test-engineer` needs to know
what the `architect` decided, it's because **the team lead copied the architect's
report into the test-engineer's prompt.** The lead is the messenger.

### Why isolation is a feature, not a limitation
- Each specialist gets a clean, focused context — no distraction from unrelated chatter.
- A read-only reviewer can't be "talked into" editing code.
- You can run several agents in **parallel** because they don't depend on a shared
  state — each is self-contained.

---

## Part 3 — Skills: shared conventions, loaded on demand

A skill is a cheat-sheet. Look at `.claude/skills/flask-api/SKILL.md`:

```yaml
---
name: flask-api
description: Conventions for this Flask Auth API — app-factory, blueprints,
             JSON response shapes, safe SQLite access. Use when adding endpoints.
---
# Flask API conventions
- Always use parameterized SQL...
- success → {"message": ...}, error → {"error": ...}
...
```

How it works:
- Claude is always aware of the skill's **name + description** (cheap, always loaded).
- When a task actually touches that topic (e.g. "add an endpoint"), Claude **opens
  the full `SKILL.md`** to follow the detailed rules. When the topic is irrelevant,
  the body stays unloaded — saving context.
- In this repo, the agents' prompts explicitly say things like *"follow the
  `flask-api` skill,"* so the builder and reviewer pull in the same conventions and
  stay consistent. **The skill is how five different agents all "agree" on the house
  style without being told the rules each time.**

---

## Part 4 — Hooks: automatic, deterministic guardrails

Hooks are **not** AI. They are scripts the harness runs **automatically** on events,
configured in `.claude/settings.json`. This repo wires three:

| Event | Script | What it does |
|-------|--------|--------------|
| `PreToolUse` on `Bash` | `guard_bash.sh` | Inspects every shell command *before* it runs; blocks dangerous ones (`rm -rf /`, force-push to `main`). Returns exit code 2 to veto. |
| `PostToolUse` on `Edit`/`Write` | `format_python.sh` | After any file edit, auto-runs `ruff format` on it. Your code is tidied without anyone asking. |
| `SessionStart` | `session_start.sh` | Prints the project banner you see at the top of each session. |

Key point: hooks fire **no matter what** — even for sub-agents, even in
"skip permissions" mode. That's why the safety guard is trustworthy. (Earlier in
this very session, the guard hook blocked one of my own test commands because it
contained `rm -rf /` — proof it's always on.)

---

## Part 5 — What a slash command actually is

`/feature` is just the file `.claude/commands/feature.md`. A command file is a
**prompt template**. When you type:

```
/feature "add a password reset endpoint"
```

Claude Code does three substitutions on the file's body **before** handing it to the
team lead as a prompt:

1. `$ARGUMENTS` → your text (`add a password reset endpoint`).
2. Any `` !`some command` `` → it runs that shell command and pastes the output in
   (e.g. `/review` injects `!`git diff HEAD`` so the live diff is in the prompt).
3. Any `@path/to/file` → pastes that file's contents in.

The resulting text becomes a normal instruction to the team lead. So a slash command
is simply **"a long, carefully-worded message you didn't have to retype."** Our
`feature.md` body literally says *"You are the team lead… you MUST delegate each step
to a sub-agent… 1. dispatch architect, 2. dispatch builder…"* — which is what makes
the lead run the pipeline instead of doing it alone.

---

## Part 6 — Step-by-step: exactly what happened in this session

Here is the real run that built the password-reset feature, with nothing skipped.
"TL" = team lead (the main session).

### Phase A — the build pipeline

**Step 1 — You invoke the pipeline.**
The `/feature` template expands and tells TL: *"deliver the password-reset feature
by delegating to architect → builder → test-engineer → code-reviewer."* TL now owns
the plan but writes none of the code itself.

**Step 2 — TL dispatches the `architect`.**
TL calls the Task tool with `subagent_type: architect` and a prompt it composed:
*"Design password reset for this Flask Auth API. Here's the layout (app/auth.py,
db.py, security.py)… follow the flask-api conventions… produce a plan + test plan."*
- The architect wakes up **blind**, reads the actual files (`Read`/`Grep` — it has no
  Edit tool), and **discovers the endpoint already existed** (from your earlier in-pane
  run). It can't change code, so it returns a **report**: *"code is already here; the
  real gap is test coverage — here are 10 test cases to add."*
- TL receives only that report.

**Step 3 — TL skips the `builder`.**
TL reads the architect's report, sees the code already exists and is correct, and
**decides** the builder has nothing to do. This decision is TL's — the architect
didn't "tell" the builder anything; TL judged it. (This is the orchestration value:
TL adapts the plan to what it learned.)

**Step 4 — TL dispatches the `test-engineer`.**
TL composes a new prompt that **includes the architect's test list** (this is the
"hand-off" — TL copying one agent's output into the next agent's input). The
test-engineer wakes up blind, but its prompt contains everything it needs.
- It has `Edit`/`Write`, so it adds 11 tests to `tests/test_auth.py`.
- **As it saves the file, the `format_python.sh` hook fires automatically** and runs
  ruff on it.
- It runs `pytest` → **19 passed** → returns a report: *"19 passing, all green."*

**Step 5 — TL dispatches the `code-reviewer`.**
TL hands it the diff to review. The reviewer (read-only) inspects `app/auth.py` and
the tests and returns a graded report: *"No critical issues, but 2 warnings: (1) a
timing side-channel lets attackers enumerate usernames by response speed; (2) the
'missing username' case isn't tested."*

**Step 6 — TL reports back to you** and stops (the `/feature` rule says *don't commit*).
You chose **option 1: fix the warnings.**

### Phase B — the fix cycle (this is where collaboration really shows)

**Step 7 — TL dispatches the `builder`** with a precise prompt describing the
timing fix (add a `dummy_verify` that burns equal CPU on the "unknown user" path).
- Builder edits `app/security.py` and `app/auth.py`, runs a quick `import app` check
  (which passes), and reports success.
- **But it made a mistake:** it used `dummy_verify` in `auth.py` without adding it to
  the import line. The import-only check didn't catch it (importing a module doesn't
  run the function body).

**Step 8 — TL dispatches the `test-engineer`** to add the missing test and run the suite.
- It runs `pytest` → **2 tests FAIL** with `NameError: dummy_verify is not defined`.
- Crucially, it **does not hack the tests to pass.** It returns a report: *"this is a
  real app bug — the import is missing in auth.py:11 — fix the code, not the tests."*
- **This is the whole point of the pipeline:** an independent checker caught a bug the
  builder introduced and was confident about, because it ran the code for real.

**Step 9 — TL dispatches the `debugger`** with the test-engineer's diagnosis.
- It adds the one-line import, re-runs `ruff` + `pytest` → **20 passed, clean** →
  reports green.

**Step 10 — TL dispatches the `code-reviewer` again** for a final pass.
- It confirms both original warnings are resolved, no new bugs → *"ready to ship."*

**Step 11 — TL summarizes the whole cycle to you.**

Notice: at no point did the builder talk to the test-engineer, or the test-engineer
to the debugger. **TL carried each report into the next agent's prompt.** That relay
*is* the collaboration.

---

## Part 7 — The full picture as a diagram

```
   YOU
    │  type:  /feature "add a password reset endpoint"
    ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  Claude Code expands .claude/commands/feature.md             │
 │  ($ARGUMENTS filled in) → hands the text to the TEAM LEAD    │
 └─────────────────────────────────────────────────────────────┘
    │
    ▼
 ╔═════════════════  TEAM LEAD (your main session)  ═════════════════╗
 ║  Owns the plan. Calls one specialist at a time via the Task tool. ║
 ║  Reads each report. Decides the next move. Relays info forward.    ║
 ╚═══════════════════════════════════════════════════════════════════╝
    │              │                  │                 │
    │ prompt       │ prompt+          │ prompt+         │ prompt+
    │              │ architect's plan │ diff            │ diagnosis
    ▼              ▼                  ▼                 ▼
 ┌────────┐   ┌──────────┐     ┌──────────────┐   ┌──────────┐
 │architect│   │  builder │     │test-engineer │   │ debugger │   ...each is a
 │(read-   │   │ (edits)  │     │ (edits+tests)│   │ (fixes)  │      SEPARATE,
 │ only)   │   │          │     │              │   │          │      BLIND
 └────────┘   └──────────┘     └──────────────┘   └──────────┘      context
    │              │                  │                 │
    │ report       │ report           │ report          │ report
    └──────────────┴──────────────────┴─────────────────┘
                          ▲
   each specialist returns ONE final message; the lead reads it and moves on

   Meanwhile, automatically and invisibly:
   • every file an agent saves   → format_python.sh (ruff) runs
   • every shell command an agent runs → guard_bash.sh checks it first
   • agents consult .claude/skills/* to follow the same house conventions
```

---

## Part 8 — How it reaches GitHub (the last mile)

Once the local pipeline is green, the GitHub side takes over:

1. `/ship` (or me running git): create a branch, commit, push, open a PR with `gh`.
2. **GitHub Actions** (`.github/workflows/`) run *on GitHub's servers*, not your machine:
   - `ci.yml` → installs deps, runs `ruff` + `pytest` on the PR.
   - `claude-code-review.yml` → a **second, automatic** Claude that reviews the PR and
     comments on it (separate from the local `code-reviewer` agent).
3. `/review-pr <n>` → the local `code-reviewer` agent reviews a PR and I post its
   verdict to GitHub with `gh`.

> Two different reviewers, easy to mix up:
> - **Local `code-reviewer` agent** → runs in our chat, reports here (or I post it up).
> - **GitHub Action bot** → runs on GitHub automatically when a PR opens, comments on
>   the PR page. It only "trusts" its workflow file once that file is on the `main`
>   branch — which is why a PR that *edits* the workflow won't be auto-reviewed.

---

## Part 9 — One-paragraph summary

You type a **slash command**, which is a saved prompt that turns your main session
into a **team lead**. The team lead calls **sub-agents** one at a time through the
Task tool. Each sub-agent is a blind, isolated worker with a fixed job and a limited
toolset; it gets one prompt, does its work privately, and returns one report. The
team lead is the only thing that sees all the reports, and it **relays** each one into
the next agent's prompt — that relay is the entire "collaboration." All the agents
follow the same **skills** (shared convention cheat-sheets) so their output is
consistent, and **hooks** run automatically in the background to format code and block
dangerous commands. When everything is green, the work goes to GitHub, where **Actions**
re-run the tests and a separate Claude bot reviews the PR.

---

## Part 10 — Commands vs. Workflows (the `/build-app` engine)

Everything in Parts 1–6 used the **team-lead** style: the main Claude *decides on the
fly* which sub-agent to call next. That's flexible but not perfectly repeatable. For
big, fixed-shape jobs (like "build 5 features in parallel, each its own PR, then
integrate") you want the *structure* to be guaranteed. That's what a **workflow** is.

### A workflow is a program that orchestrates agents
- A **slash command** (`.claude/commands/<name>.md`) is a saved **prompt** — text. The
  **LLM** reads it and decides what to do.
- A **workflow** (`.claude/workflows/<name>.js`) is a saved **program** — JavaScript.
  The **code** decides the structure (what runs, in what order, in parallel or serial,
  with loops/conditionals); the **agents** still do the actual work.

| | Slash command | Workflow |
|---|---|---|
| File | `.claude/commands/<name>.md` | `.claude/workflows/<name>.js` |
| It is a… | saved **prompt** (text) | saved **program** (code) |
| Who orchestrates | the LLM, on the fly | the **script**, deterministically |
| Parallelism / loops | only if the model chooses | explicit and guaranteed |
| Best for | "do this task" | "run these N agents in this exact shape, every time" |

They **compose**: `/build-app` is a *command* whose only job is to launch the
*workflow*. Command = friendly front door; workflow = the deterministic engine.

### Why JavaScript (a `.js` file)?
Because expressing the structure needs real code, not prose. The Workflow engine gives
you functions — `agent()`, `parallel()`, `pipeline()`, `phase()`, `log()` — and you use
ordinary JS around them:

```js
features.map(f => () => agent(..., { isolation: 'worktree' }))  // fan out one agent per feature
await parallel(...)                                             // run them all at once, wait for all
if (!green.length) return { ... }                              // skip integration if nothing built
```

`.map()` is how "a list of 3 features" becomes "3 parallel agents" — a markdown prompt
can't loop over a list and spawn an agent per item. Saving it as a **file** makes it a
**reusable, editable tool** that `/build-app` points at.

### Two ways a workflow controls things (important!)
This is the key insight from `build-app.js`:

- **Structure is deterministic code.** `isolation: 'worktree'` is a *flag* on an
  `agent()` call — the **runtime** creates the git worktree automatically. We never
  wrote `git worktree add`.
- **Actions are delegated English.** "Merge the PRs," "rebase and resolve conflicts" are
  *sentences inside an agent's prompt* — the **agent** runs the real `gh`/`git` commands
  with its Bash tool, deciding the details (like how to resolve a conflict).

```
   JS in the .js file          →  STRUCTURE (rigid skeleton)
   phase / parallel / agent /     what runs, order, isolation, parallelism
   isolation:'worktree'

   Text inside agent(`...`)     →  ACTIONS (flexible muscle)
   "merge the PRs", "rebase"       the agent runs the real commands itself
```

### How you provide the features to `/build-app`
Just list them, separated by `;` (or new lines):

```
/build-app add a GET /version endpoint; add a GET /stats user-count endpoint; add a DELETE /account endpoint
```

The command turns each phrase into a `{ slug, description }` and hands the list to the
workflow, which fans out one isolated worktree → branch → PR per feature, then integrates
them serially (resolving conflicts, with the test suite as the gate). The equivalent
structured call is:

```js
Workflow({ scriptPath: ".claude/workflows/build-app.js",
           args: { base: "main", features: [ { slug, description }, ... ] } })
```

Tips: be specific about *what* and *which file* each feature touches; the more
independent the features (different files), the cleaner the parallelism. See
`docs/PARALLEL-FEATURES.md` for the full strategy.
