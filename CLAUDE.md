# CLAUDE.md

Read README.md for project setup, API docs, and test commands. Read docs/Architecture.md for fellows_local_db's specialization and PNA-spec conformance (axis picks, fellows-specific schema, HTTP routes, debug placeholders); docs/Architecture.md cross-links into the [personal_network_toolkit](https://github.com/social-network-health/personal_network_toolkit) repo for the universal PNA architecture.

<!-- BEGIN SHARED: org-conventions v6 -->
<!-- Canonical copy: social-network-health/docs/shared/org-conventions.md
     Do not edit this block in place. Edit the canonical copy and propagate. -->

> **⚙ Shared, generated section — don't edit it here.** Everything from this line down to
> *"Changing this block"* is identical in every repo in the org. Change it in the canonical
> copy (hub `docs/shared/org-conventions.md`) and run `just sync-conventions`; an edit made
> in place will be reported as `EDITED` and then overwritten. Repo-specific guidance belongs
> in this file's *other* sections, which the tooling never touches.

## The organization

The repos of the **[social-network-health](https://github.com/social-network-health)** GitHub
org. A developer normally has them **all checked out side by side in one parent directory**,
so from any repo root every other repo is at `../<name>`. Write cross-repo paths relative to
the repo root, never absolute — the parent directory differs per host.

The set changes as repos are added and archived, so no document states a count; ask the org
(`gh repo list social-network-health`) or read `RELATED_REPOS.md`.

**[`RELATED_REPOS.md`](https://github.com/social-network-health/social-network-health/blob/main/RELATED_REPOS.md)**
in the hub repo is the single source of truth for what those repos are and what each is for.
Don't restate the list in a repo's own docs — a second copy is a second thing to forget.

The layout is a convention of the working environment; it could change, but it holds for now.
It lives in `CLAUDE.md` rather than agent memory because **memory is keyed to the working
directory** — a worktree at a different path starts with a fresh memory dir. A committed file
is the only channel that reaches every worktree and every concurrent agent.

## Planning has four layers

| # | Question | Lives in |
|---|---|---|
| 1 | "What is the software program?" | hub [`software-plan.md`](https://github.com/social-network-health/social-network-health/blob/main/software-plan.md) — the M1/M2/M3 summary |
| 2 | "What should the org be doing?" | hub [`plans/`](https://github.com/social-network-health/social-network-health/tree/main/plans) + `plans/ORG-TASKS.md` |
| 3 | "Where is this repo headed?" | **this repo's** `docs/roadmap.md` |
| 4 | "What's in flight?" | **this repo's** GitHub issues and active branches |

Record a thought at the layer matching its scope.

**Layer 2 is org-only.** Work actionable inside one existing repo belongs in that repo;
`ORG-TASKS.md` links down to it rather than restating its status. **Layer 1 is narrower than
the organization** — `software-plan.md` summarizes the software and research program, not community
building, the toolkit wiki, or educational materials.

Dated files under `plans/` are append-only thinking artifacts. Never update one; write a new
one. `ORG-TASKS.md` is the sole exception — it is kept current.

## Cross-repo working rules

Each of these was learned the hard way in one repo. They apply in all of them.

- **PR and issue bodies via `--body-file`, never an inline `--body`.** Backticks and `$(…)`
  get shell-interpreted and silently drop content — a commit hash has been lost this way.
- **After a PR merges, verify every intended commit actually landed.** A dropped commit is
  silent; recover it in a follow-up rather than assuming the merge was faithful.
- **Triage every test failure as pre-existing or newly-introduced before shipping.** Stash
  and re-run against the base to tell which. Never absorb a pre-existing red into unrelated
  work, and never claim green while a known red stands.
- **Upstream `main` beats local staging plans.** In a multi-agent setup another agent may
  have already filed, merged, or evolved a cross-repo contribution. Check the upstream repo's
  `main` before developing one further — local `plans/` lag.
- **Fail loudly.** Convert an absent guarantee into a red test or a lint failure, never a
  silent pass. Deferrals carry an honest status marker — a strict-xfail, an `Open`/`partial`
  attestation, a documented "⏳ next" — never a bare `TODO` claiming a property the code
  doesn't deliver.
- **One source of truth per fact.** Restating a fact in a second document creates a drift
  surface. Put it in the doc that owns the category and link from the others.
- **Orient without moving; branch only to work.** Reading and priming never need a branch
  change — in a multi-worktree setup `main` is often checked out elsewhere, so a checkout
  fails or strands uncommitted work. Run `git worktree list` before starting. Repo-specific
  worktree setup and port serialization live in that repo's own sections.
- **A sync rule without a mechanical check is a wish.** Anything that must hold in more than
  one repo ships with a command that verifies it, and the rule names the command. Nobody
  eyeballs every repo by hand, so silent drift is the default outcome otherwise.
- **Add a load-bearing document or module → update `.claude/commands/prime.md` in the same
  PR.** Priming is how every agent gets its systems-level picture of a repo, and a prime that
  misses the file where the invariants live sends every future session searching for it. This
  is the same rule as "a user-visible change updates the users guide in the same PR", applied
  to the agent's entry point. Prime is bespoke per repo, so no checksum catches this one —
  the PR is the only gate.
- **Prime is expensive; not priming is more expensive.** `CLAUDE.md` loads every session, so
  it holds what is always true and stays short. Prime is opt-in and costs tokens, so it holds
  the *reading list* — which files give systems-level understanding, and which to skim rather
  than read. Keep prime curated: name the seams, never glob a directory.

## Changing this block

This block is generated. To change it: edit the canonical copy, bump the version in both
markers, run `just sync-conventions` from the hub repo, then open one PR per repo.
`just check-conventions` verifies every copy matches; `just check-org` runs every org check.
Full procedure: hub `docs/org-upkeep.md`.

<!-- END SHARED: org-conventions v6 -->

## Upstream and the other reference design

- `../personal_network_toolkit` — the PNA Toolkit (PNT): the universal spec, contracts, and
  lints this design attests conformance to. Its `origin/main` is the source of truth for
  upstream work (see § Workflow, "Upstream contributions").
- `../prm` — the second reference design (Personal Relationship Manager), for cross-design
  comparison.

A change here can have cross-repo implications for PNT (a conformance or contract change);
when in doubt, read PNT's `spec/` and this repo's `docs/Architecture.md`.

## Constraints

- **No frameworks.** Python stdlib only (http.server, sqlite3, json, pathlib). No Flask, Django, Express, etc.
- **No frontend build tools.** Vanilla JS, no npm, no bundlers, no transpilers.
- **No new pip dependencies** for the app. Dev deps go in requirements-dev.txt. The `mcp_servers/` directory is the only exception — its servers may pull in non-stdlib runtime deps (the official `mcp` SDK), isolated in `mcp_servers/.venv` so the app's stdlib-only boundary stays clean. `mcp_servers/` imports from `app/` only via pure-logic helpers (e.g. `app/fellows_queries.py`).
- **No authentication.** Local-only tool.
- **Port 8765.** Do not change.

## Conventions

- Keep the server as a single file (`app/server.py`). Pure-logic helpers (e.g. `app/relationships.py`) may live alongside.
- Frontend is a single IIFE in `app/static/app.js`. No modules, no classes.
- `escapeHtml()` for all user data rendered into HTML.
- Parameterized `?` placeholders for all SQL queries.
- Validate image paths against traversal (`..` checks).
- Do not leave a long-lived server running in the terminal.
- The DB file `app/fellows.db` is gitignored; rebuild from JSON source.
- Always run relevant tests after changes.
- For deploy- or infra-related work, put **manual QA steps for the maintainer** (smoke scripts, DNS/TLS checks, browser install flow) in the **PR description**, not only in commits or docs.
- **UI/UX changes belong in `docs/users_manual.md`.** When a feature PR changes user-visible behavior (new screen, new flow, changed control, new option), include the corresponding users-manual update in the same PR — accepting the PR accepts the doc change with it. The user guide is the source of truth for UI/UX from a user's perspective; the app links to it from the About page.
- **OPFS access only via the dedicated worker; main thread is an RPC client.** All `relationships.db` and `fellows.db` reads/writes go through `app/static/vendor/sqlite-worker.js`. The main thread does not call `navigator.storage.getDirectory`, does not load `sqlite3.wasm`, and does not hold any `FileSystemSyncAccessHandle`. (Phase 1 of `plans/local_first_worker_architecture.md` enforces this in code; until then `app/static/app.js` still has the legacy main-thread paths and this convention applies to *new* code.)

## Workflow (git, PRs, shipping)

- **PR/issue bodies via `--body-file`, never inline.** Pass `gh pr create` / `gh issue create` a file (or a heredoc to a temp file). Backticks and `$(…)` in an inline `--body` get shell-interpreted and silently drop content — a commit hash has been lost this way.
- **Branch new work off `main`** (confirm with `git branch --show-current` first), and **after a PR merges, verify every intended commit actually landed.** A dropped commit is silent; recover it in a follow-up PR.
- **Before shipping, run the suite and triage every failure as pre-existing vs. newly-introduced.** A red that reproduces on a clean branch/`main` HEAD (stash your changes to check) is pre-existing — say so explicitly and fix it as its own scoped change; never silently absorb it into unrelated work, and never claim green while a known red stands. This is § Conformance discipline's *everything fails loudly* applied to the test run itself.
- **Default posture: orient without moving; branch only to work.** Reading or priming never needs a branch change — don't `git checkout main` / `git pull` just to get oriented (in a multi-worktree setup `main` is often checked out elsewhere, so the checkout fails or strands uncommitted work). Create a worktree (next bullet / `just wt`) when you start *actual work*, and run `git worktree list` first to spot a sibling already on a related branch.
- **Multiple agents on one host → one git worktree each.** When more than one Claude Code / agent works on this checkout's host concurrently, give each its own worktree so a `git checkout` in one can't yank the branch (or uncommitted work) out from under another. Spin up with `just wt <branch>`, or `git worktree add ../fellows-wt-<branch> -b <branch> && scripts/wt-setup.sh ../fellows-wt-<branch>` (the setup script symlinks the heavy gitignored artifacts — `.venv`, `app/fellows.db`, `mcp_servers/.venv` — so the worktree is test-ready instantly). Worktrees isolate the *filesystem*, **not port 8765**: edits / `just test-db` / conformance lints run in parallel, but **server-based runs (`serve`, `test-api` / `test-e2e` / `test-mobile`) must be serialized across worktrees** — `ensure_port_8765_free.sh` kills whatever holds 8765, so a sibling's e2e run dies mid-flight and looks like a flaky test. The symlinked `app/fellows.db` is *shared*, so don't `db-rebuild`/`reset` while a sibling is testing. `just wtclean <branch>` when done. Full rationale: [`docs/worktrees.md`](docs/worktrees.md).
- **Upstream contributions: the upstream repo's `main` is the source of truth — not the local plan.** Before recommending a filing action *or developing a [PNA Toolkit (PNT)](https://github.com/social-network-health/personal_network_toolkit) contribution further*, verify its real status against PNT `origin/main` — the `spec/` files + `tools/lint-spec-ids.py` — **not** the fellows-side `plans/pna_toolkit_*` banners. Those plans **lag**: in a multi-agent setup another agent may have already filed, merged, or evolved the work upstream (a fellows plan read "ready to file" while the concept was already merged on PNT main and iterated *beyond* it). Local `plans/` are staging records; the upstream `main` supersedes them and is the more recent, relevant state. Make this check **first, every time** — it's the cross-repo analog of "after a PR merges, verify every intended commit actually landed." When you do touch the PNT checkout, use a worktree off PNT `origin/main` (previous bullet) — it may be on another agent's branch.

## Conformance discipline

These rules keep `docs/Architecture.md`'s AC/CST attestation (the Security
Target) honest. See [`plans/conformance_discipline.md`](plans/conformance_discipline.md).

- **A `conformant` attestation row needs executable evidence.** It must cite a
  resolvable test ref (`path/to/test.py[::name]`) or an explicitly declared
  verification kind (`human-review` / `LLM rubric` / `code inspection` /
  `by architecture` / `by bounding` / `by construction`). A bare doc pointer is
  not evidence — a doc that *asserts* a property does not *prove* it.
  `tests/test_attestation_has_evidence.py` enforces this; run it after touching
  the attestation.
- **Negative invariants need negative tests.** "X must NOT happen off-folder" is
  not covered by the test that X happens on-folder.
- **Deferred or not-yet-true invariants are `@pytest.mark.xfail(strict=True)`
  tests that name the plan PR which will satisfy them — never a `// TODO`, a
  prose "lands later," or an `INERT` code comment.** A strict-xfail is a deferral
  with a tripwire: it goes red the day someone implements it, and
  `grep "xfail(strict"` is the live list of claimed-but-unproven invariants. The
  only other home for a deferral is the attestation table with an honest
  `partial`/`Open` status.
- **Capability reductions enforce at the data layer, never UI-only.** Hiding or
  graying a surface and redirecting a route is the cosmetic half; the reduction
  is that the *write does not happen* — refuse the mutating op at the worker (the
  OPFS owner) and, defensively, at the `dataProvider`. A gated capability whose
  RPC still succeeds from the DevTools console is not reduced.
- **Everything fails loudly.** Convert an absent guarantee into a red test or a
  blocking hook — never a silent pass.
- **The conformance-guard stop-hook is a nudge, not the gate.** It fires while
  you're *editing* `docs/Architecture.md`'s attestation without touching
  `tests/`. If `pytest tests/test_attestation_has_evidence.py` is green and the
  change is framing-only (cites already-green tests) or an honest
  `partial`/`Open` row, **acknowledge once and move on — don't re-run the gate
  or re-explain on later stops.** If a row is intentionally not-yet-true
  (test-first), say so and name the PR/step that makes it conform; it carries a
  `partial`/`Open` status or a strict-xfail until then. The pytest gate in CI is
  the enforcement; the hook only nudges while you edit (and goes quiet once you
  commit — it is working-tree-scoped).

## Two-DB architecture

User-authored data (groups, per-fellow tags, per-fellow notes, settings) lives in `app/relationships.db`, a separate SQLite file from the imported contact data in `app/fellows.db`. Cross-DB joins use SQLite `ATTACH DATABASE` with `?mode=ro` on the fellows side — read-only-ness of contact tables is enforced at the SQLite level, not just the app layer. See `app/relationships.py` (Python) and the `RELATIONSHIPS_SCHEMA_SQL` mirror in `app/static/app.js` (PWA / OPFS). `relationships.db` is gitignored, per-user, and persists across app updates; `fellows.db` is regenerated from source on every build.
