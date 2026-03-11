import os
import sys

from providers import get_llm
from core.utils.utils import _load_config, _GUARDIAN_PROMPT

# ─────────────────────────────────────────────────────────────────
# Gardien principal
# ─────────────────────────────────────────────────────────────────

def is_valid_lore_file(file_path: str, api_key: str = None) -> bool:
    """
    Valide un fichier via le LLM configuré dans config.yaml [guardian].

    Le paramètre api_key est conservé pour rétro-compatibilité avec
    ingestion.py mais n'est plus utilisé directement — la clé est
    lue depuis le config via get_llm().

    Config yaml utilisée :
        guardian:
          provider: "groq"            # provider du Gardien (indépendant de l'Oracle)
          model: "gemma2-9b-it"       # modèle léger suffisant pour classification
    """

    # ── Lecture du fichier ────────────────────────────────────────
    fname = os.path.basename(file_path)
    extension = os.path.splitext(fname)[1].lower()

    # Si c'est un PDF, on bypass la lecture texte (le Gardien auto-accepte)
    if extension == '.pdf':
        print(f"  📄 [{fname}] Format binaire (PDF) → Auto-Accepté pour conversion Unstructured")
        return True

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sample_text = f.read(1500)
    except Exception as e:
        # Fallback pour les fichiers texte avec des encodages bizarres
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                sample_text = f.read(1500)
        except:
            print(f"  🚫 [{fname}] Erreur de lecture : {e} → REFUSÉ (impossible à lire)")
            return False

    # ── Chargement config & LLM ───────────────────────────────────
    try:
        config = _load_config()
        guardian_cfg = config.get("guardian", {})
        provider_key = guardian_cfg.get("provider", "groq")
        model = guardian_cfg.get("model", "llama-3.1-8b-instant")
        llm = get_llm(provider_key=provider_key, model=model, config=config)

    except Exception as e:
        # L'API du Gardien est indisponible → on bloque TOUTE l'ingestion
        # pour éviter d'ingérer des fichiers non validés
        raise RuntimeError(
            f"🚫 Gardien indisponible ({provider_key}/{model}) : {e}\n"
            f"   Ingestion interrompue — aucun fichier ne sera ajouté sans validation."
        )

    # ── Appel LLM ────────────────────────────────────────────────
    prompt = _GUARDIAN_PROMPT.format(sample_text=sample_text)

    try:
        response = llm.invoke(prompt)
        answer = response.content.strip().upper()
        verdict = "OUI" in answer

        status = "✅ ACCEPTÉ" if verdict else "❌ REJETÉ"
        print(f"  🛡️  Gardien [{fname}] via {provider_key}/{model} → '{response.content.strip()}' → {status}")

        return verdict

    except Exception as e:
        # Erreur pendant la validation d'UN fichier → on refuse CE fichier
        # mais on laisse l'ingestion continuer pour les autres
        print(f"  🚫 [{fname}] Erreur API durant la validation : {e} → REFUSÉ (non validé)")
        return False  # fail-strict : pas de réponse = pas d'ingestion
