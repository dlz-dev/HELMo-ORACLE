# 🚀 Parcours de l'Équipe Tritech : Développement de notre solution RAG

Ce document retrace l'évolution technique de notre projet de RAG (Retrieval-Augmented Generation). Il résume les décisions globales concernant les technologies choisies, nos réponses aux requêtes et e-mails de Marcus (notre partie prenante), ainsi qu'une rétrospective transparente sur les erreurs commises et les leçons apprises durant notre apprentissage.

---

## 🏗️ Phase 0 : Premiers pas et expérimentations

Durant cette phase initiale, notre objectif principal était de prototyper rapidement une solution pour répondre aux premières exigences du projet.

* **Interface Utilisateur : Streamlit**
    * *Décision :* Nous avons choisi Streamlit pour concevoir notre interface.
    * *Raison :* Nous avions besoin d'une solution simple et rapide à mettre en place pour obtenir un affichage fonctionnel en local dans les plus brefs délais.
* **Traitement des données : Parsers et convertisseurs "maison"**
    * *Décision :* Développement de nos propres scripts pour parser des formats spécifiques (JSON, CSV, Texte, Markdown) mentionnés dans le premier e-mail de Marcus.
    * *Apprentissage :* Nous avons conçu notre première solution de vectorisation sans vérifier au préalable si des outils existants répondaient déjà à cette problématique. Nous avons rapidement réalisé que la gestion manuelle des fichiers complexes (notamment ceux contenant des balises) était  difficile.
* **Gestion de version et Sécurité : Les pièges de GitHub**
    * *Erreur :* Push des données brutes et du fichier `config.yaml` directement sur le dépôt GitHub.
    * *Apprentissage :* Nous n'étions pas encore familiers avec les bonnes pratiques, les règles de sécurité et les conventions liées à l'utilisation de Git et GitHub.
* **Environnement de développement : Manque de standardisation**
    * *Erreur :* Absence d'une version Python unifiée. Chaque membre de l'équipe travaillait sur une version différente et utilisait son propre environnement virtuel (`.venv`).
* **Base de Données Vectorielle : Le défi de la synchronisation**
    * *Décision :* Utilisation d'une base de données vectorielle pour découper les documents en *chunks*, les vectoriser, puis effectuer une recherche de similarité en vectorisant la question de l'utilisateur.
    * *Technologies :* Nous avons opté pour PostgreSQL couplé à l'extension pgvector afin d'unifier le stockage relationnel des métadonnées et des embeddings. Ce choix nous permet d'exploiter l'indexation HNSW pour une recherche vectorielle approximative (ANN) très performante, tout en tirant parti de la robustesse du moteur SQL pour implémenter nativement des stratégies de recherche hybride (similarité sémantique dense combinée à un filtrage métadonnées exact).
    * *Erreur :* Déploiement de cette première DB dans un conteneur Docker local propre à chaque développeur.
    * *Conséquence :* Un manque de synchronisation entre les membres de l'équipe concernant l'ingestion des documents.

---

## 🛠️ Phase 1 : Correction des erreurs et professionnalisation

Forts de nos premières expériences, nous avons restructuré le projet pour adopter les standards de l'industrie, en sécurisant notre code et en intégrant des outils plus robustes.

* **Orchestration des requêtes : LangChain & LangGraph**
    * *Évolution :* Intégration des frameworks **LangChain** et **LangGraph** spécifiquement pour gérer la partie "requête" (Querying).
    * *Précision architecturale :* Ces outils ont été utilisés **exclusivement** pour orchestrer le flux de recherche et la génération de la réponse par le LLM, et non pour la phase d'ingestion des documents.
* **Infrastructure de Données : Migration vers Supabase**
    * *Évolution :* Remplacement des bases Docker locales isolées par **Supabase**. 
    * *Bénéfice :* Cela a permis de centraliser notre base de données vectorielle. L'ingestion des documents est désormais gérée de manière indépendante et synchronisée pour toute l'équipe, fournissant une source de vérité unique pour nos requêtes LangChain/LangGraph.
* **Standardisation et Bonnes Pratiques Git**
    * *Ajout :* Mise en place stricte d'un `.gitignore` pour éviter de push des fichiers indésirables ou sensibles.
    * *Standardisation :* Fixation d'une version Python commune pour toute l'équipe afin de garantir la reproductibilité.
    * *Sécurité :* Les fichiers de configuration (`config.yaml`) et les *prompts* systèmes sont désormais masqués (ou fournis sous forme de templates vierges sur le dépôt).
* **Mise en place d'un premier flux de RAG complet**
    * *Implémentation :* Le pipeline est désormais pleinement fonctionnel et segmenté : l'utilisateur pose une question via l'interface, LangChain/LangGraph orchestre la recherche vectorielle sur Supabase, puis renvoie le contexte pertinent au LLM pour générer une réponse précise.

---

## 🚀 Phase 2 : Fonctionnalités avancées, optimisation et qualité

Cette phase a été marquée par la volonté d'améliorer la pertinence des résultats renvoyés par notre RAG, de fiabiliser notre code, mais aussi par de nouvelles erreurs d'optimisation riches en apprentissages.

* **Amélioration de l'ingestion : Context-Aware Chunking et Métadonnées**
    * *Enrichissement :* Ajout de **métadonnées** associées aux *chunks* directement dans notre base de données Supabase. Cela ouvre la porte à des recherches hybrides et à des filtres plus précis.
* **Fiabilisation du projet : Ajout de tests**
    * *Évolution :* Mise en place de tests automatisés pour vérifier le bon fonctionnement de notre pipeline et prévenir les régressions lors des futurs développements.
* **Expérimentation : Late Chunking contextuel via Ollama**
    * *Essai initial :* Nous avons expérimenté le *Late Chunking* token-level avec `intfloat/multilingual-e5-base` (HuggingFace local), mais ce modèle était limité à 512 tokens, ce qui rendait l'approche inefficace sur de longs documents.
    * *Solution retenue :* Migration vers **`nomic-embed-text`** servi via un conteneur **Ollama** dédié (`embedding_service`). Ce modèle supporte 8 192 tokens de contexte. Le late chunking est implémenté en préfixant chaque chunk des chunks précédents avant embedding — une approximation textuelle efficace sans limite matérielle de séquence.
* **Découplage du service d'embedding**
    * *Problème :* Le modèle HuggingFace était chargé en mémoire dans le processus Python du backend, alourdissant le démarrage et rendant le scaling difficile.
    * *Solution :* L'embedding est désormais délégué à un **conteneur Ollama indépendant**, interrogé via HTTP (`OLLAMA_BASE_URL`). Le backend reste léger ; le modèle est persisté dans un volume Docker (`./ollama_data`).

---

## 🛡️ Phase 3 : Sécurisation, Flexibilité et Alignement "LoreKeeper"

Suite à notre première démonstration, nous avons reçu un retour décisif de Markus, notre partie prenante chez RedDragon Games. La validation de notre approche "Data Engineering" (code Python structuré, Type Hints, tests unitaires et absence de notebooks en production) a marqué un tournant. Le projet s'est révélé être **LoreKeeper**, l'Oracle de l'univers du MMORPG *Aethelgard Online*, en préparation pour l'extension *Shadows of the Void*. 

Pour répondre aux nouvelles exigences de robustesse et aux directives technologiques strictes (et confidentielles) de Markus, nous avons massivement fait évoluer notre pipeline.

* **Sécurité et Résilience (Ne jamais planter)**
    * *Protection contre l'injection :* Création du module `guardian.py` pour sécuriser le système contre les injections de code et de prompts malveillants.
    * *Surveillance des données :* Mise en place de `watcher.py` pour surveiller les flux de données entrants.
    * *Gestion des fichiers et Quarantaine :* Pour répondre à l'exigence d'avaler "tout le chaos organique" sans jamais crasher, nous avons implémenté un système de mise en quarantaine automatique des fichiers corrompus, illisibles ou qui ne respectent pas les règles d'ingestion.
    * *Validation sémantique :* Ajout d'une couche de validation pour garantir la pertinence des réponses et limiter drastiquement les hallucinations.
* **Évolution de l'Expérience Conversationnelle**
    * *Mémoire et Historique :* Implémentation de la mémoire à court et long terme pour permettre au RAG de suivre le fil d'une conversation complexe.
    * *Agnosticisme des modèles :* Refonte de l'architecture pour supporter **plusieurs modèles LLM**. Nous ne sommes désormais plus limités à Groq et pouvons basculer facilement d'un fournisseur à l'autre.
* **Alignement sur la Stack "RedDragon Games"**
    Suite aux directives du mail de Markus, nous avons commencé l'intégration des technologies "standards" de l'entreprise pour nettoyer et ingérer leurs 10 ans d'historique (Bibles narratives, dialogues PNJ avec balises, exports JSON) :
    * *Orchestration & UI :* Maintien de **LangChain**, ajout de **LlamaIndex** spécifiquement optimisé pour l'ingestion complexe, et préparation à l'utilisation de **Vercel** pour le streaming de l'interface.
    * *Nettoyage (Data Parsing) :* Abandon définitif de certains de nos parsers maison au profit de **Unstructured.io**. Nous avons délibérément choisi de **ne pas utiliser LlamaParse**. Unstructured s'est avéré amplement suffisant pour traiter nos fichiers aux structures complexes, et l'empilement de ces deux outils aurait considérablement ralenti notre pipeline d'ingestion. Par ailleurs, afin d'éviter de surcharger l'API, nous avons décidé de conserver nos parsers maison pour les formats plus légers (txt, csv et json).
    * *Bases Vectorielles :* Nous utilisions déjà Supabase avec l'extension **pgvector** donc nous respections déjà cette consigne de Markus.
    * *Embeddings (Le Cerveau) :* Adoption du modèle open-source **`nomic-embed-text`** servi via **Ollama**. Par rapport à `intfloat/multilingual-e5-base` initialement utilisé, ce modèle lève la limite de 512 tokens (contexte de 8 192 tokens), s'exécute dans un conteneur isolé et permet un vrai late chunking contextuel.

---

## ⚖️ Phase 4 : Recherche Hybride et Confidentialité des Données

Dans cette phase, nous avons cherché à atteindre un niveau de précision industriel en combinant les forces de la recherche textuelle classique et de la recherche sémantique, tout en garantissant la protection des données sensibles (PII).

* **Optimisation de la pertinence : Recherche Hybride**
    * *Évolution :* Mise en place d'une approche hybride pour pallier les limites de la recherche vectorielle pure (qui peut parfois manquer de précision sur des termes techniques ou des noms propres spécifiques).
    * *Méthodologie :* Combinaison du **BM25 / Full Text Search (FTS)** classique (basé sur les mots-clés) et de la **recherche vectorielle** (basée sur le sens global).
* **Fusion des résultats : Reranking (RRF)**
    * *Implémentation :* Pour réconcilier les deux méthodes de recherche, nous avons intégré un algorithme de **Reciprocal Rank Fusion (RRF)**. 
    * *Bénéfice :* Cela nous permet de recalculer un score unique pour chaque document, garantissant que les résultats les plus pertinents (qu'ils soient identifiés par mots-clés ou par sémantique) remontent en priorité.
* **Sécurité et Éthique : PII Masking**
    * *Évolution :* Conformément aux exigences de confidentialité pour le projet LoreKeeper, nous avons intégré une couche de **PII Masking** (Personally Identifiable Information).
    * *Technologie :* Utilisation de la bibliothèque **SpaCy** pour détecter et masquer automatiquement les informations sensibles (noms réels, emails, données privées) dans les documents avant leur traitement par le LLM, évitant ainsi toute fuite de données confidentielles dans les prompts.

---

## 🏁 Phase Finale : Déploiement, Architecture Distribuée et Autonomie

Pour cette ultime étape, l'objectif était de transformer notre prototype avancé en une véritable application de production, robuste, scalable et totalement indépendante. Nous avons fait le choix de quitter les services tiers (SaaS) pour une infrastructure maîtrisée, tout en purgeant définitivement notre dette technique.

* **Souveraineté des données : Migration vers DigitalOcean**
    * *Base de Données :* Désormais, notre base de données n'est plus hébergée sur Supabase. Elle a été migrée directement sur notre **VPS DigitalOcean**, nous offrant un contrôle total sur les performances et la configuration de **pgvector**.
    * *Stockage des fichiers :* De la même manière, les documents et fichiers sources sont maintenant stockés et gérés directement **sur le serveur**. Cette centralisation élimine les dépendances externes et réduit drastiquement les temps d'accès lors de la phase d'ingestion.
* **Séparation Front-End / Back-End (Architecture Microservices)**
    * *Front-End (Interface utilisateur) :* Développement d'une interface moderne avec **Next.js** et **Tailwind CSS**. L'application est déployée sur **Vercel**.
    * *Back-End (Logique et API) :* Une API RESTful performante avec **FastAPI**, structurée avec des routes modulaires, hébergée sur le VPS derrière un reverse proxy **Nginx**.
* **Résolution de la Dette Technique et Observabilité**
    * *Nettoyage complet :* Le fichier `requirements.txt` a été **entièrement épuré**. Il ne contient plus que les dépendances critiques, garantissant un environnement léger et sécurisé.
    * *Surveillance et Fiabilité :* Implémentation de routes de **Health Check** pour monitorer la disponibilité des API et ajout d'un système de **logs** complet pour la traçabilité des requêtes et du comportement du LLM.
* **DevOps, Automatisation et Innovation**
    * *Conteneurisation et CI/CD :* Ajout d'un **Dockerfile** pour un déploiement reproductible et mise en place de pipelines **CI/CD** pour l'exécution automatique de nos **tests unitaires**.
    * *Standard MCP & Licence :* Intégration du **Model Context Protocol (MCP)** pour une connexion unifiée aux sources de données et adoption d'une **Licence MIT** pour définir le cadre légal du projet.