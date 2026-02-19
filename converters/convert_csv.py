import csv


def load_csv_data(file_path: str) -> list[dict[str, str]]:
    """
    Reads a CSV file and converts its content into a list of dictionaries.
    """
    with open(file_path, "r", encoding='utf-8') as file:
        reader = csv.DictReader(file)
        data = list(reader)

    return data
