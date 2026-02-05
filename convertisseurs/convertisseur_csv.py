import csv
import json

# première idée pour transformer un CSV en JSON

def transformer_csv(chemin_complet):
    # 1. lire le csv simplement
    with open(chemin_complet, "r", encoding='utf-8') as file:
        lecteur = csv.DictReader(file)
        donnees = list(lecteur)

    return donnees