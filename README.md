# Omarchy Feature Search

A native Linux desktop app that turns NetworkChuck's *"Omarchy Can Do WHAT?! 50
Features You're Missing"* video into a searchable knowledge base.

Browse all 83 features, search to filter the list, click one to see its details
(name, summary, command, thumbnail), and click the thumbnail to play that
exact segment of the video in-app with audio.

Built for [Omarchy](https://omarchy.org/) (Arch + Hyprland). The UI loads the
active Omarchy theme's `colors.toml` at runtime, so it always matches your
desktop look and feel.

## Features

- **Master-detail layout** — browsable list of all 83 features (group, name,
  command, thumbnail) on the left; detail panel on the right.
- **Live search** — type to filter the list instantly. Uses fast keyword search
  immediately, then switches to semantic vector search (ChromaDB +
  `sentence-transformers`) once the model finishes loading in the background.
- **In-app video playback** — clicking a thumbnail downloads just the segment
  (≤480p, AAC audio, cached per segment) and plays it in-app via Qt Multimedia,
  pausing at the clip's end. First click per segment takes ~20s (one-time
  download); subsequent clicks are instant from cache.
- **Fun progress overlay** — rotating tech phrases ("Cleaning the lugnuts…",
  "Tweaking the pipes…", etc.) while the segment downloads.
- **Informative summaries** — rich-text summary with description, how-to,
  category, timestamp, and a link to search for more info on YouTube.
- **Themed** — matches the active Omarchy desktop theme automatically.

## Requirements

- Python 3.11+
- PySide6 (Qt GUI)
- Qt Multimedia (in-app video + audio)
- yt-dlp (segment download)
- ffmpeg (video merge/transcode during download)

Optional (for semantic search):
- chromadb
- sentence-transformers

## Install

### Omarchy / Arch — AUR

```fish
yay -S omarchy-feature-search
# or: paru -S omarchy-feature-search
```

Then launch it from the Super+Space launcher (it ships a `.desktop` + icon), or
run `omarchy-feature-search` from the terminal.

The AUR package pulls in `python-pyside6` and `mpv` as required deps. The
heavy/optional deps (`python-sentence-transformers`, `python-chromadb`,
`python-mpv`, `ffmpeg`, `yt-dlp`) are listed as `optdepends` — install them to
unlock semantic search and in-app video playback.

### Other distros — pipx

```fish
pipx install omarchy-feature-search
pipx inject omarchy-feature-search chromadb sentence-transformers  # optional: semantic search
```

### From source

```fish
git clone git@git.safehomelan.com:david/ncomarchykb.git
cd ncomarchykb
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
python -m omarchy_feature_search
```

## Build the bundled data (one-time, optional)

The app ships with a pre-built `features.json` (structured table + transcript
summaries). To add real frame thumbnails and build the semantic vector index,
run the data pipeline once:

```fish
python -m data_pipeline.build_data --steps thumbnails,embed
```

- `thumbnails` — downloads the video and uses `ffmpeg` to grab a frame at each
  feature's start time.
- `embed` — embeds each feature (description + how-to + transcript) with
  `sentence-transformers` into a persistent ChromaDB index for semantic search.

Transcript summaries are already bundled in `features.json` (pulled from the
video's auto-generated subtitles).

Without this step, the app still works: keyword search, how-to text as
summaries, and placeholder thumbnails that still play the segment on click.

## Tests

```fish
pip install -e ".[dev]"
pytest
```

16 tests covering VTT parsing/slicing, timestamp parsing, seed integrity,
keyword search ranking/confidence/sorting, semantic index availability, and
GUI smoke (builds the main window offscreen).

## Project layout

```
ncomarchykb/
  src/omarchy_feature_search/   # runtime package
    app.py                        # PySide6 master-detail main window
    search.py                     # keyword + semantic search engine
    player.py                     # segment download + cache
    theme.py                      # Omarchy colors.toml -> Qt stylesheet
    data.py                       # bundled data locator
    data/features.json           # 83 features + transcript summaries
    assets/                      # NetworkChuck-themed icon + logo SVGs
  data_pipeline/                 # one-time data build
    extract_table.py             # seed 83 features from the PDF
    vtt.py                       # WebVTT parser + timestamp slicer
    build_data.py                # CLI: transcript, thumbnails, embed
  packaging/aur/                # AUR PKGBUILD + .desktop entry
  tests/                         # 16 pytest tests
```

## License

MIT
