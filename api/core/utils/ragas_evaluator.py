"""
RAGAS-based evaluation module for HELMo Oracle RAG pipeline.

Evaluates RAG quality without requiring ground-truth answers using three
reference-free metrics:
  - Faithfulness        : Is the answer grounded in the retrieved chunks?
  - Answer Relevancy    : Does the answer actually address the question?
  - Context Precision   : Are the retrieved chunks relevant to the question?

Notes:
    - RAGAS >= 0.2 uses LangChain LLMs as judges — no OpenAI key required
      as long as you supply a compatible LangChain chat model.
    - Evaluation is run synchronously (ragas.evaluate is sync).
    - Scores range from 0.0 to 1.0. A combined score is also returned.
    - Embeddings use the same model as the main pipeline (intfloat/multilingual-e5-base)
      via a LangChain-compatible wrapper to ensure consistency.
"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("oracle")

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

# ---------------------------------------------------------------------------
# LLM judge factory
# ---------------------------------------------------------------------------

def _get_judge_llm(provider: str, model: str, config: Optional[Dict[str, Any]] = None):
    """
    Returns a LangChain chat model to use as the RAGAS judge LLM.
    Supports groq, openai, anthropic, gemini — mirrors providers.py logic.

    Args:
        provider: LLM provider key (groq, openai, anthropic, gemini).
        model: Model name/identifier.
        config: Optional config dict (same format as load_config()).

    Returns:
        LangChain BaseChatModel instance.

    Raises:
        ValueError: If the provider is unsupported or the API key is missing.
    """
    import os

    api_key = ""

    # Try to pull the API key from config first, then env
    if config:
        api_key = config.get("llm", {}).get(provider, {}).get("api_key", "")

    if provider == "groq":
        api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set.")
        from langchain_groq import ChatGroq
        return ChatGroq(api_key=api_key, model=model, temperature=0)

    elif provider == "openai":
        api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(api_key=api_key, model=model, temperature=0)

    elif provider == "anthropic":
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(api_key=api_key, model=model, temperature=0)

    elif provider == "gemini":
        api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set.")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(api_key=api_key, model=model, temperature=0)

    else:
        raise ValueError(f"Unsupported RAGAS judge provider: '{provider}'")


def _get_judge_embeddings(
    provider: str,
    config: Optional[Dict[str, Any]] = None,
    shared_embeddings=None,
):
    """
    Returns a LangChain-compatible embeddings model for Answer Relevancy.

    Uses the same model as the main pipeline (intfloat/multilingual-e5-base)
    wrapped in a LangChain adapter for consistency with the retrieval index.

    If a shared HuggingFaceEmbedding instance from api.py is passed in via
    ``shared_embeddings``, it is wrapped directly — no second model load.
    Otherwise, a fresh LangChain HuggingFaceEmbeddings instance is created.

    Args:
        provider:           LLM provider key (unused, kept for API symmetry).
        config:             Optional config dict.
        shared_embeddings:  Optional llama_index HuggingFaceEmbedding singleton
                            already loaded in api.py (_embeddings).

    Returns:
        LangChain Embeddings instance.
    """
    MODEL_NAME = "intfloat/multilingual-e5-base"

    # ── Fast path: wrap the already-loaded llama-index model ──────────────
    if shared_embeddings is not None:
        from langchain_core.embeddings import Embeddings

        class _LlamaIndexEmbeddingsAdapter(Embeddings):
            """
            Thin adapter so RAGAS can use the llama-index HuggingFaceEmbedding
            that is already loaded in api.py without loading a second copy.
            """
            def __init__(self, model):
                self._model = model

            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                return [self._model.get_text_embedding(t) for t in texts]

            def embed_query(self, text: str) -> List[float]:
                return self._model.get_query_embedding(text)

        logger.debug("[RAGAS] Using shared llama-index embeddings adapter (%s)", MODEL_NAME)
        return _LlamaIndexEmbeddingsAdapter(shared_embeddings)

    # ── Slow path: load a standalone LangChain HuggingFaceEmbeddings ──────
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        logger.debug("[RAGAS] Loading standalone LangChain HuggingFaceEmbeddings (%s)", MODEL_NAME)
        return HuggingFaceEmbeddings(model_name=MODEL_NAME)
    except ImportError:
        pass

    # ── Fallback: community package ────────────────────────────────────────
    from langchain_community.embeddings import HuggingFaceEmbeddings as _HFE
    logger.warning(
        "[RAGAS] langchain_huggingface not installed — falling back to "
        "langchain_community.embeddings.HuggingFaceEmbeddings (%s)",
        MODEL_NAME,
    )
    return _HFE(model_name=MODEL_NAME)


# ---------------------------------------------------------------------------
# Core evaluation function
# ---------------------------------------------------------------------------

def evaluate_rag_response(
    question: str,
    answer: str,
    cot_storage: List[Dict[str, Any]],
    provider: str = "groq",
    model: str = "llama-3.3-70b-versatile",
    config: Optional[Dict[str, Any]] = None,
    shared_embeddings=None,
) -> Dict[str, Any]:
    """
    Evaluates a single RAG response using RAGAS reference-free metrics.

    Args:
        question:           The user's original question (after PII masking).
        answer:             The LLM's generated response text.
        cot_storage:        The cot_storage list returned by _run_agent — list of
                            dicts with keys: 'content', 'source', 'rrf_score',
                            'confidence'.
        provider:           LLM provider to use as judge (default: groq).
        model:              LLM model name to use as judge.
        config:             Optional config dict from load_config().
        shared_embeddings:  Optional llama-index HuggingFaceEmbedding singleton
                            from api.py. When supplied, avoids loading a second
                            copy of the model (saves ~500 MB RAM).

    Returns:
        Dict with keys:
            - faithfulness (float | None)
            - answer_relevancy (float | None)
            - context_precision (float | None)
            - combined_score (float | None)   — unweighted average of available scores
            - num_contexts (int)
            - duration_seconds (float)
            - error (str | None)              — set if evaluation failed
    """
    start = time.time()
    base_result: Dict[str, Any] = {
        "faithfulness": None,
        "answer_relevancy": None,
        "context_precision": None,
        "combined_score": None,
        "num_contexts": len(cot_storage),
        "duration_seconds": 0.0,
        "error": None,
    }

    if not cot_storage:
        base_result["error"] = "no contexts available (cot_storage is empty)"
        base_result["duration_seconds"] = round(time.time() - start, 3)
        return base_result

    # Extract plain text from cot_storage entries
    contexts: List[str] = [entry["content"] for entry in cot_storage if entry.get("content")]

    if not contexts:
        base_result["error"] = "cot_storage entries have no 'content' field"
        base_result["duration_seconds"] = round(time.time() - start, 3)
        return base_result

    try:
        judge_llm = _get_judge_llm(provider, model, config)
        judge_embeddings = _get_judge_embeddings(provider, config, shared_embeddings)
    except (ValueError, ImportError) as e:
        base_result["error"] = f"Failed to initialize judge LLM: {e}"
        base_result["duration_seconds"] = round(time.time() - start, 3)
        return base_result

    # Build RAGAS Dataset (one sample)
    dataset = Dataset.from_dict({
        "question":  [question],
        "answer":    [answer],
        "contexts":  [contexts],
        # 'ground_truth' is intentionally omitted — we use reference-free metrics
    })

    # Configure RAGAS metrics to use our judge LLM instead of the default (OpenAI)
    # RAGAS >= 0.2 exposes .llm and .embeddings attributes on each metric
    metrics = [faithfulness, answer_relevancy, context_precision]
    for metric in metrics:
        metric.llm = judge_llm
        if hasattr(metric, "embeddings"):
            metric.embeddings = judge_embeddings

    try:
        logger.info(
            f"[RAGAS] Starting evaluation — provider={provider} model={model} "
            f"contexts={len(contexts)}"
        )
        result = evaluate(dataset=dataset, metrics=metrics)
        scores_df = result.to_pandas()
        row = scores_df.iloc[0]

        faith = float(row.get("faithfulness", float("nan")))
        rel   = float(row.get("answer_relevancy", float("nan")))
        prec  = float(row.get("context_precision", float("nan")))

        # Replace NaN with None for clean JSON serialization
        import math
        faith = None if math.isnan(faith) else round(faith, 4)
        rel   = None if math.isnan(rel)   else round(rel, 4)
        prec  = None if math.isnan(prec)  else round(prec, 4)

        available = [s for s in [faith, rel, prec] if s is not None]
        combined  = round(sum(available) / len(available), 4) if available else None

        base_result.update({
            "faithfulness":       faith,
            "answer_relevancy":   rel,
            "context_precision":  prec,
            "combined_score":     combined,
        })
        logger.info(
            f"[RAGAS] Scores — faithfulness={faith} relevancy={rel} "
            f"precision={prec} combined={combined}"
        )

    except Exception as e:
        logger.error(f"[RAGAS] Evaluation failed: {e}", exc_info=True)
        base_result["error"] = str(e)

    base_result["duration_seconds"] = round(time.time() - start, 3)
    return base_result