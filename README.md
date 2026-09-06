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

## Install

### Omarchy / Arch — build and install locally (verified)

```fish
git clone git@git.safehomelan.com:david/ncomarchykb.git
cd ncomarchykb/packaging/aur
makepkg -si PKGBUILD
```

This builds the wheel, installs it via pacman (0.33 MiB), drops the
`.desktop` entry + icon, and registers the `omarchy-feature-search` console
script in `/usr/bin/`. After install:

- **Super+Space launcher** — search for "Omarchy Feature Search" and click it
- **Terminal** — run `omarchy-feature-search`

For the git variant (tracks latest HEAD, no release tag needed):

```fish
makepkg -si PKGBUILD-git
```

### Publish to the AUR (for `yay -S` install)

```fish
# 1. Register at https://aur.archlinux.org/register and upload your SSH key
# 2. Clone the empty AUR package
git clone ssh://aur@aur.archlinux.org/omarchy-feature-search.git aur-pkg
cd aur-pkg
# 3. Copy files in
cp /path/to/ncomarchykb/packaging/aur/PKGBUILD .
cp /path/to/ncomarchykb/packaging/aur/omarchy-feature-search.desktop .
makepkg --printsrcinfo > .SRCINFO
# 4. Commit and push to AUR
git add PKGBUILD omarchy-feature-search.desktop .SRCINFO
git commit -m "Initial import: omarchy-feature-search 0.1.0"
git push
# 5. Install from AUR
yay -S omarchy-feature-search
```

Full details and the `-git` variant in `packaging/aur/README.md`.

### Other distros — pipx

```fish
pipx install omarchy-feature-search
pipx inject omarchy-feature-search chromadb sentence-transformers  # optional: semantic search
```

### From source (dev)

```fish
git clone git@git.safehomelan.com:david/ncomarchykb.git
cd ncomarchykb
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
python -m omarchy_feature_search
```

## Requirements

**Installed by the package:**
- Python 3.11+
- PySide6 (Qt GUI + Qt Multimedia for in-app video/audio)
- yt-dlp (segment download)
- ffmpeg (video merge/transcode during download)

**Optional (for semantic search):**
- chromadb
- sentence-transformers

Install the optional deps on Arch:
```fish
sudo pacman -S python-sentence-transformers python-chromadb
```

## Usage

1. Launch the app from the Super+Space launcher or run `omarchy-feature-search`.
2. The left pane shows all 83 features. Browse or type in the search box to
   filter (e.g. "screenshot", "install", "workspace", "night light").
3. Click a feature to see its details on the right: name, summary, command(s),
   and a video thumbnail.
4. Click the thumbnail to play that segment of the video in-app. The first
   play of each segment downloads it once (~20s with a fun progress overlay);
   replays are instant from cache.
5. The summary includes a link to search for more info on YouTube.

## Build the bundled data (one-time, optional)

The app ships with a pre-built `features.json` (structured table + transcript
summaries). To add real frame thumbnails and build the semantic vector index:

```fish
python -m data_pipeline.build_data --steps thumbnails,embed
```

- `thumbnails` — downloads the video and uses `ffmpeg` to grab a frame at each
  feature's start time.
- `embed` — embeds each feature with `sentence-transformers` into a ChromaDB
  index for semantic search.

Transcript summaries are already bundled (pulled from the video's auto-generated
subtitles). Without this step the app still works — keyword search and
placeholder thumbnails that still play segments on click.

## Tests

```fish
pip install -e ".[dev]"
pytest
```

16 tests covering VTT parsing/slicing, timestamp parsing, seed integrity,
keyword search ranking/confidence/sorting, semantic index availability, and
GUI smoke (builds the main window offscreen).

## Uninstall

```fish
sudo pacman -R omarchy-feature-search
```

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
  packaging/aur/                # AUR PKGBUILD + .desktop entry + guide
  tests/                         # 16 pytest tests
```

## License

MIT
