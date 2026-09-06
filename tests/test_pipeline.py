"""Tests for the data pipeline (VTT parsing, transcript slicing, seed integrity).

These need no heavy dependencies (no torch / chromadb / PySide6).
"""

from __future__ import annotations

from pathlib import Path

from data_pipeline import build_data
from data_pipeline.extract_table import seed_features, _t
from data_pipeline.vtt import parse_vtt, slice_cues

SAMPLE_VTT = """WEBVTT

00:00:14.000 --> 00:00:20.000
Welcome to the keybindings cheat sheet
press Super K

00:00:20.000 --> 00:00:27.000
to see every shortcut at a glance

00:05:30.000 --> 00:06:00.000
now let's install packages from the AUR
"""


def test_timestamp_parser():
    assert _t("00:00:14") == 14
    assert _t("00:34:30") == 34 * 60 + 30
    assert _t("01:02:03") == 3600 + 120 + 3


def test_vtt_parse_and_slice():
    cues = parse_vtt(SAMPLE_VTT)
    assert len(cues) == 3
    assert cues[0].start == 14.0
    assert "keybindings" in cues[0].text

    summary = slice_cues(cues, 14, 27)
    assert "keybindings" in summary
    assert "shortcut" in summary
    # a window with no overlapping cues returns empty text
    assert slice_cues(cues, 100, 110) == ""


def test_enrich_transcript_fills_summaries(tmp_path: Path):
    vtt = tmp_path / "sample.en.vtt"
    vtt.write_text(SAMPLE_VTT, encoding="utf-8")
    doc = {
        "video_url": "https://example.com/v",
        "video_id": "v",
        "video_title": "t",
        "features": [
            {"feature_group": "g", "feature": "Keybindings Cheat Sheet", "how_to": "Super + K",
             "start_s": 14, "end_s": 27, "transcript_summary": "", "thumbnail": ""},
            {"feature_group": "g", "feature": "Install Packages", "how_to": "Super + Space -> install",
             "start_s": 330, "end_s": 360, "transcript_summary": "", "thumbnail": ""},
        ],
    }
    enriched = build_data.enrich_transcript(doc, vtt)
    assert "keybindings" in enriched["features"][0]["transcript_summary"]
    assert "AUR" in enriched["features"][1]["transcript_summary"]


def test_seed_features_integrity():
    rows = seed_features()
    assert len(rows) == 83
    seen = set()
    for r in rows:
        assert r["start_s"] < r["end_s"]
        assert r["feature_group"] and r["feature"] and r["how_to"]
        key = (r["feature_group"], r["feature"])
        assert key not in seen, f"duplicate feature: {key}"
        seen.add(key)
