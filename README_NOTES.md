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