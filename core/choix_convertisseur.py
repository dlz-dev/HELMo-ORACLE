from convertisseurs import convertisseur_csv, convertisseur_md
import os
import json


def traiter_fichier():

    dossier_entree = "../data/files/"
    dossier_sortie = "../data/processed/"

    # création du dossier s'il n'existe pas
    if not os.path.exists(dossier_sortie):
        os.makedirs(dossier_sortie)

    for nom_fichier in os.listdir(dossier_entree):
        chemin_complet = os.path.join(dossier_entree, nom_fichier)
        extension = os.path.splitext(nom_fichier)[1].lower()

        result = None

        if extension == '.csv':
            print(f"Traitement CSV : {nom_fichier}")
            result = convertisseur_csv.transformer_csv(chemin_complet)

        elif extension == '.md':
            print(f"Traitement MD : {nom_fichier}")
            result = convertisseur_md.transformer_md(chemin_complet)

        # elif extension == '.txt':
        #     print(f"Traitement TXT : {nom_fichier}")
        #     result = convertisseur_txt.transformer_txt(chemin_complet)

        # pour le cas ou c'est un déjà un json
        elif extension == '.json':
            print(f"Fichier déjà en JSON : {nom_fichier}")
            with open(chemin_complet, "r", encoding='utf-8') as file:
                result = json.load(file)  # on le lit juste pour le renvoyer

        if result:
            nom_json = nom_fichier.replace(extension, ".json")
            with open(os.path.join(dossier_sortie, nom_json), "w", encoding='utf-8') as file:
                json.dump(result, file, indent=4, ensure_ascii=False)
            print(f"Sauvegardé dans processed/{nom_json}")

if __name__ == "__main__":
    traiter_fichier()