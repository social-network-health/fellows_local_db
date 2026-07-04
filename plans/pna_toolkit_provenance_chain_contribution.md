# Plan — Contributing the **Provenance chain** concept to the PNA Toolkit (PNT)

> **Status: STAGED — not filed.** The fellows-side demonstrating code is landing
> (exporter half: PRs #292 in-band chain + #293 read surface, stacked on #291);
> the importer half is a **prm** task (handoff spec in § 4 below). Per the
> reference-driven contribution model, the upstream PR is not filed until at
> least the exporter demonstrator is merged and, ideally, prm's importer exists.
>
> **Before developing this further or recommending a filing action, verify the
> real status against PNT `origin/main`** (`spec/`, `spec/contracts/shared-db.schema.sql`,
> `tools/lint-spec-ids.py`) — **not** this banner. Fellows-side plans lag; in a
> multi-agent setup the concept may already have been filed, merged, or evolved
> upstream. (Verified absent from PNT `origin/main` at `facea9f`, 2026-07-04:
> the shared-DB contract carries only a commented-out single `source` column,
> per-field provenance shape is explicitly deferred to AC-PRM-B's draft
> multi-source contract, and cross-PNA interchange is `federated-read
> (deferred)`.)
>
> Local paths: PNT repo `~/src/personal_network_toolkit`; demonstrating designs
> `~/src/fellows_local_db` (exporter) and `~/src/prm` (importer, pending).
>
> **Registry:** [`upstream_contributions_staging.md`](upstream_contributions_staging.md) § 5.

---

## 1. Summary + motivation

### The discovery

Checking whether AC-17 ("mirrored data is sourced") was *legible* in fellows's
validation reports surfaced a longer chain: the maintainer moves data **between
PNAs** — the fellows directory (a single-source Knack archive) gets imported
into prm (a multi-source relationship manager). prm can say "this contact came
from `google_takeout`", but its `source` is a **flat string**: there is nowhere
to record that the `fellows_local_db` import was *itself* an archive of the EHF
Knack directory made on 2026-04-08. After one hop, ultimate-source provenance
is gone — exactly the property AC-17 exists to protect, silently lost at the
PNA-to-PNA boundary the spec doesn't yet cover.

### The mechanism

A small, append-only **provenance chain** embedded **in-band** in the Shared
DB file itself, so it travels wherever the data-bearing artifact travels (raw
DB download, OPFS copy, downstream import):

```sql
CREATE TABLE provenance (
    hop INTEGER PRIMARY KEY,   -- 0 = ultimate source; importers append hops
    system TEXT NOT NULL,      -- 'EHF Fellows Directory (Knack)'
    artifact TEXT,             -- 'knack_api_detail_dump.json'
    artifact_sha256 TEXT,      -- integrity of that hop's artifact (NULL for the DB itself)
    acquired_at TEXT,          -- source-vintage date, never build wall-clock
    method TEXT,               -- 'Knack REST API extraction'
    note TEXT
);
```

Chain rules (the normative content of the proposal):

1. **Hop 0 is the ultimate source.** An ingesting PNA MUST preserve existing
   hops and append its own hop describing the import — that is how "archived
   from Knack on 2026-04-08" survives N boundary crossings.
2. **Entries are attested claims, not proofs.** Each hop is a self-declaration
   by the application that wrote it. No signing infrastructure; `artifact_sha256`
   gives per-hop artifact integrity (the DB's own hop carries NULL — a file
   cannot contain its own hash; transport-side metadata carries it, and
   importers compute it at ingest).
3. **No per-build volatile values.** Hops carry source-vintage dates, never
   build wall-clock or VCS state, so mirror rebuilds stay deterministic and
   content-hash update signals don't churn.
4. **Batch-level, not per-field.** The chain answers "where did this *dataset*
   ultimately come from"; per-record/per-field provenance under multi-source
   merge remains AC-PRM-B's territory. The two compose: prm's per-field
   `source` label points at a source whose own chain the provenance table
   carries.
5. **Readers tolerate absence.** A pre-provenance DB yields an empty chain and
   honest fallback rendering — never a fabricated claim.
6. **The chain is itself sensitive metadata** ("member of the EHF fellows
   directory"): on any re-export/egress it belongs inside the user-legible
   dispose preview (user-mediation UM-3), and exported artifacts SHOULD carry a
   human-readable provenance line derived from it.

### Why the spec (and not just fellows) should own it

- AC-17 + IN-3 + SH-6 already make sourced provenance normative, but only
  *within* one PNA; the chain extends the same goal across the PNA-to-PNA
  boundary that `federated-read (deferred)` acknowledges but doesn't cover.
- Both reference designs hit it from opposite sides: fellows (single-source
  archive) has the story but nowhere durable to put it; prm (multi-source
  merge) has per-field provenance but no source-of-source. A mechanism both
  need is toolkit material — the same test Exceptions/Constraints passed.

## 2. Upstream shape (proposed)

A **Shared-DB sub-contract** (working id **SH-7 — provenance chain**), sited in
`spec/contracts/shared-db.schema.sql` + a short section in `PNA_Spec.md` next
to SH-6:

- Any PNA **MAY** embed the `provenance` table; a PNA whose Shared store is a
  **mirror of another PNA's data** (or any second-hand dataset) **SHOULD**.
- An ingesting PNA **MUST NOT** drop or rewrite upstream hops; it appends.
- Chain rules 1–6 above as the normative text; the table DDL as the contract
  shape (column names normative, extension columns allowed).
- `tools/lint-spec-ids.py`: SH-7 id header-tracing, matching the existing SH-*
  pattern.

This imposes a new (conditional) obligation → **reference-design route** per
PNT CONTRIBUTING: it ships with demonstrating designs, not before. Exporter
demonstrator = fellows (PRs #291/#292/#293: the ETL stamp, determinism tests,
diff-tool tolerance, About-page + export-footer read surface, AC-17
attestation). Importer demonstrator = prm (§ 4).

## 3. Open questions (surface in the PR body, don't resolve unilaterally)

- **MAY vs SHOULD floor** for first-party mirrors (fellows-style single-source
  from a live SaaS): is hop 0 + hop 1 worth mandating, or is SH-6's per-record
  `source` enough until the data crosses a PNA boundary?
- **Where the chain meets AC-PRM-B**: should the multi-source contract's
  per-field `source` labels be REQUIRED to resolve to a chain entry (a foreign
  key by convention), or stay decoupled strings?
- **Transport-side artifact hash**: standardize where the DB's own sha lives
  (fellows uses `/build-meta.json:fellows_db_sha`) or leave per-distribution?

## 4. prm handoff spec (the importer half — implemented in `~/src/prm`)

What prm needs to accept a provenance-carrying fellows import and show
ultimate-source provenance ("came from the EHF fellows directory, archived
from Knack 2026-04-08") the way it shows "came from Google/Apple/Facebook".
Grounded in prm's current code (verified 2026-07-04):

1. **A `fellows_local_db` source.** `cli/ingest.py:infer_source` has no branch
   for another PNA's Shared DB, and `cli/parsers/csv.py` rejects non-LinkedIn/
   Google CSVs. Add a parser that opens the SQLite file directly (prm is
   native-Python; no export intermediary needed): read `fellows` rows → jCard +
   per-field provenance per prm's `cli/parsers/` pattern (the `prm_backup`
   record shape — `source`, `stable_key`, `ingested_at`, jCard, `provenance[]`
   — is the closest template), and read the `provenance` table → the chain.
   Stable key: fellows `record_id` (opaque, stable across re-mirrors per the
   shared-DB contract).
2. **Source-chain storage.** prm's `source` is a flat label with no
   source-of-source. Options (prm's design call): (a) a `source_chain` JSON
   column on `source_records`, (b) a per-source metadata table keyed by source
   label + import batch. Either way: **append prm's own hop at import time**
   (system=`prm`, method=`cli/ingest.py`, acquired_at=import date is fine
   *there* — prm's ingest is an event, not a deterministic rebuild).
3. **Import-batch descriptor.** prm records only per-record `ingested_at` + a
   reimport audit line; persist the batch/source descriptor (file, sha256 —
   computed at ingest, closing fellows's hop-1 NULL — and the imported chain)
   so the UI can render a provenance card per source.
4. **UI vocabulary.** `workspace/app.js` `SOURCE_LABEL`/`srcLabel()` are a
   hardcoded map (and the import-preview source-override dropdown in
   `workspace/index.html` likewise); add `fellows_local_db` (display: "EHF
   fellows"), and teach the "where each value came from" panel to render a
   source's own origin/date from the chain.
5. **Attestation.** prm's `docs/Architecture.md` AC-17/AC-PRM-B rows gain the
   chain-preservation evidence; that PR is the second demonstrating design the
   upstream filing cites.

## 5. Sequencing

1. fellows exporter PRs merge (#291 → #292 → #293) + operator `just db-rebuild`.
2. prm importer (§ 4) as its own task in the prm repo, on a worktree off prm
   `origin/main`.
3. Only then: draft the PNT PR (SH-7 text + lint + both designs' evidence),
   after re-verifying PNT `origin/main` per the banner. Nothing files into PNT
   without the maintainer's explicit go-ahead.
