"""WebVTT subtitle parsing and timestamp-range slicing.

Parses an auto-generated ``.vtt`` subtitle track into a flat list of
(start_seconds, end_seconds, text) cues and slices out the transcript text that
falls inside an arbitrary ``[start_s, end_s]`` window.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_VTT_TIME = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})"
)
# YouTube auto-captions embed inline timing/alignment tags like
# ``<00:14:35.040><c>`` and ``</c>``; strip them from cue text.
_INLINE_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def _parse_timestamp(ts: str) -> float:
    """Parse 'HH:MM:SS.mmm' into seconds."""
    h, m, rest = ts.split(":")
    s, ms = rest.split(".")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_vtt(text: str) -> list[Cue]:
    """Parse raw WebVTT content into a list of Cue objects."""
    cues: list[Cue] = []
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        m = _VTT_TIME.search(line)
        if m:
            start = _parse_timestamp(m.group("start"))
            end = _parse_timestamp(m.group("end"))
            i += 1
            text_lines: list[str] = []
            while i < n and lines[i].strip() != "":
                t = lines[i].strip()
                if not t.startswith("WEBVTT") and not _VTT_TIME.search(t) and not t.isdigit():
                    text_lines.append(t)
                i += 1
            joined = " ".join(text_lines).strip()
            joined = _INLINE_TAG.sub("", joined)
            joined = _WS.sub(" ", joined).strip()
            if joined:
                cues.append(Cue(start=start, end=end, text=joined))
        else:
            i += 1
    return cues


def slice_cues(cues: list[Cue], start_s: float, end_s: float) -> str:
    """Return the concatenated text of cues that overlap [start_s, end_s]."""
    parts: list[str] = []
    for cue in cues:
        if cue.end < start_s or cue.start > end_s:
            continue
        parts.append(cue.text)
    return " ".join(parts)


def load_and_slice(vtt_path: str | Path, start_s: float, end_s: float) -> str:
    """Convenience: read a .vtt file and slice it in one call."""
    text = Path(vtt_path).read_text(encoding="utf-8")
    return slice_cues(parse_vtt(text), start_s, end_s)
