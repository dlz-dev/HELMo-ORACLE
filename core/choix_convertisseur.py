from convertisseurs import convertisseur_txt, convertisseur_csv
import os


def traiter_fichier(chemin_fichier):
    extension = os.path.splitext(chemin_fichier)[1].lower()

    if extension == '.csv':
        donnees = convertisseur_csv.transformer_csv(chemin_fichier)
    elif extension == '.txt':
        donnees = convertisseur_txt.transformer_txt(chemin_fichier)
    else:
        raise ValueError("Format non supporté")

    return donnees