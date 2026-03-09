import csv


def load_csv_data(file_path: str) -> list[dict[str, str]]:
    """
    Reads a CSV file and converts its content into a list of dictionaries.
    Utilise csv.Sniffer pour détecter le délimiteur et valide strictement l'UTF-8.
    """
    try:
        # Ajout de errors='strict' pour rejeter les mauvais encodages
        with open(file_path, "r", encoding='utf-8', errors='strict') as file:
            # Lire un échantillon pour le sniffer
            sample = file.read(1024)
            file.seek(0)  # On remet le curseur au début du fichier

            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error as e:
                print(f"Fichier CSV ignoré (format non reconnu ou vide) : {file_path} - {e}")
                return []

            reader = csv.DictReader(file, dialect=dialect)
            data = list(reader)

        return data

    except FileNotFoundError:
        raise
    except UnicodeDecodeError as e:
        print(f"⚠️ Erreur d'encodage (non UTF-8 valide) pour {file_path} : {e}")
        return []
    except Exception as e:
        print(f"⚠️ Erreur inattendue lors de la lecture de {file_path} : {e}")
        return []