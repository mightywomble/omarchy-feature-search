"""Tests for the keyword search backend (no heavy deps required)."""

from __future__ import annotations

from data_pipeline.extract_table import seed_features

from omarchy_feature_search.search import SearchEngine, fmt_time

DOC = {
    "video_url": "https://youtu.be/2IDjteRQgMQ",
    "video_id": "2IDjteRQgMQ",
    "video_title": "Omarchy Can Do WHAT?!",
    "features": seed_features(),
}


def make_engine() -> SearchEngine:
    return SearchEngine(DOC)


def test_fmt_time():
    assert fmt_time(14) == "00:00:14"
    assert fmt_time(34 * 60 + 30) == "00:34:30"


def test_backend_is_keyword_without_chroma():
    eng = make_engine()
    assert eng.backend == "keyword"


def test_empty_query_returns_nothing():
    assert make_engine().search("") == []
    assert make_engine().search("   ") == []


def test_screenshot_query_ranks_screenshot_feature_first():
    results = make_engine().search("screenshot")
    assert results, "expected at least one match for 'screenshot'"
    top = results[0]
    assert "screenshot" in top.feature.lower()
    assert 0 < top.confidence <= 100


def test_workspace_query_returns_workspace_features():
    results = make_engine().search("switch workspace")
    assert results, "expected matches for 'switch workspace'"
    assert any("workspace" in r.feature.lower() for r in results)


def test_results_sorted_by_confidence_desc():
    results = make_engine().search("install package")
    confs = [r.confidence for r in results]
    assert confs == sorted(confs, reverse=True)


def test_no_spurious_matches_for_unrelated_query():
    results = make_engine().search("zzzznonexistent")
    assert results == []
