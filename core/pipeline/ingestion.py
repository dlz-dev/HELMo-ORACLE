"""
Ingestion pipeline for lore files into the vector database.

Pipeline steps per file:
  1. GUARD    — Validates that the file is Dofus/MMORPG lore.
  2. CONTEXT  — An LLM generates a global description of the document.
  3. PARSE    — Converts the file based on its extension via LlamaIndex.
  4. VECTORIZE— Each contextualized chunk is vectorized and saved to the DB.
"""

import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

from converters import convert_csv, convert_markdown, convert_text, convert_json, convert_pdf, convert_unstructured
from core.agent.guardian import is_valid_lore_file
from core.database.vector_manager import VectorManager
from core.utils.utils import _CONTEXT_PROMPT, _load_config, load_api_key
from providers import get_llm


def generate_document_context(file_path: Path, llm: Any) -> str:
    """
    Generates a contextual description of the entire document using an LLM.

    Args:
        file_path (Path): The path to the file to read.
        llm (Any): The language model instance used for generation.

    Returns:
        str: The generated context, or an empty string if it fails.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            sample = f.read(3000)
    except Exception:
        return ""

    try:
        response = llm.invoke(_CONTEXT_PROMPT.format(sample=sample))
        context = response.content.strip()
        print(f"    📝 Context generated: {context[:80]}...")
        return context
    except Exception as e:
        print(f"    ⚠️ Context generation failed ({e}) — vectorizing without context")
        return ""


def seed_database() -> None:
    """
    Main pipeline to read files, validate them, generate context, chunk, and insert 
    them into the vector database.
    """
    current_dir = Path(__file__).resolve().parent
    input_folder = current_dir.parent.parent / "data" / "files"
    quarantine_folder = current_dir.parent.parent / "data" / "quarantine"
    quarantine_folder.mkdir(parents=True, exist_ok=True)

    config = _load_config()

    guardian_cfg = config.get("guardian", {})
    ctx_provider = guardian_cfg.get("provider", "groq")
    ctx_model = guardian_cfg.get("model", "gemma2-9b-it")

    try:
        context_llm = get_llm(provider_key=ctx_provider, model=ctx_model, config=config)
        print(f"🔮 Contextualization initialized via {ctx_provider}/{ctx_model}")
    except Exception as e:
        context_llm = None
        print(f"⚠️ Context LLM unavailable ({e}) — ingestion will proceed without LLM context")

    print("🗄️ Connecting to vector database...")
    db_manager = VectorManager()
    api_key = load_api_key()

    print(f"\n📂 Reading files from: {input_folder}")
    print("─" * 60)

    files = sorted(input_folder.iterdir())
    total_accepted = total_rejected = total_chunks = 0

    for file_path in files:
        if not file_path.is_file() or not file_path.name.startswith("lore_"):
            continue

        print(f"\n📄 {file_path.name}")

        try:
            valid = is_valid_lore_file(str(file_path), api_key)
        except RuntimeError as e:
            print(f"\n🛑 {e}\n   Ingestion interrupted. Restart when the service is available.")
            return

        if not valid:
            total_rejected += 1
            print("  🚫 REJECTED → moved to quarantine")
            shutil.move(str(file_path), str(quarantine_folder / file_path.name))
            continue

        total_accepted += 1
        doc_context = ""
        
        if context_llm is not None:
            doc_context = generate_document_context(file_path, context_llm)

        base_metadata: Dict[str, Any] = {"source": file_path.name}
        if doc_context:
            base_metadata["global_context"] = doc_context

        extension = file_path.suffix.lower()
        extracted_chunks: List[Tuple[str, Dict[str, Any]]] = []

        if extension == ".csv":
            extracted_chunks = convert_csv.load_csv_data(str(file_path))
        elif extension == ".md":
            extracted_chunks = convert_markdown.parse_markdown(str(file_path))
        elif extension == ".txt":
            extracted_chunks = convert_text.process_text_file(str(file_path))
        elif extension == ".json":
            extracted_chunks = convert_json.parse_json(str(file_path))
        elif extension == ".pdf":
            extracted_chunks = convert_pdf.process_pdf_file(str(file_path))
        else:
            print("  🔄 Complex format detected. Calling Unstructured.io...")
            extracted_chunks = convert_unstructured.process_with_unstructured(str(file_path))

        if extracted_chunks:
            for text_chunk, specific_metadata in extracted_chunks:
                merged_metadata = {**base_metadata, **specific_metadata}
                db_manager.add_document(text_chunk, metadata=merged_metadata)

            total_chunks += len(extracted_chunks)
            print(f"  ✅ {len(extracted_chunks)} chunks inserted")
        else:
            print(f"  ⚠️ No text extracted from {file_path.name}")

    print("\n" + "─" * 60)
    print("✅ Ingestion complete!")
    print(f"   Accepted files: {total_accepted}")
    print(f"   Rejected files: {total_rejected}")
    print(f"   Total chunks:   {total_chunks}")


if __name__ == "__main__":
    seed_database()