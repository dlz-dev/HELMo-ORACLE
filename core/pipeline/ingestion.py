"""
Pipeline d'ingestion des fichiers lore dans la base vectorielle.

Étapes pour chaque fichier :
  1. GARDE    — Le Gardien IA valide que le fichier est du lore Dofus/MMORPG.
               Si l'API est indisponible → ingestion stoppée (fail-strict).
  2. PARSE    — Conversion selon le format (csv, md, txt, json).
  3. CONTEXTE — Un LLM génère une description globale du document (1 appel/fichier).
               Ce contexte est préfixé à chaque chunk AVANT vectorisation
               (Contextual Retrieval — améliore la qualité de la recherche).
  4. VECTORISE — Chaque chunk contextualisé est vectorisé et sauvegardé.
               Le texte ORIGINAL (sans préfixe) est stocké en base pour la lecture.
"""

import json
import os
import shutil
import sys

import yaml

# ── Résolution des imports depuis core/ ─────────────────────────
_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
_BASE_DIR = os.path.dirname(_CORE_DIR)
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from core.agent.guardian import is_valid_lore_file, load_api_key
from core.database.vector_manager import VectorManager
from converters import convert_csv, convert_markdown, convert_text, convert_json
from providers import get_llm


# ─────────────────────────────────────────────────────────────────
# Config loader
# ─────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    config_path = os.path.join(_BASE_DIR, "config", "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────────────────────────────
# Contextual Retrieval — génération du contexte global par fichier
# ─────────────────────────────────────────────────────────────────

_CONTEXT_PROMPT = """Tu analyses un document provenant des archives du jeu Dofus (MMORPG).
Écris en 2-3 phrases maximum une description du CONTENU GLOBAL de ce document.
Cette description sera utilisée comme contexte pour chaque fragment du document.

Sois précis : mentionne le type de données (armes, monstres, quêtes, lore historique...),
les entités principales couvertes, et l'utilité pour un joueur Dofus.

Document (extrait des 3000 premiers caractères) :
---
{sample}
---

Réponds avec UNIQUEMENT la description, sans introduction ni ponctuation finale."""


def generate_document_context(file_path: str, llm) -> str:
    """
    Génère une description contextuelle du document entier via LLM.
    Utilisée comme préfixe pour chaque chunk avant vectorisation.

    Retourne une chaîne vide si la génération échoue (non bloquant —
    le chunk sera vectorisé sans contexte plutôt que bloqué).
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
    """
    Parcourt data/files/, valide, contextualise et ingère chaque fichier lore.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_folder = os.path.join(current_dir, "../..", "data", "files")
    quarantine_folder = os.path.join(current_dir, "../..", "data", "quarantaine")
    os.makedirs(quarantine_folder, exist_ok=True)

    config = _load_config()

    # ── Initialisation du LLM pour la contextualisation ──────────
    # On réutilise le provider du Gardien (petit modèle, suffisant pour résumer)
    guardian_cfg = config.get("guardian", {})
    ctx_provider = guardian_cfg.get("provider", "groq")
    ctx_model = guardian_cfg.get("model", "gemma2-9b-it")

    try:
        context_llm = get_llm(provider_key=ctx_provider, model=ctx_model, config=config)
        print(f"🔮 Contextualisation via {ctx_provider}/{ctx_model}")
    except Exception as e:
        # Indisponible → on continue sans contextualisation (non bloquant)
        context_llm = None
        print(f"⚠️  LLM de contextualisation indisponible ({e}) — ingestion sans contexte LLM")

    # ── Initialisation DB ─────────────────────────────────────────
    print("🗄️  Connexion à la base vectorielle...")
    db_manager = VectorManager()

    # ── Validation Guardian disponible avant de commencer ─────────
    # On charge la clé API une fois ; si ça échoue, load_api_key lève une exception
    api_key = load_api_key()

    print(f"\n📂 Lecture des fichiers dans : {input_folder}")
    print("─" * 60)

    files = sorted(os.listdir(input_folder))
    total_accepted = total_rejected = total_chunks = 0

    for file_name in files:
        file_path = os.path.join(input_folder, file_name)

        # ── Filtre préfixe ────────────────────────────────────────
        if not file_name.startswith("lore_"):
            print(f"  ⏭️  Ignoré (pas de préfixe lore_) : {file_name}")
            continue

        print(f"\n📄 {file_name}")

        # ── Étape 1 : Validation par le Gardien ───────────────────
        # is_valid_lore_file lève RuntimeError si l'API est totalement indisponible
        try:
            valid = is_valid_lore_file(file_path, api_key)
        except RuntimeError as e:
            # API du Gardien morte → on arrête tout
            print(f"\n🛑 {e}")
            print("   Ingestion interrompue. Relancez quand le service est disponible.")
            return

        if not valid:
            total_rejected += 1
            print(f"  🚫 REJETÉ → déplacé en quarantaine")
            shutil.move(file_path, os.path.join(quarantine_folder, file_name))
            continue

        total_accepted += 1

        # ── Étape 2 : Génération du contexte global (1 appel LLM) ─
        doc_context = ""
        if context_llm is not None:
            doc_context = generate_document_context(file_path, context_llm)

        # ── Étape 3 : Parse selon le format ───────────────────────
        extension = os.path.splitext(file_name)[1].lower()
        chunks_to_insert = []
        base_metadata = {"source": file_name}

        # Injecter le contexte global dans les métadonnées de chaque chunk
        if doc_context:
            base_metadata["global_context"] = doc_context

        if extension == ".csv":
            data = convert_csv.load_csv_data(file_path)
            for row in data:
                json_string = json.dumps(row, ensure_ascii=False)
                chunks_to_insert.append((json_string, base_metadata.copy()))

        elif extension == ".md":
            documents = convert_markdown.parse_markdown(file_path)
            for doc in documents:
                # Fusionner les métadonnées markdown (headers) avec le contexte global
                merged = base_metadata.copy()
                merged.update(doc.metadata)
                chunks_to_insert.append((doc.page_content, merged))

        elif extension == ".txt":
            documents = convert_text.process_text_file(file_path)
            for doc in documents:
                chunks_to_insert.append((doc.page_content, base_metadata.copy()))

        elif extension == ".json":
            data_chunks = convert_json.parse_json(file_path)
            for text_chunk, specific_metadata in data_chunks:
                merged = base_metadata.copy()
                merged.update(specific_metadata)
                chunks_to_insert.append((text_chunk, merged))

        else:
            print(f"  ⏭️  Format non supporté : {extension}")
            continue

        # ── Étape 4 : Vectorisation et insertion ──────────────────
        if chunks_to_insert:
            for text_chunk, metadata_chunk in chunks_to_insert:
                db_manager.add_document(text_chunk, metadata=metadata_chunk)

            total_chunks += len(chunks_to_insert)
            print(f"  ✅ {len(chunks_to_insert)} chunks insérés")

    # ── Résumé final ──────────────────────────────────────────────
    print("\n" + "─" * 60)
    print(f"✅ Ingestion terminée !")
    print(f"   Fichiers acceptés : {total_accepted}")
    print(f"   Fichiers rejetés  : {total_rejected}")
    print(f"   Total chunks      : {total_chunks}")


if __name__ == "__main__":
    seed_database()

# Pour vider la base avant une nouvelle ingestion :
# TRUNCATE TABLE documents RESTART IDENTITY;
