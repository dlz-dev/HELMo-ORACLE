import json
from typing import List


def parse_json(file_path: str) -> List[str]:
    """
    Reads a JSON file and splits it into textual chunks.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunks = []
    # If the JSON is a list of objects
    if isinstance(data, list):
        for item in data:
            chunks.append(json.dumps(item, ensure_ascii=False))
    # If it is a standard dictionary
    elif isinstance(data, dict):
        for key, value in data.items():
            chunks.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    else:
        chunks.append(str(data))

    return chunks