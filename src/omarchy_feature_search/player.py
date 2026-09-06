"""Video playback for Omarchy Feature Search.

Downloads just the segment (the feature's timestamp range) as a ≤480p non-AV1
merged MP4 with AAC audio, cached per segment. The local file is then played
in-app via Qt's ``QMediaPlayer`` + ``QVideoWidget``. First click per segment
takes ~20s (one-time download); subsequent clicks are instant (cached).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Non-AV1, ≤480p video + m4a audio (AAC), merged into mp4.
_FMT = (
    "bestvideo[height<=480][vcodec!*=av01]+bestaudio[ext=m4a]"
    "/bestvideo[height<=480][vcodec!*=av01]+bestaudio"
    "/best[height<=480][vcodec!*=av01]/best[height<=480]/best"
)
_CACHE_DIR = Path.home() / ".cache" / "omarchy-feature-search"


def _fmt_ts(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def segment_cache_path(video_id: str, start_s: int, end_s: int) -> Path:
    return _CACHE_DIR / f"{video_id}_{start_s}_{end_s}.mp4"


def ensure_segment_cached(
    video_id: str, start_s: int, end_s: int, video_url: str
) -> Path | None:
    """Download just the segment [start_s, end_s] once to a cache file."""
    dest = segment_cache_path(video_id, start_s, end_s)
    if dest.exists() and dest.stat().st_size > 50_000:
        return dest
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    section = f"*{_fmt_ts(start_s)}-{_fmt_ts(end_s)}"
    tmp = dest.with_suffix(".part.mp4")
    cmd = [
        "yt-dlp",
        "-f", _FMT,
        "--merge-output-format", "mp4",
        "--download-sections", section,
        "--force-keyframes-at-cuts",
        "-o", str(tmp),
        "--no-playlist",
        "--no-warnings",
        video_url,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0 and tmp.exists():
            tmp.rename(dest)
            return dest
    except Exception:
        pass
    tmp.unlink(missing_ok=True)
    return None
