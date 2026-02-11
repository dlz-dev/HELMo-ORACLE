from core.preprocess import QuestionProcessor
from core.gestionnaire_vecteurs import GestionnaireVecteurs

# 1. Initialisation
prep = QuestionProcessor()
gestionnaire = GestionnaireVecteurs()

# 2. exemple de question posée simple
question = "c'est quoi : Pic des Brumes ?"

# 3. recherche dans l'oracle
vecteur = prep.vectoriser(prep.clean_text(question))
resultats = gestionnaire.rechercher_similaires(vecteur, k=1) # on prend le meilleur

# 4. affichage
if resultats:
    print("\nL'Oracle a trouvé ceci :")
    print(resultats[0][0]) # affiche le texte du premier résultat
else:
    print("\nL'Oracle n'a rien trouvé...")