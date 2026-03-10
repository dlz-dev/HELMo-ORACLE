import csv
import json
import os
from typing import List, Tuple

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter


def load_csv_data(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[Tuple[str, dict]]:
    """
    Reads a CSV file, converts each row into a text representation,
    and uses LlamaIndex to chunk them properly.
    Returns a list of tuples (text, metadata).
    """
    file_name = os.path.basename(file_path)
    documents = []

    try:
        # Validation stricte de l'UTF-8
        with open(file_path, "r", encoding='utf-8', errors='strict') as file:
            sample = file.read(1024)
            file.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error as e:
                print(f"Fichier CSV ignoré (format non reconnu ou vide) : {file_path} - {e}")
                return []

            reader = csv.DictReader(file, dialect=dialect)
            for row in reader:
                # Extraction de métadonnées spécifiques si présentes
                item_name = row.get("name") or row.get("nom") or row.get("id") or ""
                metadata = {"source": file_name}
                if item_name:
                    metadata["item_name"] = str(item_name)

                # Conversion de la ligne en chaîne JSON lisible pour le LLM
                chunk_text = json.dumps(row, ensure_ascii=False)

                # Création du Document LlamaIndex
                doc = Document(text=chunk_text, metadata=metadata)
                documents.append(doc)

    except FileNotFoundError:
        raise
    except UnicodeDecodeError as e:
        print(f"⚠️ Erreur d'encodage (non UTF-8 valide) pour {file_path} : {e}")
        return []
    except Exception as e:
        print(f"⚠️ Erreur inattendue lors de la lecture de {file_path} : {e}")
        return []

    if not documents:
        return []

    # Découpage avec LlamaIndex (sécurise les lignes contenant des textes très longs)
    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = text_splitter.get_nodes_from_documents(documents)

    return [(node.get_content(), node.metadata) for node in nodes]