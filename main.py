from core.preprocess import QuestionProcessor

####################### TEST de la phase de prétraitement

def test_oracle():
    # 1. initialisation de ton processeur
    processor = QuestionProcessor()

    # 2. liste de questions de test
    questions_test = [
        "OU est L'éPéE de FER ?",
        "COMMENT BATTRE le Dragon de FEU DE Liège ?"
    ]

    # 3. traitement
    print(f"----- Début de la phase de prétraitement ------")

    for question in questions_test:
        print(f"Question brute : {question}")

        # appel de la fonction
        clean_q = processor.clean_text(question)

        print(f"Question propre : {clean_q}")


#######################


if __name__ == '__main__':
    test_oracle()