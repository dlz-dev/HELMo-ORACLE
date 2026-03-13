"""
Pipeline d'ingestion des fichiers lore dans la base vectorielle.

Étapes pour chaque fichier :
  1. GARDE    — Le Gardien IA valide que le fichier est du lore Dofus/MMORPG.
               Si l'API est indisponible → ingestion stoppée (fail-strict).
  2. PARSE    — Conversion selon le format via LlamaIndex (csv, md, txt, json, pdf, unstructured).
  3. CONTEXTE — Un LLM génère une description globale du document (1 appel/fichier).
               Ce contexte est préfixé à chaque chunk AVANT vectorisation
               (Contextual Retrieval — améliore la qualité de la recherche).
  4. VECTORISE — Chaque chunk contextualisé est vectorisé et sauvegardé.
               Le texte ORIGINAL (sans préfixe) est stocké en base pour la lecture.
"""

import os
import shutil

from core.agent.guardian import is_valid_lore_file, load_api_key
from core.database.vector_manager import VectorManager
from converters import convert_csv, convert_markdown, convert_text, convert_json, convert_pdf, convert_unstructured
from providers import get_llm

from core.utils.utils import _load_config, _CONTEXT_PROMPT

# ─────────────────────────────────────────────────────────────────
# Contextual Retrieval — génération du contexte global par fichier
# ─────────────────────────────────────────────────────────────────

def generate_document_context(file_path: str, llm) -> str:
    """
    Génère une description contextuelle du document entier via LLM.
    Utilisée comme préfixe pour chaque chunk avant vectorisation.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sample = f.read(3000)
    except Exception:
        return ""

    try:
        response = llm.invoke(_CONTEXT_PROMPT.format(sample=sample))
        context = response.content.strip()
        print(f"    📝 Contexte généré : {context[:80]}{'...' if len(context) > 80 else ''}")
        return context
    except Exception as e:
        print(f"    ⚠️  Génération de contexte échouée ({e}) — vectorisation sans contexte")
        return ""


# ─────────────────────────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────────────────────────

def seed_database() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(current_dir, "../..", "data", "files")
    quarantine_folder = os.path.join(current_dir, "../..", "data", "quarantine")
    os.makedirs(quarantine_folder, exist_ok=True)

    config = _load_config()

    # ── Initialisation du LLM pour la contextualisation ──────────
    guardian_cfg = config.get("guardian", {})
    ctx_provider = guardian_cfg.get("provider", "groq")
    ctx_model = guardian_cfg.get("model", "gemma2-9b-it")

    try:
        context_llm = get_llm(provider_key=ctx_provider, model=ctx_model, config=config)
        print(f"🔮 Contextualisation via {ctx_provider}/{ctx_model}")
    except Exception as e:
        context_llm = None
        print(f"⚠️  LLM de contextualisation indisponible ({e}) — ingestion sans contexte LLM")

    # ── Initialisation DB ─────────────────────────────────────────
    print("🗄️  Connexion à la base vectorielle...")
    db_manager = VectorManager()

    api_key = load_api_key()

    print(f"\n📂 Lecture des fichiers dans : {input_folder}")
    print("─" * 60)

    files = sorted(os.listdir(input_folder))
    total_accepted = total_rejected = total_chunks = 0

    for file_name in files:
        file_path = os.path.join(input_folder, file_name)

        if not file_name.startswith("lore_"):
            print(f"  ⏭️  Ignoré (pas de préfixe lore_) : {file_name}")
            continue

        print(f"\n📄 {file_name}")

        # ── Étape 1 : Validation par le Gardien ───────────────────
        try:
            valid = is_valid_lore_file(file_path, api_key)
        except RuntimeError as e:
            print(f"\n🛑 {e}")
            print("   Ingestion interrompue. Relancez quand le service est disponible.")
            return

        if not valid:
            total_rejected += 1
            print(f"  🚫 REJETÉ → déplacé en quarantaine")
            shutil.move(file_path, os.path.join(quarantine_folder, file_name))
            continue

        total_accepted += 1

        # ── Étape 2 : Génération du contexte global ───────────────
        doc_context = ""
        if context_llm is not None:
            doc_context = generate_document_context(file_path, context_llm)

        base_metadata = {"source": file_name}
        if doc_context:
            base_metadata["global_context"] = doc_context

        # ── Étape 3 : Parse unifié (LlamaIndex) ───────────────────
        extension = os.path.splitext(file_name)[1].lower()
        extracted_chunks = []

        if extension == ".csv":
            extracted_chunks = convert_csv.load_csv_data(file_path)
        elif extension == ".md":
            extracted_chunks = convert_markdown.parse_markdown(file_path)
        elif extension == ".txt":
            extracted_chunks = convert_text.process_text_file(file_path)
        elif extension == ".json":
            extracted_chunks = convert_json.parse_json(file_path)
        elif extension == ".pdf":
            extracted_chunks = convert_pdf.process_pdf_file(file_path)
        else:
            print(f"  🔄 Format complexe détecté. Appel à Unstructured.io...")
            extracted_chunks = convert_unstructured.process_with_unstructured(file_path)

        # ── Étape 4 : Vectorisation et insertion ──────────────────
        if extracted_chunks:
            for text_chunk, specific_metadata in extracted_chunks:
                # Fusion des métadonnées (le spécifique écrase le global si conflit)
                merged_metadata = {**base_metadata, **specific_metadata}
                db_manager.add_document(text_chunk, metadata=merged_metadata)

            total_chunks += len(extracted_chunks)
            print(f"  ✅ {len(extracted_chunks)} chunks insérés")
        else:
            print(f"  ⚠️  Aucun texte extrait de {file_name}")

    # ── Résumé final ──────────────────────────────────────────────
    print("\n" + "─" * 60)
    print(f"✅ Ingestion terminée !")
    print(f"   Fichiers acceptés : {total_accepted}")
    print(f"   Fichiers rejetés  : {total_rejected}")
    print(f"   Total chunks      : {total_chunks}")


if __name__ == "__main__":
    seed_database()

# N'oublie pas la commande SQL pour vider et adapter ta table si tu passes sur intfloat/multilingual-e5-base :
# ALTER TABLE documents ALTER COLUMN vecteur TYPE vector(768);
# TRUNCATE TABLE documents RESTART IDENTITY;