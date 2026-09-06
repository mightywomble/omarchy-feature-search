"""Search the feature index.

Two backends:

* **semantic** — ChromaDB + sentence-transformers, when the optional deps and a
  built vector index are present. Confidence = cosine-similarity percentage.
* **keyword** — always-available fallback scoring token overlap against the
  feature/how-to/transcript text. Confidence = normalised token-coverage %.

Both return a list of :class:`Result` with a 0–100 ``confidence``.

The semantic embedding model is loaded **lazily** on the first semantic search
(see :meth:`SearchEngine._ensure_model`), so constructing a ``SearchEngine`` is
cheap and instant — important so the app can show the full browse list at
startup without importing/loading torch.
"""

from __future__ import annotations

import importlib.util as _ilu
import re
from dataclasses import dataclass, field

from omarchy_feature_search import data as data_mod


def _have(*mods: str) -> bool:
    """True if every module is importable, WITHOUT importing them."""
    return all(_ilu.find_spec(m) is not None for m in mods)

_MODEL_NAME = "all-MiniLM-L6-v2"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "a", "an", "the", "how", "to", "do", "i", "in", "on", "of", "for", "and",
    "or", "is", "it", "my", "me", "with", "use", "using", "what", "can",
}


@dataclass
class Result:
    feature: str
    feature_group: str
    how_to: str
    transcript_summary: str
    confidence: float
    start_s: int
    end_s: int
    video_url: str
    thumbnail: str = ""
    start_fmt: str = field(default="")
    end_fmt: str = field(default="")

    def __post_init__(self) -> None:
        self.start_fmt = fmt_time(self.start_s)
        self.end_fmt = fmt_time(self.end_s)


def fmt_time(seconds: int) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def _feature_text(feat: dict) -> str:
    return " ".join(
        str(feat.get(k, "")) for k in ("feature", "how_to", "transcript_summary", "feature_group")
    )


def results_from_doc(doc: dict) -> list[Result]:
    """Build Result objects for every feature in a doc (browse mode, no score)."""
    url = doc.get("video_url", "")
    out: list[Result] = []
    for f in doc.get("features", []):
        out.append(
            Result(
                feature=str(f.get("feature", "")),
                feature_group=str(f.get("feature_group", "")),
                how_to=str(f.get("how_to", "")),
                transcript_summary=str(f.get("transcript_summary", "")) or str(f.get("how_to", "")),
                confidence=0.0,
                start_s=int(f.get("start_s", 0)),
                end_s=int(f.get("end_s", 0)),
                video_url=str(f.get("video_url", url)),
                thumbnail=str(f.get("thumbnail", "")),
            )
        )
    return out


class SearchEngine:
    def __init__(self, features_doc: dict | None = None):
        self.doc = features_doc if features_doc is not None else data_mod.load_features()
        self.features: list[dict] = self.doc.get("features", [])
        self.video_url: str = self.doc.get("video_url", "")
        # Lazy semantic state — NOT loaded at construction time.
        self._model = None
        self._coll = None
        self._st_class = None
        self._sem_checked = False
        self._sem_ok = False
        self._sem_ready = False  # set True once the model is actually loaded

    # ------------------------------------------------------------------ #
    # semantic backend (lazy)
    # ------------------------------------------------------------------ #
    def _check_semantic(self) -> bool:
        """Cheap check: chroma index present + deps importable. Does NOT load
        the sentence-transformers model."""
        if self._sem_checked:
            return self._sem_ok
        self._sem_checked = True
        chroma_path = data_mod.chroma_dir()
        if not chroma_path.exists():
            return False
        # Lightweight: confirm the deps are *installable* without importing
        # them (importing sentence_transformers pulls in torch, ~10-30s).
        if not _have("chromadb", "sentence_transformers"):
            return False
        self._sem_ok = True
        return True

    def _ensure_model(self):
        """Load chromadb + the embedding model on first use (call from a worker
        thread — this is where the heavy torch import happens)."""
        if self._coll is None:
            import chromadb
            from sentence_transformers import SentenceTransformer

            self._coll = chromadb.PersistentClient(
                path=str(data_mod.chroma_dir())
            ).get_collection("video_segments")
            self._st_class = SentenceTransformer
        if self._model is None and self._st_class is not None:
            self._model = self._st_class(_MODEL_NAME)
        self._sem_ready = self._model is not None
        return self._sem_ready

    def preload_semantic(self) -> bool:
        """Preload the semantic model in a background thread. Returns True if
        the model is now ready. Safe to call from any thread."""
        if not self._check_semantic():
            return False
        if self._sem_ready:
            return True
        return self._ensure_model()

    @property
    def semantic_ready(self) -> bool:
        return self._sem_ready

    @property
    def backend(self) -> str:
        # Only report semantic if the model is actually loaded — otherwise
        # keyword is used for instant results.
        return "semantic" if self._sem_ready else "keyword"

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def search(self, query: str, top_k: int = 30) -> list[Result]:
        query = query.strip()
        if not query:
            return []
        # Use instant keyword search until the semantic model is loaded —
        # avoids a ~30s freeze on the first query while torch imports.
        if self._sem_ready:
            try:
                return self._semantic_search(query, top_k)
            except Exception:
                pass  # fall through to keyword
        return self._keyword_search(query, top_k)

    # ------------------------------------------------------------------ #
    # implementations
    # ------------------------------------------------------------------ #
    def _semantic_search(self, query: str, top_k: int) -> list[Result]:
        if not self._ensure_model():
            return self._keyword_search(query, top_k)
        qvec = self._model.encode([query]).tolist()
        res = self._coll.query(query_embeddings=qvec, n_results=min(top_k, len(self.features)))
        out: list[Result] = []
        ids = res.get("ids", [[]])[0]
        distances = res.get("distances", [[]])[0]
        for idx_str, dist in zip(ids, distances):
            idx = int(str(idx_str).lstrip("f")) - 1
            if idx < 0 or idx >= len(self.features):
                continue
            feat = self.features[idx]
            conf = round((1.0 - (float(dist) / 2.0)) * 100.0, 1)
            conf = max(0.0, min(100.0, conf))
            out.append(self._to_result(feat, conf))
        return out

    def _keyword_search(self, query: str, top_k: int) -> list[Result]:
        q_tokens = _tokens(query)
        if not q_tokens:
            q_tokens = _TOKEN_RE.findall(query.lower())
        q_set = set(q_tokens)
        if not q_set:
            return []

        scored: list[tuple[float, dict]] = []
        for feat in self.features:
            text = _feature_text(feat)
            text_l = text.lower()
            t_tokens = set(_tokens(text))
            hits = sum(1 for t in q_set if t in t_tokens or t in text_l)
            if hits == 0:
                continue
            name_tokens = set(_tokens(str(feat.get("feature", ""))))
            name_hits = sum(1 for t in q_set if t in name_tokens)
            coverage = hits / len(q_set)
            score = coverage * 70.0 + (name_hits / len(q_set)) * 30.0
            scored.append((min(100.0, round(score, 1)), feat))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._to_result(feat, score) for score, feat in scored[:top_k]]

    def _to_result(self, feat: dict, confidence: float) -> Result:
        return Result(
            feature=str(feat.get("feature", "")),
            feature_group=str(feat.get("feature_group", "")),
            how_to=str(feat.get("how_to", "")),
            transcript_summary=str(feat.get("transcript_summary", "")) or str(feat.get("how_to", "")),
            confidence=float(confidence),
            start_s=int(feat.get("start_s", 0)),
            end_s=int(feat.get("end_s", 0)),
            video_url=str(feat.get("video_url", self.video_url)),
            thumbnail=str(feat.get("thumbnail", "")),
        )
