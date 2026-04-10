"""
Late Chunking Embedder (Ollama / nomic-embed-text)

Each chunk is embedded together with its neighbouring chunks so that the
resulting vector captures surrounding document context — a text-level
approximation of late chunking that works with any embedding API.

nomic-embed-text supports up to 8 192 tokens, so the window can be
substantially larger than what the old multilingual-e5-base allowed.

Reference: https://weaviate.io/blog/late-chunking
"""

import logging
import os
from typing import List

import requests

logger = logging.getLogger("oracle")

_DEFAULT_MODEL = "nomic-embed-text"
# Number of neighbouring chunks prepended as context for each chunk
_CONTEXT_WINDOW = 3
# Max texts per single /api/embed call (avoid OOM on large batches)
_EMBED_BATCH_SIZE = 64


class LateChunkingEmbedder:
    """
    Produces contextualised chunk embeddings by calling Ollama's /api/embed
    endpoint directly — one HTTP request per batch instead of one per chunk.

    For each chunk i, the text of the preceding _CONTEXT_WINDOW chunks is
    prepended so that the embedding captures surrounding document content.

    Usage:
        embedder = LateChunkingEmbedder()
        vectors = embedder.embed_chunks(["chunk text 1", "chunk text 2", ...])
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        base_url: str | None = None,
        context_window: int = _CONTEXT_WINDOW,
    ) -> None:
        self.model = model
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.context_window = context_window
        logger.info(
            "LateChunkingEmbedder: model '%s' via Ollama at %s (context_window=%d).",
            model, self.base_url, context_window,
        )

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Single HTTP call to Ollama /api/embed for a list of texts."""
        resp = requests.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model, "input": texts},
            timeout=300,
        )
        if not resp.ok:
            logger.error("Ollama /api/embed error %s: %s", resp.status_code, resp.text[:500])
        resp.raise_for_status()
        return resp.json()["embeddings"]

    def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        """
        Embeds all chunks from a single document using contextual late chunking.

        Each chunk is prefixed with the text of its preceding neighbours so
        that the vector captures the broader document context.

        Args:
            chunks: List of text chunks (from the same document).

        Returns:
            List of embedding vectors in the same order as *chunks*.
        """
        if not chunks:
            return []

        contextual_texts: List[str] = []
        for i, chunk in enumerate(chunks):
            start = max(0, i - self.context_window)
            context_parts = chunks[start:i]
            if context_parts:
                context = " ".join(context_parts)
                contextual_texts.append(f"Context: {context}\n\nChunk: {chunk}")
            else:
                contextual_texts.append(chunk)

        # Send in batches to avoid overwhelming Ollama with huge payloads
        all_vectors: List[List[float]] = []
        for i in range(0, len(contextual_texts), _EMBED_BATCH_SIZE):
            batch = contextual_texts[i: i + _EMBED_BATCH_SIZE]
            logger.debug(
                "Embedding batch %d-%d / %d",
                i + 1, i + len(batch), len(contextual_texts),
            )
            all_vectors.extend(self._embed_batch(batch))

        return all_vectors
