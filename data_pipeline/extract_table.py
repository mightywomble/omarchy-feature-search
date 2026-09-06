"""Seed the structured feature table from the PDF extraction.

Contains the complete feature list (feature group, feature, how-to, start/end
timestamps) for NetworkChuck's Omarchy video, used to seed ``features.json``
and to drive transcript slicing, thumbnail extraction and embedding.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

VIDEO_URL = "https://youtu.be/2IDjteRQgMQ"
VIDEO_ID = "2IDjteRQgMQ"
VIDEO_TITLE = "Omarchy Can Do WHAT?! 50 Features You're Missing"


class FeatureRow(TypedDict, total=False):
    feature_group: str
    feature: str
    how_to: str
    start_s: int
    end_s: int
    transcript_summary: str
    thumbnail: str


def _t(hms: str) -> int:
    """Parse 'HH:MM:SS' or 'MM:SS' into seconds."""
    parts = hms.split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 3:
        h, m, s = parts
        return h * 3600 + m * 60 + s
    if len(parts) == 2:
        m, s = parts
        return m * 60 + s
    raise ValueError(f"bad timestamp: {hms!r}")


# (feature_group, feature, how_to, start, end)
_ROWS: list[tuple[str, str, str, str, str]] = [
    ("Keybindings & Search", "Keybindings Cheat Sheet", "Super + K", "00:00:14", "00:00:27"),
    ("Keybindings & Search", "Universal System Search", "Super + Space", "00:00:27", "00:00:34"),
    ("Keybindings & Search", "App Search Launcher", "Super + Alt + Space", "00:00:34", "00:00:39"),
    ("Clipboard & Navigation", "Universal Copy / Paste", "Super + C / Super + V", "00:00:39", "00:00:47"),
    ("Clipboard & Navigation", "Clipboard History (with images)", "Super + Ctrl + V", "00:00:47", "00:00:53"),
    ("Window Management", "Launch Browser", "Super + Shift + B", "00:00:53", "00:00:58"),
    ("Window Management", "Focus Navigation", "Super + Left / Right", "00:00:58", "00:01:03"),
    ("Window Management", "Swap Windows", "Super + Shift + Left / Right", "00:01:03", "00:01:09"),
    ("Window Management", "Change Layout (Horizontal/Vertical)", "Super + J", "00:01:09", "00:01:14"),
    ("Window Management", "Drag Window with Mouse", "Hold Super + Drag", "00:01:14", "00:01:21"),
    ("Window Management", "Close Current Window", "Super + W", "00:01:21", "00:01:25"),
    ("Window Management", "Close All Windows", "Ctrl + Alt + Delete", "00:01:25", "00:01:29"),
    ("Workspaces", "Switch Workspaces", "Super + 1 / 2 / 3 / 4", "00:01:29", "00:01:38"),
    ("Workspaces", "Move Window & Follow to Workspace", "Super + Shift + [Number]", "00:01:38", "00:01:44"),
    ("Workspaces", "Move Window without Following", "Super + Shift + Alt + [Number]", "00:01:44", "00:01:52"),
    ("Window Modes", "Application Full Screen", "Cmd + F", "00:01:52", "00:02:00"),
    ("Window Modes", "Full Width Mode", "Cmd + Alt + F", "00:02:00", "00:02:08"),
    ("Window Modes", "Native Tiling Full Screen", "Super + Ctrl + F", "00:02:08", "00:02:17"),
    ("Layouts & Scratchpad", "Master / Scrolling Layout", "Cmd + L", "00:02:17", "00:02:30"),
    ("Layouts & Scratchpad", "Send Window to Scratchpad", "Super + Alt + S", "00:02:30", "00:02:39"),
    ("Layouts & Scratchpad", "Toggle Scratchpad Window", "Ctrl + S", "00:02:39", "00:02:56"),
    ("Window Grouping", "Group Windows / Tabs", "Super + G", "00:02:56", "00:03:09"),
    ("Window Grouping", "Switch Between Group Tabs", "Super + Alt + 1/2 or Super + Ctrl + Arrow", "00:03:09", "00:03:19"),
    ("Window Grouping", "Ungroup Windows", "Super + Alt + G", "00:03:19", "00:03:26"),
    ("App Management", "Install Packages (Arch / AUR)", "Super + Space → install", "00:05:25", "00:06:01"),
    ("App Management", "Remove Packages", "Super + Space → remove package", "00:06:01", "00:06:10"),
    ("App Management", "Quick Install Popular Apps", "Cmd + Space → Type app name", "00:06:10", "00:06:22"),
    ("App Management", "Remove Pre-installed Bloatware", "Super + Space → pre-installs", "00:06:22", "00:06:39"),
    ("App Management", "Set Default Apps (e.g. Browser)", "Cmd + Space → browser set defaults", "00:06:39", "00:06:56"),
    ("Web & TUI Apps", "Turn Any Website into Web App", "Super + Space → web app install", "00:06:56", "00:07:20"),
    ("Web & TUI Apps", "Default Web App Hotkeys", "Super + Shift + Y (YouTube) / X", "00:07:20", "00:07:29"),
    ("Web & TUI Apps", "Create Floating TUI App Launcher", "Cmd + Space → tui install", "00:07:29", "00:07:53"),
    ("Web & TUI Apps", "App Install via Hotkey", "Super + Shift + G (Signal)", "00:07:53", "00:08:03"),
    ("Dev Environments", "Spin Up Docker Dev Environments", "Super + Space → development", "00:08:03", "00:08:23"),
    ("Dev Environments", "Launch Lazy Docker", "Super + Shift + D", "00:08:23", "00:08:28"),
    ("Dev Environments", "Open / Change Default IDE", "Cmd + Shift + N & Super + Space → VS Code", "00:08:28", "00:08:52"),
    ("Terminal & Shell", "Terminal Defaults & Tmux / Herder", "Super + Alt + Return / Super + Ctrl + Enter", "00:08:52", "00:09:20"),
    ("Terminal & Shell", "Built-in CLI Fuzzy Finder", "ff", "00:09:20", "00:09:32"),
    ("Terminal & Shell", "Shell History Search", "Ctrl + R", "00:09:32", "00:09:35"),
    ("Terminal & Shell", "Built-in CLI Utilities", "zoxide (cd), rg (ripgrep), fd, bat, exa (ls, lt, lsa)", "00:09:35", "00:09:54"),
    ("System & Updates", "System Updates & Channel Config", "Super + Space → update", "00:09:54", "00:10:30"),
    ("System & Updates", "BTRFS System Snapshots", "snapshot create", "00:10:30", "00:10:52"),
    ("System & Security", "Safe Config Directory", "Custom configs saved in ~/.config", "00:10:52", "00:11:15"),
    ("System & Security", "Default Security & SSH Config", "Super + Space → SSH", "00:11:15", "00:11:35"),
    ("System & Security", "Change User / Encryption Passwords", "Super + Space → password", "00:11:35", "00:11:41"),
    ("System & Security", "Lock Screen", "Super + Ctrl + L", "00:11:41", "00:11:46"),
    ("System & Security", "Fingerprint Reader Sudo", "Super + Space → passwordless sudo", "00:11:46", "00:12:13"),
    ("Toggles & Aesthetics", "Quick Toggle Menu", "Super + Ctrl + O", "00:12:13", "00:12:24"),
    ("Toggles & Aesthetics", "Nightlight Mode", "Super + Ctrl + N", "00:12:24", "00:12:29"),
    ("Toggles & Aesthetics", "Hide Quick Bar", "Super + Shift + Space", "00:12:29", "00:12:35"),
    ("Toggles & Aesthetics", "Screensaver Launcher", "Super + Escape", "00:12:35", "00:12:47"),
    ("Toggles & Aesthetics", "Toggle Window Gaps & Borders", "Super + Shift + Backspace", "00:12:47", "00:13:00"),
    ("Networking", "Control Panel & Speedtest", "Super + Ctrl + W", "00:13:00", "00:13:36"),
    ("Networking", "CLI Network Band Selection", "omarchy network band", "00:13:36", "00:13:48"),
    ("Hardware Management", "Restart Hardware Drivers (Wi-Fi, BT)", "Super + Space → hardware", "00:13:48", "00:14:10"),
    ("Hardware Management", "Persistent SSH Connections", "Automatic reconnection on network re-establishment", "00:14:10", "00:14:36"),
    ("Hardware Management", "Battery & Auto Power Profiles", "Unplugging automatically switches profile", "00:14:36", "00:15:03"),
    ("System Monitoring", "Btop Floating / Tiled Task Manager", "Super + Ctrl + T (Toggle tile: Super + T)", "00:15:03", "00:15:23"),
    ("Media & Screen Tools", "Freeze-Frame Selective Screenshot", "Super + Space → screenshot", "00:15:23", "00:15:35"),
    ("Media & Screen Tools", "Screen Recorder with Webcam Overlay", "Webcam size adjustment: Super + Alt + [ / ]", "00:15:35", "00:16:08"),
    ("Media & Screen Tools", "Screen Optical Character Recognition (OCR)", "Super + Alt + PrintScreen", "00:16:08", "00:16:21"),
    ("Media & Screen Tools", "Screen QR Code Reader", "Super + Space → QR", "00:16:21", "00:16:39"),
    ("Media & Screen Tools", "Quick Video / GIF Transcoder", "Super + Space → transcode", "00:16:39", "00:17:03"),
    ("Disk Utilities", "Interactive Disk Usage Utility", "Super + Space → disk usage", "00:17:03", "00:17:33"),
    ("AI & Productivity", "Local VoxType Speech-to-Text Setup", "omarchy voxtype", "00:17:33", "00:19:00"),
    ("File Sharing", "LocalSend AirDrop Alternative", "Super + Ctrl + S", "00:19:00", "00:20:10"),
    ("File Sharing", "Share Clipboard via Network", "omarchy share clipboard", "00:20:10", "00:20:20"),
    ("Utilities", "Quick Emoji Picker", "Caps Lock + M (e.g. S for smile)", "00:20:20", "00:20:42"),
    ("Utilities", "Timer & Reminders", "Super + Ctrl + R", "00:20:42", "00:20:58"),
    ("Media Utilities", "Download Web Video Hotkey", "Alt + Shift + D", "00:20:58", "00:21:47"),
    ("Media Utilities", "CLI Video Trimming Tool", "omacut", "00:21:47", "00:22:20"),
    ("Built-in Apps", "Default Built-in Apps", "Notepad (Write), Calculator (Calc), Obsidian (Super+Shift+O), Amp (Super+Shift+Alt+M)", "00:22:20", "00:23:35"),
    ("Theming & Customization", "Theme Switcher", "Super + Ctrl + Shift + Space", "00:23:35", "00:24:00"),
    ("Theming & Customization", "Aether Auto-Theming from Wallpaper", "Super + Space → Aether", "00:24:00", "00:24:40"),
    ("Theming & Customization", "QuickShell Bar Placement", "omarchy bar position [top/bottom/left]", "00:24:40", "00:25:00"),
    ("Theming & Customization", "Screensaver Customization", "style screen saver set from image", "00:25:26", "00:25:50"),
    ("Theming & Customization", "Desktop Background Switcher", "Super + Ctrl + Space", "00:28:28", "00:28:35"),
    ("Plugins & Extensions", "Plugin Marketplace & Management", "Super + Space → plugin", "00:25:55", "00:26:20"),
    ("Plugins & Extensions", "CLI Plugin Addition", "omarchy plugin add [repo_url]", "00:26:20", "00:27:23"),
    ("AI Integration", "Agent & Model Switcher", "Super + Space → agent", "00:27:23", "00:27:52"),
    ("AI Integration", "Launch Default AI Agent", "Super + Shift + Ctrl + A", "00:27:52", "00:28:18"),
    ("AI Integration", "Control OS via AI Skill Set", "Prompt agent to alter OS themes/system settings", "00:28:35", "00:32:00"),
    ("Plugin Development", "Create & Publish Plugins via AI", "Prompt AI agent to write plugin specs & submit repo", "00:32:00", "00:34:30"),
]


def seed_features() -> list[FeatureRow]:
    """Return the canonical feature rows with timestamps as seconds."""
    rows: list[FeatureRow] = []
    for group, feature, how_to, start, end in _ROWS:
        rows.append(
            {
                "feature_group": group,
                "feature": feature,
                "how_to": how_to,
                "start_s": _t(start),
                "end_s": _t(end),
                "transcript_summary": "",
                "thumbnail": "",
            }
        )
    return rows


def write_seed(out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "video_url": VIDEO_URL,
        "video_id": VIDEO_ID,
        "video_title": VIDEO_TITLE,
        "features": seed_features(),
    }
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Seed the bundled feature table JSON.")
    ap.add_argument(
        "--out",
        default=str(Path(__file__).resolve().parent.parent / "src" / "omarchy_feature_search" / "data" / "features.json"),
        help="Output path for features.json",
    )
    args = ap.parse_args()
    path = write_seed(args.out)
    print(f"wrote {len(seed_features())} features -> {path}")
