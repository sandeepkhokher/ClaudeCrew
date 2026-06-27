// build-app — parallel multi-feature builder.
//
// Builds N features concurrently, each in its OWN isolated git worktree on its own
// branch with its own PR, then runs a serial integration pass that detects and
// resolves merge conflicts (keeping the test suite green as the safety net).
//
// Invoke with args:
//   { features: [ { slug: "user-count", description: "..." }, ... ], base?: "main" }
//
// Strategy (see docs/PARALLEL-FEATURES.md):
//   Plan   → predict each feature's files + which pairs collide + a merge order
//   Build  → fan out: one worktree-isolated agent per feature → branch → tests → PR
//   Integrate → merge serially in order; rebase+resolve+retest the rest

export const meta = {
  name: 'build-app',
  description:
    'Build multiple features in parallel — each in an isolated git worktree on its own branch with its own PR — then integrate serially, resolving merge conflicts with the test suite as the safety net.',
  phases: [
    { title: 'Plan', detail: 'decompose features; predict file overlaps & merge order' },
    { title: 'Build', detail: 'one isolated worktree → branch → tests → PR per feature' },
    { title: 'Integrate', detail: 'merge serially; rebase+resolve+retest conflicts' },
  ],
}

let input = args
if (typeof input === 'string') {
  try {
    input = JSON.parse(input)
  } catch {
    input = {}
  }
}
const features = (input && input.features) || []
const base = (input && input.base) || 'main'

log(`build-app args: type=${typeof args}, features=${features.length}`)

if (!features.length) {
  log('No features supplied. Pass args: { features: [{slug, description}, ...] }')
  return { error: 'no features provided', argsType: typeof args }
}

log(`build-app: ${features.length} feature(s) → ${features.map((f) => f.slug).join(', ')}`)

// ---------------------------------------------------------------- Phase 1: Plan
phase('Plan')

const PLAN_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    features: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          slug: { type: 'string' },
          files: { type: 'array', items: { type: 'string' } },
        },
        required: ['slug', 'files'],
      },
    },
    conflictPairs: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          a: { type: 'string' },
          b: { type: 'string' },
          file: { type: 'string' },
        },
        required: ['a', 'b', 'file'],
      },
    },
    mergeOrder: { type: 'array', items: { type: 'string' } },
  },
  required: ['features', 'conflictPairs', 'mergeOrder'],
}

const plan = await agent(
  `You are the ARCHITECT planning a parallel build. These features will each be built on their own branch + PR:
${features.map((f) => `- ${f.slug}: ${f.description}`).join('\n')}

Read the current codebase (app/, tests/, .claude/skills/). For EACH feature, predict the files it will create or modify. Then list every PAIR of features that would modify the SAME existing file (likely merge conflicts — e.g. both registering a blueprint in app/__init__.py). Finally recommend a merge order: the feature touching the fewest shared files first.

Do NOT write code. Return the structured result.`,
  { phase: 'Plan', schema: PLAN_SCHEMA },
)

log(
  `Plan: ${plan.conflictPairs.length} predicted conflict pair(s); merge order ${plan.mergeOrder.join(' → ')}`,
)

// --------------------------------------------------------------- Phase 2: Build
phase('Build')

const BUILD_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    slug: { type: 'string' },
    branch: { type: 'string' },
    prUrl: { type: 'string' },
    testsPassed: { type: 'boolean' },
    summary: { type: 'string' },
  },
  required: ['slug', 'testsPassed', 'summary'],
}

const built = (
  await parallel(
    features.map((f) => () =>
      agent(
        `You are a BUILDER in an ISOLATED git worktree. Build exactly ONE feature and open a PR.

Feature slug: ${f.slug}
Description: ${f.description}
Base branch: ${base}

Follow .claude/skills/ (flask-api, python-testing). Steps:
1. Deps: \`. .venv/bin/activate 2>/dev/null || (python3 -m venv .venv && . .venv/bin/activate && pip install -q -r requirements.txt)\`
2. Implement the feature. PREFER a NEW file (e.g. a new blueprint app/${f.slug.replace(/-/g, '_')}.py) over editing shared files, to minimise conflicts. If you add a blueprint, register it in app/__init__.py.
3. Add tests in tests/ per the python-testing skill (success + failure paths).
4. Verify GREEN: \`. .venv/bin/activate && ruff check . && pytest\`. Do not continue if red.
5. Commit: \`git add -A && git commit -m "feat: ${f.slug}: <summary>"\`
6. Push + PR:
   \`git push origin HEAD:refs/heads/feat/${f.slug}\`
   \`gh pr create --base ${base} --head feat/${f.slug} --fill --title "feat: ${f.slug}"\`
7. Return branch="feat/${f.slug}", the prUrl from gh output, testsPassed, and a one-line summary.

On any failure, return testsPassed=false with the reason in summary.`,
        {
          label: `build:${f.slug}`,
          phase: 'Build',
          isolation: 'worktree',
          schema: BUILD_SCHEMA,
        },
      ),
    ),
  )
).filter(Boolean)

const green = built.filter((b) => b.testsPassed)
log(`Built ${green.length}/${features.length} with green tests; opened ${built.filter((b) => b.prUrl).length} PR(s).`)

if (!green.length) {
  return { built, plan, integration: null, note: 'No green builds — nothing to integrate.' }
}

// ----------------------------------------------------------- Phase 3: Integrate
phase('Integrate')

const INTEGRATE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    merged: { type: 'array', items: { type: 'string' } },
    conflictsResolved: { type: 'array', items: { type: 'string' } },
    needsHuman: { type: 'array', items: { type: 'string' } },
    report: { type: 'string' },
  },
  required: ['report'],
}

const prLines = built
  .map((b) => `- ${b.slug}: feat/${b.slug}, PR ${b.prUrl || '(none)'}, tests ${b.testsPassed ? 'green' : 'RED'}`)
  .join('\n')

const integration = await agent(
  `You are the INTEGRATION MANAGER. These feature PRs were just opened against ${base}:
${prLines}

Predicted conflicts: ${plan.conflictPairs.map((c) => `${c.a}↔${c.b} on ${c.file}`).join('; ') || '(none)'}
Recommended merge order: ${plan.mergeOrder.join(' → ')}

Operate in the main working directory. NEVER force-push to ${base}. Procedure:
1. Merge PRs ONE AT A TIME in the recommended order: \`gh pr merge <n> --squash --delete-branch\`. After each, \`git checkout ${base} && git pull\`.
2. Before merging each later PR, if GitHub marks it conflicting (\`gh pr view <n> --json mergeable,mergeStateStatus\`): check out its branch, \`git rebase origin/${base}\`, resolve conflicts (for duplicate blueprint registrations or appended routes, KEEP BOTH sides), then \`. .venv/bin/activate && ruff check . && pytest\` must be GREEN, then \`git push --force-with-lease\` and merge it.
3. If a conflict is a genuine logic clash you cannot safely resolve, skip it, leave its PR open, and add it to needsHuman with an explanation.

Return merged[], conflictsResolved[], needsHuman[], and a readable report of exactly what you did.`,
  { phase: 'Integrate', schema: INTEGRATE_SCHEMA },
)

log(`Integration: merged ${(integration.merged || []).length}, resolved ${(integration.conflictsResolved || []).length} conflict(s), ${(integration.needsHuman || []).length} need a human.`)

return {
  built,
  plan: { conflictPairs: plan.conflictPairs, mergeOrder: plan.mergeOrder },
  integration,
}
