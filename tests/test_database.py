"""Database tests: schema, FTS5, data integrity."""
import pytest


def test_fellows_table_has_rows(db):
    """Fellows table should have at least one row."""
    cur = db.execute("SELECT COUNT(*) FROM fellows")
    assert cur.fetchone()[0] >= 1


def test_fellows_has_slug_and_name(db):
    """Should have name and slug columns with expected sample."""
    cur = db.execute(
        "SELECT name, slug FROM fellows WHERE name IS NOT NULL AND name != '' ORDER BY name LIMIT 3"
    )
    rows = cur.fetchall()
    assert len(rows) >= 3
    names = [r[0] for r in rows]
    slugs = [r[1] for r in rows]
    assert "Aaron Bird" in names
    assert "aaron_bird" in slugs


def test_fts5_exists_and_matches(db):
    """FTS5 table should exist and return rows for 'Aaron'."""
    cur = db.execute(
        "SELECT name FROM fellows_fts WHERE fellows_fts MATCH 'Aaron'"
    )
    rows = cur.fetchall()
    assert len(rows) >= 1
    names = [r[0] for r in rows]
    assert "Aaron Bird" in names or "Aaron McDonald" in names


def test_fts5_matches_first_name_richard(db):
    """Whole-token first-name match for 'Richard' returns the expected fellows."""
    cur = db.execute(
        "SELECT name FROM fellows_fts WHERE fellows_fts MATCH 'Richard'"
    )
    names = [r[0] for r in cur.fetchall()]
    assert "Richard Bodo" in names
    assert "Richard Graves" in names


def test_fts5_matches_last_name_bodo(db):
    """Whole-token last-name match for 'Bodo' returns Richard Bodo."""
    cur = db.execute(
        "SELECT name FROM fellows_fts WHERE fellows_fts MATCH 'Bodo'"
    )
    names = [r[0] for r in cur.fetchall()]
    assert "Richard Bodo" in names


def test_fts5_matches_full_name_two_tokens(db):
    """Multi-token MATCH 'Richard Bodo' is an implicit AND and pinpoints one row."""
    cur = db.execute(
        "SELECT name FROM fellows_fts WHERE fellows_fts MATCH 'Richard Bodo'"
    )
    names = [r[0] for r in cur.fetchall()]
    assert names == ["Richard Bodo"]


def test_fts5_partial_token_without_prefix_glob_returns_nothing(db):
    """As-you-type behavior: a partial token like 'Ric' returns 0 rows.

    Documents the load-bearing reason real-time search appears broken:
    FTS5 MATCH is whole-token. Without a trailing '*' the partial prefix
    'Ric' / 'Bod' matches nothing, so every keystroke before a token is
    complete shows 'no results'. The fix is to append '*' to the last
    (or every) token on the client side before issuing MATCH.
    """
    assert (
        db.execute(
            "SELECT COUNT(*) FROM fellows_fts WHERE fellows_fts MATCH 'Ric'"
        ).fetchone()[0]
        == 0
    )
    assert (
        db.execute(
            "SELECT COUNT(*) FROM fellows_fts WHERE fellows_fts MATCH 'Bod'"
        ).fetchone()[0]
        == 0
    )
    cur = db.execute(
        "SELECT name FROM fellows_fts WHERE fellows_fts MATCH 'Ric*'"
    )
    names = [r[0] for r in cur.fetchall()]
    assert "Richard Bodo" in names


def test_lookup_by_slug(db):
    """Lookup by slug aaron_bird returns Aaron Bird."""
    cur = db.execute("SELECT name FROM fellows WHERE slug = 'aaron_bird'")
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "Aaron Bird"


def test_list_query_returns_expected_columns(db):
    """List query returns record_id, slug, name for all fellows."""
    cur = db.execute("SELECT record_id, slug, name FROM fellows ORDER BY name")
    rows = cur.fetchall()
    expected_count = db.execute("SELECT COUNT(*) FROM fellows").fetchone()[0]
    assert len(rows) == expected_count
    assert len(rows[0]) == 3


def test_all_slugs_are_unique(db):
    """All slugs in the fellows table should be unique."""
    cur = db.execute("SELECT slug, COUNT(*) FROM fellows GROUP BY slug HAVING COUNT(*) > 1")
    duplicates = cur.fetchall()
    assert duplicates == [], f"Duplicate slugs found: {duplicates}"


def test_stats_aggregation_queries(db):
    """Stats aggregation queries should execute and return rows."""
    cur = db.execute(
        "SELECT fellow_type, COUNT(*) FROM fellows"
        " WHERE fellow_type IS NOT NULL GROUP BY fellow_type"
    )
    assert len(cur.fetchall()) >= 1
    cur = db.execute(
        "SELECT json_extract(extra_json, '$.primary_global_region_of_citizenship'),"
        " COUNT(*) FROM fellows WHERE extra_json IS NOT NULL GROUP BY 1"
    )
    assert len(cur.fetchall()) >= 1


def test_schema_has_expected_columns(db):
    """Fellows table should have all expected columns."""
    cur = db.execute("PRAGMA table_info(fellows)")
    columns = {row[1] for row in cur.fetchall()}
    expected = {
        "record_id", "slug", "name", "bio_tagline", "fellow_type", "cohort",
        "contact_email", "key_links", "key_links_urls", "image_url",
        "currently_based_in", "search_tags", "fellow_status", "gender_pronouns",
        "ethnicity", "primary_citizenship", "global_regions_currently_based_in",
        "has_image", "extra_json",
    }
    assert expected.issubset(columns), f"Missing columns: {expected - columns}"


def test_has_image_is_boolean_and_consistent(db):
    """has_image is always 0 or 1; counts partition the table."""
    total = db.execute("SELECT COUNT(*) FROM fellows").fetchone()[0]
    with_image = db.execute("SELECT COUNT(*) FROM fellows WHERE has_image = 1").fetchone()[0]
    without_image = db.execute("SELECT COUNT(*) FROM fellows WHERE has_image = 0").fetchone()[0]
    assert with_image + without_image == total, "has_image must always be 0 or 1"


def test_every_row_has_a_name(db):
    """Every fellow must have a non-empty name after the source_name fallback lands."""
    cur = db.execute(
        "SELECT record_id, slug FROM fellows WHERE name IS NULL OR name = ''"
    )
    nameless = cur.fetchall()
    assert not nameless, (
        "Rows without name: " + ", ".join(f"{rid}({slug})" for rid, slug in nameless[:5])
    )


def test_email_coverage_ratio_catches_demo_filter_regression(db):
    """Regression: >90% of fellows should have contact_email.

    If a demo-filter JSON (which drops fellows without profile images AND
    strips emails from the remainder) gets used as the rebuild source,
    the ratio falls to ~60%. This test is the tripwire.

    The full Apr 8 Knack REST-API extraction gives 100% coverage — any
    fellow in the dataset has their email.
    """
    total = db.execute("SELECT COUNT(*) FROM fellows").fetchone()[0]
    with_email = db.execute(
        "SELECT COUNT(*) FROM fellows "
        "WHERE contact_email IS NOT NULL AND trim(contact_email) != ''"
    ).fetchone()[0]
    ratio = with_email / total if total else 0
    assert ratio > 0.9, (
        f"Only {with_email}/{total} fellows have contact_email ({ratio:.0%}). "
        "Likely rebuilt from the demo-filtered .bak JSON. Re-run "
        "`python build/restore_from_knack_apr8.py`."
    )


def test_slug_never_falls_back_to_record_id(db):
    """Importer falls back to source_name before record_id; no slug should equal its record_id."""
    cur = db.execute(
        "SELECT record_id, slug FROM fellows WHERE slug = record_id"
    )
    rows = cur.fetchall()
    assert not rows, (
        "Slugs equal to record_id (importer fallback exhausted): "
        + ", ".join(f"{rid}" for rid, _ in rows[:5])
    )


# --- In-band provenance chain (AC-17) ----------------------------------------
# Content assertions against the real built DB. The hermetic ETL-level tests
# (sha-over-parsed-bytes, determinism, diff-tool tolerance) live in
# tests/test_etl_provenance.py; a rebuilt app/fellows.db must also carry the
# expected chain, which is what a downstream importer (another PNA, an MCP
# client) will actually read.


def test_provenance_table_has_two_hops(db):
    """The build stamps exactly the two-hop chain: source, then this pipeline."""
    rows = db.execute("SELECT hop FROM provenance ORDER BY hop").fetchall()
    assert [r[0] for r in rows] == [0, 1]


def test_provenance_hop0_names_knack_source(db):
    """Hop 0 is the ultimate source: the 2026-04-08 Knack REST-API extraction,
    with the scrapefile's sha256 riding along for artifact integrity."""
    row = db.execute(
        "SELECT system, artifact, artifact_sha256, acquired_at, method "
        "FROM provenance WHERE hop = 0"
    ).fetchone()
    assert row is not None
    system, artifact, sha, acquired_at, method = row
    assert system == "EHF Fellows Directory (Knack)"
    assert artifact  # names the scrapefile
    import re as _re
    assert sha and _re.fullmatch(r"[0-9a-f]{64}", sha)
    assert acquired_at == "2026-04-08"
    assert method == "Knack REST API extraction"


def test_provenance_hop1_has_no_volatile_values(db):
    """Hop 1 (this pipeline) must carry no per-build volatile values — no
    wall-clock date, no self-hash — so rebuilds stay deterministic and
    fellows_db_sha doesn't churn per code commit."""
    row = db.execute(
        "SELECT system, artifact, artifact_sha256, acquired_at, method "
        "FROM provenance WHERE hop = 1"
    ).fetchone()
    assert row is not None
    system, artifact, sha, acquired_at, method = row
    assert system == "fellows_local_db"
    assert artifact == "fellows.db"
    assert sha is None
    assert acquired_at is None
    assert method == "build/restore_from_knack_scrapefile.py"
