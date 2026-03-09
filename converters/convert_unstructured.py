import os
import sys
from typing import List
from langchain_core.documents import Document
from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.models import operations

# On s'assure que la racine est connue pour trouver 'core'
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)

try:
    from core.guardian import _load_config
except ImportError:
    # Fallback au cas où l'import automatique échoue encore
    import yaml
    def _load_config():
        path = os.path.join(root, "config", "config.yaml")
        with open(path, "r") as f:
            return yaml.safe_load(f)


def process_with_unstructured(file_path: str) -> List[Document]:
    config = _load_config()

    # Récupération des deux paramètres depuis le YAML
    unst_cfg = config.get("llm", {}).get("unstructured", {})
    api_key = unst_cfg.get("api_key")
    server_url = unst_cfg.get("server_url")

    if not api_key or not server_url:
        print("Erreur : API Key ou Server URL manquante dans config.yaml")
        return []

    # Initialisation avec l'URL spécifique
    client = UnstructuredClient(
        api_key_auth=api_key,
        server_url=server_url
    )

    file_name = os.path.basename(file_path)

    try:
        with open(file_path, "rb") as f:
            files = shared.Files(
                content=f.read(),
                file_name=file_name,
            )

        # On suit la doc : partitionnement
        res = client.general.partition(request=operations.PartitionRequest(
            partition_parameters=shared.PartitionParameters(
                files=files,
                strategy=shared.Strategy.HI_RES,
                languages=["fra"]
            )
        ))

        documents = []
        for el in res.elements:
            if "text" in el and el["text"].strip():
                doc = Document(
                    page_content=el["text"],
                    metadata={
                        "source": file_name,
                        "type": el.get("type"),
                        "page_number": el.get("metadata", {}).get("page_number"),
                        "method": "unstructured"
                    }
                )
                documents.append(doc)

        return documents

    except Exception as e:
        print(f"Erreur Unstructured API : {e}")
        return []