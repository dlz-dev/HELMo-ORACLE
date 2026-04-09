import json
import os
from typing import List, Tuple, Dict, Any


def parse_json(file_path: str, chunk_size: int = 512, batch_size: int = 20) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Reads a JSON file and groups items into batches to minimize the number of
    chunks sent to the embedder. Each batch of `batch_size` items becomes one chunk.
    """
    file_name = os.path.basename(file_path)

    try:
        with open(file_path, "r", encoding="utf-8", errors="strict") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"WARNING: Invalid or badly encoded JSON file ignored ({file_name}): {e}")
        return []
    except Exception as e:
        print(f"ERROR: Unexpected error while reading {file_name}: {e}")
        return []

    def _batch_items(items: list, category: str = "") -> List[Tuple[str, Dict]]:
        """Group items into batches, each batch = one chunk."""
        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i: i + batch_size]
            text = json.dumps(batch, ensure_ascii=False, separators=(",", ":"))
            # If the batch text exceeds chunk_size tokens (approx 4 chars/token),
            # split into smaller batches automatically
            if len(text) > chunk_size * 4 and batch_size > 1:
                for item in batch:
                    item_text = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
                    meta = {"source": file_name}
                    if category:
                        meta["category"] = category
                    if isinstance(item, dict):
                        name = str(item.get("name") or item.get("nom") or item.get("id") or "")
                        if name:
                            meta["item_name"] = name
                    results.append((item_text, meta))
            else:
                meta = {"source": file_name}
                if category:
                    meta["category"] = category
                results.append((text, meta))
        return results

    # Case 1: root is a dict
    if isinstance(data, dict):
        chunks = []
        for parent_key, parent_value in data.items():
            if isinstance(parent_value, list):
                chunks.extend(_batch_items(parent_value, category=parent_key))
            elif isinstance(parent_value, dict):
                text = json.dumps(parent_value, ensure_ascii=False, separators=(",", ":"))
                chunks.append((text, {"source": file_name, "category": parent_key}))
            else:
                chunks.append((str(parent_value), {"source": file_name, "category": parent_key}))
        return chunks

    # Case 2: root is a list
    if isinstance(data, list):
        return _batch_items(data)

    # Case 3: scalar
    return [(str(data), {"source": file_name})]
