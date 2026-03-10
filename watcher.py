import os
import time
import shutil

# --- IMPORTS DES OUTILS ---
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from langchain_groq import ChatGroq

# --- IMPORTS DU PROJET (Chemins réels) ---
from core.agent.guardian import load_api_key, is_valid_lore_file, _load_config
from core.database.vector_manager import VectorManager
from converters import convert_csv, convert_markdown, convert_json, convert_text, convert_pdf
from data.new_files.convert_unstructured import process_with_unstructured


class LoreWatcherHandler(FileSystemEventHandler):

    def __init__(self):
        # récupération de la config (nom du modèle + clé api) avec la fonction load_api_key()
        config = _load_config()

        guardian_cfg = config.get("guardian", {})
        provider = guardian_cfg.get("provider", "groq")
        model_name = guardian_cfg.get("model", "llama-3.1-8b-instant")

        api_key = load_api_key()

        # on prépare l'IA une seule fois au démarrage de Watcher
        self.llm = ChatGroq(
            model_name=model_name,
            groq_api_key=api_key,
            temperature=0
        )

        # connexion base de données
        self.db_manager = VectorManager()

    def on_created(self, event):
        """Cette fonction se déclenche automatiquement dès qu'un fichier est ajouté"""

        # si c'est un dossier qui est créé, on ne fait rien (pas besoin)
        if event.is_directory or os.path.basename(event.src_path).startswith(('.', '~')):
            return

        print(f"[WATCHER] Nouveau fichier détecté : {os.path.basename(event.src_path)}")

        time.sleep(1)

        # envoi du fichier à la validation
        self.process_file(event.src_path)

    def process_file(self, file_path):

        file_name = os.path.basename(file_path)
        base_dir = os.path.join(os.getcwd(), "data")

        # dossier cible
        valid_archive = os.path.join(base_dir, "files")  # Archive des fichiers traités
        refused_dir = os.path.join(base_dir, "quarantine")

        # Validation IA (Le Gardien)
        if not is_valid_lore_file(file_path, self.llm):
            print(f"[IA] REJETÉ : {file_name}. Vers 'quarantine'.")
            shutil.move(file_path, os.path.join(refused_dir, file_name))
            return

        try:
            print(f"[SYSTEM] Conversion et Vectorisation de {file_name}...")
            extension = os.path.splitext(file_name)[1].lower()
            chunks = []
            meta = {"source": file_name}

            # ROUTAGE DES FICHIERS VERS LES BONS CONVERT.
            if extension == '.txt':
                chunks = convert_text.process_text_file(file_path)

            elif extension == '.csv':
                # Si tu as aussi adapté convert_csv pour renvoyer des tuples
                chunks = convert_csv.load_csv_data(file_path)

            elif extension == '.json':
                chunks = convert_json.parse_json(file_path)

            # SI AUCUN DE CE FORMAT ON ENVOIE A UNSTRUCTURED.IO
            else:
                print(f"[SYSTEM] Format complexe / inconnu détecté. Appel à Unstructured.io (LlamaIndex)...")
                chunks = process_with_unstructured(file_path)

            # 3. Insertion réelle dans Supabase via VectorManager
            if chunks:
                for text, base_metadata in chunks:
                    # Fusion des métadonnées spécifiques du chunk avec les métadonnées globales
                    merged_metadata = {**meta, **base_metadata}
                    self.db_manager.add_document(text, metadata=merged_metadata)
                print(f"[DB] {len(chunks)} fragments insérés pour {file_name}")

            # 4. Archivage du fichier source
            shutil.move(file_path, os.path.join(valid_archive, file_name))

        except Exception as e:
            print(f"Erreur lors du traitement de {file_name} : {e}")


def start_watching():
    """Configure et lance la surveillance du dossier"""

    path = os.path.join(os.getcwd(), "data", "new_files")

    # si le dossier n'existe pas, on le crée pour éviter les erreurs
    if not os.path.exists(path):
        os.makedirs(path)

    # On initialise notre gestionnaire d'événements (le Handler)
    event_handler = LoreWatcherHandler()

    # rattraper les fichiers existants - on traite les fichiers déjà présents
    print(f"Vérification des fichiers existants dans : {path}...")
    existing_files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

    for file_name in existing_files:
        # On ignore les fichiers cachés
        if not file_name.startswith(('.', '~')):
            file_path = os.path.join(path, file_name)
            print(f"[RATTRAPAGE] Traitement de : {file_name}")
            event_handler.process_file(file_path)

    # On initialise l'observateur système
    observer = Observer()

    # On lui dit de surveiller 'path' avec notre 'event_handler'
    observer.schedule(event_handler, path, recursive=False)

    # on démarre la surveillance
    observer.start()

    print(f"Watcher actif sur : {path}")

    # boucle pour surveiller en permanence

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    start_watching()

# lancer le module
# python watcher.py