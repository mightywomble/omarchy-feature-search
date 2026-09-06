"""Search the feature index.

Two backends:

* **semantic** — ChromaDB + sentence-transformers, when the optional deps and a
  built vector index are present. Confidence = cosine-similarity percentage.
* **keyword** — always-available fallback scoring token overlap against the
  feature/how-to/transcript text. Confidence = normalised token-coverage %.

Both return a list of :class:`Result` with a 0–100 ``confidence``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from omarchy_feature_search import data as data_mod

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


class SearchEngine:
    def __init__(self, features_doc: dict | None = None):
        self.doc = features_doc if features_doc is not None else data_mod.load_features()
        self.features: list[dict] = self.doc.get("features", [])
        self.video_url: str = self.doc.get("video_url", "")
        self._semantic = self._try_semantic()

    # ------------------------------------------------------------------ #
    # semantic backend
    # ------------------------------------------------------------------ #
    def _try_semantic(self):
        chroma_path = data_mod.chroma_dir()
        if not chroma_path.exists():
            return None
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return None
        try:
            client = chromadb.PersistentClient(path=str(chroma_path))
            coll = client.get_collection("video_segments")
            model = SentenceTransformer(_MODEL_NAME)
        except Exception:
            return None
        return (model, coll)

    @property
    def backend(self) -> str:
        return "semantic" if self._semantic else "keyword"

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def search(self, query: str, top_k: int = 8) -> list[Result]:
        query = query.strip()
        if not query:
            return []
        if self._semantic:
            try:
                return self._semantic_search(query, top_k)
            except Exception:
                pass  # fall through to keyword
        return self._keyword_search(query, top_k)

    # ------------------------------------------------------------------ #
    # implementations
    # ------------------------------------------------------------------ #
    def _semantic_search(self, query: str, top_k: int) -> list[Result]:
        model, coll = self._semantic
        qvec = model.encode([query]).tolist()
        res = coll.query(query_embeddings=qvec, n_results=min(top_k, len(self.features)))
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
            # coverage of query terms, boosted for matches in the feature name
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
