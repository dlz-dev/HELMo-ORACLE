import json
from langchain_core.messages import HumanMessage
from core.utils.utils import load_judge_prompt
from core.utils.logger import log_to_db_sync
from providers import get_llm


def _run_judge_sync(query: str, response: str, cot_storage: list, user_id: str, session_id: str, config: dict):
    """Exécute le LLM Judge de manière synchrone et loggue le résultat."""
    try:
        # Formater le contexte (concaténer les extraits RRF)
        context_str = "\n\n".join([f"[{c['source']}] {c['content']}" for c in cot_storage])
        if not context_str:
            context_str = "Aucun contexte fourni."

        # Préparer le prompt
        prompt_template = load_judge_prompt()
        prompt_text = prompt_template.format(
            query=query,
            context=context_str,
            response=response
        )

        # Lire la configuration du judge
        judge_cfg = config.get("judge", {})
        judge_provider = judge_cfg.get("provider", "groq")
        judge_model = judge_cfg.get("model", "llama-3.3-70b-versatile")
        judge_temperature = float(judge_cfg.get("temperature", 0.0))

        # Surcharge de la configuration avec la température du judge
        judge_config = {**config, "llm": {**config.get("llm", {}), "temperature": judge_temperature}}
        llm = get_llm(provider_key=judge_provider, model=judge_model, config=judge_config)

        # Invoquer le LLM
        result = llm.invoke([HumanMessage(content=prompt_text)])

        # Nettoyer et parser le JSON
        raw_json = result.content.strip()
        if raw_json.startswith("```json"):
            raw_json = raw_json[7:-3].strip()

        evaluation = json.loads(raw_json)

        # Logguer dans la base de données
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
        # On ne crashe pas l'application si le juge échoue
        from core.utils.logger import logger
        logger.error(f"Erreur lors de l'exécution du LLM Judge : {e}", exc_info=True)