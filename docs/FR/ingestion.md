# Pipeline d'Ingestion de Données

Ce document détaille le processus par lequel les informations brutes sont transformées, enrichies et stockées dans notre base de connaissances vectorielle. Ce pipeline est conçu pour être modulaire, robuste et capable de traiter une grande variété de formats de fichiers.

## 1. Fichiers d'Entrée

Le pipeline commence avec un ensemble de fichiers sources. Ces fichiers peuvent provenir de diverses origines et se présenter sous plusieurs formats :

-   Fichiers structurés : `.csv`, `.json`
-   Fichiers texte simples : `.txt`, `.md`
-   Documents complexes : `.pdf`, `.docx`

Ces fichiers sont placés dans un répertoire `data/files/` surveillé par le système.

## 2. Validation du Contenu (Guardian)

Chaque fichier entrant est d'abord soumis à un **Gardien**. Ce composant utilise un modèle de langage (LLM) pour effectuer une première analyse du contenu.

-   **Objectif** : Vérifier si le contenu du fichier correspond au domaine thématique attendu par l'application.
-   **Fonctionnement** : Le LLM évalue le texte et rend un verdict.
    -   **✅ Accepté** : Si le contenu est pertinent, le fichier passe à l'étape suivante.
    -   **❌ Rejeté** : Si le contenu est jugé hors sujet, le fichier est déplacé dans un répertoire de quarantaine (`data/quarantine/`) pour un examen manuel.

Cette étape de validation garantit que seule l'information pertinente est intégrée à la base de connaissances.

## 3. Contextualisation par LLM

Une fois validé, le contenu du fichier est enrichi. Un LLM génère une **description globale** et concise du document (environ 3000 caractères).

Cette description est ensuite **préfixée à chaque morceau (chunk)** de texte extrait du document. Cette technique améliore significativement la précision de la recherche (RAG) en fournissant un contexte plus large à chaque petit fragment d'information.

## 4. Routage et Conversion

Le système route ensuite le fichier vers le convertisseur approprié en fonction de son format :

-   **Convertisseurs natifs** : Des parseurs optimisés sont utilisés pour les formats simples comme le Markdown, le CSV ou le JSON.
-   **Service Unstructured.io** : Pour les formats complexes comme les PDF et les DOCX, nous utilisons `Unstructured.io`. Ce service est capable d'extraire le texte de manière fiable en utilisant deux modes :
    -   `HI_RES` : Pour une extraction de haute fidélité, préservant la mise en page.
    -   `FAST` : Pour une extraction plus rapide lorsque la structure est moins critique.

## 5. Hachage des Chunks

Après la conversion, le document est divisé en chunks. Pour chaque chunk, un **hash unique** (SHA256) est calculé à partir de son contenu.

Ce `chunk_hash` sert d'identifiant et permet d'éviter l'ingestion de contenu dupliqué. Si un chunk avec le même hash existe déjà dans la base de données, il est simplement ignoré.

## 6. Création des Embeddings

Chaque chunk de texte (préfixé de sa description globale) est ensuite transformé en un vecteur numérique, ou **embedding**.

-   **Modèle utilisé** : `nomic-embed-text`, servi via un conteneur **Ollama** dédié (`embedding_service`). Supporte jusqu'à 8 192 tokens de contexte, levant la limite de 512 tokens de l'ancien modèle.
-   **Dimension** : Chaque vecteur est de 768 dimensions.
-   **Late chunking contextuel** : chaque chunk est préfixé des chunks précédents avant embedding, capturant le contexte du document plutôt que le chunk isolé.

Ces embeddings capturent la signification sémantique du texte, permettant des recherches basées sur le sens plutôt que sur les mots-clés.

## 7. Stockage dans la Base Vectorielle

Enfin, les données traitées sont stockées dans une base de données vectorielle. Le système supporte deux modes de déploiement :

1.  **☁️ Mode Cloud (Production)** :
    -   **Technologie** : **Supabase** avec l'extension `pgvector`.
    -   **Opération** : `INSERT` des documents avec leur contenu, vecteur, métadonnées et `chunk_hash`.
    -   **Fonctionnalités** : Profite d'une recherche hybride combinant la recherche sémantique (similarité cosinus sur les vecteurs) et la recherche par mot-clé (Full-Text Search).

2.  **💻 Mode Local (Développement)** :
    -   **Technologie** : **ChromaDB**, une base de données vectorielle locale.
    -   **Opération** : `upsert` des documents, ce qui permet d'insérer ou de mettre à jour les chunks en se basant sur leur identifiant.
    -   **Fonctionnalités** : Idéal pour le développement et les tests en environnement hors ligne.

## 8. Journalisation

L'ensemble du processus est tracé dans un fichier de log (`oracle.log`). Cela inclut :
-   Les fichiers acceptés ou rejetés par le Gardien.
-   Le nombre de chunks insérés ou ignorés (car déjà existants) pour chaque fichier.

Cette journalisation est essentielle pour le débogage et le suivi de la santé du pipeline d'ingestion.