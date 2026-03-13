import os
from typing import List, Tuple, Dict, Any

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared, operations
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from core.utils.utils import _load_config


def process_with_unstructured(file_path: str, chunk_size: int = 512, chunk_overlap: int = 50) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Processes a complex file via the Unstructured API and chunks it with LlamaIndex.
    
    Args:
        file_path (str): The path to the file.
        chunk_size (int): The maximum chunk size.
        chunk_overlap (int): The overlap between chunks.
        
    Returns:
        List[Tuple[str, Dict[str, Any]]]: A list of tuples (text, metadata).
    """
    config = _load_config()
    unst_cfg = config.get("llm", {}).get("unstructured", {})
    api_key = unst_cfg.get("api_key")
    server_url = unst_cfg.get("server_url")

    if not api_key or not server_url:
        print("ERROR: Missing API Key or Server URL in config.yaml for Unstructured.")
        return []

    client = UnstructuredClient(api_key_auth=api_key, server_url=server_url)
    file_name = os.path.basename(file_path)

    try:
        with open(file_path, "rb") as f:
            files = shared.Files(content=f.read(), file_name=file_name)

        req = operations.PartitionRequest(
            partition_parameters=shared.PartitionParameters(
                files=files,
                strategy=shared.Strategy.HI_RES,
                languages=["fra"]
            )
        )
        res = client.general.partition(request=req)

        documents = []
        for el in res.elements:
            text = el.get("text", "").strip()
            if not text:
                continue

            raw_meta = el.get("metadata", {})
            metadata: Dict[str, Any] = {
                "source": file_name,
                "type": str(el.get("type", "")),
                "method": "unstructured"
            }
            
            if "page_number" in raw_meta:
                metadata["page_number"] = str(raw_meta["page_number"])

            documents.append(Document(text=text, metadata=metadata))

        parser = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        nodes = parser.get_nodes_from_documents(documents)

        return [(node.get_content(), node.metadata) for node in nodes]

    except Exception as e:
        print(f"ERROR: Error during Unstructured processing for {file_name}: {e}")
        return []