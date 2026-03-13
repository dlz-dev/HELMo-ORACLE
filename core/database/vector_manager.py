"""
Manages vector operations and hybrid search against a PostgreSQL/Supabase database.

Search strategy:
  - Semantic search: Cosine distance (<=>) for conceptually similar content.
  - BM25 / FTS: PostgreSQL tsvector for exact keyword matches.
  - Hybrid fusion: Reciprocal Rank Fusion (RRF) to optimally merge both result lists.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pgvector.psycopg import register_vector

from core.utils.utils import _load_config

# Load configuration once at module level
config = _load_config()

_SEARCH_CFG: Dict[str, Any] = config.get("search", {})
_K_SEMANTIC: int = _SEARCH_CFG.get("k_semantic", 10)
_K_BM25: int = _SEARCH_CFG.get("k_bm25", 10)
_K_FINAL: int = _SEARCH_CFG.get("k_final", 5)
_RRF_K: int = _SEARCH_CFG.get("rrf_k", 60)
_FTS_LANG: str = _SEARCH_CFG.get("fts_language", "french")


class VectorManager:
    """
    Handles connections to PostgreSQL/Supabase and manages hybrid search operations.

    Attributes:
        conn (psycopg.Connection): The database connection.
        embeddings_model (Any): The model used to generate text embeddings.
    """

    def __init__(self, embeddings_model: Optional[Any] = None) -> None:
        """
        Initializes the VectorManager, establishes the database connection, 
        and sets up the embedding model.

        Args:
            embeddings_model (Optional[Any]): An externally shared embedding model 
                instance to avoid duplicate instantiation. Defaults to None.
        """
        db_config = config.get("database", {})
        
        if "connection_string" in db_config:
            self.conn = psycopg.connect(
                db_config["connection_string"],
                autocommit=True,
            )
        else:
            self.conn = psycopg.connect(
                host=db_config.get("host"),
                dbname=db_config.get("dbname"),
                user=db_config.get("user"),
                password=db_config.get("password"),
                port=int(db_config.get("port", 5432)),
                sslmode="require",
                autocommit=True,
            )

        register_vector(self.conn)

        if embeddings_model is not None:
            self.embeddings_model = embeddings_model
        else:
            self.embeddings_model = HuggingFaceEmbedding(
                model_name="intfloat/multilingual-e5-base"
            )

    def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Generates an embedding and saves the text with metadata and ingestion timestamp.

        Args:
            text (str): The document content to store and embed.
            metadata (Optional[Dict[str, Any]]): Associated metadata for the document.
        """
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
                """
                INSERT INTO documents (content, vecteur, metadata, ingested_at) 
                VALUES (%s, %s, %s, %s)
                """,
                (text, vector, json.dumps(metadata), ingested_at),
            )

    def search_semantic(self, query_vector: List[float], k: int = _K_SEMANTIC) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Performs a cosine similarity search to find semantically related content.

        Args:
            query_vector (List[float]): The embedded representation of the query.
            k (int): The number of results to return.

        Returns:
            List[Tuple[str, float, Dict[str, Any]]]: A list containing the content, 
            cosine distance score, and metadata. Lower scores indicate higher similarity.
        """
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

    def search_bm25(self, query: str, k: int = _K_BM25) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Performs a PostgreSQL Full-Text Search for exact keyword matches.

        Args:
            query (str): The raw text query.
            k (int): The number of results to return.

        Returns:
            List[Tuple[str, float, Dict[str, Any]]]: A list containing the content, 
            rank score, and metadata.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT content,
                           ts_rank(fts_vector, plainto_tsquery('{_FTS_LANG}', %s)) AS rank,
                           metadata
                    FROM documents
                    WHERE fts_vector @@ plainto_tsquery('{_FTS_LANG}', %s)
                    ORDER BY rank DESC
                    LIMIT %s
                    """,
                    (query, query, k),
                )
                return cur.fetchall()
        except Exception as e:
            print(f"⚠️ BM25 unavailable ({e}) — semantic-only fallback active")
            return []

    def search_hybrid(self, query: str, query_vector: List[float], k_final: int = _K_FINAL) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Executes a hybrid search fusing semantic and BM25 results via Reciprocal Rank Fusion.

        Args:
            query (str): The raw text query for BM25.
            query_vector (List[float]): The embedded representation of the query.
            k_final (int): The final number of fused results to return.

        Returns:
            List[Tuple[str, float, Dict[str, Any]]]: The fused and sorted search results.
        """
        semantic_results = self.search_semantic(query_vector, k=_K_SEMANTIC)
        bm25_results = self.search_bm25(query, k=_K_BM25)

        rrf_scores: Dict[str, float] = {}
        doc_store: Dict[str, Tuple[str, float, Dict[str, Any]]] = {}

        for rank, (content, score, metadata) in enumerate(semantic_results):
            rrf_scores[content] = rrf_scores.get(content, 0.0) + 1.0 / (_RRF_K + rank + 1)
            doc_store[content] = (content, score, metadata)

        for rank, (content, score, metadata) in enumerate(bm25_results):
            rrf_scores[content] = rrf_scores.get(content, 0.0) + 1.0 / (_RRF_K + rank + 1)
            doc_store[content] = (content, score, metadata)

        sorted_docs = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)

        return [
            (doc_store[content][0], rrf_score, doc_store[content][2])
            for content, rrf_score in sorted_docs[:k_final]
        ]

    def list_sources(self) -> List[Dict[str, Any]]:
        """
        Retrieves a summary of unique source files stored in the database.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries detailing the source file, 
            chunk count, global context, and ingestion timestamp.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT metadata ->>'source' AS source, 
                           COUNT(*) AS chunk_count, 
                           MAX(metadata->>'global_context') AS global_context, 
                           MAX(ingested_at) AS ingested_at
                    FROM documents
                    WHERE metadata->>'source' IS NOT NULL
                    GROUP BY metadata->>'source'
                    ORDER BY MAX(ingested_at) DESC NULLS LAST
                    """
                )
                rows = cur.fetchall()
                
                return [
                    {
                        "source": row[0],
                        "chunk_count": row[1],
                        "global_context": row[2] or "Aucun contexte global disponible.",
                        "ingested_at": row[3].strftime("%Y-%m-%d %H:%M UTC") if row[3] else "—",
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"⚠️ list_sources failed: {e}")
            return []

    def search_similar(self, query_vector: List[float], k: int = _K_FINAL) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Alias for search_semantic(), kept for backward compatibility.
        """
        return self.search_semantic(query_vector, k)