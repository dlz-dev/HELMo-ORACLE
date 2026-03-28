import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from langchain_groq import ChatGroq
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from converters import convert_csv, convert_json, convert_text
from converters.convert_unstructured import process_with_unstructured
from core.agent.guardian import is_valid_lore_file
from core.database.vector_manager import VectorManager
from core.utils.utils import ARCHIVE_DIR, NEW_FILES_DIR, QUARANTINE_DIR, load_api_key, load_config


class LoreWatcherHandler(FileSystemEventHandler):
    """
    Event handler for monitoring and automatically ingesting 
    lore files into the vector database.
    """

    def __init__(self) -> None:
        super().__init__()

        config: Dict[str, Any] = load_config()
        guardian_cfg: Dict[str, Any] = config.get("guardian", {})

        model_name: str = guardian_cfg.get("model", "llama-3.1-8b-instant")
        api_key: str = load_api_key()

        self.llm = ChatGroq(
            model_name=model_name,
            groq_api_key=api_key,
            temperature=0.0
        )
        self.db_manager = VectorManager()

        # Ensure required directories exist
        NEW_FILES_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    def on_created(self, event: FileSystemEvent) -> None:
        """Watchdog entry point triggered upon file creation."""
        file_path = Path(event.src_path)

        # Ignore directories and hidden/temp files
        if event.is_directory or file_path.name.startswith(('.', '~')):
            return

        print(f"[WATCHER] New file detected: {file_path.name}")

        # Small delay to ensure the OS has finished writing the file
        time.sleep(1.0)
        self.process_file(file_path)

    def process_file(self, file_path: Path) -> None:
        """
        Processes a file: AI validation, conversion, vectorization, and archiving.
        """
        file_name: str = file_path.name

        print(f"[AI] Guardian evaluating {file_name}...")

        # String conversion for legacy compatibility with is_valid_lore_file
        if not is_valid_lore_file(str(file_path), self.llm):
            print(f"[AI] REJECTED: {file_name}. Moving to quarantine.")
            shutil.move(str(file_path), str(QUARANTINE_DIR / file_name))
            return

        try:
            print(f"[SYSTEM] Converting {file_name}...")
            extension: str = file_path.suffix.lower()
            chunks: List[Tuple[str, Dict[str, Any]]] = []
            meta: Dict[str, Any] = {"source": file_name}

            # Dynamic routing based on file extension
            if extension == '.txt':
                chunks = convert_text.process_text_file(str(file_path))
            elif extension == '.csv':
                chunks = convert_csv.load_csv_data(str(file_path))
            elif extension == '.json':
                chunks = convert_json.parse_json(str(file_path))
            else:
                print(f"[SYSTEM] Complex format detected ({extension}). Calling Unstructured.io...")
                chunks = process_with_unstructured(str(file_path))

            if chunks:
                for text, base_metadata in chunks:
                    merged_metadata: Dict[str, Any] = {**meta, **base_metadata}
                    self.db_manager.add_document(text, metadata=merged_metadata)

                print(f"[DB] Successfully inserted {len(chunks)} chunks for {file_name}.")
            else:
                print(f"[SYSTEM] Warning: No content extracted from {file_name}.")

            # Archive the successfully processed file
            shutil.move(str(file_path), str(ARCHIVE_DIR / file_name))

        except Exception as e:
            print(f"[ERROR] Failed to process {file_name}: {e}")


def start_watching() -> None:
    """
    Starts monitoring the ingestion folder and catches up on any pending files.
    """
    NEW_FILES_DIR.mkdir(parents=True, exist_ok=True)
    event_handler = LoreWatcherHandler()

    print(f"[INIT] Checking for existing files in: {NEW_FILES_DIR}...")

    # Process backlog files deposited before the script started
    for file_path in NEW_FILES_DIR.iterdir():
        if file_path.is_file() and not file_path.name.startswith(('.', '~')):
            print(f"[CATCH-UP] Processing: {file_path.name}")
            event_handler.process_file(file_path)

    observer = Observer()
    observer.schedule(event_handler, str(NEW_FILES_DIR), recursive=False)
    observer.start()

    print(f"\n[WATCHER] Active and waiting for files in: {NEW_FILES_DIR}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[WATCHER] Shutdown requested by user.")
        observer.stop()

    observer.join()
    print("[WATCHER] Process terminated.")


if __name__ == "__main__":
    start_watching()
