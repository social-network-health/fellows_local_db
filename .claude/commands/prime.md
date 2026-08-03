# Prime — fellows_local_db
> Read-only orientation: understand the system, then summarize. Do NOT switch branches,
> pull, or create a worktree while priming — just orient. (CLAUDE.md § Workflow owns
> branching; `docs/worktrees.md` owns parallel work.)

## Run
git ls-files
git status -sb          # branch + ahead/behind + dirty state
git worktree list       # sibling worktrees another agent may be using
just                    # the command surface (62 recipes — test targets, wt, deploy)

## Read
docs/Architecture.md              # the specialization + PNA conformance layer; start here
docs/worktrees.md                 # parallel-development model: lanes, frozen interfaces, port 8765
docs/persistence_and_upgrades.md  # what survives an update, and why
docs/feature_platform_matrix.md   # what works where (desktop vs phone vs folder-gated)

## Know before you touch code
The frontend is the system's centre of gravity and the docs above will not tell you this:

- **`app/static/app.js` is ~12,600 lines, a single IIFE** — no modules, no classes. It is the
  main surface for most feature work and it has **exactly one owner** at a time. Don't read it
  whole; grep to the feature you need.
- **`app/server.py` (~670 lines)** is the whole backend. Small on purpose — this is a
  local-only app, not a service.
- **`app/static/vendor/sqlite-worker.js`** owns OPFS. The main thread is an RPC client and
  must never touch `navigator.storage.getDirectory` or hold a sync access handle.
- **Two databases:** `relationships.db` (user-authored, per-user, survives updates) and
  `fellows.db` (imported contacts, regenerated every build). Cross-DB joins ATTACH read-only.

Read the specific file the task needs — not all of `docs/` (22 files, ~7,000 lines) and not
all of `plans/` (46 files). `docs/users_manual.md` is worth reading **only** for UI/UX work.

## Before summarizing
- Note your branch. If a sibling worktree looks like it's on a related feature, flag the overlap.
- Say which of the two DBs and which of the three code surfaces the task will touch.
- Don't restate worktree or branching policy — CLAUDE.md and `docs/worktrees.md` own it.
