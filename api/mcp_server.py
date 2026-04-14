"""
HELMo Oracle — Serveur MCP (Model Context Protocol).

Expose le pipeline RAG comme un serveur MCP standard monté dans FastAPI.
Accessible via : https://api.dlzteam.com/mcp
"""

import os
from typing import Optional, List, Any

from mcp.server.fastmcp import FastMCP

from core.agent.tools_oracle import CONFIDENCE_THRESHOLD_HIGH, CONFIDENCE_THRESHOLD_MEDIUM

# Instance MCP
mcp = FastMCP(
    "helmo-oracle",
    instructions=(
        "Tu es connecté aux Archives Sacrées de HELMo Oracle. "
        "Utilise search_knowledge_base pour interroger la base de connaissances Dofus, "
        "et list_sources pour voir les documents disponibles."
    ),
)

# Références partagées (injectées par api.py au démarrage)
_vm: Optional[Any] = None
_redis: Optional[Any] = None


def setup(vm: Any, redis: Optional[Any] = None) -> None:
    """Injecte les dépendances requises pour l'exécution des outils."""
    global _vm, _redis
    _vm = vm
    _redis = redis


def _log_query(query: str) -> None:
    """Enregistre la requête dans Redis à des fins d'analytique."""
    if _redis is None:
        return

    try:
        _redis.xadd(
            "oracle:events",
            {
                "type": "chat",
                "question": query[:120],
                "provider": "groq",
                "model": "discord-bot",
                "latency_ms": "0",
                "source": "discord"
            },
            maxlen=500,
        )
    except Exception as e:
        print(f"Erreur logging Redis : {e}")


# Outil 1 : Recherche hybride
@mcp.tool()
def search_knowledge_base(query: str, k: int = 5) -> str:
    """
    Recherche dans les archives via une approche hybride (cosine + BM25 + RRF).
    """
    if _vm is None:
        return "Erreur : VectorManager non initialisé."

    clean_query = query.strip()[:500]
    if not clean_query:
        return "Requête vide."

    _log_query(clean_query)

    query_vector = _vm.embeddings_model.embed_query(clean_query)
    results = _vm.search_hybrid(query=clean_query, query_vector=query_vector, k_final=k)

    if not results:
        return "Aucun document trouvé pour cette requête."

    formatted_results: List[str] = []
    for content, rrf_score, metadata in results:
        source = metadata.get("source", "Source inconnue")

        if rrf_score >= CONFIDENCE_THRESHOLD_HIGH:
            confidence = "🟢 HIGH"
        elif rrf_score >= CONFIDENCE_THRESHOLD_MEDIUM:
            confidence = "🟡 MEDIUM"
        else:
            confidence = "🔴 LOW"

        formatted_results.append(
            f"[Source: {source}] [{confidence}] [Score RRF: {rrf_score:.4f}]\n{content}"
        )

    return "\n\n---\n\n".join(formatted_results)


# Outil 2 : Liste des sources
@mcp.tool()
def list_sources() -> str:
    """
    Liste les documents ingérés dans la base de connaissances.
    """
    if _vm is None:
        return "Erreur : VectorManager non initialisé."

    sources = _vm.list_sources()
    if not sources:
        return "Aucune source disponible dans la base."

    lines: List[str] = [f"📚 {len(sources)} source(s) disponible(s) :\n"]
    lines.extend([
        f"• {s.get('source', 'Inconnue')} — {s.get('chunk_count', 0)} chunks — ingéré le {s.get('ingested_at', 'N/A')}"
        for s in sources
    ])

    return "\n".join(lines)


# Lancement standalone (test local)
if __name__ == "__main__":
    from langchain_community.embeddings import OllamaEmbeddings
    from core.database.vector_manager import VectorManager

    _embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    )

    setup(VectorManager(embeddings_model=_embeddings))
    mcp.run()
