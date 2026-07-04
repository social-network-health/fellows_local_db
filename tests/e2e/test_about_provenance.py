"""E2E: the About-page "Data source" provenance line (AC-17).

The line renders from the in-band provenance chain stamped into fellows.db
(hop 0 = the ultimate source — the 2026-04-08 Knack extraction of the EHF
fellows directory), read through dataProvider.getProvenance() in worker mode
and /api/provenance in the HTTP fallback.

Vintage-robust by design: these tests assert the RENDERED line matches
whatever chain the provider actually reports — full "system, archived <date>"
when the chain is present, the honest no-date fallback when the served
fellows.db predates the provenance table. Whether a rebuilt DB carries the
chain at all is the data plane's job (tests/test_database.py::test_provenance_*
and tests/test_etl_provenance.py).
"""
from __future__ import annotations

from conftest import _STANDALONE_DISPLAY_INIT

FALLBACK_LINE = "Data source: EHF Fellows Directory (Knack)."


def _make_standalone_page(context):
    page = context.new_page()
    page.add_init_script(_STANDALONE_DISPLAY_INIT)
    return page


def _boot_then_open_about(page, base_url):
    """Same boot-first pattern as test_about_stats: settle boot's route()
    re-renders before opening #/about so the async fills aren't wiped."""
    page.goto(base_url + "/", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => window.__dataProvider && window.__dataProvider.kind === 'worker'",
        timeout=15000,
    )
    page.wait_for_function(
        "() => window.__bootMarks && window.__bootMarks.get_full_done != null",
        timeout=15000,
    )
    page.evaluate("location.hash = '#/about'")
    # The provenance line fills async after getProvenance() resolves.
    page.wait_for_function(
        "() => { const el = document.getElementById('about-provenance');"
        " return el && (el.textContent || '').indexOf('Data source:') === 0; }",
        timeout=15000,
    )


class TestAboutProvenanceLine:
    def test_data_source_line_matches_the_chain(self, context, base_url_fixture):
        """Worker mode: the rendered line is derived from hop 0 of the chain
        the worker reads from the OPFS fellows.db — or the honest no-date
        fallback when the DB predates the table."""
        page = _make_standalone_page(context)
        try:
            _boot_then_open_about(page, base_url_fixture)
            chain = page.evaluate("() => window.__dataProvider.getProvenance()")
            line = page.locator("#about-provenance").text_content() or ""
            if chain:
                hop0 = chain[0]
                expected = "Data source: " + hop0["system"]
                if hop0.get("acquired_at"):
                    expected += ", archived " + hop0["acquired_at"]
                expected += "."
                assert line == expected, f"line {line!r} != chain-derived {expected!r}"
                # hop 0 must be the ultimate source, not this app.
                assert hop0["system"] != "fellows_local_db"
            else:
                assert line == FALLBACK_LINE, (
                    f"pre-provenance DB must render the no-date fallback; got {line!r}"
                )
        finally:
            page.close()

    def test_api_provenance_route_serves_the_same_chain(
        self, context, base_url_fixture
    ):
        """The HTTP fallback path (/api/provenance, used by the api+idb
        provider on no-OPFS browsers) serves the same chain the worker
        reads — the two tiers must not tell different provenance stories."""
        page = _make_standalone_page(context)
        try:
            _boot_then_open_about(page, base_url_fixture)
            worker_chain = page.evaluate(
                "() => window.__dataProvider.getProvenance()"
            )
            api_chain = page.evaluate(
                "() => fetch('/api/provenance').then(r => r.ok ? r.json() : [])"
            )
            assert api_chain == worker_chain
        finally:
            page.close()
