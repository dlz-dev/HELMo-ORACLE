import json
from typing import List


def parse_json(file_path: str) -> List[str]:
    """
    Lit un fichier JSON et le découpe en fragments textuels.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunks = []
    # Si le JSON est une liste d'objets (ex: liste d'items ou de monstres)
    if isinstance(data, list):
        for item in data:
            chunks.append(json.dumps(item, ensure_ascii=False))
    # Si c'est un dictionnaire classique
    elif isinstance(data, dict):
        for key, value in data.items():
            chunks.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    else:
        chunks.append(str(data))

    return chunks
