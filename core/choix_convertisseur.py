import os
from convertisseurs import convertisseur_csv, convertisseur_md, convertisseur_txt
from core.gestionnaire_vecteurs import GestionnaireVecteurs


def alimenter_base_de_donnees():

    chemin_actuel = os.path.dirname(os.path.abspath(__file__))

    dossier_entree = os.path.join(chemin_actuel, "..", "data", "files")
    print(f"Dossier source détecté : {os.path.abspath(dossier_entree)}")

    # initialisation le gestionnaire qui se connecte au docker
    gestionnaire = GestionnaireVecteurs()
    print("Connexion à la base de données réussie. Début de l'importation...")

    for nom_fichier in os.listdir(dossier_entree):
        chemin_complet = os.path.join(dossier_entree, nom_fichier)
        extension = os.path.splitext(nom_fichier)[1].lower()

        textes_a_inserer = []

        # traitement selon le format
        if extension == '.csv':
            print(f"Traitement CSV : {nom_fichier}")
            donnees = convertisseur_csv.transformer_csv(chemin_complet)
            for ligne in donnees:
                phrase = " ".join([f"{cle}: {valeur}" for cle, valeur in ligne.items()])
                textes_a_inserer.append(phrase)

        elif extension == '.md':
            print(f"Traitement MD : {nom_fichier}")
            donnees = convertisseur_md.transformer_md(chemin_complet)
            for item in donnees:
                textes_a_inserer.append(item['contenu'])

        elif extension == '.txt':
            print(f"Traitement TXT : {nom_fichier}")
            splits = convertisseur_txt.transformer_txt(chemin_complet)
            for doc in splits:
                textes_a_inserer.append(doc.page_content)

        # # pour le cas ou c'est un déjà un json
        # elif extension == '.json':
        #     print(f"Fichier déjà en JSON : {nom_fichier}")
        #     with open(chemin_complet, "r", encoding='utf-8') as file:
        #         result = json.load(file)  # on le lit juste pour le renvoyer


        # insertion dans la base de données
        if textes_a_inserer:
            print(f"Insertion de {len(textes_a_inserer)} morceaux en base...")
            for texte in textes_a_inserer:
                gestionnaire.ajouter_document(texte)
            print(f"{nom_fichier} terminé.")

if __name__ == "__main__":
    alimenter_base_de_donnees()