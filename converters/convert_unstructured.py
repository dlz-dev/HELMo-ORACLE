import os
import sys
from typing import List, Tuple

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.models import operations

# Nouveaux imports LlamaIndex
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from core.utils.utils import _load_config


root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)


def process_with_unstructured(file_path: str) -> List[Tuple[str, dict]]:
    """
    Envoie le fichier à l'API Unstructured, convertit en Documents LlamaIndex,
    applique un SentenceSplitter et retourne une liste de (texte, métadonnées).
    """
    config = _load_config()

    unst_cfg = config.get("llm", {}).get("unstructured", {})
    api_key = unst_cfg.get("api_key")
    server_url = unst_cfg.get("server_url")

    if not api_key or not server_url:
        print("Erreur : API Key ou Server URL manquante dans config.yaml")
        return []

    client = UnstructuredClient(api_key_auth=api_key, server_url=server_url)
    file_name = os.path.basename(file_path)

    try:
        with open(file_path, "rb") as f:
            files = shared.Files(content=f.read(), file_name=file_name)

        res = client.general.partition(request=operations.PartitionRequest(
            partition_parameters=shared.PartitionParameters(
                files=files,
                strategy=shared.Strategy.HI_RES,
                languages=["fra"]
            )
        ))

        # 1. Création des Documents LlamaIndex
        documents = []
        for el in res.elements:
            if "text" in el and el["text"].strip():
                # Nettoyage des métadonnées pour PostgreSQL
                raw_meta = el.get("metadata", {})
                page_number = raw_meta.get("page_number")

                metadata = {
                    "source": file_name,
                    "type": str(el.get("type", "")),
                    "method": "unstructured"
                }
                if page_number:
                    metadata["page_number"] = str(page_number)

                # LlamaIndex utilise 'text' (et non 'page_content')
                doc = Document(text=el["text"], metadata=metadata)
                documents.append(doc)

        # 2. Découpage (Chunking) avec LlamaIndex
        # 512 tokens est la taille idéale pour le modèle multilingual-e5-base
        parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        nodes = parser.get_nodes_from_documents(documents)

        # 3. Retourne directement le format attendu par ton VectorManager
        return [(node.get_content(), node.metadata) for node in nodes]

    except Exception as e:
        print(f"Erreur Unstructured API : {e}")
        return []