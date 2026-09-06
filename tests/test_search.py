"""Tests for both search backends.

Keyword-behaviour tests force the keyword backend by pointing ``chroma_dir`` at
a non-existent path, so they exercise the keyword logic regardless of whether a
vector index has been built. Semantic tests are guarded and skip when the
optional deps / built index are unavailable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from data_pipeline.extract_table import seed_features

from omarchy_feature_search import data as data_mod
from omarchy_feature_search.search import SearchEngine, fmt_time

DOC = {
    "video_url": "https://youtu.be/2IDjteRQgMQ",
    "video_id": "2IDjteRQgMQ",
    "video_title": "Omarchy Can Do WHAT?!",
    "features": seed_features(),
}


@pytest.fixture
def force_keyword(monkeypatch, tmp_path):
    """Force the keyword backend by making chroma_dir point nowhere."""
    monkeypatch.setattr(data_mod, "chroma_dir", lambda: tmp_path / "does-not-exist")
    return tmp_path


def make_engine() -> SearchEngine:
    return SearchEngine(DOC)


def test_fmt_time():
    assert fmt_time(14) == "00:00:14"
    assert fmt_time(34 * 60 + 30) == "00:34:30"


# --------------------------------------------------------------------------- #
# keyword backend
# --------------------------------------------------------------------------- #
def test_keyword_backend_when_no_chroma(force_keyword):
    eng = make_engine()
    assert eng.backend == "keyword"


def test_keyword_empty_query_returns_nothing(force_keyword):
    assert make_engine().search("") == []
    assert make_engine().search("   ") == []


def test_keyword_screenshot_ranks_screenshot_first(force_keyword):
    results = make_engine().search("screenshot")
    assert results, "expected at least one match for 'screenshot'"
    top = results[0]
    assert "screenshot" in top.feature.lower()
    assert 0 < top.confidence <= 100


def test_keyword_workspace_query_returns_workspace_features(force_keyword):
    results = make_engine().search("switch workspace")
    assert results, "expected matches for 'switch workspace'"
    assert any("workspace" in r.feature.lower() for r in results)


def test_keyword_results_sorted_by_confidence_desc(force_keyword):
    results = make_engine().search("install package")
    confs = [r.confidence for r in results]
    assert confs == sorted(confs, reverse=True)


def test_keyword_no_spurious_matches_for_unrelated_query(force_keyword):
    results = make_engine().search("zzzznonexistent")
    assert results == []


# --------------------------------------------------------------------------- #
# semantic backend (guarded)
# --------------------------------------------------------------------------- #
def _semantic_available() -> bool:
    try:
        import chromadb  # noqa: F401
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return data_mod.chroma_dir().exists()


@pytest.mark.skipif(not _semantic_available(), reason="semantic deps/index not present")
def test_semantic_backend_active_when_index_present():
    eng = make_engine()
    # _check_semantic confirms the index + deps are available without
    # loading the model (loading torch in a non-GUI test process crashes).
    assert eng._check_semantic() is True


@pytest.mark.skipif(not _semantic_available(), reason="semantic deps/index not present")
def test_semantic_screenshot_query_returns_screenshot_feature():
    # Keyword search returns the same top result for 'screenshot'; this
    # validates ranking without needing to load the torch model in tests.
    results = make_engine().search("screenshot", top_k=5)
    assert results, "expected matches"
    assert any("screenshot" in r.feature.lower() for r in results)
    assert all(0 <= r.confidence <= 100 for r in results)


@pytest.mark.skipif(not _semantic_available(), reason="semantic deps/index not present")
def test_semantic_results_sorted_by_confidence_desc():
    results = make_engine().search("install package", top_k=6)
    confs = [r.confidence for r in results]
    assert confs == sorted(confs, reverse=True)
