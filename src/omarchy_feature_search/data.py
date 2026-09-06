"""Locate the bundled data + assets for the installed app.

Search order for the data directory (chosen by the first one that contains
``features.json``):

1. ``$OMARCHY_FEATURE_SEARCH_DATA`` (explicit override)
2. the package's own ``data/`` (works for pip/pipx/AUR installs)
3. ``/usr/share/omarchy-feature-search/data`` (AUR layout)
4. ``~/.local/share/omarchy-feature-search/data`` (per-user)
5. ``./data`` (run from a source checkout)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
_ENV = "OMARCHY_FEATURE_SEARCH_DATA"


def data_dir() -> Path:
    candidates: list[Path] = []
    env = os.environ.get(_ENV)
    if env:
        candidates.append(Path(env))
    candidates.append(PKG_DIR / "data")
    candidates.append(Path("/usr/share/omarchy-feature-search/data"))
    candidates.append(Path.home() / ".local/share/omarchy-feature-search/data")
    candidates.append(Path.cwd() / "data")
    for c in candidates:
        if (c / "features.json").exists():
            return c
    # Nothing built yet — default to the package data dir (writable in dev).
    return PKG_DIR / "data"


def assets_dir() -> Path:
    candidates = [
        PKG_DIR / "assets",
        Path("/usr/share/omarchy-feature-search/assets"),
        PKG_DIR.parent.parent / "assets",
    ]
    for c in candidates:
        if c.exists():
            return c
    return PKG_DIR / "assets"


def features_path() -> Path:
    return data_dir() / "features.json"


def seed_path() -> Path:
    return data_dir() / "features.seed.json"


def chroma_dir() -> Path:
    return data_dir() / "chroma"


def thumbnails_dir() -> Path:
    return data_dir() / "thumbnails"


def icon_path() -> Path:
    return assets_dir() / "icon.svg"


def logo_path() -> Path:
    return assets_dir() / "logo.svg"


def thumbnail_path(rel: str) -> Path | None:
    if not rel:
        return None
    p = data_dir() / rel
    return p if p.exists() else None


def load_features() -> dict:
    """Load the bundled feature table, falling back to the seed, then a generated seed."""
    p = features_path()
    if not p.exists():
        p = seed_path()
    if not p.exists():
        try:
            from data_pipeline.extract_table import write_seed

            p = write_seed(PKG_DIR / "data" / "features.seed.json")
        except Exception:
            return {"video_url": "", "video_id": "", "video_title": "", "features": []}
    return json.loads(p.read_text(encoding="utf-8"))
