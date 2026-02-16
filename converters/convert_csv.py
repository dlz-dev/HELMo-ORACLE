import csv


def load_csv_data(file_path: str) -> list[dict[str, str]]:
    """
    Reads a CSV file and converts its content into a list of dictionaries.

    Args:
        file_path (str): The complete path to the CSV file to be read.

    Returns:
        List[Dict[str, str]]: A list of rows, where each row is a dictionary
                              mapping column headers to their respective values.
    """
    with open(file_path, "r", encoding='utf-8') as file:
        reader = csv.DictReader(file)
        data = list(reader)

    return data
