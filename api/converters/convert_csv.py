import csv
import json
import os
from typing import List, Tuple, Dict, Any


def load_csv_data(file_path: str, chunk_size: int = 512, batch_size: int = 20) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Reads a CSV file and groups rows into batches to minimize the number of
    chunks sent to the embedder. Each batch of `batch_size` rows becomes one chunk.
    """
    file_name = os.path.basename(file_path)
    rows = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="strict") as f:
            sample = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample)
            reader = csv.DictReader(f, dialect=dialect)
            for row in reader:
                rows.append(dict(row))

    except csv.Error as e:
        print(f"WARNING: Unrecognized CSV format or empty file ignored ({file_name}): {e}")
        return []
    except UnicodeDecodeError as e:
        print(f"WARNING: UTF-8 encoding error for {file_name}: {e}")
        return []
    except Exception as e:
        print(f"ERROR: Unexpected error while reading {file_name}: {e}")
        return []

    if not rows:
        return []

    chunks = []
    for i in range(0, len(rows), batch_size):
        batch = rows[i: i + batch_size]
        text = json.dumps(batch, ensure_ascii=False, separators=(",", ":"))
        # If batch is too large, fall back to one row per chunk
        if len(text) > chunk_size * 4 and batch_size > 1:
            for row in batch:
                chunks.append((json.dumps(row, ensure_ascii=False, separators=(",", ":")), {"source": file_name}))
        else:
            chunks.append((text, {"source": file_name}))

    return chunks
