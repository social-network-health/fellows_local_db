# Parallel development (worktrees, lanes, fan-out)

When more than one Claude Code instance — or one orchestrator spawning subagents
— works on this repo's host at the same time, give each its own **git worktree**.
A worktree is a second working directory backed by the same `.git`, checked out
to its own branch. The hazard it removes is the common one: two agents sharing a
single working tree means a `git checkout` (or `reset`, or a stash pop) in one
yanks the branch and uncommitted changes out from under the other. Worktrees make
that impossible — each agent has its own files and its own branch.

This is opt-in, not mandatory. For a single agent, work in the primary checkout
as usual. Reach for a worktree the day you know two or more agents will run here.

## Create one

```bash
just wt <branch>          # worktrunk: create/switch worktree, symlink .venv, launch claude
just wtclean <branch>     # remove the worktree (and the branch if merged)
```

Plain git, no worktrunk:

```bash
git worktree add ../fellows-wt-<branch> -b <branch>
scripts/wt-setup.sh ../fellows-wt-<branch>     # symlink the heavy gitignored artifacts
git worktree remove ../fellows-wt-<branch>     # when done; then: git worktree prune
```

`scripts/wt-setup.sh` symlinks `.venv`, `app/fellows.db`, and `mcp_servers/.venv`
from the primary checkout. A bare worktree shares `.git` but gets **no** gitignored
files, so without this it can't run tests without a slow `just setup`. We symlink
rather than copy on purpose: a copied `.venv` breaks because its `bin/` shebangs
hardcode the original absolute path; a symlink resolves back to the real venv.
Playwright browsers live in a per-user global cache, so they're shared for free.

## The one rule that matters: port 8765 is host-global

Worktrees isolate the **filesystem, not the network.** The app's port (`8765`,
fixed — see CLAUDE.md) is shared across every worktree on the host. So:

| Activity | Across worktrees |
|---|---|
| Editing, reading, committing | parallel-safe |
| `just test-db`, conformance lints, pure-logic tests | parallel-safe |
| `just serve`, `test-api`, `test-e2e`, `test-mobile`, `serve-prod` | **must be serialized** |

The failure mode is sharper than a polite "address in use": every server-based
`just` recipe runs `scripts/ensure_port_8765_free.sh` first, which **kills**
whatever holds 8765. Start an e2e run in worktree B while worktree A is mid-e2e
and A's server is killed under it — A's run fails in a way that looks like a flaky
test, not a conflict. Stagger the server/e2e step; let everything else run in
parallel. Don't try to "fix" this by changing the port — 8765 is load-bearing for
the service-worker, manifest, and auth assumptions.

## Shared artifacts are shared

Because `wt-setup.sh` *symlinks* rather than copies:

- **`app/fellows.db`** is one file behind all worktrees. Reads are fine (that's
  the common case), but a `just db-rebuild`/`reset` in one worktree rewrites it
  for all of them — don't rebuild the directory DB while a sibling is testing.
- **`.venv`** is shared. Fine for this stdlib-only app; just know a `pip install`
  in one worktree affects all.
- **`relationships.db`** is *not* a concern: it lives in the browser's OPFS, and
  Playwright uses an ephemeral context per test, so there's no on-disk file to
  collide across worktrees.

## Subagents with harness worktree isolation

The Agent/Workflow `isolation: "worktree"` option creates a throwaway worktree per
subagent. Those share `.git` but, like any bare worktree, get **none** of the
gitignored artifacts — so a subagent that only reads/searches/edits is fine, but
one that needs to *run the test suite* must have `scripts/wt-setup.sh` pointed at
its worktree first. For human-launched parallel instances, `just wt` is the lever;
for an orchestrator spawning subagents, the harness option is.

## Cleanup

Worktrees and their branches accumulate. `just wtclean <branch>` (or
`git worktree remove … && git worktree prune`) when a lane is finished.
`git worktree list` shows what's currently checked out where.

---

# How to split the work

Everything above is mechanics. This is the part that decides whether parallel work
actually goes faster — extracted from the private-data-gate + mobile-rebuild effort
(`plans/EPIC_private_data_and_mobile.md`, completed 2026-06-07), which is the largest
multi-agent push this repo has run.

## Lanes, not PRs

**One worktree per *lane* — a file-ownership boundary — not per PR.** Split by PR and two
agents end up editing the same file; split by ownership and every merge is clean.

The lane set that worked here:

| Lane | Owns | Parallel? |
|---|---|---|
| **CORE** | `app/static/app.js` | **critical path — sequential, one owner, always** |
| WORKER | `app/static/vendor/sqlite-worker.js` | yes, against the RPC contract |
| STYLE | `app/static/styles.css`, `index.html` | yes, against the class / DOM-id contract |
| DOCS | `docs/*` | fully parallel |
| TESTS | `tests/e2e/*` | yes; baselines deferred to integration |

**`app/static/app.js` has exactly one owner and is never split across concurrent agents.**
CLAUDE.md says it's a single IIFE with no modules or classes; the consequence is that its
12,000+ lines cannot be meaningfully divided. It is the critical path, and everything else
parallelizes *around* it.

## Freeze the interfaces before fanning out

Run a **read-only analysis pass first**, and have it produce the contracts the lanes will
build against — the worker↔page RPC surface (with its `WORKER_RPC_VERSION` bump), the DOM/CSS
class names, the inventory of sites needing changes, the test-gap list.

Lanes then build against frozen names and merge cleanly. Skipping this step is what turns
parallel work into conflict resolution. Those findings are worth keeping: this repo's are in
`plans/EPIC_phase0_findings.md`.

## Fan-out needs no inter-agent comms

Independent lanes working against frozen interfaces return findings and diffs to the
orchestrator, which integrates. Reserve agent-to-agent coordination for the one case that
justifies it: a lane discovers the frozen interface is *wrong*. Even then it's cheaper for
the orchestrator to re-freeze and re-dispatch than for lanes to negotiate.

## The honest ceiling

The speedup comes from offloading WORKER/STYLE/DOCS/TESTS while CORE proceeds — **not** from
parallelizing `app.js`. Don't expect linear scaling. The single-file frontend and the single
test port bound it, and **port 8765, not agent count, is the real cap on concurrent
verification.**

## Integration order

Merge the lanes, resolve the `app.js` ↔ css ↔ worker seams, then run the full suite.

- **Re-baseline mobile snapshots LAST.** Pixels keep moving until the UI is final, so
  baselining early just means doing it twice.
- **Watch for coupled landings.** Some changes cannot go green separately and must ship as
  one unit. The gate work hit this: the desktop e2e suite and the `worker_data` wipe fixture
  run in a *no-folder* context but expect `relationships.db` to work — precisely the state the
  gate turns into browse-only. So the localStorage-only fix, the surface gating, and the new
  folder-attached fixture had to land together. When a test fixture encodes an assumption your
  change invalidates, the fixture change is part of the same landing.
