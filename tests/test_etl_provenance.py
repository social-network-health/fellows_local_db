"""In-band provenance chain (AC-17) — hermetic ETL tests.

The real Knack scrapefile is never in the repo (docs/data_provenance.md), so
these build tiny DBs from a synthesized scrapefile in tmp_path and verify the
three properties the provenance design leans on:

  * hop 0's artifact_sha256 is the sha256 of the EXACT bytes the ETL parsed;
  * a rebuild from the same scrapefile is byte-deterministic (no wall-clock,
    no git sha in the DB), which is what keeps fellows_db_sha — the opt-in
    update-availability signal — from churning per code commit;
  * build/diff_fellows_db.py stays green across the provenance table (it is a
    logical per-column diff of the fellows table, so the frozen 2026-04-08
    reference backup, which predates the table, still verifies fresh builds).

Content assertions against the real DB live in tests/test_database.py
(test_provenance_*), which skip when app/fellows.db is absent.
"""
import hashlib
import json
import sqlite3

from build import diff_fellows_db
from build import restore_from_knack_scrapefile as etl

# Minimal valid detail-dump shape: dict keyed by record_id; name comes from
# field_10 (slug pass) / field_10_raw.full (column mapping). Two records so
# multi-row insert order is exercised.
FAKE_SCRAPE = {
    "rec_001": {"field_10": "Ada Lovelace", "field_10_raw": {"full": "Ada Lovelace"}},
    "rec_002": {"field_10": "Grace Hopper", "field_10_raw": {"full": "Grace Hopper"}},
}


def _write_scrapefile(tmp_path, name="fake_scrape.json"):
    src = tmp_path / name
    src.write_text(json.dumps(FAKE_SCRAPE), encoding="utf-8")
    return src


def _build(tmp_path, src, db_name, extra_args=()):
    out = tmp_path / db_name
    rc = etl.main([str(src), "--db", str(out), *extra_args])
    assert rc == 0
    return out


def _provenance_rows(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT hop, system, artifact, artifact_sha256, acquired_at, method "
            "FROM provenance ORDER BY hop"
        ).fetchall()
    finally:
        conn.close()


def test_hop0_sha_matches_source_bytes(tmp_path):
    src = _write_scrapefile(tmp_path)
    out = _build(tmp_path, src, "out.db")
    rows = _provenance_rows(out)
    assert len(rows) == 2
    hop0 = rows[0]
    assert hop0[1] == etl.SOURCE_SYSTEM
    assert hop0[2] == src.name
    assert hop0[3] == hashlib.sha256(src.read_bytes()).hexdigest()
    assert hop0[4] == etl.SOURCE_ACQUIRED_AT
    assert hop0[5] == etl.SOURCE_METHOD


def test_source_acquired_at_is_overridable(tmp_path):
    """A re-scrape of a different vintage must not silently carry the frozen
    2026-04-08 date — the flag sets hop 0's acquired_at."""
    src = _write_scrapefile(tmp_path)
    out = _build(tmp_path, src, "out.db",
                 extra_args=("--source-acquired-at", "2027-01-15"))
    assert _provenance_rows(out)[0][4] == "2027-01-15"


def test_hop1_has_no_volatile_values(tmp_path):
    src = _write_scrapefile(tmp_path)
    out = _build(tmp_path, src, "out.db")
    hop1 = _provenance_rows(out)[1]
    assert hop1[1] == "fellows_local_db"
    assert hop1[2] == "fellows.db"
    assert hop1[3] is None  # a DB cannot contain its own hash
    assert hop1[4] is None  # never a build wall-clock date
    assert hop1[5] == "build/restore_from_knack_scrapefile.py"


def test_build_is_byte_deterministic(tmp_path):
    """Two builds from identical source bytes produce identical DB bytes (on
    one machine — the SQLite library version in the header and the images dir
    contents are per-environment inputs, both pre-existing). This is the
    guarantee that adding provenance did not smuggle a timestamp or random
    value into the file."""
    src = _write_scrapefile(tmp_path)
    a = _build(tmp_path, src, "a.db")
    b = _build(tmp_path, src, "b.db")
    assert hashlib.sha256(a.read_bytes()).hexdigest() == \
        hashlib.sha256(b.read_bytes()).hexdigest()


def test_diff_tool_tolerates_provenance_table(tmp_path, capsys):
    """A fresh build (with provenance) diffed against a pre-provenance
    reference of identical fellows content exits 0 — so `just db-verify`
    against the frozen 2026-04-08 backup stays meaningful and green."""
    src = _write_scrapefile(tmp_path)
    new = _build(tmp_path, src, "new.db")
    ref = _build(tmp_path, src, "ref.db")
    conn = sqlite3.connect(ref)
    conn.execute("DROP TABLE provenance")
    conn.commit()
    conn.close()

    rc = diff_fellows_db.main([str(new), str(ref)])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "column-exact match" in out
    assert "pre-provenance" in out  # the informational asymmetry note


def test_read_helpers_tolerate_missing_table_and_agree(tmp_path):
    """The two server-side readers (app/fellows_queries.get_provenance and
    deploy/sqlite_api_support.get_provenance) return the same rows on a
    provenance-carrying DB and both return [] on a pre-provenance DB —
    the dev and prod tiers must not tell different provenance stories."""
    import sqlite3
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    deploy_dir = str(repo_root / "deploy")
    if deploy_dir not in sys.path:
        sys.path.insert(0, deploy_dir)
    from app.fellows_queries import get_provenance as app_get
    import sqlite_api_support as sq

    src = _write_scrapefile(tmp_path)
    with_table = _build(tmp_path, src, "with.db")
    without_table = _build(tmp_path, src, "without.db")
    conn = sqlite3.connect(without_table)
    conn.execute("DROP TABLE provenance")
    conn.commit()
    conn.close()

    c1 = sqlite3.connect(with_table)
    c2 = sqlite3.connect(without_table)
    try:
        app_chain = app_get(c1)
        assert len(app_chain) == 2 and app_chain[0]["hop"] == 0
        assert app_chain == sq.get_provenance(c1)
        assert app_get(c2) == []
        assert sq.get_provenance(c2) == []
    finally:
        c1.close()
        c2.close()
