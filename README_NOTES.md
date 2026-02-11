# Projet Oracle IA - Documentation Technique

Ce projet vise à concevoir un **Oracle intelligent** capable de répondre aux questions sur l'univers d'un jeu vidéo en s'appuyant sur une architecture **RAG** (Retrieval-Augmented Generation).

---

## Organisation du Projet
Le projet suit une structure modulaire pour garantir la clarté et la maintenance :
* **`data/`** : Stockage des sources brutes (CSV, JSON, TXT, MD) et de la base de données Postgres.
* **`convertisseurs/`** : Scripts d'automatisation pour uniformiser les données hétérogènes.
* **`core/`** : Logique métier incluant le prétraitement et le moteur de vectorisation.
* **`main.py`** : Script de test et chef d'orchestre du projet.

---

## Réalisations (Suivi Kanban)

### 1. Gestion des Données (Data Management)
* **Standardisation** : Conversion de fichiers TXT, CSV et MD vers un format **JSON pivot**.
* **Persistance** : Mise en place d'une base **SQLite** (fichier `.db`) pour centraliser les connaissances et faciliter le partage au sein du groupe.
* **Nettoyage** : Filtrage des données brutes pour ne conserver que les informations utiles au Lore du jeu.

### 2. Prétraitement de la Question (Preprocessing)
Développement du module `core/preprocess.py` pour raffiner les entrées utilisateur :
* **Lowercasing** : Passage systématique en minuscules pour l'uniformité.
* **Dé-accentuation** : Normalisation Unicode pour éviter les erreurs de frappe (ex: "épée" -> "epee").
* **Nettoyage ponctuel** : Suppression des caractères spéciaux et de la ponctuation.
* **Filtrage Stopwords** : Retrait des mots "vides" (le, la, de, du) pour isoler les mots-clés sémantiques.

### 3. Moteur IA & Vectorisation
* **Modèle d'Embedding** : Intégration de la bibliothèque `sentence-transformers` (modèle `all-MiniLM-L6-v2`).
* **Vectorisation** : Transformation du texte en vecteurs de **384 dimensions** (coordonnées mathématiques du sens).
* **Similarité Cosinus** : Implémentation d'un algorithme de comparaison pour mesurer la proximité entre la question du joueur et les connaissances stockées.

---

## Installation et Tests

### Prérequis
Installer les dépendances du requirements.txt



###########################################################################################################




# Projet Oracle : Système de Recherche Vectorielle (RAG)

Ce projet permet de transformer des documents bruts (CSV, MD, TXT) en une base de connaissances intelligente.
Il utilise l'IA pour transformer le texte en vecteurs mathématiques et les stocker dans une base PostgreSQL.

---

## Prérequis

1. Docker Desktop (doit être lancé).
2. Python 3.10+ (Testé avec succès sur 3.12 et 3.14).
3. Les fichiers à indexer doivent se trouver dans : `data/files/`

---

## Guide de démarrage rapide

### 1. Lancer l'infrastructure (Docker)

Ouvre un terminal à la racine du projet et lance le container PostgreSQL (avec l'extension pgvector) :

docker-compose up -d

### 2. Installer les bibliothèques Python

Installe les dépendances nécessaires (IA + Base de données) :

pip install langchain langchain-community langchain-huggingface sentence-transformers psycopg[binary] pgvector

### 3. Alimenter la base de données (Importation)

Cette commande lit tes documents, les transforme en vecteurs et les injecte dans Docker :

python -m core.choix_convertisseur

Note : Le script téléchargera le modèle d'IA (environ 100 Mo) au premier lancement.
C'est normal si le terminal semble figé quelques instants.

### 4. Interroger l'Oracle (Test)

Pour poser une question à l'Oracle et vérifier qu'il trouve les bonnes infos :

python test_temporaire_oracle.py

---

## Structure du Projet

core/                 → Logique de vectorisation (preprocess.py) et gestion du Docker (gestionnaire_vecteurs.py)
convertisseurs/       → Modules de nettoyage spécifique pour chaque format (CSV, MD, TXT)
data/files/           → Dossier source où déposer tes documents à indexer
docker-compose.yml    → Configuration du container de stockage
init_vector_db.sql    → Script d'initialisation de la table SQL

---

## Notes Techniques & Troubleshooting

Python 3.14+ :
Si tu vois un UserWarning sur Pydantic V1, c'est normal.
Ignore-le, cela n'empêche pas le script de fonctionner.

Erreur SQL :
La base utilise les colonnes content (le texte) et vecteur (les données IA).
Le code Python est configuré pour correspondre à ces noms.

Base vide :
Si le test affiche "L'Oracle n'a rien trouvé", relance l'étape 3 pour t'assurer que les données ont bien été insérées.

---

Développé pour le Projet IA – Intégration RAG – HELMo BLOC 2
