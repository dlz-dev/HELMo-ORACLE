"""
LangGraph tool — searches the knowledge base and exposes raw results
with RRF confidence scores for Chain-of-Thought (CoT) display in the UI.

Results are stored in the cot_storage list passed to get_search_tool(), or
in the optional cot_storage list (API mode).
"""

from typing import Callable, Any, Optional

from langchain_core.tools import tool

from ..database.vector_manager import VectorManager

# RRF score thresholds for confidence classification
# Empirical values for the paraphrase-multilingual-MiniLM-L12-v2 model
CONFIDENCE_THRESHOLD_HIGH: float = 0.025
CONFIDENCE_THRESHOLD_MEDIUM: float = 0.010


def get_search_tool(vm: VectorManager, k_final: int = 5, cot_storage: Optional[list] = None) -> Callable:
    """
    Factory function returning a LangGraph tool bound to the shared VectorManager.

    Args:
        vm (VectorManager): Shared VectorManager singleton instance.
        k_final (int): Number of results to retrieve (controlled via UI).
        cot_storage (Optional[list]): If provided, CoT results are stored here (API mode).
            If None, CoT results are discarded.

    Returns:
        Callable: The initialized LangGraph tool.
    """

    @tool
    def search_knowledge_base(query: str) -> str:
        """
        Searches the Oracle's complete database for relevant information.
        Uses hybrid search (semantic cosine + BM25 keywords) fused with
        Reciprocal Rank Fusion (RRF) for maximum recall.

        Args:
            query (str): The user's search query.

        Returns:
            str: Formatted XML string containing the retrieved excerpts.
        """
        if cot_storage is not None:
            cot_storage.clear()

        # Sanitisation : tronque et nettoie la query avant injection dans le pipeline RAG
        query = query.strip()[:500]
        if not query:
            return "<archives_sacrees>\nEmpty query.\n</archives_sacrees>"

        query_vector = vm.embeddings_model.get_query_embedding(query)
        results = vm.search_hybrid(query=query, query_vector=query_vector, k_final=k_final)

        if not results:
            return "<archives_sacrees>\nNo documents found for this query.\n</archives_sacrees>"

        cot_entries: list[dict[str, Any]] = []
        context_lines: list[str] = []

        for content, rrf_score, metadata in results:
            source = metadata.get("source", "Unknown Archive")

            # Determine confidence level
            if rrf_score >= CONFIDENCE_THRESHOLD_HIGH:
                confidence = "high"
            elif rrf_score >= CONFIDENCE_THRESHOLD_MEDIUM:
                confidence = "medium"
            else:
                confidence = "low"

            cot_entries.append({
                "source": source,
                "content": content,
                "rrf_score": round(rrf_score, 4),
                "confidence": confidence,
            })
            context_lines.append(f"[Source: {source}]\nExcerpt: {content}")

        if cot_storage is not None:
            cot_storage.extend(cot_entries)

        # Use standard Python string joining instead of chr(10)
        return f"<archives_sacrees>\n{'\n'.join(context_lines)}\n</archives_sacrees>"

    return search_knowledge_base