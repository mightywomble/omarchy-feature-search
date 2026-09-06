"""Load the active Omarchy theme palette and build a matching Qt stylesheet.

Reads the theme name from ``~/.local/state/omarchy/current/theme.name`` and the
palette from ``<theme>/colors.toml`` (user theme in ``~/.config/omarchy/themes``
first, then stock themes in ``/usr/share/omarchy/themes``). Falls back to an
embedded Omarchy-default dark palette when no theme is found.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

HOME = Path.home()
THEME_NAME_PATH = HOME / ".local/state/omarchy/current/theme.name"
USER_THEMES = HOME / ".config/omarchy/themes"
STOCK_THEMES = Path("/usr/share/omarchy/themes")

# Fallback palette (Omarchy-ish dark) used when no colors.toml can be read.
_FALLBACK = {
    "mode": "dark",
    "accent": "#ff6b35",
    "selection": "#2a2a3a",
    "muted": "#676b70",
    "background": "#0d1116",
    "dark_background": "#0a0d11",
    "darker_background": "#07090b",
    "lighter_background": "#25292d",
    "foreground": "#e6e6e6",
    "dark_foreground": "#8a8f98",
    "light_foreground": "#f0f0f0",
    "bright_foreground": "#ffffff",
    "red": "#f38ba8",
    "yellow": "#f9e2af",
    "green": "#a6e3a1",
    "cyan": "#94e2d5",
    "blue": "#89b4fa",
    "magenta": "#f5c2e7",
}

_FIELDS = tuple(_FALLBACK.keys())


@dataclass(frozen=True)
class Theme:
    colors: dict

    def c(self, key: str, default: str = "") -> str:
        return self.colors.get(key, _FALLBACK.get(key, default))

    @property
    def is_dark(self) -> bool:
        return self.colors.get("mode", "dark") == "dark"


def _theme_colors_path() -> Path | None:
    name = ""
    try:
        name = THEME_NAME_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not name:
        return None
    user = USER_THEMES / name / "colors.toml"
    if user.exists():
        return user
    stock = STOCK_THEMES / name / "colors.toml"
    if stock.exists():
        return stock
    return None


def load_theme() -> Theme:
    """Load the active Omarchy palette, or the fallback if unavailable."""
    path = _theme_colors_path()
    colors: dict = dict(_FALLBACK)
    if path is not None:
        try:
            with path.open("rb") as fh:
                loaded = tomllib.load(fh)
            for k, v in loaded.items():
                if isinstance(v, str):
                    colors[k] = v
        except Exception:
            pass
    return Theme(colors=colors)


def stylesheet(theme: Theme) -> str:
    """Build a Qt stylesheet from the theme palette."""
    c = theme.c
    return f"""
QMainWindow, QWidget {{
    background-color: {c('background')};
    color: {c('foreground')};
    font-family: "Inter", "Noto Sans", "DejaVu Sans", sans-serif;
}}
QLineEdit#searchBox {{
    background-color: {c('lighter_background')};
    color: {c('bright_foreground')};
    border: 2px solid {c('selection')};
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 16px;
    selection-background-color: {c('accent')};
}}
QLineEdit#searchBox:focus {{
    border: 2px solid {c('accent')};
}}
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QFrame#resultCard {{
    background-color: {c('lighter_background')};
    border: 1px solid {c('selection')};
    border-radius: 12px;
}}
QLabel#confidence {{
    color: {c('bright_foreground')};
    background-color: {c('accent')};
    border-radius: 10px;
    padding: 2px 10px;
    font-weight: 700;
}}
QLabel#featureName {{
    color: {c('bright_foreground')};
    font-size: 15px;
    font-weight: 700;
}}
QLabel#featureGroup {{
    color: {c('accent')};
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
QLabel#howTo {{
    color: {c('cyan', c('foreground'))};
    font-family: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", monospace;
    font-size: 12px;
}}
QLabel#summary {{
    color: {c('dark_foreground')};
    font-size: 12px;
}}
QLabel#timestamp {{
    color: {c('muted')};
    font-family: "JetBrains Mono", "Fira Code", "DejaVu Sans Mono", monospace;
    font-size: 11px;
}}
QPushButton#thumbButton {{
    background-color: {c('dark_background')};
    border: 2px solid {c('selection')};
    border-radius: 8px;
    color: {c('accent')};
}}
QPushButton#thumbButton:hover {{
    border: 2px solid {c('accent')};
}}
QFrame#playerFrame {{
    background-color: {c('darker_background')};
    border: 1px solid {c('selection')};
    border-radius: 10px;
}}
QLabel#headerTitle {{
    color: {c('bright_foreground')};
    font-size: 20px;
    font-weight: 800;
}}
QLabel#headerSub {{
    color: {c('muted')};
    font-size: 12px;
}}
QLabel#statusBar {{
    color: {c('muted')};
    font-size: 11px;
}}
QPushButton#externalButton {{
    background-color: {c('selection')};
    color: {c('bright_foreground')};
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 11px;
}}
QPushButton#externalButton:hover {{
    background-color: {c('accent')};
    color: {c('background')};
}}
"""
