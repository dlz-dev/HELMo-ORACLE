import os
import shutil
import time
from typing import Any, Dict, List, Tuple

from langchain_groq import ChatGroq
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from core.database.vector_manager import VectorManager
from converters import convert_csv, convert_json, convert_text
from converters.convert_unstructured import process_with_unstructured
from core.utils.utils import _load_config, load_api_key

class LoreWatcherHandler(FileSystemEventHandler):
    """
    Gestionnaire d'événements pour la surveillance et l'ingestion automatique
    des fichiers de lore dans la base vectorielle.
    """

    def __init__(self) -> None:
        super().__init__()

        config: Dict[str, Any] = _load_config()
        guardian_cfg: Dict[str, Any] = config.get("guardian", {})

        model_name: str = guardian_cfg.get("model", "llama-3.1-8b-instant")
        api_key: str = load_api_key()

        self.llm: ChatGroq = ChatGroq(
            model_name=model_name,
            groq_api_key=api_key,
            temperature=0.0
        )

        self.db_manager: VectorManager = VectorManager()

    def on_created(self, event: FileSystemEvent) -> None:
        """Point d'entrée de watchdog lors de la création d'un fichier."""
        file_name: str = os.path.basename(event.src_path)
        if event.is_directory or file_name.startswith(('.', '~')):
            return

        print(f"[WATCHER] Nouveau fichier détecté : {file_name}")
        time.sleep(1.0)

        self.process_file(event.src_path)

    def process_file(self, file_path: str) -> None:
        """Traite un fichier : validation IA, conversion, vectorisation et archivage."""
        file_name: str = os.path.basename(file_path)
        base_dir: str = os.path.join(os.getcwd(), "data")

        valid_archive: str = os.path.join(base_dir, "files")
        refused_dir: str = os.path.join(base_dir, "quarantine")

        os.makedirs(valid_archive, exist_ok=True)
        os.makedirs(refused_dir, exist_ok=True)

        print(f"[IA] Évaluation de {file_name} par le Gardien...")
        if not is_valid_lore_file(file_path, self.llm):
            print(f"[IA] REJETÉ : {file_name}. Déplacement vers 'quarantine'.")
            shutil.move(file_path, os.path.join(refused_dir, file_name))
            return

        try:
            print(f"[SYSTEM] Conversion de {file_name}...")
            extension: str = os.path.splitext(file_name)[1].lower()
            chunks: List[Tuple[str, Dict[str, Any]]] = []
            meta: Dict[str, Any] = {"source": file_name}

            # Routage dynamique selon l'extension du fichier
            if extension == '.txt':
                chunks = convert_text.process_text_file(file_path)
            elif extension == '.csv':
                chunks = convert_csv.load_csv_data(file_path)
            elif extension == '.json':
                chunks = convert_json.parse_json(file_path)
            else:
                print("[SYSTEM] Format complexe détecté. Appel à Unstructured.io...")
                chunks = process_with_unstructured(file_path)

            if chunks:
                for text, base_metadata in chunks:
                    merged_metadata: Dict[str, Any] = {**meta, **base_metadata}
                    self.db_manager.add_document(text, metadata=merged_metadata)

                print(f"[DB] {len(chunks)} fragments insérés avec succès pour {file_name}.")
            else:
                print(f"[SYSTEM] Avertissement : Aucun contenu extrait de {file_name}.")

            shutil.move(file_path, os.path.join(valid_archive, file_name))

        except Exception as e:
            print(f"[ERREUR] Échec lors du traitement de {file_name} : {e}")


def start_watching() -> None:
    """Lance la surveillance du dossier d'ingestion et rattrape les fichiers en attente."""
    path: str = os.path.join(os.getcwd(), "data", "new_files")
    os.makedirs(path, exist_ok=True)

    event_handler = LoreWatcherHandler()

    # Traitement des fichiers déposés avant le lancement du script (rattrapage)
    print(f"[INIT] Vérification des fichiers existants dans : {path}...")
    existing_files: List[str] = [
        f for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f))
    ]

    for file_name in existing_files:
        if not file_name.startswith(('.', '~')):
            file_path: str = os.path.join(path, file_name)
            print(f"[RATTRAPAGE] Traitement de : {file_name}")
            event_handler.process_file(file_path)

    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    print(f"\n[WATCHER] Actif et en attente de fichiers sur : {path}\nAppuyez sur Ctrl+C pour arrêter.")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[WATCHER] Arrêt demandé par l'utilisateur.")
        observer.stop()

    observer.join()
    print("[WATCHER] Processus terminé.")


if __name__ == "__main__":
    start_watching()