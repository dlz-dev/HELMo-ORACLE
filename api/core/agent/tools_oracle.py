from typing import Callable, Any

from langchain_core.tools import tool

from core.database.vector_manager import VectorManager

StepCallback = Callable[[str], None] | None

# RRF score thresholds for confidence classification
# Empirical values specific to the paraphrase-multilingual-MiniLM-L12-v2 model
CONFIDENCE_THRESHOLD_HIGH: float = 0.025
CONFIDENCE_THRESHOLD_MEDIUM: float = 0.010


def get_search_tool(
        vm: VectorManager,
        k_final: int = 5,
        cot_storage: list[dict[str, Any]] | None = None,
        step_callback: StepCallback = None
) -> Callable[[str], str]:
    """
    Factory function returning a LangGraph tool bound to the shared VectorManager.

    Args:
        vm: Shared VectorManager singleton instance.
        k_final: Number of results to retrieve.
        cot_storage: Mutable list to store CoT metadata for the UI (API mode).
        step_callback: Optional callback to track the retrieval stages.
    """

    @tool
    def search_knowledge_base(query: str) -> str:
        """
        Searches the Oracle's complete database for relevant information.
        Uses hybrid search (semantic cosine + BM25 keywords) fused with
        Reciprocal Rank Fusion (RRF) for maximum recall.
        """
        if cot_storage is not None:
            cot_storage.clear()

        # Tronque la requête à 500 caractères pour prévenir les dépassements de contexte d'embedding
        query = query.strip()[:500]
        if not query:
            return "<archives_sacrees>\nEmpty query.\n</archives_sacrees>"

        if step_callback:
            step_callback("embedding")

        query_vector: list[float] = vm.embeddings_model.embed_query(query)

        if step_callback:
            step_callback("retrieval")

        results: list[tuple[str, float, dict[str, Any]]] = vm.search_hybrid(
            query=query,
            query_vector=query_vector,
            k_final=k_final
        )

        if step_callback:
            step_callback("reranking")

        if not results:
            return "<archives_sacrees>\nNo documents found for this query.\n</archives_sacrees>"

        cot_entries: list[dict[str, Any]] = []
        context_lines: list[str] = []

        for content, rrf_score, metadata in results:
            source: str = metadata.get("source", "Unknown Archive")

            if rrf_score >= CONFIDENCE_THRESHOLD_HIGH:
                confidence: str = "high"
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

        return f"<archives_sacrees>\n{'\n'.join(context_lines)}\n</archives_sacrees>"

    return search_knowledge_base
