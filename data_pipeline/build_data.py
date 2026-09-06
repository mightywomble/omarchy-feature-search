"""Build the bundled data artefacts.

Run once (ideally on a dev/test machine) to enrich the seeded feature table with
real transcript summaries, frame thumbnails and a semantic vector index::

    python -m data_pipeline.build_data --steps transcript,thumbnails,embed

Each step is independent and safe to re-run. ``transcript`` is lightweight (no
video download); ``thumbnails`` downloads the video once; ``embed`` requires
``sentence-transformers`` + ``chromadb``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from data_pipeline.extract_table import VIDEO_URL, seed_features, write_seed
from data_pipeline.vtt import load_and_slice, parse_vtt, slice_cues

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "src" / "omarchy_feature_search" / "data"
FEATURES_JSON = DATA_DIR / "features.json"
THUMB_DIR = DATA_DIR / "thumbnails"
CHROMA_DIR = DATA_DIR / "chroma"

ALL_STEPS = ("transcript", "thumbnails", "embed")


# --------------------------------------------------------------------------- #
# features.json load / save
# --------------------------------------------------------------------------- #
def load_features() -> dict:
    """Load the bundled features.json, falling back to the seed if absent."""
    if FEATURES_JSON.exists():
        return json.loads(FEATURES_JSON.read_text(encoding="utf-8"))
    write_seed(FEATURES_JSON)
    return json.loads(FEATURES_JSON.read_text(encoding="utf-8"))


def save_features(data: dict) -> None:
    FEATURES_JSON.parent.mkdir(parents=True, exist_ok=True)
    FEATURES_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- #
# transcript step
# --------------------------------------------------------------------------- #
def fetch_transcript(video_url: str, dest_dir: Path) -> Path:
    """Use yt-dlp to download the auto-generated English .vtt subtitle track."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_tmpl = str(dest_dir / "%(id)s")
    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--sub-format", "vtt",
        "--skip-download",
        "-o", out_tmpl,
        video_url,
    ]
    print(f"==> running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    vtt_files = sorted(dest_dir.glob("*.vtt"))
    if not vtt_files:
        raise RuntimeError("no .vtt file produced by yt-dlp")
    return vtt_files[0]


def enrich_transcript(data: dict, vtt_path: Path) -> dict:
    """Fill transcript_summary on each feature from the sliced subtitle cues."""
    cues = parse_vtt(vtt_path.read_text(encoding="utf-8"))
    for feat in data["features"]:
        summary = slice_cues(cues, feat["start_s"], feat["end_s"])
        feat["transcript_summary"] = summary.strip()
    return data


def run_transcript() -> None:
    data = load_features()
    with tempfile.TemporaryDirectory() as td:
        vtt = fetch_transcript(data.get("video_url", VIDEO_URL), Path(td))
        data = enrich_transcript(data, vtt)
    save_features(data)
    filled = sum(1 for f in data["features"] if f["transcript_summary"])
    print(f"==> transcript: enriched {filled}/{len(data['features'])} features")


# --------------------------------------------------------------------------- #
# thumbnails step
# --------------------------------------------------------------------------- #
def download_video(video_url: str, dest: Path, height: int = 720) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fmt = f"best[height<={height}][ext=mp4]/best[height<={height}]/best"
    cmd = ["yt-dlp", "-f", fmt, "-o", str(dest), video_url]
    print(f"==> running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    return dest


def extract_thumbnails(video_path: Path, data: dict, thumb_dir: Path) -> dict:
    thumb_dir.mkdir(parents=True, exist_ok=True)
    for i, feat in enumerate(data["features"], 1):
        thumb = thumb_dir / f"{i:03d}.jpg"
        ts = max(0, feat["start_s"])
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ts),
            "-i", str(video_path),
            "-frames:v", "1",
            "-vf", "scale=480:-1",
            "-q:v", "5",
            str(thumb),
        ]
        print(f"==> thumb {i:03d} @ {ts}s")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        feat["thumbnail"] = str(thumb.relative_to(DATA_DIR))
    return data


def run_thumbnails(height: int = 720) -> None:
    data = load_features()
    with tempfile.TemporaryDirectory() as td:
        video = download_video(data.get("video_url", VIDEO_URL), Path(td) / "video.mp4", height)
        data = extract_thumbnails(video, data, THUMB_DIR)
    save_features(data)
    print(f"==> thumbnails: wrote {len(data['features'])} frames -> {THUMB_DIR}")


# --------------------------------------------------------------------------- #
# embed step
# --------------------------------------------------------------------------- #
def _combined_text(feat: dict) -> str:
    parts = [feat.get("feature", ""), feat.get("how_to", ""), feat.get("transcript_summary", "")]
    return " | ".join(p for p in parts if p)


def build_embeddings(data: dict, chroma_path: Path, model_name: str = "all-MiniLM-L6-v2") -> None:
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SystemExit(
            "embed step requires `sentence-transformers` and `chromadb`:\n"
            "  pip install sentence-transformers chromadb"
        ) from exc

    print(f"==> loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    if chroma_path.exists():
        shutil.rmtree(chroma_path)
    client = chromadb.PersistentClient(path=str(chroma_path))
    coll = client.get_or_create_collection("video_segments")

    feats = data["features"]
    docs = [_combined_text(f) for f in feats]
    embs = model.encode(docs, show_progress_bar=True).tolist()
    coll.add(
        ids=[f"f{i+1:03d}" for i in range(len(feats))],
        documents=docs,
        embeddings=embs,
        metadatas=[
            {
                "start_s": f["start_s"],
                "end_s": f["end_s"],
                "feature": f["feature"],
                "feature_group": f["feature_group"],
                "how_to": f["how_to"],
            }
            for f in feats
        ],
    )
    print(f"==> embed: indexed {len(feats)} features -> {chroma_path}")


def run_embed(model_name: str = "all-MiniLM-L6-v2") -> None:
    data = load_features()
    build_embeddings(data, CHROMA_DIR, model_name)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build bundled Omarchy Feature Search data.")
    ap.add_argument("--steps", default="transcript", help=f"comma list: {','.join(ALL_STEPS)}")
    ap.add_argument("--thumb-height", type=int, default=720, help="max video height for thumbnail extraction")
    ap.add_argument("--model", default="all-MiniLM-L6-v2", help="sentence-transformers model name")
    args = ap.parse_args(argv)

    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    bad = [s for s in steps if s not in ALL_STEPS]
    if bad:
        ap.error(f"unknown steps: {bad}; choose from {ALL_STEPS}")

    # Make sure the bundled feature table exists first.
    load_features()

    for step in steps:
        if step == "transcript":
            run_transcript()
        elif step == "thumbnails":
            run_thumbnails(height=args.thumb_height)
        elif step == "embed":
            run_embed(model_name=args.model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
