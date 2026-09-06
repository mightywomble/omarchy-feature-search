# Omarchy Feature Search

A native Linux desktop app that turns NetworkChuck's *"Omarchy Can Do WHAT?! 50
Features You're Missing"* video into a searchable knowledge base. Type **"how do
I…"** and get, per match:

- the structured feature row (feature group, feature, **how to use**, start/end timestamp)
- a **match-confidence %**
- a short **transcript summary** of that part of the video
- a **video-frame thumbnail** — click it to play that exact segment inline,
  seeking to the timestamp.

Built for [Omarchy](https://omarchy.org/) (Arch + Hyprland). The UI loads the
active Omarchy theme's `colors.toml` at runtime, so it always matches your
desktop look and feel, and the app icon is a NetworkChuck-themed mark.

## How it works

- **Search** — semantic vector search (ChromaDB + `sentence-transformers`
  `all-MiniLM-L6-v2`) when the optional deps + built index are present, else a
  fast local keyword fallback. Both return a 0–100 confidence %.
- **Playback** — `mpv` streams the YouTube segment at the timestamp
  (`mpv --start=SS --ytdl …`). No full video download needed to play. Embedded
  in-app when `python-mpv` is installed, otherwise an external mpv window.
- **Data** — `data/features.json` ships bundled (feature table + transcript
  summaries). The optional pipeline (`python -m data_pipeline.build_data`)
  enriches it with real frame thumbnails and builds the semantic vector index.

## Install

### Omarchy / Arch (recommended) — AUR

```fish
yay -S omarchy-feature-search
# or: paru -S omarchy-feature-search
```

Then launch it from the Super+Space launcher (it ships a `.desktop` + icon), or
run `omarchy-feature-search`.

Required deps pulled in by the package: `python-pyside6`, `mpv`. Heavy/optional
deps (`python-sentence-transformers`, `python-chromadb`, `python-mpv`, `ffmpeg`,
`yt-dlp`) are listed as `optdepends` — install them to unlock embedded playback
and semantic search, then run the data pipeline once.

### Other distros — pipx

```fish
pipx install omarchy-feature-search
pipx inject omarchy-feature-search python-mpv chromadb sentence-transformers  # optional extras
```

## Build the enhanced bundled data (optional, one-time)

```fish
python -m data_pipeline.build_data --steps transcript,thumbnails,embed
```

- `transcript` — `yt-dlp` pulls the auto-generated subtitle track; each feature's
  timestamp range is sliced into a transcript summary. (Lightweight, no video
  download.)
- `thumbnails` — downloads the video once and uses `ffmpeg` to grab a frame at
  each feature's start time. (Heavier — best run on a dev/test machine.)
- `embed` — embeds each feature (description + how-to + transcript) with
  `sentence-transformers` into a persistent ChromaDB index for semantic search.

Without this, the app still works: keyword search, how-to text as the summary,
and styled placeholder thumbnails that still play the segment on click.

## Run from source

```fish
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
python -m omarchy_feature_search
```

## Tests

```fish
pip install -e ".[dev]"
pytest
```

The pipeline and search tests need no heavy deps (they cover VTT slicing,
timestamp parsing, keyword ranking/confidence). The GUI smoke test skips
automatically if `PySide6` is not installed.
