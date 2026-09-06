"""GUI smoke test — builds the main window offscreen.

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


def test_main_window_builds(qapp):
    from omarchy_feature_search.app import MainWindow
    from omarchy_feature_search.theme import load_theme

    doc = {
        "video_url": "https://youtu.be/2IDjteRQgMQ",
        "video_id": "2IDjteRQgMQ",
        "video_title": "Omarchy Can Do WHAT?!",
        "features": [
            {"feature_group": "Keybindings & Search", "feature": "Keybindings Cheat Sheet",
             "how_to": "Super + K", "start_s": 14, "end_s": 27,
             "transcript_summary": "press Super K to see shortcuts", "thumbnail": ""},
        ],
    }
    win = MainWindow(load_theme(), features_doc=doc)
    win.show()
    qapp.processEvents()
    assert win.windowTitle() == "Omarchy Feature Search"
    # Simulate a search and ensure a result card renders.
    win.search_box.setText("keybinding")
    qapp.processEvents()
    win._do_search()
    qapp.processEvents()
    assert win.results_layout.count() >= 2  # card + stretch
    win.close()
