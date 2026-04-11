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

import os as _os
if _os.environ.get("OLLAMA_BATCH", "false").lower() == "true":
    from langchain_ollama import OllamaEmbeddings
else:
    from langchain_community.embeddings import OllamaEmbeddings

logger = logging.getLogger("oracle")

_DEFAULT_MODEL = "nomic-embed-text"
# Number of neighbouring chunks prepended as context for each chunk
_CONTEXT_WINDOW = 3


class LateChunkingEmbedder:
    """
    Produces contextualised chunk embeddings using OllamaEmbeddings.

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
        resolved_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.embeddings = OllamaEmbeddings(model=model, base_url=resolved_url)
        self.context_window = context_window
        logger.info(
            "LateChunkingEmbedder: model '%s' via Ollama at %s (context_window=%d).",
            model, resolved_url, context_window,
        )

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

        MAX_CHARS = 3000
        contextual_texts: List[str] = []
        for i, chunk in enumerate(chunks):
            start = max(0, i - self.context_window)
            context_parts = chunks[start:i]
            if context_parts:
                context = " ".join(context_parts)
                text = f"Context: {context}\n\nChunk: {chunk}"
            else:
                text = chunk
            contextual_texts.append(text[:MAX_CHARS])

        return self.embeddings.embed_documents(contextual_texts)
