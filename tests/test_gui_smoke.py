"""GUI smoke test — builds the master/detail window offscreen.

Skipped automatically when PySide6 is not installed. Uses a self-managed
QApplication so it does not depend on pytest-qt.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6")


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _doc():
    return {
        "video_url": "https://youtu.be/2IDjteRQgMQ",
        "video_id": "2IDjteRQgMQ",
        "video_title": "Omarchy Can Do WHAT?!",
        "features": [
            {"feature_group": "Keybindings & Search", "feature": "Keybindings Cheat Sheet",
             "how_to": "Super + K", "start_s": 14, "end_s": 27,
             "transcript_summary": "press Super K to see shortcuts", "thumbnail": ""},
            {"feature_group": "Media & Screen Tools", "feature": "Freeze-Frame Screenshot",
             "how_to": "Super + Space -> screenshot", "start_s": 923, "end_s": 935,
             "transcript_summary": "take a screenshot", "thumbnail": ""},
        ],
    }


def test_window_builds_and_default_list_populated(qapp):
    from omarchy_feature_search.app import MainWindow
    from omarchy_feature_search.theme import load_theme

    win = MainWindow(load_theme(), features_doc=_doc())
    win.show()
    qapp.processEvents()
    assert win.windowTitle() == "Omarchy Feature Search"
    # default browse list shows every feature (2 in this doc) + trailing stretch
    assert win.list_layout.count() == 3
    # selecting an item populates the detail panel
    first = win.list_layout.itemAt(0).widget()
    first.selected.emit(first._result)
    qapp.processEvents()
    assert win.detail._result is not None
    assert win.detail.name.text() == "Keybindings Cheat Sheet"
    assert "Super + K" in win.detail.command.text()
    win.close()


def test_search_filters_list(qapp):
    from omarchy_feature_search.app import MainWindow
    from omarchy_feature_search.search import results_from_doc
    from omarchy_feature_search.theme import load_theme

    win = MainWindow(load_theme(), features_doc=_doc())
    win.show()
    qapp.processEvents()
    # simulate a search result set (bypass the worker thread for determinism)
    doc = _doc()
    filtered = results_from_doc(doc)[:1]
    win._search_seq += 1
    win._on_results(filtered, seq=win._search_seq)
    qapp.processEvents()
    # one card + stretch
    assert win.list_layout.count() == 2
    win.close()
