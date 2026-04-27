import glob
import logging
import os

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class BugPatternRetriever:
    """TF-IDF retriever over the knowledge_base/bugs/ corpus."""

    def __init__(self, kb_dir: str = "knowledge_base/bugs"):
        self.docs: list[str] = []
        self.filenames: list[str] = []
        self._load(kb_dir)

        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        if self.docs:
            self.matrix = self.vectorizer.fit_transform(self.docs)
            logger.info(f"Retriever loaded {len(self.docs)} documents from {kb_dir}")
        else:
            self.matrix = None
            logger.warning(f"No documents found in {kb_dir}")

    def _load(self, kb_dir: str) -> None:
        pattern = os.path.join(kb_dir, "*.md")
        for path in sorted(glob.glob(pattern)):
            with open(path, encoding="utf-8") as f:
                self.docs.append(f.read())
                self.filenames.append(os.path.basename(path))

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """Return up to top_k docs ranked by cosine similarity to the query."""
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
                    }
                )

        logger.info(
            f"Retrieval for '{query[:60]}': "
            f"{[r['filename'] for r in results]}"
        )
        return results
