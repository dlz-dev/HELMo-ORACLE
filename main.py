from core.preprocess import QuestionProcessor

####################### TEST de la phase de prétraitement

def test_simple():
    processor = QuestionProcessor()

    # Deux connaissances très différentes
    connaissance_1 = "Le soleil brille et il fait tres chaud dehors."
    connaissance_2 = "La pizza au fromage est délicieuse et croustillante."

    # On les vectorise
    vec_c1 = processor.vectoriser(processor.clean_text(connaissance_1))
    vec_c2 = processor.vectoriser(processor.clean_text(connaissance_2))

    # Question sans ambiguïté
    question_joueur = "Est-ce qu'il y a du soleil ?"
    print(f"\n--- TEST SIMPLE ---")
    print(f"Question : {question_joueur}")

    vec_q = processor.vectoriser(processor.clean_text(question_joueur))

    # Comparaison
    score_meteo = processor.comparer(vec_q, vec_c1)
    score_pizza = processor.comparer(vec_q, vec_c2)

    print(f"Score Météo : {score_meteo:.4f}")
    print(f"Score Pizza : {score_pizza:.4f}")

    if score_meteo > score_pizza:
        print("Résultat : L'Oracle a bien reconnu le sujet Météo !")


#######################


if __name__ == '__main__':
    test_simple()