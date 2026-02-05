import csv
import json

# première idée pour transformer un CSV en JSON

def transformer_csv(nom_fichier):
    # 1. lire le csv simplement
    with open(f"{nom_fichier}.csv", "r", encoding='utf-8') as file:
        lecteur = csv.DictReader(file)
        donnees = list(lecteur)

    # 2. créer le json
    with open(f"{nom_fichier}.json", "w", encoding='utf-8') as file:
        json.dump(donnees, file, indent=4) # indent pour rendre le json beau et lisible

    print(f"Fichier {nom_fichier}.json généré avec succès !")

# pour tester sur le fichier test -> exécuter transformer_csv('test')
transformer_csv('test')