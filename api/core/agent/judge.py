import json
from typing import Any

from langchain_core.messages import HumanMessage

from core.utils.logger import log_to_db_sync
from core.utils.utils import load_judge_prompt
from providers import get_llm


def _run_judge_sync(
        query: str,
        response: str,
        cot_storage: list[dict[str, Any]],
        user_id: str,
        session_id: str,
        config: dict[str, Any]
) -> None:
    """
    Executes the LLM Judge synchronously to evaluate the quality of a RAG response
    (faithfulness, coverage, etc.) and logs the result to the database.

    Failure of this function is silent to ensure it does not interrupt the user experience.
    """
    try:
        context_str: str = "\n\n".join([f"[{c.get('source', 'Unknown')}] {c.get('content', '')}" for c in cot_storage])
        if not context_str:
            context_str = "No context provided."

        prompt_template = load_judge_prompt()
        prompt_text: str = prompt_template.format(
            query=query,
            context=context_str,
            response=response
        )

        judge_cfg: dict[str, Any] = config.get("judge", {})
        judge_provider: str = judge_cfg.get("provider", "groq")
        judge_model: str = judge_cfg.get("model", "llama-3.3-70b-versatile")
        judge_temperature: float = float(judge_cfg.get("temperature", 0.0))

        # Secure temperature override to ensure deterministic output (often required for strict JSON)
        judge_config: dict[str, Any] = {
            **config,
            "llm": {**config.get("llm", {}), "temperature": judge_temperature}
        }
        llm = get_llm(provider_key=judge_provider, model=judge_model, config=judge_config)

        result = llm.invoke([HumanMessage(content=prompt_text)])
        raw_json: str = result.content.strip()

        # Robust cleaning of markdown tags (```json or ```)
        if raw_json.startswith("```"):
            raw_json = raw_json.split("\n", 1)[-1]  # Remove the first line defining the block
            if raw_json.endswith("```"):
                raw_json = raw_json[:-3].strip()

        evaluation: dict[str, int] = json.loads(raw_json)

        required_keys: set[str] = {"context_relevance", "faithfulness", "answer_relevance", "context_coverage"}
        if not required_keys.issubset(evaluation.keys()):
            raise ValueError(f"Incomplete Judge JSON — missing keys: {required_keys - evaluation.keys()}")

        for key in required_keys:
            if not isinstance(evaluation[key], int) or not (1 <= evaluation[key] <= 5):
                raise ValueError(f"Invalid score for '{key}': {evaluation[key]}")

        log_to_db_sync(
            level="INFO",
            source="LLM_JUDGE",
            message="RAG Evaluation Completed",
            metadata={
                "session_id": session_id,
                "scores": evaluation,
                "provider": judge_provider,
                "model": judge_model
            },
            user_id=user_id
        )

    except Exception as e:
        from core.utils.logger import logger
        logger.error(f"Error during LLM Judge execution: {e}", exc_info=True)
