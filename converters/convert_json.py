import json
from typing import List, Tuple


def parse_json(file_path: str) -> List[Tuple[str, dict]]:
    """
    Reads a JSON file and splits it into logical objects.
    Extracts parent keys as metadata.
    Returns a list of tuples (chunk_text, metadata_dictionary).
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunks_with_metadata = []

    # Case 1: The JSON is a large dictionary
    if isinstance(data, dict):
        for parent_key, parent_value in data.items():

            # If the category contains a list of objects
            if isinstance(parent_value, list):
                for item in parent_value:
                    metadata = {"category": parent_key}

                    # If the object has a name or an ID, we isolate it
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("nom") or item.get("id")
                        if name:
                            metadata["item_name"] = str(name)

                    chunk_text = json.dumps(item, ensure_ascii=False)
                    chunks_with_metadata.append((chunk_text, metadata))

            # If the category contains a single object
            elif isinstance(parent_value, dict):
                metadata = {"category": parent_key}
                chunk_text = json.dumps(parent_value, ensure_ascii=False)
                chunks_with_metadata.append((chunk_text, metadata))

            # Other (raw text)
            else:
                metadata = {"category": parent_key}
                chunks_with_metadata.append((str(parent_value), metadata))

    # Case 2: The JSON is directly a list (no parent key)
    elif isinstance(data, list):
        for item in data:
            metadata = {}
            if isinstance(item, dict):
                name = item.get("name") or item.get("nom") or item.get("id")
                if name:
                    metadata["item_name"] = str(name)

            chunk_text = json.dumps(item, ensure_ascii=False)
            chunks_with_metadata.append((chunk_text, metadata))

    else:
        chunks_with_metadata.append((str(data), {}))

    return chunks_with_metadata
