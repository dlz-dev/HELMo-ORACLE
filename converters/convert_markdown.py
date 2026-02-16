from typing import List, Dict


def parse_markdown(file_path: str) -> List[Dict[str, any]]:
    """
    Reads a Markdown file and extracts basic structure (headings, lists, paragraphs).

    Args:
        file_path (str): The path to the .md file to be parsed.

    Returns:
        List[Dict[str, any]]: A list of dictionaries containing line numbers, 
                              content types, and the clean text.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        # splitlines() removes the trailing \n automatically
        lines = f.read().splitlines()

    parsed_data = []

    for i, text in enumerate(lines):
        clean_text = text.strip()

        # Skip empty lines to keep the data relevant for RAG indexing
        if not clean_text:
            continue

        # Simple logic to determine the content type
        content_type = "paragraph"
        if clean_text.startswith("#"):
            content_type = "heading"
        elif clean_text.startswith(("- ", "* ", "1. ")):
            content_type = "list_item"

        parsed_data.append({
            "line_number": i + 1,
            "type": content_type,
            "content": clean_text
        })

    return parsed_data
