import glob
import logging
import os

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

DEFAULT_KB_DIRS = [
    "knowledge_base/bugs",
    "knowledge_base/patterns",
]


class BugPatternRetriever:
    """
    Multi-source TF-IDF retriever over the knowledge_base/ corpus.

    Loads markdown documents from one or more directories, builds a
    combined TF-IDF matrix, and returns top-k results ranked by cosine
    similarity. Each result is tagged with its source directory so the
    caller knows which corpus produced it.
    """

    def __init__(self, kb_dirs: list[str] | None = None):
        self.kb_dirs = kb_dirs if kb_dirs is not None else DEFAULT_KB_DIRS
        self.docs: list[str] = []
        self.filenames: list[str] = []
        self.sources: list[str] = []  # which kb_dir each doc came from

        for kb_dir in self.kb_dirs:
            self._load(kb_dir)

        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        if self.docs:
            self.matrix = self.vectorizer.fit_transform(self.docs)
            logger.info(
                "Retriever loaded %d documents from %d source(s): %s",
                len(self.docs),
                len(self.kb_dirs),
                self.kb_dirs,
            )
        else:
            self.matrix = None
            logger.warning("No documents found in any of: %s", self.kb_dirs)

    def _load(self, kb_dir: str) -> None:
        pattern = os.path.join(kb_dir, "*.md")
        for path in sorted(glob.glob(pattern)):
            with open(path, encoding="utf-8") as f:
                self.docs.append(f.read())
                self.filenames.append(os.path.basename(path))
                self.sources.append(os.path.basename(kb_dir))

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Return up to top_k docs ranked by cosine similarity to the query.

        Each result dict contains:
            filename : str   — e.g. "state_reset.md"
            content  : str   — full document text
            score    : float — cosine similarity score
            source   : str   — which corpus directory ("bugs" or "patterns")
        """
        if not self.docs or self.matrix is None:
            logger.warning("Retriever has no documents — returning empty results.")
            return []

        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self.matrix).flatten()
        ranked = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in ranked:
            if scores[idx] > 0.0:
                results.append(
                    {
                        "filename": self.filenames[idx],
                        "content": self.docs[idx],
                        "score": float(scores[idx]),
                        "source": self.sources[idx],
                    }
                )

        logger.info(
            "Retrieval for '%s': %s",
            query[:60],
            [(r["filename"], r["source"], round(r["score"], 3)) for r in results],
        )
        return results
