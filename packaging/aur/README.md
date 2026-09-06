# AUR packaging for omarchy-feature-search

Files here build the Arch User Repository package. Two install paths are
supported by the same package:

## 1. From a released source tarball (the `source=` in the PKGBUILD)

1. Tag a release: `git tag v0.1.0 && git push origin v0.1.0`
2. The PKGBUILD `source=()` downloads the GitHub tarball for that tag.
3. Build locally to verify:
   ```fish
   makepkg -si
   ```
4. Publish to AUR (`omarchy-feature-search`) — see the AUR submit docs.

## 2. `-git` variant (optional, not included here)

A `-git` PKGBUILD would use `source=("git+https://github.com/david/ncomarchykb.git")`
and set `pkgver()` to derive a version from `git describe`. Add later if desired.

## What the package installs

- `omarchy-feature-search` console script (entry point in `pyproject.toml`)
- the Python package under `site-packages/`, including the bundled
  `data/features.json` (structured table + transcript summaries) and the
  `assets/` SVGs.
- `/usr/share/applications/omarchy-feature-search.desktop` (launcher entry)
- `/usr/share/icons/hicolor/scalable/apps/omarchy-feature-search.svg` (icon)

So it shows up in the Omarchy Super+Space launcher immediately after install.

## Optional deps (optdepends)

| Package | Unlocks |
|---|---|
| `python-mpv` | embedded in-app video playback (otherwise external mpv window) |
| `python-sentence-transformers` + `python-chromadb` | semantic vector search |
| `yt-dlp` + `ffmpeg` | one-time data pipeline to add real thumbnails + rebuild the vector index |

After installing the optdepends for full functionality, run the data pipeline
once to build the vector index and thumbnails:

```fish
python -m data_pipeline.build_data --steps thumbnails,embed
```

(`transcript` summaries already ship bundled in `features.json`.)
