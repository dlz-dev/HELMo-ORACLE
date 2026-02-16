
def transformer_md(chemin_fichier):
    with open(chemin_fichier, 'r', encoding='utf-8') as f:
        lignes = f.read().splitlines()

    resultat = []
    for i, texte in enumerate(lignes):
        texte_propre = texte.strip()
        if not texte_propre:
            continue

        # On essaie de deviner le type de contenu
        type_contenu = "paragraphe"
        if texte_propre.startswith("#"):
            type_contenu = "titre"
        elif texte_propre.startswith("- ") or texte_propre.startswith("* "):
            type_contenu = "liste"

        resultat.append({
            "ligne": i + 1,
            "type": type_contenu,
            "contenu": texte_propre
        })

    return resultat

# Test
if __name__ == "__main__":
    # 1. On transforme le MD en données Python
    donnees = transformer_md("../test.md")

    # 2. On écrit ces données dans un nouveau fichier .json
    import json
    with open("test.json", "w", encoding="utf-8") as f:
        json.dump(donnees, f, indent=4, ensure_ascii=False)

    print("Fichier test_projet.json créé avec succès !")