# 📂 Instructions pour le dossier `data/files/`

Ce dossier constitue la **matière première** (les Archives Sacrées) de l'Oracle. Tous les fichiers placés ici seront découpés, vectorisés et envoyés dans la base de données PostgreSQL (pgvector) lors de l'exécution du script d'ingestion.

## 🎯 Rôle de ce dossier
Il contient l'intégralité du "Lore", des règles, des statistiques et des textes que l'IA peut consulter pour répondre aux questions des utilisateurs. Si une information n'est pas dans ces fichiers, l'Oracle ne la connaîtra pas.

---

## 🏷️ Conventions de nommage (Obligatoire)

Pour garantir une bonne traçabilité des sources par l'Oracle, tous les fichiers doivent respecter les règles suivantes :

1. **Préfixe obligatoire :** Tous les fichiers **doivent** commencer par `lore_`. 
2. **Minuscules et séparateurs :** Utilisez uniquement des lettres minuscules. Pas d'espaces, utilisez des tirets du bas (`_`) ou des tirets (`-`).
3. **Clarté :** Le nom du fichier doit indiquer clairement son contenu (ce nom sera cité comme source par l'IA).

✅ **Exemples valides :**
- `lore_bestiaire_monstres.json`
- `lore_quetes-principales.csv`
- `lore_histoire_amakna.md`

❌ **Exemples invalides :**
- `Bestiaire.json` *(Manque le préfixe lore_, majuscule)*
- `lore histoire version 2.txt` *(Espaces interdits)*

> 💡 *Note : Un script de renommage automatique (`name change _lore.py`) est disponible pour forcer le préfixe sur les anciens fichiers.*

---

## 📄 Formats acceptés et bonnes pratiques de rédaction

Le pipeline d'ingestion gère 4 types de fichiers. Chacun a ses propres règles pour optimiser la compréhension de l'IA :

### 1. Fichiers Markdown (`.md`)
* **Comment c'est traité :** Le script coupe le texte en fonction des titres (`#`, `##`, `###`).
* **Bonne pratique :** Structurez bien votre document avec des niveaux de titres clairs. Chaque section sous un titre deviendra un "bloc de connaissance" indépendant pour l'Oracle.

### 2. Fichiers JSON (`.json`)
* **Comment c'est traité :** Le script isole chaque objet du JSON. Il repère automatiquement les clés nommées `"name"`, `"nom"` ou `"id"` pour les utiliser comme métadonnées.
* **Bonne pratique :** Privilégiez des listes d'objets bien structurés. Assurez-vous que chaque entité (monstre, objet, PNJ) possède une clé `name` ou `nom` explicite.

### 3. Fichiers CSV (`.csv`)
* **Comment c'est traité :** Chaque ligne du tableur devient un fragment de connaissance indépendant.
* **Bonne pratique :** La première ligne doit absolument contenir les en-têtes de colonnes (ex: `Nom_Arme`, `Degats`, `Element`). 

### 4. Fichiers Texte brut (`.txt`)
* **Comment c'est traité :** Le fichier est coupé en morceaux de 500 caractères. **Attention :** Le script extrait les 300 premiers caractères du fichier pour s'en servir de "Contexte Global" sur tous les autres morceaux.
* **Bonne pratique :** Mettez toujours un résumé clair de 2 ou 3 phrases tout en haut de votre fichier `.txt` pour expliquer de quoi parle le document.

---

## 🚀 Mise à jour de la Base de Données

À chaque fois que vous ajoutez, modifiez ou supprimez un fichier dans ce dossier, vous devez re-générer les vecteurs.

1. **Videz l'ancienne table** dans PostgreSQL pour éviter les doublons (la commande SQL est : `TRUNCATE TABLE documents RESTART IDENTITY;`).
2. **Lancez l'ingestion :** Exécutez le script `ingestion.py` à la racine du projet.