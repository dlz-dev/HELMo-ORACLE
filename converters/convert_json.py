import json
import os
from typing import List, Tuple

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter


def parse_json(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[Tuple[str, dict]]:
    """
    Reads a JSON file, extracts logical objects/metadata,
    and splits them using LlamaIndex SentenceSplitter.
    Returns a list of tuples (text, metadata).
    """
    file_name = os.path.basename(file_path)
    try:
        with open(file_path, 'r', encoding='utf-8', errors='strict') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Fichier JSON invalide ignoré ({file_path}) : {e}")
        return []
    except UnicodeDecodeError as e:
        print(f"Erreur d'encodage (non UTF-8 valide) pour {file_path} : {e}")
        return []
    except Exception as e:
        print(f"Erreur inattendue lors de la lecture de {file_path} : {e}")
        return []

    documents = []

    # Case 1: The JSON is a large dictionary
    if isinstance(data, dict):
        for parent_key, parent_value in data.items():

            # If the category contains a list of objects
            if isinstance(parent_value, list):
                for item in parent_value:
                    metadata = {"source": file_name, "category": parent_key}
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("nom") or item.get("id")
                        if name:
                            metadata["item_name"] = str(name)

                    chunk_text = json.dumps(item, ensure_ascii=False)
                    documents.append(Document(text=chunk_text, metadata=metadata))

            # If the category contains a single object
            elif isinstance(parent_value, dict):
                metadata = {"source": file_name, "category": parent_key}
                chunk_text = json.dumps(parent_value, ensure_ascii=False)
                documents.append(Document(text=chunk_text, metadata=metadata))

            # Other (raw text)
            else:
                metadata = {"source": file_name, "category": parent_key}
                documents.append(Document(text=str(parent_value), metadata=metadata))

    # Case 2: The JSON is directly a list (no parent key)
    elif isinstance(data, list):
        for item in data:
            metadata = {"source": file_name}
            if isinstance(item, dict):
                name = item.get("name") or item.get("nom") or item.get("id")
                if name:
                    metadata["item_name"] = str(name)

            chunk_text = json.dumps(item, ensure_ascii=False)
            documents.append(Document(text=chunk_text, metadata=metadata))

    else:
        documents.append(Document(text=str(data), metadata={"source": file_name}))

    if not documents:
        return []

    # Découpage avec LlamaIndex pour respecter la fenêtre de tokens du modèle d'embedding
    text_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = text_splitter.get_nodes_from_documents(documents)

    return [(node.get_content(), node.metadata) for node in nodes]