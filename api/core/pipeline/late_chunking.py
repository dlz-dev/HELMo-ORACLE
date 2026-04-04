"""
Late Chunking Embedder

Instead of embedding each chunk in isolation, the full document (or a
rolling window of consecutive chunks) is processed in a single forward
pass, and each chunk's embedding is obtained by mean-pooling the token
representations that correspond to it in the shared sequence.

Reference: https://weaviate.io/blog/late-chunking
"""

import logging
from typing import List, Optional

import torch
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger("oracle")

_DEFAULT_MODEL = "intfloat/multilingual-e5-base"
_MAX_SEQ_LEN = 512  # hard limit for the model


class LateChunkingEmbedder:
    """
    Produces contextualized chunk embeddings using late chunking.

    Usage:
        embedder = LateChunkingEmbedder()
        vectors = embedder.embed_chunks(["chunk text 1", "chunk text 2", ...])
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()
        logger.info("LateChunkingEmbedder: model '%s' loaded.", model_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _embed_window(self, window_texts: List[str]) -> List[List[float]]:
        """
        Single forward pass over a window of consecutive chunk texts.

        The chunks are concatenated into one sequence. Each chunk's
        embedding is the mean of its corresponding token representations,
        normalized to unit length.

        Args:
            window_texts: Chunk texts that together fit within _MAX_SEQ_LEN.

        Returns:
            One embedding vector per chunk (same order).
        """
        # 1. Build full window string + track character spans per chunk
        full_text = ""
        char_spans: List[tuple] = []
        for text in window_texts:
            start = len(full_text)
            full_text += text
            char_spans.append((start, len(full_text)))
            full_text += " "  # lightweight separator

        # 2. Tokenize with offset mapping
        enc = self.tokenizer(
            full_text,
            return_tensors="pt",
            return_offsets_mapping=True,
            truncation=True,
            max_length=_MAX_SEQ_LEN,
        )
        offset_mapping = enc.pop("offset_mapping")[0].tolist()  # list[(start, end)]

        # 3. Forward pass — single call for the whole window
        with torch.no_grad():
            outputs = self.model(**enc)

        token_embs = outputs.last_hidden_state[0]  # (seq_len, hidden_size)

        # 4. Mean-pool token embeddings per chunk span
        embeddings: List[List[float]] = []
        for c_start, c_end in char_spans:
            indices = [
                i
                for i, (t_start, t_end) in enumerate(offset_mapping)
                if t_start != t_end and t_end > c_start and t_start < c_end
            ]

            if indices:
                emb = token_embs[indices].mean(dim=0)
            else:
                # Fallback: mean over the entire window (should not happen)
                emb = token_embs.mean(dim=0)

            emb = emb / (emb.norm() + 1e-8)
            embeddings.append(emb.detach().tolist())

        return embeddings

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        """
        Embeds all chunks from a single document using late chunking.

        Consecutive chunks are grouped into windows that fit within the
        model's max sequence length. All chunks inside the same window
        share attention context during the forward pass.

        Args:
            chunks: List of text chunks (from the same document).

        Returns:
            List of embedding vectors in the same order as *chunks*.
        """
        if not chunks:
            return []

        # Pre-tokenize each chunk (without special tokens) to measure their length
        token_counts = [
            len(self.tokenizer.encode(c, add_special_tokens=False))
            for c in chunks
        ]

        embeddings: List[Optional[List[float]]] = [None] * len(chunks)

        i = 0
        while i < len(chunks):
            # Budget: _MAX_SEQ_LEN minus 2 special tokens ([CLS] / [SEP])
            budget = _MAX_SEQ_LEN - 2
            window_indices: List[int] = []
            used = 0

            j = i
            while j < len(chunks):
                # +1 accounts for the space separator between chunks
                needed = token_counts[j] + (1 if window_indices else 0)
                if used + needed > budget and window_indices:
                    break
                window_indices.append(j)
                used += needed
                j += 1

            window_texts = [chunks[k] for k in window_indices]
            window_embs = self._embed_window(window_texts)

            for idx, emb in zip(window_indices, window_embs):
                embeddings[idx] = emb

            i = j

        return embeddings  # type: ignore[return-value]
