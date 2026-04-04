"""
Manages vector operations and hybrid search against the PostgreSQL/Supabase database.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from core.utils.utils import FTS_LANG, K_BM25, K_FINAL, K_SEMANTIC, RRF_K, load_config
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pgvector.psycopg import register_vector
from psycopg import sql

# Get the logger instance configured in logger.py
logger = logging.getLogger("oracle")


class VectorManager:
    """Handles connections to PostgreSQL/Supabase and manages hybrid search execution."""

    def __init__(self, embeddings_model: Any = None) -> None:
        """Initializes database connection and embedding model."""
        config = load_config()
        db_config = config.get("database", {})
        self.conn = None
        self.db_available = False

        try:
            conn_string = db_config.get("connection_string")
            if not conn_string:
                raise ValueError("DATABASE_URL (connection_string) is not set in the configuration.")

            self._conn_string = conn_string
            self.conn = psycopg.connect(conn_string, autocommit=True)
            register_vector(self.conn)

            # Test connection
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")

            self.db_available = True
            logger.info("VectorManager: Database connection successful.")

        except (psycopg.Error, ValueError) as e:
            # Log the specific connection error
            logger.error(f"VectorManager: Failed to connect to the database. Error: {e}", exc_info=True)
            if self.conn:
                self.conn.close()
            self.conn = None
            self.db_available = False
            self._conn_string = db_config.get("connection_string", "")

        self.embeddings_model = embeddings_model or HuggingFaceEmbedding(
            model_name="intfloat/multilingual-e5-base"
        )
        # Lazy import to avoid circular dependency (core.pipeline.__init__
        # imports ingestion, which imports VectorManager).
        from core.pipeline.late_chunking import LateChunkingEmbedder
        self.late_chunking_embedder = LateChunkingEmbedder()

    def _reconnect(self) -> bool:
        """Attempts to re-establish the database connection."""
        try:
            if self.conn and not self.conn.closed:
                try:
                    self.conn.close()
                except Exception:
                    pass
            conn_string = getattr(self, "_conn_string", None)
            if not conn_string:
                return False
            self.conn = psycopg.connect(conn_string, autocommit=True, connect_timeout=10)
            register_vector(self.conn)
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
            self.db_available = True
            logger.info("VectorManager: Reconnected to database successfully.")
            return True
        except Exception as e:
            logger.error(f"VectorManager: Reconnect failed. Error: {e}")
            self.conn = None
            self.db_available = False
            return False

    def is_db_available(self) -> bool:
        """Checks if the database connection is active, attempting a reconnect if needed."""
        if not self.db_available or self.conn is None or self.conn.closed:
            return self._reconnect()
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            logger.warning("VectorManager: Connection lost, attempting reconnect...")
            return self._reconnect()

    def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Generates an embedding and saves the text with metadata and ingestion timestamp.
        Returns True if the chunk was inserted, False if it already exists (duplicate).
        """
        if not self.is_db_available():
            raise ConnectionError("Database is not available.")

        chunk_hash = hashlib.sha256(text.encode()).hexdigest()
        metadata = metadata or {}
        text_to_embed = text

        if "global_context" in metadata:
            text_to_embed = f"Global Context: {metadata['global_context']}\n\nContent: {text}"
        elif "Header 1" in metadata:
            text_to_embed = f"Chapter: {metadata['Header 1']}\n\nContent: {text}"
        elif "category" in metadata and "item_name" in metadata:
            text_to_embed = f"Category: {metadata['category']} | Item: {metadata['item_name']}\n\nContent: {text}"

        vector = self.embeddings_model.get_text_embedding(text_to_embed)
        ingested_at = datetime.now(timezone.utc)

        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO documents (content, vecteur, metadata, ingested_at, chunk_hash)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (chunk_hash) WHERE (chunk_hash IS NOT NULL) DO NOTHING""",
                (text, vector, json.dumps(metadata), ingested_at, chunk_hash),
            )
            return cur.rowcount == 1

    def add_documents_batch(
            self,
            chunks: List[Tuple[str, Optional[Dict[str, Any]]]],
            use_late_chunking: bool = True,
    ) -> int:
        """
        Inserts a batch of chunks from the same document.

        When *use_late_chunking* is True (default), all chunk texts are
        embedded in context using the LateChunkingEmbedder so that each
        vector captures the surrounding document content.

        Args:
            chunks: List of (text, metadata) pairs from the same document.
            use_late_chunking: Use late chunking embedder instead of per-chunk embedding.

        Returns:
            Number of chunks actually inserted (duplicates are skipped).
        """
        if not chunks:
            return 0
        if not self.is_db_available():
            raise ConnectionError("Database is not available.")

        texts = [text for text, _ in chunks]

        if use_late_chunking and self.late_chunking_embedder is not None:
            vectors = self.late_chunking_embedder.embed_chunks(texts)
        else:
            vectors = [self.embeddings_model.get_text_embedding(t) for t in texts]

        inserted = 0
        ingested_at = datetime.now(timezone.utc)

        with self.conn.cursor() as cur:
            for (text, metadata), vector in zip(chunks, vectors):
                metadata = metadata or {}
                chunk_hash = hashlib.sha256(text.encode()).hexdigest()
                cur.execute(
                    """INSERT INTO documents (content, vecteur, metadata, ingested_at, chunk_hash)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (chunk_hash) WHERE (chunk_hash IS NOT NULL) DO NOTHING""",
                    (text, vector, json.dumps(metadata), ingested_at, chunk_hash),
                )
                inserted += cur.rowcount

        return inserted

    def search_semantic(
            self, query_vector: List[float], k: int = K_SEMANTIC
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Executes cosine similarity search (<=>).
        """
        if not self.is_db_available():
            return []

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT content, vecteur <=> %s::vector AS distance, metadata
                FROM documents
                ORDER BY distance
                    LIMIT %s
                """,
                (query_vector, k),
            )
            return cur.fetchall()

    def search_bm25(self, query: str, k: int = K_BM25) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Executes PostgreSQL Full-Text Search for exact keyword matches.
        """
        if not self.is_db_available():
            return []

        try:
            with self.conn.cursor() as cur:
                query_sql = sql.SQL(
                    """
                    SELECT content,
                           ts_rank(fts_vector, plainto_tsquery({lang}, %s)) AS rank,
                           metadata
                    FROM documents
                    WHERE fts_vector @@ plainto_tsquery({lang}
                        , %s)
                    ORDER BY rank DESC
                        LIMIT %s
                    """
                ).format(lang=sql.Literal(FTS_LANG))

                cur.execute(query_sql, (query, query, k))
                return cur.fetchall()
        except Exception as e:
            logger.warning(f"BM25 search failed: {e}")
            return []

    def search_hybrid(
            self, query: str, query_vector: List[float], k_final: int = K_FINAL
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Combines semantic and BM25 searches using Reciprocal Rank Fusion.
        """
        if not self.is_db_available():
            return []

        semantic_results = self.search_semantic(query_vector, k=K_SEMANTIC)
        bm25_results = self.search_bm25(query, k=K_BM25)

        rrf_scores: Dict[str, float] = {}
        doc_store: Dict[str, Tuple[str, float, Dict[str, Any]]] = {}

        for rank, (content, score, metadata) in enumerate(semantic_results):
            rrf_scores[content] = rrf_scores.get(content, 0.0) + 1.0 / (RRF_K + rank + 1)
            doc_store[content] = (content, score, metadata)

        for rank, (content, score, metadata) in enumerate(bm25_results):
            rrf_scores[content] = rrf_scores.get(content, 0.0) + 1.0 / (RRF_K + rank + 1)
            doc_store[content] = (content, score, metadata)

        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        return [
            (doc_store[content][0], rrf_score, doc_store[content][2])
            for content, rrf_score in sorted_docs[:k_final]
        ]

    def list_sources(self) -> List[Dict[str, Any]]:
        """
        Aggregates database entries to return unique source files.
        """
        if not self.is_db_available():
            return []

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT metadata ->>'source' AS source, COUNT (*) AS chunk_count, MAX (metadata->>'global_context') AS global_context, MAX (ingested_at) AS ingested_at
                    FROM documents
                    WHERE metadata->>'source' IS NOT NULL
                    GROUP BY metadata->>'source'
                    ORDER BY MAX (ingested_at) DESC NULLS LAST
                    """
                )
                rows = cur.fetchall()
                return [
                    {
                        "source": r[0],
                        "chunk_count": r[1],
                        "global_context": r[2] or "Aucun contexte global disponible.",
                        "ingested_at": r[3].strftime("%Y-%m-%d %H:%M UTC") if r[3] else "—",
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.warning(f"list_sources failed: {e}")
            return []

    def search_similar(
            self, query_vector: List[float], k: int = K_FINAL
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Alias for search_semantic() — kept for backward compatibility."""
        return self.search_semantic(query_vector, k)
