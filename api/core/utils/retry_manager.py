"""
Retry manager for HELMo Oracle RAG pipeline.

Orchestrates up to MAX_RETRIES attempts when a RAGAS quality check determines
that the LLM response is unsatisfactory.

Retry strategy
--------------
1. Run the agent normally (_run_agent).
2. Evaluate the response with RAGAS (faithfulness + answer_relevancy).
3. If both scores are above their thresholds → return the response.
4. Otherwise, ask the LLM to *reformulate* the question from a different angle
   and repeat from step 1 (up to MAX_RETRIES additional attempts).
5. After all attempts fail → raise RetryExhaustedError so the caller can
   surface a graceful error message to the user.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("oracle")

# ---------------------------------------------------------------------------
# Configuration (read once at import time, overridable via .env)
# ---------------------------------------------------------------------------
MAX_ATTEMPTS:              int   = int(os.environ.get("RETRY_MAX_ATTEMPTS",            "3"))
FAITHFULNESS_THRESHOLD:    float = float(os.environ.get("RETRY_FAITHFULNESS_THRESHOLD", "0.5"))
RELEVANCY_THRESHOLD:       float = float(os.environ.get("RETRY_RELEVANCY_THRESHOLD",    "0.5"))
RETRY_JUDGE_PROVIDER:      str   = os.environ.get("RETRY_JUDGE_PROVIDER", "groq")
RETRY_JUDGE_MODEL:         str   = os.environ.get("RETRY_JUDGE_MODEL",    "llama-3.3-70b-versatile")

# Message shown to the user after all retries are exhausted
EXHAUSTED_USER_MESSAGE = (
    "Je n'ai pas pu trouver une réponse suffisamment fiable à votre question après plusieurs "
    "tentatives. Pourriez-vous reformuler votre question ou la préciser davantage ?"
)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------
class RetryExhaustedError(Exception):
    """Raised when all retry attempts fail the quality threshold."""
    def __init__(self, attempts: int, last_scores: Dict[str, Any]):
        self.attempts    = attempts
        self.last_scores = last_scores
        super().__init__(EXHAUSTED_USER_MESSAGE)


# ---------------------------------------------------------------------------
# Question reformulation
# ---------------------------------------------------------------------------

def _reformulate_question(original: str, attempt: int, provider: str, model: str) -> str:
    """
    Asks the LLM to rephrase the question from a different angle.

    The reformulation prompt is intentionally minimal so as not to distort
    the user's intent — it only asks for a different wording / perspective.

    Args:
        original: The question to reformulate (already PII-masked).
        attempt:  Current attempt number (1-based), used for logging.
        provider: LLM provider key.
        model:    Model name.

    Returns:
        Reformulated question string, or the original if reformulation fails.
    """
    from core.utils.ragas_evaluator import _get_judge_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    prompt_system = (
        "Tu es un assistant spécialisé dans la reformulation de questions. "
        "Ton unique rôle est de réécrire la question fournie sous un angle différent, "
        "en conservant exactement le même sens et la même intention. "
        "Ne réponds PAS à la question. Renvoie UNIQUEMENT la question reformulée, "
        "sans guillemets, sans préambule, sans explication."
    )
    prompt_user = (
        f"Reformule cette question d'une façon différente (tentative {attempt}) :\n\n"
        f"{original}"
    )

    try:
        llm           = _get_judge_llm(provider, model)
        messages      = [SystemMessage(content=prompt_system), HumanMessage(content=prompt_user)]
        result        = llm.invoke(messages)
        reformulated  = result.content.strip()

        if not reformulated or len(reformulated) < 5:
            raise ValueError("Empty reformulation returned")

        logger.info(
            f"[RETRY] Attempt {attempt} — reformulated question: "
            f"{reformulated[:120]}{'…' if len(reformulated) > 120 else ''}"
        )
        return reformulated

    except Exception as e:
        logger.warning(f"[RETRY] Reformulation failed (attempt {attempt}): {e} — using original")
        return original


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------

def _passes_quality_gate(ragas_result: Dict[str, Any]) -> bool:
    """
    Returns True if RAGAS scores meet both thresholds.

    A None score (metric failed to compute) is treated as 0.0 so that
    evaluation errors don't silently pass a bad response through.

    Args:
        ragas_result: Dict returned by evaluate_rag_response().

    Returns:
        bool
    """
    if ragas_result.get("error") and ragas_result.get("faithfulness") is None:
        # RAGAS itself failed (e.g. not installed) — let the response through
        # to avoid blocking the whole pipeline when evaluation is unavailable.
        logger.warning("[RETRY] RAGAS evaluation unavailable — skipping quality gate.")
        return True

    faith = ragas_result.get("faithfulness") or 0.0
    rel   = ragas_result.get("answer_relevancy") or 0.0

    passes = faith >= FAITHFULNESS_THRESHOLD and rel >= RELEVANCY_THRESHOLD
    logger.info(
        f"[RETRY] Quality gate — faithfulness={faith} (min {FAITHFULNESS_THRESHOLD}), "
        f"answer_relevancy={rel} (min {RELEVANCY_THRESHOLD}) → {'PASS ✓' if passes else 'FAIL ✗'}"
    )
    return passes


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_agent_with_retry(
    session:         Dict[str, Any],
    masked_message:  str,
    provider:        str,
    model:           str,
    temperature:     float,
    k_final:         int,
    agent_func:      callable,
    config:          Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Runs the RAG agent with automatic retry on low-quality responses.

    Args:
        session:        Session dict (from SessionManager).
        masked_message: PII-masked user question.
        provider:       LLM provider key.
        model:          LLM model name.
        temperature:    LLM temperature.
        k_final:        Number of RAG chunks to retrieve.
        config:         Optional config dict from load_config().

    Returns:
        Tuple of:
            response     (str)             — final LLM answer text
            cot_storage  (list)            — RAG chunks used
            retry_meta   (dict)            — metadata about the retry process:
                {
                    "attempts":      int,           # total attempts made
                    "question_used": str,           # final question that succeeded
                    "ragas_scores":  dict,          # scores from the successful attempt
                    "all_attempts":  list[dict],    # scores for every attempt
                    "total_seconds": float,
                }

    Raises:
        RetryExhaustedError: If all MAX_ATTEMPTS fail the quality gate.
        Exception:           Any unexpected error from _run_agent.
    """
    # Lazy import to avoid circular deps — api.py defines _run_agent
    from api import _run_agent
    from core.utils.ragas_evaluator import evaluate_rag_response

    if config is None:
        from core.utils.utils import load_config
        config = load_config()

    start_total      = time.time()
    current_question = masked_message
    all_attempts     = []
    last_scores      = {}

    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info(f"[RETRY] === Attempt {attempt}/{MAX_ATTEMPTS} ===")

        # ── 1. Run the agent ────────────────────────────────────────────────
        try:
            response, cot_storage = agent_func(
                session=session,
                masked_message=current_question,
                provider=provider,
                model=model,
                temperature=temperature,
                k_final=k_final,
            )
        except Exception as e:
            logger.error(f"[RETRY] _run_agent raised on attempt {attempt}: {e}", exc_info=True)
            # Technical error counts as a failed attempt
            all_attempts.append({"attempt": attempt, "question": current_question, "error": str(e)})
            if attempt < MAX_ATTEMPTS:
                current_question = _reformulate_question(
                    masked_message, attempt + 1,
                    RETRY_JUDGE_PROVIDER, RETRY_JUDGE_MODEL,
                )
            continue

        # ── 2. Evaluate with RAGAS ──────────────────────────────────────────
        ragas_result = evaluate_rag_response(
            question=current_question,
            answer=response,
            cot_storage=cot_storage,
            provider=RETRY_JUDGE_PROVIDER,
            model=RETRY_JUDGE_MODEL,
            config=config,
        )
        last_scores = ragas_result
        all_attempts.append({
            "attempt":  attempt,
            "question": current_question,
            "scores":   ragas_result,
        })

        # ── 3. Quality gate ─────────────────────────────────────────────────
        if _passes_quality_gate(ragas_result):
            retry_meta = {
                "attempts":      attempt,
                "question_used": current_question,
                "ragas_scores":  ragas_result,
                "all_attempts":  all_attempts,
                "total_seconds": round(time.time() - start_total, 3),
            }
            logger.info(
                f"[RETRY] Success on attempt {attempt}/{MAX_ATTEMPTS} "
                f"— total {retry_meta['total_seconds']}s"
            )
            return response, cot_storage, retry_meta

        # ── 4. Reformulate for next attempt ─────────────────────────────────
        if attempt < MAX_ATTEMPTS:
            current_question = _reformulate_question(
                masked_message, attempt + 1,
                RETRY_JUDGE_PROVIDER, RETRY_JUDGE_MODEL,
            )

    # All attempts exhausted
    total = round(time.time() - start_total, 3)
    logger.warning(
        f"[RETRY] All {MAX_ATTEMPTS} attempts failed quality gate "
        f"— last scores: {last_scores} — total {total}s"
    )
    raise RetryExhaustedError(attempts=MAX_ATTEMPTS, last_scores=last_scores)
